
import sys
import os
import copy
from time import perf_counter

# Importa tu motor y tus agentes
from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState, ActionType
from src.ai.level1_agent import Level1Agent
from src.ai.level2_agent import Level2Agent
from src.utils.data_loader import DataLoader

def run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs=False):
    """Ejecuta una batalla sin Pygame y retorna el ID del ganador y los turnos."""
    p1_active_idx = 0
    p2_active_idx = 0
    match_over = False
    winner = None
    turn_count = 0

    while not match_over and turn_count < 100:  
        turn_count += 1
        
        state = BattleState(
            p1_team=p1_team, p1_active_index=p1_active_idx,
            p2_team=p2_team, p2_active_index=p2_active_idx,
            turn_number=turn_count
        )

        p1_action = agent1.get_action(state)
        p2_action = agent2.get_action(state)

        turn_result, new_p1_idx, new_p2_idx = process_turn(
            p1_team, p1_active_idx, p1_action,
            p2_team, p2_active_idx, p2_action
        )

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



# LÓGICA DE TABLAS 

def imprimir_tabla_winrates(resultados_3v3, resultados_4v4):
    """
    Imprime una tabla que resume los resultados de simulaciones de juegos 3v3 y 4v4.

    Args:
        resultados_3v3 (dict): Diccionario con los resultados de las simulaciones 3v3.
        resultados_4v4 (dict): Diccionario con los resultados de las simulaciones 4v4.

    Returns:
        None

    Raises:
        KeyError: Si alguno de los diccionarios no contiene las claves esperadas (nivel_1, nivel_2, turnos, tiempos).
        TypeError: Si alguno de los valores en los diccionarios no es una lista.
    """
    print("\n" + "="*85)
    print(f"{'RESULTADOS DE SIMULACIONES':^85}")
    print("="*85)
    print("                                     3v3                                   4v4")
    print("Simulacion             1     2     3     4     5           1     2     3     4     5")
    print("-" * 85)
    
    vacio = ["-", "-", "-", "-", "-"]
    r_3v3_l1 = resultados_3v3.get('nivel_1', vacio)
    r_3v3_l2 = resultados_3v3.get('nivel_2', vacio)
    r_3v3_t  = resultados_3v3.get('turnos', vacio)
    r_3v3_tm = resultados_3v3.get('tiempos', vacio)
    
    r_4v4_l1 = resultados_4v4.get('nivel_1', vacio)
    r_4v4_l2 = resultados_4v4.get('nivel_2', vacio)
    r_4v4_t  = resultados_4v4.get('turnos', vacio)
    r_4v4_tm = resultados_4v4.get('tiempos', vacio)
    
    formatear = lambda lista: " ".join([f"{str(x):>5}" for x in lista])

    print(f"Sim Nivel 1      {formatear(r_3v3_l1)}         {formatear(r_4v4_l1)}")
    print(f"Sim Nivel 2      {formatear(r_3v3_l2)}         {formatear(r_4v4_l2)}")
    print("-" * 85)
    print(f"Prom Turnos      {formatear(r_3v3_t)}         {formatear(r_4v4_t)}")
    print(f"Tiempo Ejec      {formatear(r_3v3_tm)}         {formatear(r_4v4_tm)}")
    print("="*85 + "\n")

def correr_simulaciones_winrate(team_size, num_simulaciones=5, batallas_por_sim=100):
    """
    Descripción breve:
     Ejecuta simulaciones de batallas de Pokémon entre equipos aleatorios y devuelve las tasas de victoria para cada nivel de agente.

    Args:
        team_size (int): Tamaño del equipo de Pokémon.
        num_simulaciones (int, optional): Número de simulaciones a ejecutar. Valor por defecto: 5.
        batallas_por_sim (int, optional): Número de batallas por simulación. Valor por defecto: 100.

    Returns:
        dict: Un diccionario con las tasas de victoria para cada nivel de agente, el número promedio de turnos y los tiempos de ejecución.

    Raises:
        No se lanzan excepciones explícitas. Sin embargo, puede producirse un error si no se pueden cargar los datos de los Pokémon o si hay un problema con la ejecución de las batallas.
    """
    loader = DataLoader("data/pokemon_pool.json", "data/moves_pool.json")
    
    winrates_l1 = []
    winrates_l2 = []
    turnos_promedio = []
    tiempos_ejecucion = []
    
    for sim in range(num_simulaciones):
        start_time = perf_counter()
        wins_p1 = 0
        wins_p2 = 0
        total_turns = 0
        
        for _ in range(batallas_por_sim):
            p1_team = loader.generate_random_team(team_size)
            p2_team = loader.generate_random_team(team_size)
            
            agent1 = Level1Agent(player_id=1)
            agent2 = Level2Agent(player_id=2)
            
            winner, turns = run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs=False)
            
            total_turns += turns
            if winner == 1:
                wins_p1 += 1
            elif winner == 2:
                wins_p2 += 1
                
        end_time = perf_counter()
        
        exec_time = round(end_time - start_time, 2)
        avg_turns = round(total_turns / batallas_por_sim, 1)
        
        total_validas = wins_p1 + wins_p2
        if total_validas > 0:
            wr_l1 = round((wins_p1 / total_validas) * 100)
            wr_l2 = round((wins_p2 / total_validas) * 100)
        else:
            wr_l1, wr_l2 = 0, 0
            
        winrates_l1.append(f"{wr_l1}%")
        winrates_l2.append(f"{wr_l2}%")
        turnos_promedio.append(str(avg_turns))
        tiempos_ejecucion.append(str(exec_time))
        
    return {
        'nivel_1': winrates_l1, 
        'nivel_2': winrates_l2,
        'turnos': turnos_promedio,
        'tiempos': tiempos_ejecucion
    }


if __name__ == "__main__":
    print("Calculando simulaciones 3v3 (5 rondas de 100 batallas)...")
    resultados_3v3 = correr_simulaciones_winrate(team_size=3, num_simulaciones=5, batallas_por_sim=100)
    
    print("Calculando simulaciones 4v4 (5 rondas de 100 batallas)...")
    resultados_4v4 = correr_simulaciones_winrate(team_size=4, num_simulaciones=5, batallas_por_sim=100)
    
    imprimir_tabla_winrates(resultados_3v3, resultados_4v4)