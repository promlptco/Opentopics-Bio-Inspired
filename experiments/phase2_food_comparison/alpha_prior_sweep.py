"""Phase 2 alpha × prior sweep (mothers only, no care).

Previous experiments swept alpha with prior locked at init_food/(W×H) = 0.12,
confounding total food availability with Shannon spatial structure.

This sweep independently varies:
  alpha — Shannon patchiness strength (0 = uniform burst; >0 = entropy spawning)
  prior — patch equilibrium probability, sets food density target
           prior < 1/e ≈ 0.37 → depletion disperses food (eating → less spawn)
           prior > 1/e       → eating moves p toward entropy max → convergence

Design: init_food = int(prior × W × H) so initial density matches equilibrium.

Metrics (Phase 2, mothers only):
  mean_final_pop  — mean survivors at max_ticks across seeds
  mean_energy     — mean energy of alive mothers at end
  survival_rate   — fraction of seeds with at least 1 survivor

Output:
  outputs/phase2_alpha_prior_sweep/exp_<ts>/
    summary.csv
    heatmap_mean_final_pop.png
    heatmap_mean_energy.png
    heatmap_survival_rate.png

Usage:
  python -m experiments.phase2_food_comparison.alpha_prior_sweep
  python -m experiments.phase2_food_comparison.alpha_prior_sweep --seeds 10 --ticks 2000 --workers 4
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config

# Shannon entropy maximum at p = 1/e ≈ 0.368
ALPHA_VALUES: list[float] = [0.00, 0.05, 0.10, 0.20, 0.50]
PRIOR_VALUES: list[float] = [0.12, 0.24, 0.37, 0.50, 0.75]

_ECOLOGY_PATH = (
    PROJECT_ROOT
    / "outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json"
)
_FALLBACK: dict = {
    "eat_gain": 0.70,
    "move_cost": 0.005,
    "rest_recovery": 0.005,
    "perception_radius": 8,
    "food_perception_radius": 8,
}


def load_ecology() -> dict:
    if _ECOLOGY_PATH.exists():
        try:
            data = json.loads(_ECOLOGY_PATH.read_text())
            return data.get("BEST_CALIBRATED", data)
        except Exception as exc:
            print("Warning: %s" % exc)
    return _FALLBACK.copy()


def make_config(alpha: float, prior: float, eco: dict, max_ticks: int) -> Config:
    cfg = Config()
    cfg.width = 50
    cfg.height = 50
    cfg.init_mothers = 15
    cfg.initial_energy = 1.0
    cfg.max_ticks = max_ticks

    # prior drives both initial food density AND Shannon equilibrium target
    cfg.init_food = max(1, int(prior * cfg.width * cfg.height))
    cfg.food_patch_prior = prior

    cfg.eat_gain = eco.get("eat_gain", 0.70)
    cfg.move_cost = eco.get("move_cost", 0.005)
    cfg.rest_recovery = eco.get("rest_recovery", 0.005)
    cfg.perception_radius = int(eco.get("perception_radius", 8))
    cfg.food_perception_radius = int(eco.get("food_perception_radius", 8))
    cfg.hunger_rate = 1.0 / 35.0
    cfg.fatigue_rate = 0.01
    cfg.feed_cost = 0.01

    cfg.food_entropy_alpha = alpha
    cfg.food_entropy_beta = 0.01   # depletion per eat event
    cfg.food_entropy_gamma = 0.01  # recovery rate toward prior per tick

    cfg.care_weight = 0.0
    cfg.forage_weight = 1.0
    cfg.self_weight = 1.0
    cfg.children_enabled = False
    cfg.care_enabled = False
    cfg.reproduction_enabled = False
    cfg.mutation_enabled = False
    cfg.plasticity_enabled = False
    return cfg


def _worker(args: tuple) -> dict:
    alpha, prior, seed, max_ticks, eco = args
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
    import random as _random
    import numpy as _np
    _random.seed(seed)
    _np.random.seed(seed)

    from experiments.phase2_food_comparison.alpha_prior_sweep import make_config
    from experiments.phase2_survival_minimal.new_run import SurvivalSimulation

    cfg = make_config(alpha, prior, eco, max_ticks)
    sim = SurvivalSimulation(cfg)
    result = sim.run()
    result["alpha"] = alpha
    result["prior"] = prior
    result["seed"] = seed
    return result


def _aggregate(results: list[dict]) -> dict:
    finals = [r.get("final_pop", 0) for r in results]
    energies = [r.get("mean_energy", 0.0) for r in results]
    return {
        "mean_final_pop": float(np.mean(finals)),
        "mean_energy": float(np.mean(energies)),
        "survival_rate": float(np.mean([1.0 if f > 0 else 0.0 for f in finals])),
        "n": len(results),
    }


def plot_heatmap(
    grid: dict,
    alpha_vals: list[float],
    prior_vals: list[float],
    metric_key: str,
    title: str,
    cbar_label: str,
    out: Path,
    cmap: str = "viridis",
    fmt: str = ".2f",
) -> None:
    data = np.array([
        [grid.get((a, p, metric_key), np.nan) for a in alpha_vals]
        for p in prior_vals
    ])

    fig, ax = plt.subplots(figsize=(9, 5))
    vmin, vmax = np.nanmin(data), np.nanmax(data)
    im = ax.imshow(data, aspect="auto", cmap=cmap, origin="lower",
                   vmin=vmin, vmax=vmax)

    ax.set_xticks(range(len(alpha_vals)))
    ax.set_xticklabels([f"{a:.2f}" for a in alpha_vals])
    ax.set_yticks(range(len(prior_vals)))
    ax.set_yticklabels([
        f"{p:.2f}\n(food~{int(p*2500)})" for p in prior_vals
    ])
    ax.set_xlabel("Shannon alpha  (0 = uniform/burst)", fontsize=11)
    ax.set_ylabel("Patch prior  (food density target)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")

    # vertical line at entropy maximum alpha is not a prior axis thing, but
    # mark the entropy-maximum prior row with a dashed border
    entropy_max_idx = min(range(len(prior_vals)),
                          key=lambda i: abs(prior_vals[i] - 1.0 / np.e))
    for col in range(len(alpha_vals)):
        ax.add_patch(plt.Rectangle(
            (col - 0.5, entropy_max_idx - 0.5), 1, 1,
            fill=False, edgecolor="red", linewidth=1.5, linestyle="--"
        ))

    span = (vmax - vmin) if vmax > vmin else 1.0
    for i, p in enumerate(prior_vals):
        for j, a in enumerate(alpha_vals):
            val = grid.get((a, p, metric_key), np.nan)
            if not np.isnan(val):
                brightness = (val - vmin) / span
                color = "white" if brightness < 0.55 else "black"
                ax.text(j, i, format(val, fmt),
                        ha="center", va="center", fontsize=8,
                        color=color, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(cbar_label, fontsize=10)
    ax.text(0.98, 0.02, "red dashed = entropy max (prior≈0.37)",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7, color="red", style="italic")

    plt.tight_layout()
    fname = out / f"heatmap_{metric_key}.png"
    fig.savefig(str(fname), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved -> %s" % fname)


def run(
    seeds: int = 5,
    max_ticks: int = 2000,
    workers: int = 1,
    output_dir: Path | None = None,
) -> Path:
    eco = load_ecology()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = output_dir or (
        PROJECT_ROOT / "outputs" / "phase2_alpha_prior_sweep" / f"exp_{ts}"
    )
    out.mkdir(parents=True, exist_ok=True)

    n_cond = len(ALPHA_VALUES) * len(PRIOR_VALUES)
    seed_list = list(range(42, 42 + seeds))

    print("[phase2_alpha_prior_sweep]")
    print("  alpha values: %s" % ALPHA_VALUES)
    print("  prior values: %s  (entropy_max=1/e~0.37)" % PRIOR_VALUES)
    print("  conditions: %d x %d = %d" % (len(ALPHA_VALUES), len(PRIOR_VALUES), n_cond))
    print("  seeds=%d  ticks=%d  workers=%d" % (seeds, max_ticks, workers))
    print("  output: %s" % out)

    seed_list = list(range(42, 42 + seeds))
    jobs = [
        (alpha, prior, seed, max_ticks, eco)
        for alpha in ALPHA_VALUES
        for prior in PRIOR_VALUES
        for seed in seed_list
    ]

    results_by_cond: dict[tuple, list] = {
        (a, p): [] for a in ALPHA_VALUES for p in PRIOR_VALUES
    }

    if workers <= 1:
        for job in jobs:
            r = _worker(job)
            results_by_cond[(r["alpha"], r["prior"])].append(r)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_worker, job): job for job in jobs}
            for future in as_completed(futures):
                try:
                    r = future.result()
                    results_by_cond[(r["alpha"], r["prior"])].append(r)
                except Exception as exc:
                    job = futures[future]
                    print("  [FAIL] alpha=%.2f prior=%.2f seed=%d: %s" % (
                        job[0], job[1], job[2], exc))

    # Aggregate
    grid: dict = {}
    csv_rows: list[dict] = []

    print("\n  Results (mean across %d seeds):" % seeds)
    print("  %6s  %6s  %8s  %8s  %6s  %8s" % (
        "alpha", "prior", "food_eq", "final_pop", "energy", "survive%"))
    for a in ALPHA_VALUES:
        for p in PRIOR_VALUES:
            agg = _aggregate(results_by_cond[(a, p)])
            grid[(a, p, "mean_final_pop")] = agg["mean_final_pop"]
            grid[(a, p, "mean_energy")] = agg["mean_energy"]
            grid[(a, p, "survival_rate")] = agg["survival_rate"]
            food_eq = int(p * 2500)
            csv_rows.append({
                "alpha": a, "prior": p, "food_equiv": food_eq,
                **agg,
            })
            print("  %6.2f  %6.2f  %8d  %8.1f  %6.3f  %7.0f%%" % (
                a, p, food_eq,
                agg["mean_final_pop"], agg["mean_energy"],
                agg["survival_rate"] * 100))

    # CSV
    csv_path = out / "summary.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    print("\nSummary -> %s" % csv_path)

    # Heatmaps
    plot_heatmap(
        grid, ALPHA_VALUES, PRIOR_VALUES,
        "mean_final_pop",
        "Phase 2 — Mean Final Population\n(mothers only, no care, n=%d seeds)" % seeds,
        "Mean survivors at max_ticks", out, cmap="viridis", fmt=".1f",
    )
    plot_heatmap(
        grid, ALPHA_VALUES, PRIOR_VALUES,
        "mean_energy",
        "Phase 2 — Mean Energy at End\n(mothers only, no care, n=%d seeds)" % seeds,
        "Mean energy of alive mothers", out, cmap="plasma", fmt=".3f",
    )
    plot_heatmap(
        grid, ALPHA_VALUES, PRIOR_VALUES,
        "survival_rate",
        "Phase 2 — Survival Rate\n(fraction of seeds with ≥1 survivor, n=%d seeds)" % seeds,
        "Survival rate (0–1)", out, cmap="RdYlGn", fmt=".2f",
    )

    print("\n[ok] Phase 2 alpha x prior sweep complete -- %s" % out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 alpha × prior sweep")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--ticks", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()
    run(
        seeds=args.seeds,
        max_ticks=args.ticks,
        workers=max(1, args.workers),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )


if __name__ == "__main__":
    main()
