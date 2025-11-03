import pygame
import random
import sys
from typing import Optional, Tuple, Dict
from app.pygame_ui.ui_core.screen import Screen
import app.pygame_ui.ui_core.theme as theme
from app.naval_battle.board_model import BoardModel
from app.pygame_ui.ui_core.button import Button
from app.naval_battle.ships import SHIP_TYPES
from app.pygame_ui.constants import (
    GRID_SIZE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    MARGIN,
    TOP_BAR_HEIGHT,
)
from app.network.p2p_udp import UdpPeer
class GameScreen(Screen):
    def __init__(self, my_board: BoardModel,
                on_exit_game: Optional[callable] = None,
                players_count_provider: Optional[callable] = None,
                udp_peer: UdpPeer = None) -> None:
        # Fonts
        self.title_font = theme.load_font(size=28, bold=True) or pygame.font.SysFont("consolas", 28, bold=True)
        self.sub_font = theme.load_font(size=18, bold=False) or pygame.font.SysFont("consolas", 18)
        self.small_font = theme.load_font(size=14, bold=False) or pygame.font.SysFont("consolas", 14)
        self.list_font = theme.load_font(size=18, bold=True) or pygame.font.SysFont("consolas", 18, bold=True)
        # Provider para contagem de jogadores conectados
        self.players_count_provider = players_count_provider

        # Boards
        self.my_board = my_board
        self.enemy_board = BoardModel()  # sem embarcações (UI apenas)

        # Mapa de cores por navio (key -> color) para meu tabuleiro
        self.ship_color_by_key: Dict[str, Tuple[int, int, int]] = {}
        for idx, st in enumerate(SHIP_TYPES):
            self.ship_color_by_key[st.key] = st.color

        # Layout baseline
        self.top_bar_rect = pygame.Rect(0, 0, WINDOW_WIDTH, TOP_BAR_HEIGHT)

        # Cálculo de célula considerando dois grids lado a lado + painel inferior
        horizontal_available = WINDOW_WIDTH - (2 * MARGIN)
        # gap entre os grids para não sobrepor coordenadas
        inter_grid_gap = max(MARGIN * 2, 40)
        # dois grids lado a lado, descontando o gap
        cell_by_width = (horizontal_available - inter_grid_gap) // (2 * GRID_SIZE)
        vertical_available = WINDOW_HEIGHT - (TOP_BAR_HEIGHT + 3 * MARGIN + 120)  # reserva ~120px para painel inferior
        cell_by_height = vertical_available // GRID_SIZE
        self.cell = max(36, min(cell_by_width, cell_by_height))

        # Grids
        self.grid_w = self.cell * GRID_SIZE
        self.grid_h = self.cell * GRID_SIZE

        # Esquerda (meu tabuleiro)
        self.left_grid_x = MARGIN + 10
        self.left_grid_y = TOP_BAR_HEIGHT + MARGIN + 24
        self.left_grid_rect = pygame.Rect(self.left_grid_x, self.left_grid_y, self.grid_w, self.grid_h)

        # Direita (tabuleiro inimigo)
        self.right_grid_x = self.left_grid_x + self.grid_w + inter_grid_gap
        self.right_grid_y = self.left_grid_y
        self.right_grid_rect = pygame.Rect(self.right_grid_x, self.right_grid_y, self.grid_w, self.grid_h)

        # Painel inferior (abaixo dos tabuleiros)
        bottom_y = self.left_grid_y + self.grid_h + MARGIN
        bottom_h = max(120, WINDOW_HEIGHT - bottom_y - MARGIN)
        self.bottom_rect = pygame.Rect(MARGIN, bottom_y, WINDOW_WIDTH - 2 * MARGIN, bottom_h)

        # Botões e controles
        self.btn_exit = Button(
            pygame.Rect(self.bottom_rect.x + 16, self.bottom_rect.y + 16, 160, 40),
            "Sair do jogo",
            self.on_exit_click,
        )

        # Timer de 10s
        self.countdown_total = 10.0
        self.countdown_remaining = self.countdown_total

        # Estado de seleção de tiro
        self.selected_shot: Optional[Tuple[int, int]] = None

        # Toggle de tiros aleatórios (auto) + botão de alternância (renderizado na barra inferior)
        self.random_shots_enabled: bool = False
        self.btn_random_toggle = Button(pygame.Rect(0, 0, 160, 34), "Tiros aleatórios: OFF", self.on_toggle_random)

        # Registro de tiros: misses (preto) e hits (vermelho)
        self.shot_misses: set[Tuple[int, int]] = set()
        self.shot_hits: set[Tuple[int, int]] = set()
        # Incoming shots on my board (left grid)
        self.incoming_shot_misses: set[Tuple[int, int]] = set()
        self.incoming_shot_hits: set[Tuple[int, int]] = set()
        self.last_incoming_event: Optional[str] = None
        # Track incoming hits per ship and sunk status
        self.incoming_hits_by_ship: Dict[str, set[Tuple[int, int]]] = {}
        self.sunk_ships_on_my_board: set[str] = set()

        # Score (placeholders)
        self.shots_made = 0
        self.hits_received_count = 0
        self.distinct_players_hit_count = 0

        # Callback de saída (placeholder)
        self.on_exit_game = on_exit_game

        self.running = True

        # Estatísticas por jogador e modal de saída
        self.hits_by_player: Dict[str, int] = {}
        self.destroyed_ships_by_player: Dict[str, int] = {}
        self.exit_modal_open: bool = False
        self.exit_modal_rect = pygame.Rect(WINDOW_WIDTH // 2 - 320, WINDOW_HEIGHT // 2 - 200, 640, 380)
        self.btn_exit_confirm = Button(pygame.Rect(0, 0, 160, 44), "SAIR", self.on_confirm_exit)
        self.btn_exit_cancel = Button(pygame.Rect(0, 0, 160, 44), "Cancelar", self.on_cancel_exit)

        # Newtwork
        self.udp_peer = udp_peer
        # Game state
        self.game_over: bool = False

    def on_enter(self) -> None:
        pygame.display.set_caption("Batalha Naval - Jogo")

    def on_exit(self) -> None:
        pass

    def on_exit_click(self) -> None:
        # Abre o modal de confirmação/score em vez de sair imediatamente
        self.exit_modal_open = True
           
    def handle_event(self, event) -> None:
        # Se o modal de saída está aberto, delega eventos apenas aos botões do modal
        if self.exit_modal_open:
            # Garante que os botões estejam posicionados corretamente antes de processar cliques
            self.layout_exit_modal_buttons()
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.btn_exit_confirm.handle_event(event)
                self.btn_exit_cancel.handle_event(event)
            return
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Botões
            self.btn_exit.handle_event(event)
            self.btn_random_toggle.handle_event(event)
            # Seleção no tabuleiro inimigo 
            if event.button == 1:
                gcoords = self.grid_coords_from_pos(event.pos, right=True)
                if gcoords:
                    self.selected_shot = gcoords

    def update(self, dt: float) -> None:
        # Pausa o jogo se o modal de saída estiver aberto
        if self.exit_modal_open:
            return
        # Se o jogo terminou, não processa mais tiros/temporizador
        if getattr(self, "game_over", False):
            return
        # Atualiza timer e dispara tiro a cada 10s
        # Pausa o contador se houver menos de 2 jogadores conectados
        if self.players_count_provider:
            if self.players_count_provider() < 2:
                return
          
        self.countdown_remaining -= dt
        if self.countdown_remaining <= 0.0:
            # Se não há seleção e modo aleatório está ON, escolha uma posição para atirar
            if self.selected_shot is None and self.random_shots_enabled:
                self.selected_shot = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))

            # Dispara o tiro se houver uma posição selecionada (manual ou aleatória)
            if self.selected_shot is not None:
                self.execute_shot()

            # Reinicia ciclo do timer
            self.countdown_remaining = self.countdown_total

            # Pré-seleciona próxima posição apenas se aleatório estiver ON
            if self.random_shots_enabled:
                self.selected_shot = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))

    def render(self, surface) -> None:
        surface.fill(theme.COLOR_BG)
        mouse_pos = pygame.mouse.get_pos()
        self.draw_top_bar(surface)
        self.draw_grid_left(surface)
        self.draw_grid_right(surface)
        self.draw_bottom_panel(surface, mouse_pos)

        # Modal de saída (overlay)
        if self.exit_modal_open:
            self.draw_exit_modal(surface, mouse_pos)

    # Helpers de grid/coords
    def grid_coords_from_pos(self, pos: Tuple[int, int], right: bool) -> Optional[Tuple[int, int]]:
        x, y = pos
        rect = self.right_grid_rect if right else self.left_grid_rect
        gx0 = self.right_grid_x if right else self.left_grid_x
        gy0 = self.right_grid_y if right else self.left_grid_y
        if not rect.collidepoint(x, y):
            return None
        gx = (x - gx0) // self.cell
        gy = (y - gy0) // self.cell
        return int(gx), int(gy)

    def draw_top_bar(self, surface):
        theme.vertical_gradient(surface, (self.top_bar_rect.x, self.top_bar_rect.y, self.top_bar_rect.width, self.top_bar_rect.height),
                                (40, 60, 100), (20, 30, 50))
        pygame.draw.line(surface, theme.COLOR_PANEL_BORDER, (0, self.top_bar_rect.bottom), (WINDOW_WIDTH, self.top_bar_rect.bottom), 2)
        # Define o status do jogo ao lado do título
        if getattr(self, "game_over", False):
            status = "Fim de Jogo!"
        else:
            status = "Em Execução!"
            if self.players_count_provider:
                try:
                    status = "Em Execução!" if self.players_count_provider() >= 2 else "Aguardando Jogadores..."
                except Exception:
                    # Em caso de erro no provider, mantém o padrão "Em Execução!"
                    pass
        title = f"Batalha Naval - {status}"
        title_surf = self.title_font.render(title, True, theme.COLOR_TITLE)
        surface.blit(title_surf, (MARGIN, 20))

        # Botão sair no final da linha do título (topo, à direita)
        pad = 12
        btn_w, btn_h = 160, 40
        self.btn_exit.rect.width = btn_w
        self.btn_exit.rect.height = btn_h
        self.btn_exit.rect.x = self.top_bar_rect.right - pad - btn_w
        self.btn_exit.rect.y = self.top_bar_rect.y + (TOP_BAR_HEIGHT - btn_h) // 2
        self.btn_exit.draw(surface, self.list_font, pygame.mouse.get_pos())

    def draw_grid_base(self, surface, rect, grid_x, grid_y, reveal_ships: bool, board: BoardModel):
        # painel base
        theme.draw_rounded_rect(surface, theme.COLOR_PANEL_BG, rect, radius=8, border=theme.COLOR_PANEL_BORDER)
        # células
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                cell_rect = pygame.Rect(grid_x + x * self.cell + 1, grid_y + y * self.cell + 1, self.cell - 2, self.cell - 2)
                base_color = theme.COLOR_WATER_ALT if (x + y) % 2 else theme.COLOR_WATER
                pygame.draw.rect(surface, base_color, cell_rect, border_radius=6)
                pygame.draw.rect(surface, theme.COLOR_GRID, cell_rect, 1, border_radius=6)
        # navios (apenas se reveal_ships)
        if reveal_ships:
            for pl in board.placements.values():
                for (x, y) in pl.cells:
                    color = self.ship_color_by_key.get(pl.key, theme.SHIP_COLORS[0])
                    rect_cell = pygame.Rect(grid_x + x * self.cell + 1, grid_y + y * self.cell + 1, self.cell - 2, self.cell - 2)
                    pygame.draw.rect(surface, color, rect_cell, border_radius=6)
                    pygame.draw.rect(surface, theme.COLOR_GRID_ACCENT, rect_cell, 2, border_radius=6)
        # eixos
        axis_font = self.small_font
        for i in range(GRID_SIZE):
            xs = axis_font.render(str(i), True, theme.COLOR_TEXT_MUTED)
            ys = axis_font.render(str(i), True, theme.COLOR_TEXT_MUTED)
            surface.blit(xs, (grid_x + i * self.cell + self.cell // 2 - xs.get_width() // 2, grid_y - 18))
            surface.blit(ys, (grid_x - 18, grid_y + i * self.cell + self.cell // 2 - ys.get_height() // 2))

    def draw_grid_left(self, surface):
        # título acima do grid esquerdo
        title = "Meu Tabuleiro"
        t_surf = self.list_font.render(title, True, theme.COLOR_TITLE)
        # Posiciona o título acima do eixo X, sem sobrepor os números
        t_h = t_surf.get_height()
        axis_y = self.left_grid_y - 18  # y das coordenadas do eixo X
        y_title = axis_y - 6 - t_h      # 6px de folga acima do eixo
        y_title = max(self.top_bar_rect.bottom + 6, y_title)
        surface.blit(t_surf, (self.left_grid_x, y_title))
        self.draw_grid_base(surface, self.left_grid_rect, self.left_grid_x, self.left_grid_y, True, self.my_board)
        # Overlay incoming shots: misses (gray) and hits (red X)
        for (sx, sy) in getattr(self, "incoming_shot_misses", set()):
            r = pygame.Rect(self.left_grid_x + sx * self.cell + 1, self.left_grid_y + sy * self.cell + 1, self.cell - 2, self.cell - 2)
            pygame.draw.rect(surface, (110, 114, 120), r, border_radius=6)  # gray
        for (hx, hy) in getattr(self, "incoming_shot_hits", set()):
            x0 = self.left_grid_x + hx * self.cell + 4
            y0 = self.left_grid_y + hy * self.cell + 4
            x1 = x0 + self.cell - 8
            y1 = y0 + self.cell - 8
            pygame.draw.line(surface, (200, 40, 40), (x0, y0), (x1, y1), 3)
            pygame.draw.line(surface, (200, 40, 40), (x0, y1), (x1, y0), 3)

    def draw_grid_right(self, surface):
        # título acima do grid direito
        title = "Tabuleiro Inimigo"
        t_surf = self.list_font.render(title, True, theme.COLOR_TITLE)
        # Posiciona o título acima do eixo X, sem sobrepor os números
        t_h = t_surf.get_height()
        axis_y = self.right_grid_y - 18  # y das coordenadas do eixo X
        y_title = axis_y - 6 - t_h       # 6px de folga acima do eixo
        y_title = max(self.top_bar_rect.bottom + 6, y_title)
        surface.blit(t_surf, (self.right_grid_x, y_title))
        self.draw_grid_base(surface, self.right_grid_rect, self.right_grid_x, self.right_grid_y, False, self.enemy_board)
        # sobreposições de tiros: misses (preto) e hits (vermelho)
        for (sx, sy) in self.shot_misses:
            r = pygame.Rect(self.right_grid_x + sx * self.cell + 1, self.right_grid_y + sy * self.cell + 1, self.cell - 2, self.cell - 2)
            pygame.draw.rect(surface, (110, 114, 120), r, border_radius=6)  # cinza
        for (hx, hy) in self.shot_hits:
            r = pygame.Rect(self.right_grid_x + hx * self.cell + 1, self.right_grid_y + hy * self.cell + 1, self.cell - 2, self.cell - 2)
            pygame.draw.rect(surface, (200, 40, 40), r, border_radius=6)     # vermelho
        # destaque de seleção atual
        if self.selected_shot:
            sx, sy = self.selected_shot
            rect_sel = pygame.Rect(self.right_grid_x + sx * self.cell + 2, self.right_grid_y + sy * self.cell + 2, self.cell - 4, self.cell - 4)
            pygame.draw.rect(surface, theme.COLOR_HOVER, rect_sel, 3, border_radius=8)

    def draw_bottom_panel(self, surface, mouse_pos):
        # base
        theme.draw_rounded_rect(surface, theme.COLOR_PANEL_BG, self.bottom_rect, radius=12, border=theme.COLOR_PANEL_BORDER)
        pad = 16

        # Áreas de conteúdo (esquerda/direita) e centro
        content_left = self.bottom_rect.x + pad
        content_right = self.bottom_rect.right - pad

        base_y = self.bottom_rect.y + pad

        # Legenda (meus navios) na esquerda, em duas colunas
        legend_title = self.sub_font.render("Legenda (meus navios)", True, theme.COLOR_TITLE)
        surface.blit(legend_title, (content_left, base_y))
        y = base_y + 28
        # duas colunas dentro da área da esquerda
        col_gap = 24
        legend_area_w = (self.bottom_rect.width - 2 * pad) // 3
        inner_col_w = (legend_area_w - col_gap) // 2
        col1_x = content_left
        col2_x = content_left + inner_col_w + col_gap
        # dividir lista em duas metades
        half = (len(SHIP_TYPES) + 1) // 2
        for i, st in enumerate(SHIP_TYPES[:half]):
            box = pygame.Rect(col1_x, y + i * 28, 22, 22)
            pygame.draw.rect(surface, st.color, box, border_radius=4)
            name = self.small_font.render(st.name, True, theme.COLOR_TEXT)
            surface.blit(name, (col1_x + 28, y + i * 28 + 2))
        for j, st in enumerate(SHIP_TYPES[half:]):
            box = pygame.Rect(col2_x, y + j * 28, 22, 22)
            pygame.draw.rect(surface, st.color, box, border_radius=4)
            name = self.small_font.render(st.name, True, theme.COLOR_TEXT)
            surface.blit(name, (col2_x + 28, y + j * 28 + 2))

        # Timer + seleção centralizados (apenas segundos em vermelho)
        timer_prefix = "Próximo tiro em:"
        prefix_surf = self.list_font.render(timer_prefix, True, theme.COLOR_TITLE)
        secs_text = f" {int(self.countdown_remaining)}s"
        secs_surf = self.list_font.render(secs_text, True, (200, 40, 40))
        mid_total_w = prefix_surf.get_width() + secs_surf.get_width()
        mid_start_x = self.bottom_rect.centerx - (mid_total_w // 2)
        surface.blit(prefix_surf, (mid_start_x, base_y))
        surface.blit(secs_surf, (mid_start_x + prefix_surf.get_width(), base_y))

        sel_text = f"Posição: {self.selected_shot if self.selected_shot else '(nenhuma)'}"
        s_surf = self.sub_font.render(sel_text, True, theme.COLOR_TEXT)
        surface.blit(s_surf, (self.bottom_rect.centerx - s_surf.get_width() // 2, base_y + 28))

        # Toggle abaixo da posição (centralizado)
        btn_w, btn_h = 220, 34
        self.btn_random_toggle.rect.width = btn_w
        self.btn_random_toggle.rect.height = btn_h
        self.btn_random_toggle.rect.x = self.bottom_rect.centerx - btn_w // 2
        self.btn_random_toggle.rect.y = base_y + 28 + 26 + 6
        self.btn_random_toggle.draw(surface, self.sub_font, mouse_pos)

        # Score na direita (bloco à direita; textos alinhados à esquerda dentro do bloco)
        score_lines = [
            f"Tiros: {self.shots_made}",
            f"Atingido: {self.hits_received_count}",
            f"Destruídos: {self.distinct_players_hit_count}",
        ]
        # Alinhar os textos de score mais à direita mantendo o mesmo espaçamento da borda
        widths = [self.sub_font.render(line, True, theme.COLOR_TEXT).get_width() for line in score_lines]
        max_w = max(widths) if widths else 0
        start_x = content_right - max_w  # borda direita menos a largura máxima
        y_score = base_y
        for line in score_lines:
            ls = self.sub_font.render(line, True, theme.COLOR_TEXT)
            surface.blit(ls, (start_x, y_score))
            y_score += 28

    # Ação de "atirar" automática a cada 10s
    def execute_shot(self) -> None:
        # Se não há posição selecionada, escolha aleatória
        if not self.selected_shot:
            self.selected_shot = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))

        sx, sy = self.selected_shot
        print(f"[GameScreen] Executando tiro em {self.selected_shot}.")
        # Por padrão, marca como miss (preto). Integrações futuras podem chamar register_shot_result(True).
        self.shot_misses.add(self.selected_shot)
        self.shots_made += 1

        msg = f"shot:{sx},{sy}"
        self.udp_peer.send_shot_unicast(msg)

    # Permite registrar resultado de tiro (para UI de acerto em vermelho)
    def register_shot_result(self, hit: bool) -> None:
        if not self.selected_shot:
            return
        if hit:
            self.shot_hits.add(self.selected_shot)
            # remove de misses se houver
            if self.selected_shot in self.shot_misses:
                self.shot_misses.discard(self.selected_shot)

    def on_toggle_random(self) -> None:
        # Alterna o modo de tiros automáticos (random shots)
        self.random_shots_enabled = not self.random_shots_enabled
        self.btn_random_toggle.label = "Tiros aleatórios: ON" if self.random_shots_enabled else "Tiros aleatórios: OFF"
        # Se acabou de ligar o modo aleatório, já mostra uma posição aleatória selecionada
        if self.random_shots_enabled and self.selected_shot is None:
            self.selected_shot = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))

    def compute_score(self) -> Tuple[int, Dict[str, int], int, int]:
        # hits_received, hits_by_player, distinct_players_hit, final_score
        hits_received = self.hits_received_count
        hits_by_player = dict(self.hits_by_player)
        distinct_players_hit = len([ip for ip, c in hits_by_player.items() if c > 0])
        final_score = distinct_players_hit - hits_received
        return hits_received, hits_by_player, distinct_players_hit, final_score

    def layout_exit_modal_buttons(self):
        btn_gap = 20
        total_btn_w = self.btn_exit_confirm.rect.width + btn_gap + self.btn_exit_cancel.rect.width
        start_x = self.exit_modal_rect.centerx - total_btn_w // 2
        btn_y = self.exit_modal_rect.bottom - 20 - self.btn_exit_confirm.rect.height
        self.btn_exit_confirm.rect.x = start_x
        self.btn_exit_confirm.rect.y = btn_y
        self.btn_exit_cancel.rect.x = start_x + self.btn_exit_confirm.rect.width + btn_gap
        self.btn_exit_cancel.rect.y = btn_y

    def draw_exit_modal(self, surface, mouse_pos):
        # Overlay escurecido
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        rect = self.exit_modal_rect
        theme.draw_rounded_rect(surface, theme.COLOR_PANEL_BG, rect, radius=12, border=theme.COLOR_PANEL_BORDER)

        # Título
        title = "Resumo da Partida"
        title_surf = self.title_font.render(title, True, theme.COLOR_TITLE)
        surface.blit(title_surf, (rect.x + 20, rect.y + 16))

        # Conteúdo
        hits_received, hits_by_player, distinct_players_hit, final_score = self.compute_score()
        y = rect.y + 60
        line_gap = 26

        # Quantidade de vezes que foi atingido
        l1 = self.sub_font.render(f"Você foi atingido: {hits_received} vez(es)", True, theme.COLOR_TEXT)
        surface.blit(l1, (rect.x + 20, y))
        y += line_gap

        # Quantidade de acertos por jogador
        l2 = self.sub_font.render("Acertos por jogador:", True, theme.COLOR_TEXT)
        surface.blit(l2, (rect.x + 20, y))
        y += line_gap

        if hits_by_player:
            # Lista IP -> contagem
            for ip, cnt in hits_by_player.items():
                line = self.small_font.render(f"- {ip}: {cnt} acerto(s)", True, theme.COLOR_TEXT)
                surface.blit(line, (rect.x + 36, y))
                y += 22
        else:
            none_line = self.small_font.render("- Nenhum jogador atingido", True, theme.COLOR_TEXT_MUTED)
            surface.blit(none_line, (rect.x + 36, y))
            y += 22

        # Score final (destaque)
        y += 8
        score_text = self.list_font.render(f"Score Final: {final_score}  (Jogadores atingidos: {distinct_players_hit} - Atingido: {hits_received})", True, theme.COLOR_TITLE)
        surface.blit(score_text, (rect.x + 20, y))
        y += line_gap + 6

        # Botões
        btn_gap = 20
        total_btn_w = self.btn_exit_confirm.rect.width + btn_gap + self.btn_exit_cancel.rect.width
        start_x = rect.centerx - total_btn_w // 2
        btn_y = rect.bottom - 20 - self.btn_exit_confirm.rect.height

        self.btn_exit_confirm.rect.x = start_x
        self.btn_exit_confirm.rect.y = btn_y
        self.btn_exit_cancel.rect.x = start_x + self.btn_exit_confirm.rect.width + btn_gap
        self.btn_exit_cancel.rect.y = btn_y

        self.btn_exit_confirm.draw(surface, self.list_font, mouse_pos)
        self.btn_exit_cancel.draw(surface, self.list_font, mouse_pos)

    def on_confirm_exit(self) -> None:
        # Callback de saída (encerra janela de jogadores, etc.)
        if callable(self.on_exit_game):
            try:
                self.on_exit_game()
            except Exception:
                pass

        # Finaliza a aplicação
        try:
            pygame.quit()
        except Exception:
            pass
        sys.exit(0)

    def on_cancel_exit(self) -> None:
        self.exit_modal_open = False

    def register_incoming_hit(self, from_ip: str | None = None) -> None:
        # Incrementa contador de vezes que fui atingido
        self.hits_received_count += 1

    def register_outgoing_hit(self, player_ip: str) -> None:
        self.hits_by_player[player_ip] = self.hits_by_player.get(player_ip, 0) + 1
        self.distinct_players_hit_count = len([ip for ip, c in self.hits_by_player.items() if c > 0])

    def register_outgoing_destroyed(self, player_ip: str) -> None:
        self.destroyed_ships_by_player[player_ip] = self.destroyed_ships_by_player.get(player_ip, 0) + 1

    def handle_network_event(self, addr, msg) -> None:
        print(f"[GameScreen] Received message from {addr}: {msg}")
        
        if msg.startswith("shot:"):
            self.handle_incoming_shot(addr, msg)
        elif msg == "hit":
            self.register_outgoing_hit(addr[0])
            print(f"[GameScreen] Registered outgoing hit on enemy board at {addr}")
        elif msg == "destroyed":
            self.register_outgoing_destroyed(addr[0])
            print(f"[GameScreen] Enemy ship destroyed notification from {addr}")

    def parse_shot_message(self, msg: str) -> Optional[Tuple[int, int]]:
        payload = msg[5:].strip()
        x_str, y_str = payload.split(",", 1)
        x = int(x_str)
        y = int(y_str)
        return x, y

    def is_hit_on_my_board(self, x: int, y: int) -> bool:
        return (x, y) in self.my_board.occupied()

    def find_ship_key_at(self, x: int, y: int) -> Optional[str]:
        # Returns the ship key occupying (x, y) on my_board, if any
        for key, pl in self.my_board.placements.items():
            if (x, y) in pl.cells:
                return key
        return None

    def check_end_of_game(self) -> None:
        # Verifica se todas as embarcações do meu tabuleiro foram destruídas
        total = len(self.my_board.placements)
        if total > 0 and len(self.sunk_ships_on_my_board) >= total:
            if not getattr(self, "game_over", False):
                self.game_over = True
                self.udp_peer.send_lost_unicast("lost")

    def record_incoming_hit(self, x: int, y: int, addr) -> None:
        self.incoming_shot_hits.add((x, y))
        self.register_incoming_hit()
        # Track hit per ship and detect sunk
        ship_key = self.find_ship_key_at(x, y)
        if ship_key:
            hits = self.incoming_hits_by_ship.get(ship_key)
            if hits is None:
                hits = set()
                self.incoming_hits_by_ship[ship_key] = hits
            hits.add((x, y))

            # Notify attacker of hit
            try:
                if self.udp_peer and getattr(self.udp_peer, "tcp_peer", None):
                    self.udp_peer.tcp_peer.send_message(addr[0], 5001, "hit")
            except Exception:
                pass

            # Check sunk: all cells of this ship were hit
            ship_cells = self.my_board.placements.get(ship_key).cells if ship_key in self.my_board.placements else set()
            if ship_cells and hits.issuperset(ship_cells) and ship_key not in self.sunk_ships_on_my_board:
                self.sunk_ships_on_my_board.add(ship_key)
                self.last_incoming_event = f"sunk:{ship_key}"
                print(f"[GameScreen] SUNK ship '{ship_key}' on my board by {addr}")
                # Notify attacker of hit (sunk)
                try:
                    if self.udp_peer and getattr(self.udp_peer, "tcp_peer", None):
                        self.udp_peer.tcp_peer.send_message(addr[0], 5001, "destroyed")
                except Exception:
                    pass
                # Verifica fim de jogo após afundar um navio
                self.check_end_of_game()

        print(f"[GameScreen] HIT on my board at ({x},{y}) from {addr}")

    def record_incoming_miss(self, x: int, y: int, addr) -> None:
        self.incoming_shot_misses.add((x, y))
        print(f"[GameScreen] MISS on my board at ({x},{y}) from {addr}")

    def handle_incoming_shot(self, addr, msg) -> bool:
        coords = self.parse_shot_message(msg)
     
        x, y = coords
        if self.is_hit_on_my_board(x, y):
            self.record_incoming_hit(x, y, addr)
        else:
            self.record_incoming_miss(x, y, addr)
