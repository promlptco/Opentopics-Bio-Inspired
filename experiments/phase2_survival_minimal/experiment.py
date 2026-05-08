# experiments/phase2_survival_minimal/experiment.py
"""
Phase 2 Experiment adapter — mother-only ecological survival baseline.

Entry point:
    python -m experiments.phase2_survival_minimal.experiment \
        --mode pipeline --duration 1000 --seeds 10 --workers 4

This is a thin wrapper over the existing new_run.py pipeline that satisfies
the BaseExperiment interface.  The old new_run.py is kept unchanged.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.base.experiment import BaseExperiment
from experiments.base.cli import build_parser, load_overrides, n_workers
from experiments.base.io_utils import make_output_dir


class Phase2Experiment(BaseExperiment):
    """Phase 2 single-run wrapper compatible with BaseExperiment."""

    def run_one(self, seed: int) -> dict:
        import random
        import numpy as np
        random.seed(seed)
        np.random.seed(seed)

        from experiments.phase2_survival_minimal.new_run import (
            SurvivalSimulation,
        )
        from experiments.phase2_survival_minimal.new_config import (
            BALANCED_BASELINE, make_config,
        )

        params  = dict(BALANCED_BASELINE)
        cfg     = make_config(params, self.cfg.max_ticks)
        cfg.seed = seed
        sim     = SurvivalSimulation(cfg)
        result  = sim.run()
        return {
            "seed":        seed,
            "final_pop":   result["final_pop"],
            "mean_energy": result["mean_energy"],
            "final_energy": result["final_energy"],
        }

    def make_plots(self, results: list[dict]) -> None:
        pass   # Phase 2 plot generation is handled inside new_run.py pipeline


def main() -> None:
    parser = build_parser(
        description="Phase 2 Ecological Survival Baseline",
        modes=["pipeline", "sweep", "single", "caretrap"],
        default_mode="pipeline",
        default_duration=1000,
    )
    args      = parser.parse_args()
    overrides = load_overrides(args)
    workers   = n_workers(args.workers)

    # Delegate directly to the existing Phase 2 pipeline
    from experiments.phase2_survival_minimal.new_run import run_experiment as _run
    import argparse as _ap

    # Build a compatible args namespace for new_run.run_experiment
    proxy = _ap.Namespace(
        mode=args.mode,
        duration=args.duration,
        repeats=args.seeds,
        workers=workers,
    )

    if args.output_dir:
        # Patch PROJECT_ROOT-relative output path via env (new_run uses out_dir computed internally)
        os.environ["PHASE2_OUTPUT_DIR"] = args.output_dir

    _run(proxy)


if __name__ == "__main__":
    main()
