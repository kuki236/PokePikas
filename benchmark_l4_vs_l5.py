"""
benchmark_l4_vs_l5.py
=====================
Enfrenta directamente a Level4Agent (IA4) vs Level5Agent (IA5)
con mayor muestra estadística para reducir el ruido.

Uso:
    python benchmark_l4_vs_l5.py              # 500 batallas por defecto
    python benchmark_l4_vs_l5.py --n 1000     # 1000 batallas
    python benchmark_l4_vs_l5.py --n 200      # 200 batallas (rápido)
"""

import argparse
import os
import time
from multiprocessing import Pool, cpu_count
from statistics import mean
from typing import Tuple

from src.ai.level4_agent import Level4Agent
from src.ai.level5_agent import Level5Agent
from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState
from src.utils.move_registry import get_data_loader

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
POKEMON_PATH = os.path.join(ROOT_DIR, 'data', 'pokemon_pool.json')
MOVES_PATH   = os.path.join(ROOT_DIR, 'data', 'moves_pool.json')
TEAM_SIZE    = 4
MAX_TURNS    = 120


def _init_worker() -> None:
    """Pre-carga el singleton de DataLoader en cada worker."""
    get_data_loader(POKEMON_PATH, MOVES_PATH)


def _run_battle(args) -> Tuple[int, int, float, float]:
    """
    Retorna (winner, turns, hp_ratio_ia5, alive_ratio_ia5).
    winner: 1 = IA5 ganó, 2 = IA4 ganó, 0 = empate.
    La perspectiva alterna cada batalla para eliminar el sesgo de quién va primero.
    """
    seed, ia5_is_p1 = args

    import random
    random.seed(seed)

    loader = get_data_loader(POKEMON_PATH, MOVES_PATH)
    p1_team = loader.generate_random_team(TEAM_SIZE)
    p2_team = loader.generate_random_team(TEAM_SIZE)

    if ia5_is_p1:
        agent_ia5 = Level5Agent(player_id=1)
        agent_ia4 = Level4Agent(player_id=2)
    else:
        agent_ia4 = Level4Agent(player_id=1)
        agent_ia5 = Level5Agent(player_id=2)

    p1_idx = p2_idx = 0
    winner_raw = None
    turns_played = 0

    for turn in range(1, MAX_TURNS + 1):
        turns_played = turn
        state = BattleState(
            p1_team=[p.to_state() for p in p1_team],
            p2_team=[p.to_state() for p in p2_team],
            p1_active_index=p1_idx,
            p2_active_index=p2_idx,
            turn_number=turn,
        )
        if ia5_is_p1:
            a1 = agent_ia5.get_action(state)
            a2 = agent_ia4.get_action(state)
        else:
            a1 = agent_ia4.get_action(state)
            a2 = agent_ia5.get_action(state)

        result, p1_idx, p2_idx = process_turn(p1_team, p1_idx, a1, p2_team, p2_idx, a2)
        winner_raw = result.winner
        if result.match_over:
            break

    # HP e IA5 vivos al final
    if ia5_is_p1:
        ia5_team = p1_team
    else:
        ia5_team = p2_team

    hp_ratio = sum(max(0, p.current_hp) for p in ia5_team) / max(1, sum(p.max_hp for p in ia5_team))
    alive    = sum(1 for p in ia5_team if p.current_hp > 0) / TEAM_SIZE

    # Normalizar ganador a perspectiva IA5
    if winner_raw is None:
        winner = 0
    elif ia5_is_p1 and winner_raw == 1:
        winner = 1
    elif not ia5_is_p1 and winner_raw == 2:
        winner = 1
    else:
        winner = 2

    return winner, turns_played, hp_ratio, alive


def run_benchmark(n_battles: int = 500, n_cores: int = None) -> None:
    """
    Ejecuta un benchmark entre Level4Agent y Level5Agent a lo largo de múltiples
    batallas simuladas, opcionalmente en paralelo.

    Alterna qué agente actúa como jugador 1 en cada batalla para reducir el sesgo
    asociado al orden de turno. Al finalizar, calcula e imprime en consola
    estadísticas agregadas, incluyendo victorias, empates, win rate de IA5,
    intervalo de confianza del 95%, HP restante promedio, Pokémon vivos promedio
    y duración media de las partidas.

    Args:
        n_battles: Cantidad total de batallas a simular.
        n_cores: Número de procesos a usar. Si es None, usa cpu_count() - 1
            con un mínimo de 1.

    Returns:
        None.

    Raises:
        Puede propagar excepciones relacionadas con multiprocessing, carga de datos
        o errores internos durante la simulación de batallas.
    """
    if n_cores is None:
        n_cores = max(1, cpu_count() - 1)

    print('=' * 80)
    print(f'  BENCHMARK DIRECTO: IA4 (Level4Agent) vs IA5 (Level5Agent)')
    print(f'  Batallas: {n_battles}  |  Núcleos: {n_cores}  |  Equipo: {TEAM_SIZE}v{TEAM_SIZE}')
    print('=' * 80)

    # Alternar qué agente va de P1 para eliminar sesgo de turno
    args_list = [(i, i % 2 == 0) for i in range(n_battles)]

    t0 = time.time()
    if n_cores > 1:
        with Pool(processes=n_cores, initializer=_init_worker) as pool:
            results = pool.map(_run_battle, args_list)
    else:
        _init_worker()
        results = [_run_battle(a) for a in args_list]
    elapsed = time.time() - t0

    wins_ia5    = sum(1 for r in results if r[0] == 1)
    wins_ia4    = sum(1 for r in results if r[0] == 2)
    draws       = sum(1 for r in results if r[0] == 0)
    valid       = n_battles - draws

    wr_ia5 = wins_ia5 / n_battles * 100
    wr_ia4 = wins_ia4 / n_battles * 100
    wr_ia5_nodraw = wins_ia5 / max(1, valid) * 100

    turns_list = [r[1] for r in results]
    hp_list    = [r[2] for r in results]
    alive_list = [r[3] for r in results]

    avg_turns = mean(turns_list)
    avg_hp    = mean(hp_list) * 100
    avg_alive = mean(alive_list) * 100
    std_wr    = (wr_ia5 * (100 - wr_ia5) / n_battles) ** 0.5  # SE porcentual

    # Intervalo de confianza 95% (Wilson aproximado)
    import math
    z = 1.96
    p = wins_ia5 / n_battles
    lo = (p + z**2 / (2*n_battles) - z * math.sqrt(p*(1-p)/n_battles + z**2/(4*n_battles**2))) \
         / (1 + z**2/n_battles) * 100
    hi = (p + z**2 / (2*n_battles) + z * math.sqrt(p*(1-p)/n_battles + z**2/(4*n_battles**2))) \
         / (1 + z**2/n_battles) * 100

    # Desglose por perspectiva
    ia5_as_p1 = [r for r, a in zip(results, args_list) if a[1]]
    ia5_as_p2 = [r for r, a in zip(results, args_list) if not a[1]]
    wr_p1 = sum(1 for r in ia5_as_p1 if r[0] == 1) / max(1, len(ia5_as_p1)) * 100
    wr_p2 = sum(1 for r in ia5_as_p2 if r[0] == 1) / max(1, len(ia5_as_p2)) * 100

    print()
    print(f'  {'RESULTADO GLOBAL':<30}')
    print(f'  {"IA5 gana:":<30} {wins_ia5:>5} batallas  ({wr_ia5:.1f}%)')
    print(f'  {"IA4 gana:":<30} {wins_ia4:>5} batallas  ({wr_ia4:.1f}%)')
    print(f'  {"Empates:":<30} {draws:>5} batallas')
    print()
    print(f'  {"Win rate IA5 (sin empates):":<30} {wr_ia5_nodraw:.1f}%')
    print(f'  {"IC 95% win rate IA5:":<30} [{lo:.1f}%  –  {hi:.1f}%]')
    print()
    print(f'  DESGLOSE POR PERSPECTIVA')
    print(f'  {"IA5 como jugador 1:":<30} {wr_p1:.1f}%')
    print(f'  {"IA5 como jugador 2:":<30} {wr_p2:.1f}%')
    print()
    print(f'  ESTADÍSTICAS DE PARTIDA (perspectiva IA5 al finalizar)')
    print(f'  {"HP restante promedio:":<30} {avg_hp:.1f}%')
    print(f'  {"Pokémon vivos promedio:":<30} {avg_alive:.1f}%')
    print(f'  {"Turnos promedio:":<30} {avg_turns:.1f}')
    print()

    if lo > 50.0:
        verdict = '✅ IA5 supera estadísticamente a IA4'
    elif hi < 50.0:
        verdict = '❌ IA4 supera estadísticamente a IA5'
    else:
        verdict = '⚠️  Resultado estadísticamente incierto (empate técnico)'

    print(f'  VEREDICTO: {verdict}')
    print()
    print(f'  Tiempo total: {elapsed:.1f}s')
    print('=' * 80)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark IA4 vs IA5')
    parser.add_argument('--n', type=int, default=500, help='Número de batallas (default: 500)')
    parser.add_argument('--cores', type=int, default=None, help='Núcleos a usar (default: auto)')
    args = parser.parse_args()
    run_benchmark(n_battles=args.n, n_cores=args.cores)
