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
    # 1. Load config
    config = Config()
    config.seed = seed
    config.init_mothers = 30
    config.init_food = 25
    config.max_ticks = 1000

    # Zero-shot: children+care on, plasticity+reproduction off
    config.children_enabled = True
    config.care_enabled = True
    config.plasticity_enabled = False
    config.reproduction_enabled = False

    # 2. Set seed
    set_seed(config.seed)

    # 3. Create output dir
    output_dir = create_run_dir(PHASE_NAME, config.seed)

    # 4. Load evolved genomes from phase3 (if available)
    if phase3_run_dir:
        genomes = load_evolved_genomes(phase3_run_dir)
        source_genomes = phase3_run_dir
    else:
        genomes = None
        source_genomes = "default"
    
    # 5. Save config
    save_config(config, output_dir)
    
    # 6. Save metadata
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        seed=config.seed,
        num_agents=config.init_mothers * 2,
        grid_size=[config.width, config.height],
        plasticity_enabled=False,
        source_genomes=source_genomes,
        note="Genomes loaded from phase3 maternal evolution run",
    )

    # 7. Run simulation
    sim = Simulation(config)
    sim.initialize(genomes)
    
    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
    
    # 8. Save logs
    sim.logger.save_all(output_dir)
    
    # 9. Compute zero-shot metrics
    total_care = len(sim.logger.care_records)
    successful_care = len([r for r in sim.logger.care_records if r.success])
    surviving_children = len([c for c in sim.children if c.alive])
    
    metrics = {
        "total_care_events": total_care,
        "successful_care_events": successful_care,
        "surviving_children": surviving_children,
        "care_rate": successful_care / config.max_ticks if config.max_ticks > 0 else 0,
    }
    
    metrics_path = os.path.join(output_dir, "zeroshot_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    
    # 10. Print summary
    generate_all_plots(output_dir)
    print(f"Output saved to: {output_dir}")
    print(f"Zero-shot care events: {successful_care}")
    print(f"Surviving children: {surviving_children}")


if __name__ == "__main__":
    # Pass phase3 evolution output dir to load evolved genomes, e.g.:
    # run(seed=42, phase3_run_dir="outputs/phase3_maternal/run_xxx")
    run(seed=42)