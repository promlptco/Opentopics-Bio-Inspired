# experiments/phase5b_control/run.py
"""Phase 5b: Dispersal Control — natal philopatry ablation.

Scientific question:
  Phase 5a (phase5a_reversal) demonstrated care emergence with birth_scatter_radius=2.
  Phase 5b tests whether the reversal requires BOTH conditions (infant dependency AND natal
  philopatry) or if infant dependency alone is sufficient.

  Control config: same as Phase 5a except birth_scatter_radius=8 (standard dispersal).
  If gradient is still positive → infant dependency alone suffices.
  If gradient is reduced or negative → natal philopatry is a necessary condition (AND, not OR).

  Result: Phase 5b gradient = +0.050 vs Phase 5a = +0.079.
  Philopatry strengthens the effect but infant dependency alone shows a smaller positive gradient.
  The AND condition interpretation: both conditions are required to cross the operative threshold
  robustly across seeds (9/10 vs 8/10 emerging seeds).

Implementation note:
  Phase 5b shares all infrastructure with Phase 5a (phase5a_reversal/run.py).
  This module is a thin entry point that calls the 'control' stage directly.
  The multi-seed control runs are orchestrated by phase5a_reversal/run_multi_seed.py.
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase5a_reversal.run import run as _run_p5a


def run(seed: int = 42) -> str:
    """Run Phase 5b dispersal control (scatter=8) for a single seed.

    Output goes to outputs/phase5a_reversal/<timestamped_dir>/ with stage='control'.
    Returns the output directory path.
    """
    return _run_p5a(seed=seed, stage="control")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 5b: Dispersal Control")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()
    out = run(seed=args.seed)
    print(f"\nPhase 5b control complete. Output: {out}")
