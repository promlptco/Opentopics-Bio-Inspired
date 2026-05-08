# experiments/phase3_survival_full/experiment.py
"""
Phase 3 Experiment adapter — mother+child ecological calibration.

Entry point:
    python -m experiments.phase3_survival_full.experiment \
        --mode pipeline --duration 400 --workers 4 \
        --param init_food=200 --param eat_gain=0.5

Supports all modes from run.py: pipeline, sweep, single, caretrap.
--param and --config overrides are applied to BALANCED_BASELINE before running.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.base.experiment import BaseExperiment
from experiments.base.cli import build_parser, load_overrides, n_workers
from experiments.base.io_utils import make_output_dir


class Phase3Experiment(BaseExperiment):
    """Phase 3 single-run wrapper compatible with BaseExperiment."""

    def __init__(self, cfg, out_dir: Path, params: dict | None = None) -> None:
        super().__init__(cfg, out_dir)
        self.params = params or {}

    def run_one(self, seed: int) -> dict:
        from experiments.phase3_survival_full.run import run_one as _run_one
        result = _run_one(self.params, seed, self.cfg.max_ticks)
        return {
            "seed":                   seed,
            "final_pop":              result["final_pop"],
            "mean_energy":            result["mean_energy"],
            "final_energy":           result["final_energy"],
            "child_maturation_rate":  result.get("child_maturation_rate", 0.0),
            "child_death_tick_mean":  result.get("child_death_tick_mean", 0.0),
            "care_pct":               result.get("care_pct", 0.0),
            "forage_pct":             result.get("forage_pct", 0.0),
            "self_pct":               result.get("self_pct", 0.0),
        }

    def make_plots(self, results: list[dict]) -> None:
        pass   # Phase 3 plots are generated inside the pipeline


def main() -> None:
    parser = build_parser(
        description="Phase 3 Mother+Child Ecological Calibration",
        modes=["pipeline", "sweep", "single", "caretrap"],
        default_mode="pipeline",
        default_duration=400,
    )
    args      = parser.parse_args()
    overrides = load_overrides(args)
    workers   = n_workers(args.workers)

    from experiments.phase3_survival_full.run import run_experiment as _run
    import argparse as _ap

    proxy = _ap.Namespace(
        mode=args.mode,
        duration=args.duration,
        repeats=args.seeds,
        workers=workers,
    )
    _run(proxy)


if __name__ == "__main__":
    main()
