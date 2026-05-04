from __future__ import annotations
from typing import TYPE_CHECKING
from agents.agent import Agent

if TYPE_CHECKING:
    from evolution.genome import Genome

class ChildAgent(Agent):
    def __init__(self, x: int, y: int, lineage_id: int, generation: int, mother_id: int):
        super().__init__(x, y, lineage_id, generation)
        self.mother_id: int = mother_id
        self.genome: Genome | None = None  # assigned at birth by Simulation._check_reproduction
        self.separation: float = 0.0
        self.distress: float = 0.0
        self.matured: bool = False  # set True by _check_maturation before die(); distinguishes maturation from starvation in death log
    
    def update_hunger(self, hunger_rate: float) -> None:
        # Deplete energy (same mechanic as mother.update_state).
        # hunger = 1 - energy is the derived inverse: 0 = full, 1 = dead.
        self.energy = max(0.0, self.energy - hunger_rate)
        self.hunger = 1.0 - self.energy

    def update_separation(self, steps_to_mother: int, perception_radius: int) -> None:
        self.separation = min(1.0, steps_to_mother / perception_radius)

    def update_distress(self) -> None:
        self.distress = (self.hunger + self.separation) / 2.0

    def receive_food(self, amount: float) -> float:
        """Restore energy; return energy gained (= hunger reduced)."""
        old_energy = self.energy
        self.energy = min(1.0, self.energy + amount)
        self.hunger = 1.0 - self.energy
        return self.energy - old_energy

    def check_maturity(self, maturity_age: int) -> bool:
        return self.age >= maturity_age and self.alive