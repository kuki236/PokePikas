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
from src.entities.enums import AilmentType


class BattleScreen:
    def __init__(self, screen, renderer, p1_team, difficulty, mode):
        self.screen = screen
        self.renderer = renderer
        self.p1_team_names = p1_team
        self.difficulty = difficulty
        self.mode = mode

        self.running = True
        self.clock = pygame.time.Clock()
        self.action_after_battle = "MENU"

        # Resoluciones
        self.sw = self.screen.get_width()
        self.sh = self.screen.get_height()
        
        # Pantalla dividida tipo DS
        self.top_h = int(self.sh * 0.80) # 80% para la batalla
        self.bottom_h = self.sh - self.top_h # 20% para la UI

        # Cargamos el fondo de la batalla para la pantalla superior
        self.bg_battle = self.renderer.load_background(
            os.path.join('assets', 'bg_battle.jpg'),
            self.sw,
            self.top_h
        )

        if self.bg_battle is None:
            self.bg_battle = self.renderer.load_background(
                os.path.join('assets', 'bg_modos.jpg'),
                self.sw,
                self.top_h
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
        
        # Índices visuales independientes de la lógica
        self.p1_visual_idx = 0
        self.p2_visual_idx = 0

        def _agent_for_level(pid, lvl):
            if lvl == 1:
                return Level1Agent(player_id=pid)
            elif lvl == 2:
                return Level2Agent(player_id=pid)
            return Level2Agent(player_id=pid)

        mode_str = str(self.mode).lower() if self.mode else ""
        self.human_player = any(k in mode_str for k in ("humano", "1p", "manual", "human"))

        self.agent_p1 = None if self.human_player else _agent_for_level(1, 1)
        self.agent_p2 = _agent_for_level(2, self.difficulty or 1)
        self._temp_agent_for_human = _agent_for_level(1, 1)

        self.message_queue = []
        self.current_message = ""
        self.message_display_time = perf_counter()
        
        self.message_duration = 1.2 

        self.auto_mode = not self.human_player
        self.last_turn_time = perf_counter()
        self.turn_interval = 1.0
        self.turn_number = 1

        # --- LAYOUT TIPO DS (Pantalla Inferior) ---
        self.main_dialog_rect = pygame.Rect(10, self.top_h + 10, (self.sw // 2) - 20, self.bottom_h - 20)
        btn_action_w = (self.sw // 2) - 20
        btn_action_h = (self.bottom_h - 30) // 2
        self.btn_lucha = pygame.Rect(self.sw // 2, self.top_h + 10, btn_action_w, btn_action_h)
        self.btn_pokemon = pygame.Rect(self.sw // 2, self.top_h + 20 + btn_action_h, btn_action_w, btn_action_h)
        
        move_btn_w = 220 
        move_btn_h = 55
        pad_x = 15
        pad_y = 15
        total_w = (move_btn_w * 2) + pad_x
        total_h = (move_btn_h * 2) + pad_y
        start_x = (self.sw - total_w) // 2
        start_y = self.top_h + (self.bottom_h - total_h) // 2 + 5

        self.move_buttons = [
            pygame.Rect(start_x, start_y, move_btn_w, move_btn_h),
            pygame.Rect(start_x + move_btn_w + pad_x, start_y, move_btn_w, move_btn_h),
            pygame.Rect(start_x, start_y + move_btn_h + pad_y, move_btn_w, move_btn_h),
            pygame.Rect(start_x + move_btn_w + pad_x, start_y + move_btn_h + pad_y, move_btn_w, move_btn_h),
        ]

        self.btn_replay = pygame.Rect(self.sw // 2 - 250, self.sh // 2, 200, 60)
        self.btn_menu = pygame.Rect(self.sw // 2 + 50, self.sh // 2, 200, 60)

        self.waiting_for_player_action = False
        self.waiting_for_player_switch = False
        self.showing_moves = False 
        self.player_pending_action = None
        self.battle_finished = False

        self.p1_animating_damage = False
        self.p2_animating_damage = False
        self.p1_animation_start = 0
        self.p2_animation_start = 0
        self.animation_duration = 0.3
        
        self.p1_fainted = False
        self.p2_fainted = False
        self.p1_fainted_anim_start = 0
        self.p2_fainted_anim_start = 0
        self.faint_anim_duration = 1.0 
        
        # Variables de la Pokéball
        self.pokeball_img = self.renderer.load_sprite("pokeball", os.path.join('assets', 'sprites', 'pokeball.png'))
        self.p1_switching_anim = False
        self.p2_switching_anim = False
        self.switch_anim_start = 0
        self.switch_anim_duration = 0.8
        
        self.animating_blocking = False # Usado para CUALQUIER animación bloqueante

        self.p1_fainted_id = None
        self.p2_fainted_id = None
        self.p1_next_id = None
        self.p2_next_id = None

        # BARRAS DE VIDA FLUIDAS
        self.p1_display_hp = -1
        self.p2_display_hp = -1
        self.p1_target_hp = -1
        self.p2_target_hp = -1
        self.last_p1_id = None
        self.last_p2_id = None

        if self.human_player and not self.auto_mode:
            self.waiting_for_player_action = True
            self._set_default_message()

    def _set_default_message(self):
        active_pkm = self.p1_team[self.p1_visual_idx]
        self.current_message = f"¿Qué debería\nhacer {active_pkm.name.capitalize()}?"

    def _build_battle_state(self) -> BattleState:
        return BattleState(
            p1_team=[p.to_state() for p in self.p1_team],
            p2_team=[p.to_state() for p in self.p2_team],
            p1_active_index=self.p1_active_idx,
            p2_active_index=self.p2_active_idx,
            turn_number=self.turn_number
        )

    def _advance_message(self):
        if self.animating_blocking:
            return

        if self.message_queue:
            msg = self.message_queue.pop(0)
            
            if isinstance(msg, dict):
                # Sincronizar metas de HP visual
                if "p1_target_hp" in msg:
                    self.p1_target_hp = int(msg["p1_target_hp"])
                if "p2_target_hp" in msg:
                    self.p2_target_hp = int(msg["p2_target_hp"])
                
                if msg.get("sync_hp"):
                    self.p1_target_hp = self.p1_team[self.p1_visual_idx].current_hp
                    self.p2_target_hp = self.p2_team[self.p2_visual_idx].current_hp
                    
                    if self.p1_target_hp <= 0 and not self.p1_fainted:
                        self.message_queue.insert(0, {"text": f"¡Tu {self.p1_team[self.p1_visual_idx].name.capitalize()}\nse ha debilitado por su estado!", "trigger_anim": "p1_fainted", "id": self.p1_team[self.p1_visual_idx].name})
                    if self.p2_target_hp <= 0 and not self.p2_fainted:
                        self.message_queue.insert(0, {"text": f"¡El {self.p2_team[self.p2_visual_idx].name.capitalize()}\nrival se ha debilitado por su estado!", "trigger_anim": "p2_fainted", "id": self.p2_team[self.p2_visual_idx].name})
                
                # Activar animaciones
                if "trigger_anim" in msg:
                    trigger = msg["trigger_anim"]
                    if trigger == "p1_damage":
                        self.p1_animating_damage = True
                        self.p1_animation_start = perf_counter()
                    elif trigger == "p2_damage":
                        self.p2_animating_damage = True
                        self.p2_animation_start = perf_counter()
                    elif trigger == "p1_fainted":
                        self.p1_fainted = True
                        self.p1_fainted_anim_start = perf_counter()
                        self.p1_fainted_id = msg.get("id")
                        self.animating_blocking = True
                    elif trigger == "p2_fainted":
                        self.p2_fainted = True
                        self.p2_fainted_anim_start = perf_counter()
                        self.p2_fainted_id = msg.get("id")
                        self.animating_blocking = True
                    elif trigger == "p1_switch":
                        self.p1_fainted = False 
                        self.p1_visual_idx = msg.get("idx")
                        self.p1_switching_anim = True
                        self.switch_anim_start = perf_counter()
                        self.animating_blocking = True
                        self.p1_next_id = msg.get("id")
                    elif trigger == "p2_switch":
                        self.p2_fainted = False 
                        self.p2_visual_idx = msg.get("idx")
                        self.p2_switching_anim = True
                        self.switch_anim_start = perf_counter()
                        self.animating_blocking = True
                        self.p2_next_id = msg.get("id")

                if msg.get("end_battle"):
                    self.battle_finished = True
                
                text = msg.get("text")
                if text is not None:
                    self.current_message = text
                    self.message_display_time = perf_counter()
                else:
                    self._advance_message()
            else:
                self.current_message = msg
                self.message_display_time = perf_counter()
        else:
            self.current_message = ""
            self._check_post_turn()

    def _check_post_turn(self):
        if self.battle_finished:
            return

        if self.p2_team[self.p2_active_idx].current_hp <= 0:
            self._ai_switch_pokemon(2)
            self._advance_message()
        elif self.p1_team[self.p1_active_idx].current_hp <= 0:
            if self.human_player and not self.auto_mode:
                if not self.waiting_for_player_switch:
                    self.waiting_for_player_switch = True
                    self.waiting_for_player_action = False
                    self.current_message = "¡Tu Pokémon se ha debilitado!\nElige un nuevo Pokémon."
            else:
                self._ai_switch_pokemon(1)
                self._advance_message()
        elif self.human_player and not self.auto_mode:
            if not self.waiting_for_player_action and not self.waiting_for_player_switch:
                self.waiting_for_player_action = True
                self._set_default_message()
        elif self.auto_mode:
            self.last_turn_time = perf_counter()

    def _describe_outcomes(self, outcomes, pre_turn_p1_name, pre_turn_p2_name):
        current_p1_name = pre_turn_p1_name
        current_p2_name = pre_turn_p2_name

        for out in outcomes:
            actor_name = current_p1_name if out.actor == 1 else current_p2_name

            if out.action_type == ActionType.SWITCH:
                new_idx = 0
                name = None
                for i, p in enumerate(self.p1_team if out.actor == 1 else self.p2_team):
                    if p.id == out.action_id:
                        name = p.name
                        new_idx = i
                        break
                name = name or f"#{out.action_id}"

                if out.actor == 1:
                    if not out.target_fainted:
                         self.message_queue.append({
                             "text": f"¡Jugador cambió a {name.capitalize()}!",
                             "trigger_anim": "p1_switch",
                             "idx": new_idx,
                             "id": name
                         })
                    current_p1_name = name
                else:
                    if not out.target_fainted:
                         self.message_queue.append({
                             "text": f"¡La IA cambió a {name.capitalize()}!",
                             "trigger_anim": "p2_switch",
                             "idx": new_idx,
                             "id": name
                         })
                    current_p2_name = name

            else:
                mv_name = None
                actual_move = None
                for p in (self.p1_team + self.p2_team):
                    for mv in getattr(p, 'moves', []):
                        if getattr(mv, 'id', None) == out.action_id:
                            mv_name = getattr(mv, 'name', None)
                            actual_move = mv
                            break
                    if mv_name:
                        break

                label = mv_name or f"Movimiento #{out.action_id}"

                if not out.hit_success:
                    self.message_queue.append({"text": f"¡{actor_name.capitalize()} usó {label}\npero falló!"})
                elif out.damage_dealt > 0:
                    self.message_queue.append({"text": f"¡{actor_name.capitalize()} usó {label}!"})
                    
                    msg = {"text": f"¡Y causó {out.damage_dealt} de daño!"}
                    if out.actor == 1:
                        msg["trigger_anim"] = "p2_damage"
                        msg["p2_target_hp"] = out.target_hp_remaining
                    else:
                        msg["trigger_anim"] = "p1_damage"
                        msg["p1_target_hp"] = out.target_hp_remaining
                    self.message_queue.append(msg)
                    
                    if actual_move and getattr(actual_move, 'drain', 0) > 0:
                        drain_msg = {"text": f"¡{actor_name.capitalize()} absorbió\nenergía del rival!"}
                        if out.actor == 1:
                            drain_msg["p1_target_hp"] = out.attacker_hp_remaining
                        else:
                            drain_msg["p2_target_hp"] = out.attacker_hp_remaining
                        self.message_queue.append(drain_msg)
                else:
                    self.message_queue.append({"text": f"¡{actor_name.capitalize()} usó {label}!"})
                    if actual_move and getattr(actual_move, 'healing', 0) > 0:
                        heal_msg = {"text": f"¡{actor_name.capitalize()} restauró su salud!"}
                        if out.actor == 1:
                            heal_msg["p1_target_hp"] = out.attacker_hp_remaining
                        else:
                            heal_msg["p2_target_hp"] = out.attacker_hp_remaining
                        self.message_queue.append(heal_msg)
                    
                    if out.status_applied:
                        status_name = str(out.status_applied).split('.')[-1]
                        self.message_queue.append({"text": f"¡El rival ahora sufre de\n{status_name}!"})

                if out.target_fainted:
                    target_name = current_p2_name if out.actor == 1 else current_p1_name
                    faint_msg = {"text": f"¡El {target_name.capitalize()}\nse ha debilitado!"}
                    if out.actor == 1:
                        faint_msg["trigger_anim"] = "p2_fainted"
                        faint_msg["id"] = current_p2_name
                        faint_msg["p2_target_hp"] = 0
                    else:
                        faint_msg["trigger_anim"] = "p1_fainted"
                        faint_msg["id"] = current_p1_name
                        faint_msg["p1_target_hp"] = 0
                    self.message_queue.append(faint_msg)
        
        if not outcomes:
            self.message_queue.append({"text": "No pasó nada relevante este turno."})
            
        self.message_queue.append({"text": None, "sync_hp": True})

        p1_active = next((p for p in self.p1_team if p.name == current_p1_name and getattr(p, 'current_hp', 0) > 0), None)
        if p1_active and p1_active.status_ailment != AilmentType.NONE:
            if p1_active.status_ailment == AilmentType.POISON:
                self.message_queue.append({"text": f"¡El veneno resta PS\na {current_p1_name.capitalize()}!"})
            elif p1_active.status_ailment == AilmentType.BURN:
                self.message_queue.append({"text": f"¡{current_p1_name.capitalize()} se resiente\nde la quemadura!"})
            elif p1_active.status_ailment == AilmentType.LEECH_SEED:
                self.message_queue.append({"text": f"¡Las drenadoras restan salud\na {current_p1_name.capitalize()}!"})

        p2_active = next((p for p in self.p2_team if p.name == current_p2_name and getattr(p, 'current_hp', 0) > 0), None)
        if p2_active and p2_active.status_ailment != AilmentType.NONE:
            if p2_active.status_ailment == AilmentType.POISON:
                self.message_queue.append({"text": f"¡El veneno resta PS\na {current_p2_name.capitalize()}!"})
            elif p2_active.status_ailment == AilmentType.BURN:
                self.message_queue.append({"text": f"¡{current_p2_name.capitalize()} se resiente\nde la quemadura!"})
            elif p2_active.status_ailment == AilmentType.LEECH_SEED:
                self.message_queue.append({"text": f"¡Las drenadoras restan salud\na {current_p2_name.capitalize()}!"})

    def _get_active_move_data(self):
        active = self.p1_team[self.p1_active_idx] if self.p1_team else None
        moves = getattr(active, 'moves', []) if active else []
        return moves

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
                        if self.showing_moves:
                            self.showing_moves = False
                        else:
                            self.running = False
                            self.action_after_battle = "MENU"
                            
                    elif event.key == pygame.K_SPACE:
                        if self.human_player:
                            if self.animating_blocking:
                                pass 
                            elif self.message_queue or (self.current_message and not self.waiting_for_player_action and not self.waiting_for_player_switch):
                                self._advance_message()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Pantalla final de botones (Ir al Menú / Repetir)
                    if self.battle_finished and not self.message_queue and not self.animating_blocking:
                        if self.btn_replay.collidepoint(event.pos):
                            self.action_after_battle = "REPLAY"
                            self.running = False
                        elif self.btn_menu.collidepoint(event.pos):
                            self.action_after_battle = "MENU"
                            self.running = False
                            
                    # Lógica mientras juegas y lees mensajes
                    elif self.human_player:
                        if self.animating_blocking:
                            continue
                            
                        # Permitimos avanzar mensajes INCLUSO si la batalla ya terminó (para ver quién ganó)
                        if self.message_queue or (self.current_message and not self.waiting_for_player_action and not self.waiting_for_player_switch):
                             self._advance_message()
                             
                        # Las acciones de combate (Lucha/Cambio) SOLO si la batalla sigue activa
                        elif not self.battle_finished:
                            if self.waiting_for_player_action:
                                if not self.showing_moves:
                                    if self.btn_lucha.collidepoint(event.pos):
                                        self.showing_moves = True
                                    elif self.btn_pokemon.collidepoint(event.pos):
                                        self.waiting_for_player_switch = True
                                        self.waiting_for_player_action = False
                                else:
                                    clicked_move = False
                                    for rect in self.move_buttons:
                                        if rect.collidepoint(event.pos):
                                            clicked_move = True
                                            break
                                    if not clicked_move:
                                        self.showing_moves = False
                                    else:
                                        self._handle_move_click(event.pos)
                            elif self.waiting_for_player_switch:
                                self._handle_switch_click(event.pos)

            if self.animating_blocking:
                anim_p1_done = True
                if self.p1_fainted:
                    if now - self.p1_fainted_anim_start < self.faint_anim_duration:
                        anim_p1_done = False
                elif self.p1_switching_anim:
                    if now - self.switch_anim_start < self.switch_anim_duration:
                        anim_p1_done = False
                    else:
                        self.p1_switching_anim = False
                
                anim_p2_done = True
                if self.p2_fainted:
                    if now - self.p2_fainted_anim_start < self.faint_anim_duration:
                        anim_p2_done = False
                elif self.p2_switching_anim:
                    if now - self.switch_anim_start < self.switch_anim_duration:
                        anim_p2_done = False
                    else:
                        self.p2_switching_anim = False
                        
                if anim_p1_done and anim_p2_done:
                    self.animating_blocking = False
                    if self.battle_finished and not self.message_queue:
                         pass

            if not self.animating_blocking:
                if self.auto_mode:
                    if self.message_queue or (self.current_message and not self.waiting_for_player_action and not self.waiting_for_player_switch and not self.battle_finished):
                        if now - self.message_display_time > self.message_duration:
                            self._advance_message()
                    else:
                        if not self.battle_finished and not self.waiting_for_player_action and not self.waiting_for_player_switch:
                            if now - self.last_turn_time >= self.turn_interval:
                                self._process_full_turn()
                                self._advance_message() 
                                self.last_turn_time = now

            # --- DIBUJO DE PANTALLAS ---
            self.renderer.clear_screen((20, 20, 25))

            if self.bg_battle:
                self.screen.blit(self.bg_battle, (0, 0))

            pygame.draw.line(self.screen, (0, 0, 0), (0, self.top_h), (self.sw, self.top_h), 10)
            pygame.draw.rect(self.screen, (230, 240, 245), (0, self.top_h + 5, self.sw, self.bottom_h))

            # Capturar Pokémon Visual
            active_p1 = self.p1_team[self.p1_visual_idx]
            active_p2 = self.p2_team[self.p2_visual_idx]
            
            if self.p1_display_hp == -1:
                self.p1_display_hp = active_p1.current_hp
                self.p1_target_hp = active_p1.current_hp
            if self.p2_display_hp == -1:
                self.p2_display_hp = active_p2.current_hp
                self.p2_target_hp = active_p2.current_hp

            # Disminución progresiva del HP
            hp_speed_1 = max(1, active_p1.max_hp // 50)
            if self.p1_display_hp > self.p1_target_hp:
                self.p1_display_hp = max(self.p1_target_hp, self.p1_display_hp - hp_speed_1)
            elif self.p1_display_hp < self.p1_target_hp:
                self.p1_display_hp = min(self.p1_target_hp, self.p1_display_hp + hp_speed_1)
                
            hp_speed_2 = max(1, active_p2.max_hp // 50)
            if self.p2_display_hp > self.p2_target_hp:
                self.p2_display_hp = max(self.p2_target_hp, self.p2_display_hp - hp_speed_2)
            elif self.p2_display_hp < self.p2_target_hp:
                self.p2_display_hp = min(self.p2_target_hp, self.p2_display_hp + hp_speed_2)

            draw_p1_name = self.p1_next_id if self.p1_switching_anim else (self.p1_fainted_id if self.p1_fainted else active_p1.name)
            draw_p2_name = self.p2_next_id if self.p2_switching_anim else (self.p2_fainted_id if self.p2_fainted else active_p2.name)

            img_p1_back = self.renderer.load_battle_sprite(
                draw_p1_name,
                os.path.join('assets', 'sprites_back', f"{draw_p1_name}.png"),
                is_back=True
            )
            img_p2_front = self.renderer.load_battle_sprite(
                draw_p2_name,
                os.path.join('assets', 'sprites', f"{draw_p2_name}.png"),
                is_back=False
            )
            
            # --- Animaciones P2 ---
            show_p2 = True
            p2_y_offset = 0
            if self.p2_fainted:
                elapsed_faint = now - self.p2_fainted_anim_start
                if elapsed_faint < self.faint_anim_duration:
                    p2_y_offset = int((elapsed_faint / self.faint_anim_duration) * 200)
                else:
                    show_p2 = False # <--- CORRECCIÓN ZOMBIE P2: El Pokémon ya no resucita.
            elif self.p2_animating_damage:
                elapsed = now - self.p2_animation_start
                if elapsed > self.animation_duration:
                    self.p2_animating_damage = False
                else:
                    if int(elapsed * 10) % 2 == 0:
                        show_p2 = False
            elif self.p2_switching_anim:
                elapsed_switch = now - self.switch_anim_start
                if elapsed_switch < self.switch_anim_duration / 2:
                    if self.pokeball_img:
                        self.screen.blit(self.pokeball_img, (650, 200))
                    show_p2 = False
                else:
                    show_p2 = True
            
            if img_p2_front and show_p2:
                self.screen.blit(img_p2_front, (600, 150 + p2_y_offset))
            
            # --- Animaciones P1 ---
            show_p1 = True
            p1_y_offset = 0
            if self.p1_fainted:
                elapsed_faint = now - self.p1_fainted_anim_start
                if elapsed_faint < self.faint_anim_duration:
                    p1_y_offset = int((elapsed_faint / self.faint_anim_duration) * 200)
                else:
                    show_p1 = False # <--- CORRECCIÓN ZOMBIE P1: El Pokémon ya no resucita.
            elif self.p1_animating_damage:
                elapsed = now - self.p1_animation_start
                if elapsed > self.animation_duration:
                    self.p1_animating_damage = False
                else:
                    if int(elapsed * 10) % 2 == 0:
                        show_p1 = False
            elif self.p1_switching_anim:
                elapsed_switch = now - self.switch_anim_start
                if elapsed_switch < self.switch_anim_duration / 2:
                    if self.pokeball_img:
                        self.screen.blit(self.pokeball_img, (200, 400))
                    show_p1 = False
                else:
                    show_p1 = True

            if img_p1_back and show_p1:
                self.screen.blit(img_p1_back, (100, self.top_h - 200 + p1_y_offset))

            self.renderer.draw_health_bar(30, 30, draw_p2_name, int(self.p2_display_hp), active_p2.max_hp, level=50, is_player=False, status=active_p2.status_ailment)
            self.renderer.draw_health_bar(self.sw - 350, self.top_h - 100, draw_p1_name, int(self.p1_display_hp), active_p1.max_hp, level=50, is_player=True, status=active_p1.status_ailment)

            if self.human_player and not self.battle_finished:
                if self.waiting_for_player_action:
                    if self.showing_moves:
                        move_data = self._get_active_move_data()
                        self._draw_move_buttons(mouse_pos, move_data)
                    else:
                        self._draw_main_dialog_box()
                        self._draw_action_buttons(mouse_pos)
                elif self.waiting_for_player_switch:
                    self._draw_switch_options(mouse_pos)
                else:
                    self._draw_full_dialog_box()
            else:
                self._draw_full_dialog_box()

            if self.battle_finished and not self.message_queue and not self.animating_blocking:
                overlay = pygame.Surface((self.sw, self.sh))
                overlay.set_alpha(150)
                overlay.fill((0, 0, 0))
                self.screen.blit(overlay, (0, 0))
                
                self.renderer.draw_text("FIN DEL COMBATE", 'title', (255, 215, 0), self.sw//2, self.sh//2 - 100, center=True)

                self.renderer.draw_button(self.btn_replay, "Repetir", self.btn_replay.collidepoint(mouse_pos))
                self.renderer.draw_button(self.btn_menu, "Ir al Menú", self.btn_menu.collidepoint(mouse_pos))

            pygame.display.flip()
            self.clock.tick(60)
            
        return self.action_after_battle

    def _draw_main_dialog_box(self):
        pygame.draw.rect(self.screen, (240, 240, 240), self.main_dialog_rect, border_radius=10)
        pygame.draw.rect(self.screen, (50, 50, 150), self.main_dialog_rect, width=6, border_radius=10)
        
        if self.current_message:
            font = self.renderer.font_subtitle
            max_text_width = self.main_dialog_rect.width - 40
            wrapped_lines = self.renderer._wrap_text(str(self.current_message), font, max_text_width)

            max_lines = 3
            line_height = font.get_height() + 4
            start_y = self.main_dialog_rect.y + 20

            for i, line in enumerate(wrapped_lines[:max_lines]):
                y = start_y + i * line_height
                shadow_surface = font.render(line, True, (180, 180, 180))
                text_surface = font.render(line, True, (40, 40, 40))
                self.screen.blit(shadow_surface, (self.main_dialog_rect.x + 22, y + 2))
                self.screen.blit(text_surface, (self.main_dialog_rect.x + 20, y))

    def _draw_full_dialog_box(self):
        full_rect = pygame.Rect(20, self.top_h + 20, self.sw - 40, self.bottom_h - 40)
        pygame.draw.rect(self.screen, (240, 240, 240), full_rect, border_radius=10)
        pygame.draw.rect(self.screen, (50, 50, 150), full_rect, width=6, border_radius=10)

        if self.current_message:
            font = self.renderer.font_subtitle
            max_text_width = full_rect.width - 40
            wrapped_lines = self.renderer._wrap_text(str(self.current_message), font, max_text_width)

            max_lines = 5
            line_height = font.get_height() + 4
            start_y = full_rect.y + 20

            for i, line in enumerate(wrapped_lines[:max_lines]):
                y = start_y + i * line_height
                shadow_surface = font.render(line, True, (180, 180, 180))
                text_surface = font.render(line, True, (40, 40, 40))
                self.screen.blit(shadow_surface, (full_rect.x + 22, y + 2))
                self.screen.blit(text_surface, (full_rect.x + 20, y))


    def _draw_action_buttons(self, mouse_pos):
        is_hovered_lucha = self.btn_lucha.collidepoint(mouse_pos)
        self._draw_colored_button(self.btn_lucha, "LUCHA", is_hovered_lucha, (210, 60, 60))
        
        is_hovered_pokemon = self.btn_pokemon.collidepoint(mouse_pos)
        self._draw_colored_button(self.btn_pokemon, "POKéMON", is_hovered_pokemon, (60, 210, 60))

    def _draw_colored_button(self, rect, text, is_hovered, base_color, sub_text=None, font_override=None, text_offset_y=0):
        button_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        if is_hovered:
            bg_color = (min(255, base_color[0] + 40), min(255, base_color[1] + 40), min(255, base_color[2] + 40), 255)
            border_color = (255, 255, 255, 255)
        else:
            bg_color = (base_color[0], base_color[1], base_color[2], 255)
            border_color = (min(255, base_color[0] + 60), min(255, base_color[1] + 60), min(255, base_color[2] + 60), 255)

        pygame.draw.rect(button_surface, bg_color, button_surface.get_rect(), border_radius=15)
        pygame.draw.rect(button_surface, border_color, button_surface.get_rect(), width=4, border_radius=15)
        
        self.screen.blit(button_surface, (rect.x, rect.y))
        
        font = font_override if font_override else self.renderer.font_title
        
        if sub_text:
            if not font_override:
                font = self.renderer.font_subtitle
                
            shadow_surface = font.render(text, True, (50, 50, 50))
            text_surface = font.render(text, True, (255, 255, 255))
            
            sub_font = self.renderer.font_small
            sub_shadow = sub_font.render(sub_text, True, (50, 50, 50))
            sub_surf = sub_font.render(sub_text, True, (255, 255, 255))
            
            x = rect.centerx - text_surface.get_width() // 2
            y = rect.centery - text_surface.get_height() // 2 - 8 + text_offset_y
            self.screen.blit(shadow_surface, (x + 2, y + 2))
            self.screen.blit(text_surface, (x, y))
            
            sx = rect.centerx - sub_surf.get_width() // 2
            sy = rect.centery - sub_surf.get_height() // 2 + 12 + text_offset_y
            self.screen.blit(sub_shadow, (sx + 2, sy + 2))
            self.screen.blit(sub_surf, (sx, sy))
        else:
            shadow_surface = font.render(text, True, (50, 50, 50))
            text_surface = font.render(text, True, (255, 255, 255))
            
            x = rect.centerx - text_surface.get_width() // 2
            y = rect.centery - text_surface.get_height() // 2 + text_offset_y
            self.screen.blit(shadow_surface, (x + 2, y + 2))
            self.screen.blit(text_surface, (x, y))


    def _process_full_turn(self, player_action: Action = None):
        if self.battle_finished:
            return

        state = self._build_battle_state()

        if self.human_player and not self.auto_mode:
            if player_action is None:
                return
        else:
            if player_action is None:
                player_action = self.agent_p1.get_action(state)

        ai_action = self.agent_p2.get_action(state)

        pre_turn_p1_name = self.p1_team[self.p1_active_idx].name
        pre_turn_p2_name = self.p2_team[self.p2_active_idx].name

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
        self.showing_moves = False
        
        if self.p1_team[self.p1_active_idx].current_hp > 0:
             self.p1_fainted = False
        if self.p2_team[self.p2_active_idx].current_hp > 0:
             self.p2_fainted = False

        self._describe_outcomes(result.outcomes, pre_turn_p1_name, pre_turn_p2_name)

        if result.match_over:
            self.battle_finished = True
            self.auto_mode = False
            if result.winner == 1:
                self.message_queue.append({"text": "¡El jugador ha ganado la batalla!"})
            elif result.winner == 2:
                self.message_queue.append({"text": "¡La IA ha ganado la batalla!"})
            else:
                self.message_queue.append({"text": "Resultado: empate."})

    def _draw_move_buttons(self, mouse_pos, move_data=None):
        if move_data is None:
            move_data = self._get_active_move_data()

        enabled = self.waiting_for_player_action and not self.battle_finished

        moves_bg = pygame.Rect(10, self.top_h + 10, self.sw - 20, self.bottom_h - 20)
        pygame.draw.rect(self.screen, (200, 220, 240), moves_bg, border_radius=10)
            
        for i, rect in enumerate(self.move_buttons):
            has_move = i < len(move_data)
            hovered = enabled and has_move and rect.collidepoint(mouse_pos)

            disabled = not enabled or not has_move
            if not disabled and has_move:
                mv = move_data[i]
                pp = getattr(mv, 'current_pp', None)
                if pp is not None and pp <= 0:
                    disabled = True

            if has_move:
                mv = move_data[i]
                name = getattr(mv, 'name', 'Movimiento')
                pp = getattr(mv, 'current_pp', 0)
                max_pp = getattr(mv, 'max_pp', 0)
                
                self._draw_colored_button(
                    rect, 
                    name, 
                    hovered, 
                    (200, 200, 200) if disabled else (240, 240, 240),
                    font_override=self.renderer.font_subtitle,
                    text_offset_y=-8
                )
                
                if not disabled:
                    pp_str = f"PP {pp}/{max_pp}"
                    font = self.renderer.font_small 
                    pp_surf = font.render(pp_str, True, (60, 60, 60))
                    
                    self.screen.blit(pp_surf, (rect.centerx - pp_surf.get_width() // 2, rect.bottom - pp_surf.get_height() - 8))
            else:
                self._draw_colored_button(rect, "-", False, (200, 200, 200))

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
                    self.message_queue.append({"text": "¡Ese movimiento no tiene PP! Elige otro."})
                    self.showing_moves = False
                    self._advance_message()
                    return

                action = Action(type=ActionType.MOVE, target_index=i)
                self.player_pending_action = action
                self.waiting_for_player_action = False
                self.showing_moves = False
                self._process_full_turn(player_action=action)
                self._advance_message()
                return

    def _draw_switch_options(self, mouse_pos):
        available_pokemon = []
        for i, pkm in enumerate(self.p1_team):
            if pkm.current_hp > 0 and i != self.p1_visual_idx:
                available_pokemon.append((i, pkm))
        
        btn_w = 200
        btn_h = 60
        pad = 20
        
        start_x = (self.sw - (len(available_pokemon) * btn_w + (len(available_pokemon) - 1) * pad)) // 2
        start_y = self.top_h + (self.bottom_h - btn_h) // 2

        self.switch_buttons_rects = []
        
        switch_bg = pygame.Rect(10, self.top_h + 10, self.sw - 20, self.bottom_h - 20)
        pygame.draw.rect(self.screen, (200, 240, 200), switch_bg, border_radius=10)
        self.renderer.draw_text("Elige un Pokémon:", 'subtitle', (40, 40, 40), self.sw//2, self.top_h + 30, center=True, shadow=False)

        for i, (idx, pkm) in enumerate(available_pokemon):
            rect = pygame.Rect(start_x + i * (btn_w + pad), start_y, btn_w, btn_h)
            self.switch_buttons_rects.append((rect, idx))
            
            is_hovered = rect.collidepoint(mouse_pos)
            
            hp_text = f"HP: {pkm.current_hp}/{pkm.max_hp}"
            self._draw_colored_button(rect, pkm.name.capitalize(), is_hovered, (80, 200, 80), sub_text=hp_text, font_override=self.renderer.font_subtitle)

    def _handle_switch_click(self, mouse_pos):
        for rect, pkm_idx in self.switch_buttons_rects:
            if rect.collidepoint(mouse_pos):
                if self.p1_team[self.p1_active_idx].current_hp > 0:
                    action = Action(type=ActionType.SWITCH, target_index=pkm_idx)
                    self.player_pending_action = action
                    self.waiting_for_player_action = False
                    self.showing_moves = False
                    self._process_full_turn(player_action=action)
                    self._advance_message()
                else:
                    self.message_queue.append({
                        "text": f"¡Adelante, {self.p1_team[pkm_idx].name.capitalize()}!", 
                        "trigger_anim": "p1_switch",
                        "idx": pkm_idx,
                        "id": self.p1_team[pkm_idx].name
                    })
                    self.p1_active_idx = pkm_idx
                    self.waiting_for_player_switch = False
                    self._advance_message()
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
                self.message_queue.append({
                    "text": f"¡La IA envió a {team[new_active_idx].name.capitalize()}!",
                    "trigger_anim": "p1_switch",
                    "idx": new_active_idx,
                    "id": team[new_active_idx].name
                })
                self.p1_active_idx = new_active_idx
            else:
                self.message_queue.append({
                    "text": f"¡La IA envió a {team[new_active_idx].name.capitalize()}!",
                    "trigger_anim": "p2_switch",
                    "idx": new_active_idx,
                    "id": team[new_active_idx].name
                })
                self.p2_active_idx = new_active_idx