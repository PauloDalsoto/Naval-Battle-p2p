from dataclasses import dataclass, field
from typing import  Set, Tuple

Coord = Tuple[int, int]

@dataclass
class Placement:
    key: str
    name: str
    size: int
    start: Coord
    orient: str 
    cells: Set[Coord] = field(default_factory=set)
