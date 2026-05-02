# src/tools/auto_battler.py

import sys
import copy
from time import perf_counter

# Importa tu motor y tus agentes
from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState
from src.ai.level1_agent import Level1Agent
from src.ai.level2_agent import Level2Agent
from src.core.interfaces import BattleState, ActionType
from src.utils.data_loader import DataLoader
def run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs=False):
    """Ejecuta una batalla sin Pygame y retorna el ID del ganador (1, 2, o None)."""
    p1_active_idx = 0
    p2_active_idx = 0
    match_over = False
    winner = None
    turn_count = 0

    while not match_over and turn_count < 100:  # Límite de 100 turnos para evitar bucles infinitos
        turn_count += 1
        
        # 1. Preparar el estado para los agentes
        state = BattleState(
            p1_team=p1_team, p1_active_index=p1_active_idx,
            p2_team=p2_team, p2_active_index=p2_active_idx,
            turn_number=turn_count
        )

        # 2. Los cerebros deciden
        p1_action = agent1.get_action(state)
        p2_action = agent2.get_action(state)

        # 3. El árbitro resuelve el turno
        turn_result, new_p1_idx, new_p2_idx = process_turn(
            p1_team, p1_active_idx, p1_action,
            p2_team, p2_active_idx, p2_action
        )

        p1_active_idx = new_p1_idx
        p2_active_idx = new_p2_idx
        match_over = turn_result.match_over
        winner = turn_result.winner

        if print_logs:
            print(f"\n--- TURNO {turn_count} ---")
            
            # Guardamos los nombres al inicio del turno para saber quién es quién
            current_p1 = p1_team[p1_active_idx].name.capitalize()
            current_p2 = p2_team[p2_active_idx].name.capitalize()

            for out in turn_result.outcomes:
                actor_name = current_p1 if out.actor == 1 else current_p2
                target_name = current_p2 if out.actor == 1 else current_p1

                # --- CASO 1: CAMBIO (SWITCH) ---
                if out.action_type == ActionType.SWITCH:
                    switched_pkmn = next((p for p in (p1_team if out.actor == 1 else p2_team) if p.id == out.action_id), None)
                    name = switched_pkmn.name.capitalize() if switched_pkmn else f"#{out.action_id}"
                    print(f"[CAMBIO] Actor {out.actor} sacó a {name}")
                    
                    # Actualizamos el nombre en memoria para los siguientes mensajes
                    if out.actor == 1:
                        current_p1 = name
                    else:
                        current_p2 = name

                # --- CASO 2: ATAQUE (MOVE) ---
                else:
                    # Buscar el nombre y datos del movimiento
                    team = p1_team if out.actor == 1 else p2_team
                    active_pkmn = next((p for p in team if p.name.capitalize() == actor_name), None)
                    
                    mv_name = "Movimiento Desconocido"
                    actual_move = None
                    if active_pkmn:
                        for mv in getattr(active_pkmn, 'moves', []):
                            if getattr(mv, 'id', None) == out.action_id:
                                mv_name = getattr(mv, 'name', '???')
                                actual_move = mv
                                break
                    
                    label = mv_name

                    # 2.1 Fallo o Bloqueo
                    if not out.hit_success:
                        print(f"[{actor_name}] intentó usar {label} pero falló (o no pudo moverse).")
                    
                    # 2.2 Ataque con Daño
                    elif out.damage_dealt > 0:
                        print(f"[{actor_name}] usó {label}. Daño: {out.damage_dealt}")
                        if getattr(actual_move, 'drain', 0) > 0:
                            print(f"  -> [{actor_name}] drenó vida. HP actual: {out.attacker_hp_remaining}")
                    
                    # 2.3 Efecto de Estado, Curación o Inmunidad (Daño 0)
                    else:
                        if getattr(out, 'type_multiplier', 1.0) == 0.0:
                            print(f"[{actor_name}] usó {label} -> NO TIENE EFECTO (Inmunidad de {target_name})")
                        else:
                            print(f"[{actor_name}] usó {label} (Efecto)")
                            if getattr(actual_move, 'healing', 0) > 0:
                                print(f"  -> [{actor_name}] se curó. HP actual: {out.attacker_hp_remaining}")

                    # --- LOG DE ESTADOS Y DEBILITAMIENTO ---
                    if getattr(out, 'status_applied', None):
                        status_name = str(out.status_applied).split('.')[-1].replace('_', ' ')
                        print(f"  -> [ESTADO] ¡Se aplicó {status_name} a {target_name}!")

                    if out.target_fainted:
                        print(f"  -> [KO] {target_name} ha caído.")
    return winner, turn_count

def run_tournament(n_battles: int, AgentClass1, AgentClass2):
    print(f" INICIANDO TORNEO: {AgentClass1.__name__} VS {AgentClass2.__name__} ({n_battles} Batallas) ")
    start_time = perf_counter()

    wins_p1 = 0
    wins_p2 = 0
    draws = 0
    total_turns = 0
    loader = DataLoader("data/pokemon_pool.json", "data/moves_pool.json")
    for i in range(n_battles):
        # 2. Genera equipos frescos (con HP y PP al 100%) para cada batalla
        p1_team_fresh = loader.generate_random_team(4)
        p2_team_fresh = loader.generate_random_team(4)

        agent1 = AgentClass1(player_id=1)
        agent2 = AgentClass2(player_id=2)

        show_logs = (i == 0) 
        
        winner, turns = run_headless_battle(p1_team_fresh, p2_team_fresh, agent1, agent2, print_logs=show_logs)
        
        total_turns += turns
        if winner == 1:
            wins_p1 += 1
        elif winner == 2:
            wins_p2 += 1
        else:
            draws += 1

    end_time = perf_counter()
    
    print("\n==========================================")
    print(" RESULTADOS DEL TORNEO ")
    print("==========================================")
    print(f"Total de batallas: {n_battles}")
    print(f"Tiempo de ejecución: {end_time - start_time:.3f} segundos")
    print(f"Promedio de turnos por batalla: {total_turns / n_battles:.1f}")
    print("------------------------------------------")
    print(f"Victorias {AgentClass1.__name__} (P1): {wins_p1} ({(wins_p1/n_battles)*100:.1f}%)")
    print(f"Victorias {AgentClass2.__name__} (P2): {wins_p2} ({(wins_p2/n_battles)*100:.1f}%)")
    print(f"Empates / Límite de turnos: {draws}")
    print("==========================================\n")


import sys
import os

def run_debug_batch(n_battles: int, AgentClass1, AgentClass2, output_file="debug_logs.txt"):
    """Ejecuta batallas y guarda TODO el registro (Turno a Turno) en un archivo .txt"""
    original_stdout = sys.stdout  # Guardamos la consola original
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    poke_path = os.path.join(project_root, "data", "pokemon_pool.json")
    moves_path = os.path.join(project_root, "data", "moves_pool.json")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            sys.stdout = f  
            
            print(f"🔥 INICIANDO MODO DEBUG: {n_battles} BATALLAS COMPLETAS 🔥")
            loader = DataLoader(poke_path, moves_path)
            
            for i in range(1, n_battles + 1):
                print(f"\n\n==========================================")
                print(f" BATALLA {i} DE {n_battles} ")
                print(f"==========================================")
                
                p1_team = loader.generate_random_team(4)
                p2_team = loader.generate_random_team(4)
                
                agent1 = AgentClass1(player_id=1)
                agent2 = AgentClass2(player_id=2)
                
                run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs=True)
                
    finally:
        sys.stdout = original_stdout  
        
    print(f" ¡Operación exitosa! Se guardó el registro paso a paso de {n_battles} batallas.")
    print(f" Revisa el archivo: {output_file} en tu carpeta del proyecto.")
if __name__ == "__main__":
    CANTIDAD_BATALLAS = 1000
    CANTIDAD_BATALLAS_DEBUG = 100

    #run_tournament(CANTIDAD_BATALLAS, Level1Agent, Level2Agent)
    
    run_debug_batch(CANTIDAD_BATALLAS_DEBUG, Level1Agent, Level2Agent, "debug_logs.txt")