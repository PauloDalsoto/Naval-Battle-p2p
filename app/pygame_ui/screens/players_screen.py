import pygame
from typing import List, Optional
import app.pygame_ui.ui_core.theme as theme
from app.pygame_ui.ui_core.screen import Screen
from app.naval_battle.player_model import Player


class PlayersScreen(Screen):
    def __init__(self, players: Optional[List[Player]] = None, local_ip: str = ""):
        # Lista de jogadores
        self.players = list(players or [])
        # Detecta IPs locais para rotular "(Eu)"
        self.local_ips = {local_ip}

        # Fonts
        self.title_font = theme.load_font(size=18, bold=True) or pygame.font.SysFont("consolas", 18, bold=True)
        self.item_font = theme.load_font(size=16, bold=False) or pygame.font.SysFont("consolas", 16)
        self.small_font = theme.load_font(size=14, bold=False) or pygame.font.SysFont("consolas", 14)

        # Estado
        self.running = True
        self.pad = 12

    def on_enter(self) -> None:
        try:
            pygame.display.set_caption("Jogadores Conectados")
        except Exception:
            pass

    def on_exit(self) -> None:
        pass

    def handle_event(self, event) -> None:
        # Permite que o App trate o QUIT, mas também encerra o ciclo interno desta tela
        if event.type == pygame.QUIT:
            self.running = False

    def update(self, dt: float) -> None:
        # Update players
        pass

    def render(self, surface) -> None:
        # Adapta layout ao tamanho do surface (funciona tanto na janela principal quanto em janela dedicada)
        width, height = surface.get_width(), surface.get_height()
        surface.fill(theme.COLOR_BG)

        pad = self.pad

        # Barra de título
        title_bar_rect = pygame.Rect(pad, pad, width - 2 * pad, 36)
        theme.vertical_gradient(
            surface,
            (title_bar_rect.x, title_bar_rect.y, title_bar_rect.width, title_bar_rect.height),
            (40, 60, 100),
            (20, 30, 50),
        )
        pygame.draw.rect(surface, theme.COLOR_PANEL_BORDER, title_bar_rect, width=1, border_radius=8)
        title_surf = self.title_font.render("Lista de Jogadores", True, theme.COLOR_TITLE)
        surface.blit(title_surf, (title_bar_rect.x + 10, title_bar_rect.y + 8))

        # Painel base (usa o mesmo tema das demais telas)
        panel_rect = pygame.Rect(pad, title_bar_rect.bottom + 8, width - 2 * pad, height - (title_bar_rect.bottom + 8) - pad)
        theme.draw_rounded_rect(surface, theme.COLOR_PANEL_BG, panel_rect, radius=10, border=theme.COLOR_PANEL_BORDER)

        # Lista
        list_y = panel_rect.y + 12
        item_h = 28
        non_self_counter = 1
        # Exibe até 8 itens
        for idx, p in enumerate(self.players[:8]):
            row_y = list_y + idx * item_h
            # Indicador de status (alinhado verticalmente com o IP) + rótulos
            is_active = getattr(p, "active", False)
            dot_color = (46, 204, 113) if is_active else (200, 40, 40)
            ip_text = getattr(p, "ip", "")
            status_text = "ativo" if is_active else "inativo"

            # Sufixo: "(Eu)" se IP local; caso contrário "Jogador N"
            if ip_text in self.local_ips:
                suffix = " (Eu)"
            else:
                suffix = f" (Jogador {non_self_counter})"
                non_self_counter += 1

            ip_label = f"{ip_text}{suffix}"
            ip_surf = self.item_font.render(ip_label, True, theme.COLOR_TEXT)
            st_color = (200, 40, 40) if not is_active else theme.COLOR_TEXT_MUTED
            st_surf = self.small_font.render(f"({status_text})", True, st_color)

            # Ponto de status como círculo, alinhado ao meio da altura do texto
            dot_x = panel_rect.x + 16
            dot_y = row_y + (ip_surf.get_height() // 2) + 2
            pygame.draw.circle(surface, dot_color, (dot_x, dot_y), 6)

            # Textos: IP + sufixo e status
            text_x = dot_x + 16
            surface.blit(ip_surf, (text_x, row_y))
            surface.blit(st_surf, (text_x + ip_surf.get_width() + 10, row_y + 2))

    # Atualiza a lista de jogadores dinamicamente
    def set_players(self, players: Optional[List[Player]]) -> None:
        self.players = list(players or [])
