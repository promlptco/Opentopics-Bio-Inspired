# experiments/phase3_erosion/run_multi_seed.py
"""
Run evolution stage across N seeds and produce:
  - Per-seed generation_snapshots + full outputs
  - Multi-seed mean care_weight ± 95% CI plot
  - Summary table: final care_weight, forage_weight, max_generation per seed
"""
import sys
import os
import json
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase3_erosion.run import run
from utils.plotting import plot_start_vs_end_multiseed

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

SEEDS = list(range(42, 52))   # seeds 42–51  (10 runs)
STAGE = "evolution"


def _load_snapshots(run_dir: str) -> list[dict]:
    path = os.path.join(run_dir, "generation_snapshots.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _ci95(values: list[float]) -> float:
    """95% CI half-width assuming normal distribution."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    se = math.sqrt(variance / n)
    return 1.96 * se


def plot_multi_seed_ci(all_snapshots: list[list[dict]], seeds: list[int], output_dir: str) -> None:
    """
    Mean care_weight ± 95% CI across seeds.
    X-axis: tick. Shading = CI. Individual seed lines shown faint.
    Also plots forage_weight mean to rule out hitchhiking.
    """
    if plt is None or not all_snapshots:
        return

    os.makedirs(output_dir, exist_ok=True)

    # Align on ticks present in ALL seeds
    tick_sets = [set(s["tick"] for s in snaps) for snaps in all_snapshots]
    common_ticks = sorted(set.intersection(*tick_sets))
    if not common_ticks:
        print("No common ticks across seeds — skipping CI plot.")
        return

    def get_series(snaps: list[dict], key: str) -> dict[int, float]:
        return {s["tick"]: s.get(key, 0.0) for s in snaps}

    care_by_seed  = [get_series(s, "avg_care_weight")   for s in all_snapshots]
    forage_by_seed = [get_series(s, "avg_forage_weight") for s in all_snapshots]

    care_mean, care_ci = [], []
    forage_mean = []

    for t in common_ticks:
        c_vals = [d[t] for d in care_by_seed]
        f_vals = [d[t] for d in forage_by_seed]
        care_mean.append(sum(c_vals) / len(c_vals))
        care_ci.append(_ci95(c_vals))
        forage_mean.append(sum(f_vals) / len(f_vals))

    care_lo = [m - ci for m, ci in zip(care_mean, care_ci)]
    care_hi = [m + ci for m, ci in zip(care_mean, care_ci)]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    # Individual seed traces (faint)
    for i, snaps in enumerate(all_snapshots):
        ticks_i = [s["tick"] for s in snaps if s["tick"] in set(common_ticks)]
        care_i  = [get_series(snaps, "avg_care_weight")[t] for t in ticks_i]
        ax1.plot(ticks_i, care_i, color="steelblue", alpha=0.15, linewidth=1)

    # Mean + CI
    ax1.plot(common_ticks, care_mean, color="steelblue", linewidth=2.5, label=f"mean care_weight (n={len(seeds)})")
    ax1.fill_between(common_ticks, care_lo, care_hi, alpha=0.3, color="steelblue", label="95% CI")
    ax1.set_ylabel("care_weight")
    ax1.set_title(f"care_weight Evolution — {len(seeds)} seeds (selection vs drift)")
    ax1.set_ylim(0, 1)
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # Forage mean
    ax2.plot(common_ticks, forage_mean, color="darkorange", linewidth=2.5, label="mean forage_weight")
    ax2.set_xlabel("Tick")
    ax2.set_ylabel("forage_weight")
    ax2.set_ylim(0, 1)
    ax2.set_title("forage_weight Evolution (hitchhiking check)")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "multi_seed_care_weight_ci.png")
    plt.savefig(path)
    plt.close()
    print(f"Saved: {path}")


def run_all(seeds: list[int] = SEEDS, stage: str = STAGE) -> None:
    run_dirs = []
    all_snapshots = []
    summaries = []

    print(f"Running {len(seeds)} seeds: {seeds}\n")

    for seed in seeds:
        print(f"--- seed={seed} ---")
        out_dir = run(seed=seed, stage=stage)
        run_dirs.append(out_dir)

        snaps = _load_snapshots(out_dir)
        all_snapshots.append(snaps)

        # Per-seed final summary
        top_path = os.path.join(out_dir, "top_genomes.json")
        if os.path.exists(top_path):
            with open(top_path) as f:
                genomes = json.load(f)
            care_vals   = [g["care_weight"]   for g in genomes]
            forage_vals = [g["forage_weight"]  for g in genomes]
            gen_vals    = [g.get("generation", 0) for g in genomes]
            summaries.append({
                "seed":              seed,
                "n_survivors":       len(genomes),
                "final_care_mean":   sum(care_vals)   / len(care_vals)   if care_vals   else 0,
                "final_forage_mean": sum(forage_vals)  / len(forage_vals) if forage_vals else 0,
                "max_generation":    max(gen_vals)     if gen_vals else 0,
            })
        print()

    # Combined output dir (next to individual runs)
    combined_dir = os.path.join(
        PROJECT_ROOT, "outputs", "phase3_erosion", "multi_seed_evolution"
    )
    os.makedirs(combined_dir, exist_ok=True)

    # Save run_dirs manifest
    with open(os.path.join(combined_dir, "run_dirs.json"), "w") as f:
        json.dump({"seeds": seeds, "run_dirs": run_dirs}, f, indent=2)

    # Save summary table
    with open(os.path.join(combined_dir, "summary.json"), "w") as f:
        json.dump(summaries, f, indent=2)

    # CI plot + start vs end barchart
    plot_multi_seed_ci(all_snapshots, seeds, combined_dir)
    plot_start_vs_end_multiseed(summaries, combined_dir)

    # Print summary table
    print("\n=== Multi-Seed Summary ===")
    print(f"{'Seed':>5}  {'Survivors':>9}  {'care_w':>8}  {'forage_w':>9}  {'max_gen':>7}")
    print("-" * 47)
    for s in summaries:
        print(f"{s['seed']:>5}  {s['n_survivors']:>9}  "
              f"{s['final_care_mean']:>8.3f}  {s['final_forage_mean']:>9.3f}  "
              f"{s['max_generation']:>7}")

    care_finals = [s["final_care_mean"] for s in summaries]
    overall_mean = sum(care_finals) / len(care_finals)
    overall_ci   = _ci95(care_finals)
    print("-" * 47)
    print(f"Mean care_weight across seeds: {overall_mean:.3f} +/- {overall_ci:.3f} (95% CI)")
    print(f"Combined output: {combined_dir}")


if __name__ == "__main__":
    run_all()
