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

def run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs=False, record_logs=False):
    """Ejecuta una batalla sin Pygame. Graba el historial completo si record_logs=True."""
    p1_active_idx = 0
    p2_active_idx = 0
    match_over = False
    winner = None
    turn_count = 0
    
    battle_transcript = []

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

        if print_logs or record_logs:
            turn_log = [f"--- TURNO {turn_count} ---"]
            p1_pkmn = p1_team[p1_active_idx]
            p2_pkmn = p2_team[p2_active_idx]

            for out in turn_result.outcomes:
                attacker = p1_pkmn if out.actor == 1 else p2_pkmn
                defender = p2_pkmn if out.actor == 1 else p1_team[p1_active_idx] if out.actor == 2 else p2_team[p2_active_idx]
                
                actor_name = attacker.name.capitalize()
                target_name = defender.name.capitalize() if defender else "Oponente"

                if out.action_type == ActionType.SWITCH:
                    switched_pkmn = next((p for p in (p1_team if out.actor == 1 else p2_team) if p.id == out.action_id), None)
                    name = switched_pkmn.name.capitalize() if switched_pkmn else "???"
                    turn_log.append(f"[CAMBIO] Actor {out.actor} sacó a {name}")
                    if out.actor == 1: p1_pkmn = switched_pkmn
                    else: p2_pkmn = switched_pkmn
                else:
                    actual_move = None
                    if attacker and hasattr(attacker, 'moves'):
                        actual_move = next((m for m in attacker.moves if m.id == out.action_id), None)
                    
                    mv_label = actual_move.name if actual_move else "Desconocido"
                    
                    if not out.hit_success:
                        turn_log.append(f"[{actor_name}] intentó usar {mv_label} pero falló.")
                    elif out.damage_dealt > 0:
                        turn_log.append(f"[{actor_name}] usó {mv_label}. Daño: {out.damage_dealt}")
                    else:
                        if getattr(out, 'type_multiplier', 1.0) == 0.0:
                            turn_log.append(f"[{actor_name}] usó {mv_label} -> 🚫 INMUNE")
                        else:
                            turn_log.append(f"[{actor_name}] usó {mv_label} (Efecto de estado/cura)")

                    if out.target_fainted:
                        turn_log.append(f"  -> [KO] {target_name} ha caído.")

            p1_name_active = p1_team[new_p1_idx].name
            p2_name_active = p2_team[new_p2_idx].name
            turn_log.append(f"  [HP RESTANTE] P1({p1_name_active}): {p1_team[new_p1_idx].current_hp}/{p1_team[new_p1_idx].max_hp} | P2({p2_name_active}): {p2_team[new_p2_idx].current_hp}/{p2_team[new_p2_idx].max_hp}")

            if print_logs:
                for line in turn_log: print(line)
            if record_logs:
                battle_transcript.extend(turn_log)

        p1_active_idx = new_p1_idx
        p2_active_idx = new_p2_idx
        match_over = turn_result.match_over
        winner = turn_result.winner
        
    return winner, turn_count, battle_transcript

def correr_torneo_con_volcado_txt(team_size=4, batallas=100, txt_filename="derrotas_level4.txt"):
    """Ejecuta el torneo y guarda TODAS las derrotas del Nivel 4 en un archivo de texto plano."""
    print(f"Iniciando torneo: {batallas} batallas de Nivel 2 (P1) vs Nivel 4 (P2) en {team_size}v{team_size}...")
    loader = DataLoader("data/pokemon_pool.json", "data/moves_pool.json")
    wins_p1 = 0
    wins_p2 = 0
    
    start_time = perf_counter()
    
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write("=====================================================================")
        f.write(f"   REPORTE COMPLETO DE AUTOPSIAS: TODAS LAS DERROTAS DEL NIVEL 4\n")
        f.write(f"   Configuración del Torneo: Muestra de {batallas} batallas ({team_size}v{team_size})\n")
        f.write("=====================================================================\n")
        
        for i in range(batallas):
            p1_team = loader.generate_random_team(team_size)
            p2_team = loader.generate_random_team(team_size)
            
            agent1 = Level2Agent(player_id=1)
            agent2 = Level4Agent(player_id=2)
            
            winner, turns, transcript = run_headless_battle(p1_team, p2_team, agent1, agent2, print_logs=False, record_logs=True)
            
            if winner == 1:
                wins_p1 += 1
                f.write(f"---------------------------------------------------------------------\n")
                f.write(f"💥 DERROTA REGISTRADA #{wins_p1} | Batalla #{i+1} del Torneo (Duró {turns} turnos)\n")
                f.write(f"---------------------------------------------------------------------\n")
                for line in transcript:
                    f.write(line + "\n")
                f.write("\n")
            elif winner == 2:
                wins_p2 += 1

    total_time = round(perf_counter() - start_time, 2)
    wr_p1 = round((wins_p1 / batallas) * 100) if batallas > 0 else 0
    wr_p2 = round((wins_p2 / batallas) * 100) if batallas > 0 else 0
    
    print("\n" + "="*85)
    print(f"TORNEO COMPLETADO EN {total_time}s")
    print(f"Win Rate Nivel 2 (Greedy): {wr_p1}%")
    print(f"Win Rate Nivel 4 (Avanzado): {wr_p2}%")
    print(f"-> ¡ÉXITO! Se han guardado las {wins_p1} derrotas en el archivo: '{txt_filename}'")
    print("="*85 + "\n")

if __name__ == "__main__":
    correr_torneo_con_volcado_txt(team_size=4, batallas=100, txt_filename="derrotas_level4.txt")