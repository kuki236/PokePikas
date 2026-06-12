"""
simulate_ai_5.py
================
Torneo de Level5Agent (IA optimizada por algoritmo genetico) contra los
demas niveles (L1-L4). Alterna perspectiva P1/P2 cada batalla, reporta
empates explicitamente, calcula IC 95% Wilson y paraleliza con Pool.

Uso:
    python simulate_ai_5.py                       # 200 batallas, 3v3 y 4v4
    python simulate_ai_5.py --n 500               # 500 batallas por par
    python simulate_ai_5.py --size 3              # solo 3v3
    python simulate_ai_5.py --size 4              # solo 4v4
    python simulate_ai_5.py --cores 4             # forzar 4 procesos
"""

import argparse
import math
import os
import time
from multiprocessing import Pool, cpu_count
from statistics import mean
from typing import List, Tuple

from src.ai.level1_agent import Level1Agent
from src.ai.level2_agent import Level2Agent
from src.ai.level3_agent import Level3Agent
from src.ai.level4_agent import Level4Agent
from src.ai.level5_agent import Level5Agent
from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState
from src.utils.move_registry import get_data_loader

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
POKEMON_PATH = os.path.join(ROOT_DIR, 'data', 'pokemon_pool.json')
MOVES_PATH = os.path.join(ROOT_DIR, 'data', 'moves_pool.json')
MAX_TURNS = 120

AGENT_REGISTRY = {
    "L1": (Level1Agent, "Azar"),
    "L2": (Level2Agent, "Greedy"),
    "L3": (Level3Agent, "Minimax"),
    "L4": (Level4Agent, "Avanzado"),
    "L5": (Level5Agent, "Evolutivo"),
}

MATCHUPS: List[Tuple[str, str]] = [
    ("L5", "L1"),
    ("L5", "L2"),
    ("L5", "L3"),
    ("L5", "L4"),
]


def _init_worker() -> None:
    """Pre-carga el singleton de DataLoader en cada worker."""
    get_data_loader(POKEMON_PATH, MOVES_PATH)


def _run_battle(args) -> Tuple[int, int, float, float]:
    """
    Ejecuta una batalla y retorna (winner_a, turns, hp_ratio_a, alive_ratio_a).

    winner: 1 = gano A, 2 = gano B, 0 = empate.
    a_is_p1 indica si A actua como P1 (alternancia para eliminar sesgo).
    """
    seed, agent_a_key, agent_b_key, a_is_p1, team_size = args

    import random
    random.seed(seed)

    loader = get_data_loader(POKEMON_PATH, MOVES_PATH)
    p1_team = loader.generate_random_team(team_size)
    p2_team = loader.generate_random_team(team_size)

    cls_a = AGENT_REGISTRY[agent_a_key][0]
    cls_b = AGENT_REGISTRY[agent_b_key][0]

    if a_is_p1:
        agent_p1 = cls_a(player_id=1)
        agent_p2 = cls_b(player_id=2)
    else:
        agent_p1 = cls_b(player_id=1)
        agent_p2 = cls_a(player_id=2)

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
        a1 = agent_p1.get_action(state)
        a2 = agent_p2.get_action(state)
        result, p1_idx, p2_idx = process_turn(p1_team, p1_idx, a1, p2_team, p2_idx, a2)
        winner_raw = result.winner
        if result.match_over:
            break

    team_a = p1_team if a_is_p1 else p2_team
    hp_ratio = sum(max(0, p.current_hp) for p in team_a) / max(1, sum(p.max_hp for p in team_a))
    alive_ratio = sum(1 for p in team_a if p.current_hp > 0) / team_size

    if winner_raw is None:
        winner = 0
    elif a_is_p1 and winner_raw == 1:
        winner = 1
    elif not a_is_p1 and winner_raw == 2:
        winner = 1
    else:
        winner = 2

    return winner, turns_played, hp_ratio, alive_ratio


def _wilson_interval(wins: int, n: int) -> Tuple[float, float]:
    """Intervalo de confianza 95% de Wilson para una proporcion."""
    if n == 0:
        return 0.0, 0.0
    z = 1.96
    p = wins / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (centre - half) * 100, (centre + half) * 100


def _run_pairing(
    agent_a_key: str,
    agent_b_key: str,
    n_battles: int,
    team_size: int,
    n_cores: int,
) -> dict:
    """Ejecuta n_battles entre A y B (alternando perspectiva) y retorna metricas."""
    args_list = [
        (i, agent_a_key, agent_b_key, i % 2 == 0, team_size)
        for i in range(n_battles)
    ]

    t0 = time.time()
    if n_cores > 1:
        with Pool(processes=n_cores, initializer=_init_worker) as pool:
            results = pool.map(_run_battle, args_list)
    else:
        _init_worker()
        results = [_run_battle(a) for a in args_list]
    elapsed = time.time() - t0

    wins_a = sum(1 for r in results if r[0] == 1)
    wins_b = sum(1 for r in results if r[0] == 2)
    draws = sum(1 for r in results if r[0] == 0)

    wr_a = wins_a / n_battles * 100
    wr_b = wins_b / n_battles * 100
    ic_lo, ic_hi = _wilson_interval(wins_a, n_battles)

    avg_turns = mean(r[1] for r in results)
    avg_hp = mean(r[2] for r in results) * 100
    avg_alive = mean(r[3] for r in results) * 100

    return {
        "wins_a": wins_a, "wins_b": wins_b, "draws": draws,
        "wr_a": wr_a, "wr_b": wr_b,
        "ic_lo": ic_lo, "ic_hi": ic_hi,
        "avg_turns": avg_turns,
        "avg_hp": avg_hp, "avg_alive": avg_alive,
        "elapsed": elapsed,
    }


def _verdict(ic_lo: float, ic_hi: float, label_a: str, label_b: str) -> str:
    if ic_lo > 50.0:
        return f'{label_a} > {label_b}'
    if ic_hi < 50.0:
        return f'{label_b} > {label_a}'
    return 'Empate tecnico'


def imprimir_torneo(team_size: int, n_battles: int, n_cores: int) -> None:
    """Ejecuta y reporta el torneo de L5 contra L1-L4 para un team_size dado."""
    width = 138
    print()
    print('=' * width)
    print(f"{f'TORNEO IA5 (Evolutivo) vs L1-L4 ({team_size}v{team_size})':^{width}}")
    sub = f'{n_battles} batallas por par  |  {n_cores} nucleos  |  perspectiva alternada P1/P2'
    print(f"{sub:^{width}}")
    print('=' * width)

    header = (
        f"{'EMPAREJAMIENTO':<32} | "
        f"{'WR L5':>6} | {'WR OPP':>6} | {'EMP':>4} | "
        f"{'IC 95% L5':>16} | {'HP L5':>6} | {'VIVOS':>6} | "
        f"{'TURNOS':>7} | {'TIEMPO':>8} | {'VEREDICTO':<16}"
    )
    print(header)
    print('-' * width)

    total_elapsed = 0.0
    for key_a, key_b in MATCHUPS:
        desc_a = AGENT_REGISTRY[key_a][1]
        desc_b = AGENT_REGISTRY[key_b][1]
        pairing_label = f'{key_a} ({desc_a}) vs {key_b} ({desc_b})'

        m = _run_pairing(key_a, key_b, n_battles, team_size, n_cores)
        total_elapsed += m["elapsed"]

        ic_str = f'[{m["ic_lo"]:>4.1f}, {m["ic_hi"]:>4.1f}]'
        verdict = _verdict(m['ic_lo'], m['ic_hi'], key_a, key_b)
        print(
            f"{pairing_label:<32} | "
            f"{m['wr_a']:>5.1f}% | {m['wr_b']:>5.1f}% | {m['draws']:>4} | "
            f"{ic_str:>16} | {m['avg_hp']:>5.1f}% | {m['avg_alive']:>5.1f}% | "
            f"{m['avg_turns']:>7.1f} | {m['elapsed']:>7.1f}s | {verdict:<16}"
        )

    print('-' * width)
    print(f"{'Tiempo total ' + str(team_size) + 'v' + str(team_size) + ':':<32}   {total_elapsed:>6.1f}s")
    print('=' * width)


def main() -> None:
    """Parse CLI args y ejecuta el torneo para los tamanos solicitados."""
    parser = argparse.ArgumentParser(description='Torneo IA5 vs L1-L4')
    parser.add_argument('--n', type=int, default=200,
                        help='Batallas por emparejamiento (default: 200)')
    parser.add_argument('--cores', type=int, default=None,
                        help='Nucleos a usar (default: cpu_count - 1)')
    parser.add_argument('--size', choices=['3', '4', 'both'], default='both',
                        help='Tamano de equipo: 3, 4, o both (default: both)')
    args = parser.parse_args()

    n_cores = args.cores if args.cores is not None else max(1, cpu_count() - 1)

    sizes = [3, 4] if args.size == 'both' else [int(args.size)]
    for ts in sizes:
        imprimir_torneo(team_size=ts, n_battles=args.n, n_cores=n_cores)


if __name__ == '__main__':
    main()
