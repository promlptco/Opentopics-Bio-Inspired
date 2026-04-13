# experiments/p3_survival_full/run.py
"""Phase 03: Survival Gate — Full Simulation Engine
Same survival gate as Phase 02 but using the production Simulation class.
Confirms all features can be disabled without breaking the engine.
"""
import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import plot_population_and_energy

PHASE_NAME = "phase03_survival_full"


def run(seed: int = 42):
    # 1. Config — Baseline-V0 with all non-survival features disabled
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

    config.children_enabled = False
    config.care_enabled = False
    config.plasticity_enabled = False
    config.reproduction_enabled = False

    # 2. Seed
    set_seed(config.seed)

    # 3. Output dir
    output_dir = create_run_dir(PHASE_NAME, config.seed)

    # 4. Save config + metadata
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        seed=config.seed,
        num_agents=config.init_mothers,
        grid_size=[config.width, config.height],
        description="Survival-only gate: no children, care, plasticity, or reproduction",
    )

    # 5. Run tick-by-tick to collect metrics
    sim = Simulation(config)
    sim.initialize()

    population_history: list[int] = []
    energy_history: list[float] = []
    extinction_tick: int | None = None

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1

        alive = [m for m in sim.mothers if m.alive]
        population_history.append(len(alive))

        if alive:
            energy_history.append(sum(m.energy for m in alive) / len(alive))
        else:
            energy_history.append(0.0)
            if extinction_tick is None:
                extinction_tick = sim.tick
            break

    # 6. Collect results
    alive = [m for m in sim.mothers if m.alive]
    lifetimes = [m.age for m in sim.mothers]
    results = {
        "surviving_mothers": len(alive),
        "extinction_tick": extinction_tick,
        "mean_lifetime": sum(lifetimes) / len(lifetimes) if lifetimes else 0,
        "avg_energy_overall": sum(energy_history) / len(energy_history) if energy_history else 0,
        "final_tick": sim.tick,
        "passed": len(alive) > 0 and extinction_tick is None,
    }

    # 7. Save results + history
    with open(os.path.join(output_dir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)

    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history, "energy": energy_history}, f, indent=2)

    # 8. Plot
    plot_population_and_energy(population_history, energy_history, output_dir)

    # 9. Print summary
    print("=" * 50)
    print("PHASE 1: SURVIVAL-ONLY GATE")
    print("=" * 50)
    print(f"Output: {output_dir}")
    print(f"Surviving mothers : {results['surviving_mothers']}")
    print(f"Extinction tick   : {results['extinction_tick']}")
    print(f"Mean lifetime     : {results['mean_lifetime']:.1f}")
    print(f"Avg energy        : {results['avg_energy_overall']:.3f}")
    print(f"Final tick        : {results['final_tick']}")
    print("=" * 50)

    if results["passed"]:
        print("PASSED — Survival gate cleared. Proceed to phase04_care_erosion.")
    else:
        print("FAILED — Debug before proceeding.")
        if extinction_tick is not None:
            print(f"  Extinction at tick {extinction_tick}")
    print("=" * 50)

    return results


if __name__ == "__main__":
    run(seed=42)
