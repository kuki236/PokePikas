import copy
import random
from typing import List
from src.ai.base_agent import BaseAgent
from src.core.interfaces import Action, ActionType, BattleState, PokemonState
from src.core.damage_calc import calculate_damage, get_type_multiplier
from src.ai.heuristics import evaluate_level4_state
from src.entities.enums import PokemonType
from config import AI_LEVEL4_DEPTH, INF 

DEPTH = AI_LEVEL4_DEPTH 

class Level4Agent(BaseAgent):
    def __init__(self, player_id: int):
        super().__init__(player_id)
        self.turns_since_last_switch = 0

    def _get_team_and_active(self, state: BattleState):
        if self.player_id == 1: return state.p1_team, state.p1_active_index, state.p2_team, state.p2_active_index
        else: return state.p2_team, state.p2_active_index, state.p1_team, state.p1_active_index

    def _safe_index(self, idx: int, seq) -> int:
        if not seq: return 0
        if idx is None or idx < 0 or idx >= len(seq): return 0
        return idx

    def _is_match_over(self, state: BattleState) -> bool:
        p1_alive = any(p.current_hp > 0 for p in state.p1_team)
        p2_alive = any(p.current_hp > 0 for p in state.p2_team)
        return not (p1_alive and p2_alive)

    def _get_smart_legal_actions(self, team: List[PokemonState], active_idx: int, opp: PokemonState, my_cooldown: int) -> List[Action]:
        """Move Ordering con daño estimado real y Switches libres."""
        actions = []
        if not team: return actions
        
        active_idx = self._safe_index(active_idx, team)
        active = team[active_idx]
        
        opp_types = []
        if opp:
            opp_types = [PokemonType[t.upper()] for t in getattr(opp, 'types', []) if t.upper() in PokemonType.__members__]

        attack_actions = []
        if active.current_hp > 0 and getattr(active, 'moves', []):
            for i, move in enumerate(active.moves):
                if getattr(move, 'current_pp', 0) > 0:
                    power = getattr(move, 'power', 0)
                    score = power
                    if power > 0 and opp_types:
                        m_type_str = getattr(move, 'move_type', 'NORMAL').upper()
                        m_enum = PokemonType[m_type_str] if m_type_str in PokemonType.__members__ else PokemonType.NORMAL
                        mult = get_type_multiplier(m_enum, opp_types)
                        score = power * mult  # Daño relativo real
                        
                    attack_actions.append((Action(type=ActionType.MOVE, target_index=i), score))
            
            attack_actions.sort(key=lambda x: x[1], reverse=True)
            actions.extend([a[0] for a in attack_actions])

        switch_candidates = [i for i, p in enumerate(team) if p.current_hp > 0 and i != active_idx]
        
        if active.current_hp <= 0:
            for c in switch_candidates: actions.append(Action(type=ActionType.SWITCH, target_index=c))
        elif switch_candidates and my_cooldown >= 2:
            for c in switch_candidates: actions.append(Action(type=ActionType.SWITCH, target_index=c))

        if not actions: actions.append(Action(type=ActionType.MOVE, target_index=0))
        return actions
    def _simulate_deterministic_transition(self, state: BattleState, action: Action, is_p1: bool) -> BattleState:

        sim_state = copy.deepcopy(state)

        if is_p1:
            my_team, my_idx = sim_state.p1_team, sim_state.p1_active_index
            opp_team, opp_idx = sim_state.p2_team, sim_state.p2_active_index
        else:
            my_team, my_idx = sim_state.p2_team, sim_state.p2_active_index
            opp_team, opp_idx = sim_state.p1_team, sim_state.p1_active_index

        active = my_team[self._safe_index(my_idx, my_team)]
        opp = opp_team[self._safe_index(opp_idx, opp_team)]

        # =========================
        # SWITCH
        # =========================
        if action.type == ActionType.SWITCH:
            if is_p1:
                sim_state.p1_active_index = action.target_index
            else:
                sim_state.p2_active_index = action.target_index

            return sim_state

        # =========================
        # MOVE
        # =========================
        if action.type == ActionType.MOVE and opp.current_hp > 0 and active.current_hp > 0:

            move = active.moves[self._safe_index(action.target_index, active.moves)]

            # =========================================
            # STATUS CHECKS (NUEVO)
            # =========================================
            can_attack = True
            status_obj = getattr(active, 'status_ailment', 'NONE')
            status = (
                status_obj.name
                if hasattr(status_obj, 'name')
                else str(status_obj).upper()
            )

            if status in ['SLEEP', 'FREEZE']:
                can_attack = False

            elif status == 'PARALYSIS':
                if random.randint(1, 100) <= 25:
                    can_attack = False

            if not can_attack:
                return sim_state

            # =========================================
            # TYPES
            # =========================================
            opp_types = [
                PokemonType[t.upper()]
                for t in getattr(opp, 'types', [])
                if t.upper() in PokemonType.__members__
            ]

            m_type_str = getattr(move, 'move_type', 'NORMAL').upper()

            move_type_enum = (
                PokemonType[m_type_str]
                if m_type_str in PokemonType.__members__
                else PokemonType.NORMAL
            )

            # =========================================
            # PHYSICAL / SPECIAL
            # =========================================
            is_phys = getattr(move, 'category', 'PHYSICAL').upper() == 'PHYSICAL'

            atk_key = 'attack' if is_phys else 'special_attack'
            def_key = 'defense' if is_phys else 'special_defense'

            atk_stat = active.attack if is_phys else active.special_attack
            def_stat = opp.defense if is_phys else opp.special_defense

            # =========================================
            # DAMAGE CALC
            # =========================================
            damage, type_mult = calculate_damage(
                attacker_base_stat=atk_stat,
                defender_base_stat=def_stat,
                defender_spd=opp.speed,
                move_power=getattr(move, 'power', 0),
                move_type=move_type_enum,
                defender_types=opp_types,
                attacker_stage=active.stat_stages.get(atk_key, 0),
                defender_stage=opp.stat_stages.get(def_key, 0),

                # =====================================
                # NUEVO: BURN REDUCE ATAQUE
                # =====================================
                attacker_ailment=getattr(active, 'status_ailment', 'NONE')
            )

            # =========================================
            # APPLY DAMAGE
            # =========================================
            opp.current_hp = max(0, opp.current_hp - damage)

            move.current_pp = max(
                0,
                getattr(move, 'current_pp', 1) - 1
            )

            # =========================================
            # DRAIN
            # =========================================
            drain_val = getattr(move, 'drain', 0)

            if drain_val > 0 and damage > 0:
                cura_drenaje = int(damage * (drain_val / 100.0))

                active.current_hp = min(
                    active.max_hp,
                    active.current_hp + cura_drenaje
                )

            # =========================================
            # HEALING
            # =========================================
            healing_val = getattr(move, 'healing', 0)

            if healing_val > 0:

                m_name = getattr(move, 'name', '').lower()

                mod_rest = 0.4 if m_name == "rest" else 1.0

                cura_directa = int(
                    active.max_hp *
                    (healing_val / 100.0) *
                    mod_rest
                )

                active.current_hp = min(
                    active.max_hp,
                    active.current_hp + cura_directa
                )

        # =============================================
        # RESIDUAL DAMAGE (NUEVO)
        # =============================================
        for p in [active, opp]:

            status_obj = getattr(p, 'status_ailment', 'NONE')

            status = (
                status_obj.name
                if hasattr(status_obj, 'name')
                else str(status_obj).upper()
            )

            if status in ['BURN', 'POISON']:

                residual = max(1, p.max_hp // 8)

                p.current_hp = max(
                    0,
                    p.current_hp - residual
                )

        return sim_state

    # MINIMAX 
    def get_action(self, state: BattleState) -> Action:
        team, active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
        self.turns_since_last_switch += 1
        opp = opp_team[self._safe_index(opp_active_idx, opp_team)] if opp_team else None
        
        legal_actions = self._get_smart_legal_actions(team, active_idx, opp, self.turns_since_last_switch)
        
        if len(legal_actions) == 1:
            if legal_actions[0].type == ActionType.SWITCH: self.turns_since_last_switch = 0
            return legal_actions[0]

        best_action = legal_actions[0]
        best_value = -INF
        alpha = -INF
        beta = INF

        for my_action in legal_actions:
            next_state = self._simulate_deterministic_transition(state, my_action, is_p1=(self.player_id == 1))
            next_my_cooldown = 0 if my_action.type == ActionType.SWITCH else self.turns_since_last_switch + 1
            next_opp_cooldown = 2 
            
            value = self._min_value(next_state, DEPTH - 1, alpha, beta, next_my_cooldown, next_opp_cooldown)
            
            if value > best_value:
                best_value = value
                best_action = my_action
            alpha = max(alpha, best_value)

        if best_action.type == ActionType.SWITCH:
            self.turns_since_last_switch = 0
            
        return best_action

    def _max_value(self, state: BattleState, depth: int, alpha: float, beta: float, my_cooldown: int, opp_cooldown: int) -> float:
        if depth == 0 or self._is_match_over(state):
            return evaluate_level4_state(state, self.player_id)

        team, active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
        opp = opp_team[self._safe_index(opp_active_idx, opp_team)] if opp_team else None
        
        legal_actions = self._get_smart_legal_actions(team, active_idx, opp, my_cooldown)

        v = -INF
        for my_action in legal_actions:
            next_state = self._simulate_deterministic_transition(state, my_action, is_p1=(self.player_id == 1))
            next_my_cd = 0 if my_action.type == ActionType.SWITCH else my_cooldown + 1
            
            v = max(v, self._min_value(next_state, depth - 1, alpha, beta, next_my_cd, opp_cooldown + 1))
            if v >= beta: return v
            alpha = max(alpha, v)
        return v

    def _min_value(self, state: BattleState, depth: int, alpha: float, beta: float, my_cooldown: int, opp_cooldown: int) -> float:
        if depth == 0 or self._is_match_over(state):
            return evaluate_level4_state(state, self.player_id)

        my_team, my_active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
        my_active = my_team[self._safe_index(my_active_idx, my_team)] if my_team else None
        
        opp_actions = self._get_smart_legal_actions(opp_team, opp_active_idx, my_active, opp_cooldown)

        v = INF
        for opp_action in opp_actions:
            next_state = self._simulate_deterministic_transition(state, opp_action, is_p1=(self.player_id != 1))
            next_opp_cd = 0 if opp_action.type == ActionType.SWITCH else opp_cooldown + 1
            
            v = min(v, self._max_value(next_state, depth - 1, alpha, beta, my_cooldown + 1, next_opp_cd))
            if v <= alpha: return v
            beta = min(beta, v)
        return v