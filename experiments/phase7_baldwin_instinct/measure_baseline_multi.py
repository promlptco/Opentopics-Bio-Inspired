# experiments/p6_controls_and_baldwin/p6c_depleted_baseline/run_multi_seed.py
"""Phase 10: Depleted-Init Baseline Zero-Shot — multi-seed runner (seeds 42–51).

Runs Phase 10 for 10 seeds and reports mean ± SD care_window_rate.
This is the depleted-init reference baseline required for fair comparison with
Phase 08 and Phase 09 zero-shot rates.

After all seeds complete, update shared/constants.py:
    DEPLETED_BASELINE = <measured mean>

Output: outputs/phase10_depleted_baseline/multi_seed/
"""
import sys
import os
import json
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase7_baldwin_instinct.measure_baseline import (
    run as run_single,
    PHASE_NAME,
    CARE_WINDOW_END,
)

SEEDS        = list(range(42, 52))
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", PHASE_NAME, "multi_seed")
CHECKPOINT   = os.path.join(COMBINED_DIR, "checkpoint.json")


# =============================================================================
# Helpers
# =============================================================================

def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _sd(values):
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (n - 1))


def _load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {"completed": [], "run_dirs": {}, "window_rates": {}}


def _save_checkpoint(cp: dict) -> None:
    os.makedirs(COMBINED_DIR, exist_ok=True)
    with open(CHECKPOINT, "w") as f:
        json.dump(cp, f, indent=2)


def _load_window_rate(run_dir: str) -> float | None:
    path = os.path.join(run_dir, "zeroshot_metrics.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    return data.get("care_window_rate")


# =============================================================================
# Main
# =============================================================================

def run_all(seeds=SEEDS):
    os.makedirs(COMBINED_DIR, exist_ok=True)

    cp           = _load_checkpoint()
    done         = set(cp["completed"])
    run_dirs     = dict(cp["run_dirs"])
    window_rates = dict(cp["window_rates"])

    print(f"Phase 10 multi-seed: {len(seeds)} seeds {seeds}")
    print(f"  Care window end tick : {CARE_WINDOW_END}  (matches PHASE3_ZS_BASELINE window)")
    if done:
        print(f"  [checkpoint] Already done: {sorted(done)}")
    print()

    for seed in seeds:
        if seed in done:
            print(f"  [checkpoint] seed={seed} already done, skipping.")
            continue

        print(f"--- seed={seed} ---")
        run_dir = run_single(seed=seed)
        rate    = _load_window_rate(run_dir)

        run_dirs[str(seed)]     = run_dir
        window_rates[str(seed)] = rate
        cp["completed"].append(seed)
        cp["run_dirs"]      = run_dirs
        cp["window_rates"]  = window_rates
        _save_checkpoint(cp)
        print(f"  [checkpoint] seed={seed} saved. care_window_rate={rate}\n")

    # ── Aggregate ─────────────────────────────────────────────────────────────
    rates = [v for v in window_rates.values() if v is not None]
    mean_rate = _mean(rates)
    sd_rate   = _sd(rates)

    summary = {
        "phase":               PHASE_NAME,
        "seeds":               seeds,
        "n_completed":         len(rates),
        "care_window_end":     CARE_WINDOW_END,
        "mean_window_rate":    round(mean_rate, 6),
        "sd_window_rate":      round(sd_rate, 6),
        "per_seed":            {str(s): window_rates.get(str(s)) for s in seeds},
        "phase3_zs_baseline":  0.09069,
        "note": (
            "DEPLETED_BASELINE = mean_window_rate. "
            "Update shared/constants.py with this value after run completes."
        ),
    }
    summary_path = os.path.join(COMBINED_DIR, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # ── Report ────────────────────────────────────────────────────────────────
    print("\n=== Phase 10 Depleted-Init Baseline — Summary ===")
    print(f"{'Seed':>6}  {'care_window_rate':>18}")
    print("-" * 28)
    for s in seeds:
        r = window_rates.get(str(s))
        print(f"{s:>6}  {r:>18.5f}" if r is not None else f"{s:>6}  {'N/A':>18}")
    print("-" * 28)
    print(f"  Mean  : {mean_rate:.5f}")
    print(f"  SD    : {sd_rate:.5f}")
    print(f"  n     : {len(rates)} / {len(seeds)}")
    print(f"\n  PHASE3_ZS_BASELINE (high-care genomes): 0.09069")
    print(f"\n  → Update shared/constants.py:")
    print(f"      DEPLETED_BASELINE = {mean_rate:.5f}")
    print(f"\nOutput: {COMBINED_DIR}")


if __name__ == "__main__":
    run_all()
