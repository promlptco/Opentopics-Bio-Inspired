# experiments/phase1_survival/run.py
"""Phase 1: Survival-Only Evolution (no children)"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from dataclasses import dataclass
from config import Config
from simulation.simulation import Simulation
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata
from utils.plotting import generate_all_plots

PHASE_NAME = "phase1_survival"


@dataclass
class Phase1Config(Config):
    """Config for survival-only evolution."""
    # Disable children
    init_mothers: int = 30
    init_food: int = 30
    max_ticks: int = 2000
    
    # No reproduction of children
    reproduction_enabled: bool = False  # flag for simulation


def run(seed: int = 42):
    # 1. Load config
    config = Phase1Config()
    config.seed = seed
    
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
        description="Survival-only evolution, no children",
    )
    
    # 6. Run simulation
    # TODO: Implement survival-only simulation variant
    generate_all_plots(output_dir)
    print(f"Phase 1 not fully implemented yet")
    print(f"Output dir created: {output_dir}")


if __name__ == "__main__":
    run(seed=42)