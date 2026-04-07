# experiments/phase0_evolution_sanity/run.py
"""Phase 0: Evolution Sanity Check"""
import sys
sys.path.append("../..")

from config import Config
from simulation.simulation import Simulation
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata

PHASE_NAME = "phase0_evolution_sanity"


def run(seed: int = 42):
    # 1. Load config
    config = Config()
    config.seed = seed
    config.init_mothers = 10
    config.max_ticks = 500
    
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
    )
    
    # 6. Run simulation
    sim = Simulation(config)
    sim.run()
    
    # 7. Save logs
    sim.logger.save_all(output_dir)
    
    # 8. Print summary
    print(f"Output saved to: {output_dir}")
    print(f"Surviving mothers: {len([m for m in sim.mothers if m.alive])}")
    print(f"Surviving children: {len([c for c in sim.children if c.alive])}")
    print(f"Choice records: {len(sim.logger.choice_records)}")
    print(f"Care records: {len(sim.logger.care_records)}")


if __name__ == "__main__":
    run(seed=42)