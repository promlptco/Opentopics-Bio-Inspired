# experiments/phase4_weight_sweep/experiment.py
"""
Phase 4 Experiment adapter — motivation weight sweep.

Entry point:
    python -m experiments.phase4_weight_sweep.experiment \
        --mode sweep --workers 4

Also accepts --param care_weight=1.5 etc. to run a non-grid single test.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.base.experiment import BaseExperiment
from experiments.base.cli import build_parser, load_overrides, n_workers


class Phase4Experiment(BaseExperiment):
    """Phase 4 single-run wrapper compatible with BaseExperiment."""

    def __init__(self, cfg, out_dir: Path,
                 care_weight: float = 1.0,
                 forage_weight: float = 1.0) -> None:
        super().__init__(cfg, out_dir)
        self.care_weight   = care_weight
        self.forage_weight = forage_weight

    def run_one(self, seed: int) -> dict:
        from experiments.phase4_weight_sweep.run import run_one as _run_one
        result = _run_one(self.care_weight, self.forage_weight, seed,
                          duration=self.cfg.max_ticks)
        return {
            "seed":            seed,
            "care_weight":     result["care_weight"],
            "forage_weight":   result["forage_weight"],
            "c_matr":          result["c_matr"],
            "m_surv":          result["m_surv"],
            "child_death_mu":  result["child_death_mu"],
            "care_pct":        result["care_pct"],
        }

    def make_plots(self, results: list[dict]) -> None:
        pass   # Phase 4 plots are generated in run.py's run_experiment()


def main() -> None:
    parser = build_parser(
        description="Phase 4 Motivation Weight Sweep",
        modes=["sweep", "single"],
        default_mode="sweep",
        default_duration=400,
    )
    args      = parser.parse_args()
    overrides = load_overrides(args)
    workers   = n_workers(args.workers)

    from experiments.phase4_weight_sweep.run import run_experiment as _run
    import argparse as _ap

    proxy = _ap.Namespace(
        mode=args.mode,
        workers=workers,
    )
    _run(proxy)


if __name__ == "__main__":
    main()
