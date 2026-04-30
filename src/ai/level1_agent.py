import random
from src.ai.base_agent import BaseAgent
from src.core.interfaces import Action, ActionType, BattleState


class Level1Agent(BaseAgent):
    """
    Agente Nivel 1: baseline estrictamente aleatorio.

    Reglas:
    - Elige uniformemente entre acciones legales.
    - Puede atacar o cambiar de Pokémon.
    - Si ataca, solo usa movimientos válidos (preferentemente con PP > 0).
    - Si cambia, solo elige Pokémon vivos y distintos al activo.
    - Soporta equipos de tamaño variable (3v3, 4v4, etc.).
    """

    def __init__(self, player_id: int):
        super().__init__(player_id)

    def _get_team_and_active(self, state: BattleState):
        if self.player_id == 1:
            return state.p1_team, state.p1_active_index
        return state.p2_team, state.p2_active_index

    def _get_valid_switches(self, team, active_idx):
        valid_switches = []
        for i, p in enumerate(team):
            if i == active_idx:
                continue
            if getattr(p, "current_hp", 0) > 0:
                valid_switches.append(i)
        return valid_switches

    def _get_valid_moves(self, active):
        moves = getattr(active, "moves", []) or []
        valid_moves = []

        for i, move in enumerate(moves):
            pp = getattr(move, "current_pp", None)
            if pp is None or pp > 0:
                valid_moves.append(i)

        # Fallback defensivo: si hay movimientos pero todos salen inválidos
        # por datos incompletos, permitir cualquiera de los slots existentes.
        if not valid_moves and moves:
            valid_moves = list(range(len(moves)))

        return valid_moves

    def get_action(self, state: BattleState) -> Action:
        team, active_idx = self._get_team_and_active(state)

        if not team:
            return Action(type=ActionType.MOVE, target_index=0)

        if active_idx < 0 or active_idx >= len(team):
            active_idx = 0

        active = team[active_idx]

        valid_switches = self._get_valid_switches(team, active_idx)
        valid_moves = self._get_valid_moves(active)

        legal_actions = []

        for move_idx in valid_moves:
            legal_actions.append(Action(type=ActionType.MOVE, target_index=move_idx))

        for switch_idx in valid_switches:
            legal_actions.append(Action(type=ActionType.SWITCH, target_index=switch_idx))

        # Si el Pokémon activo está debilitado, priorizar cambio si existe.
        if getattr(active, "current_hp", 0) <= 0 and valid_switches:
            return Action(type=ActionType.SWITCH, target_index=random.choice(valid_switches))

        # Si no hay acciones legales reales, fallback mínimo.
        if not legal_actions:
            if valid_switches:
                return Action(type=ActionType.SWITCH, target_index=random.choice(valid_switches))
            return Action(type=ActionType.MOVE, target_index=0)

        return random.choice(legal_actions)