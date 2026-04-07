from __future__ import annotations
class Entity:
    _next_id: int = 0
    
    def __init__(self, x: int, y: int):
        self.id: int = Entity._next_id
        Entity._next_id += 1
        self.x: int = x
        self.y: int = y
        self.alive: bool = True
    
    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)
    
    def move_to(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
    
    def die(self) -> None:
        self.alive = False