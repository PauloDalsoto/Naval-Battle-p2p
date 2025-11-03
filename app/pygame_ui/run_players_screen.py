import pygame
from typing import List, Optional
from app.naval_battle.player_model import Player
from app.pygame_ui.screens.players_screen import PlayersScreen

def run_players_window(players: Optional[List[Player]] = None, local_ip: str = "", update_queue=None) -> None:
    pygame.init()
    width, height = 380, 300
    surface = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Jogadores Conectados")
    clock = pygame.time.Clock()

    screen = PlayersScreen(players=players, local_ip=local_ip)
    try:
        screen.on_enter()
    except Exception:
        pass

    running = True
    while running and screen.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            try:
                screen.handle_event(event)
            except Exception:
                pass

        dt = clock.tick(30) / 1000.0
        try:
            screen.update(dt)
        except Exception:
            pass

        # Consume queued updates to players list
        if update_queue:
            latest = None
            try:
                while True:
                    latest = update_queue.get_nowait()
            except Exception:
                pass
            if latest is not None:
                try:
                    screen.set_players(latest)
                except Exception:
                    pass

        try:
            screen.render(surface)
        except Exception:
            pass

        pygame.display.flip()

    pygame.display.quit()
