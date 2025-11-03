from typing import Protocol

class Screen(Protocol):
    def handle_event(self, event) -> None:
        ...

    def render(self, surface) -> None:
        ...

    def on_enter(self) -> None:
        ...

    def on_exit(self) -> None:
        ...
