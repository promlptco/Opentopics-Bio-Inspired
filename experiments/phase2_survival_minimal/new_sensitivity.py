"""
experiments/phase2_survival_minimal/sensitivity_sweep.py

One-Variable-at-a-Time (OVAT) Sensitivity Analysis for Phase 2.

Usage:
  python experiments/phase2_survival_minimal/sensitivity_sweep.py
  python experiments/phase2_survival_minimal/sensitivity_sweep.py --duration 1000 --seeds 10 --repeats 3
  python experiments/phase2_survival_minimal/sensitivity_sweep.py --sets ABC
  python experiments/phase2_survival_minimal/sensitivity_sweep.py --tau 0.1 --perceptual_noise 0.1

Outputs:
  outputs/phase2_survival_minimal/sensitivity/<timestamp>/
    ├── sensitivity_map.png
    ├── set_A_init_food.csv
    ├── set_B_eat_gain.csv
    ├── set_C_move_cost.csv
    └── sensitivity_summary.json
"""

import sys
import os
import csv
import json
import argparse
from datetime import datetime

import numpy as np
from concurrent.futures import ProcessPoolExecutor
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase2_survival_minimal.new_run import SurvivalSimulation, make_config
from experiments.phase2_survival_minimal.new_config import (
    INIT_MOTHERS,
    TAIL_WINDOW,
    BALANCED_BASELINE,
    SENSITIVITY_SWEEPS,
    SENSITIVITY_SUBPLOT_CONFIG,
    HIDE_BASELINE_FOR,
)
from utils.experiment import set_seed


def run_one(params, seed, duration, tau=0.1, noise=0.1):
    set_seed(seed)
    cfg = make_config(params, duration)
    sim = SurvivalSimulation(cfg, tau=tau, perceptual_noise=noise)
    return sim.run()


def _run_task(task):
    """Top-level wrapper required for ProcessPoolExecutor pickling."""
    params, seed, duration, tau, noise = task
    return run_one(params, seed, duration, tau=tau, noise=noise)


def pad_series(values, duration):
    arr = np.full(duration, np.nan)
    values = np.asarray(values, dtype=float)
    arr[: min(duration, len(values))] = values[:duration]
    return arr


def summarize_runs(run_results, duration, tail_window=TAIL_WINDOW):
    final_pops = np.asarray([r["final_pop"] for r in run_results], dtype=float)
    mean_energies = np.asarray([r["mean_energy"] for r in run_results], dtype=float)
    final_energies = np.asarray([r["final_energy"] for r in run_results], dtype=float)

    tail_energy_means = []
    tail_pop_means = []

    for r in run_results:
        energy = np.nan_to_num(pad_series(r["energy_history"], duration), nan=0.0)
        pop = np.nan_to_num(pad_series(r["population_history"], duration), nan=0.0)

        tail_energy_means.append(np.mean(energy[-tail_window:]))
        tail_pop_means.append(np.mean(pop[-tail_window:]))

    tail_energy_means = np.asarray(tail_energy_means, dtype=float)
    tail_pop_means = np.asarray(tail_pop_means, dtype=float)

    return {
        "num_runs": int(len(run_results)),
        "survival_rate_mean": float(np.mean(final_pops) / INIT_MOTHERS),
        "survival_rate_sd": float(np.std(final_pops) / INIT_MOTHERS),
        "final_pop_mean": float(np.mean(final_pops)),
        "final_pop_sd": float(np.std(final_pops)),
        "mean_energy_mean": float(np.mean(mean_energies)),
        "mean_energy_sd": float(np.std(mean_energies)),
        "final_energy_mean": float(np.mean(final_energies)),
        "final_energy_sd": float(np.std(final_energies)),
        "tail_energy_mean": float(np.mean(tail_energy_means)),
        "tail_energy_sd": float(np.std(tail_energy_means)),
        "tail_pop_mean": float(np.mean(tail_pop_means)),
        "tail_pop_sd": float(np.std(tail_pop_means)),
    }


def find_food_anchor(
    seeds,
    repeats,
    duration,
    tau,
    noise,
    workers=1,
    target_survival=0.50,
    food_step=15,
    food_max=600,
):
    """Phase A — sweep init_food from near-zero upward; return the first value
    where mean survival rate >= target_survival.

    All non-food parameters are held at the provisional BALANCED_BASELINE.
    This only finds a rough food-density anchor. Final ecologies must still
    come from the multi-parameter validation grid.
    """
    base = {k: v for k, v in BALANCED_BASELINE.items() if k != "init_food"}
    food_range = range(10, food_max + food_step, food_step)

    print(f"\n-- Phase A: Food anchor sweep (target survival >= {target_survival:.0%}) --")

    anchor_food = None
    anchor_summary = None
    best_food = None
    best_survival = -1.0
    best_summary = None

    for food in food_range:
        params = {**base, "init_food": int(food)}
        tasks = [
            (dict(params), seed * 1000 + rep, duration, tau, noise)
            for seed in seeds
            for rep in range(repeats)
        ]

        if workers <= 1:
            run_results = [_run_task(t) for t in tasks]
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                run_results = list(pool.map(_run_task, tasks))

        summary = summarize_runs(run_results, duration)
        survival = summary["survival_rate_mean"]

        print(
            f"  init_food={food:4d}  "
            f"survival={survival:.2f}  tailE={summary['tail_energy_mean']:.3f}"
        )

        if survival > best_survival:
            best_survival = survival
            best_food = int(food)
            best_summary = summary

        if anchor_food is None and survival >= target_survival:
            anchor_food = int(food)
            anchor_summary = summary
            print(f"\n  Anchor found: init_food = {anchor_food} (survival = {survival:.2f})")
            break

    if anchor_food is None:
        anchor_food = best_food if best_food is not None else int(list(food_range)[-1])
        anchor_summary = best_summary
        print(
            f"\n  Warning: no anchor found up to init_food={int(list(food_range)[-1])}. "
            f"Using argmax: init_food = {anchor_food} (survival = {best_survival:.2f})"
        )

    return anchor_food, anchor_summary


def run_set(set_id, sweep, baseline, seeds, repeats, duration, tau, noise, tail_window, workers=1):
    key = sweep["key"]
    results = []

    for val in sweep["values"]:
        params = dict(baseline)
        params[key] = int(val) if key == "init_food" else float(val)

        tasks = [
            (dict(params), seed * 1000 + rep, duration, tau, noise)
            for seed in seeds
            for rep in range(repeats)
        ]

        if workers <= 1:
            run_results = [_run_task(t) for t in tasks]
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                run_results = list(pool.map(_run_task, tasks))

        summary = summarize_runs(run_results, duration, tail_window=tail_window)
        summary["param_value"] = params[key]
        results.append(summary)

        print(
            f"  Set {set_id} [{key}={params[key]}] "
            f"runs={summary['num_runs']:02d} | "
            f"survival={summary['survival_rate_mean']:.2f} +/- {summary['survival_rate_sd']:.2f} | "
            f"tailE={summary['tail_energy_mean']:.3f} +/- {summary['tail_energy_sd']:.3f}"
        )

    return results


def save_csv(results, path):
    if not results:
        return

    fieldnames = [
        "param_value",
        "num_runs",
        "survival_rate_mean",
        "survival_rate_sd",
        "final_pop_mean",
        "final_pop_sd",
        "mean_energy_mean",
        "mean_energy_sd",
        "final_energy_mean",
        "final_energy_sd",
        "tail_energy_mean",
        "tail_energy_sd",
        "tail_pop_mean",
        "tail_pop_sd",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def plot_sensitivity_map(all_results, baseline, out_dir, hide_keys=None):
    n_sets = len(SENSITIVITY_SUBPLOT_CONFIG)  # 3 sets: A, B, C
    n_cols = n_sets
    n_rows = 1

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 5))
    axes_flat = np.asarray(axes).flatten()
    energy_color = "#2E3440"

    fig.suptitle(
        "Phase 2 · OVAT Sensitivity Analysis  |  "
        "MotherAgent: Environmental Cue × Genome Weight → Softmax",
        fontsize=13,
        fontweight="bold",
        y=1.02,
    )

    if hide_keys is None:
        hide_keys = HIDE_BASELINE_FOR

    for idx, (set_id, key, xlabel, color) in enumerate(SENSITIVITY_SUBPLOT_CONFIG):
        ax_surv = axes_flat[idx]
        ax_energy = ax_surv.twinx()

        data = all_results[set_id]
        xs = np.asarray([d["param_value"] for d in data], dtype=float)

        surv = np.asarray([d["survival_rate_mean"] for d in data], dtype=float)
        surv_sd = np.asarray([d["survival_rate_sd"] for d in data], dtype=float)

        energy = np.asarray([d["tail_energy_mean"] for d in data], dtype=float)
        energy_sd = np.asarray([d["tail_energy_sd"] for d in data], dtype=float)

        ax_surv.plot(
            xs,
            surv,
            color=color,
            linewidth=2.0,
            marker="o",
            markersize=4,
            label="Survival rate",
        )
        ax_surv.fill_between(
            xs,
            np.clip(surv - surv_sd, 0.0, 1.0),
            np.clip(surv + surv_sd, 0.0, 1.0),
            color=color,
            alpha=0.12,
            label="Survival mean ± 1 SD",
        )

        ax_surv.set_ylim(-0.05, 1.15)
        ax_surv.set_ylabel("Survival rate", color=color, fontsize=10)
        ax_surv.tick_params(axis="y", labelcolor=color, direction="in")
        ax_surv.tick_params(axis="x", direction="in")

        ax_energy.plot(
            xs,
            energy,
            color=energy_color,
            linewidth=1.8,
            linestyle="--",
            marker="s",
            markersize=3.5,
            label="Tail mean energy",
        )
        ax_energy.fill_between(
            xs,
            np.clip(energy - energy_sd, 0.0, 1.0),
            np.clip(energy + energy_sd, 0.0, 1.0),
            color=energy_color,
            alpha=0.07,
            label="Energy mean ± 1 SD",
        )

        ax_energy.set_ylim(-0.05, 1.15)
        ax_energy.set_ylabel("Tail mean energy", color=energy_color, fontsize=10)
        ax_energy.tick_params(axis="y", labelcolor=energy_color, direction="in")

        ax_surv.set_xlabel(xlabel, fontsize=10)
        ax_surv.set_title(f"Set {set_id}  ·  {key}", fontsize=11, fontweight="bold")
        ax_surv.grid(True, linestyle="--", linewidth=0.5, alpha=0.35)
        ax_surv.spines["top"].set_visible(False)

        lines_surv, labels_surv = ax_surv.get_legend_handles_labels()
        lines_energy, labels_energy = ax_energy.get_legend_handles_labels()

        ax_surv.legend(
            lines_surv + lines_energy,
            labels_surv + labels_energy,
            loc="upper left",
            fontsize=8,
            framealpha=0.92,
            edgecolor="#cccccc",
            fancybox=False,
        )

    # No unused slots (n_sets == n_cols)
    for i in range(n_sets, n_rows * n_cols):
        axes_flat[i].set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "sensitivity_map.png")
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"\nSaved sensitivity map -> {out_path}")


def main():
    parser = argparse.ArgumentParser(description="OVAT Sensitivity Sweep for Phase 2.")
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--seeds", type=int, default=10, help="Number of seeds starting from 42. Phase 2 claims require at least 10 seeds.")
    parser.add_argument("--repeats", type=int, default=3, help="Repeats per seed.")
    parser.add_argument("--sets", type=str, default="".join(SENSITIVITY_SWEEPS.keys()),
                        help="Which sets to run, e.g. A, B, C, or ABC.")
    parser.add_argument("--tau", type=float, default=0.1)
    parser.add_argument("--perceptual_noise", type=float, default=0.1)
    parser.add_argument("--tail_window", type=int, default=TAIL_WINDOW)
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers (0=auto/cpu_count, 1=sequential)")
    parser.add_argument("--anchor_target", type=float, default=0.50,
                        help="Phase A target survival rate for food anchor (default 0.50).")
    parser.add_argument("--anchor_step", type=int, default=15,
                        help="init_food step size for Phase A anchor sweep (default 15).")
    parser.add_argument("--anchor_max", type=int, default=600,
                        help="Upper bound of Phase A anchor sweep (default 600).")
    parser.add_argument("--skip_anchor", action="store_true",
                        help="Skip Phase A and use BALANCED_BASELINE init_food directly.")

    args = parser.parse_args()

    import os as _os
    n_workers = ((_os.cpu_count() or 1) if args.workers == 0 else max(1, args.workers))

    seeds = list(range(42, 42 + args.seeds))
    sets_to_run = [s.upper() for s in args.sets if s.upper() in SENSITIVITY_SWEEPS]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT,
        "outputs",
        "phase2_survival_minimal",
        "sensitivity",
        ts,
    )
    os.makedirs(out_dir, exist_ok=True)

    # ── Phase A: find empirical food anchor ──────────────────────────────────
    if args.skip_anchor:
        anchor_food = BALANCED_BASELINE["init_food"]
        anchor_summary = None
        print(f"\nPhase A skipped -- using BALANCED_BASELINE init_food = {anchor_food}")
    else:
        anchor_food, anchor_summary = find_food_anchor(
            seeds=seeds,
            repeats=args.repeats,
            duration=args.duration,
            tau=args.tau,
            noise=args.perceptual_noise,
            workers=n_workers,
            target_survival=args.anchor_target,
            food_step=args.anchor_step,
            food_max=args.anchor_max,
        )

    # Phase B baseline: non-food params from BALANCED_BASELINE, init_food from Phase A.
    # Set D sweeps init_food itself — it still uses this baseline for all other params,
    # and the anchor_food value is recorded as the reference marker on the plot.
    anchored_baseline = {**BALANCED_BASELINE, "init_food": anchor_food}

    total_values = sum(len(SENSITIVITY_SWEEPS[s]["values"]) for s in sets_to_run)
    total_runs = total_values * len(seeds) * args.repeats

    print("\n" + "=" * 70)
    print("Phase 2 - OVAT Sensitivity Sweep (Phase B)")
    print(f"Duration         : {args.duration} ticks")
    print(f"Seeds            : {seeds}")
    print(f"Repeats per seed : {args.repeats}")
    print(f"Runs per value   : {len(seeds) * args.repeats}")
    print(f"Total values     : {total_values}")
    print(f"Total runs       : {total_runs}")
    print(f"Sets             : {sets_to_run}")
    print(f"Tau              : {args.tau}")
    print(f"Perceptual noise : {args.perceptual_noise}")
    print(f"Tail window      : {args.tail_window}")
    print(f"Workers          : {n_workers}")
    print(f"Anchored baseline: {anchored_baseline}")
    print(f"Output           : {out_dir}")
    print("=" * 70)

    all_results = {}

    for set_id in sets_to_run:
        sweep = SENSITIVITY_SWEEPS[set_id]
        key = sweep["key"]

        print(f"\n-- Set {set_id}: Sweeping '{key}' --")
        print(f"   Values: {sweep['values']}")

        results = run_set(
            set_id=set_id,
            sweep=sweep,
            baseline=anchored_baseline,
            seeds=seeds,
            repeats=args.repeats,
            duration=args.duration,
            tau=args.tau,
            noise=args.perceptual_noise,
            tail_window=args.tail_window,
            workers=n_workers,
        )

        all_results[set_id] = results

        csv_path = os.path.join(out_dir, f"set_{set_id}_{key}.csv")
        save_csv(results, csv_path)
        print(f"   Saved CSV -> {csv_path}")

    expected_sets = list(SENSITIVITY_SWEEPS.keys())
    if all(s in all_results for s in expected_sets):
        plot_sensitivity_map(all_results, anchored_baseline, out_dir)
    else:
        missing = [s for s in expected_sets if s not in all_results]
        print(f"\nSkipping full sensitivity map -- missing sets: {missing}")

    summary_path = os.path.join(out_dir, "sensitivity_summary.json")
    with open(summary_path, "w") as f:
        json.dump(
            {
                "anchor_food": anchor_food,
                "anchored_baseline": anchored_baseline,
                "balanced_baseline_original": BALANCED_BASELINE,
                "duration": args.duration,
                "seeds": seeds,
                "repeats": args.repeats,
                "tau": args.tau,
                "perceptual_noise": args.perceptual_noise,
                "tail_window": args.tail_window,
                "total_values": total_values,
                "total_runs": total_runs,
                "results": all_results,
            },
            f,
            indent=2,
        )

    print(f"Saved summary JSON -> {summary_path}")

    # Do not auto-overwrite the validation grid. Final HARSH/BALANCED/EASY
    # ecologies must be selected from the multi-parameter validation grid in run.py.

    print("\nDone.")


if __name__ == "__main__":
    main()