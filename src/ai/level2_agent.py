import random
from typing import Optional, List
from src.ai.base_agent import BaseAgent
from src.core.interfaces import Action, ActionType, BattleState
from src.core.damage_calc import calculate_damage
from src.entities.enums import PokemonType


class Level2Agent(BaseAgent):
    """Agente codicioso: elige el ataque que maximiza la 'Diferencia de HP'.

    Diferencia = (Mi_HP_Actual + Posible_Curacion) - (Su_HP_Actual - Posible_Daño)
    Si todas las diferencias son < 5, considerar hacer SWITCH a un pokémon vivo.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id)

    def _get_team_and_active(self, state: BattleState):
        if self.player_id == 1:
            return state.p1_team, state.p1_active_index, state.p2_team, state.p2_active_index
        else:
            return state.p2_team, state.p2_active_index, state.p1_team, state.p1_active_index

    def _safe_index(self, idx: int, seq) -> int:
        if not seq:
            return 0
        try:
            if idx is None:
                return 0
            if idx < 0 or idx >= len(seq):
                return 0
            return idx
        except Exception:
            return 0

    def _to_pokemon_types(self, types_list) -> List[PokemonType]:
        res: List[PokemonType] = []
        for t in types_list or []:
            if isinstance(t, PokemonType):
                res.append(t)
            else:
                key = str(t).upper()
                if key in PokemonType.__members__:
                    res.append(PokemonType[key])
        return res

    def _to_move_type(self, move) -> PokemonType:
        mt = getattr(move, 'move_type', None)
        if isinstance(mt, PokemonType):
            return mt
        key = str(mt).upper() if mt is not None else ''
        return PokemonType[key] if key in PokemonType.__members__ else PokemonType.NORMAL

    def get_action(self, state: BattleState) -> Action:
        team, active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)

        if not team:
            return Action(type=ActionType.MOVE, target_index=0)

        active_idx = self._safe_index(active_idx, team)
        opp_active_idx = self._safe_index(opp_active_idx, opp_team)

        active = team[active_idx]
        opp = opp_team[opp_active_idx] if opp_team else None

        # Prepare switch candidates
        switch_candidates = [i for i, p in enumerate(team) if getattr(p, 'current_hp', 0) > 0 and i != active_idx]

        # If we don't have move objects in the state, fallback to random Level1 behavior
        if not hasattr(active, 'moves'):
            if switch_candidates:
                return Action(type=ActionType.SWITCH, target_index=random.choice(switch_candidates))
            move_count = len(getattr(active, 'move_ids', [0, 1, 2, 3]))
            return Action(type=ActionType.MOVE, target_index=random.randrange(move_count))

        best_index: Optional[int] = None
        best_diff = -10**9

        defender_types = self._to_pokemon_types(getattr(opp, 'types', []))

        for i, move in enumerate(active.moves):
            pp = getattr(move, 'current_pp', None)
            if pp is not None and pp <= 0:
                continue

            move_type_enum = self._to_move_type(move)
            damage, _mult = calculate_damage(
                attacker_atk=getattr(active, 'attack', 0),
                defender_def=getattr(opp, 'defense', 1) if opp else 1,
                defender_spd=getattr(opp, 'speed', 0) if opp else 0,
                move_power=getattr(move, 'power', 0),
                move_type=move_type_enum,
                defender_types=defender_types
            )

            possible_cure = 0
            if getattr(move, 'drain', 0) > 0:
                possible_cure += int(damage * (move.drain / 100.0))
            if getattr(move, 'healing', 0) > 0:
                possible_cure += int(getattr(active, 'max_hp', 0) * (move.healing / 100.0))

            my_hp = getattr(active, 'current_hp', 0)
            opp_hp = getattr(opp, 'current_hp', 0) if opp else 0

            diff = (my_hp + possible_cure) - (opp_hp - damage)

            if diff > best_diff:
                best_diff = diff
                best_index = i

        # Si no encontramos movimientos válidos
        if best_index is None:
            if switch_candidates:
                return Action(type=ActionType.SWITCH, target_index=random.choice(switch_candidates))
            return Action(type=ActionType.MOVE, target_index=0)

        # Si la mejor diferencia es pobre, considerar cambiar
        if best_diff < -20 and switch_candidates:
            return Action(type=ActionType.SWITCH, target_index=random.choice(switch_candidates))

        return Action(type=ActionType.MOVE, target_index=best_index)
