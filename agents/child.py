from __future__ import annotations
from agents.agent import Agent

class ChildAgent(Agent):
    def __init__(self, x: int, y: int, lineage_id: int, generation: int, mother_id: int):
        super().__init__(x, y, lineage_id, generation)
        self.mother_id: int = mother_id
        self.hunger: float = 0.0
        self.separation: float = 0.0
        self.distress: float = 0.0
    
    def update_hunger(self, hunger_rate: float) -> None:
        self.hunger = min(1.0, self.hunger + hunger_rate)
    
    def update_separation(self, steps_to_mother: int, perception_radius: int) -> None:
        self.separation = min(1.0, steps_to_mother / perception_radius)
    
    def update_distress(self) -> None:
        self.distress = (self.hunger + self.separation) / 2.0
    
    def receive_food(self, amount: float) -> float:
        """Return actual hunger reduced"""
        old_hunger = self.hunger
        self.hunger = max(0.0, self.hunger - amount)
        return old_hunger - self.hunger
    
    def check_death(self) -> str | None:
        if self.hunger >= 1.0:
            self.die()
            return "starvation"
        return None
    
    def check_maturity(self, maturity_age: int) -> bool:
        return self.age >= maturity_age and self.alive