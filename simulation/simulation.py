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
            
    def _spawn_with_spacing(self, min_dist: int = 3) -> tuple[int, int]:
        """Find position at least min_dist from all agents."""
        for _ in range(50):  # max attempts
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            if not self.world.is_free((x, y)):
                continue
            
            too_close = False
            for entity in self.world.entities.values():
                if self.world.get_distance((x, y), entity.pos) < min_dist:
                    too_close = True
                    break
            
            if not too_close:
                return x, y
        
        # Fallback: random free cell
        return self._random_free_pos()
    
    def _random_free_pos(self) -> tuple[int, int]:
        for _ in range(100):
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            if self.world.is_free((x, y)):
                return x, y
        return 0, 0
    
    def run(self) -> None:
        self.initialize()
        while self.tick < self.config.max_ticks:
            self.step()
            self.tick += 1
    
    def step(self) -> None:
        # 1. Spawn food
        if len(self.world.food_positions) < self.config.init_food // 2:
            self._spawn_food(5)
        
        # 2. Update children
        for child in self.children:
            if not child.alive:
                continue
            child.update_hunger(self.config.hunger_rate)
            mother = self._get_mother_by_id(child.mother_id)
            if mother and mother.alive:
                steps = self.world.get_distance(child.pos, mother.pos)
            else:
                steps = self.config.perception_radius
            child.update_separation(steps, self.config.perception_radius)
            child.update_distress()
            child.tick_age()
            child.check_death()
        
        # 3. Shuffle mothers (randomize order)
        alive_mothers = [m for m in self.mothers if m.alive]
        random.shuffle(alive_mothers)
        
        # 4. Update mothers
        for mother in alive_mothers:
            mother.update_state(self.config.hunger_rate)
            mother.tick_age()
            mother.tick_commit()
            
            # Perceive
            visible_children = self._get_visible_children(mother)
            
            # Log choice if distressed child exists
            if any(c.distress >= 0.3 for c in visible_children):  # distress_threshold
                self._log_choice(mother, visible_children)
            
            # Check commitment or choose new
            if mother.has_commitment():
                domain = "care"
            else:
                domain = mother.choose_domain(visible_children)
            
            # Execute
            self._execute_action(mother, domain, visible_children)
            
            mother.check_death()
        
        # 5. Check maturation
        self._check_maturation()
        
        # 6. Check reproduction
        self._check_reproduction()
        
        # 7. Cleanup
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
            # Get target (committed or new)
            target = None
            if mother.has_commitment():
                target = self._get_child_by_id(mother.target_child_id)
            if target is None or not target.alive:
                target = mother.choose_child(visible_children)
                if target:
                    mother.set_target(target.id, duration=5)
            
            if target:
                dist = self.world.get_distance(mother.pos, target.pos)
                if dist == 1:
                    # Feed (adjacent)
                    total_cost = mother.get_total_cost(self.config.feed_cost)
                    success, benefit = mother.feed_child(target, self.config.feed_cost, self.world)
                    r = self.lineage.get_relatedness(mother.id, target.id)
                    self.logger.log_care(CareRecord(
                        tick=self.tick,
                        mother_id=mother.id,
                        child_id=target.id,
                        r=r,
                        benefit=benefit,
                        cost=total_cost,
                        success=success
                    ))
                    if success:
                        mother.plastic_update(benefit, self.config.plastic_gain)
                    mother.commit_ticks = 0  # done
                else:
                    # Move toward
                    new_pos = self.world.get_step_toward(mother.pos, target.pos)
                    if self.world.update_position(mother, new_pos):
                        mother.add_move_cost(self.config.move_cost)
                        mother.energy -= self.config.move_cost
        
        elif domain == "forage":
            if mother.held_food > 0:
                mother.eat(self.config.eat_gain)
            elif mother.pos in self.world.food_positions:
                mother.pick_food(self.world)
            else:
                nearest = self._nearest_food(mother.pos)
                if nearest:
                    new_pos = self.world.get_step_toward(mother.pos, nearest)
                    if self.world.update_position(mother, new_pos):
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