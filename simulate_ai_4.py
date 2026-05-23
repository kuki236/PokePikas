import sys
import os
import copy
from time import perf_counter
import random

from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState, ActionType
from src.ai.level1_agent import Level1Agent
from src.ai.level2_agent import Level2Agent
from src.ai.level3_agent import Level3Agent
from src.ai.level4_agent import Level4Agent  
from src.utils.data_loader import DataLoader

def run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs=False):
    """Ejecuta una batalla sin renderizado y retorna el ID del ganador y los turnos."""
    p1_active_idx = 0
    p2_active_idx = 0
    match_over = False
    winner = None
    turn_count = 0

    while not match_over and turn_count < 100:  
        turn_count += 1
        
        p1_state_team = [p.to_state() for p in p1_team]
        p2_state_team = [p.to_state() for p in p2_team]

        state = BattleState(
            p1_team=p1_state_team, p1_active_index=p1_active_idx,
            p2_team=p2_state_team, p2_active_index=p2_active_idx,
            turn_number=turn_count
        )

        p1_action = agent1.get_action(state)
        p2_action = agent2.get_action(state)

        old_stdout = sys.stdout
        if not print_logs:
            sys.stdout = open(os.devnull, 'w')
            
        try:
            turn_result, new_p1_idx, new_p2_idx = process_turn(
                p1_team, p1_active_idx, p1_action,
                p2_team, p2_active_idx, p2_action
            )
        finally:
            if not print_logs:
                sys.stdout.close()
                sys.stdout = old_stdout
    

        if print_logs:
            print(f"\n--- TURNO {turn_count} ---")
            p1_pkmn = p1_team[p1_active_idx]
            p2_pkmn = p2_team[p2_active_idx]

            for out in turn_result.outcomes:
                attacker = p1_pkmn if out.actor == 1 else p2_pkmn
                defender = p2_pkmn if out.actor == 1 else p1_pkmn
                
                actor_name = attacker.name.capitalize()
                target_name = defender.name.capitalize()

                if out.action_type == ActionType.SWITCH:
                    switched_pkmn = next((p for p in (p1_team if out.actor == 1 else p2_team) if p.id == out.action_id), None)
                    name = switched_pkmn.name.capitalize() if switched_pkmn else "???"
                    print(f"[CAMBIO] Actor {out.actor} sacó a {name}")
                    
                    if out.actor == 1: p1_pkmn = switched_pkmn
                    else: p2_pkmn = switched_pkmn
                else:
                    actual_move = None
                    if attacker and hasattr(attacker, 'moves'):
                        actual_move = next((m for m in attacker.moves if m.id == out.action_id), None)
                    
                    if actual_move is None:
                        mv_label = "Movimiento Desconocido"
                        cat_icon = "❓"
                    else:
                        mv_label = actual_move.name
                        category = getattr(actual_move, 'category', 'PHYSICAL')
                        cat_icon = "💥" if category == "PHYSICAL" else ("🔮" if category == "SPECIAL" else "🛡️")
                    
                    if not out.hit_success:
                        print(f"[{actor_name}] intentó usar {mv_label} pero falló o está incapacitado.")
                    elif out.damage_dealt > 0:
                        print(f"[{actor_name}] usó {mv_label} {cat_icon}. Daño: {out.damage_dealt}")
                        if actual_move and getattr(actual_move, 'drain', 0) > 0:
                            print(f"  -> [{actor_name}] drenó vida. HP actual: {out.attacker_hp_remaining}")
                    else:
                        if getattr(out, 'type_multiplier', 1.0) == 0.0:
                            print(f"[{actor_name}] usó {mv_label} -> 🚫 NO TIENE EFECTO (Inmunidad de {target_name})")
                        else:
                            print(f"[{actor_name}] usó {mv_label} (Efecto)")
                            if actual_move and getattr(actual_move, 'healing', 0) > 0:
                                print(f"  -> [{actor_name}] se curó. HP actual: {out.attacker_hp_remaining}")

                    if out.status_applied:
                        status_str = str(out.status_applied).split('.')[-1].replace('_', ' ')
                        final_target = actor_name if mv_label.lower() == "rest" else target_name
                        print(f"  -> [ESTADO] ¡{status_str} aplicado a {final_target}!")

                    if out.target_fainted:
                        print(f"  -> [KO] {target_name} ha caído.")

        p1_active_idx = new_p1_idx
        p2_active_idx = new_p2_idx
        match_over = turn_result.match_over
        winner = turn_result.winner
        
    return winner, turn_count

def correr_bateria_enfrentamiento(agent_class_p1, agent_class_p2, team_size=3, batallas=200):
    """Ejecuta una batería concentrada de batallas entre dos tipos de agentes específicos."""
    loader = DataLoader("data/pokemon_pool.json", "data/moves_pool.json")
    wins_p1 = 0
    wins_p2 = 0
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
            
    total_validas = wins_p1 + wins_p2
    wr_p1 = round((wins_p1 / total_validas) * 100) if total_validas > 0 else 0
    wr_p2 = round((wins_p2 / total_validas) * 100) if total_validas > 0 else 0
    avg_turns = round(total_turns / batallas, 1) if batallas > 0 else 0
    
    return wr_p1, wr_p2, avg_turns

def imprimir_matriz_competitiva(team_size, batallas):
    print("\n" + "="*85)
    print(f"{f'TORNEO MULTI-AGENTE POKÉPIKAS ({team_size}v{team_size})':^85}")
    print(f"{f'Muestra estadística: {batallas} batallas por emparejamiento':^85}")
    print("="*85)
    
    start = perf_counter()
    wr_l1_a, wr_l2_a, turns_a = correr_bateria_enfrentamiento(Level1Agent, Level2Agent, team_size, batallas)
    time_a = round(perf_counter() - start, 2)
    
    start = perf_counter()
    wr_l2_b, wr_l3_b, turns_b = correr_bateria_enfrentamiento(Level2Agent, Level3Agent, team_size, batallas)
    time_b = round(perf_counter() - start, 2)

    start = perf_counter()
    wr_l2_c, wr_l4_c, turns_c = correr_bateria_enfrentamiento(Level2Agent, Level4Agent, team_size, batallas)
    time_c = round(perf_counter() - start, 2)

    start = perf_counter()
    wr_l3_d, wr_l4_d, turns_d = correr_bateria_enfrentamiento(Level3Agent, Level4Agent, team_size, batallas)
    time_d = round(perf_counter() - start, 2)
    
    print(f"{'EMPAREJAMIENTO (P1 vs P2)':<38} | {'WIN RATE P1':<11} | {'WIN RATE P2':<11} | {'TURNOS':<6} | {'TIEMPO':<8}")
    print("-" * 85)
    print(f"{'Nivel 1 (Azar) vs Nivel 2 (Greedy)':<38} | {f'{wr_l1_a}%':>10} | {f'{wr_l2_a}%':>10} | {turns_a:>6} | {f'{time_a}s':>7}")
    print("-" * 85)
    print(f"{'Nivel 2 (Greedy) vs Nivel 3 (Minimax)':<38} | {f'{wr_l2_b}%':>10} | {f'{wr_l3_b}%':>10} | {turns_b:>6} | {f'{time_b}s':>7}")
    print(f"{'Nivel 2 (Greedy) vs Nivel 4 (Avanzado)':<38} | {f'{wr_l2_c}%':>10} | {f'{wr_l4_c}%':>10} | {turns_c:>6} | {f'{time_c}s':>7}")
    print("-" * 85)
    print(f"{'Nivel 3 (Minimax) vs Nivel 4 (Avanzado)':<38} | {f'{wr_l3_d}%':>10} | {f'{wr_l4_d}%':>10} | {turns_d:>6} | {f'{time_d}s':>7}")
    print("="*85 + "\n")

if __name__ == "__main__":
    print("Iniciando simulación Headless de Torneo Cruzado...")
    imprimir_matriz_competitiva(team_size=3, batallas=200)
    imprimir_matriz_competitiva(team_size=4, batallas=200)