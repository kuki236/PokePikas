import pygame
import sys
import json
import os
import random
from enum import Enum

# Asegurar que la carpeta raíz del proyecto esté en `sys.path`
# cuando se ejecuta `python src/gui/menu.py` directamente. Esto permite
# que imports como `from src.utils.data_loader import ...` funcionen.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from renderer import Renderer

class GameState(Enum):
    START = 1
    MODE_SELECT = 2
    TEAM_SELECT = 3
    DIFFICULTY_SELECT = 4
    BATTLE = 5

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
FPS = 60

def main():
    pygame.init()
    pygame.mixer.init() # Inicializa el módulo de música

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Pokémon Pikas - Menú")
    clock = pygame.time.Clock()

    renderer = Renderer(screen)

    # --- RUTAS DE MÚSICA Y SONIDOS ---
    ruta_musica_menu = os.path.join('assets', 'music', 'menu_theme.mp3')
    ruta_musica_batalla = os.path.join('assets', 'music', 'battle_theme.mp3')
    ruta_sonido_select = os.path.join('assets', 'music', 'select.wav.mp3')

    # --- CARGA DE SONIDOS ---
    sonido_select = None
    if os.path.exists(ruta_sonido_select):
        sonido_select = pygame.mixer.Sound(ruta_sonido_select)
        sonido_select.set_volume(1.0) # <--- VOLUMEN AL MÁXIMO
    else:
        print(f"Advertencia: No se encontró el sonido de selección en {ruta_sonido_select}")

    def reproducir_sonido_select():
        if sonido_select:
            sonido_select.play()

    # --- CARGA Y REPRODUCCIÓN DE MÚSICA DEL MENÚ ---
    if os.path.exists(ruta_musica_menu):
        pygame.mixer.music.load(ruta_musica_menu)
        pygame.mixer.music.set_volume(0.3) # Volumen de 0.0 a 1.0
        pygame.mixer.music.play(-1) # -1 hace que se repita en bucle infinito
    else:
        print(f"Advertencia: No se encontró la música del menú en {ruta_musica_menu}")

    # 1. CARGAR DATOS Y SPRITES
    pokemon_pool = []
    try:
        with open('data/pokemon_pool.json', 'r', encoding='utf-8') as f:
            pokemon_pool = json.load(f)
            
        for pkm in pokemon_pool:
            filepath = os.path.join('assets', 'sprites', f"{pkm['name']}.png")
            renderer.load_sprite(pkm['name'], filepath)
    except FileNotFoundError:
        print("Advertencia: No se encontró data/pokemon_pool.json.")

    # --- CARGA DE FONDOS ---
    bg_start  = renderer.load_background(os.path.join('assets', 'start_bg.jpg'), WINDOW_WIDTH, WINDOW_HEIGHT)
    bg_modos  = renderer.load_background(os.path.join('assets', 'bg_modos.jpg'), WINDOW_WIDTH, WINDOW_HEIGHT)
    bg_equipo = renderer.load_background(os.path.join('assets', 'bg_equipos.jpg'), WINDOW_WIDTH, WINDOW_HEIGHT)
    bg_nivel  = renderer.load_background(os.path.join('assets', 'bg_nivel.jpg'), WINDOW_WIDTH, WINDOW_HEIGHT)

    # 2. ESTADOS Y VARIABLES
    current_state = GameState.START
    selected_mode = None  
    team_size = None      
    p1_team = []          
    pc1_difficulty = None
    pc2_difficulty = None
    
    tiempo_proximo_rayo = pygame.time.get_ticks() + random.randint(3000, 8000)
    secuencia_rayo = [150, 50, 255, 100, 0] 
    paso_secuencia_actual = -1 
    color_rayo = (230, 245, 255)

    # 3. RECTÁNGULOS DE BOTONES
    btn_pve = pygame.Rect(200, 200, 280, 60) 
    btn_pvp = pygame.Rect(520, 200, 280, 60)
    btn_3v3 = pygame.Rect(320, 350, 150, 60) 
    btn_4v4 = pygame.Rect(530, 350, 150, 60)
    btn_continue_mode = pygame.Rect(WINDOW_WIDTH//2 - 125, 480, 250, 60)
    
    # ¡NUEVA POSICIÓN DEL BOTÓN CONFIRMAR! (En el panel derecho del monitor)
    btn_confirm = pygame.Rect(670, 480, 160, 60)
    
    btn_pc1_easy = pygame.Rect(WINDOW_WIDTH//2 - 250, 230, 150, 60)
    btn_pc1_med  = pygame.Rect(WINDOW_WIDTH//2 - 75, 230, 150, 60)
    btn_pc1_hard = pygame.Rect(WINDOW_WIDTH//2 + 100, 230, 150, 60)
    btn_pc2_easy = pygame.Rect(WINDOW_WIDTH//2 - 250, 400, 150, 60)
    btn_pc2_med  = pygame.Rect(WINDOW_WIDTH//2 - 75, 400, 150, 60)
    btn_pc2_hard = pygame.Rect(WINDOW_WIDTH//2 + 100, 400, 150, 60)
    
    btn_start_battle = pygame.Rect(WINDOW_WIDTH//2 - 140, WINDOW_HEIGHT - 100, 280, 70)

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        tiempo_actual = pygame.time.get_ticks() 
        
        # --- LÓGICA DE EVENTOS ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if current_state == GameState.START:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    reproducir_sonido_select()
                    current_state = GameState.MODE_SELECT

            elif current_state == GameState.MODE_SELECT:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_pve.collidepoint(mouse_pos): 
                        selected_mode = "Humano vs PC"
                        reproducir_sonido_select()
                    elif btn_pvp.collidepoint(mouse_pos): 
                        selected_mode = "PC vs PC"
                        reproducir_sonido_select()
                    elif btn_3v3.collidepoint(mouse_pos): 
                        team_size = 3
                        reproducir_sonido_select()
                    elif btn_4v4.collidepoint(mouse_pos): 
                        team_size = 4
                        reproducir_sonido_select()
                    elif btn_continue_mode.collidepoint(mouse_pos) and selected_mode and team_size:
                        reproducir_sonido_select()
                        current_state = GameState.TEAM_SELECT

            elif current_state == GameState.TEAM_SELECT:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # NUEVA MATEMÁTICA DE COLISIÓN (Cajas de 60x60, Espacio de 75)
                    start_x, start_y = 180, 160
                    spacing_x, spacing_y = 75, 75
                    
                    col = (mouse_pos[0] - start_x) // spacing_x
                    row = (mouse_pos[1] - start_y) // spacing_y
                    local_x = (mouse_pos[0] - start_x) % spacing_x
                    local_y = (mouse_pos[1] - start_y) % spacing_y
                    
                    # Validamos el clic en la nueva caja más pequeña
                    if 0 <= col < 6 and 0 <= row < 5 and local_x < 60 and local_y < 60:
                        index = row * 6 + col
                        if index < len(pokemon_pool):
                            clicked_name = pokemon_pool[index]['name']
                            if clicked_name in p1_team: 
                                p1_team.remove(clicked_name)
                                reproducir_sonido_select()
                            elif len(p1_team) < team_size: 
                                p1_team.append(clicked_name)
                                reproducir_sonido_select()
                            
                    if len(p1_team) == team_size and btn_confirm.collidepoint(mouse_pos):
                        reproducir_sonido_select()
                        current_state = GameState.DIFFICULTY_SELECT

            elif current_state == GameState.DIFFICULTY_SELECT:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_pc1_easy.collidepoint(mouse_pos): 
                        pc1_difficulty = 1
                        reproducir_sonido_select()
                    elif btn_pc1_med.collidepoint(mouse_pos): 
                        pc1_difficulty = 2
                        reproducir_sonido_select()
                    elif btn_pc1_hard.collidepoint(mouse_pos): 
                        pc1_difficulty = 3
                        reproducir_sonido_select()
                    
                    if selected_mode == "PC vs PC":
                        if btn_pc2_easy.collidepoint(mouse_pos): 
                            pc2_difficulty = 1
                            reproducir_sonido_select()
                        elif btn_pc2_med.collidepoint(mouse_pos): 
                            pc2_difficulty = 2
                            reproducir_sonido_select()
                        elif btn_pc2_hard.collidepoint(mouse_pos): 
                            pc2_difficulty = 3
                            reproducir_sonido_select()
                        
                    can_start = False
                    if selected_mode == "Humano vs PC" and pc1_difficulty is not None: can_start = True
                    elif selected_mode == "PC vs PC" and pc1_difficulty is not None and pc2_difficulty is not None: can_start = True
                    
                    if can_start and btn_start_battle.collidepoint(mouse_pos):
                        reproducir_sonido_select()
                        current_state = GameState.BATTLE
                        print("\n🔥 ¡DATOS LISTOS PARA EL MOTOR! 🔥")
                        print("="*35)
                        
                        # --- DETENER MÚSICA DE MENÚ Y REPRODUCIR LA DE BATALLA ---
                        pygame.mixer.music.stop()
                        if os.path.exists(ruta_musica_batalla):
                            pygame.mixer.music.load(ruta_musica_batalla)
                            pygame.mixer.music.play(-1)
                        else:
                            print(f"Advertencia: No se encontró la música de batalla en {ruta_musica_batalla}")


        # --- GESTOR DE RAYOS ---
        intensidad_rayo_actual = 0
        if current_state == GameState.START:
            if paso_secuencia_actual == -1:
                if tiempo_actual > tiempo_proximo_rayo: paso_secuencia_actual = 0
            if paso_secuencia_actual != -1:
                intensidad_rayo_actual = secuencia_rayo[paso_secuencia_actual]
                paso_secuencia_actual += 1
                if paso_secuencia_actual >= len(secuencia_rayo):
                    paso_secuencia_actual = -1
                    tiempo_proximo_rayo = tiempo_actual + random.randint(5000, 15000)

        # --- LÓGICA DE DIBUJADO ---
        if current_state == GameState.START:
            renderer.draw_background(bg_start)
            renderer.draw_lightning_flash(intensidad_rayo_actual, color_rayo)
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(50) 
            overlay.fill((0,0,0))
            screen.blit(overlay, (0,0))
            if pygame.time.get_ticks() % 1000 < 500:
                renderer.draw_text("Presiona ENTER para comenzar", 'subtitle', (255, 255, 255), WINDOW_WIDTH//2, WINDOW_HEIGHT - 80, center=True)

        else:
            if current_state == GameState.MODE_SELECT:
                renderer.draw_background(bg_modos, apply_dark_overlay=True)
                renderer.draw_text("CONFIGURACIÓN DE PARTIDA", 'title', (255, 204, 0), WINDOW_WIDTH//2, 80, center=True)
                renderer.draw_text("1. Elige el Modo de Juego:", 'subtitle', (255, 255, 255), WINDOW_WIDTH//2, 160, center=True)
                renderer.draw_button(btn_pve, "Humano vs PC", selected_mode == "Humano vs PC" or btn_pve.collidepoint(mouse_pos))
                renderer.draw_button(btn_pvp, "PC vs PC", selected_mode == "PC vs PC" or btn_pvp.collidepoint(mouse_pos))
                renderer.draw_text("2. Tamaño de los Equipos:", 'subtitle', (255, 255, 255), WINDOW_WIDTH//2, 310, center=True)
                renderer.draw_button(btn_3v3, "3 vs 3", team_size == 3 or btn_3v3.collidepoint(mouse_pos))
                renderer.draw_button(btn_4v4, "4 vs 4", team_size == 4 or btn_4v4.collidepoint(mouse_pos))
                if selected_mode is not None and team_size is not None:
                    renderer.draw_button(btn_continue_mode, "Continuar", btn_continue_mode.collidepoint(mouse_pos))

            elif current_state == GameState.TEAM_SELECT:
                # El fondo no se oscurece para apreciar los detalles de la máquina
                renderer.draw_background(bg_equipo, apply_dark_overlay=False)
                
                # Título arriba, en la pared gris fuera del monitor
                renderer.draw_text("SISTEMA DE ALMACENAMIENTO", 'title', (100, 255, 255), WINDOW_WIDTH//2, 40, center=True)
                
                # Contador en el panel derecho del monitor
                renderer.draw_text("Seleccionados", 'subtitle', (200, 200, 200), 750, 230, center=True)
                color_text = (100, 255, 100) if len(p1_team) == team_size else (255, 255, 255)
                renderer.draw_text(f"{len(p1_team)} / {team_size}", 'title', color_text, 750, 280, center=True)
                
                if pokemon_pool: 
                    # Coordenadas exactas para encajar en la mitad izquierda del monitor
                    renderer.draw_pokemon_grid(pokemon_pool, start_x=180, start_y=160, selected_names=p1_team, columns=6, spacing_x=75, spacing_y=75)
                
                if len(p1_team) == team_size: 
                    renderer.draw_button(btn_confirm, "Confirmar", btn_confirm.collidepoint(mouse_pos))

            elif current_state == GameState.DIFFICULTY_SELECT:
                renderer.draw_background(bg_nivel, apply_dark_overlay=True)
                renderer.draw_text("SELECCIÓN DE NIVEL", 'title', (255, 204, 0), WINDOW_WIDTH//2, 50, center=True)
                renderer.draw_text(f"Tu Equipo: {', '.join(p1_team).title()}", 'subtitle', (100, 255, 100), WINDOW_WIDTH//2, 100, center=True)
                
                if selected_mode == "Humano vs PC":
                    renderer.draw_text("Elige el nivel de la Máquina:", 'subtitle', (255, 255, 255), WINDOW_WIDTH//2, 180, center=True)
                    renderer.draw_button(btn_pc1_easy, "Nivel ★", pc1_difficulty == 1 or btn_pc1_easy.collidepoint(mouse_pos))
                    renderer.draw_button(btn_pc1_med, "Nivel ★★", pc1_difficulty == 2 or btn_pc1_med.collidepoint(mouse_pos))
                    renderer.draw_button(btn_pc1_hard, "Nivel ★★★", pc1_difficulty == 3 or btn_pc1_hard.collidepoint(mouse_pos))
                    if pc1_difficulty is not None: renderer.draw_button(btn_start_battle, "¡INICIAR BATALLA!", btn_start_battle.collidepoint(mouse_pos))
                
                elif selected_mode == "PC vs PC":
                    renderer.draw_text("Elige el nivel de la PC 1:", 'subtitle', (255, 255, 255), WINDOW_WIDTH//2, 180, center=True)
                    renderer.draw_button(btn_pc1_easy, "Nivel ★", pc1_difficulty == 1 or btn_pc1_easy.collidepoint(mouse_pos))
                    renderer.draw_button(btn_pc1_med, "Nivel ★★", pc1_difficulty == 2 or btn_pc1_med.collidepoint(mouse_pos))
                    renderer.draw_button(btn_pc1_hard, "Nivel ★★★", pc1_difficulty == 3 or btn_pc1_hard.collidepoint(mouse_pos))
                    
                    renderer.draw_text("Elige el nivel de la PC 2:", 'subtitle', (255, 255, 255), WINDOW_WIDTH//2, 350, center=True)
                    renderer.draw_button(btn_pc2_easy, "Nivel ★", pc2_difficulty == 1 or btn_pc2_easy.collidepoint(mouse_pos))
                    renderer.draw_button(btn_pc2_med, "Nivel ★★", pc2_difficulty == 2 or btn_pc2_med.collidepoint(mouse_pos))
                    renderer.draw_button(btn_pc2_hard, "Nivel ★★★", pc2_difficulty == 3 or btn_pc2_hard.collidepoint(mouse_pos))
                    if pc1_difficulty is not None and pc2_difficulty is not None: renderer.draw_button(btn_start_battle, "¡INICIAR SIMULACIÓN!", btn_start_battle.collidepoint(mouse_pos))

            elif current_state == GameState.BATTLE:
                # La lógica de cambio de música ya se ejecutó al entrar a este estado desde DIFFICULTY_SELECT
                renderer.draw_background(bg_equipo, apply_dark_overlay=True) # Esto es solo un placeholder, la pantalla de batalla tendrá su propio fondo
                
                print("\n🔥 ¡TRANSICIÓN AL MODO BATALLA! 🔥")
                
                # --- CAMBIO AQUÍ: Importación directa ---
                from battle_ui import BattleScreen
                batalla = BattleScreen(screen, renderer, p1_team, pc1_difficulty, selected_mode)
                
                # Ejecutamos el bucle de la batalla
                batalla.run() 
                
                # Cuando la batalla termine (ej. presionando ESCAPE), volvemos al estado inicial
                current_state = GameState.START
                p1_team = [] 
                pc1_difficulty = None
                pc2_difficulty = None

                # --- DETENER MÚSICA DE BATALLA Y REPRODUCIR LA DEL MENÚ ---
                pygame.mixer.music.stop()
                if os.path.exists(ruta_musica_menu):
                    pygame.mixer.music.load(ruta_musica_menu)
                    pygame.mixer.music.play(-1)
                else:
                    print(f"Advertencia: No se encontró la música del menú en {ruta_musica_menu}")

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()