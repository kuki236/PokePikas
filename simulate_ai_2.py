
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

    while not match_over and turn_count < 100:  # Límite de 100 turnos
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

        if print_logs:
            print(f"\n--- TURNO {turn_count} ---")
            
            # Referencias temporales para el log antes de actualizar los índices globales
            # Esto ayuda a rastrear quién empezó el turno
            p1_pkmn = p1_team[p1_active_idx]
            p2_pkmn = p2_team[p2_active_idx]

            for out in turn_result.outcomes:
                # Determinamos atacante y defensor REALES basándonos en el actor_id
                attacker = p1_pkmn if out.actor == 1 else p2_pkmn
                defender = p2_pkmn if out.actor == 1 else p1_pkmn
                
                actor_name = attacker.name.capitalize()
                target_name = defender.name.capitalize()

                # --- CASO 1: CAMBIO (SWITCH) ---
                if out.action_type == ActionType.SWITCH:
                    switched_pkmn = next((p for p in (p1_team if out.actor == 1 else p2_team) if p.id == out.action_id), None)
                    name = switched_pkmn.name.capitalize() if switched_pkmn else "???"
                    print(f"[CAMBIO] Actor {out.actor} sacó a {name}")
                    
                    # Sincronizamos la referencia local para los siguientes outcomes del turno
                    if out.actor == 1: p1_pkmn = switched_pkmn
                    else: p2_pkmn = switched_pkmn

                # --- CASO 2: ATAQUE (MOVE) ---
                else:
                    # Búsqueda segura del movimiento para evitar AttributeError
                    actual_move = None
                    if attacker and hasattr(attacker, 'moves'):
                        actual_move = next((m for m in attacker.moves if m.id == out.action_id), None)
                    
                    if actual_move is None:
                        mv_label = "Movimiento Desconocido"
                        cat_icon = "❓"
                    else:
                        mv_label = actual_move.name
                        # Verificación segura de categoría
                        category = getattr(actual_move, 'category', 'PHYSICAL')
                        cat_icon = "💥" if category == "PHYSICAL" else ("🔮" if category == "SPECIAL" else "🛡️")
                    
                    # 2.1 Fallo o incapacidad (Parálisis, Sueño, Fallo de precisión)
                    if not out.hit_success:
                        print(f"[{actor_name}] intentó usar {mv_label} pero falló o está incapacitado.")
                    
                    # 2.2 Ataque con Daño
                    elif out.damage_dealt > 0:
                        print(f"[{actor_name}] usó {mv_label} {cat_icon}. Daño: {out.damage_dealt}")
                        if actual_move and getattr(actual_move, 'drain', 0) > 0:
                            print(f"  -> [{actor_name}] drenó vida. HP actual: {out.attacker_hp_remaining}")
                    
                    # 2.3 Efecto Puro o Inmunidad
                    else:
                        if getattr(out, 'type_multiplier', 1.0) == 0.0:
                            print(f"[{actor_name}] usó {mv_label} -> 🚫 NO TIENE EFECTO (Inmunidad de {target_name})")
                        else:
                            print(f"[{actor_name}] usó {mv_label} (Efecto)")
                            # Lógica de curación para Roost/Synthesis
                            if actual_move and getattr(actual_move, 'healing', 0) > 0:
                                print(f"  -> [{actor_name}] se curó. HP actual: {out.attacker_hp_remaining}")

                    # Logs de Estado (Toxic, Burn, Sleep, etc.)
                    if out.status_applied:
                        status_str = str(out.status_applied).split('.')[-1].replace('_', ' ')
                        # Rest aplica el estado al actor, los demás al objetivo
                        final_target = actor_name if mv_label.lower() == "rest" else target_name
                        print(f"  -> [ESTADO] ¡{status_str} aplicado a {final_target}!")

                    if out.target_fainted:
                        print(f"  -> [KO] {target_name} ha caído.")

        # Actualizar índices activos para el siguiente turno
        p1_active_idx = new_p1_idx
        p2_active_idx = new_p2_idx
        match_over = turn_result.match_over
        winner = turn_result.winner
        
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

    run_tournament(CANTIDAD_BATALLAS, Level1Agent, Level2Agent)
    
    #run_debug_batch(CANTIDAD_BATALLAS_DEBUG, Level1Agent, Level2Agent, "debug_logs.txt")