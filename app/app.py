import pygame
from app.pygame_ui.screens.placement_screen import PlacementScreen
from app.pygame_ui.screens.game_screen import GameScreen
from app.naval_battle.player_model import Player
from app.pygame_ui.constants import WINDOW_WIDTH, WINDOW_HEIGHT
from app.naval_battle.board_model import BoardModel
from app.pygame_ui.ui_core.screen_manager import ScreenManager
from multiprocessing import Process, Queue
from app.pygame_ui.run_players_screen import run_players_window
from app.network.p2p_udp import UdpPeer
from app.network.p2p_tcp import TcpPeer

class App:
    def __init__(self):
        pygame.init()
        self.surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Batalha Naval - p2p")
        self.clock = pygame.time.Clock()
        self.running = True

        self.board = BoardModel()
        placement = PlacementScreen(board=self.board, on_start_game=self.on_start_game)
        self.manager = ScreenManager(placement, "PlacementScreen")

        # Processo da segunda janela (lista de jogadores)
        self.players_proc: Process | None = None
        self.players_queue: Queue | None = None

        # Network
        self.udp_peer = None
        self.tcp_peer = None
        
    def on_start_game(self) -> None:
        # Configure UDP Peer (robust to errors to avoid blocking screen change)
        try:
            self.tcp_peer = TcpPeer()

            self.udp_peer = UdpPeer(tcp_peer=self.tcp_peer)
            self.udp_peer.send_broadcast_connecting()

        except Exception as e:
            print(f"[App] UDP peer initialization failed: {e}")
            self.udp_peer = None

        # Create and switch to GameScreen
        try:
            game = GameScreen(
                my_board=self.board,
                on_exit_game=self.on_exit_game,
                players_count_provider=self.get_players_count,
                udp_peer=self.udp_peer,
            )
            self.manager.set_screen(game, "GameScreen")
            print("[App] Switched to GameScreen.")
        except Exception as e:
            print(f"[App] Failed to switch to GameScreen: {e}")

        # Launch secondary players window in a separate process (best effort)
        try:
            initial_players = self.udp_peer.get_participants() if self.udp_peer else []
            local_ip = self.udp_peer.get_local_ip() if self.udp_peer else ""
            self.players_queue = Queue()
            self.players_proc = Process(target=run_players_window, args=(initial_players, local_ip, self.players_queue), daemon=True)
            self.players_proc.start()
            # envia snapshot inicial para a janela
            if self.players_queue is not None:
                try:
                    self.players_queue.put(initial_players)
                except Exception:
                    pass
        except Exception as e:
            print(f"[App] Failed to start players window process: {e}")
            self.players_proc = None
   

    def on_exit_game(self) -> None:
        # Avisa saída via UDP
        if self.udp_peer:
            try:
                self.udp_peer.send_broadcast_leaving()
            except Exception:
                pass

        # Encerra janela de jogadores se estiver ativa
       
        if self.players_proc and self.players_proc.is_alive():
            self.players_proc.terminate()
            self.players_proc.join(timeout=1.0)
       
    def get_players_count(self) -> int:
        participants = self.udp_peer.get_participants()
        return len(participants) + 1 
        return 3

    def run(self) -> None:
        while self.running:
            if self.manager.current_name == "GameScreen":
                self.handle_network()
            self.handle_ui()

        pygame.quit()

    def handle_network(self) -> None:
        conn, addr, msg_tcp = self.tcp_peer.wait_for_connection()
        addr, msg_udp = self.udp_peer.wait_for_message()

        if addr and msg_udp:
            self.manager.current.handle_network_event(addr, msg_udp)
            # Atualiza janela de jogadores quando há mudanças explícitas (Conectando/Saindo)
            if msg_udp in ("Conectando", "Saindo") and self.players_queue:
                try:
                    self.players_queue.put(self.udp_peer.get_participants())
                except Exception:
                    pass

        if msg_tcp and addr:
            self.manager.current.handle_network_event(addr, msg_tcp)
        
    def handle_ui(self) -> None:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            else:
                self.manager.current.handle_event(event)

        # Update (dt em segundos)
        dt = self.clock.tick(60) / 1000.0
        try:
            self.manager.current.update(dt)
        except Exception:
            pass

        # Render
        try:
            self.manager.current.render(self.surface)
        except Exception:
            pass

        pygame.display.flip()

def main() -> None:
    app = App()
    app.run()
