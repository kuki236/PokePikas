from src.utils.data_loader import DataLoader
from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState, ActionType

# Importamos los agentes de P3 (Asegúrate de que P3 los haya creado)
from src.ai.level1_agent import Level1Agent
from src.ai.level2_agent import Level2Agent

def build_battle_state(p1_team, p2_team, p1_idx, p2_idx, turn_num) -> BattleState:
    """Función auxiliar para empaquetar la 'foto matemática' para la IA"""
    return BattleState(
        p1_team=[p.to_state() for p in p1_team],
        p2_team=[p.to_state() for p in p2_team],
        p1_active_index=p1_idx,
        p2_active_index=p2_idx,
        turn_number=turn_num
    )

def test_ai_battle_1v1():
    print("=== INICIANDO SIMULACIÓN 1v1: IA vs IA ===")
    
    loader = DataLoader("data/pokemon_pool.json", "data/moves_pool.json")
    
    p1_team = [loader.create_battle_pokemon(6)] 
    p2_team = [loader.create_battle_pokemon(3)]
    p1_idx = 0
    p2_idx = 0

    agent_p1 = Level2Agent(player_id=1) 
    agent_p2 = Level1Agent(player_id=2)

    match_over = False
    turn_number = 1

    while not match_over and turn_number < 50:
        print(f"\n--- TURNO {turn_number} ---")
        print(f"P1: {p1_team[p1_idx].name.upper()} (HP: {p1_team[p1_idx].current_hp})")
        print(f"P2: {p2_team[p2_idx].name.upper()} (HP: {p2_team[p2_idx].current_hp})")

        current_state = build_battle_state(p1_team, p2_team, p1_idx, p2_idx, turn_number)

        action_p1 = agent_p1.get_action(current_state)
        action_p2 = agent_p2.get_action(current_state)

        result, p1_idx, p2_idx = process_turn(
            p1_team, p1_idx, action_p1,
            p2_team, p2_idx, action_p2
        )

        for outcome in result.outcomes:
            atacante = p1_team[p1_idx].name if outcome.actor == 1 else p2_team[p2_idx].name
            if outcome.action_type == ActionType.SWITCH:
                print(f"> {atacante.upper()} entró al campo de batalla.")
            else:
                if outcome.hit_success:
                    print(f"> {atacante.upper()} atacó. Daño causado: {outcome.damage_dealt}")
                else:
                    print(f"> {atacante.upper()} falló el ataque.")

        match_over = result.match_over
        turn_number += 1

    print("\n=== FIN DEL COMBATE 1v1 ===")
    if result.winner:
        print(f"¡El Jugador {result.winner} (Agente Nivel {2 if result.winner==1 else 1}) ha ganado!")
    else:
        print("Empate o límite de turnos alcanzado.")


def test_ai_battle_3v3():
    print("=== SIMULACIÓN 3v3: ESTRATEGIA DE EQUIPO ===")
    loader = DataLoader("data/pokemon_pool.json", "data/moves_pool.json")
    
    try:
        p1_team = [loader.create_battle_pokemon(6), loader.create_battle_pokemon(3), loader.create_battle_pokemon(9)]
        p2_team = [loader.create_battle_pokemon(94), loader.create_battle_pokemon(143), loader.create_battle_pokemon(254)]
    except Exception as e:
        print(f"Error al cargar el equipo (verifica los IDs en tu JSON): {e}")
        return
    
    p1_idx = 0
    p2_idx = 0
    match_over = False
    turn_number = 1

    agent_p1 = Level2Agent(player_id=1) 
    agent_p2 = Level1Agent(player_id=2)

    while not match_over and turn_number < 222: 
        print(f"\n--- TURNO {turn_number} ---")

        if p1_team[p1_idx].is_fainted():
            for i, p in enumerate(p1_team):
                if not p.is_fainted():
                    p1_idx = i
                    print(f"|> Jugador 1 envía a {p1_team[p1_idx].name.upper()} para reemplazar al caído.")
                    break
        
        if p2_team[p2_idx].is_fainted():
            for i, p in enumerate(p2_team):
                if not p.is_fainted():
                    p2_idx = i
                    print(f"|> Jugador 2 envía a {p2_team[p2_idx].name.upper()} para reemplazar al caído.")
                    break

        print(f"P1 Activo: {p1_team[p1_idx].name.upper()} (HP: {p1_team[p1_idx].current_hp}/{p1_team[p1_idx].max_hp})")
        print(f"P2 Activo: {p2_team[p2_idx].name.upper()} (HP: {p2_team[p2_idx].current_hp}/{p2_team[p2_idx].max_hp})")

        current_state = build_battle_state(p1_team, p2_team, p1_idx, p2_idx, turn_number)

        action_p1 = agent_p1.get_action(current_state)
        action_p2 = agent_p2.get_action(current_state)

        result, p1_idx, p2_idx = process_turn(
            p1_team, p1_idx, action_p1,
            p2_team, p2_idx, action_p2
        )

        for outcome in result.outcomes:
            actor_name = p1_team[p1_idx].name if outcome.actor == 1 else p2_team[p2_idx].name
            
            if outcome.action_type == ActionType.SWITCH:
                print(f"> {actor_name.upper()} fue intercambiado estratégicamente.")
            else:
                if outcome.hit_success:
                    print(f"> {actor_name.upper()} atacó. Daño: {outcome.damage_dealt}")
                    if outcome.status_applied:
                        print(f"  ¡Se aplicó el estado {outcome.status_applied.value}!")
                else:
                    print(f"> {actor_name.upper()} falló el ataque.")

        match_over = result.match_over
        turn_number += 1

    print("\n=== FIN DEL COMBATE 3v3 ===")
    if result.winner:
        print(f"¡El Jugador {result.winner} (Agente Nivel {2 if result.winner==1 else 1}) ha ganado la batalla de equipos!")
    else:
        print("Empate o límite de turnos alcanzado.")

if __name__ == "__main__":
    # choose your type of battle
    # test_ai_battle_1v1()
    test_ai_battle_3v3()