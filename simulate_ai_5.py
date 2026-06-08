import os
import sys
from time import perf_counter
from typing import List, Tuple

from src.ai.level1_agent import Level1Agent
from src.ai.level2_agent import Level2Agent
from src.ai.level3_agent import Level3Agent
from src.ai.level4_agent import Level4Agent
from src.ai.level5_agent import Level5Agent
from src.core.battle_engine import process_turn
from src.core.interfaces import ActionType, BattleState
from src.utils.data_loader import DataLoader


DEFAULT_POKEMON_PATH = 'data/pokemon_pool.json'
DEFAULT_MOVES_PATH = 'data/moves_pool.json'
MAX_TURNS = 100


def run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs: bool = False):
    """
    Descripción breve:
    Ejecuta una batalla entre dos equipos de Pokémon de forma headless.
    """
    p1_active_idx = 0
    p2_active_idx = 0
    match_over = False
    winner = None
    turn_count = 0

    while not match_over and turn_count < MAX_TURNS:
        turn_count += 1

        state = BattleState(
            p1_team=[p.to_state() for p in p1_team],
            p1_active_index=p1_active_idx,
            p2_team=[p.to_state() for p in p2_team],
            p2_active_index=p2_active_idx,
            turn_number=turn_count,
        )

        p1_action = agent1.get_action(state)
        p2_action = agent2.get_action(state)

        old_stdout = sys.stdout
        devnull_handle = None
        if not print_logs:
            devnull_handle = open(os.devnull, 'w')
            sys.stdout = devnull_handle

        try:
            turn_result, new_p1_idx, new_p2_idx = process_turn(
                p1_team, p1_active_idx, p1_action,
                p2_team, p2_active_idx, p2_action,
            )
        finally:
            if not print_logs:
                sys.stdout = old_stdout
                devnull_handle.close()

        if print_logs:
            print(f'\n--- TURNO {turn_count} ---')
            p1_pkmn = p1_team[p1_active_idx]
            p2_pkmn = p2_team[p2_active_idx]

            for out in turn_result.outcomes:
                attacker = p1_pkmn if out.actor == 1 else p2_pkmn
                defender = p2_pkmn if out.actor == 1 else p1_pkmn
                actor_name = attacker.name.capitalize()
                target_name = defender.name.capitalize()

                if out.action_type == ActionType.SWITCH:
                    switched_pkmn = next(
                        (p for p in (p1_team if out.actor == 1 else p2_team) if p.id == out.action_id),
                        None,
                    )
                    name = switched_pkmn.name.capitalize() if switched_pkmn else '???'
                    print(f'[CAMBIO] Actor {out.actor} sacó a {name}')
                    if out.actor == 1:
                        p1_pkmn = switched_pkmn
                    else:
                        p2_pkmn = switched_pkmn
                else:
                    actual_move = None
                    if attacker and hasattr(attacker, 'moves'):
                        actual_move = next((m for m in attacker.moves if m.id == out.action_id), None)

                    if actual_move is None:
                        mv_label = 'Movimiento Desconocido'
                        cat_icon = '❓'
                    else:
                        mv_label = actual_move.name
                        category = getattr(actual_move, 'category', 'PHYSICAL')
                        cat_icon = '💥' if category == 'PHYSICAL' else ('🔮' if category == 'SPECIAL' else '🛡️')

                    if not out.hit_success:
                        print(f'[{actor_name}] intentó usar {mv_label} pero falló o está incapacitado.')
                    elif out.damage_dealt > 0:
                        print(f'[{actor_name}] usó {mv_label} {cat_icon}. Daño: {out.damage_dealt}')
                        if actual_move and getattr(actual_move, 'drain', 0) > 0:
                            print(f'  -> [{actor_name}] drenó vida. HP actual: {out.attacker_hp_remaining}')
                    else:
                        if getattr(out, 'type_multiplier', 1.0) == 0.0:
                            print(f'[{actor_name}] usó {mv_label} -> 🚫 NO TIENE EFECTO (Inmunidad de {target_name})')
                        else:
                            print(f'[{actor_name}] usó {mv_label} (Efecto)')
                            if actual_move and getattr(actual_move, 'healing', 0) > 0:
                                print(f'  -> [{actor_name}] se curó. HP actual: {out.attacker_hp_remaining}')

                    if out.status_applied:
                        status_str = str(out.status_applied).split('.')[-1].replace('_', ' ')
                        final_target = actor_name if mv_label.lower() == 'rest' else target_name
                        print(f'  -> [ESTADO] ¡{status_str} aplicado a {final_target}!')

                    if out.target_fainted:
                        print(f'  -> [KO] {target_name} ha caído.')

        p1_active_idx = new_p1_idx
        p2_active_idx = new_p2_idx
        match_over = turn_result.match_over
        winner = turn_result.winner

    return winner, turn_count


def correr_bateria_enfrentamiento(agent_class_p1, agent_class_p2, team_size: int = 3, batallas: int = 200):
    """
    Descripción breve:
    Realiza una batería de enfrentamientos entre dos agentes de batalla y devuelve las estadísticas.
    """
    loader = DataLoader(DEFAULT_POKEMON_PATH, DEFAULT_MOVES_PATH)
    wins_p1 = 0
    wins_p2 = 0
    ties = 0
    total_turns = 0

    for _ in range(batallas):
        p1_team = loader.generate_random_team(team_size)
        p2_team = loader.generate_random_team(team_size)

        agent1 = agent_class_p1(player_id=1)
        agent2 = agent_class_p2(player_id=2)

        winner, turns = run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs=False)
        total_turns += turns

        if winner == 1:
            wins_p1 += 1
        elif winner == 2:
            wins_p2 += 1
        else:
            ties += 1

    total_validas = wins_p1 + wins_p2
    wr_p1 = round((wins_p1 / total_validas) * 100, 1) if total_validas > 0 else 0.0
    wr_p2 = round((wins_p2 / total_validas) * 100, 1) if total_validas > 0 else 0.0
    avg_turns = round(total_turns / batallas, 1) if batallas > 0 else 0.0

    return wr_p1, wr_p2, avg_turns, ties


def ejecutar_emparejamiento(label: str, cls1, cls2, team_size: int, batallas: int):
    start = perf_counter()
    wr1, wr2, turns, ties = correr_bateria_enfrentamiento(cls1, cls2, team_size, batallas)
    elapsed = round(perf_counter() - start, 2)
    return label, wr1, wr2, turns, ties, elapsed


def imprimir_resultado(label: str, wr1: float, wr2: float, turns: float, ties: int, elapsed: float):
    print(f"{label:<45} | {str(wr1) + '%':>8} | {str(wr2) + '%':>8} | {ties:>8} | {turns:>8} | {str(elapsed) + 's':>10}")


def torneo_level5(team_size: int = 3, batallas: int = 200):
    """
    Descripción breve:
    Realiza pruebas de nivel 5 asegurando que IA 5 es el Jugador 1.
    """
    print('\n' + '=' * 115)
    print(f"{'PRUEBAS DE NIVEL 5 (' + str(team_size) + 'v' + str(team_size) + ')':^115}")
    print(f"{'Muestra estadística: ' + str(batallas) + ' batallas por emparejamiento':^115}")
    print('=' * 115)
    # [MODIFICADO] Amplié ligeramente el espacio del Label para que encajen los nuevos nombres
    print(f"{'EMPAREJAMIENTO (P1 vs P2)':<45} | {'WR P1':>8} | {'WR P2':>8} | {'EMPATES':>8} | {'TURNOS':>8} | {'TIEMPO':>10}")
    print('-' * 115)

    # [MODIFICADO] Ahora Level5Agent se pasa primero para que sea instanciado como P1
    pairings: List[Tuple[str, object, object]] = [
        ('Nivel 5 (Evolutivo) vs Nivel 1 (Azar)', Level5Agent, Level1Agent),
        ('Nivel 5 (Evolutivo) vs Nivel 2 (Greedy)', Level5Agent, Level2Agent),
        ('Nivel 5 (Evolutivo) vs Nivel 3 (Minimax)', Level5Agent, Level3Agent),
        ('Nivel 5 (Evolutivo) vs Nivel 4 (Avanzado)', Level5Agent, Level4Agent),
    ]

    for label, c1, c2 in pairings:
        result = ejecutar_emparejamiento(label, c1, c2, team_size, batallas)
        imprimir_resultado(*result)

    print('=' * 115 + '\n')


def prueba_rapida_level4_vs_level5(team_size: int = 3):
    """
    Descripción breve:
    Realiza una prueba rápida asignando a IA 5 como P1 y a IA 4 como P2.
    """
    loader = DataLoader(DEFAULT_POKEMON_PATH, DEFAULT_MOVES_PATH)
    p1_team = loader.generate_random_team(team_size)
    p2_team = loader.generate_random_team(team_size)

    # [MODIFICADO] Se invierten las asignaciones. Ahora agent1 es IA 5.
    agent1 = Level5Agent(player_id=1)
    agent2 = Level4Agent(player_id=2)

    print('Agentes creados, iniciando batalla (P1=IA5, P2=IA4)...')
    winner, turns = run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs=True)
    print(f'Ganador: Jugador {winner}, Turnos: {turns}')


if __name__ == '__main__':
    print('Iniciando simulación Headless de pruebas (IA 5 siempre como P1)...')
    prueba_rapida_level4_vs_level5(team_size=3)
    torneo_level5(team_size=3, batallas=200)