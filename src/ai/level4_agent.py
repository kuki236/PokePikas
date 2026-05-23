from typing import List
from src.ai.base_agent import BaseAgent
from src.core.interfaces import Action, ActionType, BattleState, PokemonState
from src.core.damage_calc import calculate_damage, get_type_multiplier
from src.ai.heuristics import evaluate_level4_state
from src.entities.enums import PokemonType
from src.entities.pokemon import Pokemon
from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState
from config import AI_LEVEL4_DEPTH, INF 

DEPTH = AI_LEVEL4_DEPTH 

class Level4Agent(BaseAgent):
    def __init__(self, player_id: int):
        super().__init__(player_id)
        self.turns_since_last_switch = 0
        
        self.opp_turns_since_last_switch = 2  
        self.last_opp_active_name = None     

    def _get_team_and_active(self, state: BattleState):
        if self.player_id == 1: return state.p1_team, state.p1_active_index, state.p2_team, state.p2_active_index
        else: return state.p2_team, state.p2_active_index, state.p1_team, state.p1_active_index

    def _safe_index(self, idx: int, seq) -> int:
        if not seq: return 0
        if idx is None or idx < 0 or idx >= len(seq): return 0
        return idx

    def _build_real_team(self, state_team):
        return [Pokemon.from_state(p) for p in state_team]

    def _is_match_over(self, state: BattleState) -> bool:
        p1_alive = any(p.current_hp > 0 for p in state.p1_team)
        p2_alive = any(p.current_hp > 0 for p in state.p2_team)
        return not (p1_alive and p2_alive)

    def _get_smart_legal_actions(
            self,
            team: List[PokemonState],
            active_idx: int,
            opp: PokemonState,
            my_cooldown: int
        ) -> List[Action]:

            actions = []
            if not team:
                return actions

            active_idx = self._safe_index(active_idx, team)
            active = team[active_idx]

            opp_types = []
            if opp:
                opp_types = [
                    PokemonType[t.upper()]
                    for t in getattr(opp, 'types', [])
                    if t.upper() in PokemonType.__members__
                ]

            attack_actions = []

            if active.current_hp > 0 and getattr(active, 'moves', []):
                for i, move in enumerate(active.moves):
                    if getattr(move, 'current_pp', 0) <= 0:
                        continue

                    power = getattr(move, 'power', 0)
                    
                    m_type_str = getattr(move, 'move_type', 'NORMAL').upper()
                    m_enum = PokemonType[m_type_str] if m_type_str in PokemonType.__members__ else PokemonType.NORMAL
                    is_physical = getattr(move, 'category', 'PHYSICAL').upper() == 'PHYSICAL'
                    atk_key = 'attack' if is_physical else 'special_attack'
                    def_key = 'defense' if is_physical else 'special_defense'

                    atk_stat = active.attack if is_physical else active.special_attack
                    def_stat = opp.defense if is_physical else getattr(opp, 'special_defense', 1)

                    damage, type_mult = calculate_damage(
                        attacker_base_stat=atk_stat,
                        defender_base_stat=def_stat,
                        defender_spd=getattr(opp, 'speed', 0) if opp else 0,
                        move_power=power,
                        move_type=m_enum,
                        defender_types=opp_types,
                        attacker_stage=active.stat_stages.get(atk_key, 0),
                        defender_stage=getattr(opp, 'stat_stages', {}).get(def_key, 0) if opp else 0,
                        attacker_ailment=getattr(active, 'status_ailment', 'NONE')
                    )

                    possible_cure = 0
                    drain_val = getattr(move, 'drain', 0)
                    if drain_val > 0:
                        possible_cure += int(damage * (drain_val / 100.0))

                    healing_val = getattr(move, 'healing', 0)
                    if healing_val > 0:
                        mod_rest = 0.4 if getattr(move, 'name', '').lower() == 'rest' else 1.0
                        possible_cure += int(active.max_hp * (healing_val / 100.0) * mod_rest)

                    score = damage + possible_cure

                    if type_mult == 0.0:
                        score -= 5000 

                    if opp and damage >= opp.current_hp:
                        score += 5000 

                    if getattr(move, 'priority', 0) > 0 and opp and damage >= opp.current_hp:
                        score += 2000

                    attack_actions.append(
                        (Action(type=ActionType.MOVE, target_index=i), score)
                    )

            attack_actions.sort(key=lambda x: x[1], reverse=True)

            actions.extend([a[0] for a in attack_actions])

            switch_candidates = [
                i for i, p in enumerate(team)
                if p.current_hp > 0 and i != active_idx
            ]

            if active.current_hp <= 0:
                for c in switch_candidates:
                    actions.append(Action(type=ActionType.SWITCH, target_index=c))
            elif switch_candidates and my_cooldown >= 2:
                for c in switch_candidates:
                    actions.append(Action(type=ActionType.SWITCH, target_index=c))

            if not actions:
                actions.append(Action(type=ActionType.MOVE, target_index=0))

            return actions

    def _simulate_full_turn(
        self,
        state: BattleState,
        p1_action: Action,
        p2_action: Action
    ) -> BattleState:

        p1_team = self._build_real_team(state.p1_team)
        p2_team = self._build_real_team(state.p2_team)

        p1_idx = state.p1_active_index
        p2_idx = state.p2_active_index

        _, new_p1_idx, new_p2_idx = process_turn(
            p1_team,
            p1_idx,
            p1_action,
            p2_team,
            p2_idx,
            p2_action
        )

        new_state = BattleState(
            p1_team=[p.to_state() for p in p1_team],
            p2_team=[p.to_state() for p in p2_team],
            p1_active_index=new_p1_idx,
            p2_active_index=new_p2_idx,
            turn_number=state.turn_number + 1
        )

        return new_state

    def get_action(self, state: BattleState) -> Action:
            team, active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
            
            self.turns_since_last_switch += 1
            opp = opp_team[self._safe_index(opp_active_idx, opp_team)] if opp_team else None

            if opp:
                current_opp_name = getattr(opp, 'name', None)
                if self.last_opp_active_name is not None and current_opp_name != self.last_opp_active_name:
                    self.opp_turns_since_last_switch = 0
                else:
                    self.opp_turns_since_last_switch += 1
                self.last_opp_active_name = current_opp_name

            legal_actions = self._get_smart_legal_actions(team, active_idx, opp, self.turns_since_last_switch)
            
            if len(legal_actions) == 1:
                if legal_actions[0].type == ActionType.SWITCH: self.turns_since_last_switch = 0
                return legal_actions[0]

            best_action = legal_actions[0]
            best_value = -INF
            alpha = -INF
            beta = INF

            for my_action in legal_actions:
                next_my_cooldown = 0 if my_action.type == ActionType.SWITCH else self.turns_since_last_switch + 1
                
                value = self._min_value(
                    state, 
                    DEPTH - 1, 
                    alpha, 
                    beta, 
                    my_action, 
                    next_my_cooldown, 
                    self.opp_turns_since_last_switch  
                )
                
                if value > best_value:
                    best_value = value
                    best_action = my_action
                alpha = max(alpha, best_value)

            if best_action.type == ActionType.SWITCH:
                self.turns_since_last_switch = 0
                
            return best_action

    def _max_value(
        self,
        state: BattleState,
        depth: int,
        alpha: float,
        beta: float,
        my_cooldown: int,
        opp_cooldown: int
    ) -> float:

        if depth == 0 or self._is_match_over(state):
            return evaluate_level4_state(state, self.player_id)

        team, active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)

        opp = (
            opp_team[self._safe_index(opp_active_idx, opp_team)]
            if opp_team else None
        )

        legal_actions = self._get_smart_legal_actions(
            team,
            active_idx,
            opp,
            my_cooldown
        )

        v = -INF

        for my_action in legal_actions:

            next_my_cd = (
                0
                if my_action.type == ActionType.SWITCH
                else my_cooldown + 1
            )

            value = self._min_value(
                state,
                depth - 1,
                alpha,
                beta,
                my_action,
                next_my_cd,
                opp_cooldown + 1
            )

            v = max(v, value)

            if v >= beta:
                return v

            alpha = max(alpha, v)

        return v

    def _min_value(
        self,
        state: BattleState,
        depth: int,
        alpha: float,
        beta: float,
        my_action: Action,
        my_cooldown: int,
        opp_cooldown: int
    ) -> float:

        if depth == 0 or self._is_match_over(state):
            return evaluate_level4_state(state, self.player_id)

        my_team, my_active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)

        my_active = my_team[self._safe_index(my_active_idx, my_team)]

        opp_actions = self._get_smart_legal_actions(
            opp_team,
            opp_active_idx,
            my_active,
            opp_cooldown
        )

        v = INF

        for opp_action in opp_actions:

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

            next_opp_cd = (
                0 if opp_action.type == ActionType.SWITCH
                else opp_cooldown + 1
            )

            value = self._max_value(
                next_state,
                depth,
                alpha,
                beta,
                my_cooldown,
                next_opp_cd
            )

            v = min(v, value)

            if v <= alpha:
                return v

            beta = min(beta, v)

        return v