from __future__ import annotations
from agents.entity import Entity

class Agent(Entity):
    def __init__(self, x: int, y: int, lineage_id: int, generation: int):
        super().__init__(x, y)
        self.lineage_id: int = lineage_id
        self.generation: int = generation
        self.age: int = 0
        self.energy: float = 1.0
        self.hunger: float = 0.0
    
    def tick_age(self) -> None:
        self.age += 1
    
    def check_death(self) -> str | None:
        """Return cause of death or None if alive"""
        if self.energy <= 0:
            self.die()
            return "starvation"
        return None