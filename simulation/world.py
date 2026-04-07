from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.entity import Entity


class GridWorld:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.food_positions: set[tuple[int, int]] = set()
        self.entities: dict[int, Entity] = {}
        self.occupied: set[tuple[int, int]] = set()
    
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height
    
    def is_free(self, pos: tuple[int, int]) -> bool:
        return pos not in self.occupied and self.in_bounds(*pos)
    
    def place_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity
        self.occupied.add(entity.pos)
    
    def remove_entity(self, entity_id: int) -> None:
        if entity_id in self.entities:
            entity = self.entities[entity_id]
            self.occupied.discard(entity.pos)
            del self.entities[entity_id]
    
    def update_position(self, entity: Entity, new_pos: tuple[int, int]) -> bool:
        """Move entity if new_pos is free. Return success."""
        if new_pos == entity.pos:
            return False
        if not self.is_free(new_pos):
            return False
        self.occupied.discard(entity.pos)
        entity.move_to(*new_pos)
        self.occupied.add(new_pos)
        return True
    
    def place_food(self, x: int, y: int) -> None:
        if self.in_bounds(x, y):
            self.food_positions.add((x, y))
    
    def remove_food(self, x: int, y: int) -> None:
        self.food_positions.discard((x, y))
    
    def get_distance(self, pos1: tuple[int, int], pos2: tuple[int, int]) -> int:
        """Chebyshev distance (8-directional)."""
        return max(abs(pos1[0] - pos2[0]), abs(pos1[1] - pos2[1]))
    
    def get_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """8-directional neighbors that are free."""
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self.in_bounds(nx, ny) and self.is_free((nx, ny)):
                    neighbors.append((nx, ny))
        return neighbors
    
    def get_step_toward(self, from_pos: tuple[int, int], to_pos: tuple[int, int]) -> tuple[int, int]:
        """Return next free position toward target, or stay."""
        fx, fy = from_pos
        tx, ty = to_pos
        
        dx = 0 if tx == fx else (1 if tx > fx else -1)
        dy = 0 if ty == fy else (1 if ty > fy else -1)
        
        # Try primary direction
        primary = (fx + dx, fy + dy)
        if self.is_free(primary):
            return primary
        
        # Try secondary (only dx or only dy)
        if dx != 0:
            alt1 = (fx + dx, fy)
            if self.is_free(alt1):
                return alt1
        if dy != 0:
            alt2 = (fx, fy + dy)
            if self.is_free(alt2):
                return alt2
        
        # Stuck
        return from_pos