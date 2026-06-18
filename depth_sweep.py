"""
depth_sweep.py
==============
Mide el impacto de la profundidad de busqueda (depth) de Level3Agent y
Level4Agent contra Level2Agent (Greedy) en formatos 3v3 y 4v4.

Evalua como la profundidad del arbol Minimax afecta:
    - Win rate del agente variable contra L2
    - Turnos promedio por batalla
    - Tiempo de ejecucion por batalla

IMPORTANTE: Este script parchea AI_LEVEL3_DEPTH / AI_LEVEL4_DEPTH en cada
worker antes de instanciar el agente, porque los agentes capturan esos
valores al momento de importacion.

Uso:
    python depth_sweep.py
    python depth_sweep.py --n 200 --size both
    python depth_sweep.py --n 100 --size 3
    python depth_sweep.py --l3-depths 2 3 --l4-depths 2 3

Genera tablas LaTeX listas para incluir en la tesis.
"""

import argparse
import os
import sys
import time
from multiprocessing import Pool, cpu_count
from statistics import mean
from typing import Tuple

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import config  # noqa: E402
from src.utils.move_registry import get_data_loader  # noqa: E402

POKEMON_PATH = os.path.join(ROOT_DIR, 'data', 'pokemon_pool.json')
MOVES_PATH = os.path.join(ROOT_DIR, 'data', 'moves_pool.json')
MAX_TURNS = 120


def _init_worker() -> None:
    """Pre-carga el singleton de DataLoader en cada worker."""
    get_data_loader(POKEMON_PATH, MOVES_PATH)


def _run_battle(args) -> Tuple[int, int, float]:
    """Ejecuta una batalla y retorna (winner, turns, elapsed_seconds).

    Parchea AI_LEVEL3_DEPTH o AI_LEVEL4_DEPTH (y DEPTH en L4) antes de
    instanciar el agente para variar la profundidad del arbol.

    winner: 1 = A (variable) gano, 2 = B (L2) gano, 0 = empate.
    """
    seed, depth, agent_name, a_is_p1, team_size = args

    import random
    random.seed(seed)

    # Re-importar los modulos en este worker para poder parchearlos.
    # En multiprocessing cada worker tiene su propio namespace.
    import config as cfg
    import src.ai.level3_agent as l3_mod
    import src.ai.level4_agent as l4_mod

    if agent_name == 'L3':
        cfg.AI_LEVEL3_DEPTH = depth
        l3_mod.AI_LEVEL3_DEPTH = depth
    else:
        cfg.AI_LEVEL4_DEPTH = depth
        l4_mod.AI_LEVEL4_DEPTH = depth
        l4_mod.DEPTH = depth  # L4 captura DEPTH al importar

    from src.ai.level2_agent import Level2Agent
    from src.ai.level3_agent import Level3Agent
    from src.ai.level4_agent import Level4Agent
    from src.core.battle_engine import process_turn
    from src.core.interfaces import BattleState

    loader = get_data_loader(POKEMON_PATH, MOVES_PATH)
    p1_team = loader.generate_random_team(team_size)
    p2_team = loader.generate_random_team(team_size)

    if a_is_p1:
        if agent_name == 'L3':
            agent_p1 = Level3Agent(player_id=1)
        else:
            agent_p1 = Level4Agent(player_id=1)
        agent_p2 = Level2Agent(player_id=2)
    else:
        agent_p1 = Level2Agent(player_id=1)
        if agent_name == 'L3':
            agent_p2 = Level3Agent(player_id=2)
        else:
            agent_p2 = Level4Agent(player_id=2)

    p1_idx = p2_idx = 0
    winner_raw = None
    turns_played = 0

    t0 = time.time()
    for turn in range(1, MAX_TURNS + 1):
        turns_played = turn
        state = BattleState(
            p1_team=[p.to_state() for p in p1_team],
            p2_team=[p.to_state() for p in p2_team],
            p1_active_index=p1_idx,
            p2_active_index=p2_idx,
            turn_number=turn,
        )
        a1 = agent_p1.get_action(state)
        a2 = agent_p2.get_action(state)
        result, p1_idx, p2_idx = process_turn(
            p1_team, p1_idx, a1, p2_team, p2_idx, a2
        )
        winner_raw = result.winner
        if result.match_over:
            break
    elapsed = time.time() - t0

    if winner_raw is None:
        winner = 0
    elif a_is_p1 and winner_raw == 1:
        winner = 1
    elif not a_is_p1 and winner_raw == 2:
        winner = 1
    else:
        winner = 2

    return winner, turns_played, elapsed


def run_sweep(agent_name, depths, team_size, n_battles, n_cores):
    """Ejecuta el barrido de profundidades para un agente y retorna metricas.

    Returns:
        list: Lista de dicts con metricas por profundidad.
    """
    results = []

    print()
    print('=' * 80)
    print(f"  Barrido de profundidad para {agent_name} vs L2 (Greedy) "
          f"-- {team_size}v{team_size}, {n_battles} batallas")
    print('=' * 80)
    print(f"  {'Depth':<6} | {'WR Agente':>10} | {'WR L2':>8} | {'Emp.':>5} | "
          f"{'Turnos':>7} | {'Total':>9} | {'ms/batalla':>10}")
    print('  ' + '-' * 75)

    for depth in depths:
        args_list = [
            (i, depth, agent_name, i % 2 == 0, team_size)
            for i in range(n_battles)
        ]

        t0 = time.time()
        if n_cores > 1:
            with Pool(processes=n_cores, initializer=_init_worker) as pool:
                battle_results = pool.map(_run_battle, args_list)
        else:
            _init_worker()
            battle_results = [_run_battle(a) for a in args_list]
        total_elapsed = time.time() - t0

        wins_a = sum(1 for r in battle_results if r[0] == 1)
        wins_b = sum(1 for r in battle_results if r[0] == 2)
        draws = sum(1 for r in battle_results if r[0] == 0)
        wr_a = wins_a / n_battles * 100
        wr_b = wins_b / n_battles * 100
        avg_turns = mean(r[1] for r in battle_results)
        per_battle_ms = (total_elapsed / n_battles) * 1000

        results.append({
            'agent': agent_name,
            'depth': depth,
            'wr_a': wr_a,
            'wr_b': wr_b,
            'draws': draws,
            'avg_turns': avg_turns,
            'per_battle_ms': per_battle_ms,
            'total_time': total_elapsed,
        })

        print(f"  {depth:<6} | {wr_a:>9.1f}% | {wr_b:>7.1f}% | {draws:>5} | "
              f"{avg_turns:>7.1f} | {total_elapsed:>8.1f}s | {per_battle_ms:>9.1f}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Barrido de profundidad L3/L4 vs L2 (Greedy)'
    )
    parser.add_argument('--n', type=int, default=200,
                        help='Batallas por par (default: 200)')
    parser.add_argument('--cores', type=int, default=None,
                        help='Nucleos a usar (default: cpu_count-1)')
    parser.add_argument('--size', choices=['3', '4', 'both'], default='both',
                        help='Tamano de equipo: 3, 4, o both (default: both)')
    parser.add_argument('--l3-depths', type=int, nargs='+', default=[1, 2, 3],
                        help='Profundidades a evaluar para L3 (default: 1 2 3)')
    parser.add_argument('--l4-depths', type=int, nargs='+', default=[1, 2, 3, 4],
                        help='Profundidades a evaluar para L4 (default: 1 2 3 4)')
    args = parser.parse_args()

    n_cores = args.cores if args.cores is not None else max(1, cpu_count() - 1)
    sizes = [3, 4] if args.size == 'both' else [int(args.size)]

    if any(d < 1 for d in args.l3_depths + args.l4_depths):
        parser.error('Todas las profundidades deben ser >= 1')

    for team_size in sizes:
        results_l3 = run_sweep('L3', args.l3_depths, team_size, args.n, n_cores)
        results_l4 = run_sweep('L4', args.l4_depths, team_size, args.n, n_cores)
        print()


if __name__ == '__main__':
    main()
