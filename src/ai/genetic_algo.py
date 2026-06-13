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
    """Pre-carga el singleton de DataLoader en cada worker spawn de Windows."""
    get_data_loader(DEFAULT_POKEMON_PATH, DEFAULT_MOVES_PATH)


@dataclass
class GeneticConfig:
    # población y generaciones para permitir una evolución real
    population_size: int = 40
    elite_size: int = 4
    mutation_rate: float = 0.15
    mutation_strength: float = 0.20
    tournament_size: int = 5
    max_generations: int = 50
    patience: int = 15
    min_improvement: float = 0.005
    # las batallas para reducir el factor suerte (RNG)
    battles_phase1: int = 4
    battles_phase2: int = 8
    top_fraction: float = 0.35
    team_size: int = 3
    scenarios_per_opponent: int = 4
    holdout_scenarios_level4: int = 8
    holdout_battles: int = 4
    max_turns: int = 120
    seed: int = 42
    n_cores: Optional[int] = None # Usa todos los núcleos disponibles para no demorar tanto tiempo
    diversity_pressure: float = 0.05
    log_path: str = DEFAULT_LOG_PATH
    output_path: str = DEFAULT_OUTPUT_PATH

# El entrenamiento se centra en la IA4 (peso masivo)
OPPONENT_MAP = {
    'Level3Agent': (Level3Agent, 1.00),
    'Level4Agent': (Level4Agent, 15.00),
}

DEFAULT_BOUNDS: Dict[str, Tuple[float, float]] = {
    'hp_balance': (0.0, 5.0),
    'alive_balance': (0.0, 5.0),
    'type_pressure': (0.0, 8.0),   # Permite castigar fuertemente inmunidades/resistencias
    'speed_pressure': (0.0, 3.0),
    'status_pressure': (0.0, 3.0),
    'move_pressure': (0.0, 5.0),
    'switch_pressure': (0.0, 4.0),
    'ko_pressure': (0.0, 10.0),    # Permite priorizar KOs absolutos
}

def _setup_logger(log_path: str) -> logging.Logger:
    """
    Configure un objeto de registro de eventos (logger) para escribir registros en un archivo y la consola.

    Args:
        log_path (str): La ruta del archivo de registro.

    Returns:
        logging.Logger: Un objeto Logger configurado con un formato de registro determinado.

    Raises:
        OSError: Si no se puede crear el directorio del archivo de registro.
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
    return max(lo, min(hi, v))

def _random_weights() -> Dict[str, float]:
    return {k: round(random.uniform(lo, hi), 4) for k, (lo, hi) in DEFAULT_BOUNDS.items()}

def _tournament_select(population: List[Dict], fitnesses: List[float], size: int) -> Dict:
    idx = random.sample(range(len(population)), k=min(size, len(population)))
    best = max(idx, key=lambda i: fitnesses[i])
    return dict(population[best])

def _crossover(a: Dict, b: Dict) -> Dict:
    """
    Descripción breve:
     Combina dos diccionarios para generar un nuevo diccionario hijo mediante un proceso de cruza.

    Args:
        a (Dict): El primer diccionario padre.
        b (Dict): El segundo diccionario padre.

    Returns:
        Dict: Un nuevo diccionario hijo generado mediante la combinación de los padres.

    Raises:
        KeyError: Si los diccionarios a y b no tienen las mismas claves que las definidas en DEFAULT_BOUNDS.
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
    """
    Aplica una mutación aleatoria a un candidato según una tasa y fuerza de mutación determinadas.

    Args:
        candidate (Dict): El candidato a mutar.
        mutation_rate (float): La probabilidad de mutación para cada parámetro.
        mutation_strength (float): La fuerza de la mutación, quecontrola el rango de variación aleatoria.

    Returns:
        Dict: El candidato mutado.

    Raises:
        No se contempla explícitamenteexceptions, aunque la función puede fallar si el tipo o contenido de `candidate` no coincide con los esperados por `DEFAULT_BOUNDS`.
    """
    out = dict(candidate)
    for k, (lo, hi) in DEFAULT_BOUNDS.items():
        if random.random() <= mutation_rate:
            span = hi - lo
            out[k] = round(_clamp(out[k] + random.gauss(0.0, mutation_strength * span), lo, hi), 4)
    return out

def _diversity_penalty(candidate: Dict, elites: List[Dict], pressure: float) -> float:
    """
    Descripción breve:
    Calcula la penalización por diversidad para un candidato en función de su cercanía a los elitros.

    Args:
        candidate (Dict): Candidato a evaluar.
        elites (List[Dict]): Lista de elitros.
        pressure (float): Presión de selección.

    Returns:
        float: Valor de la penalización por diversidad.

    Raises:
        No se lanzan excepciones.
    """
    if not elites or pressure <= 0.0: return 0.0
    keys = list(DEFAULT_BOUNDS.keys())
    min_dist = min(sum((candidate[k] - e[k]) ** 2 for k in keys) ** 0.5 for e in elites)
    max_dist = sum((hi - lo) ** 2 for lo, hi in DEFAULT_BOUNDS.values()) ** 0.5
    normalized = min_dist / max(max_dist, 1e-9)
    return -pressure * max(0.0, 0.25 - normalized)

def _run_headless_battle(p1_team, p2_team, agent1, agent2, max_turns: int = 120):
    """
    Descripción breve:
     Ejecuta una batalla entre dos equipos de forma headless utilizando dos agentes que toman decisiones.

    Args:
        p1_team (list): Equipo del jugador 1.
        p2_team (list): Equipo del jugador 2.
        agent1: Agente que toma decisiones para el equipo del jugador 1.
        agent2: Agente que toma decisiones para el equipo del jugador 2.
        max_turns (int): Número máximo de turnos que puede durar la batalla. Por defecto es 120.

    Returns:
        tuple: Una tupla que contiene el ganador de la batalla, el número de turnos jugados y los equipos finales de ambos jugadores.

    Raises:
        No se especifican excepciones explícitas en esta función, pero puede lanzar excepciones si los agentes o los equipos no están correctamente configurados.
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
    cur = sum(max(0, p.current_hp) for p in team)
    mx = sum(max(1, p.max_hp) for p in team)
    return cur / mx

def _alive_ratio(team) -> float:
    return sum(1 for p in team if p.current_hp > 0) / max(1, len(team))

def _score_battle(winner, turns, p1_team, p2_team, perspective: int, max_turns: int, opp_weight: float = 1.0) -> float:
    """
    Descripción breve:
      Calcula la puntuación de una batalla de manera relativa, considerando el resultado, el estado de salud de los equipos y la velocidad de victoria.

    Args:
      winner (int): Identificador del ganador de la batalla (None si es empate).
      turns (int): Número de turnos que duró la batalla.
      p1_team (object): Equipo del jugador 1.
      p2_team (object): Equipo del jugador 2.
      perspective (int): Perspectiva desde la que se evalúa la batalla (1 o 2).
      max_turns (int): Número máximo de turnos permitidos en la batalla.
      opp_weight (float, opcional): Peso de la importancia del oponente. Por defecto es 1.0.

    Returns:
      float: Puntuación de la batalla, calculada en base a factores como resultado, salud de los equipos y velocidad de victoria.

    Raises:
      No se especifican excepciones explícitas, pero puede lanzar errores en caso de que los parámetros no cumplan con los tipos y rangos esperados.
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
    """
    Descripción breve:
    Evalúa un candidato (conjunto de pesos) en diferentes escenarios de batalla y devuelve una puntuación que refleja su desempeño.

    Args:
        args (tuple): Tupla que contiene los siguientes parámetros:
            - weights (dict): Conjunto de pesos para el agente.
            - scenarios (list): Lista de escenarios de batalla. Cada elemento es (scenario_id, p1_states, p2_states, opp_class_name).
            - battles_per_opp (int): Número de batallas por oponente.
            - max_turns (int): Máximo número de turnos por batalla.
            - elites (list): Lista de pesos elitistas.
            - diversity_pressure (float): Presión de diversidad.
            - generation_seed (int): Semilla base de la generación para anclar el PRNG.

    Returns:
        float: Puntuación que refleja el desempeño del candidato en los escenarios de batalla, calculada como la media de las puntuaciones obtenidas en cada batalla, ajustada con una penalización por diversidad.
    """
    weights, scenarios, battles_per_opp, max_turns, elites, diversity_pressure, generation_seed = args
    scores = []
    for scenario_id, p1_states, p2_states, opp_class_name in scenarios:
        opp_class, opp_weight = OPPONENT_MAP[opp_class_name]
        for battle_idx in range(battles_per_opp):
            # Anclaje determinista del PRNG: misma seed para todos los candidatos
            # en esta combinación (generación, escenario, batalla). Elimina ruido
            # estocástico espurio en la comparación de fitness.
            battle_seed = generation_seed * 100000 + scenario_id * 1000 + battle_idx * 2

            # Batalla de Ida
            random.seed(battle_seed)
            ag1 = Level5Agent(player_id=1)
            ag1.weights = dict(weights)
            ag2 = opp_class(player_id=2)
            w, turns, fp1, fp2 = _run_headless_battle([Pokemon.from_state(s) for s in p1_states], [Pokemon.from_state(s) for s in p2_states], ag1, ag2, max_turns)
            scores.append(_score_battle(w, turns, fp1, fp2, 1, max_turns, opp_weight))

            # Batalla de Vuelta (Invertimos equipos)
            random.seed(battle_seed + 1)
            ag3 = opp_class(player_id=1)
            ag4 = Level5Agent(player_id=2)
            ag4.weights = dict(weights)
            w2, t2, fp1m, fp2m = _run_headless_battle([Pokemon.from_state(s) for s in p1_states], [Pokemon.from_state(s) for s in p2_states], ag3, ag4, max_turns)
            scores.append(_score_battle(w2, t2, fp1m, fp2m, 2, max_turns, opp_weight))

    base = mean(scores) if scores else float('-inf')
    return base + _diversity_penalty(weights, elites, diversity_pressure)

def _build_scenarios(loader, team_size: int, n_per_opponent: int) -> List:
    """
    Crea escenarios para partidas contra oponentes generando equipos aleatorios.
    Cada escenario incluye un scenario_id estable para anclar el PRNG.

    Args:
        loader: objeto que carga y proporciona recursos para la generación de equipos
        team_size (int): tamaño de cada equipo
        n_per_opponent (int): número de escenarios por oponente

    Returns:
        List[Tuple[int, list, list, str]]: lista de (scenario_id, p1_states, p2_states, opp_name)
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
    scenarios = []
    for i in range(n_scenarios):
        scenarios.append((i, [p.to_state() for p in loader.generate_random_team(team_size)],
                          [p.to_state() for p in loader.generate_random_team(team_size)], 'Level4Agent'))
    return scenarios

def _evaluate_population(population: List[Dict], scenarios: List, battles_per_opp: int, n_cores: int, max_turns: int, elites: List[Dict], diversity_pressure: float, generation_seed: int) -> List[float]:
    """
    Evalúa la población en paralelo con anclaje de PRNG por (generación, escenario).

    Args:
        population (List[Dict]): Población de candidatos a evaluar.
        scenarios (List): Escenarios en los que se evaluarán los candidatos.
        battles_per_opp (int): Número de batallas por oponente.
        n_cores (int): Número de núcleos a utilizar para la evaluación.
        max_turns (int): Número máximo de turnos por batalla.
        elites (List[Dict]): Candidatos de élite.
        diversity_pressure (float): Presión de diversidad.
        generation_seed (int): Semilla base de la generación para anclar el PRNG.

    Returns:
        List[float]: Puntuaciones de la población evaluada.
    """
    args_list = [(candidate, scenarios, battles_per_opp, max_turns, elites, diversity_pressure, generation_seed) for candidate in population]
    if n_cores and n_cores > 1:
        with Pool(processes=n_cores, initializer=_init_worker) as pool:
            return pool.map(_eval_candidate_on_scenarios, args_list)
    return [_eval_candidate_on_scenarios(a) for a in args_list]

def _holdout_level4_score(weights: Dict, holdout_scenarios: List, battles_per_opp: int, max_turns: int, generation_seed: int) -> float:
    return _eval_candidate_on_scenarios((weights, holdout_scenarios, battles_per_opp, max_turns, [], 0.0, generation_seed))

def _save_weights(path: str, weights: Dict, metadata: Optional[Dict] = None) -> None:
    """
    Salvar pesos en un archivo JSON.

    Args:
        path (str): Ruta del archivo donde se guardarán los pesos.
        weights (Dict): Diccionario que contiene los pesos a guardar.
        metadata (Optional[Dict], optional): Metadatos asociados a los pesos. Defaults to None.

    Returns:
        None

    Raises:
        Exception: Si ocurre un error al crear el directorio o al escribir en el archivo.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {'weights': weights}
    if metadata: payload['metadata'] = metadata
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=True)

def run_genetic_algorithm(config: Optional[GeneticConfig] = None) -> Dict[str, float]:
    """
    Ejecuta un algoritmo genético para encontrar los mejores pesos para un modelo.

    Args:
        config (Optional[GeneticConfig], opcional): La configuración del algoritmo genético. Si no se proporciona, se utiliza un objeto GeneticConfig por defecto.

    Returns:
        Dict[str, float]: Un diccionario con los mejores pesos encontrados.

    Raises:
        Exception: Cualquier error que ocurra durante la ejecución del algoritmo genético.
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
        # Semilla derivada por generación: anclaje del PRNG en fase 1, fase 2 y
        # holdout. Distintos offsets garantizan que la re-evaluación no sea trivial.
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