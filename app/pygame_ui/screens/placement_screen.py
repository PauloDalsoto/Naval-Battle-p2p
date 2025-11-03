import pygame
from typing import Optional, Tuple, Dict
from app.pygame_ui.ui_core.screen import Screen
from app.pygame_ui.ui_core import theme
from app.naval_battle.board_model import BoardModel
from app.naval_battle.ships import SHIP_TYPES
from app.pygame_ui.constants import (
    GRID_SIZE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    MARGIN,
    TOP_BAR_HEIGHT,
    SIDEBAR_WIDTH,
    ORIENT_H
)
from app.pygame_ui.ui_core.button import Button

class PlacementScreen(Screen):
    def __init__(self, board: Optional[BoardModel] = None, on_start_game: Optional[callable] = None):
        # Fonts
        self.title_font = theme.load_font(size=28, bold=True) or pygame.font.SysFont("consolas", 28, bold=True)
        self.sub_font = theme.load_font(size=18, bold=False) or pygame.font.SysFont("consolas", 18)
        self.small_font = theme.load_font(size=14, bold=False) or pygame.font.SysFont("consolas", 14)
        self.list_font = theme.load_font(size=18, bold=True) or pygame.font.SysFont("consolas", 18, bold=True)
       
        # Layout baseline
        self.top_bar_rect = pygame.Rect(0, 0, WINDOW_WIDTH, TOP_BAR_HEIGHT)

        # Adaptive cell size to minimize empty space
        self.cell = min(
            (WINDOW_WIDTH - SIDEBAR_WIDTH - 2 * MARGIN) // GRID_SIZE,
            (WINDOW_HEIGHT - (TOP_BAR_HEIGHT + 2 * MARGIN)) // GRID_SIZE,
        )
        if self.cell < 36:
            self.cell = 36

        # Grid rect
        self.grid_w = self.cell * GRID_SIZE
        self.grid_h = self.cell * GRID_SIZE
        # Pequeno espaçamento extra no topo e à esquerda para não encostar nos limites
        self.grid_x = MARGIN + 12
        self.grid_y = TOP_BAR_HEIGHT + MARGIN + 12
        self.grid_rect = pygame.Rect(self.grid_x, self.grid_y, self.grid_w, self.grid_h)

        # Sidebar rect
        self.sidebar_x = WINDOW_WIDTH - SIDEBAR_WIDTH - MARGIN
        self.sidebar_y = TOP_BAR_HEIGHT + MARGIN + 12
        self.sidebar_rect = pygame.Rect(self.sidebar_x, self.sidebar_y, SIDEBAR_WIDTH, self.grid_h)

        # Buttons in sidebar
        btn_w = SIDEBAR_WIDTH - 2 * 16
        self.btn_random = Button(
            pygame.Rect(self.sidebar_x + 16, self.sidebar_y + 16, btn_w, 40),
            "Aleatório",
            self.on_random,
        )
        self.btn_clear = Button(
            pygame.Rect(self.sidebar_x + 16, self.sidebar_y + 66, btn_w, 40),
            "Limpar",
            self.on_clear,
        )
        self.btn_orient = Button(
            pygame.Rect(self.sidebar_x + 16, self.sidebar_y + 116, btn_w, 40),
            "Orientação (L): Horizontal",
            self.on_toggle_orient,
        )
        # Start button at bottom; same style/size; appears only when all placed
        self.btn_start = Button(
            pygame.Rect(self.sidebar_x + 16, self.sidebar_rect.bottom - 56, btn_w, 40),
            "Iniciar jogo",
            self.on_start_game,
        )

        # Ship list area
        self.ship_list_rect = pygame.Rect(self.sidebar_x + 16, self.sidebar_y + 176, btn_w, self.grid_h - 200)

        # Clickable rects for ships
        self.ship_row_rects: Dict[str, pygame.Rect] = {}

        # Game variables
        self.board = board if board is not None else BoardModel()
        self.on_start_game_cb = on_start_game
        self.running = True

    # Screen protocol methods
    def on_enter(self) -> None:
        pygame.display.set_caption("Batalha Naval - p2p")

    def on_exit(self) -> None:
        pass

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_l:
                self.on_toggle_orient()
                return
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Ensure start button rect is positioned before handling clicks
            self.btn_start.rect.topleft = (self.sidebar_x + 16, self.sidebar_rect.bottom - 56)
            # Buttons
            self.btn_random.handle_event(event)
            self.btn_clear.handle_event(event)
            self.btn_orient.handle_event(event)
            # Always route click to start button; on_start_game will guard by all_placed()
            self.btn_start.handle_event(event)

            # Ship list clicks (left button)
            if event.button == 1:
                for st in SHIP_TYPES:
                    rr = self.ship_row_rects.get(st.key)
                    if rr and rr.collidepoint(event.pos):
                        self.board.set_selected_ship(st.key)
                        return
                # Grid click placement
                gcoords = self.grid_coords_from_pos(event.pos)
                if gcoords and self.board.selected_ship_key:
                    gx, gy = gcoords
                    self.place_selected_at(gx, gy)
                    return
            # Right-click remove
            if event.button == 3:
                gcoords = self.grid_coords_from_pos(event.pos)
                if gcoords:
                    gx, gy = gcoords
                    self.remove_at(gx, gy)
                    return

    def render(self, surface) -> None:
        surface.fill(theme.COLOR_BG)
        mouse_pos = pygame.mouse.get_pos()

        # Top bar
        self.draw_top_bar(surface)

        # Grid
        self.draw_grid(surface, mouse_pos)

        # Sidebar (buttons + title + list + start button if ready)
        self.draw_sidebar(surface, mouse_pos)

    # Button callbacks
    def on_random(self):
        self.board.randomize()

    def on_clear(self):
        self.board.reset()

    def on_toggle_orient(self):
        self.board.toggle_orientation()
        label = "Orientação (L): Horizontal" if self.board.current_orient == ORIENT_H else "Orientação (L): Vertical"
        self.btn_orient.label = label

    def on_start_game(self):
        # Guard: only proceed when all ships are placed
        if not self.board.all_placed():
            return
        
        if callable(self.on_start_game_cb):
            self.on_start_game_cb()

    def grid_coords_from_pos(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        x, y = pos
        if not self.grid_rect.collidepoint(x, y):
            return None
        gx = (x - self.grid_x) // self.cell
        gy = (y - self.grid_y) // self.cell
        return int(gx), int(gy)

    def draw_top_bar(self, surface):
        theme.vertical_gradient(surface, (self.top_bar_rect.x, self.top_bar_rect.y, self.top_bar_rect.width, self.top_bar_rect.height),
                                (40, 60, 100), (20, 30, 50))
        pygame.draw.line(surface, theme.COLOR_PANEL_BORDER, (0, self.top_bar_rect.bottom), (WINDOW_WIDTH, self.top_bar_rect.bottom), 2)
        title = "Batalha Naval - Escolher posições"
        title_surf = self.title_font.render(title, True, theme.COLOR_TITLE)
        surface.blit(title_surf, (MARGIN, 20))

    def draw_grid(self, surface, mouse_pos):
        # grid background
        theme.draw_rounded_rect(surface, theme.COLOR_PANEL_BG, self.grid_rect, radius=8, border=theme.COLOR_PANEL_BORDER)
        # cells
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                cell_rect = pygame.Rect(self.grid_x + x * self.cell + 1, self.grid_y + y * self.cell + 1, self.cell - 2, self.cell - 2)
                base_color = theme.COLOR_WATER_ALT if (x + y) % 2 else theme.COLOR_WATER
                pygame.draw.rect(surface, base_color, cell_rect, border_radius=6)
                pygame.draw.rect(surface, theme.COLOR_GRID, cell_rect, 1, border_radius=6)

        # draw placed ships
        for st in SHIP_TYPES:
            pl = self.board.placements.get(st.key)
            if not pl:
                continue
            for (x, y) in pl.cells:
                rect = pygame.Rect(self.grid_x + x * self.cell + 1, self.grid_y + y * self.cell + 1, self.cell - 2, self.cell - 2)
                pygame.draw.rect(surface, st.color, rect, border_radius=6)
                pygame.draw.rect(surface, theme.COLOR_GRID_ACCENT, rect, 2, border_radius=6)

        # preview placement
        if self.board.selected_ship_key:
            grid_coords = self.grid_coords_from_pos(mouse_pos)
            if grid_coords:
                px, py = grid_coords
                valid, cells = self.board.get_preview_cells(px, py, self.board.selected_ship_key)
                for (x, y) in cells:
                    rect = pygame.Rect(self.grid_x + x * self.cell + 2, self.grid_y + y * self.cell + 2, self.cell - 4, self.cell - 4)
                    color = theme.COLOR_VALID if valid else theme.COLOR_INVALID
                    pygame.draw.rect(surface, color, rect, 3, border_radius=8)

        # axis labels
        axis_font = self.small_font
        for i in range(GRID_SIZE):
            xs = axis_font.render(str(i), True, theme.COLOR_TEXT_MUTED)
            ys = axis_font.render(str(i), True, theme.COLOR_TEXT_MUTED)
            surface.blit(xs, (self.grid_x + i * self.cell + self.cell // 2 - xs.get_width() // 2, self.grid_y - 18))
            surface.blit(ys, (self.grid_x - 18, self.grid_y + i * self.cell + self.cell // 2 - ys.get_height() // 2))

    def draw_sidebar(self, surface, mouse_pos):
        theme.draw_rounded_rect(surface, theme.COLOR_PANEL_BG, self.sidebar_rect, radius=12, border=theme.COLOR_PANEL_BORDER)

        # buttons
        self.btn_random.draw(surface, self.list_font, mouse_pos)
        self.btn_clear.draw(surface, self.list_font, mouse_pos)
        self.btn_orient.draw(surface, self.list_font, mouse_pos)

        # title "Embarcações"
        title_surf = self.list_font.render("Embarcações", True, theme.COLOR_TITLE)
        title_y = self.btn_orient.rect.bottom + 16
        surface.blit(title_surf, (self.sidebar_x + 16, title_y))

        # ship list box, clamped to available height considering start button
        list_rect = self.ship_list_rect.copy()
        list_rect.y = title_y + 28
        reserved_bottom = 0
        if self.board.all_placed():
            self.btn_start.rect.topleft = (self.sidebar_x + 16, self.sidebar_rect.bottom - 56)
            self.btn_start.draw(surface, self.list_font, mouse_pos)
            reserved_bottom = self.btn_start.rect.height + 16

        max_list_height = self.sidebar_rect.bottom - 16 - reserved_bottom - list_rect.y
        if max_list_height < 100:
            max_list_height = 100
        list_rect.height = min(list_rect.height, max_list_height)

        pygame.draw.rect(surface, (24, 28, 40), list_rect, border_radius=8)
        pygame.draw.rect(surface, theme.COLOR_PANEL_BORDER, list_rect, 1, border_radius=8)

        # list items
        self.ship_row_rects.clear()
        available_y = list_rect.y + 10
        for st in SHIP_TYPES:
            placed = st.key in self.board.placements
            row_rect = pygame.Rect(list_rect.x + 10, available_y, list_rect.width - 20, 44)
            hover = row_rect.collidepoint(mouse_pos)
            bg = (36, 42, 60) if not hover else (44, 52, 72)
            theme.draw_rounded_rect(surface, bg, row_rect, radius=10)
            # selection highlight
            if self.board.selected_ship_key == st.key:
                pygame.draw.rect(surface, theme.COLOR_HOVER, row_rect, 2, border_radius=10)
            # color chip
            chip = pygame.Rect(row_rect.x + 8, row_rect.y + 8, 28, 28)
            theme.draw_rounded_rect(surface, st.color, chip, radius=6)

            name_surf = self.list_font.render(st.name, True, theme.COLOR_TEXT)
            size_surf = self.small_font.render(f"{st.size} posições", True, theme.COLOR_TEXT_MUTED)
            surface.blit(name_surf, (chip.right + 10, row_rect.y + 6))
            surface.blit(size_surf, (chip.right + 12, row_rect.y + 24))

            if placed:
                theme.draw_badge(surface, "OK", (row_rect.right - 48, row_rect.y + 12), font=self.small_font)

            self.ship_row_rects[st.key] = row_rect
            available_y += 52

    # placement helpers
    def place_selected_at(self, gx: int, gy: int):
        key = self.board.selected_ship_key
        if not key:
            return
        ok = self.board.place_ship(key, gx, gy, self.board.current_orient)
        if not ok:
            print("Posicionamento inválido para", key)

    def remove_at(self, gx: int, gy: int):
        removed = self.board.remove_ship_at(gx, gy)
        if removed:
            print("Removido navio:", removed)
