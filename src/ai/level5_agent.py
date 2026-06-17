import json
import os
from typing import List

from src.ai.base_agent import BaseAgent
from src.core.interfaces import Action, ActionType, BattleState, PokemonState
from src.core.damage_calc import calculate_damage
from src.entities.enums import PokemonType
from src.entities.pokemon import Pokemon
from src.core.battle_engine import process_turn
from src.ai.heuristics import evaluate_level4_state, L4_WEIGHTS
from config import AI_LEVEL4_DEPTH, INF

# Misma profundidad que L4: la inteligencia superior de L5 viene de los pesos,
# no de buscar mas profundo.
DEPTH = AI_LEVEL4_DEPTH


class Level5Agent(BaseAgent):
    """Agente Minimax con la MISMA arquitectura que L4 pero con pesos evolucionados por AG.

    Diferencia respecto a L4: en lugar de los pesos hand-tuned L4_WEIGHTS,
    usa los 5 pesos (hp, alive, type, speed, status) cargados desde
    data/ai/level5_weights.json, optimizados por Algoritmo Genetico.
    Si el archivo no existe o es invalido, usa los L4_WEIGHTS como fallback
    (en cuyo caso se comporta identicamente a L4).
    """

    def __init__(self, player_id: int, weights_path: str = None):
        """Inicializa el agente cargando los pesos evolucionados por AG.

        Args:
            player_id (int): Identificador del jugador (1 o 2).
            weights_path (str, optional): Ruta al JSON de pesos.
                Si es None, usa data/ai/level5_weights.json por defecto.
        """
        super().__init__(player_id)
        self.turns_since_last_switch = 0
        self.opp_turns_since_last_switch = 2
        self.last_opp_active_name = None

        if weights_path is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            weights_path = os.path.join(root_dir, 'data', 'ai', 'level5_weights.json')

        self.weights = self._load_weights(weights_path)

    def _load_weights(self, path: str) -> dict:
        """Carga los pesos evolucionados del AG desde un JSON.

        Args:
            path (str): Ruta al archivo JSON con la clave 'weights'.

        Returns:
            dict: {nombre_peso: valor} con exactamente las 5 claves de L4_WEIGHTS.
                Si el archivo no existe, esta corrupto, o le faltan claves,
                devuelve una copia de L4_WEIGHTS (comportamiento equivalente a L4).
        """
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        raw = data.get('weights', {})
                        if isinstance(raw, dict) and all(k in raw for k in L4_WEIGHTS):
                            return {k: float(raw[k]) for k in L4_WEIGHTS}
        except Exception:
            pass
        return dict(L4_WEIGHTS)

    def _get_team_and_active(self, state: BattleState):
        """Devuelve (mi_equipo, mi_activo, equipo_rival, activo_rival) desde la perspectiva del agente."""
        if self.player_id == 1:
            return state.p1_team, state.p1_active_index, state.p2_team, state.p2_active_index
        return state.p2_team, state.p2_active_index, state.p1_team, state.p1_active_index

    def _safe_index(self, idx: int, seq) -> int:
        """Devuelve un indice valido dentro de `seq`, o 0 si es invalido/vacio."""
        if not seq or idx is None or idx < 0 or idx >= len(seq):
            return 0
        return idx

    def _build_real_team(self, state_team):
        """Reconstruye instancias de Pokemon a partir de PokemonState."""
        return [Pokemon.from_state(p) for p in state_team]

    def _is_match_over(self, state: BattleState) -> bool:
        """Indica si la batalla ha finalizado (algun equipo sin Pokemon con HP > 0)."""
        p1_alive = any(p.current_hp > 0 for p in state.p1_team)
        p2_alive = any(p.current_hp > 0 for p in state.p2_team)
        return not (p1_alive and p2_alive)

    def _evaluate_state(self, state: BattleState) -> float:
        """Evalua el estado con los 5 pesos evolucionados por AG.

        Reutiliza la misma funcion que L4 (`evaluate_level4_state`), pero
        inyecta los pesos propios del agente en lugar de los hard-tuned.

        Args:
            state (BattleState): Estado actual de la batalla.

        Returns:
            float: +/- 10000.0 en estados terminales, valor ponderado en [-1, 1] aprox.
        """
        return evaluate_level4_state(state, self.player_id, self.weights)

    def _get_smart_legal_actions(
            self,
            team: List[PokemonState],
            active_idx: int,
            opp: PokemonState,
            my_cooldown: int
        ) -> List[Action]:
        """Genera y ordena acciones legales con bonificaciones tacticas (identicas a L4).

        Aplica Knowledge-Based Move Ordering pre-evaluando cada movimiento
        con dano esperado, cure, KO bonus (5000), inmunidad (5000) y prioridad (2000).

        Args:
            team (List[PokemonState]): Equipo del agente.
            active_idx (int): Indice del Pokemon activo.
            opp (PokemonState): Estado del Pokemon rival activo.
            my_cooldown (int): Turnos desde el ultimo cambio propio.

        Returns:
            List[Action]: Acciones legales ordenadas de mayor a menor utilidad.
        """
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

        if active.current_hp > 0 and getattr(active, "moves", []):
            for i, move in enumerate(active.moves):
                if getattr(move, "current_pp", 0) <= 0:
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
                    mod_rest = 0.4 if getattr(move, 'name', '').lower() == 'descanso' else 1.0
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
        """Simula un turno completo y devuelve el nuevo BattleState."""
        p1_team = self._build_real_team(state.p1_team)
        p2_team = self._build_real_team(state.p2_team)

        _, new_p1_idx, new_p2_idx = process_turn(
            p1_team, state.p1_active_index, p1_action,
            p2_team, state.p2_active_index, p2_action
        )

        return BattleState(
            p1_team=[p.to_state() for p in p1_team],
            p2_team=[p.to_state() for p in p2_team],
            p1_active_index=new_p1_idx,
            p2_active_index=new_p2_idx,
            turn_number=state.turn_number + 1
        )

    def _max_value(
        self,
        state: BattleState,
        depth: int,
        alpha: float,
        beta: float,
        my_cd: int,
        opp_cd: int
    ) -> float:
        """Nodo MAX del Minimax con poda alfa-beta."""
        if depth == 0 or self._is_match_over(state):
            return self._evaluate_state(state)

        team, active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
        opp = opp_team[self._safe_index(opp_active_idx, opp_team)] if opp_team else None

        v = -INF
        for my_action in self._get_smart_legal_actions(team, active_idx, opp, my_cd):
            next_my_cd = 0 if my_action.type == ActionType.SWITCH else my_cd + 1
            v = max(v, self._min_value(state, depth - 1, alpha, beta, my_action, next_my_cd, opp_cd + 1))
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
        my_cd: int,
        opp_cd: int
    ) -> float:
        """Nodo MIN del Minimax con poda alfa-beta."""
        if depth == 0 or self._is_match_over(state):
            return self._evaluate_state(state)

        my_team, my_active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
        my_active = my_team[self._safe_index(my_active_idx, my_team)]

        v = INF
        for opp_action in self._get_smart_legal_actions(opp_team, opp_active_idx, my_active, opp_cd):
            next_state = (
                self._simulate_full_turn(state, my_action, opp_action)
                if self.player_id == 1
                else self._simulate_full_turn(state, opp_action, my_action)
            )
            next_opp_cd = 0 if opp_action.type == ActionType.SWITCH else opp_cd + 1
            v = min(v, self._max_value(next_state, depth, alpha, beta, my_cd, next_opp_cd))
            if v <= alpha:
                return v
            beta = min(beta, v)
        return v

    def get_action(self, state: BattleState) -> Action:
        """Obtiene la accion optima para el estado actual de la batalla.

        Args:
            state (BattleState): Estado actual de la batalla.

        Returns:
            Action: Mejor accion segun Minimax con pesos evolucionados por AG.
        """
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
            if legal_actions[0].type == ActionType.SWITCH:
                self.turns_since_last_switch = 0
            return legal_actions[0]

        best_action, best_value, alpha, beta = legal_actions[0], -INF, -INF, INF

        for my_action in legal_actions:
            next_my_cooldown = 0 if my_action.type == ActionType.SWITCH else self.turns_since_last_switch + 1
            value = self._min_value(
                state, DEPTH - 1, alpha, beta,
                my_action, next_my_cooldown, self.opp_turns_since_last_switch
            )
            if value > best_value:
                best_value, best_action = value, my_action
            alpha = max(alpha, best_value)

        if best_action.type == ActionType.SWITCH:
            self.turns_since_last_switch = 0

        return best_action