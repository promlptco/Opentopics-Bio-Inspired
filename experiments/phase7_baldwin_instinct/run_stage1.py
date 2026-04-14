# experiments/phase7_baldwin_instinct/run_stage1.py
"""Phase 7 Stage 1 — entry point: evolution with kin-conditional plasticity (10 000 ticks).

Thin wrapper around run.py's run_evolution(). Use this for single-seed runs.
For multi-seed, use run_multi_seed.py.
"""
import sys
import os
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase7_baldwin_instinct.run import run_evolution

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 7 Stage 1: evolution with plasticity ON (10 000 ticks)"
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    out = run_evolution(seed=args.seed)
    print(f"\nStage 1 complete. Output: {out}")
    print(f"→ Run Stage 2 with: python run_stage2.py --seed {args.seed} --source-dir {out}")
