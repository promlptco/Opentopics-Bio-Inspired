# experiments/phase2_zeroshot/run.py
"""Phase 2: Zero-Shot Transfer
Load survival genomes into maternal world without plasticity.
Test if agents perform care at all.
"""
import sys
import os
import json
sys.path.append("../..")

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata

PHASE_NAME = "phase2_zeroshot"


def load_survival_genomes(phase1_run_dir: str) -> list[Genome]:
    """Load top genomes from Phase 1 output."""
    genome_path = os.path.join(phase1_run_dir, "top_genomes.json")
    
    if not os.path.exists(genome_path):
        print(f"Warning: {genome_path} not found, using default genomes")
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


def run(seed: int = 42, phase1_run_dir: str = None):
    # 1. Load config
    config = Config()
    config.seed = seed
    config.init_mothers = 30
    config.init_food = 25
    config.max_ticks = 1000
    
    # Disable plasticity for zero-shot test
    config.plastic_gain = 0.0
    
    # 2. Set seed
    set_seed(config.seed)
    
    # 3. Create output dir
    output_dir = create_run_dir(PHASE_NAME, config.seed)
    
    # 4. Load survival genomes (if available)
    if phase1_run_dir:
        genomes = load_survival_genomes(phase1_run_dir)
        source_genomes = phase1_run_dir
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
    )
    
    # 7. Run simulation
    sim = Simulation(config)
    if genomes:
        sim.initialize_with_genomes(genomes)
    else:
        sim.initialize()
    
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
    print(f"Output saved to: {output_dir}")
    print(f"Zero-shot care events: {successful_care}")
    print(f"Surviving children: {surviving_children}")


if __name__ == "__main__":
    run(seed=42)