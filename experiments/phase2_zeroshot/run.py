# experiments/phase2_zeroshot/run.py
"""Phase 2: Zero-Shot Transfer
Load survival genomes into maternal world without plasticity.
Test if agents perform care at all.
"""
import sys
import os
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME = "phase2_zeroshot"


def load_evolved_genomes(phase3_run_dir: str) -> list[Genome]:
    """Load top genomes from Phase 3 (maternal evolution) output."""
    genome_path = os.path.join(phase3_run_dir, "top_genomes.json")
    
    if not os.path.exists(genome_path):
        print(f"Warning: {genome_path} not found. Run phase3_maternal evolution stage first.")
        return [Genome() for _ in range(10)]
    
    with open(genome_path, "r") as f:
        data = json.load(f)
    
    genomes = []
    for g in data:
        genomes.append(Genome(
            care_weight=g.get("care_weight", 0.5),
            forage_weight=g.get("forage_weight", 0.5),
            self_weight=g.get("self_weight", 0.5),
            learning_rate=g.get("learning_rate", 0.1),
            learning_cost=g.get("learning_cost", 0.05),
        ))
    return genomes


def run(seed: int = 42, phase3_run_dir: str = None):
    # 1. Load evolved genomes first — init_mothers matches genome count
    if phase3_run_dir:
        genomes = load_evolved_genomes(phase3_run_dir)
        source_genomes = phase3_run_dir
    else:
        genomes = None
        source_genomes = "default"

    n_mothers = len(genomes) if genomes else 12

    # 2. Config
    config = Config()
    config.seed = seed
    config.init_mothers = n_mothers
    # Children mature at tick ~100, doubling mothers to ~2×n_mothers.
    # Scale food to support peak population: 2×n × 1.8 food/mother ≈ 90 for n=25.
    config.init_food = n_mothers * 4  # ~100 for n=25; was 25 → extinction
    config.max_ticks = 1000

    # Zero-shot: children+care on, no reproduction, no mutation, no plasticity
    config.children_enabled = True
    config.care_enabled = True
    config.plasticity_enabled = False
    config.reproduction_enabled = False
    config.mutation_enabled = False

    # 3. Set seed
    set_seed(config.seed)

    # 4. Create output dir
    output_dir = create_run_dir(PHASE_NAME, config.seed)

    # 5. Save config + metadata
    save_config(config, output_dir)
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        seed=config.seed,
        num_agents=n_mothers * 2,
        grid_size=[config.width, config.height],
        plasticity_enabled=False,
        source_genomes=source_genomes,
        note="Evolved genomes from phase3 maternal evolution — zero-shot transfer test",
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

    # 7. Save logs + history
    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history, "energy": energy_history}, f)

    # 8. Zero-shot metrics
    total_care = len(sim.logger.care_records)
    successful_care = len([r for r in sim.logger.care_records if r.success])
    surviving_mothers = len([m for m in sim.mothers if m.alive])
    surviving_children = len([c for c in sim.children if c.alive])

    # Normalised care rate: events per alive-mother-tick (fair cross-run comparison)
    total_mother_ticks = sum(population_history)   # Σ n_alive over all ticks
    care_per_mother_tick = (successful_care / total_mother_ticks
                            if total_mother_ticks > 0 else 0.0)

    # Last tick any mother was alive
    last_alive_tick = max((t for t, p in enumerate(population_history) if p > 0),
                          default=0)

    metrics = {
        "total_care_events": total_care,
        "successful_care_events": successful_care,
        "surviving_mothers": surviving_mothers,
        "surviving_children": surviving_children,
        "care_rate_per_tick": successful_care / config.max_ticks,
        "care_per_mother_tick": care_per_mother_tick,
        "total_mother_ticks": total_mother_ticks,
        "last_alive_tick": last_alive_tick,
        "source_genomes": source_genomes,
        "note": (
            "Extinction is expected: no reproduction -> 50 mothers post-maturation "
            "with no replacement. Key metric is care_per_mother_tick."
        ),
    }
    with open(os.path.join(output_dir, "zeroshot_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    # 9. Plots + summary
    generate_all_plots(output_dir)
    print(f"\n[phase2_zeroshot] Output: {output_dir}")
    print(f"  Source genomes          : {source_genomes}")
    print(f"  Surviving mothers       : {surviving_mothers} / {n_mothers}  "
          f"(extinction expected — no reproduction)")
    print(f"  Last alive tick         : {last_alive_tick} / {config.max_ticks}")
    print(f"  Care events (success)   : {successful_care} / {total_care} total")
    print(f"  Care / alive-mother-tick: {care_per_mother_tick:.5f}  "
          f"(normalised — comparable across runs)")

    return output_dir


if __name__ == "__main__":
    # Pass phase3 evolution output dir to load evolved genomes, e.g.:
    # run(seed=42, phase3_run_dir="outputs/phase3_maternal/run_xxx")
    run(seed=42)