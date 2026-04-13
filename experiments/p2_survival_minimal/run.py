# experiments/p2_survival_minimal/run.py
"""
Phase 02: Survival Gate — Minimal Simulation
Verify agents can survive with only: MOVE_TO_FOOD, PICK_FOOD, EAT, REST
Uses a lightweight custom SurvivalSimulation (not the full Simulation class).
"""
import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.world import GridWorld
from agents.mother import MotherAgent
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots, plot_population_and_energy
import random

PHASE_NAME = "phase02_survival_minimal"


class SurvivalSimulation:
    """Minimal simulation for survival-only check."""
    
    def __init__(self, config: Config):
        self.config = config
        self.world = GridWorld(config.width, config.height)
        self.mothers: list[MotherAgent] = []
        self.tick = 0
        
        # Metrics
        self.total_food_picked = 0
        self.total_food_eaten = 0
        self.energy_history: list[float] = []
        self.population_history: list[int] = []
        self.extinction_tick: int | None = None
    
    def initialize(self) -> None:
        """Spawn mothers only, no children."""
        for i in range(self.config.init_mothers):
            x, y = self._random_free_pos()
            genome = Genome(
                care_weight=0.0,  # disabled
                forage_weight=0.7,
                self_weight=0.3,
                learning_rate=0.0,
                learning_cost=0.0,
            )
            mother = MotherAgent(x, y, lineage_id=i, generation=0, genome=genome)
            mother.energy = self.config.initial_energy
            self.mothers.append(mother)
            self.world.place_entity(mother)
        
        # Spawn food
        self._spawn_food(self.config.init_food)
        
    def _random_free_pos(self) -> tuple[int, int]:
        for _ in range(100):
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            if self.world.is_free((x, y)):
                return x, y
        return 0, 0
    
    def _spawn_food(self, count: int) -> None:
        spawned = 0
        for _ in range(count * 3):
            if spawned >= count:
                break
            x = random.randint(0, self.config.width - 1)
            y = random.randint(0, self.config.height - 1)
            if (x, y) not in self.world.food_positions:
                self.world.place_food(x, y)
                spawned += 1
    
    def step(self) -> None:
        # Shuffle for fairness
        alive_mothers = [m for m in self.mothers if m.alive]
        random.shuffle(alive_mothers)
        
        for mother in alive_mothers:
            
            # Tick age
            mother.tick_age()
            
            # Apply hunger
            mother.energy -= self.config.hunger_rate
            mother.energy = max(0.0, mother.energy)
            
            # Choose action (survival only: forage or rest)
            action = self._choose_action(mother)
            
            # Execute action
            self._execute_action(mother, action)
            
            # Check death
            if mother.energy <= 0:
                mother.die()
                self.world.remove_entity(mother.id)
        
        # Respawn food if low
        if len(self.world.food_positions) < self.config.init_food // 2:
            self._spawn_food(5)
        
        # Record metrics
        alive = [m for m in self.mothers if m.alive]
        self.population_history.append(len(alive))
        if alive:
            avg_energy = sum(m.energy for m in alive) / len(alive)
            self.energy_history.append(avg_energy)
        else:
            self.energy_history.append(0.0)
            if self.extinction_tick is None:
                self.extinction_tick = self.tick
    
    def _choose_action(self, mother: MotherAgent) -> str:
        """Survival-only: forage or rest."""
        # If very low energy and fatigued, rest
        if mother.energy < 0.2 and mother.fatigue > 0.5:
            return "REST"
        
        # If holding food, eat
        if mother.held_food > 0:
            return "EAT"
        
        # If on food, pick
        if mother.pos in self.world.food_positions:
            return "PICK_FOOD"
        
        # Otherwise move to food
        return "MOVE_TO_FOOD"
    
    def _execute_action(self, mother: MotherAgent, action: str) -> None:
        if action == "REST":
            mother.fatigue = max(0.0, mother.fatigue - self.config.rest_recovery)
        
        elif action == "EAT":
            if mother.held_food > 0:
                mother.held_food -= 1
                mother.energy = min(1.0, mother.energy + self.config.eat_gain)
                self.total_food_eaten += 1
        
        elif action == "PICK_FOOD":
            if mother.pos in self.world.food_positions:
                self.world.remove_food(*mother.pos)
                mother.held_food += 1
                self.total_food_picked += 1
        
        elif action == "MOVE_TO_FOOD":
            nearest = self._nearest_food(mother.pos)
            if nearest:
                new_pos = self.world.get_step_toward(mother.pos, nearest)
                if self.world.update_position(mother, new_pos):
                    mother.energy -= self.config.move_cost
                    mother.fatigue = min(1.0, mother.fatigue + 0.01)
    
    def _nearest_food(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if not self.world.food_positions:
            return None
        return min(self.world.food_positions, key=lambda f: self.world.get_distance(pos, f))
    
    def run(self) -> dict:
        self.initialize()
        
        while self.tick < self.config.max_ticks:
            self.step()
            self.tick += 1
            
            # Early stop if extinction
            if all(not m.alive for m in self.mothers):
                break
        
        return self.get_results()
    
    def get_results(self) -> dict:
        alive = [m for m in self.mothers if m.alive]
        lifetimes = [m.age for m in self.mothers]
        
        return {
            "surviving_mothers": len(alive),
            "extinction_tick": self.extinction_tick,
            "mean_lifetime": sum(lifetimes) / len(lifetimes) if lifetimes else 0,
            "total_food_picked": self.total_food_picked,
            "total_food_eaten": self.total_food_eaten,
            "avg_energy_overall": sum(self.energy_history) / len(self.energy_history) if self.energy_history else 0,
            "final_tick": self.tick,
            "passed": len(alive) > 0 and self.extinction_tick is None,
        }


def run(seed: int = 42):
    # 1. Config
    config = Config()
    config.seed = seed
    config.width = 30
    config.height = 30
    config.init_mothers = 12
    config.init_food = 45
    config.perception_radius = 8
    config.initial_energy = 0.85
    config.hunger_rate = 0.008
    config.move_cost = 0.005
    config.eat_gain = 0.25
    config.rest_recovery = 0.03
    config.max_ticks = 300
    
    # Disable all non-survival features
    config.children_enabled = False
    config.care_enabled = False
    config.plasticity_enabled = False
    config.reproduction_enabled = False
    
    # 2. Set seed
    set_seed(config.seed)
    
    # 3. Create output dir
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    
    # 4. Save config
    save_config(config, output_dir)
    
    # 5. Save metadata
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        seed=config.seed,
        num_agents=config.init_mothers,
        grid_size=[config.width, config.height],
        mode="survival_only",
    )
    
    # 6. Run simulation
    sim = SurvivalSimulation(config)
    results = sim.run()
    
    # 7. Save results
    results_path = os.path.join(output_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # 8. Save population history
    history_path = os.path.join(output_dir, "population_history.json")
    with open(history_path, "w") as f:
        json.dump({
            "population": sim.population_history,
            "energy": sim.energy_history,
        }, f, indent=2)
    
    # 9. Print results and generate plots
    plot_population_and_energy(
        sim.population_history,
        sim.energy_history,
        output_dir
    )
    
    print("=" * 50)
    print("STEP 1: SURVIVAL-ONLY CHECK")
    print("=" * 50)
    print(f"Output: {output_dir}")
    print(f"Surviving mothers: {results['surviving_mothers']}")
    print(f"Extinction tick: {results['extinction_tick']}")
    print(f"Mean lifetime: {results['mean_lifetime']:.1f}")
    print(f"Food picked: {results['total_food_picked']}")
    print(f"Food eaten: {results['total_food_eaten']}")
    print(f"Avg energy: {results['avg_energy_overall']:.3f}")
    print(f"Final tick: {results['final_tick']}")
    print("=" * 50)
    
    if results['passed']:
        print("✅ PASSED — Proceed to baseline experiments")
    else:
        print("❌ FAILED — Debug before proceeding")
        if results['extinction_tick'] is not None:
            print(f"   Extinction at tick {results['extinction_tick']}")
        if results['total_food_picked'] == 0:
            print("   Issue: No food picked — check movement/food spawn")
        if results['total_food_eaten'] == 0:
            print("   Issue: No food eaten — check eat logic")
    
    print("=" * 50)
    
    return results


if __name__ == "__main__":
    run(seed=42)