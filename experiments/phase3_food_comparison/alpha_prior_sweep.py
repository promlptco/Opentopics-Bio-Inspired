"""Phase 3 alpha × prior sweep (mothers + children, care enabled).

Mirrors phase2_food_comparison/alpha_prior_sweep.py but with Phase 3 mechanics:
care motivation, children, infant starvation, FORAGE/SELF/CARE softmax.

Key question: does the Shannon spatial effect (alpha) help CMR independently of
food quantity (prior), or was the CMR gain in the alpha sweep just a food-density effect?

Design: init_food = int(prior × W × H) so initial density == equilibrium target.
        prior spans below / at / above the Shannon entropy maximum (1/e ≈ 0.37).

Metrics (Phase 3, mothers + children):
  cmr            — child maturation rate  (main Phase 3 outcome)
  care_pct       — fraction of ticks mother chose CARE
  mean_final_pop — mean surviving mothers at max_ticks
  joint          — cmr × clamp(mean_final_pop / init_mothers, 0, 1)
                   combined fitness: children AND mothers survive

Output:
  outputs/phase3_alpha_prior_sweep/exp_<ts>/
    summary.csv
    heatmap_cmr.png
    heatmap_care_pct.png
    heatmap_mean_final_pop.png
    heatmap_joint.png

Usage:
  python -m experiments.phase3_food_comparison.alpha_prior_sweep
  python -m experiments.phase3_food_comparison.alpha_prior_sweep --seeds 10 --ticks 2000 --workers 4
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

# Alpha rescaled for fixed-p=0.5 formula: rate = alpha*log(2) per empty cell per tick.
# At 2500 cells and ~5-10 picks/tick, equilibrium food density ≈ init_food when alpha≈0.003-0.010.
ALPHA_VALUES: list[float] = [0.000, 0.003, 0.005, 0.010, 0.020]
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
    "infant_starvation_multiplier": 1.0,
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
    cfg.food_entropy_beta = 0.01
    cfg.food_entropy_gamma = 0.01

    # Phase 3 care mechanics (unbiased weights)
    cfg.care_weight = 1.0
    cfg.forage_weight = 1.0
    cfg.self_weight = 1.0
    cfg.children_enabled = True
    cfg.care_enabled = True
    cfg.reproduction_enabled = False
    cfg.mutation_enabled = False
    cfg.plasticity_enabled = False
    cfg.allow_allomothering = False

    cfg.infant_starvation_multiplier = float(eco.get("infant_starvation_multiplier", 1.0))
    cfg.maturity_age = 80
    cfg.starvation_threshold = 1.0
    cfg.mother_max_age = 400
    cfg.reproduction_threshold = 0.85
    cfg.reproduction_cost = 0.20
    cfg.reproduction_cooldown = 120

    cfg.softmax_tau = 0.1
    cfg.cry_decay_radius = 8.0  # Phase3+: distance-attenuated cry (= perception_radius)
    cfg.temperature_sensitivity = 0.0
    cfg.warmth_factor = 0.0
    cfg.warmth_radius = 3
    cfg.temperature_period = 200
    cfg.birth_scatter_radius = 2
    cfg.mutation_rate = 0.5
    cfg.mutation_sigma = 0.02
    cfg.min_mutation_rate = 0.01
    cfg.plastic_gain = 0.1
    cfg.plasticity_metabolic_alpha = 0.01
    cfg.plasticity_maintenance_beta = 0.001
    cfg.plasticity_kin_conditional = True
    cfg.init_learning_rate = 1.0
    cfg.init_plasticity_coefficient = 1.0
    cfg.phenotype_retention = 0.15
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

    from experiments.phase3_food_comparison.alpha_prior_sweep import make_config
    from experiments.phase3_survival_full.run import Phase3Simulation

    cfg = make_config(alpha, prior, eco, max_ticks)
    cfg.seed = seed  # Simulation re-seeds from cfg.seed in initialize()
    sim = Phase3Simulation(cfg)
    result = sim.run()
    result["alpha"] = alpha
    result["prior"] = prior
    result["seed"] = seed
    return result


def _aggregate(results: list[dict], init_mothers: int = 15) -> dict:
    cmrs = [r.get("child_maturation_rate", 0.0) for r in results]
    care_pcts = [r.get("care_pct", 0.0) for r in results]
    finals = [r.get("final_pop", 0) for r in results]
    mother_surv = [min(1.0, f / max(1, init_mothers)) for f in finals]
    joints = [c * m for c, m in zip(cmrs, mother_surv)]
    return {
        "cmr": float(np.mean(cmrs)),
        "care_pct": float(np.mean(care_pcts)),
        "mean_final_pop": float(np.mean(finals)),
        "joint": float(np.mean(joints)),
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
        f"{p:.2f}\n(food≈{int(p*2500)})" for p in prior_vals
    ])
    ax.set_xlabel("Shannon alpha  (0 = uniform/burst)", fontsize=11)
    ax.set_ylabel("Patch prior  (food density target)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")

    # highlight balanced food density row (prior=0.37 ≈ init_food=925)
    balanced_idx = min(range(len(prior_vals)),
                       key=lambda i: abs(prior_vals[i] - 0.37))
    for col in range(len(alpha_vals)):
        ax.add_patch(plt.Rectangle(
            (col - 0.5, balanced_idx - 0.5), 1, 1,
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
    ax.text(0.98, 0.02, "red dashed = balanced density (prior≈0.37, init_food≈925)",
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
        PROJECT_ROOT / "outputs" / "phase3_alpha_prior_sweep" / f"exp_{ts}"
    )
    out.mkdir(parents=True, exist_ok=True)

    n_cond = len(ALPHA_VALUES) * len(PRIOR_VALUES)
    seed_list = list(range(42, 42 + seeds))

    print("[phase3_alpha_prior_sweep]")
    print("  alpha values: %s" % ALPHA_VALUES)
    print("  prior values: %s  (entropy_max=1/e~0.37)" % PRIOR_VALUES)
    print("  conditions: %d x %d = %d" % (len(ALPHA_VALUES), len(PRIOR_VALUES), n_cond))
    print("  seeds=%d  ticks=%d  workers=%d" % (seeds, max_ticks, workers))
    print("  output: %s" % out)

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
    print("  %6s  %6s  %8s  %6s  %8s  %8s  %8s" % (
        "alpha", "prior", "food_eq", "cmr", "care%", "pop", "joint"))
    for a in ALPHA_VALUES:
        for p in PRIOR_VALUES:
            agg = _aggregate(results_by_cond[(a, p)])
            grid[(a, p, "cmr")] = agg["cmr"]
            grid[(a, p, "care_pct")] = agg["care_pct"]
            grid[(a, p, "mean_final_pop")] = agg["mean_final_pop"]
            grid[(a, p, "joint")] = agg["joint"]
            food_eq = int(p * 2500)
            csv_rows.append({
                "alpha": a, "prior": p, "food_equiv": food_eq,
                **agg,
            })
            print("  %6.2f  %6.2f  %8d  %6.3f  %7.3f  %8.1f  %8.3f" % (
                a, p, food_eq,
                agg["cmr"], agg["care_pct"],
                agg["mean_final_pop"], agg["joint"]))

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
        "cmr",
        "Phase 3 — Child Maturation Rate (CMR)\n(mothers+children, unbiased weights, n=%d seeds)" % seeds,
        "CMR (fraction of children reaching maturity)", out, cmap="viridis", fmt=".2f",
    )
    plot_heatmap(
        grid, ALPHA_VALUES, PRIOR_VALUES,
        "care_pct",
        "Phase 3 — CARE Motivation Fraction\n(fraction of ticks mother chose CARE, n=%d seeds)" % seeds,
        "care_pct", out, cmap="Blues", fmt=".2f",
    )
    plot_heatmap(
        grid, ALPHA_VALUES, PRIOR_VALUES,
        "mean_final_pop",
        "Phase 3 — Mean Final Mother Population\n(n=%d seeds)" % seeds,
        "Mean surviving mothers at max_ticks", out, cmap="plasma", fmt=".1f",
    )
    plot_heatmap(
        grid, ALPHA_VALUES, PRIOR_VALUES,
        "joint",
        "Phase 3 — Joint Fitness (CMR × mother_survival)\n(n=%d seeds)" % seeds,
        "Joint fitness (0–1)", out, cmap="RdYlGn", fmt=".2f",
    )

    print("\n[ok] Phase 3 alpha x prior sweep complete -- %s" % out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 alpha × prior sweep")
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
