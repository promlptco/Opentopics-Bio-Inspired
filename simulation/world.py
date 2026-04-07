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
    
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height
    
    def place_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity
    
    def remove_entity(self, entity_id: int) -> None:
        if entity_id in self.entities:
            del self.entities[entity_id]
    
    def place_food(self, x: int, y: int) -> None:
        if self.in_bounds(x, y):
            self.food_positions.add((x, y))
    
    def remove_food(self, x: int, y: int) -> None:
        self.food_positions.discard((x, y))
    
    def get_distance(self, pos1: tuple[int, int], pos2: tuple[int, int]) -> int:
        """Chebyshev distance (8-directional)"""
        return max(abs(pos1[0] - pos2[0]), abs(pos1[1] - pos2[1]))
    
    def get_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """8-directional neighbors"""
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self.in_bounds(nx, ny):
                    neighbors.append((nx, ny))
        return neighbors
    
    def get_step_toward(self, from_pos: tuple[int, int], to_pos: tuple[int, int]) -> tuple[int, int]:
        """Return next position moving 1 step toward target"""
        fx, fy = from_pos
        tx, ty = to_pos
        
        dx = 0 if tx == fx else (1 if tx > fx else -1)
        dy = 0 if ty == fy else (1 if ty > fy else -1)
        
        new_pos = (fx + dx, fy + dy)
        if self.in_bounds(*new_pos):
            return new_pos
        return from_pos