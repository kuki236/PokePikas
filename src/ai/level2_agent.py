import random
from typing import Optional
from src.ai.base_agent import BaseAgent
from src.core.interfaces import Action, ActionType, BattleState

class Level2Agent(BaseAgent):
    def __init__(self, player_id: int):
        super().__init__(player_id)
        self.turns_since_last_switch = 0

    def _get_team_and_active(self, state: BattleState):
        if self.player_id == 1:
            return state.p1_team, state.p1_active_index, state.p2_team, state.p2_active_index
        else:
            return state.p2_team, state.p2_active_index, state.p1_team, state.p1_active_index

    def _safe_index(self, idx: int, seq) -> int:
        if not seq: return 0
        if idx is None or idx < 0 or idx >= len(seq): return 0
        return idx

    def get_action(self, state: BattleState) -> Action:
        team, active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
        if not team: return Action(type=ActionType.MOVE, target_index=0)

        active = team[self._safe_index(active_idx, team)]
        opp = opp_team[self._safe_index(opp_active_idx, opp_team)] if opp_team else None
        
        switch_candidates = [i for i, p in enumerate(team) if getattr(p, 'current_hp', 0) > 0 and i != active_idx]
        self.turns_since_last_switch += 1
        if getattr(active, 'current_hp', 0) <= 0 and switch_candidates:
            self.turns_since_last_switch = 0
            return Action(type=ActionType.SWITCH, target_index=random.choice(switch_candidates))

        best_index: Optional[int] = None
        best_diff = -10**9

        for i, move in enumerate(active.moves):
            if getattr(move, 'current_pp', 0) <= 0: continue

            damage = getattr(move, 'power', 0)
            
            my_hp = active.current_hp
            opp_hp = opp.current_hp if opp else 0
            
            diff = my_hp - (opp_hp - damage)
            
            if diff > best_diff:
                best_diff = diff
                best_index = i

        if best_index is None:
            return Action(type=ActionType.MOVE, target_index=0)

        return Action(type=ActionType.MOVE, target_index=best_index)