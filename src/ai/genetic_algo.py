import json
import logging
import os
import random
import time
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from statistics import mean
from typing import Dict, List, Optional, Tuple

from src.ai.level3_agent import Level3Agent
from src.ai.level4_agent import Level4Agent
from src.ai.level5_agent import Level5Agent
from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState
from src.entities.pokemon import Pokemon
from src.utils.data_loader import DataLoader
from src.utils.move_registry import get_data_loader

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_OUTPUT_PATH = os.path.join(ROOT_DIR, 'data', 'ai', 'level5_weights.json')
DEFAULT_POKEMON_PATH = os.path.join(ROOT_DIR, 'data', 'pokemon_pool.json')
DEFAULT_MOVES_PATH = os.path.join(ROOT_DIR, 'data', 'moves_pool.json')
DEFAULT_LOG_PATH = os.path.join(ROOT_DIR, 'data', 'ai', 'level5_ga.log')


def _init_worker() -> None:
    """Inicializa el singleton de DataLoader en cada worker de multiprocessing.

    Usado como `initializer` de `multiprocessing.Pool` para que cada proceso
    hijo tenga su propia instancia compartida (singleton via `lru_cache`).
    """
    get_data_loader(DEFAULT_POKEMON_PATH, DEFAULT_MOVES_PATH)


@dataclass
class GeneticConfig:
    """Configuracion del algoritmo genetico.

    Attributes:
        population_size: Cantidad de individuos por generacion.
        elite_size: Cuantos individuos pasan intactos a la siguiente generacion.
        mutation_rate: Probabilidad de mutar cada gen de un hijo.
        mutation_strength: Desviacion estandar de la mutacion, como fraccion del rango del gen.
        tournament_size: Tamanio del torneo en la seleccion por torneo.
        max_generations: Numero maximo de generaciones antes de cortar.
        patience: Generaciones sin mejora antes de hacer early stop.
        min_improvement: Mejora minima en el holdout para considerarla un avance real.
        battles_phase1: Batallas por escenario en la primera fase de evaluacion.
        battles_phase2: Batallas por escenario al re-evaluar el top de la fase 1.
        top_fraction: Fraccion de la poblacion que se re-evalua en la fase 2.
        team_size: Tamanio de los equipos generados en cada escenario.
        scenarios_per_opponent: Escenarios aleatorios por cada oponente del mapa.
        holdout_scenarios_level4: Escenarios reservados para validar contra L4.
        holdout_battles: Batallas por escenario del holdout.
        max_turns: Tope de turnos por batalla antes de declarar empate.
        seed: Semilla maestra del experimento.
        n_cores: Workers de multiprocessing; None = usar todos los disponibles.
        diversity_pressure: Peso de la penalizacion por parecerse a los elites.
        log_path: Ruta del archivo de log.
        output_path: Ruta del JSON donde se persisten los mejores pesos.
    """
    population_size: int = 40
    elite_size: int = 4
    mutation_rate: float = 0.15
    mutation_strength: float = 0.20
    tournament_size: int = 5
    max_generations: int = 50
    patience: int = 15
    min_improvement: float = 0.005
    battles_phase1: int = 4
    battles_phase2: int = 8
    top_fraction: float = 0.35
    team_size: int = 4
    scenarios_per_opponent: int = 4
    holdout_scenarios_level4: int = 8
    holdout_battles: int = 4
    max_turns: int = 120
    seed: int = 42
    n_cores: Optional[int] = None
    diversity_pressure: float = 0.05
    log_path: str = DEFAULT_LOG_PATH
    output_path: str = DEFAULT_OUTPUT_PATH


OPPONENT_MAP: Dict[str, Tuple[type, float]] = {
    'Level3Agent': (Level3Agent, 1.00),
    'Level4Agent': (Level4Agent, 15.00),
}


DEFAULT_BOUNDS: Dict[str, Tuple[float, float]] = {
    'hp':     (0.0, 1.5),
    'alive':  (0.0, 1.5),
    'type':   (0.0, 1.0),
    'speed':  (0.0, 0.5),
    'status': (0.0, 0.5),
}

def _setup_logger(log_path: str) -> logging.Logger:
    """Crea un logger que escribe a archivo y consola.

    Args:
        log_path (str): Ruta del archivo de log. El directorio se crea si no existe.

    Returns:
        logging.Logger: Logger llamado 'level5_ga' con un FileHandler y un StreamHandler.

    Raises:
        OSError: Si no se puede crear el directorio del archivo de log.
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger('level5_ga')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.propagate = False
    return logger

def _clamp(v: float, lo: float, hi: float) -> float:
    """Satura `v` al intervalo cerrado [lo, hi].

    Args:
        v (float): Valor a limitar.
        lo (float): Cota inferior.
        hi (float): Cota superior.

    Returns:
        float: `v` recortado a [lo, hi].
    """
    return max(lo, min(hi, v))


def _random_weights() -> Dict[str, float]:
    """Muestrea un vector de pesos uniforme en DEFAULT_BOUNDS.

    Returns:
        Dict[str, float]: {nombre_peso: valor_aleatorio_redondeado_a_4_decimales}.
    """
    return {k: round(random.uniform(lo, hi), 4) for k, (lo, hi) in DEFAULT_BOUNDS.items()}


def _tournament_select(population: List[Dict], fitnesses: List[float], size: int) -> Dict:
    """Selecciona un individuo por torneo.

    Args:
        population (List[Dict]): Poblacion actual.
        fitnesses (List[float]): Fitness de cada individuo (mismo orden).
        size (int): Tamanio del torneo.

    Returns:
        Dict: Copia del ganador del torneo.
    """
    idx = random.sample(range(len(population)), k=min(size, len(population)))
    best = max(idx, key=lambda i: fitnesses[i])
    return dict(population[best])


def _crossover(a: Dict, b: Dict) -> Dict:
    """Operador de cruza BLX-alpha entre dos vectores de pesos.

    Para cada gen, muestrea uniforme en [min - alpha*rango, max + alpha*rango]
    y luego satura al DEFAULT_BOUNDS del gen.

    Args:
        a (Dict): Padre A con las mismas claves que DEFAULT_BOUNDS.
        b (Dict): Padre B con las mismas claves que DEFAULT_BOUNDS.

    Returns:
        Dict: Hijo con un valor por clave de DEFAULT_BOUNDS.

    Raises:
        KeyError: Si `a` o `b` no contienen las claves esperadas.
    """
    child = {}
    alpha = 0.25
    for k, (lo, hi) in DEFAULT_BOUNDS.items():
        lo_p = min(a[k], b[k]) - alpha * abs(a[k] - b[k])
        hi_p = max(a[k], b[k]) + alpha * abs(a[k] - b[k])
        val = random.uniform(lo_p, hi_p)
        child[k] = round(_clamp(val, lo, hi), 4)
    return child


def _mutate(candidate: Dict, mutation_rate: float, mutation_strength: float) -> Dict:
    """Muta cada gen con probabilidad `mutation_rate` mediante ruido gaussiano.

    La desviacion estandar del ruido es `mutation_strength` por el rango del gen.

    Args:
        candidate (Dict): Individuo a mutar.
        mutation_rate (float): Probabilidad por gen de aplicar ruido.
        mutation_strength (float): Magnitud del ruido como fraccion del rango.

    Returns:
        Dict: Copia mutada de `candidate`. No modifica el original.
    """
    out = dict(candidate)
    for k, (lo, hi) in DEFAULT_BOUNDS.items():
        if random.random() <= mutation_rate:
            span = hi - lo
            out[k] = round(_clamp(out[k] + random.gauss(0.0, mutation_strength * span), lo, hi), 4)
    return out


def _diversity_penalty(candidate: Dict, elites: List[Dict], pressure: float) -> float:
    """Penaliza candidatos demasiado parecidos a los elites.

    Args:
        candidate (Dict): Individuo a evaluar.
        elites (List[Dict]): Lista de elites de la generacion anterior.
        pressure (float): Magnitud maxima de la penalizacion.

    Returns:
        float: Valor en [-pressure, 0]. 0 si no hay elites o `pressure<=0`.
    """
    if not elites or pressure <= 0.0: return 0.0
    keys = list(DEFAULT_BOUNDS.keys())
    min_dist = min(sum((candidate[k] - e[k]) ** 2 for k in keys) ** 0.5 for e in elites)
    max_dist = sum((hi - lo) ** 2 for lo, hi in DEFAULT_BOUNDS.values()) ** 0.5
    normalized = min_dist / max(max_dist, 1e-9)
    return -pressure * max(0.0, 0.25 - normalized)

def _run_headless_battle(p1_team, p2_team, agent1, agent2, max_turns: int = 120):
    """Ejecuta una batalla completa entre dos equipos sin interfaz grafica.

    Args:
        p1_team (list): Lista de Pokemon del jugador 1.
        p2_team (list): Lista de Pokemon del jugador 2.
        agent1: Agente que controla al jugador 1.
        agent2: Agente que controla al jugador 2.
        max_turns (int): Tope de turnos antes de declarar empate. Por defecto 120.

    Returns:
        tuple: (ganador, turnos_jugados, p1_team_final, p2_team_final).
            ganador es 1, 2 o None (empate/timeout).
    """
    p1_idx, p2_idx = 0, 0
    winner = None
    turns_played = 0
    for turn in range(1, max_turns + 1):
        turns_played = turn
        state = BattleState(
            p1_team=[p.to_state() for p in p1_team], p2_team=[p.to_state() for p in p2_team],
            p1_active_index=p1_idx, p2_active_index=p2_idx, turn_number=turn,
        )
        a1 = agent1.get_action(state)
        a2 = agent2.get_action(state)
        result, p1_idx, p2_idx = process_turn(p1_team, p1_idx, a1, p2_team, p2_idx, a2)
        winner = result.winner
        if result.match_over: break
    return winner, turns_played, p1_team, p2_team

def _normalized_team_hp(team) -> float:
    """Calcula la fraccion de HP total restante de un equipo (0.0 a 1.0).

    Args:
        team (list): Lista de objetos Pokemon.

    Returns:
        float: Suma de HP actuales / suma de HP maximos. Devuelve 0.0 si el equipo esta vacio.
    """
    cur = sum(max(0, p.current_hp) for p in team)
    mx = sum(max(1, p.max_hp) for p in team)
    return cur / mx

def _alive_ratio(team) -> float:
    """Calcula la fraccion de miembros vivos de un equipo.

    Args:
        team (list): Lista de objetos Pokemon.

    Returns:
        float: Numero de Pokemon con HP > 0 dividido por el tamanio del equipo (minimo 1).
    """
    return sum(1 for p in team if p.current_hp > 0) / max(1, len(team))

def _score_battle(winner, turns, p1_team, p2_team, perspective: int, max_turns: int, opp_weight: float = 1.0) -> float:
    """Puntuacion de la batalla vista desde la perspectiva indicada.

    Combina: resultado (65%), HP residual (15%), vivos (10%), velocidad de victoria (10%).

    Args:
        winner (int): Ganador (1 o 2). None si empate/timeout.
        turns (int): Turnos jugados.
        p1_team (list): Equipo final del jugador 1.
        p2_team (list): Equipo final del jugador 2.
        perspective (int): Lado desde el que se evalua (1 o 2).
        max_turns (int): Tope de turnos usado para normalizar la velocidad.
        opp_weight (float): Multiplicador para pesar la dificultad del oponente.

    Returns:
        float: Puntuacion en [-opp_weight, opp_weight] aprox.
    """
    my_team = p1_team if perspective == 1 else p2_team
    opp_team = p2_team if perspective == 1 else p1_team

    hp_component = _normalized_team_hp(my_team) - _normalized_team_hp(opp_team)
    alive_component = _alive_ratio(my_team) - _alive_ratio(opp_team)

    if winner == perspective: result_component = 1.0
    elif winner is None: result_component = -0.15
    else: result_component = -1.0

    speed_component = max(0.0, (max_turns - turns) / max_turns) if winner == perspective else 0.0

    raw = (
        0.65 * result_component
        + 0.15 * hp_component
        + 0.10 * alive_component
        + 0.10 * speed_component
    )
    return raw * opp_weight

def _eval_candidate_on_scenarios(args) -> float:
    """Evalua un candidato (vector de pesos) en una bateria de batallas.

    Para cada (escenario, batalla) corre dos enfrentamientos (ida y vuelta con
    equipos invertidos) y los puntua. Devuelve la media mas la penalizacion
    por diversidad.

    Args:
        args (tuple): Tupla (weights, scenarios, battles_per_opp, max_turns,
            elites, diversity_pressure, generation_seed).

    Returns:
        float: Fitness del candidato. -inf si no se pudo evaluar nada.
    """
    weights, scenarios, battles_per_opp, max_turns, elites, diversity_pressure, generation_seed = args
    scores = []
    for scenario_id, p1_states, p2_states, opp_class_name in scenarios:
        opp_class, opp_weight = OPPONENT_MAP[opp_class_name]
        for battle_idx in range(battles_per_opp):
            battle_seed = generation_seed * 100000 + scenario_id * 1000 + battle_idx * 2

            random.seed(battle_seed)
            ag1 = Level5Agent(player_id=1)
            ag1.weights = dict(weights)
            ag2 = opp_class(player_id=2)
            w, turns, fp1, fp2 = _run_headless_battle([Pokemon.from_state(s) for s in p1_states], [Pokemon.from_state(s) for s in p2_states], ag1, ag2, max_turns)
            scores.append(_score_battle(w, turns, fp1, fp2, 1, max_turns, opp_weight))

            random.seed(battle_seed + 1)
            ag3 = opp_class(player_id=1)
            ag4 = Level5Agent(player_id=2)
            ag4.weights = dict(weights)
            w2, t2, fp1m, fp2m = _run_headless_battle([Pokemon.from_state(s) for s in p1_states], [Pokemon.from_state(s) for s in p2_states], ag3, ag4, max_turns)
            scores.append(_score_battle(w2, t2, fp1m, fp2m, 2, max_turns, opp_weight))

    base = mean(scores) if scores else float('-inf')
    return base + _diversity_penalty(weights, elites, diversity_pressure)

def _build_scenarios(loader, team_size: int, n_per_opponent: int) -> List:
    """Genera escenarios de batalla con equipos aleatorios contra cada oponente.

    Args:
        loader: Cargador con el pool de Pokemon y la factory de equipos.
        team_size (int): Tamanio de cada equipo generado.
        n_per_opponent (int): Escenarios por cada oponente de OPPONENT_MAP.

    Returns:
        list: Lista de tuplas (scenario_id, p1_states, p2_states, opp_name).
    """
    scenarios = []
    scenario_id = 0
    for opp_name in OPPONENT_MAP:
        for _ in range(n_per_opponent):
            p1 = [p.to_state() for p in loader.generate_random_team(team_size)]
            p2 = [p.to_state() for p in loader.generate_random_team(team_size)]
            scenarios.append((scenario_id, p1, p2, opp_name))
            scenario_id += 1
    return scenarios

def _build_level4_holdout(loader, team_size: int, n_scenarios: int) -> List:
    """Genera un set de validacion fijo contra Level4Agent.

    Args:
        loader: Cargador con el pool de Pokemon.
        team_size (int): Tamanio de cada equipo.
        n_scenarios (int): Cantidad de escenarios a generar.

    Returns:
        list: Lista de tuplas (scenario_id, p1_states, p2_states, 'Level4Agent').
    """
    scenarios = []
    for i in range(n_scenarios):
        scenarios.append((i, [p.to_state() for p in loader.generate_random_team(team_size)],
                          [p.to_state() for p in loader.generate_random_team(team_size)], 'Level4Agent'))
    return scenarios

def _evaluate_population(population: List[Dict], scenarios: List, battles_per_opp: int, n_cores: int, max_turns: int, elites: List[Dict], diversity_pressure: float, generation_seed: int) -> List[float]:
    """Evalua toda la poblacion en paralelo sobre los mismos escenarios.

    Args:
        population (List[Dict]): Candidatos a evaluar.
        scenarios (List): Escenarios compartidos.
        battles_per_opp (int): Batallas por escenario.
        n_cores (int): Workers de multiprocessing. Si <=1, evalua secuencial.
        max_turns (int): Tope de turnos por batalla.
        elites (List[Dict]): Elites para la penalizacion por diversidad.
        diversity_pressure (float): Peso de la penalizacion.
        generation_seed (int): Semilla base de la generacion.

    Returns:
        List[float]: Fitness de cada candidato, en el mismo orden que `population`.
    """
    args_list = [(candidate, scenarios, battles_per_opp, max_turns, elites, diversity_pressure, generation_seed) for candidate in population]
    if n_cores and n_cores > 1:
        with Pool(processes=n_cores, initializer=_init_worker) as pool:
            return pool.map(_eval_candidate_on_scenarios, args_list)
    return [_eval_candidate_on_scenarios(a) for a in args_list]

def _holdout_level4_score(weights: Dict, holdout_scenarios: List, battles_per_opp: int, max_turns: int, generation_seed: int) -> float:
    """Evalua un candidato exclusivamente contra L4 en el set reservado.

    Args:
        weights (Dict): Vector de pesos a evaluar.
        holdout_scenarios (list): Escenarios de validacion.
        battles_per_opp (int): Batallas por escenario.
        max_turns (int): Tope de turnos.
        generation_seed (int): Semilla para anclar el PRNG.

    Returns:
        float: Fitness promedio del candidato en el holdout.
    """
    return _eval_candidate_on_scenarios((weights, holdout_scenarios, battles_per_opp, max_turns, [], 0.0, generation_seed))

def _save_weights(path: str, weights: Dict, metadata: Optional[Dict] = None) -> None:
    """Persiste un vector de pesos en un JSON, con metadatos opcionales.

    Args:
        path (str): Ruta del archivo destino. El directorio se crea si no existe.
        weights (Dict): Pesos a guardar bajo la clave 'weights'.
        metadata (Optional[Dict]): Info extra (generacion, holdout, etc).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {'weights': weights}
    if metadata: payload['metadata'] = metadata
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=True)

def run_genetic_algorithm(config: Optional[GeneticConfig] = None) -> Dict[str, float]:
    """Ejecuta el ciclo evolutivo completo y devuelve el mejor vector de pesos.

    Args:
        config (Optional[GeneticConfig]): Configuracion del AG. Si es None, usa los defaults.

    Returns:
        Dict[str, float]: Mejores pesos encontrados, con las 5 claves de DEFAULT_BOUNDS.
    """
    config = config or GeneticConfig()
    logger = _setup_logger(config.log_path)
    random.seed(config.seed)
    n_cores = config.n_cores if config.n_cores is not None else max(1, cpu_count() - 1)
    
    logger.info('GA start | cores=%s | pop=%s | max_gen=%s', n_cores, config.population_size, config.max_generations)
    loader = DataLoader(DEFAULT_POKEMON_PATH, DEFAULT_MOVES_PATH)
    population = [_random_weights() for _ in range(config.population_size)]

    best_weights = dict(population[0])
    best_fitness, best_holdout = float('-inf'), float('-inf')
    stagnation = 0
    current_mutation_rate = config.mutation_rate
    current_mutation_strength = config.mutation_strength
    elites: List[Dict] = []
    
    total_start = time.time()

    for generation in range(config.max_generations):
        gen_start = time.time()
        generation_seed = config.seed * 10000 + generation
        scenarios = _build_scenarios(loader, config.team_size, config.scenarios_per_opponent)
        holdout_level4 = _build_level4_holdout(loader, config.team_size, config.holdout_scenarios_level4)

        fitnesses_p1 = _evaluate_population(population, scenarios, config.battles_phase1, n_cores, config.max_turns, elites, config.diversity_pressure, generation_seed)

        n_top = max(1, int(len(population) * config.top_fraction))
        ranked_idx = sorted(range(len(population)), key=lambda i: fitnesses_p1[i], reverse=True)
        
        fitnesses_final = list(fitnesses_p1)
        top_population = [population[i] for i in ranked_idx[:n_top]]
        top_fitnesses = _evaluate_population(top_population, scenarios, config.battles_phase2, n_cores, config.max_turns, elites, config.diversity_pressure, generation_seed + 50000)
        
        for rank, orig_i in enumerate(ranked_idx[:n_top]):
            fitnesses_final[orig_i] = top_fitnesses[rank]

        ranked_final = sorted(zip(population, fitnesses_final), key=lambda x: x[1], reverse=True)
        current_best_w, current_best_f = ranked_final[0]

        current_holdout = _holdout_level4_score(current_best_w, holdout_level4, config.holdout_battles, config.max_turns, generation_seed + 90000)

        improved = (current_holdout > best_holdout + config.min_improvement) or \
                   (current_best_f > best_fitness + config.min_improvement and current_holdout >= best_holdout - 0.01)

        if improved:
            best_fitness, best_holdout, best_weights = current_best_f, current_holdout, dict(current_best_w)
            stagnation, current_mutation_rate, current_mutation_strength = 0, config.mutation_rate, config.mutation_strength
        else:
            stagnation += 1
            if stagnation >= max(2, config.patience // 2):
                current_mutation_rate = min(0.60, current_mutation_rate * 1.25)
                current_mutation_strength = min(0.50, current_mutation_strength * 1.20)

        elites = [dict(w) for w, _ in ranked_final[:config.elite_size]]
        _save_weights(config.output_path, best_weights, metadata={'generation': generation, 'best_holdout': best_holdout})

        logger.info('Gen %s | best=%.4f | holdoutL4=%.4f | stagnation=%s | %.1fs', generation, current_best_f, current_holdout, stagnation, time.time() - gen_start)

        if stagnation >= config.patience:
            logger.info('Early stop | stagnation=%s', stagnation)
            break

        next_pop = list(elites)
        all_w, all_f = [w for w, _ in ranked_final], [f for _, f in ranked_final]

        while len(next_pop) < config.population_size:
            parent_a = _tournament_select(all_w, all_f, config.tournament_size)
            parent_b = _tournament_select(all_w, all_f, config.tournament_size)
            child = _mutate(_crossover(parent_a, parent_b), current_mutation_rate, current_mutation_strength)
            next_pop.append(child)
            
        population = next_pop

    logger.info('GA finished | best_holdout_level4=%.4f', best_holdout)
    return best_weights

if __name__ == '__main__':
    run_genetic_algorithm()