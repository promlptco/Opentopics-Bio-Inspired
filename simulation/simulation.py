from __future__ import annotations
import random
import numpy as np
from config import Config
from simulation.world import GridWorld
from agents.mother import MotherAgent
from agents.child import ChildAgent
from evolution.genome import Genome
from evolution.lineage import LineageManager
from logging_system.logger import Logger
from logging_system.records import ChoiceRecord, CareRecord, DeathRecord, BirthRecord

class Simulation:
    def __init__(self, config: Config):
        self.config = config
        self.world = GridWorld(config.width, config.height)
        self.lineage = LineageManager()
        self.logger = Logger()
        self.tick = 0
        
        self.mothers: list[MotherAgent] = []
        self.children: list[ChildAgent] = []
        self.genome_fallback_count: int = 0  # defensive counter; must stay 0 after birth-fix
        self._mother_by_id: dict[int, MotherAgent] = {}
        self._child_by_id:  dict[int, ChildAgent]  = {}
        self._food_frac: float = 0.0  # fractional accumulator for continuous trickle

        random.seed(config.seed)
        np.random.seed(config.seed)
    
    def initialize(self, genomes: list[Genome] | None = None) -> None:
        # Spawn initial mothers with children
        for i in range(self.config.init_mothers):
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)

            genome = genomes[i % len(genomes)].copy() if genomes else Genome(
                care_weight=self.config.care_weight,
                forage_weight=self.config.forage_weight,
                self_weight=self.config.self_weight,
            )
            mother = MotherAgent(x, y, lineage_id=i, generation=0, genome=genome)
            self.mothers.append(mother)
            self._mother_by_id[mother.id] = mother
            self.world.place_entity(mother)  # mothers block movement
            self.lineage.register_mother(mother.id, i, 0)

            # Spawn child nearby (only if children enabled)
            if self.config.children_enabled:
                cx, cy = self._nearby_pos(x, y)
                child = ChildAgent(cx, cy, lineage_id=i, generation=1, mother_id=mother.id)
                child.genome = mother.genome.mutate(
                    mutation_rate=self.config.mutation_rate,
                    sigma=self.config.mutation_sigma,
                    lock_learning_rate=self.config.lock_learning_rate,
                ) if self.config.mutation_enabled else mother.genome.copy()
                self.children.append(child)
                self._child_by_id[child.id] = child
                self.world.place_entity(child, blocking=False)  # children non-blocking (Change C)
                self.lineage.register_birth(child.id, mother.id, i, 1)
                mother.own_child_id = child.id
        
        # Spawn food
        self._spawn_food(self.config.init_food)
    
    def _nearby_pos(self, x: int, y: int) -> tuple[int, int]:
        neighbors = self.world.get_neighbors(x, y)
        if neighbors:
            return random.choice(neighbors)
        return self._random_free_pos()

    def _birth_pos(self, x: int, y: int) -> tuple[int, int]:
        """Find a free birth position within birth_scatter_radius of (x, y).
        Phase 5: tight radius keeps newborns near kin (natal philopatry).
        Falls back to _random_free_pos only if the radius is fully occupied.
        """
        radius = self.config.birth_scatter_radius
        candidates = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self.world.in_bounds(nx, ny) and self.world.is_free((nx, ny)):
                    candidates.append((nx, ny))
        if candidates:
            return random.choice(candidates)
        return self._random_free_pos()
    
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
    
    def initialize_with_genomes(self, genomes: list[Genome]) -> None:
        self.initialize(genomes)

    def run(self) -> None:
        self.initialize()
        while self.tick < self.config.max_ticks:
            self.step()
            self.tick += 1
    
    def step(self) -> None:
        # 1. Burst replenishment (Phase 5b params)
        _food_thresh = int(self.config.init_food * self.config.food_replenish_threshold_ratio)
        if len(self.world.food_positions) < _food_thresh:
            self._spawn_food(self.config.food_replenish_amount)

        # 1b. Continuous trickle (Phase 5d — disabled when continuous_food_rate == 0.0)
        if self.config.continuous_food_rate > 0.0:
            self._food_frac += self.config.continuous_food_rate
            to_add = int(self._food_frac)
            if to_add > 0:
                self._food_frac -= to_add
                if self.config.continuous_food_max > 0:
                    current = len(self.world.food_positions)
                    to_add = min(to_add, max(0, self.config.continuous_food_max - current))
                if to_add > 0:
                    self._spawn_food(to_add)
        
        # 2. Update children (only if enabled)
        if self.config.children_enabled:
            for child in self.children:
                if not child.alive:
                    continue
                hunger_rate = self.config.hunger_rate
                if child.age < self.config.maturity_age:
                    hunger_rate *= self.config.infant_starvation_multiplier
                # Change H: warm behavior — maternal proximity reduces infant hunger cost.
                # hunger_rate *= (1 - warmth_factor * warmth_proximity) within warmth_radius.
                if self.config.warmth_factor > 0:
                    mother = self._get_mother_by_id(child.mother_id)
                    if mother and mother.alive:
                        dist_to_mother = self.world.get_distance(child.pos, mother.pos)
                        if dist_to_mother <= self.config.warmth_radius:
                            warmth_prox = max(0.0, 1.0 - dist_to_mother / self.config.warmth_radius)
                            hunger_rate *= (1.0 - self.config.warmth_factor * warmth_prox)
                child.update_hunger(hunger_rate)
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
            mother.update_state(self.config.hunger_rate, self.config.fatigue_rate)
            mother.tick_age()
            if self.config.mother_max_age is not None and mother.age >= self.config.mother_max_age:
                mother.die()
            mother.tick_commit()
            
            # Perceive (empty if care disabled)
            visible_children = self._get_visible_children(mother) if self.config.care_enabled else []

            # Determine domain using the unified environmental-cue motivation model.
            # choose_motivation() returns uppercase ("FORAGE"/"SELF"/"CARE"); lower()
            # keeps it consistent with _execute_action() and _log_choice().
            if mother.has_commitment():
                domain = "care"
            else:
                nearest_food = self._nearest_food(mother.pos)
                dist_to_food = (
                    float(self.world.get_distance(mother.pos, nearest_food))
                    if nearest_food is not None
                    else None
                )
                care_child = (
                    mother.choose_child(visible_children)
                    if (self.config.care_enabled and visible_children)
                    else None
                )
                chosen, _, _ = mother.choose_motivation(
                    perception_radius=self.config.perception_radius,
                    tau=self.config.softmax_tau,  # Change G: tau from Config
                    child=care_child,
                    nearest_food=nearest_food,
                    distance_to_food=dist_to_food,
                    care_enabled=self.config.care_enabled,
                )
                mother.last_motivation = chosen
                domain = chosen.lower()

            # Option A — distress_sensitivity: cortisol-analog penalty for ignoring own
            # distressed infant. Fires whenever mother is NOT caring and her own child is
            # alive, nearby, and distressed. Makes non-care energetically costly so that
            # selection favours both care_weight and distress_sensitivity rising together.
            if (domain != "care" and self.config.care_enabled
                    and mother.own_child_id is not None):
                own_child = self._get_child_by_id(mother.own_child_id)
                if own_child and own_child.alive and mother.genome.distress_sensitivity > 0:
                    dist_to_own = self.world.get_distance(mother.pos, own_child.pos)
                    if dist_to_own <= self.config.perception_radius:
                        mother.energy = max(
                            0.0,
                            mother.energy - mother.genome.distress_sensitivity * own_child.distress,
                        )

            # Log choice if distressed child exists
            if any(c.distress >= 0.3 for c in visible_children):  # distress_threshold
                self._log_choice(mother, visible_children, domain)

            # Execute
            self._execute_action(mother, domain, visible_children)
            
            mother.check_death()
        
        # 5. Check maturation (only if children enabled)
        if self.config.children_enabled:
            self._check_maturation()

        # 6. Check reproduction (only if enabled)
        if self.config.reproduction_enabled:
            self._check_reproduction()

        # 7. Cleanup — log deaths and clear stale own_child_id references
        dead_child_ids = {c.id for c in self.children if not c.alive}
        for m in self.mothers:
            if not m.alive:
                self.logger.log_death(DeathRecord(
                    tick=self.tick, agent_id=m.id, agent_type="mother",
                    lineage_id=m.lineage_id, generation=m.generation, cause="starvation",
                ))
            elif m.own_child_id in dead_child_ids:
                # Bug #19 fix: child died — clear so mother can reproduce again
                m.own_child_id = None
        for c in self.children:
            if not c.alive:
                cause = "matured" if c.matured else "hunger"
                self.logger.log_death(DeathRecord(
                    tick=self.tick, agent_id=c.id, agent_type="child",
                    lineage_id=c.lineage_id, generation=c.generation, cause=cause,
                ))
        for m in self.mothers:
            if not m.alive:
                self._mother_by_id.pop(m.id, None)
        for c in self.children:
            if not c.alive:
                self._child_by_id.pop(c.id, None)
        self.mothers = [m for m in self.mothers if m.alive]
        if self.config.children_enabled:
            self.children = [c for c in self.children if c.alive]
    
    def _get_mother_by_id(self, mother_id: int) -> MotherAgent | None:
        return self._mother_by_id.get(mother_id)

    def _get_child_by_id(self, child_id: int) -> ChildAgent | None:
        return self._child_by_id.get(child_id)
    
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
                    mother.set_target(target.id, duration=20)  # Change D: 20-tick max commitment
            
            if target:
                dist = self.world.get_distance(mother.pos, target.pos)
                if dist == 0:
                    # Change C: same-cell feed. Children are non-blocking so the mother
                    # can occupy their cell. feed_child() guards dist > 1.
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
                        success=success,
                        mother_lineage_id=mother.lineage_id,
                        child_lineage_id=target.lineage_id,
                        is_own_child=(target.mother_id == mother.id),
                    ))
                    if success:
                        is_own = (target.mother_id == mother.id)
                        if is_own and mother.genome.care_recovery > 0:
                            mother.energy = min(
                                1.0,
                                mother.energy + mother.genome.care_recovery * benefit,
                            )
                        if self.config.plasticity_enabled:
                            if not self.config.plasticity_kin_conditional or is_own:
                                mother.plastic_update(
                                    benefit, self.config.plastic_gain,
                                    energy_cost=self.config.plasticity_energy_cost,
                                    noise_sigma=self.config.plasticity_noise_sigma,
                                )
                        # Change D: outcome-based commitment — release only when child sated.
                        if target.hunger < 0.3:
                            mother.commit_ticks = 0  # child sated; release commitment
                        # else: keep commitment; tick_commit() decrements naturally
                else:
                    # Move toward child (when dist > 0). Children are non-blocking so
                    # the mother moves onto their cell when dist becomes 1→0.
                    new_pos = self.world.get_step_toward(mother.pos, target.pos)
                    if self.world.update_position(mother, new_pos):
                        mother.add_move_cost(self.config.move_cost)
                        mother.energy -= self.config.move_cost
                        mother.fatigue = min(1.0, mother.fatigue + self.config.fatigue_rate)
        
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
                        mother.add_move_cost(self.config.move_cost)
                        mother.energy -= self.config.move_cost
                        mother.fatigue = min(1.0, mother.fatigue + self.config.fatigue_rate)

        elif domain == "self":
            mother.rest(self.config.rest_recovery)
    
    def _nearest_food(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if not self.world.food_positions:
            return None
        return min(self.world.food_positions, key=lambda f: self.world.get_distance(pos, f))
    
    def _log_choice(self, mother: MotherAgent, visible_children: list[ChildAgent], domain: str) -> None:
        if domain == "care":
            if mother.has_commitment():
                target = self._get_child_by_id(mother.target_child_id)
                if target is None or not target.alive:
                    target = mother.choose_child(visible_children)
            else:
                target = mother.choose_child(visible_children)
        else:
            target = None
        
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
                # Genome was assigned at birth — never depends on mother being alive at maturation
                if child.genome is not None:
                    genome = child.genome
                else:
                    # Defensive fallback only — should never trigger after birth-fix
                    genome = Genome()
                    self.genome_fallback_count += 1

                # Still need mother reference to clear own_child_id (Bug #19)
                birth_mother = self._get_mother_by_id(child.mother_id)
                if birth_mother:
                    birth_mother.own_child_id = None

                pos = child.pos  # save before removal

                # Mark matured BEFORE die() so the cleanup block logs cause="matured"
                # rather than cause="hunger" (R05 fix).
                child.matured = True
                child.die()
                self._child_by_id.pop(child.id, None)
                self.world.remove_entity(child.id)

                # Then place new mother at same position
                new_mother = MotherAgent(
                    pos[0], pos[1],
                    lineage_id=child.lineage_id,
                    generation=child.generation,
                    genome=genome
                )
                self.mothers.append(new_mother)
                self._mother_by_id[new_mother.id] = new_mother
                self.world.place_entity(new_mother)
                self.lineage.register_mother(new_mother.id, child.lineage_id, child.generation)
                self.lineage.parents[new_mother.id] = child.mother_id  # preserve pedigree chain through maturation
    
    def _check_reproduction(self) -> None:
        for mother in self.mothers:
            if not mother.alive:
                continue
            if not mother.can_reproduce(self.config.reproduction_threshold):
                continue
            if len(self.mothers) + len(self.children) >= self.config.max_population:
                continue
            
            # Spawn child — birth_scatter_radius controls natal philopatry (Phase 5)
            cx, cy = self._birth_pos(mother.x, mother.y)
            new_gen = mother.generation + 1
            child = ChildAgent(cx, cy, mother.lineage_id, new_gen, mother.id)
            child.genome = mother.genome.mutate(
                mutation_rate=self.config.mutation_rate,
                sigma=self.config.mutation_sigma,
                lock_learning_rate=self.config.lock_learning_rate,
            ) if self.config.mutation_enabled else mother.genome.copy()
            self.children.append(child)
            self._child_by_id[child.id] = child
            self.world.place_entity(child, blocking=False)  # Change C: non-blocking child
            self.lineage.register_birth(child.id, mother.id, mother.lineage_id, new_gen)

            mother.own_child_id = child.id
            mother.has_reproduced = True  # Change F: one-child-per-lifetime
            mother.energy -= self.config.reproduction_cost
            mother.cooldown = self.config.reproduction_cooldown

            self.logger.log_birth(BirthRecord(
                tick=self.tick,
                mother_id=mother.id,
                child_id=child.id,
                mother_lineage_id=mother.lineage_id,
                mother_generation=mother.generation,
                mother_care_weight=mother.genome.care_weight,
                mother_forage_weight=mother.genome.forage_weight,
                mother_self_weight=mother.genome.self_weight,
            ))

    def get_surviving_lineages(self) -> dict[int, dict]:
        """Return per-founding-lineage counts of living descendants.

        Returns a dict keyed by lineage_id:
          {lineage_id: {"mothers": int, "children": int, "total": int}}
        Useful for B_social (inclusive fitness) in Hamilton analysis.
        """
        result: dict[int, dict] = {}
        for m in self.mothers:
            if m.alive:
                lid = m.lineage_id
                if lid not in result:
                    result[lid] = {"mothers": 0, "children": 0, "total": 0}
                result[lid]["mothers"] += 1
                result[lid]["total"] += 1
        for c in self.children:
            if c.alive:
                lid = c.lineage_id
                if lid not in result:
                    result[lid] = {"mothers": 0, "children": 0, "total": 0}
                result[lid]["children"] += 1
                result[lid]["total"] += 1
        return result