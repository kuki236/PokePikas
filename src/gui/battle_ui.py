# src/gui/battle_ui.py
import pygame
import sys
import os
import random
from time import perf_counter

from src.utils.data_loader import DataLoader
from src.core.battle_engine import process_turn
from src.core.interfaces import BattleState, Action, ActionType
from src.ai.level1_agent import Level1Agent
from src.ai.level2_agent import Level2Agent


class BattleScreen:
    def __init__(self, screen, renderer, p1_team, difficulty, mode):
        self.screen = screen
        self.renderer = renderer
        self.p1_team_names = p1_team
        self.difficulty = difficulty
        self.mode = mode

        self.running = True
        self.clock = pygame.time.Clock()

        self.bg_battle = self.renderer.load_background(
            os.path.join('assets', 'bg_modos.jpg'),
            self.screen.get_width(),
            self.screen.get_height()
        )

        self.loader = DataLoader('data/pokemon_pool.json', 'data/moves_pool.json')

        name_to_id = {p['name']: p.get('poke_id', None) for p in self.loader.pokemon_data}

        self.p1_team = []
        for name in self.p1_team_names:
            pid = name_to_id.get(name)
            if pid is None:
                pid = random.choice(self.loader.pokemon_data)['poke_id']
            try:
                self.p1_team.append(self.loader.create_battle_pokemon(pid))
            except Exception:
                self.p1_team.append(
                    self.loader.create_battle_pokemon(
                        random.choice(self.loader.pokemon_data)['poke_id']
                    )
                )

        pool_ids = [p['poke_id'] for p in self.loader.pokemon_data]
        self.p2_team = []
        while len(self.p2_team) < len(self.p1_team):
            pid = random.choice(pool_ids)
            self.p2_team.append(self.loader.create_battle_pokemon(pid))

        self.p1_active_idx = 0
        self.p2_active_idx = 0

        def _agent_for_level(pid, lvl):
            if lvl == 1:
                return Level1Agent(player_id=pid)
            elif lvl == 2:
                return Level2Agent(player_id=pid)
            return Level2Agent(player_id=pid)

        # ---------------------------------------------------------------
        # Detección de modo humano robusta: acepta "humano", "1p", "manual"
        # ---------------------------------------------------------------
        mode_str = str(self.mode).lower() if self.mode else ""
        self.human_player = any(k in mode_str for k in ("humano", "1p", "manual", "human"))

        self.agent_p1 = None if self.human_player else _agent_for_level(1, 1)
        self.agent_p2 = _agent_for_level(2, self.difficulty or 1)
        self._temp_agent_for_human = _agent_for_level(1, 1)

        self.mensaje_batalla = "¡Un combate comienza!"

        self.auto_mode = not self.human_player
        self.last_turn_time = perf_counter()
        self.turn_interval = 1.2
        self.turn_number = 1

        sw = self.screen.get_width()
        sh = self.screen.get_height()
        btn_w = 220
        btn_h = 48
        pad = 12
        dialog_h = 100
        top_y = sh - dialog_h - 20 - (btn_h * 2 + pad)
        left_x = sw - 40 - 2 * btn_w - pad
        right_x = sw - 40 - btn_w

        self.move_buttons = [
            pygame.Rect(left_x, top_y, btn_w, btn_h),
            pygame.Rect(right_x, top_y, btn_w, btn_h),
            pygame.Rect(left_x, top_y + btn_h + pad, btn_w, btn_h),
            pygame.Rect(right_x, top_y + btn_h + pad, btn_w, btn_h),
        ]

        self.waiting_for_player_action = False
        self.player_pending_action = None
        self.battle_finished = False

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------
    def _build_battle_state(self) -> BattleState:
        return BattleState(
            p1_team=[p.to_state() for p in self.p1_team],
            p2_team=[p.to_state() for p in self.p2_team],
            p1_active_index=self.p1_active_idx,
            p2_active_index=self.p2_active_idx,
            turn_number=self.turn_number
        )

    # ------------------------------------------------------------------
    # Describir resultados del turno
    # ------------------------------------------------------------------
    def _describe_outcomes(self, outcomes):
        lines = []
        for out in outcomes:
            actor = 'Jugador' if out.actor == 1 else 'IA'

            if out.action_type == ActionType.SWITCH:
                # action_id = pokemon.id del que entró
                name = None
                for p in (self.p1_team + self.p2_team):
                    if p.id == out.action_id:
                        name = p.name
                        break
                name = name or f"#{out.action_id}"
                lines.append(f"> {actor} cambió a {name}.")

            else:
                # action_id = move.id del movimiento usado
                mv_name = None
                for p in (self.p1_team + self.p2_team):
                    for mv in getattr(p, 'moves', []):
                        if getattr(mv, 'id', None) == out.action_id:
                            mv_name = getattr(mv, 'name', None)
                            break
                    if mv_name:
                        break

                label = mv_name or f"Movimiento #{out.action_id}"

                if not out.hit_success:
                    lines.append(f"> {actor} usó {label} pero falló.")
                elif out.damage_dealt > 0:
                    lines.append(f"> {actor} usó {label} y causó {out.damage_dealt} de daño.")
                else:
                    lines.append(f"> {actor} usó {label}.")

                if out.target_fainted:
                    target_name = "rival" if out.actor == 1 else "tu Pokémon"
                    lines.append(f"  ¡El {target_name} se ha debilitado!")

        return '\n'.join(lines) if lines else "No pasó nada relevante este turno."

    # ------------------------------------------------------------------
    # Labels de movimientos del activo del jugador
    # ------------------------------------------------------------------
    def _get_active_move_labels(self):
        active = self.p1_team[self.p1_active_idx] if self.p1_team else None
        moves = getattr(active, 'moves', []) if active else []

        labels = []
        for i in range(4):
            if i < len(moves):
                mv = moves[i]
                pp = getattr(mv, 'current_pp', None)
                max_pp = getattr(mv, 'max_pp', None)
                name = getattr(mv, 'name', 'Movimiento')
                if pp is not None and max_pp is not None:
                    labels.append(f"{name} ({pp}/{max_pp})")
                else:
                    labels.append(name)
            else:
                labels.append("-")
        return labels

    # ------------------------------------------------------------------
    # Bucle principal
    # ------------------------------------------------------------------
    def run(self):
        # Si el jugador es humano, arrancar el primer turno para activar
        # el estado "esperando acción" inmediatamente
        if self.human_player and not self.auto_mode:
            self._process_full_turn()

        while self.running:
            now = perf_counter()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

                    elif event.key == pygame.K_SPACE and not self.battle_finished:
                        self.auto_mode = not self.auto_mode
                        if self.human_player:
                            if self.auto_mode:
                                self.agent_p1 = self._temp_agent_for_human
                                self.waiting_for_player_action = False
                                self.mensaje_batalla = "Modo automático activado."
                            else:
                                self.agent_p1 = None
                                self.waiting_for_player_action = False
                                self.mensaje_batalla = "Modo manual. Elige movimiento."
                                self._process_full_turn()

                    elif event.key == pygame.K_n and not self.battle_finished:
                        self._process_full_turn()

                # -------------------------------------------------------
                # IMPORTANTE: MOUSEBUTTONDOWN al mismo nivel que KEYDOWN
                # -------------------------------------------------------
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if (
                        self.human_player
                        and self.waiting_for_player_action
                        and not self.battle_finished
                    ):
                        self._handle_move_click(event.pos)

            # Avance automático con timer
            if (
                not self.battle_finished
                and self.auto_mode
                and (not self.human_player or self.agent_p1 is not None)
                and (now - self.last_turn_time) >= self.turn_interval
            ):
                self._process_full_turn()
                self.last_turn_time = now

            # ----------------------------------------------------------
            # DIBUJO
            # ----------------------------------------------------------
            self.renderer.draw_background(self.bg_battle)

            p1_name = self.p1_team[self.p1_active_idx].name
            p2_name = self.p2_team[self.p2_active_idx].name

            img_p1_back = self.renderer.load_battle_sprite(
                p1_name,
                os.path.join('assets', 'sprites_back', f"{p1_name}.png"),
                is_back=True
            )
            img_p2_front = self.renderer.load_battle_sprite(
                p2_name,
                os.path.join('assets', 'sprites', f"{p2_name}.png"),
                is_back=False
            )

            if img_p2_front:
                self.screen.blit(img_p2_front, (600, 150))
            if img_p1_back:
                self.screen.blit(img_p1_back, (150, 350))

            p2_hp = self.p2_team[self.p2_active_idx].current_hp
            p2_max = self.p2_team[self.p2_active_idx].max_hp
            p1_hp = self.p1_team[self.p1_active_idx].current_hp
            p1_max = self.p1_team[self.p1_active_idx].max_hp

            self.renderer.draw_health_bar(50, 100, p2_name, p2_hp, p2_max, level=50, is_player=False)
            self.renderer.draw_health_bar(650, 420, p1_name, p1_hp, p1_max, level=50, is_player=True)

            self.renderer.draw_dialog_box(self.mensaje_batalla)

            if self.human_player:
                move_labels = self._get_active_move_labels()
                self._draw_move_buttons(pygame.mouse.get_pos(), move_labels)

            pygame.display.flip()
            self.clock.tick(60)

    # ------------------------------------------------------------------
    # Procesar turno completo
    # ------------------------------------------------------------------
    def _process_full_turn(self, player_action: Action = None):
        if self.battle_finished:
            return

        state = self._build_battle_state()

        if self.human_player:
            if player_action is None:
                if self.agent_p1 is None:
                    # Modo manual: esperar que el jugador haga click
                    self.waiting_for_player_action = True
                    self.mensaje_batalla = "Elige movimiento (haz click en un botón)."
                    return
                else:
                    # Modo auto-play: agente temporal decide por el humano
                    player_action = self.agent_p1.get_action(state)
        else:
            if player_action is None:
                player_action = self.agent_p1.get_action(state)

        ai_action = self.agent_p2.get_action(state)

        result, new_p1_idx, new_p2_idx = process_turn(
            self.p1_team,
            self.p1_active_idx,
            player_action,
            self.p2_team,
            self.p2_active_idx,
            ai_action
        )

        self.p1_active_idx = new_p1_idx
        self.p2_active_idx = new_p2_idx
        self.turn_number += 1
        self.waiting_for_player_action = False
        self.player_pending_action = None

        summary = self._describe_outcomes(result.outcomes)

        if result.match_over:
            self.battle_finished = True
            self.auto_mode = False
            if result.winner == 1:
                summary += "\n\n¡El jugador ha ganado la batalla!"
            elif result.winner == 2:
                summary += "\n\n¡La IA ha ganado la batalla!"
            else:
                summary += "\n\nResultado: empate."
            self.mensaje_batalla = summary
            return

        self.mensaje_batalla = summary

        # ---------------------------------------------------------------
        # CORRECCIÓN CLAVE: después de procesar un turno humano en modo
        # manual, re-entrar automáticamente en estado "esperando acción"
        # para el siguiente turno sin que el jugador tenga que hacer nada.
        # ---------------------------------------------------------------
        if self.human_player and not self.auto_mode and self.agent_p1 is None:
            self._process_full_turn()

    # ------------------------------------------------------------------
    # Dibujar botones de movimientos
    # ------------------------------------------------------------------
    def _draw_move_buttons(self, mouse_pos, labels=None):
        if labels is None:
            labels = self._get_active_move_labels()

        active = self.p1_team[self.p1_active_idx]
        moves = getattr(active, 'moves', []) if active else []

        enabled = self.waiting_for_player_action and not self.battle_finished

        for i, rect in enumerate(self.move_buttons):
            label = labels[i] if i < len(labels) else "-"
            has_move = i < len(moves)
            hovered = enabled and has_move and rect.collidepoint(mouse_pos)

            disabled = not enabled or not has_move
            if not disabled and has_move:
                pp = getattr(moves[i], 'current_pp', None)
                if pp is not None and pp <= 0:
                    disabled = True

            self.renderer.draw_button(rect, label, hovered, disabled=disabled)

    # ------------------------------------------------------------------
    # Manejar click en botón de movimiento
    # ------------------------------------------------------------------
    def _handle_move_click(self, mouse_pos):
        active = self.p1_team[self.p1_active_idx]
        moves = getattr(active, 'moves', []) if active else []

        for i, rect in enumerate(self.move_buttons):
            if rect.collidepoint(mouse_pos):
                if i >= len(moves):
                    return

                mv = moves[i]
                pp = getattr(mv, 'current_pp', None)
                if pp is not None and pp <= 0:
                    self.mensaje_batalla = "¡Ese movimiento no tiene PP! Elige otro."
                    return

                action = Action(type=ActionType.MOVE, target_index=i)
                self.player_pending_action = action
                self._process_full_turn(player_action=action)
                return