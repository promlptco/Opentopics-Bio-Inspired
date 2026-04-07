# experiments/phase3_maternal/run.py
"""Phase 3: Maternal Evolution"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME = "phase3_maternal"


def run(seed: int = 42):
    # 1. Load config
    config = Config()
    config.seed = seed
    config.init_mothers = 30
    config.init_food = 25
    config.max_ticks = 5000
    
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
        num_agents=config.init_mothers * 2,  # mothers + children
        grid_size=[config.width, config.height],
        commitment_ticks=5,
        perception_radius=config.perception_radius,
    )
    
    # 6. Run simulation
    sim = Simulation(config)
    sim.run()
    
    # 7. Save logs
    sim.logger.save_all(output_dir)
    
    # 8. Print summary
    generate_all_plots(output_dir)
    print(f"Output saved to: {output_dir}")
    print(f"Surviving mothers: {len([m for m in sim.mothers if m.alive])}")
    print(f"Surviving children: {len([c for c in sim.children if c.alive])}")
    print(f"Choice records: {len(sim.logger.choice_records)}")
    print(f"Care records: {len(sim.logger.care_records)}")


if __name__ == "__main__":
    run(seed=42)