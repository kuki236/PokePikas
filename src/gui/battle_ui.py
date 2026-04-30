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
        self.action_after_battle = "MENU" # Por defecto vuelve al menú

        # Cargamos el fondo de la batalla desde 'assets/bg_battle.jpg'
        self.bg_battle = self.renderer.load_background(
            os.path.join('assets', 'bg_battle.jpg'),
            self.screen.get_width(),
            self.screen.get_height()
        )

        # Si no se encuentra 'bg_battle.jpg', se usa 'bg_modos.jpg' como respaldo
        if self.bg_battle is None:
            self.bg_battle = self.renderer.load_background(
                os.path.join('assets', 'bg_modos.jpg'),
                self.screen.get_width(),
                self.screen.get_height()
            )
            print("Advertencia: No se encontró 'assets/bg_battle.jpg'. Usando imagen de respaldo.")

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

        # Variables para la cola de mensajes
        self.message_queue = []
        self.current_message = ""
        self.message_display_time = perf_counter()
        self.message_duration = 1.5 # Duración de cada mensaje en segundos (ajustado para mayor fluidez)

        self.auto_mode = not self.human_player
        self.last_turn_time = perf_counter()
        self.turn_interval = 1.0
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

        # Botones post-batalla
        self.btn_replay = pygame.Rect(sw // 2 - 250, sh // 2, 200, 60)
        self.btn_menu = pygame.Rect(sw // 2 + 50, sh // 2, 200, 60)

        self.waiting_for_player_action = False
        self.waiting_for_player_switch = False
        self.player_pending_action = None
        self.battle_finished = False

        if self.human_player and not self.auto_mode:
            self.waiting_for_player_action = True
            self.current_message = "Elige movimiento (haz click en un botón)."

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
        for out in outcomes:
            actor_name = self.p1_team[self.p1_active_idx].name if out.actor == 1 else self.p2_team[self.p2_active_idx].name

            if out.action_type == ActionType.SWITCH:
                name = None
                for p in (self.p1_team + self.p2_team):
                    if p.id == out.action_id:
                        name = p.name
                        break
                name = name or f"#{out.action_id}"

                if out.actor == 1:
                    self.message_queue.append(f"¡Jugador cambió a {name.capitalize()}!")
                else:
                    self.message_queue.append(f"¡La IA cambió a {name.capitalize()}!")

            else:
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
                    self.message_queue.append(f"¡{actor_name.capitalize()} usó {label} pero falló!")
                elif out.damage_dealt > 0:
                    self.message_queue.append(f"¡{actor_name.capitalize()} usó {label} y causó {out.damage_dealt} de daño!")
                else:
                    self.message_queue.append(f"¡{actor_name.capitalize()} usó {label}!")

                if out.target_fainted:
                    target_name = self.p2_team[self.p2_active_idx].name if out.actor == 1 else self.p1_team[self.p1_active_idx].name
                    self.message_queue.append(f"¡El {target_name.capitalize()} se ha debilitado!")
        
        if not outcomes:
            self.message_queue.append("No pasó nada relevante este turno.")

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
        while self.running:
            now = perf_counter()
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        self.action_after_battle = "MENU"

                    elif event.key == pygame.K_SPACE and not self.battle_finished:
                        self.auto_mode = not self.auto_mode
                        if self.human_player:
                            if self.auto_mode:
                                self.agent_p1 = self._temp_agent_for_human
                                self.waiting_for_player_action = False
                                self.waiting_for_player_switch = False
                                self.message_queue.append("Modo automático activado.")
                            else:
                                self.agent_p1 = None
                                self.waiting_for_player_action = False
                                self.waiting_for_player_switch = False
                                self.message_queue.append("Modo manual. Elige movimiento.")

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.battle_finished:
                        if self.btn_replay.collidepoint(event.pos):
                            self.action_after_battle = "REPLAY"
                            self.running = False
                        elif self.btn_menu.collidepoint(event.pos):
                            self.action_after_battle = "MENU"
                            self.running = False
                    elif self.human_player and not self.battle_finished:
                        if self.waiting_for_player_action:
                            self._handle_move_click(event.pos)
                        elif self.waiting_for_player_switch:
                            self._handle_switch_click(event.pos)

            # --- Lógica de visualización de mensajes y transición de estados ---
            if self.message_queue:
                if now - self.message_display_time > self.message_duration:
                    self.current_message = self.message_queue.pop(0)
                    self.message_display_time = now
            else:
                # Ya no hay mensajes en la cola. Esperamos a que el último se lea.
                if now - self.message_display_time > self.message_duration:
                    if not self.battle_finished:
                        # 1. Chequeamos si el P2 (IA) necesita cambiar de Pokémon
                        if self.p2_team[self.p2_active_idx].current_hp <= 0:
                            self._ai_switch_pokemon(2)
                            
                        # 2. Chequeamos si el P1 necesita cambiar de Pokémon
                        elif self.p1_team[self.p1_active_idx].current_hp <= 0:
                            if self.human_player and not self.auto_mode:
                                if not self.waiting_for_player_switch:
                                    self.waiting_for_player_switch = True
                                    self.waiting_for_player_action = False
                                    self.current_message = "¡Tu Pokémon se ha debilitado! Elige un nuevo Pokémon."
                            else:
                                self._ai_switch_pokemon(1)
                                
                        # 3. Si nadie necesita cambiar y es el turno del humano en manual
                        elif self.human_player and not self.auto_mode:
                            if not self.waiting_for_player_action and not self.waiting_for_player_switch:
                                self.waiting_for_player_action = True
                                self.current_message = "Elige movimiento (haz click en un botón)."
                                
                        # 4. Si es auto_mode y ya pasó el intervalo, procesamos el turno
                        elif self.auto_mode:
                            if now - self.last_turn_time >= self.turn_interval:
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

            if img_p2_front and self.p2_team[self.p2_active_idx].current_hp > 0:
                self.screen.blit(img_p2_front, (600, 150))
            
            if img_p1_back and self.p1_team[self.p1_active_idx].current_hp > 0:
                self.screen.blit(img_p1_back, (150, 350))

            p2_hp = self.p2_team[self.p2_active_idx].current_hp
            p2_max = self.p2_team[self.p2_active_idx].max_hp
            p1_hp = self.p1_team[self.p1_active_idx].current_hp
            p1_max = self.p1_team[self.p1_active_idx].max_hp

            self.renderer.draw_health_bar(50, 100, p2_name, p2_hp, p2_max, level=50, is_player=False)
            self.renderer.draw_health_bar(650, 420, p1_name, p1_hp, p1_max, level=50, is_player=True)

            self.renderer.draw_dialog_box(self.current_message)

            if self.human_player and not self.battle_finished:
                if self.waiting_for_player_action:
                    move_labels = self._get_active_move_labels()
                    self._draw_move_buttons(mouse_pos, move_labels)
                elif self.waiting_for_player_switch:
                    self._draw_switch_options(mouse_pos)

            if self.battle_finished:
                overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
                overlay.set_alpha(150)
                overlay.fill((0, 0, 0))
                self.screen.blit(overlay, (0, 0))
                
                self.renderer.draw_text("FIN DEL COMBATE", 'title', (255, 215, 0), self.screen.get_width()//2, self.screen.get_height()//2 - 100, center=True)

                self.renderer.draw_button(self.btn_replay, "Repetir", self.btn_replay.collidepoint(mouse_pos))
                self.renderer.draw_button(self.btn_menu, "Ir al Menú", self.btn_menu.collidepoint(mouse_pos))

            pygame.display.flip()
            self.clock.tick(60)
            
        return self.action_after_battle

    def _process_full_turn(self, player_action: Action = None):
        if self.battle_finished:
            return

        state = self._build_battle_state()

        if self.human_player and not self.auto_mode:
            # En modo manual esperamos que `player_action` ya venga al llamar a la función
            if player_action is None:
                return
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
        self.waiting_for_player_switch = False
        self.player_pending_action = None

        self._describe_outcomes(result.outcomes)

        if result.match_over:
            self.battle_finished = True
            self.auto_mode = False
            if result.winner == 1:
                self.message_queue.append("¡El jugador ha ganado la batalla!")
            elif result.winner == 2:
                self.message_queue.append("¡La IA ha ganado la batalla!")
            else:
                self.message_queue.append("Resultado: empate.")

    def _draw_move_buttons(self, mouse_pos, labels=None):
        if labels is None:
            labels = self._get_active_move_labels()

        active = self.p1_team[self.p1_active_idx]
        moves = getattr(active, 'moves', []) if active else []

        enabled = self.waiting_for_player_action and not self.battle_finished

        has_disabled_param = False
        try:
            from inspect import signature
            sig = signature(self.renderer.draw_button)
            if 'disabled' in sig.parameters:
                has_disabled_param = True
        except:
            pass
            
        for i, rect in enumerate(self.move_buttons):
            label = labels[i] if i < len(labels) else "-"
            has_move = i < len(moves)
            hovered = enabled and has_move and rect.collidepoint(mouse_pos)

            disabled = not enabled or not has_move
            if not disabled and has_move:
                pp = getattr(moves[i], 'current_pp', None)
                if pp is not None and pp <= 0:
                    disabled = True

            if has_disabled_param:
                self.renderer.draw_button(rect, label, hovered, disabled=disabled)
            else:
                self.renderer.draw_button(rect, label, hovered)

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
                    self.message_queue.append("¡Ese movimiento no tiene PP! Elige otro.")
                    return

                action = Action(type=ActionType.MOVE, target_index=i)
                self.player_pending_action = action
                # Ocultamos los botones de inmediato
                self.waiting_for_player_action = False
                # Procesamos el turno
                self._process_full_turn(player_action=action)
                return

    def _draw_switch_options(self, mouse_pos):
        available_pokemon = []
        for i, pkm in enumerate(self.p1_team):
            if pkm.current_hp > 0 and i != self.p1_active_idx:
                available_pokemon.append((i, pkm))
        
        sw = self.screen.get_width()
        sh = self.screen.get_height()
        btn_w = 180
        btn_h = 48
        pad = 10
        
        start_x = (sw - (len(available_pokemon) * btn_w + (len(available_pokemon) - 1) * pad)) // 2
        start_y = sh - 100

        self.switch_buttons_rects = []
        for i, (idx, pkm) in enumerate(available_pokemon):
            rect = pygame.Rect(start_x + i * (btn_w + pad), start_y, btn_w, btn_h)
            self.switch_buttons_rects.append((rect, idx))
            
            is_hovered = rect.collidepoint(mouse_pos)
            self.renderer.draw_button(rect, pkm.name.capitalize(), is_hovered)

    def _handle_switch_click(self, mouse_pos):
        for rect, pkm_idx in self.switch_buttons_rects:
            if rect.collidepoint(mouse_pos):
                self.p1_active_idx = pkm_idx
                self.message_queue.append(f"¡Adelante, {self.p1_team[pkm_idx].name.capitalize()}!")
                self.waiting_for_player_switch = False
                return

    def _ai_switch_pokemon(self, player_id):
        team = self.p1_team if player_id == 1 else self.p2_team
        active_idx = self.p1_active_idx if player_id == 1 else self.p2_active_idx

        available_switches = [
            idx for idx, pkm in enumerate(team)
            if pkm.current_hp > 0 and idx != active_idx
        ]

        if available_switches:
            new_active_idx = random.choice(available_switches)
            if player_id == 1:
                self.p1_active_idx = new_active_idx
            else:
                self.p2_active_idx = new_active_idx
                
            self.message_queue.append(f"¡La IA envió a {team[new_active_idx].name.capitalize()}!")
