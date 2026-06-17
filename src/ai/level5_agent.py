import json
import os
from typing import List
from src.ai.base_agent import BaseAgent
from src.core.interfaces import Action, ActionType, BattleState, PokemonState
from src.core.damage_calc import calculate_damage
from src.entities.enums import PokemonType
from src.entities.pokemon import Pokemon
from src.core.battle_engine import process_turn
from config import AI_LEVEL4_DEPTH, INF 

# La IA 5 usa la misma profundidad computacional que la 4, pero es más inteligente.
DEPTH = AI_LEVEL4_DEPTH 

class Level5Agent(BaseAgent):
    def __init__(self, player_id: int, weights_path: str = None):
        """
        Inicializa un objeto de jugador con un identificador y cargando pesos de entrenamiento.

        Args:
            player_id (int): Identificador único del jugador.
            weights_path (str, optional): Ruta al archivo de pesos de entrenamiento. Defaults a None.

        Returns:
            None

        Raises:
            Exception: Si no se puede cargar el archivo de pesos en la ruta especificada.
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
        """Carga los pesos evolucionados. Si no existen, usa valores neutrales por defecto."""
        default_weights = {
            'hp_balance': 1.0, 'alive_balance': 1.0, 'type_pressure': 1.0, 
            'speed_pressure': 1.0, 'status_pressure': 1.0, 'move_pressure': 1.0, 
            'switch_pressure': 1.0, 'ko_pressure': 1.0
        }
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('weights', default_weights)
        except Exception:
            pass
        return default_weights

    def _get_team_and_active(self, state: BattleState):
        """Devuelve los equipos e indices activos desde la perspectiva del agente.

        Args:
            state (BattleState): Estado actual de la batalla.

        Returns:
            tuple: (mi_equipo, mi_activo, equipo_rival, activo_rival).
        """
        if self.player_id == 1: return state.p1_team, state.p1_active_index, state.p2_team, state.p2_active_index
        else: return state.p2_team, state.p2_active_index, state.p1_team, state.p1_active_index

    def _safe_index(self, idx: int, seq) -> int:
        """Devuelve un indice valido dentro de una secuencia, o 0 si es invalida.

        Args:
            idx (int): Indice propuesto.
            seq: Secuencia sobre la que se indexara.

        Returns:
            int: Indice seguro (0..len(seq)-1).
        """
        if not seq or idx is None or idx < 0 or idx >= len(seq): return 0
        return idx

    def _build_real_team(self, state_team):
        """Reconstruye instancias de Pokemon a partir de sus estados serializados.

        Args:
            state_team (list): Lista de PokemonState.

        Returns:
            list: Lista de Pokemon listos para usar en el motor.
        """
        return [Pokemon.from_state(p) for p in state_team]

    def _is_match_over(self, state: BattleState) -> bool:
        """Indica si la batalla ha finalizado.

        Args:
            state (BattleState): Estado actual de la batalla.

        Returns:
            bool: True si algun equipo no tiene Pokemon con HP > 0.
        """
        p1_alive = any(p.current_hp > 0 for p in state.p1_team)
        p2_alive = any(p.current_hp > 0 for p in state.p2_team)
        return not (p1_alive and p2_alive)

    def _evaluate_state(self, state: BattleState) -> float:
        """Heurística final dinamizada por el Algoritmo Genético."""
        my_team, _, opp_team, _ = self._get_team_and_active(state)
        
        my_hp = sum(max(0, p.current_hp) / max(1, p.max_hp) for p in my_team)
        opp_hp = sum(max(0, p.current_hp) / max(1, p.max_hp) for p in opp_team)
        
        my_alive = sum(1 for p in my_team if p.current_hp > 0)
        opp_alive = sum(1 for p in opp_team if p.current_hp > 0)
        
        # Se aplican los genes de balance descubiertos por la evolución
        score = (my_hp - opp_hp) * 1000 * self.weights.get('hp_balance', 1.0)
        score += (my_alive - opp_alive) * 2000 * self.weights.get('alive_balance', 1.0)
        
        if opp_alive == 0:
            score += 10000 * self.weights.get('ko_pressure', 1.0)
            
        return score

    def _get_smart_legal_actions(self, team: List[PokemonState], active_idx: int, opp: PokemonState, my_cooldown: int) -> List[Action]:
        """
        Descripción breve:
         Obtiene las acciones legales inteligentes para un equipo de Pokémon.

        Args:
            team (List[PokemonState]): El equipo de Pokémon.
            active_idx (int): El índice del Pokémon activo en el equipo.
            opp (PokemonState): El oponente.
            my_cooldown (int): El tiempo de enfriamiento de las acciones.

        Returns:
            List[Action]: Una lista de acciones legales inteligentes.

        Raises:
            No se lanzan excepciones explícitas. Sin embargo, es posible que se produzcan excepciones si los parámetros no son del tipo correcto o si hay un error en la lógica de la función.
        """
        actions = []
        if not team: return actions

        active_idx = self._safe_index(active_idx, team)
        active = team[active_idx]
        opp_types = [PokemonType[t.upper()] for t in getattr(opp, 'types', []) if t.upper() in PokemonType.__members__] if opp else []

        attack_actions = []

        if active.current_hp > 0 and getattr(active, 'moves', []):
            for i, move in enumerate(active.moves):
                if getattr(move, 'current_pp', 0) <= 0: continue

                power = getattr(move, 'power', 0)
                m_type_str = getattr(move, 'move_type', 'NORMAL').upper()
                m_enum = PokemonType[m_type_str] if m_type_str in PokemonType.__members__ else PokemonType.NORMAL
                is_physical = getattr(move, 'category', 'PHYSICAL').upper() == 'PHYSICAL'
                
                atk_key = 'attack' if is_physical else 'special_attack'
                def_key = 'defense' if is_physical else 'special_defense'

                atk_stat = active.attack if is_physical else active.special_attack
                def_stat = opp.defense if is_physical else getattr(opp, 'special_defense', 1)

                damage, type_mult = calculate_damage(
                    attacker_base_stat=atk_stat, defender_base_stat=def_stat,
                    defender_spd=getattr(opp, 'speed', 0) if opp else 0,
                    move_power=power, move_type=m_enum, defender_types=opp_types,
                    attacker_stage=active.stat_stages.get(atk_key, 0),
                    defender_stage=getattr(opp, 'stat_stages', {}).get(def_key, 0) if opp else 0,
                    attacker_ailment=getattr(active, 'status_ailment', 'NONE')
                )

                possible_cure = 0
                if getattr(move, 'drain', 0) > 0:
                    possible_cure += int(damage * (getattr(move, 'drain', 0) / 100.0))

                # Aquí el Algoritmo Genético toma el control de las prioridades del agente
                score = (damage + possible_cure) * self.weights.get('move_pressure', 1.0)

                # Penalización adaptable por inmunidad o resistencia
                if type_mult < 1.0:
                    score -= 1000 * (2.0 - type_mult) * self.weights.get('type_pressure', 1.0)
                elif type_mult > 1.0:
                    score += 1000 * type_mult * self.weights.get('type_pressure', 1.0)

                # Presión de KO adaptable
                if opp and damage >= opp.current_hp:
                    score += 5000 * self.weights.get('ko_pressure', 1.0)

                # Presión de Velocidad/Prioridad adaptable
                if getattr(move, 'priority', 0) > 0 and opp and damage >= opp.current_hp:
                    score += 2000 * self.weights.get('speed_pressure', 1.0)

                attack_actions.append((Action(type=ActionType.MOVE, target_index=i), score))

        attack_actions.sort(key=lambda x: x[1], reverse=True)
        actions.extend([a[0] for a in attack_actions])

        switch_candidates = [i for i, p in enumerate(team) if p.current_hp > 0 and i != active_idx]

        # Se aplica la presión de cambio
        if active.current_hp <= 0:
            actions.extend([Action(type=ActionType.SWITCH, target_index=c) for c in switch_candidates])
        elif switch_candidates and my_cooldown >= max(1, int(3 - self.weights.get('switch_pressure', 1.0))):
            actions.extend([Action(type=ActionType.SWITCH, target_index=c) for c in switch_candidates])

        if not actions:
            actions.append(Action(type=ActionType.MOVE, target_index=0))

        return actions

    def _simulate_full_turn(self, state: BattleState, p1_action: Action, p2_action: Action) -> BattleState:
        """Simula un turno completo y devuelve el BattleState resultante.

        Args:
            state (BattleState): Estado actual antes del turno.
            p1_action (Action): Accion del jugador 1.
            p2_action (Action): Accion del jugador 2.

        Returns:
            BattleState: Nuevo estado tras aplicar ambas acciones.
        """
        p1_team = self._build_real_team(state.p1_team)
        p2_team = self._build_real_team(state.p2_team)
        _, new_p1_idx, new_p2_idx = process_turn(p1_team, state.p1_active_index, p1_action, p2_team, state.p2_active_index, p2_action)
        return BattleState(p1_team=[p.to_state() for p in p1_team], p2_team=[p.to_state() for p in p2_team], p1_active_index=new_p1_idx, p2_active_index=new_p2_idx, turn_number=state.turn_number + 1)

    def _max_value(self, state: BattleState, depth: int, alpha: float, beta: float, my_cd: int, opp_cd: int) -> float:
        """
        Obtiene el valor máximo en una situación determinada de una batalla.

        Args:
            state (BattleState): Estado actual de la batalla.
            depth (int): Profundidad de la búsqueda.
            alpha (float): Mejor valor garantizado para el jugador actual.
            beta (float): Mejor valor garantizado para el oponente.
            my_cd (int): Tiempo de enfriamiento actual para el equipo del jugador.
            opp_cd (int): Tiempo de enfriamiento actual para el equipo del oponente.

        Returns:
            float: Valor máximo obtenible en la situación actual.

        Raises:
            Exception: Si se produce un error durante la evaluación del estado.
        """
        if depth == 0 or self._is_match_over(state): return self._evaluate_state(state)
        team, active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
        opp = opp_team[self._safe_index(opp_active_idx, opp_team)] if opp_team else None
        
        v = -INF
        for my_action in self._get_smart_legal_actions(team, active_idx, opp, my_cd):
            next_my_cd = 0 if my_action.type == ActionType.SWITCH else my_cd + 1
            v = max(v, self._min_value(state, depth - 1, alpha, beta, my_action, next_my_cd, opp_cd + 1))
            if v >= beta: return v
            alpha = max(alpha, v)
        return v

    def _min_value(self, state: BattleState, depth: int, alpha: float, beta: float, my_action: Action, my_cd: int, opp_cd: int) -> float:
        """
        Calcula el valor mínimo de una función de evaluación en un árbol de juego.

        Args:
            state (BattleState): Estado actual del juego.
            depth (int): Profundidad actual en el árbol de juego.
            alpha (float): Mejor valor posible para el maximizador.
            beta (float): Peor valor posible para el minimizador.
            my_action (Action): Acción actual del jugador.
            my_cd (int): Tiempo de enfriamiento actual del jugador.
            opp_cd (int): Tiempo de enfriamiento actual del oponente.

        Returns:
            float: Valor mínimo de la función de evaluación.

        Raises:
            No se lanzan excepciones explícitas, pero puede ocurrir un error si el estado del juego es inválido.
        """
        if depth == 0 or self._is_match_over(state): return self._evaluate_state(state)
        my_team, my_active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
        my_active = my_team[self._safe_index(my_active_idx, my_team)]
        
        v = INF
        for opp_action in self._get_smart_legal_actions(opp_team, opp_active_idx, my_active, opp_cd):
            next_state = self._simulate_full_turn(state, my_action, opp_action) if self.player_id == 1 else self._simulate_full_turn(state, opp_action, my_action)
            next_opp_cd = 0 if opp_action.type == ActionType.SWITCH else opp_cd + 1
            v = min(v, self._max_value(next_state, depth, alpha, beta, my_cd, next_opp_cd))
            if v <= alpha: return v
            beta = min(beta, v)
        return v

    def get_action(self, state: BattleState) -> Action:
        """
        Descripción breve:
        Obtiene la acción óptima para un estado de batalla dado, considerando las acciones legales y el valor de cada acción.

        Args:
            state (BattleState): El estado de batalla actual.

        Returns:
            Action: La acción óptima para el estado de batalla dado.

        Raises:
            Exception: Si no se puede determinar la acción óptima debido a un error interno.
        """
        team, active_idx, opp_team, opp_active_idx = self._get_team_and_active(state)
        self.turns_since_last_switch += 1
        opp = opp_team[self._safe_index(opp_active_idx, opp_team)] if opp_team else None

        if opp:
            current_opp_name = getattr(opp, 'name', None)
            if self.last_opp_active_name is not None and current_opp_name != self.last_opp_active_name:
                self.opp_turns_since_last_switch = 0
            else: self.opp_turns_since_last_switch += 1
            self.last_opp_active_name = current_opp_name

        legal_actions = self._get_smart_legal_actions(team, active_idx, opp, self.turns_since_last_switch)
        if len(legal_actions) == 1:
            if legal_actions[0].type == ActionType.SWITCH: self.turns_since_last_switch = 0
            return legal_actions[0]

        best_action, best_value, alpha, beta = legal_actions[0], -INF, -INF, INF

        for my_action in legal_actions:
            next_my_cooldown = 0 if my_action.type == ActionType.SWITCH else self.turns_since_last_switch + 1
            value = self._min_value(state, DEPTH - 1, alpha, beta, my_action, next_my_cooldown, self.opp_turns_since_last_switch)
            if value > best_value:
                best_value, best_action = value, my_action
            alpha = max(alpha, best_value)

        if best_action.type == ActionType.SWITCH: self.turns_since_last_switch = 0
        return best_action