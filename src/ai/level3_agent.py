import random
from typing import List

from src.ai.base_agent import BaseAgent
from src.ai.heuristics import evaluate_level3_state

from src.core.interfaces import (Action,ActionType,BattleState,PokemonState)

from src.core.battle_engine import process_turn

from src.entities.pokemon import Pokemon

from config import AI_LEVEL3_DEPTH, INF


class Level3Agent(BaseAgent):

    def __init__(self, player_id: int):
        super().__init__(player_id)
        self.turns_since_last_switch = 0

    # =========================================================
    # HELPERS
    # =========================================================

    def _get_team_and_active(self, state: BattleState):

        if self.player_id == 1:

            return (
                state.p1_team,
                state.p1_active_index,
                state.p2_team,
                state.p2_active_index
            )

        else:

            return (
                state.p2_team,
                state.p2_active_index,
                state.p1_team,
                state.p1_active_index
            )

    def _safe_index(self, idx: int, seq) -> int:

        if not seq:
            return 0

        if idx is None or idx < 0 or idx >= len(seq):
            return 0

        return idx

    def _is_match_over(self, state: BattleState) -> bool:

        p1_alive = any(p.current_hp > 0 for p in state.p1_team)

        p2_alive = any(p.current_hp > 0 for p in state.p2_team)

        return not (p1_alive and p2_alive)

    def _build_real_team(self, state_team):

        return [Pokemon.from_state(p) for p in state_team]

    # =========================================================
    # LEGAL ACTIONS
    # =========================================================

    def _get_legal_actions(
        self,
        team: List[PokemonState],
        active_idx: int,
        turns_since_switch: int
    ) -> List[Action]:

        actions = []

        if not team:
            return actions

        active_idx = self._safe_index(active_idx, team)

        active = team[active_idx]

        # =========================================
        # MOVIMIENTOS
        # =========================================

        if active.current_hp > 0 and getattr(active, "moves", []):

            for i, move in enumerate(active.moves):

                if getattr(move, "current_pp", 0) > 0:

                    actions.append(
                        Action(
                            type=ActionType.MOVE,
                            target_index=i
                        )
                    )

        # =========================================
        # CAMBIOS
        # =========================================

        switch_candidates = [

            i for i, p in enumerate(team)

            if p.current_hp > 0 and i != active_idx
        ]

        if active.current_hp <= 0:

            for c in switch_candidates:

                actions.append(
                    Action(
                        type=ActionType.SWITCH,
                        target_index=c
                    )
                )

        elif switch_candidates and turns_since_switch >= 2:

            for c in switch_candidates:

                actions.append(
                    Action(
                        type=ActionType.SWITCH,
                        target_index=c
                    )
                )

        # =========================================
        # FALLBACK
        # =========================================

        if not actions:

            actions.append(
                Action(
                    type=ActionType.MOVE,
                    target_index=0
                )
            )

        return actions

    # =========================================================
    # SIMULACIÓN REAL
    # =========================================================

    def _simulate_full_turn(
        self,
        state: BattleState,
        p1_action: Action,
        p2_action: Action
    ) -> BattleState:

        # =========================================
        # CONVERTIR A POKEMON REALES
        # =========================================

        p1_team = self._build_real_team(state.p1_team)

        p2_team = self._build_real_team(state.p2_team)

        p1_idx = state.p1_active_index

        p2_idx = state.p2_active_index

        # =========================================
        # PROCESAR TURNO REAL
        # =========================================

        _, new_p1_idx, new_p2_idx = process_turn(
            p1_team,
            p1_idx,
            p1_action,
            p2_team,
            p2_idx,
            p2_action
        )

        # =========================================
        # RECONSTRUIR STATE
        # =========================================

        new_state = BattleState(

            p1_team=[p.to_state() for p in p1_team],

            p2_team=[p.to_state() for p in p2_team],

            p1_active_index=new_p1_idx,

            p2_active_index=new_p2_idx,

            turn_number=state.turn_number + 1
        )

        return new_state

    # =========================================================
    # GET ACTION
    # =========================================================

    def get_action(self, state: BattleState) -> Action:

        team, active_idx, _, _ = self._get_team_and_active(state)

        self.turns_since_last_switch += 1

        legal_actions = self._get_legal_actions(
            team,
            active_idx,
            self.turns_since_last_switch
        )

        # =========================================
        # SOLO 1 ACCIÓN
        # =========================================

        if len(legal_actions) == 1:

            if legal_actions[0].type == ActionType.SWITCH:

                self.turns_since_last_switch = 0

            return legal_actions[0]

        # =========================================
        # MINIMAX
        # =========================================

        best_action = legal_actions[0]

        best_value = -INF

        alpha = -INF

        beta = INF

        random.shuffle(legal_actions)

        for my_action in legal_actions:

            value = self._min_value(
                state,
                AI_LEVEL3_DEPTH - 1,
                alpha,
                beta,
                my_action
            )

            if value > best_value:

                best_value = value

                best_action = my_action

            alpha = max(alpha, best_value)

        # =========================================
        # RESET SWITCH TIMER
        # =========================================

        if best_action.type == ActionType.SWITCH:

            self.turns_since_last_switch = 0

        return best_action

    # =========================================================
    # MAX
    # =========================================================

    def _max_value(
        self,
        state: BattleState,
        depth: int,
        alpha: float,
        beta: float
    ) -> float:

        if depth == 0 or self._is_match_over(state):

            return evaluate_level3_state(
                state,
                self.player_id
            )

        team, active_idx, _, _ = self._get_team_and_active(state)

        legal_actions = self._get_legal_actions(
            team,
            active_idx,
            2
        )

        v = -INF

        for my_action in legal_actions:

            value = self._min_value(
                state,
                depth - 1,
                alpha,
                beta,
                my_action
            )

            v = max(v, value)

            # =========================================
            # PODA BETA
            # =========================================

            if v >= beta:

                return v

            alpha = max(alpha, v)

        return v

    # =========================================================
    # MIN
    # =========================================================

    def _min_value(
        self,
        state: BattleState,
        depth: int,
        alpha: float,
        beta: float,
        my_action: Action
    ) -> float:

        if depth == 0 or self._is_match_over(state):

            return evaluate_level3_state(
                state,
                self.player_id
            )

        my_team, my_active_idx, opp_team, opp_active_idx = (
            self._get_team_and_active(state)
        )

        my_active = my_team[
            self._safe_index(my_active_idx, my_team)
        ]

        opp_actions = self._get_legal_actions(
            opp_team,
            opp_active_idx,
            2
        )

        v = INF

        for opp_action in opp_actions:

            # =========================================
            # SIMULACIÓN COMPLETA REAL
            # =========================================

            if self.player_id == 1:

                next_state = self._simulate_full_turn(
                    state,
                    my_action,
                    opp_action
                )

            else:

                next_state = self._simulate_full_turn(
                    state,
                    opp_action,
                    my_action
                )

            value = self._max_value(
                next_state,
                depth - 1,
                alpha,
                beta
            )

            v = min(v, value)

            # =========================================
            # PODA ALFA
            # =========================================

            if v <= alpha:

                return v

            beta = min(beta, v)

        return v
