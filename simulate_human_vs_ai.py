from src.utils.data_loader import DataLoader
from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState, Action, ActionType
from src.ai.level1_agent import Level1Agent
from src.ai.level2_agent import Level2Agent


def build_battle_state(p1_team, p2_team, p1_idx, p2_idx, turn_num) -> BattleState:
    return BattleState(
        p1_team=[p.to_state() for p in p1_team],
        p2_team=[p.to_state() for p in p2_team],
        p1_active_index=p1_idx,
        p2_active_index=p2_idx,
        turn_number=turn_num
    )


def choose_ids(prompt, default_ids):
    raw = input(f"{prompt} (ingresa IDs separados por comas, o Enter para default {default_ids}): ")
    if not raw.strip():
        return default_ids
    try:
        ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        return ids
    except Exception:
        print("Entrada inválida, usando valores por defecto.")
        return default_ids


def human_vs_ai():
    print("== Humano vs IA - Interactivo ==")
    loader = DataLoader("data/pokemon_pool.json", "data/moves_pool.json")

    mode = input("Modo: 1 para 1v1, 3 para 3v3 (default 3): ")
    if mode.strip() == "1":
        p1_ids = choose_ids("IDs de tu Pokémon (ej: 6)", [6])
        p2_ids = choose_ids("IDs de la IA (ej: 3)", [3])
    else:
        p1_ids = choose_ids("IDs de tu equipo 3v3 (ej: 6,3,9)", [6, 3, 9])
        p2_ids = choose_ids("IDs del equipo IA 3v3 (ej: 94,143,254)", [94, 143, 254])

    # crear equipos
    try:
        p1_team = [loader.create_battle_pokemon(i) for i in p1_ids]
        p2_team = [loader.create_battle_pokemon(i) for i in p2_ids]
    except Exception as e:
        print(f"Error al crear equipos: {e}")
        return

    # elegir agente IA
    ai_level = input("IA nivel: 1 o 2 (default 1): ")
    if ai_level.strip() == "2":
        agent = Level2Agent(player_id=2)
    else:
        agent = Level1Agent(player_id=2)

    p1_idx = 0
    p2_idx = 0
    turn = 1

    while True:
        print(f"\n--- TURNO {turn} ---")

        # si activo caído, forzar switch humano
        if p1_team[p1_idx].is_fainted():
            alive = [i for i, p in enumerate(p1_team) if not p.is_fainted()]
            if not alive:
                print("Has perdido. Todos tus Pokémon están debilitados.")
                break
            print("Tu Pokémon activo está debilitado. Elige reemplazo:")
            for i in alive:
                p = p1_team[i]
                print(f"{i}: {p.name} (HP {p.current_hp}/{p.max_hp})")
            sel = int(input("Índice a enviar: "))
            if sel in alive:
                p1_idx = sel
            else:
                p1_idx = alive[0]

        if p2_team[p2_idx].is_fainted():
            alive2 = [i for i, p in enumerate(p2_team) if not p.is_fainted()]
            if not alive2:
                print("¡Has ganado! La IA no tiene más Pokémon.")
                break
            p2_idx = alive2[0]

        print(f"Tu activo: {p1_team[p1_idx].name} (HP {p1_team[p1_idx].current_hp}/{p1_team[p1_idx].max_hp})")
        print(f"IA activo: {p2_team[p2_idx].name} (HP {p2_team[p2_idx].current_hp}/{p2_team[p2_idx].max_hp})")

        # Construir BattleState para que IA y humano puedan leer
        state = build_battle_state(p1_team, p2_team, p1_idx, p2_idx, turn)

        # Preguntar acción humana
        print("Tus movimientos:")
        for i, mv in enumerate(p1_team[p1_idx].moves):
            print(f"{i}: {mv.name} (PP {mv.current_pp}/{mv.max_pp}, Power {mv.power})")

        print("Opciones: 'm' para mover, 's' para cambiar")
        choice = input("Elige acción (m/s): ").strip().lower()
        if choice == 's':
            alive = [i for i, p in enumerate(p1_team) if not p.is_fainted() and i != p1_idx]
            if not alive:
                print("No hay Pokémon válidos para cambiar; se forzará un movimiento.")
                human_action = Action(type=ActionType.MOVE, target_index=0)
            else:
                print("Elegibles para switch:")
                for i in alive:
                    p = p1_team[i]
                    print(f"{i}: {p.name} (HP {p.current_hp}/{p.max_hp})")
                sel = input("Índice a cambiar: ")
                try:
                    sel_i = int(sel)
                    if sel_i in alive:
                        human_action = Action(type=ActionType.SWITCH, target_index=sel_i)
                    else:
                        print("Selección inválida, eligiendo primero disponible.")
                        human_action = Action(type=ActionType.SWITCH, target_index=alive[0])
                except Exception:
                    human_action = Action(type=ActionType.SWITCH, target_index=alive[0])
        else:
            sel = input("Índice de movimiento a usar: ")
            try:
                mv_i = int(sel)
                human_action = Action(type=ActionType.MOVE, target_index=mv_i)
            except Exception:
                print("Entrada inválida, usando movimiento 0.")
                human_action = Action(type=ActionType.MOVE, target_index=0)

        # IA decide
        ai_action = agent.get_action(state)

        # Procesar turno
        result, p1_idx, p2_idx = process_turn(p1_team, p1_idx, human_action, p2_team, p2_idx, ai_action)

        for out in result.outcomes:
            actor_name = p1_team[p1_idx].name if out.actor == 1 else p2_team[p2_idx].name
            if out.action_type == ActionType.SWITCH:
                print(f"> {actor_name} fue intercambiado.")
            else:
                if out.hit_success:
                    print(f"> {actor_name} atacó. Daño: {out.damage_dealt}")
                else:
                    print(f"> {actor_name} falló el ataque.")

        if result.match_over:
            if result.winner == 1:
                print("¡Has ganado la partida!")
            elif result.winner == 2:
                print("La IA ha ganado la partida.")
            else:
                print("Empate.")
            break

        turn += 1


if __name__ == '__main__':
    human_vs_ai()
