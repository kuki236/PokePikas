# src/gui/renderer.py
import pygame
import os
import math
import random
from src.entities.enums import AilmentType

class Renderer:
    def __init__(self, screen):
        """
        Inicializa un objeto para manejar la renderización de texto en una pantalla de Pygame.

        Args:
            screen: La pantalla de Pygame en la que se renderizará el texto.

        Raises:
            No lanza excepciones explícitamente, pero puede fallar si no se encuentra la fuente especificada o si hay un error al inicializar Pygame.

        Nota: Esta función es un constructor y no devuelve nada explícitamente (equivale a None). Se utiliza para inicializar los atributos de la clase, incluyendo fuentes de texto y una caché de imágenes.
        """
        self.screen = screen

        ruta_fuente = os.path.join('assets', 'pokemon_pixel.ttf')

        if os.path.exists(ruta_fuente):
            self.font_title = pygame.font.Font(ruta_fuente, 30)
            self.font_subtitle = pygame.font.Font(ruta_fuente, 16)
            self.font_small = pygame.font.Font(ruta_fuente, 6) 
        else:
            self.font_title = pygame.font.SysFont("Arial", 45, bold=True)
            self.font_subtitle = pygame.font.SysFont("Arial", 26)
            self.font_small = pygame.font.SysFont("Arial", 12)

        self.image_cache = {}

    def clear_screen(self, color=(30, 30, 40)):
        """Rellena la pantalla completa con un color solido.

        Args:
            color (tuple): Color RGB a aplicar. Por defecto azul oscuro (30, 30, 40).
        """
        self.screen.fill(color)

    def load_background(self, filepath, width, height):
        """Carga y escala una imagen de fondo desde disco.

        Args:
            filepath (str): Ruta al archivo de imagen.
            width (int): Ancho objetivo al que escalar.
            height (int): Alto objetivo al que escalar.

        Returns:
            pygame.Surface | None: Superficie escalada o None si el archivo no existe.
        """
        if os.path.exists(filepath):
            img = pygame.image.load(filepath).convert()
            return pygame.transform.scale(img, (width, height))
        return None

    def draw_background(self, img, apply_dark_overlay=False):
        """
        Dibuja el fondo de la pantalla con la imagen proporcionada.

        Args:
            img: La imagen que se utilizará como fondo. (pygame.Surface)
            apply_dark_overlay (bool): Indica si se debe aplicar una capa oscura sobre la imagen de fondo. Por defecto es False.

        Returns:
            None

        Raises:
            No lanza excepciones explícitas, pero puede propagar excepciones de pygame si ocurre un error al dibujar la imagen o la capa oscura.
        """
        if img:
            self.screen.blit(img, (0, 0))
            if apply_dark_overlay:
                overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
                overlay.set_alpha(120) 
                overlay.fill((0, 0, 0))
                self.screen.blit(overlay, (0, 0))
        else:
            self.clear_screen()

    def draw_lightning_flash(self, intensity, color=(255, 255, 255)):
        """
        Dibuja un relámpago en la pantalla.

        Args:
            intensity (int): Intensidad del relámpago, donde 0 significa no se dibuja.
            color (tuple): Color del relámpago, por defecto es blanco (255, 255, 255).

        Returns:
            None

        Raises:
            No se lanzan excepciones explícitamente, pero puede lanzar errores de Pygame si no se ha iniciado correctamente o si hay problemas con la superficie de la pantalla.
        """
        if intensity > 0:
            flash_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
            flash_surface.set_alpha(intensity)
            flash_surface.fill(color)
            self.screen.blit(flash_surface, (0, 0))

    def draw_text(self, text, font_type, color, x, y, center=False, shadow=True):
        """
        Dibuja texto en la pantalla.

        Args:
            text (str): El texto a dibujar.
            font_type (str): El tipo de fuente, puede ser 'title','subtitle' o cualquier otro valor para fuente pequeña.
            color (tuple): El color del texto como tupla RGB.
            x (int): La coordenada x del texto.
            y (int): La coordenada y del texto.
            center (bool): Indica si el texto debe centrarse en la posición dada. Por defecto es False.
            shadow (bool): Indica si el texto debe tener una sombra. Por defecto es True.

        Returns:
            None

        Raises:
            No lanza excepciones.
        """
        if font_type == 'title': font = self.font_title
        elif font_type == 'subtitle': font = self.font_subtitle
        else: font = self.font_small

        surface = font.render(text, True, color)
        
        if center:
            x = x - surface.get_width() // 2
            y = y - surface.get_height() // 2

        if shadow:
            shadow_surface = font.render(text, True, (20, 20, 20))
            self.screen.blit(shadow_surface, (x + 2, y + 2))
            
        self.screen.blit(surface, (x, y))

    def draw_button(self, rect, text, is_hovered):
        """
        Dibuja un botón en la pantalla con ciertos efectos visuales cuando se pasa sobre él.

        Args:
            rect (Rect): El rectángulo que ocupa el botón.
            text (str): El texto que se muestra en el botón.
            is_hovered (bool): Indica si el cursor está sobre el botón.

        Returns:
            None

        Raises:
            None
        """
        button_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        if is_hovered:
            bg_color = (255, 180, 20, 230) 
            border_color = (255, 255, 100, 255) 
        else:
            bg_color = (200, 120, 10, 210) 
            border_color = (255, 200, 50, 255) 
            
        pygame.draw.rect(button_surface, bg_color, button_surface.get_rect(), border_radius=10)
        pygame.draw.rect(button_surface, border_color, button_surface.get_rect(), width=3, border_radius=10)
        
        self.screen.blit(button_surface, (rect.x, rect.y))
        self.draw_text(text, 'subtitle', (255, 255, 255), rect.centerx, rect.centery, center=True)

    def load_sprite(self, name, filepath):
        """
        Carga un sprite en el caché de imágenes si no existe ya, redimensionándolo a un tamaño fijo.

        Args:
            name (str): Nombre del sprite para su identificación en el caché.
            filepath (str): Ruta del archivo de imagen del sprite.

        Returns:
            pygame.Surface o None: El sprite cargado y redimensionado, o None si el archivo de imagen no existe.

        Raises:
            FileNotFoundError: Si ocurre un problema al intentar acceder al archivo de imagen en la ruta proporcionada.
            pygame.error: Si ocurre un error al cargar o procesar la imagen con Pygame.
        """
        if name not in self.image_cache:
            if os.path.exists(filepath):
                img = pygame.image.load(filepath).convert_alpha()
                self.image_cache[name] = pygame.transform.scale(img, (75, 75))
            else:
                self.image_cache[name] = None 
        return self.image_cache.get(name)

    def load_battle_sprite(self, name, filepath, is_back=False):
        """
        Descripción breve:
            Carga un sprite de batalla del archivo especificado y lo almacena en la caché de imágenes.

        Args:
            name (str): Nombre del sprite.
            filepath (str): Ruta del archivo del sprite.
            is_back (bool): Indica si el sprite es el lado trasero o no. Por defecto es False.

        Returns:
            Surface: El sprite cargado y escalado a 250x250 pixeles, o None si el archivo no existe.

        Raises:
            FileNotFoundError: Si el archivo del sprite no existe en la ruta especificada.
            pygame.Error: Si ocurre un error al cargar o procesar la imagen.
        """
        cache_key = f"battle_{'back' if is_back else 'front'}_{name}"
        if cache_key not in self.image_cache:
            if os.path.exists(filepath):
                img = pygame.image.load(filepath).convert_alpha()
                
                # Recortar el exceso de transparencia para que todos tengan un tamaño estandarizado
                bbox = img.get_bounding_rect()
                if bbox.width > 0 and bbox.height > 0:
                    img = img.subsurface(bbox)
                    
                side = max(img.get_width(), img.get_height())
                square_img = pygame.Surface((side, side), pygame.SRCALPHA)
                cx = (side - img.get_width()) // 2
                cy = side - img.get_height()
                square_img.blit(img, (cx, cy))
                
                self.image_cache[cache_key] = pygame.transform.scale(square_img, (250, 250))
            else:
                self.image_cache[cache_key] = None
        return self.image_cache.get(cache_key)
        
    def draw_pokemon_grid(self, pokemon_list, start_x, start_y, selected_names, columns=6, spacing_x=75, spacing_y=75):
        """
        Dibuja una cuadrícula de Pokémon en la pantalla.

        Args:
            pokemon_list (list): Lista de diccionarios que contienen la información de cada Pokémon.
            start_x (int): Coordenada x inicial de la cuadrícula.
            start_y (int): Coordenada y inicial de la cuadrícula.
            selected_names (list): Lista de nombres de Pokémon seleccionados.
            columns (int, optional): Número de columnas en la cuadrícula. Por defecto es 6.
            spacing_x (int, optional): Espacio horizontal entre cada celda de la cuadrícula. Por defecto es 75.
            spacing_y (int, optional): Espacio vertical entre cada celda de la cuadrícula. Por defecto es 75.

        Returns:
            None

        Raises:
            No se lanzan excepciones explícitas, pero puede generar errores si no se proporciona una lista válida de Pokémon o si no se puede cargar la imagen de un Pokémon.
        """
        for i, pkm in enumerate(pokemon_list):
            name = pkm['name']
            col = i % columns
            row = i // columns
            x = start_x + (col * spacing_x)
            y = start_y + (row * spacing_y)
            
            is_selected = name in selected_names
            bg_color = (60, 120, 60) if is_selected else (40, 40, 50)
            
            pygame.draw.rect(self.screen, bg_color, (x, y, 60, 60), border_radius=6)
            if is_selected:
                pygame.draw.rect(self.screen, (100, 255, 100), (x, y, 60, 60), width=3, border_radius=6)
                
            img = self.image_cache.get(name)
            if img:
                self.screen.blit(img, (x - 7, y - 10)) 
            
            display_name = name.capitalize().replace("-", " ")
            self.draw_text(display_name, 'small', (200, 200, 200), x + 30, y + 65, center=True)

    def _wrap_text(self, text, font, max_width):
        """
        Descripción breve:
            Esta función envuelve un texto dentro de un ancho máximo, considerando el tamaño de la fuente.

        Args:
            text (str): El texto a envolver.
            font: La fuente utilizada para medir el tamaño del texto.
            max_width (int): El ancho máximo permitido para el texto.

        Returns:
            list: Una lista de cadenas, cada una representando una línea del texto envuelto.

        Raises:
            None: No se lanzan excepciones explícitas. Sin embargo, es posible que se produzcan errores si el objeto font no tiene el método size o si max_width no es numérico.
        """
        wrapped_lines = []
        paragraphs = str(text).split('\n')

        for paragraph in paragraphs:
            if not paragraph.strip():
                wrapped_lines.append("")
                continue

            words = paragraph.split()
            current_line = words[0]

            for word in words[1:]:
                test_line = current_line + " " + word
                if font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    wrapped_lines.append(current_line)
                    current_line = word

            wrapped_lines.append(current_line)

        return wrapped_lines

    def draw_health_bar(self, x, y, name, hp, max_hp, level, is_player=False, status=AilmentType.NONE):
        """
        Dibuja una barra de salud en la pantalla.

        Args:
            x (int): La coordenada x donde se dibujará la barra de salud.
            y (int): La coordenada y donde se dibujará la barra de salud.
            name (str): El nombre del personaje o entidad que posee la barra de salud.
            hp (int): La cantidad de puntos de salud actuales.
            max_hp (int): La cantidad máxima de puntos de salud.
            level (int): El nivel del personaje o entidad.
            is_player (bool, opcional): Un indicador que especifica si la barra de salud es para el jugador. Por defecto es False.
            status (AilmentType, opcional): El estado de afectación del personaje o entidad. Por defecto es AilmentType.NONE.

        Returns:
            None

        Raises:
            None
        """
        box_rect = pygame.Rect(x, y, 280, 80)
        pygame.draw.rect(self.screen, (240, 240, 230), box_rect, border_radius=10)
        pygame.draw.rect(self.screen, (50, 50, 50), box_rect, width=3, border_radius=10)

        self.draw_text(name.upper(), 'subtitle', (30, 30, 30), x + 15, y + 10, shadow=False)
        self.draw_text(f"Lv{level}", 'subtitle', (50, 50, 50), x + 210, y + 10, shadow=False)

        if status != AilmentType.NONE:
            status_text = str(status).split('.')[-1]
            status_colors = {
                "POISON": (150, 50, 150),
                "BURN": (200, 50, 50),
                "PARALYSIS": (200, 200, 50),
                "SLEEP": (100, 100, 200),
                "FREEZE": (100, 200, 200),
                "LEECH_SEED": (50, 150, 50)
            }
            color = status_colors.get(status_text, (100, 100, 100))
            pygame.draw.rect(self.screen, color, (x + 15, y + 45, 30, 15), border_radius=4)
            self.draw_text(status_text[:3], 'small', (255, 255, 255), x + 17, y + 46, shadow=False)

        bar_x, bar_y = x + 50, y + 45
        bar_w, bar_h = 200, 15
        pygame.draw.rect(self.screen, (100, 100, 100), (bar_x, bar_y, bar_w, bar_h), border_radius=5)

        # --- FIX: MATEMÁTICA DEFENSIVA ---
        # Aseguramos que el ratio nunca sea menor a 0.0 ni mayor a 1.0
        if max_hp <= 0: max_hp = 1 
        ratio = max(0.0, min(1.0, hp / max_hp))
        fill_w = int(bar_w * ratio)
        
        if ratio > 0.5: color = (50, 200, 50)     
        elif ratio > 0.2: color = (200, 200, 50)  
        else: color = (200, 50, 50)               
        
        if fill_w > 0:
            pygame.draw.rect(self.screen, color, (bar_x, bar_y, fill_w, bar_h), border_radius=5)

        self.draw_text(f"{hp}/{max_hp}", 'subtitle', (30, 30, 30), bar_x + 130, bar_y + 18, shadow=False)

    # =========================================================================
    # EL NUEVO MOTOR DE PARTÍCULAS (Acepta imágenes descargadas)
    # =========================================================================
    def load_effect_sprite(self, move_type):
        """Busca una imagen PNG del usuario para las partículas del ataque"""
        move_type = move_type.name if hasattr(move_type, 'name') else str(move_type).split('.')[-1]
        cache_key = f"effect_{move_type}"
        if cache_key not in self.image_cache:
            paths_to_check = [
                os.path.join('assets', 'effects', f"{move_type.lower()}.png"),
                os.path.join('assets', 'effects', f"{move_type.upper()}.png"),
                os.path.join('assets', f"{move_type.lower()}.png"),
                os.path.join('assets', f"{move_type.upper()}.png")
            ]
            
            self.image_cache[cache_key] = None
            for path in paths_to_check:
                if os.path.exists(path):
                    img = pygame.image.load(path).convert_alpha()
                    self.image_cache[cache_key] = pygame.transform.scale(img, (30, 30))
                    break
        return self.image_cache[cache_key]

    def draw_attack_effect(self, move_type, tx, ty, progress):
        """Genera una explosión de físicas sobre el enemigo"""
        move_type = move_type.name if hasattr(move_type, 'name') else str(move_type).split('.')[-1]
        surf = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        
        # 1. Intentamos cargar tu propia imagen si la tienes
        particle_img = self.load_effect_sprite(move_type)
        
        # Usamos el objetivo como "semilla" para que las partículas no parpadeen caóticamente
        random.seed(tx + ty) 
        
        num_particles = 30 # Cuántas chispas/llamas/gotas salen disparadas
        
        for i in range(num_particles):
            # Matemáticas de física: Dirección y Velocidad
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(50, 250)
            
            # Trayectoria
            dist = progress * speed
            x = tx + math.cos(angle) * dist
            y = ty + math.sin(angle) * dist
            
            # Gravedad simulada (las partículas caen al final de la animación)
            y += (progress ** 2) * 150 
            
            # Fade out (Desvanecimiento)
            alpha = max(0, min(255, 255 - int(progress * 255)))
            
            # 2. DIBUJAR
            if particle_img:
                # SI TIENES EL ASSET DESCARGADO: Lo usamos como partícula real
                temp = particle_img.copy()
                temp.set_alpha(alpha)
                surf.blit(temp, (int(x) - 15, int(y) - 15))
            else:
                # SI NO TIENES EL ASSET: Hacemos una explosión procedimental MUCHO mejor
                if move_type == "FIRE":
                    pygame.draw.circle(surf, (255, random.randint(50, 150), 0, alpha), (int(x), int(y)), random.randint(10, 25))
                elif move_type == "WATER":
                    pygame.draw.circle(surf, (0, 150, 255, alpha), (int(x), int(y)), random.randint(5, 15))
                elif move_type == "GRASS":
                    pygame.draw.ellipse(surf, (50, 200, 50, alpha), (int(x), int(y), 20, 10))
                elif move_type == "ELECTRIC":
                    # El eléctrico son rayos rectos en lugar de partículas
                    if random.random() > 0.5:
                        pygame.draw.line(surf, (255, 255, 0, alpha), (tx, ty), (int(x), int(y)), 5)
                elif move_type in ["DARK", "GHOST"]:
                    pygame.draw.circle(surf, (100, 0, 150, alpha), (int(x), int(y)), random.randint(8, 20))
                elif move_type == "ICE":
                    pygame.draw.rect(surf, (150, 255, 255, alpha), (int(x) - 5, int(y) - 5, 10, 10))
                elif move_type == "POISON":
                    pygame.draw.circle(surf, (150, 0, 255, alpha), (int(x), int(y)), random.randint(5, 15))
                elif move_type == "PSYCHIC":
                    pygame.draw.circle(surf, (255, 100, 255, alpha), (int(x), int(y)), random.randint(5, 15))
                elif move_type == "FIGHTING":
                    pygame.draw.polygon(surf, (200, 50, 50, alpha), [(int(x), int(y) - 10), (int(x) - 10, int(y) + 10), (int(x) + 10, int(y) + 10)])
                elif move_type == "DRAGON":
                    pygame.draw.circle(surf, (50, 50, 255, alpha), (int(x), int(y)), random.randint(10, 20))
                elif move_type == "FAIRY":
                    pygame.draw.circle(surf, (255, 150, 255, alpha), (int(x), int(y)), random.randint(3, 8))
                    pygame.draw.circle(surf, (255, 255, 255, alpha), (int(x), int(y)), random.randint(1, 4))
                elif move_type in ["GROUND", "ROCK"]:
                    pygame.draw.rect(surf, (150, 100, 50, alpha), (int(x) - 8, int(y) - 8, 16, 16))
                elif move_type == "BUG":
                    pygame.draw.circle(surf, (150, 255, 50, alpha), (int(x), int(y)), random.randint(3, 8))
                elif move_type == "FLYING":
                    pygame.draw.ellipse(surf, (200, 200, 255, alpha), (int(x), int(y), 15, 5))
                elif move_type == "STEEL":
                    pygame.draw.polygon(surf, (200, 200, 200, alpha), [(int(x), int(y) - 8), (int(x) - 8, int(y)), (int(x), int(y) + 8), (int(x) + 8, int(y))])
                else:
                    # El nuevo impacto NORMAL (Ya no es una cruz gigante, son chispas de impacto)
                    pygame.draw.circle(surf, (255, 255, 200, alpha), (int(x), int(y)), random.randint(3, 8))

        # Dibujamos todo sobre la pantalla
        self.screen.blit(surf, (0, 0))
        
        # Restaurar la semilla aleatoria para no romper la IA del juego
        random.seed()