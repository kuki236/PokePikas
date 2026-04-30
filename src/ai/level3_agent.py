from src.core.interfaces import Agent, BattleState, Action, ActionType
import random

class Level3Agent(Agent):
    def __init__(self, player_id: int):
        super().__init__(player_id)
        print(f"Level3Agent (Player {player_id}) initialized.")

    def get_action(self, state: BattleState) -> Action:
        # Implementación simple de placeholder para Level3Agent
        # Este agente simplemente elige un movimiento al azar, como el Level1Agent
        
        # Obtener el Pokémon activo del agente
        active_pokemon = state.get_active_pokemon(self.player_id)
        
        # Si el Pokémon está debilitado, intentar cambiar
        if active_pokemon.current_hp <= 0:
            available_switches = [
                idx for idx, pkm in enumerate(state.get_team(self.player_id))
                if pkm.current_hp > 0 and idx != state.get_active_pokemon_index(self.player_id)
            ]
            if available_switches:
                return Action(ActionType.SWITCH, random.choice(available_switches))
            # Si no hay Pokémon para cambiar, no se puede hacer nada
            return Action(ActionType.FORFEIT) # O un movimiento si es el último Pokémon y está debilitado

        # Elegir un movimiento al azar que tenga PP
        available_moves = [
            idx for idx, move in enumerate(active_pokemon.moves)
            if move.current_pp > 0
        ]
        if available_moves:
            return Action(ActionType.MOVE, random.choice(available_moves))
        
        # Si no hay movimientos con PP, intentar cambiar si es posible
        available_switches = [
            idx for idx, pkm in enumerate(state.get_team(self.player_id))
            if pkm.current_hp > 0 and idx != state.get_active_pokemon_index(self.player_id)
        ]
        if available_switches:
            return Action(ActionType.SWITCH, random.choice(available_switches))
            
        # Si no hay movimientos ni cambios posibles, rendirse
        return Action(ActionType.FORFEIT)
