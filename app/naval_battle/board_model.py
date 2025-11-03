import random
from typing import Dict, List, Optional, Set, Tuple
from app.pygame_ui.constants import GRID_SIZE, ORIENT_H, ORIENT_V
from app.naval_battle.ships import SHIP_TYPES, ShipType
from app.naval_battle.placement import Placement

Coord = Tuple[int, int]

class BoardModel:
    def __init__(self):
        # UI state
        self.selected_ship_key: Optional[str] = None
        self.current_orient: str = ORIENT_H
        self.grid_size: int = GRID_SIZE

        # Game variables
        self.ship_types: List[ShipType] = SHIP_TYPES
        self.placements: Dict[str, Placement] = {}

    def reset(self) -> None:
        self.placements.clear()

    def all_placed(self) -> bool:
        keys_needed = {t.key for t in self.ship_types}
        return keys_needed.issubset(set(self.placements.keys()))

    def get_ship_type(self, key: str) -> Optional[ShipType]:
        for t in self.ship_types:
            if t.key == key:
                return t
        return None

    def occupied(self) -> Set[Coord]:
        occ: Set[Coord] = set()
        for pl in self.placements.values():
            occ.update(pl.cells)
        return occ

    def can_place(self, key: str, start_x: int, start_y: int, orient: Optional[str] = None) -> Tuple[bool, Set[Coord]]:
        st = self.get_ship_type(key)
        if st is None:
            return False, set()
        orient = orient or self.current_orient
        cells: Set[Coord] = set()
        for i in range(st.size):
            x = start_x + (i if orient == ORIENT_H else 0)
            y = start_y + (0 if orient == ORIENT_H else i)
            if not (0 <= x < self.grid_size and 0 <= y < self.grid_size):
                return False, set()
            cells.add((x, y))
        # Overlap: allow overlap with own current cells (reposition)
        occ = self.occupied()
        own_cells = self.placements.get(key).cells if key in self.placements else set()
        for c in cells:
            if c in occ and c not in own_cells:
                return False, set()
        return True, cells

    def place_ship(self, key: str, start_x: int, start_y: int, orient: Optional[str] = None) -> bool:
        st = self.get_ship_type(key)
        if st is None:
            return False
        orient = orient or self.current_orient
        ok, cells = self.can_place(key, start_x, start_y, orient)
        if not ok:
            return False
        self.placements[key] = Placement(
            key=key,
            name=st.name,
            size=st.size,
            start=(start_x, start_y),
            orient=orient,
            cells=cells,
        )
        return True

    def remove_ship_at(self, x: int, y: int) -> Optional[str]:
        for key, pl in list(self.placements.items()):
            if (x, y) in pl.cells:
                del self.placements[key]
                return key
        return None

    def randomize(self, seed: Optional[int] = None) -> None:
        rnd = random.Random(seed)
        self.reset()
        for st in self.ship_types:
            placed = False
            attempts = 0
            while not placed and attempts < 5000:
                orient = rnd.choice([ORIENT_H, ORIENT_V])
                if orient == ORIENT_H:
                    x = rnd.randint(0, self.grid_size - st.size)
                    y = rnd.randint(0, self.grid_size - 1)
                else:
                    x = rnd.randint(0, self.grid_size - 1)
                    y = rnd.randint(0, self.grid_size - st.size)
                if self.place_ship(st.key, x, y, orient):
                    placed = True
                attempts += 1
            if not placed:
                self.reset()
                return self.randomize(seed=rnd.randint(0, 1_000_000))

    def set_selected_ship(self, key: Optional[str]) -> None:
        self.selected_ship_key = key

    def toggle_orientation(self) -> None:
        self.current_orient = ORIENT_V if self.current_orient == ORIENT_H else ORIENT_H

    def get_preview_cells(self, start_x: int, start_y: int, key: Optional[str] = None) -> Tuple[bool, Set[Coord]]:
        key = key or self.selected_ship_key
        if not key:
            return False, set()
        return self.can_place(key, start_x, start_y, self.current_orient)
