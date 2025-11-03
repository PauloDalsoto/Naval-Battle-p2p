from typing import Optional
from app.pygame_ui.ui_core.screen import Screen

class ScreenManager:
    def __init__(self, initial: Screen, initial_name: Optional[str] = None) -> None:
        self.current: Screen = initial
        self.current_name: Optional[str] = initial_name
        # Notifica que a tela atual foi ativada
        try:
            self.current.on_enter()
        except Exception:
            pass

    def set_screen(self, next_screen: Screen, next_name: Optional[str] = None) -> None:
        # Sai da tela atual
        try:
            self.current.on_exit()
        except Exception:
            pass

        # Entra na nova tela
        self.current = next_screen
        self.current_name = next_name
        try:
            self.current.on_enter()
        except Exception:
            pass
