from dataclasses import dataclass
from typing import List, Tuple
from app.pygame_ui.ui_core import theme

# Ship specs (name, size)
SHIP_SPECS = [
    ("Porta-aviões", 5),
    ("Bombardeiro", 4),
    ("Submarino", 3),
    ("Lancha militar", 2),
]

@dataclass(frozen=True)
class ShipType:
    key: str
    name: str
    size: int
    color: Tuple[int, int, int]


def get_ship_types() -> List[ShipType]:
    types: List[ShipType] = []
    for idx, (name, size) in enumerate(SHIP_SPECS):
        color = theme.SHIP_COLORS[idx % len(theme.SHIP_COLORS)]
        key = name.lower().replace(" ", "_")
        types.append(ShipType(key=key, name=name, size=size, color=color))
    return types


# Lista padrão de tipos
SHIP_TYPES: List[ShipType] = get_ship_types()
