import random
from typing import List, Optional

from src.ai.base_agent import BaseAgent
from src.ai.heuristics import calculate_hp_differential_l3
from src.core.interfaces import (Action,ActionType,BattleState,PokemonState)
from src.core.battle_engine import process_turn
from src.entities.pokemon import Pokemon
from config import AI_LEVEL3_DEPTH, INF


class Level3Agent(BaseAgent):

    def __init__(self, player_id: int):
        super().__init__(player_id)
        self.turns_since_last_switch = 0

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
        """
        Descripción breve:
        Obtiene un índice seguro para una secuencia, evitando excepciones de índice fuera de rango.

        Args:
            idx (int): El índice deseado.
            seq: La secuencia sobre la que se quiere acceder.

        Returns:
            int: El índice seguro para la secuencia.

        Raises:
            No lanza excepciones, en su lugar devuelve 0 cuando el índice no es válido o la secuencia está vacía.
        """
        if not seq:
            return 0
        if idx is None or idx < 0 or idx >= len(seq):
            return 0
        return idx

    def _is_match_over(self, state: BattleState) -> bool:
        p1_alive = any(p.current_hp > 0 for p in state.p1_team)
        p2_alive = any(p.current_hp > 0 for p in state.p2_team)
        return not (p1_alive and p2_alive)

    def _get_terminal_value(self, state: BattleState) -> Optional[float]:
        """
        Retorna un valor centinela de utilidad pura si el estado es terminal
        (victoria/derrota absoluta). Retorna None si la batalla continúa.

        La magnitud 10000.0 se eligió para superar cualquier valor posible
        de la heurística `calculate_hp_differential_l3` (cuyo techo teórico
        en un combate 6v6 nivel 100 ronda ~3000 puntos de HP), garantizando
        que el algoritmo Minimax siempre prefiera una victoria real
        inmediata a cualquier ventaja posicional incierta.
        """
        p1_alive = any(p.current_hp > 0 for p in state.p1_team)
        p2_alive = any(p.current_hp > 0 for p in state.p2_team)

        if p1_alive and p2_alive:
            return None
        if not p1_alive and not p2_alive:
            return 0.0

        p1_won = p1_alive and not p2_alive
        i_am_p1 = (self.player_id == 1)
        i_win = (p1_won == i_am_p1)

        return 10000.0 if i_win else -10000.0

    def _build_real_team(self, state_team):
        return [Pokemon.from_state(p) for p in state_team]

    def _get_legal_actions(
        self,
        team: List[PokemonState],
        active_idx: int,
        turns_since_switch: int
    ) -> List[Action]:

        """
        Obtiene las acciones legales permitidas para un equipo de Pokémon en un momento dado del juego.

        Args:
            team (List[PokemonState]): El equipo de Pokémon.
            active_idx (int): El índice del Pokémon activo en el equipo.
            turns_since_switch (int): El número de turnos desde la última vez que se cambió de Pokémon.

        Returns:
            List[Action]: Una lista de acciones legales que se pueden realizar, donde cada acción es un objeto con un tipo y un índice de objetivo.

        Raises:
            No se lanzan excepciones explícitas, pero puede ocurrir un error si el equipo o el índice activo son inválidos.
        """
        actions = []
        if not team:
            return actions

        active_idx = self._safe_index(active_idx, team)
        active = team[active_idx]

        if active.current_hp > 0 and getattr(active, "moves", []):
            for i, move in enumerate(active.moves):
                if getattr(move, "current_pp", 0) > 0:
                    actions.append(
                        Action(
                            type=ActionType.MOVE,
                            target_index=i
                        )
                    )

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

        if not actions:
            actions.append(
                Action(
                    type=ActionType.MOVE,
                    target_index=0
                )
            )

        return actions

    def _simulate_full_turn(
        self,
        state: BattleState,
        p1_action: Action,
        p2_action: Action
    ) -> BattleState:

        """
        Simula un turno completo de una batalla, aplicando las acciones de ambos jugadores y actualizando el estado de la batalla.

        Args:
            state (BattleState): El estado actual de la batalla.
            p1_action (Action): La acción tomada por el jugador 1.
            p2_action (Action): La acción tomada por el jugador 2.

        Returns:
            BattleState: El nuevo estado de la batalla después de aplicar las acciones de ambos jugadores.

        Raises:
            No se lanzan excepciones explícitas en esta función, pero puede propagar excepciones de las funciones llamadas, como `_build_real_team` o `process_turn`.
        """
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

        """
        Obtiene la mejor acción posible para el estado actual de la batalla.

        Args:
            state (BattleState): El estado actual de la batalla.

        Returns:
            Action: La mejor acción posible.

        Raises:
            No se lanzan excepciones explícitas.
        """
        team, active_idx, _, _ = self._get_team_and_active(state)
        self.turns_since_last_switch += 1

        legal_actions = self._get_legal_actions(
            team,
            active_idx,
            self.turns_since_last_switch
        )

        if len(legal_actions) == 1:
            if legal_actions[0].type == ActionType.SWITCH:
                self.turns_since_last_switch = 0
            return legal_actions[0]

        legal_actions.sort(
            key=lambda a: 0 if a.type == ActionType.MOVE else 1
        )

        TERMINAL_LOSS = -10000.0
        alpha = -10000.0
        beta = 10000.0

        best_action = legal_actions[0]
        best_value = TERMINAL_LOSS

        for my_action in legal_actions:
            next_my_cooldown = (
                0
                if my_action.type == ActionType.SWITCH
                else self.turns_since_last_switch + 1
            )
            value = self._min_value(
                state,
                AI_LEVEL3_DEPTH - 1,
                alpha,
                beta,
                my_action,
                next_my_cooldown,
                2
            )

            if value > best_value:
                best_value = value
                best_action = my_action

            alpha = max(alpha, value)

        if best_value <= TERMINAL_LOSS:
            best_action = random.choice(legal_actions)

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

        """
        Devuelve el valor máximo obtenible en una situación de batalla.

        Args:
            state (BattleState): Estado actual de la batalla.
            depth (int): Nivel de profundidad en la búsqueda.
            alpha (float): Mejor valor posible para el jugador máximo.
            beta (float): Mejor valor posible para el jugador mínimo.

        Returns:
            float: Valor máximo esperado.

        Raises:
            No se especifican excepciones.
        """
        terminal = self._get_terminal_value(state)
        if terminal is not None:
            return terminal
        if depth == 0:
            return calculate_hp_differential_l3(
                state,
                self.player_id
            )

        team, active_idx, _, _ = self._get_team_and_active(state)

        legal_actions = self._get_legal_actions(
            team,
            active_idx,
            my_cooldown
        )

        max_utility = -INF

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
                opp_cooldown
            )

            max_utility = max(max_utility, value)

            if max_utility >= beta:
                return max_utility

            alpha = max(alpha, max_utility)

        return max_utility

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

        """

        Calcula el valor mínimo de una situación de batalla mediante el algoritmo minimax.

        Args:
            state (BattleState): El estado actual de la batalla.
            depth (int): La profundidad máxima del árbol de búsqueda.
            alpha (float): El límite inferior del rango de búsqueda.
            beta (float): El límite superior del rango de búsqueda.
            my_action (Action): La acción que se va a realizar.

        Returns:
            float: El valor mínimo de la situación de batalla.

        Raises:
            No se lanzan excepciones explícitas, pero puede ocurrir un error si el estado de la batalla es inválido o si se produce un error en la evaluación del estado.

        """
        terminal = self._get_terminal_value(state)
        if terminal is not None:
            return terminal
        if depth == 0:
            return calculate_hp_differential_l3(
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
            opp_cooldown
        )

        min_utility = INF

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
                0
                if opp_action.type == ActionType.SWITCH
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

            min_utility = min(min_utility, value)

            if min_utility <= alpha:
                return min_utility

            beta = min(beta, min_utility)

        return min_utility