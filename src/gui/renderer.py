# src/gui/renderer.py
import pygame
import os


class Renderer:
    def __init__(self, screen):
        self.screen = screen

        ruta_fuente = os.path.join('assets', 'pokemon_pixel.ttf')

        if os.path.exists(ruta_fuente):
            self.font_title = pygame.font.Font(ruta_fuente, 30)
            self.font_subtitle = pygame.font.Font(ruta_fuente, 16)
            self.font_small = pygame.font.Font(ruta_fuente, 6) # Aumentado para mejor legibilidad
        else:
            self.font_title = pygame.font.SysFont("Arial", 45, bold=True)
            self.font_subtitle = pygame.font.SysFont("Arial", 26)
            self.font_small = pygame.font.SysFont("Arial", 14)

        self.image_cache = {}

    def clear_screen(self, color=(30, 30, 40)):
        self.screen.fill(color)

    def load_background(self, filepath, width, height):
        if os.path.exists(filepath):
            img = pygame.image.load(filepath).convert()
            return pygame.transform.scale(img, (width, height))
        return None

    def draw_background(self, img, apply_dark_overlay=False):
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
        if intensity > 0:
            flash_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
            flash_surface.set_alpha(intensity)
            flash_surface.fill(color)
            self.screen.blit(flash_surface, (0, 0))

    def _get_font(self, font_type):
        if font_type == 'title':
            return self.font_title
        elif font_type == 'subtitle':
            return self.font_subtitle
        return self.font_small

    def draw_text(self, text, font_type, color, x, y, center=False, shadow=True):
        font = self._get_font(font_type)
        surface = font.render(str(text), True, color)

        if center:
            x = x - surface.get_width() // 2
            y = y - surface.get_height() // 2

        if shadow:
            shadow_surface = font.render(str(text), True, (20, 20, 20))
            self.screen.blit(shadow_surface, (x + 2, y + 2))

        self.screen.blit(surface, (x, y))

    def draw_button(self, rect, text, is_hovered, disabled=False, sub_text=None):
        button_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

        if disabled:
            bg_color = (90, 90, 90, 190)
            border_color = (150, 150, 150, 220)
            text_color = (210, 210, 210)
        elif is_hovered:
            bg_color = (255, 180, 20, 230)
            border_color = (255, 255, 100, 255)
            text_color = (255, 255, 255)
        else:
            bg_color = (200, 120, 10, 210)
            border_color = (255, 200, 50, 255)
            text_color = (255, 255, 255)

        pygame.draw.rect(button_surface, bg_color, button_surface.get_rect(), border_radius=10)
        pygame.draw.rect(button_surface, border_color, button_surface.get_rect(), width=3, border_radius=10)

        self.screen.blit(button_surface, (rect.x, rect.y))
        
        if sub_text:
            # Si hay subtexto, el texto principal va arriba y el subtexto abajo
            self.draw_text(text, 'subtitle', text_color, rect.centerx, rect.centery - 10, center=True)
            self.draw_text(sub_text, 'small', text_color, rect.centerx, rect.centery + 10, center=True)
        else:
            self.draw_text(text, 'subtitle', text_color, rect.centerx, rect.centery, center=True)


    def load_sprite(self, name, filepath):
        if name not in self.image_cache:
            if os.path.exists(filepath):
                img = pygame.image.load(filepath).convert_alpha()
                self.image_cache[name] = pygame.transform.scale(img, (75, 75))
            else:
                self.image_cache[name] = None
        return self.image_cache.get(name)

    def draw_pokemon_grid(self, pokemon_list, start_x, start_y, selected_names, columns=6, spacing_x=75, spacing_y=75):
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

            self.draw_text(name.capitalize(), 'small', (200, 200, 200), x + 30, y + 65, center=True)

    def load_battle_sprite(self, name, filepath, is_back=False):
        cache_key = f"battle_{'back' if is_back else 'front'}_{name}"
        if cache_key not in self.image_cache:
            if os.path.exists(filepath):
                img = pygame.image.load(filepath).convert_alpha()
                self.image_cache[cache_key] = pygame.transform.scale(img, (200, 200))
            else:
                self.image_cache[cache_key] = None
        return self.image_cache.get(cache_key)

    def draw_health_bar(self, x, y, name, hp, max_hp, level, is_player=False):
        box_rect = pygame.Rect(x, y, 280, 80)
        pygame.draw.rect(self.screen, (240, 240, 230), box_rect, border_radius=10)
        pygame.draw.rect(self.screen, (50, 50, 50), box_rect, width=3, border_radius=10)

        self.draw_text(name.upper(), 'subtitle', (30, 30, 30), x + 15, y + 10)
        self.draw_text(f"Lv{level}", 'subtitle', (50, 50, 50), x + 210, y + 10)

        bar_x, bar_y = x + 50, y + 45
        bar_w, bar_h = 200, 15
        pygame.draw.rect(self.screen, (100, 100, 100), (bar_x, bar_y, bar_w, bar_h), border_radius=5)

        safe_max_hp = max(1, max_hp)
        ratio = max(0.0, min(1.0, hp / safe_max_hp))
        fill_w = int(bar_w * ratio)

        if ratio > 0.5:
            color = (50, 200, 50)
        elif ratio > 0.2:
            color = (200, 200, 50)
        else:
            color = (200, 50, 50)

        if fill_w > 0:
            pygame.draw.rect(self.screen, color, (bar_x, bar_y, fill_w, bar_h), border_radius=5)

        # SIEMPRE mostrar el texto de los puntos de vida
        self.draw_text(f"{hp}/{max_hp}", 'small', (30, 30, 30), bar_x + 130, bar_y + 18)

    def _wrap_text(self, text, font, max_width):
        if not text:
            return []

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

    def draw_dialog_box(self, text):
        box_rect = pygame.Rect(20, self.screen.get_height() - 120, self.screen.get_width() - 40, 100)
        pygame.draw.rect(self.screen, (40, 40, 50), box_rect, border_radius=10)
        pygame.draw.rect(self.screen, (200, 200, 200), box_rect, width=4, border_radius=10)

        if text is None:
            return

        font = self.font_subtitle
        max_text_width = box_rect.width - 60
        wrapped_lines = self._wrap_text(str(text), font, max_text_width)

        max_lines = 3
        line_height = font.get_height() + 4
        start_y = box_rect.y + 12

        for i, line in enumerate(wrapped_lines[:max_lines]):
            y = start_y + i * line_height
            self.draw_text(line, 'subtitle', (255, 255, 255), box_rect.x + 30, y)