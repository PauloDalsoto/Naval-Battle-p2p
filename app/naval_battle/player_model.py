from dataclasses import dataclass

@dataclass
class Player:
    ip: str
    active: bool = True
