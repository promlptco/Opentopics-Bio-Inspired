from __future__ import annotations
from typing import TYPE_CHECKING
from agents import child
from agents.agent import Agent
from evolution.genome import Genome
from simulation import world

if TYPE_CHECKING:
    from agents.child import ChildAgent
    from simulation.world import GridWorld

class MotherAgent(Agent):
    def __init__(self, x: int, y: int, lineage_id: int, generation: int, genome: Genome):
        super().__init__(x, y, lineage_id, generation)
        self.genome: Genome = genome
        self.stress: float = 0.0
        self.fatigue: float = 0.0
        self.held_food: int = 0
        self.own_child_id: int | None = None
        self.cooldown: int = 0
        self.target_child_id: int | None = None
        self.commit_ticks: int = 0
        self.pending_move_cost: float = 0.0
        
    # === Tracking Movement Cost ===
    
    def add_move_cost(self, cost: float) -> None:
        self.pending_move_cost += cost
    
    def get_total_cost(self, feed_cost: float) -> float:
        total = self.pending_move_cost + feed_cost
        self.pending_move_cost = 0.0
        return total
        
    # === Commitment ===
    
    def set_target(self, child_id: int, duration: int = 5) -> None:
        self.target_child_id = child_id
        self.commit_ticks = duration
    
    def tick_commit(self) -> None:
        if self.commit_ticks > 0:
            self.commit_ticks -= 1
        else:
            self.target_child_id = None
    
    def has_commitment(self) -> bool:
        return self.commit_ticks > 0 and self.target_child_id is not None
    
    # === Motivation ===
    
    def calc_care_score(self, child: ChildAgent) -> float:
        return self.genome.care_weight * child.distress
    
    def calc_forage_motivation(self) -> float:
        return self.genome.forage_weight * (1.0 - self.energy)
    
    def calc_self_motivation(self) -> float:
        return self.genome.self_weight * (self.stress + self.fatigue) / 2.0
    
    def choose_domain(self, visible_children: list[ChildAgent]) -> str:
        m_care = 0.0
        if visible_children:
            m_care = max(self.calc_care_score(c) for c in visible_children)
        
        m_forage = self.calc_forage_motivation()
        m_self = self.calc_self_motivation()
        
        scores = {"care": m_care, "forage": m_forage, "self": m_self}
        return max(scores, key=scores.get)
    
    def choose_child(self, visible_children: list[ChildAgent]) -> ChildAgent | None:
        if not visible_children:
            return None
        return max(visible_children, key=lambda c: self.calc_care_score(c))
    
    # === Actions ===
    
    def move_toward(self, target_pos: tuple[int, int], world: GridWorld) -> float:
        new_pos = world.get_step_toward(self.pos, target_pos)
        self.move_to(*new_pos)
        return 0.01  # move_cost
    
    def pick_food(self, world: GridWorld) -> bool:
        if self.pos in world.food_positions:
            world.remove_food(*self.pos)
            self.held_food += 1
            return True
        return False
    
    def eat(self, eat_gain: float) -> None:
        if self.held_food > 0:
            self.held_food -= 1
            self.energy = min(1.0, self.energy + eat_gain)
    
    def feed_child(self, child: ChildAgent, feed_cost: float, world: GridWorld) -> tuple[bool, float]:
        """Feed child if adjacent (dist = 1), not same cell"""
        dist = world.get_distance(self.pos, child.pos)
        if dist != 1:  # adjacent to the cell
            return False, 0.0
        
        self.energy -= feed_cost
        hunger_reduced = child.receive_food(0.2)
        return True, hunger_reduced
    
    def rest(self, rest_recovery: float) -> None:
        self.fatigue = max(0.0, self.fatigue - rest_recovery)
    
    # === Reproduction ===
    
    def can_reproduce(self, threshold: float) -> bool:
        return (
            self.energy >= threshold
            and self.own_child_id is None
            and self.cooldown == 0
        )
    
    def tick_cooldown(self) -> None:
        if self.cooldown > 0:
            self.cooldown -= 1
    
    # === Plasticity ===
    
    def plastic_update(self, reward: float, plastic_gain: float) -> None:
        delta = self.genome.learning_rate * reward * plastic_gain
        self.genome.care_weight = max(0.0, min(1.0, self.genome.care_weight + delta))
        self.energy -= self.genome.learning_cost * abs(delta)
    
    # === State update ===
    
    def update_state(self, hunger_rate: float) -> None:
        self.hunger = min(1.0, self.hunger + hunger_rate)
        self.energy = max(0.0, self.energy - self.hunger * 0.01)
        self.tick_cooldown()