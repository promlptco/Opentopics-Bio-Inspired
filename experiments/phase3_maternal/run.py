# experiments/phase3_maternal/run.py
"""Phase 3: Maternal — supports 3 stages via `stage` parameter.

Stages:
  baseline_c0  : fixed weights, no evolution, no plasticity  (Baseline-C0)
  baseline_r0  : random weights, no evolution, no plasticity (Baseline-R0)
  evolution    : full evolution + optional plasticity         (default)
"""
import sys
import os
import json
import random as _random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME = "phase3_maternal"


def _fixed_genomes(care: float, forage: float, self_w: float, n: int) -> list[Genome]:
    return [Genome(care_weight=care, forage_weight=forage, self_weight=self_w) for _ in range(n)]


def _random_genomes(n: int) -> list[Genome]:
    return [
        Genome(
            care_weight=_random.uniform(0.0, 1.0),
            forage_weight=_random.uniform(0.0, 1.0),
            self_weight=_random.uniform(0.0, 1.0),
        )
        for _ in range(n)
    ]


def _save_top_genomes(sim: Simulation, output_dir: str) -> None:
    alive = [m for m in sim.mothers if m.alive]
    data = [
        {
            "care_weight": m.genome.care_weight,
            "forage_weight": m.genome.forage_weight,
            "self_weight": m.genome.self_weight,
            "learning_rate": m.genome.learning_rate,
            "learning_cost": m.genome.learning_cost,
        }
        for m in alive
    ]
    with open(os.path.join(output_dir, "top_genomes.json"), "w") as f:
        json.dump(data, f, indent=2)


def run(
    seed: int = 42,
    stage: str = "evolution",
    care_weight: float = 0.7,
    forage_weight: float = 0.85,
    self_weight: float = 0.55,
):
    """
    stage:
      'baseline_c0' — fixed weights, children+care on, evolution+plasticity off
      'baseline_r0' — random weights, children+care on, evolution+plasticity off
      'evolution'   — full evolution (all flags on, default)
    """
    # 1. Config
    config = Config()
    config.seed = seed
    config.init_mothers = 12
    config.init_food = 45
    config.max_ticks = 5000

    if stage in ("baseline_c0", "baseline_r0"):
        config.children_enabled = True
        config.care_enabled = True
        config.plasticity_enabled = False
        config.reproduction_enabled = True
        config.mutation_enabled = False     # fixed genomes — no evolution
    elif stage == "evolution":
        config.children_enabled = True
        config.care_enabled = True
        config.plasticity_enabled = False   # plasticity added in phase4
        config.reproduction_enabled = True
        config.mutation_enabled = True
    else:
        raise ValueError(f"Unknown stage: {stage!r}. Use 'baseline_c0', 'baseline_r0', or 'evolution'.")

    # 2. Seed
    set_seed(config.seed)

    # 3. Build genome list
    if stage == "baseline_c0":
        genomes = _fixed_genomes(care_weight, forage_weight, self_weight, config.init_mothers)
    elif stage == "baseline_r0":
        genomes = _random_genomes(config.init_mothers)
    else:
        genomes = None  # default Genome() in Simulation.initialize

    # 4. Output dir
    output_dir = create_run_dir(PHASE_NAME, config.seed)

    # 5. Save config + metadata
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        stage=stage,
        seed=config.seed,
        num_agents=config.init_mothers * 2,  # 12 mothers + 12 children
        grid_size=[config.width, config.height],
        perception_radius=config.perception_radius,
        care_weight=care_weight if stage == "baseline_c0" else "random" if stage == "baseline_r0" else "evolved",
    )

    # 6. Run simulation
    sim = Simulation(config)
    sim.initialize(genomes)

    population_history = []
    energy_history = []

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        alive_m = [m for m in sim.mothers if m.alive]
        population_history.append(len(alive_m))
        energy_history.append(
            sum(m.energy for m in alive_m) / len(alive_m) if alive_m else 0.0
        )

    # 7. Save logs + genomes
    sim.logger.save_all(output_dir)
    _save_top_genomes(sim, output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history, "energy": energy_history}, f)

    # 8. Plots + summary
    generate_all_plots(output_dir)
    alive_m = len([m for m in sim.mothers if m.alive])
    alive_c = len([c for c in sim.children if c.alive])
    print(f"[phase3 | {stage}] Output: {output_dir}")
    print(f"  Surviving mothers : {alive_m}")
    print(f"  Surviving children: {alive_c}")
    print(f"  Choice records    : {len(sim.logger.choice_records)}")
    print(f"  Care records      : {len(sim.logger.care_records)}")
    print(f"  top_genomes.json  : {alive_m} genomes saved")

    return output_dir


if __name__ == "__main__":
    # Default: run balanced fixed-weight baseline (Baseline-C0 candidate)
    run(seed=42, stage="baseline_c0", care_weight=0.7, forage_weight=0.85, self_weight=0.55)
