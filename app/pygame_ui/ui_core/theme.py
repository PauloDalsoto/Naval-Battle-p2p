from dataclasses import dataclass
from typing import Tuple
import pygame

# Paleta base 
COLOR_BG = (18, 24, 38)          # fundo geral
COLOR_PANEL_BG = (28, 34, 48)    # painéis/sidebars
COLOR_PANEL_BORDER = (60, 70, 95)
COLOR_TITLE = (238, 238, 245)
COLOR_SUBTITLE = (180, 190, 210)
COLOR_GRID = (90, 105, 135)
COLOR_GRID_ACCENT = (120, 135, 165)
COLOR_WATER = (28, 80, 130)
COLOR_WATER_ALT = (24, 66, 110)
COLOR_HOVER = (70, 150, 230)
COLOR_VALID = (70, 200, 120)
COLOR_INVALID = (220, 90, 90)
COLOR_TEXT = (230, 235, 245)
COLOR_TEXT_MUTED = (180, 185, 195)
COLOR_BUTTON = (64, 92, 140)
COLOR_BUTTON_HOVER = (84, 112, 160)
COLOR_BUTTON_TEXT = (245, 247, 250)
COLOR_BADGE = (34, 139, 34)  #
COLOR_BADGE_TEXT = (255, 255, 255)

# Cores para navios (Porta-aviões, Bombardeiro, Submarino, Lancha militar)
SHIP_COLORS = [
    (252, 163, 17),   # laranja quente
    (59, 130, 246),   # azul
    (16, 185, 129),   # verde
    (236, 72, 153),   # rosa
]

HIT_COLOR = (220, 40, 40)
MISS_COLOR = (120, 180, 230)


@dataclass
class ButtonStyle:
    bg: Tuple[int, int, int] = COLOR_BUTTON
    bg_hover: Tuple[int, int, int] = COLOR_BUTTON_HOVER
    text: Tuple[int, int, int] = COLOR_BUTTON_TEXT
    radius: int = 8
    padding_x: int = 14
    padding_y: int = 8
    border: Tuple[int, int, int] = COLOR_PANEL_BORDER


def load_font(name: str = "consolas", size: int = 18, bold: bool = False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return None


def draw_rounded_rect(surface, color, rect, radius: int = 8, border: Tuple[int, int, int] | None = None):
    shape_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shape_surf, color, (0, 0, *rect.size), border_radius=radius)
    surface.blit(shape_surf, rect.topleft)
    if border:
        pygame.draw.rect(surface, border, rect, width=1, border_radius=radius)


def vertical_gradient(surface, rect, top_color, bottom_color):
    x, y, w, h = rect
    for i in range(h):
        ratio = i / max(h - 1, 1)
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (x, y + i), (x + w, y + i))


def draw_badge(surface, text: str, pos: Tuple[int, int], font=None):
    if font is None:
        font = load_font(size=14, bold=True)
    text_surf = font.render(text, True, COLOR_BADGE_TEXT)
    pad_x, pad_y = 8, 4
    rect = text_surf.get_rect()
    badge_rect = pygame.Rect(pos[0], pos[1], rect.width + pad_x * 2, rect.height + pad_y * 2)
    draw_rounded_rect(surface, COLOR_BADGE, badge_rect, radius=10)
    surface.blit(text_surf, (badge_rect.x + pad_x, badge_rect.y + pad_y))
