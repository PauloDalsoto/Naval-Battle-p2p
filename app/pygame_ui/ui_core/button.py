import pygame
from app.pygame_ui.ui_core import theme
from typing import Tuple

class Button:
    def __init__(self, rect: pygame.Rect, label: str, callback, style: theme.ButtonStyle | None = None):
        self.rect = rect
        self.label = label
        self.callback = callback
        self.style = style or theme.ButtonStyle()

    def draw(self, surface, font, mouse_pos: Tuple[int, int]):
        hover = self.rect.collidepoint(mouse_pos)
        theme.draw_rounded_rect(
            surface,
            self.style.bg_hover if hover else self.style.bg,
            self.rect,
            radius=self.style.radius,
            border=self.style.border,
        )
        text_surf = font.render(self.label, True, self.style.text)
        tx = self.rect.centerx - text_surf.get_width() // 2
        ty = self.rect.centery - text_surf.get_height() // 2
        surface.blit(text_surf, (tx, ty))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if callable(self.callback):
                    self.callback()