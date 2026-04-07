from __future__ import annotations
import random
from config import Config
from simulation.world import GridWorld
from agents.mother import MotherAgent
from agents.child import ChildAgent
from evolution.genome import Genome
from evolution.lineage import LineageManager
from logging_system.logger import Logger
from logging_system.records import ChoiceRecord, CareRecord

class Simulation:
    def __init__(self, config: Config):
        self.config = config
        self.world = GridWorld(config.width, config.height)
        self.lineage = LineageManager()
        self.logger = Logger()
        self.tick = 0
        
        self.mothers: list[MotherAgent] = []
        self.children: list[ChildAgent] = []
        
        random.seed(config.seed)
    
    def initialize(self) -> None:
        # Spawn initial mothers with children
        for i in range(self.config.init_mothers):
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            
            genome = Genome()  # default values
            mother = MotherAgent(x, y, lineage_id=i, generation=0, genome=genome)
            self.mothers.append(mother)
            self.world.place_entity(mother)
            self.lineage.register_mother(mother.id, i, 0)
            
            # Spawn child nearby
            cx, cy = self._nearby_pos(x, y)
            child = ChildAgent(cx, cy, lineage_id=i, generation=1, mother_id=mother.id)
            self.children.append(child)
            self.world.place_entity(child)
            self.lineage.register_birth(child.id, mother.id, i, 1)
            mother.own_child_id = child.id
        
        # Spawn food
        self._spawn_food(self.config.init_food)
    
    def _nearby_pos(self, x: int, y: int) -> tuple[int, int]:
        neighbors = self.world.get_neighbors(x, y)
        if neighbors:
            return random.choice(neighbors)
        return x, y
    
    def _spawn_food(self, count: int) -> None:
        for _ in range(count):
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            self.world.place_food(x, y)
    
    def run(self) -> None:
        self.initialize()
        while self.tick < self.config.max_ticks:
            self.step()
            self.tick += 1
        self._export_logs()
    
    def step(self) -> None:
        # 1. Spawn food if needed
        if len(self.world.food_positions) < self.config.init_food // 2:
            self._spawn_food(5)
        
        # 2. Update children
        for child in self.children:
            if not child.alive:
                continue
            child.update_hunger(self.config.hunger_rate)
            mother = self._get_mother_by_id(child.mother_id)
            if mother:
                steps = self.world.get_distance(child.pos, mother.pos)
            else:
                steps = self.config.perception_radius
            child.update_separation(steps, self.config.perception_radius)
            child.update_distress()
            child.tick_age()
            child.check_death()
        
        # 3. Update mothers
        for mother in self.mothers:
            if not mother.alive:
                continue
            mother.update_state(self.config.hunger_rate)
            mother.tick_age()
            
            # Perceive
            visible_children = self._get_visible_children(mother)
            
            # Log choice if any distressed child
            if any(c.distress > 0.1 for c in visible_children):
                self._log_choice(mother, visible_children)
            
            # Choose domain
            domain = mother.choose_domain(visible_children)
            
            # Execute action
            self._execute_action(mother, domain, visible_children)
            
            # Check death
            mother.check_death()
        
        # 4. Check maturation
        self._check_maturation()
        
        # 5. Check reproduction
        self._check_reproduction()
        
        # 6. Cleanup dead
        self.mothers = [m for m in self.mothers if m.alive]
        self.children = [c for c in self.children if c.alive]
    
    def _get_mother_by_id(self, mother_id: int) -> MotherAgent | None:
        for m in self.mothers:
            if m.id == mother_id:
                return m
        return None
    
    def _get_child_by_id(self, child_id: int) -> ChildAgent | None:
        for c in self.children:
            if c.id == child_id:
                return c
        return None
    
    def _get_visible_children(self, mother: MotherAgent) -> list[ChildAgent]:
        visible = []
        for child in self.children:
            if not child.alive:
                continue
            dist = self.world.get_distance(mother.pos, child.pos)
            if dist <= self.config.perception_radius:
                visible.append(child)
        return visible
    
    def _execute_action(self, mother: MotherAgent, domain: str, visible_children: list[ChildAgent]) -> None:
        if domain == "care":
            target = mother.choose_child(visible_children)
            if target:
                dist = self.world.get_distance(mother.pos, target.pos)
                if dist <= 1:
                    # Feed
                    success, benefit = mother.feed_child(target, self.config.feed_cost, self.world)
                    cost = self.config.feed_cost
                    r = self.lineage.get_relatedness(mother.id, target.id)
                    self.logger.log_care(CareRecord(
                        tick=self.tick,
                        mother_id=mother.id,
                        child_id=target.id,
                        r=r,
                        benefit=benefit,
                        cost=cost,
                        success=success
                    ))
                    if success:
                        mother.plastic_update(benefit, self.config.plastic_gain)
                else:
                    # Move toward child
                    mother.move_toward(target.pos, self.world)
                    mother.energy -= self.config.move_cost
        
        elif domain == "forage":
            if mother.held_food > 0:
                mother.eat(self.config.eat_gain)
            elif mother.pos in self.world.food_positions:
                mother.pick_food(self.world)
            else:
                # Move toward nearest food
                nearest = self._nearest_food(mother.pos)
                if nearest:
                    mother.move_toward(nearest, self.world)
                    mother.energy -= self.config.move_cost
        
        elif domain == "self":
            mother.rest(self.config.rest_recovery)
    
    def _nearest_food(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if not self.world.food_positions:
            return None
        return min(self.world.food_positions, key=lambda f: self.world.get_distance(pos, f))
    
    def _log_choice(self, mother: MotherAgent, visible_children: list[ChildAgent]) -> None:
        domain = mother.choose_domain(visible_children)
        target = mother.choose_child(visible_children) if domain == "care" else None
        
        record = ChoiceRecord(
            tick=self.tick,
            mother_id=mother.id,
            mother_energy=mother.energy,
            winner_domain=domain,
            candidate_child_ids=[c.id for c in visible_children],
            candidate_r=[self.lineage.get_relatedness(mother.id, c.id) for c in visible_children],
            candidate_distress=[c.distress for c in visible_children],
            candidate_distance=[self.world.get_distance(mother.pos, c.pos) for c in visible_children],
            chosen_child_id=target.id if target else None,
            chosen_r=self.lineage.get_relatedness(mother.id, target.id) if target else None,
            chosen_distress=target.distress if target else None,
            chosen_distance=self.world.get_distance(mother.pos, target.pos) if target else None,
        )
        self.logger.log_choice(record)
    
    def _check_maturation(self) -> None:
        for child in self.children[:]:
            if child.check_maturity(self.config.maturity_age):
                # Convert to mother
                genome = Genome()  # inherit from lineage later
                new_mother = MotherAgent(
                    child.x, child.y,
                    lineage_id=child.lineage_id,
                    generation=child.generation,
                    genome=genome
                )
                self.mothers.append(new_mother)
                self.world.place_entity(new_mother)
                self.lineage.register_mother(new_mother.id, child.lineage_id, child.generation)
                
                # Remove child
                child.die()
                self.world.remove_entity(child.id)
    
    def _check_reproduction(self) -> None:
        for mother in self.mothers:
            if not mother.alive:
                continue
            if not mother.can_reproduce(self.config.reproduction_threshold):
                continue
            if len(self.mothers) + len(self.children) >= self.config.max_population:
                continue
            
            # Spawn child
            cx, cy = self._nearby_pos(mother.x, mother.y)
            new_gen = mother.generation + 1
            child = ChildAgent(cx, cy, mother.lineage_id, new_gen, mother.id)
            self.children.append(child)
            self.world.place_entity(child)
            self.lineage.register_birth(child.id, mother.id, mother.lineage_id, new_gen)
            
            mother.own_child_id = child.id
            mother.energy -= self.config.reproduction_cost
            mother.cooldown = self.config.reproduction_cooldown
    
    def _export_logs(self) -> None:
        self.logger.export_choices("choice_log.csv")
        self.logger.export_cares("care_log.csv")