import pygame
import random
import os
from src.utils.data_loader import DataLoader
from src.gui.battle_ui import BattleScreen
from src.entities.enums import AilmentType

class PlayerSprite(pygame.sprite.Sprite):
    def __init__(self, x, y, sprite_sheet_path):
        super().__init__()
        
        # Detalles de los cuadros de animación (frames)
        self.frame_width = 424
        self.frame_height = 632
        self.columns = 4
        self.rows = 4
        
        # Diccionario para almacenar las animaciones según la dirección
        self.animations = {
            'down': [],   # Fila 0
            'up': [],     # Fila 1
            'left': [],   # Fila 2
            'right': []   # Fila 3
        }
        self.load_sprites(sprite_sheet_path)
        
        # Estado inicial (mirando hacia abajo, en reposo)
        self.direction = 'down'
        self.current_frame = 0
        self.image = self.animations[self.direction][self.current_frame]
        self.rect = self.image.get_rect(center=(x, y))
        
        # Atributos de movimiento
        self.speed = 5
        self.is_moving = False
        
        # Temporizador para la animación
        self.last_update = pygame.time.get_ticks()
        self.frame_rate = 150 # Tiempo en milisegundos entre cada fotograma

    def load_sprites(self, path):
        """Carga y extrae (slice) la hoja de sprites."""
        if os.path.exists(path):
            print(f"[INFO] Cargando hoja de sprites desde: {path}")
            # Usar convert_alpha() garantiza un canal alfa (transparencia real)
            sheet = pygame.image.load(path).convert_alpha()
            
            # Calculamos dinámicamente las dimensiones exactas por si la imagen fue redimensionada
            self.frame_width = sheet.get_width() // self.columns
            self.frame_height = sheet.get_height() // self.rows
            
            # Tomamos la muestra en (2,2) para evitar cualquier línea de cuadrícula en el borde exacto
            bg_color = sheet.get_at((2, 2)) 
            
            # Usamos PixelArray para reemplazar el beige por transparente al instante.
            # Esto es más seguro que set_colorkey porque no se pierde al usar transform.scale()
            pixels = pygame.PixelArray(sheet)
            pixels.replace(bg_color, (0, 0, 0, 0))
            pixels.close() # Siempre debemos cerrarlo antes de usar la imagen
        else:
            print(f"[AVISO] No se encontró la hoja de sprites en {path}. Usando un bloque de color.")
            sheet = pygame.Surface((self.frame_width * self.columns, self.frame_height * self.rows), pygame.SRCALPHA)
            sheet.fill((50, 150, 255))
            
        # Asignación estricta a las filas: 0=Abajo, 1=Arriba, 2=Derecha (Fila 3), 3=Izquierda (Fila 4)
        directions = ['down', 'up', 'right', 'left']
        
        for row in range(self.rows):
            for col in range(self.columns):
                # Coordenadas dinámicas basadas en las medidas reales de la imagen
                x = col * self.frame_width
                y = row * self.frame_height
                
                # Crear el rectángulo para hacer slice
                rect = pygame.Rect(x, y, self.frame_width, self.frame_height)
                
                # Extraemos el fotograma usando subsurface y hacemos una copia limpia
                image = sheet.subsurface(rect).copy()
                
                # Escalamos la imagen a un tamaño manejable para la pantalla (64x96)
                image = pygame.transform.scale(image, (64, 96))
                
                self.animations[directions[row]].append(image)
                
    def update(self, keys, bounds_rect):
        """Actualiza la posición y calcula la dirección del jugador."""
        self.is_moving = False
        dx = 0
        dy = 0
        
        # Evaluamos el Eje X (Filas 2 y 3) de manera independiente
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -self.speed
            self.direction = 'left'  # Usa estrictamente la Fila 4 (Y=1896)
            self.is_moving = True
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = self.speed
            self.direction = 'right' # Usa estrictamente la Fila 3 (Y=1264)
            self.is_moving = True
            
        # Evaluamos el Eje Y (Filas 0 y 1) de manera independiente
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -self.speed
            if dx == 0:  # Si no se mueve a los lados, mira hacia arriba
                self.direction = 'up'    # Usa estrictamente la Fila 1 (Y=632)
            self.is_moving = True
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = self.speed
            if dx == 0:  # Si no se mueve a los lados, mira hacia abajo
                self.direction = 'down'  # Usa estrictamente la Fila 0 (Y=0)
            self.is_moving = True

        # Aplicar el movimiento
        self.rect.x += dx
        self.rect.y += dy
        
        # Mantener al jugador dentro de los límites pasados (room_rect)
        self.rect.clamp_ip(bounds_rect)

        # Alternar fotogramas
        self.animate()

    def animate(self):
        """Maneja el cambio de fotogramas (animación) con el temporizador."""
        now = pygame.time.get_ticks()
        
        if self.is_moving:
            if now - self.last_update > self.frame_rate:
                self.last_update = now
                self.current_frame = (self.current_frame + 1) % self.columns
                self.image = self.animations[self.direction][self.current_frame]
        else:
            # Si no se mueve, muestra el fotograma de reposo (columna 0) en su última dirección
            self.current_frame = 0
            self.image = self.animations[self.direction][self.current_frame]

class MapManager:
    """
    Gestor dedicado para cargar y procesar la progresión de los fondos del Alto Mando.
    Carga imágenes individuales de alta calidad para cada escenario.
    """
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        
        # Nombres asignados directamente como el archivo .png del escenario respectivo
        self.rooms_data = [
            {"name": "sobrevilla"},
            {"name": "maguiña"},
            {"name": "salinas"},
            {"name": "gamarra"},
            {"name": "cortez"},
            {"name": "hall_of_fame"}
        ]
        
        # Máquina de estados: Comienza estrictamente en 0 (Lorelei)
        self.current_room_index = 0
        self.loaded_backgrounds = {}

    def get_current_room_surface(self, target_size: tuple) -> pygame.Surface:
        """
        Obtiene la imagen de la sala actual cargándola desde su archivo individual, 
        y la escala para encajar limpiamente en la pantalla del juego.
        """
        room_name = self.rooms_data[self.current_room_index]["name"]
        
        if room_name not in self.loaded_backgrounds:
            # Intentamos buscar en assets/sprites/ o assets/
            path_sprites = os.path.join(self.base_dir, 'assets', 'sprites', f"{room_name}.png")
            path_assets = os.path.join(self.base_dir, 'assets', f"{room_name}.png")
            
            if os.path.exists(path_sprites):
                print(f"[INFO] Cargando fondo desde: {path_sprites}")
                img = pygame.image.load(path_sprites).convert()
            elif os.path.exists(path_assets):
                print(f"[INFO] Cargando fondo desde: {path_assets}")
                img = pygame.image.load(path_assets).convert()
            else:
                print(f"[AVISO] No se encontró el fondo {room_name}.png. Usando color sólido.")
                img = pygame.Surface(target_size)
                img.fill((40, 40, 50))
                
            self.loaded_backgrounds[room_name] = img
            
        room_surface = self.loaded_backgrounds[room_name]
        return pygame.transform.scale(room_surface, target_size)

    def transition_to_next_room(self, player_sprite, screen_width, screen_height):
        """
        Función de Transición/Carga: Se ejecuta bajo condición de VICTORIA.
        Aumenta el índice de la sala y reinicia la posición lógica del jugador.
        """
        if self.current_room_index < len(self.rooms_data) - 1:
            self.current_room_index += 1
            
            # Reiniciar la posición lógica del jugador (entrada inferior de la sala)
            if player_sprite is not None:
                player_sprite.rect.centerx = screen_width // 2
                player_sprite.rect.bottom = screen_height - 100
            
            print(f"[INFO] Transición a: {self.rooms_data[self.current_room_index]['name']}")
            return True
        return False

class LeagueRoom:
    def __init__(self, screen, renderer, room_index, map_manager):
        self.screen = screen
        self.renderer = renderer
        self.room_index = room_index
        self.map_manager = map_manager
        self.clock = pygame.time.Clock()
        
        # Inicializar al jugador con la clase PlayerSprite
        # Resolvemos la ruta absoluta de manera segura para evitar errores de directorio
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        player_sprite_path = os.path.join(base_dir, 'assets', 'sprites', 'jugador.png')
        self.player = PlayerSprite(screen.get_width() // 2, screen.get_height() - 100, player_sprite_path)
        self.sprites_group = pygame.sprite.Group(self.player)
        
        # Coordenadas y atributos del NPC (Alto Mando / Campeón)
        self.npc_size = 50
        self.npc_x = screen.get_width() // 2
        self.npc_y = 150
        
        # Intentar cargar la imagen del NPC correspondiente
        room_name = self.map_manager.rooms_data[self.room_index]["name"]
        npc_image_path = os.path.join(base_dir, 'assets', 'sprites', f"npc_{room_name}.png")
        
        if os.path.exists(npc_image_path):
            self.npc_sprite = pygame.image.load(npc_image_path).convert_alpha()
            self.npc_sprite = pygame.transform.scale(self.npc_sprite, (75, 80)) # Tamaño ajustado (más ancho)
        else:
            self.npc_sprite = None
        
        self.running = True
        self.start_battle = False
        
    def run(self):
        while self.running:
            # 1. Dibujar el fondo gestionado por MapManager
            room_bg = self.map_manager.get_current_room_surface((self.screen.get_width(), self.screen.get_height()))
            self.screen.blit(room_bg, (0, 0))
            
            # Creamos bordes virtuales para mantener al jugador dentro del mapa
            room_rect = pygame.Rect(50, 50, self.screen.get_width() - 100, self.screen.get_height() - 100)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.KEYDOWN:
                    # Interacción al presionar ENTER, ESPACIO o Z
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                        if self.room_index == 5:
                            # En el Salón de la Fama puedes presionar ENTER desde cualquier lugar
                            self.start_battle = True
                            self.running = False
                        else:
                            dist = ((self.player.rect.centerx - self.npc_x)**2 + (self.player.rect.centery - self.npc_y)**2)**0.5
                            if dist < 80: # Distancia de interacción
                                self.start_battle = True
                                self.running = False
                            
            # Obtener inputs del teclado
            keys = pygame.key.get_pressed()
            
            # Actualizar lógica y animación del jugador pasándole los límites de la sala
            self.player.update(keys, room_rect)
            
            # Dibujar NPC o Puerta de avance (Dependiendo del tipo de sala)
            if self.room_index == 5:
                titulo = "Salón de la Fama"
                sub_text = "¡Felicidades! Presiona ENTER para registrarte en el Salón"
            else:
                titulo = f"Batalla Alto Mando: {self.map_manager.rooms_data[self.room_index]['name'].capitalize()}"
                sub_text = "Acércate al rival y presiona ENTER para luchar"
                
                if self.npc_sprite:
                    sprite_x = self.npc_x - self.npc_sprite.get_width() // 2
                    sprite_y = self.npc_y - self.npc_sprite.get_height() // 2
                    self.screen.blit(self.npc_sprite, (sprite_x, sprite_y))
                else:
                    npc_color = (255, 215, 0) if self.room_index == 4 else (255, 60, 60) # Dorado para Campeón
                    pygame.draw.rect(self.screen, npc_color, (self.npc_x - self.npc_size//2, self.npc_y - self.npc_size//2, self.npc_size, self.npc_size))
            
            # Dibujar al jugador (el grupo Group() maneja internamente el uso de .image y .rect)
            self.sprites_group.draw(self.screen)
            
            # Textos guía
            self.renderer.draw_text(titulo, 'title', (255, 215, 0), self.screen.get_width()//2, 20, center=True)
            self.renderer.draw_text(sub_text, 'subtitle', (200, 200, 200), self.screen.get_width()//2, self.screen.get_height() - 25, center=True)
            
            pygame.display.flip()
            self.clock.tick(60)
            
        return self.start_battle

class LeagueManager:
    def __init__(self, screen, renderer, p1_team_names):
        self.screen = screen
        self.renderer = renderer
        self.p1_team_names = p1_team_names
        self.loader = DataLoader('data/pokemon_pool.json', 'data/moves_pool.json')
        
        # Instanciar el equipo del jugador una sola vez para PRESERVAR EL HP entre batallas
        name_to_id = {p['name']: p.get('poke_id', None) for p in self.loader.pokemon_data}
        self.p1_team_instances = []
        for name in self.p1_team_names:
            pid = name_to_id.get(name)
            if pid is None:
                pid = random.choice(self.loader.pokemon_data)['poke_id']
            try:
                self.p1_team_instances.append(self.loader.create_battle_pokemon(pid))
            except Exception:
                pass
        
        self.current_room = 0
        self.max_rooms = 6 # Progresión actualizada a 6 mapas (Lorelei -> Hall of Fame)
        
        # IA asignada para las 5 verdaderas batallas de la sala 0 (IA1) a la 4 (IA5)
        self.ai_levels = [1, 2, 3, 4, 5]
        
        # Cargar MapManager pasándole el directorio base del proyecto
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.map_manager = MapManager(base_dir)
        
    def _generate_npc_team(self, room_index):
        pool_ids = [p['poke_id'] for p in self.loader.pokemon_data]
        p2_team = []
        
        team_size = len(self.p1_team_instances)
        
        # Evitar Pokémon repetidos (que daban la ilusión de ser inmortales)
        selected_ids = random.sample(pool_ids, min(team_size, len(pool_ids)))
        for pid in selected_ids:
            p2_team.append(self.loader.create_battle_pokemon(pid))
        return p2_team

    def run(self):
        while self.current_room < self.max_rooms:
            # Sincronizamos la máquina de estados del gestor visual con la real
            self.map_manager.current_room_index = self.current_room
            
            # 1. Fase Exploración (Overworld 2D)
            room = LeagueRoom(self.screen, self.renderer, self.current_room, self.map_manager)
            wants_to_battle = room.run()
            
            if not wants_to_battle:
                return "MENU"
                
            # 2. Fase Interacción/Batalla (Depende del tipo de sala)
            if self.current_room in [0, 1, 2, 3, 4]:
                p2_team_instances = self._generate_npc_team(self.current_room)
                difficulty = self.ai_levels[self.current_room] # Ajuste directo para IA [1,2,3,4,5]
                
                # Iniciar música de batalla
                ruta_musica_batalla = os.path.join(self.map_manager.base_dir, 'assets', 'music', 'battle_theme.mp3')
                try:
                    if pygame.mixer.get_init() and os.path.exists(ruta_musica_batalla):
                        pygame.mixer.music.load(ruta_musica_batalla)
                        pygame.mixer.music.play(-1)
                except Exception as e:
                    print(f"[AVISO] No se pudo reproducir música de batalla en el Alto Mando: {e}")

                battle = BattleScreen(self.screen, self.renderer, self.p1_team_names, difficulty, "Alto Mando", 
                                      p1_team_instances=self.p1_team_instances, p2_team_instances=p2_team_instances)
                post_battle = battle.run()
                
                # Detener música al terminar el combate
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                except Exception:
                    pass

                if post_battle == "MENU":
                    player_alive = any(p.current_hp > 0 for p in self.p1_team_instances)
                    npc_alive = any(p.current_hp > 0 for p in p2_team_instances)
                    
                    if player_alive and not npc_alive:
                        # Función de transición de carga (VICTORIA)
                        self.map_manager.transition_to_next_room(None, self.screen.get_width(), self.screen.get_height())
                        self.current_room = self.map_manager.current_room_index
                        
                        # Recuperar toda la vida, curar estados y revivir a los Pokémon debilitados
                        for pkm in self.p1_team_instances:
                            pkm.current_hp = pkm.max_hp
                            pkm.status_ailment = AilmentType.NONE
                            for move in getattr(pkm, 'moves', []):
                                move.current_pp = getattr(move, 'max_pp', move.current_pp)
                    else:
                        return "MENU" 
                elif post_battle == "REPLAY":
                    return "MENU"
                    
            elif self.current_room == 5:
                # Hall of Fame finalizado
                return "CHAMPION"

        return "CHAMPION"