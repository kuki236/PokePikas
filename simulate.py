from src.utils.data_loader import DataLoader
from src.core.battle_engine import process_turn
from src.core.interfaces import Action, ActionType

def test_engine():
    print("=== INICIANDO PRUEBA DE INTEGRACIÓN DEL MOTOR ===")
    
    # 1. Instanciamos el cargador con las rutas a los JSON
    loader = DataLoader("data/pokemon_pool.json", "data/moves_pool.json")

    # 2. Creamos los Pokémon (6=Charizard, 3=Venusaur según tu JSON)
    charizard = loader.create_battle_pokemon(6)
    venusaur = loader.create_battle_pokemon(3)

    p1_team = [charizard]
    p2_team = [venusaur]

    print(f"\nCOMBATE: {charizard.name.upper()} vs {venusaur.name.upper()}")
    print(f"Ataques aleatorios asignados a Charizard:")
    for i, move in enumerate(charizard.moves):
        print(f"  [{i}] {move.name} (PP: {move.current_pp})")

    # 3. Simulamos un turno donde ambos atacan usando su primer movimiento (índice 0)
    print("\n--- EJECUTANDO TURNO 1 ---")
    action_p1 = Action(type=ActionType.MOVE, target_index=0)
    action_p2 = Action(type=ActionType.MOVE, target_index=0)

    # Llamamos a tu motor
    result, new_p1_idx, new_p2_idx = process_turn(
        p1_team, 0, action_p1,
        p2_team, 0, action_p2
    )

    # 4. Imprimir resultados tal como los procesó tu motor
    for outcome in result.outcomes:
        atacante = charizard.name if outcome.actor == 1 else venusaur.name
        defensor = venusaur.name if outcome.actor == 1 else charizard.name
        
        print(f"\n> {atacante.upper()} atacó.")
        if not outcome.hit_success:
            print(f"  El ataque falló (Precisión).")
        else:
            print(f"  Ataque acertado. Multiplicador de tipo: x{outcome.type_multiplier}")
            print(f"  Daño causado: {outcome.damage_dealt}")
            if outcome.status_applied:
                print(f"  ¡{defensor} sufrió un estado de {outcome.status_applied.name}!")
        
        print(f"  -> HP actual de {defensor}: {outcome.target_hp_remaining}")

    if result.match_over:
        print(f"\n¡LA PARTIDA TERMINÓ! El Jugador {result.winner} ganó.")

if __name__ == "__main__":
    test_engine()