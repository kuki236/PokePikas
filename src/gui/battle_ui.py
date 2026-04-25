# src/gui/battle_ui.py
import pygame
import sys
import os
import json
import random

class BattleScreen:
    def __init__(self, screen, renderer, p1_team, difficulty, mode):
        self.screen = screen
        self.renderer = renderer
        self.p1_team = p1_team
        self.difficulty = difficulty
        self.mode = mode
        
        self.running = True
        self.clock = pygame.time.Clock()

        # Cargamos el fondo de la batalla (usa tu imagen del bosque o consigue una de estadio)
        self.bg_battle = self.renderer.load_background(os.path.join('assets', 'bg_modos.jpg'), self.screen.get_width(), self.screen.get_height())

        # ==========================================
        # DATOS VISUALES FALSOS (MOCKUP) PARA LA UI
        # Luego los reemplazaremos con los objetos de battle_engine.py
        # ==========================================
        # Tu Pokémon activo (el primero que elegiste)
        self.p1_active_name = p1_team[0] 
        self.p1_hp = 100
        self.p1_max_hp = 100
        
        # Leemos el JSON para sacar un rival al azar
        with open('data/pokemon_pool.json', 'r', encoding='utf-8') as f:
            pool = json.load(f)
        self.p2_active_name = random.choice(pool)['name']
        self.p2_hp = 100
        self.p2_max_hp = 100

        self.mensaje_batalla = f"¡Un {self.p2_active_name.capitalize()} salvaje apareció!"

    def run(self):
        # Cargamos las imágenes grandes antes de entrar al bucle
        img_p1_back = self.renderer.load_battle_sprite(self.p1_active_name, os.path.join('assets', 'sprites_back', f"{self.p1_active_name}.png"), is_back=True)
        img_p2_front = self.renderer.load_battle_sprite(self.p2_active_name, os.path.join('assets', 'sprites', f"{self.p2_active_name}.png"), is_back=False)

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False # Salir de la batalla
                    elif event.key == pygame.K_SPACE:
                        # Simulamos que haces daño al apretar ESPACIO (Para probar la barra de vida)
                        self.p2_hp -= 15
                        self.mensaje_batalla = f"¡{self.p1_active_name.capitalize()} usó Placaje! ¡Es muy eficaz!"
                        if self.p2_hp < 0: self.p2_hp = 0

            # 1. DIBUJAR FONDO
            self.renderer.draw_background(self.bg_battle)

            # 2. DIBUJAR SPRITES DE BATALLA
            # El rival (Frente) va arriba a la derecha
            if img_p2_front:
                self.screen.blit(img_p2_front, (600, 150))
            
            # El jugador (Espalda) va abajo a la izquierda
            if img_p1_back:
                self.screen.blit(img_p1_back, (150, 350))

            # 3. DIBUJAR BARRAS DE VIDA (HUD)
            # HUD Rival (Izquierda arriba)
            self.renderer.draw_health_bar(50, 100, self.p2_active_name, self.p2_hp, self.p2_max_hp, level=50, is_player=False)
            
            # HUD Jugador (Derecha abajo)
            self.renderer.draw_health_bar(650, 420, self.p1_active_name, self.p1_hp, self.p1_max_hp, level=50, is_player=True)

            # 4. CAJA DE DIÁLOGO
            self.renderer.draw_dialog_box(self.mensaje_batalla)

            pygame.display.flip()
            self.clock.tick(60)