# experiments/phase7_baldwin_instinct/run_stage2.py
"""Phase 7 Stage 2 — entry point: instinct test with plasticity OFF (10 000 ticks).

Thin wrapper around run.py's run_instinct(). Loads top_genomes.json from the
Stage 1 output directory and runs the instinct assimilation test.
"""
import sys
import os
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase7_baldwin_instinct.run import run_instinct

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 7 Stage 2: instinct test with plasticity OFF (10 000 ticks)"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--source-dir", required=True,
        help="Output directory from Stage 1 run_stage1.py (contains top_genomes.json)"
    )
    args = parser.parse_args()
    out = run_instinct(seed=args.seed, source_dir=args.source_dir)
    print(f"\nStage 2 complete. Output: {out}")
