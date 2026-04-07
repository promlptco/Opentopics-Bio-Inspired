# experiments/phase4_plasticity/run.py
"""Phase 4: Plasticity / Baldwin Effect Analysis
Track learning_rate evolution across generations.
Measure zero-shot performance improvement.
"""
import sys
import os
import json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME = "phase4_plasticity"


def run(seed: int = 42):
    # 1. Load config
    config = Config()
    config.seed = seed
    config.init_mothers = 30
    config.init_food = 25
    config.max_ticks = 10000  # longer for Baldwin effect
    
    # Enable plasticity
    config.plastic_gain = 0.1
    
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
        num_agents=config.init_mothers * 2,
        grid_size=[config.width, config.height],
        plasticity_enabled=True,
        plastic_gain=config.plastic_gain,
    )
    
    # 6. Run simulation with generation tracking
    sim = Simulation(config)
    sim.initialize()
    
    generation_snapshots = []
    snapshot_interval = 1000
    
    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        
        # Snapshot every interval
        if sim.tick % snapshot_interval == 0:
            snapshot = collect_generation_snapshot(sim)
            generation_snapshots.append(snapshot)
    
    # 7. Save logs
    sim.logger.save_all(output_dir)
    
    # 8. Save generation snapshots
    snapshots_path = os.path.join(output_dir, "generation_snapshots.json")
    with open(snapshots_path, "w") as f:
        json.dump(generation_snapshots, f, indent=2)
    
    # 9. Compute Baldwin metrics
    metrics = compute_baldwin_metrics(generation_snapshots)
    metrics_path = os.path.join(output_dir, "baldwin_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    
    # 10. Print summary
    generate_all_plots(output_dir)
    print(f"Output saved to: {output_dir}")
    print(f"Generation snapshots: {len(generation_snapshots)}")
    print(f"Final avg learning_rate: {metrics.get('final_avg_learning_rate', 'N/A')}")


def collect_generation_snapshot(sim: Simulation) -> dict:
    """Collect genome stats at current tick."""
    mothers = [m for m in sim.mothers if m.alive]
    
    if not mothers:
        return {
            "tick": sim.tick,
            "num_mothers": 0,
            "avg_care_weight": None,
            "avg_learning_rate": None,
            "avg_generation": None,
        }
    
    return {
        "tick": sim.tick,
        "num_mothers": len(mothers),
        "avg_care_weight": sum(m.genome.care_weight for m in mothers) / len(mothers),
        "avg_forage_weight": sum(m.genome.forage_weight for m in mothers) / len(mothers),
        "avg_self_weight": sum(m.genome.self_weight for m in mothers) / len(mothers),
        "avg_learning_rate": sum(m.genome.learning_rate for m in mothers) / len(mothers),
        "avg_learning_cost": sum(m.genome.learning_cost for m in mothers) / len(mothers),
        "avg_generation": sum(m.generation for m in mothers) / len(mothers),
    }


def compute_baldwin_metrics(snapshots: list[dict]) -> dict:
    """Compute Baldwin effect metrics from snapshots."""
    if not snapshots:
        return {}
    
    valid = [s for s in snapshots if s.get("avg_learning_rate") is not None]
    
    if len(valid) < 2:
        return {"insufficient_data": True}
    
    first = valid[0]
    last = valid[-1]
    
    return {
        "initial_avg_learning_rate": first.get("avg_learning_rate"),
        "final_avg_learning_rate": last.get("avg_learning_rate"),
        "learning_rate_change": last.get("avg_learning_rate", 0) - first.get("avg_learning_rate", 0),
        "initial_avg_care_weight": first.get("avg_care_weight"),
        "final_avg_care_weight": last.get("avg_care_weight"),
        "care_weight_change": last.get("avg_care_weight", 0) - first.get("avg_care_weight", 0),
        "num_snapshots": len(valid),
    }


if __name__ == "__main__":
    run(seed=42)