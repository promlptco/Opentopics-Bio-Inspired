"""
experiments/phase3_survival_full/sensitivity_sweep.py

One-Variable-at-a-Time (OVAT) Sensitivity Analysis for Phase 3.

Phase 3 adds one child per mother and evaluates whether the Phase 2-style
ecological baseline still supports mother-child survival.

Usage:
  # Recommended first run: sweep only resource availability
  python experiments/phase3_survival_full/sensitivity_sweep.py --sets A

  # Run selected sweep sets
  python experiments/phase3_survival_full/sensitivity_sweep.py --sets AB
  python experiments/phase3_survival_full/sensitivity_sweep.py --sets ABCD

  # Run with custom duration, seeds, and repeats
  python experiments/phase3_survival_full/sensitivity_sweep.py --duration 1000 --seeds 5 --repeats 3

  # Run with custom decision/perception noise
  python experiments/phase3_survival_full/sensitivity_sweep.py --tau 0.1 --perceptual_noise 0.1

Outputs:
  outputs/phase3_survival_full/sensitivity/<timestamp>/
    ├── phase3_sensitivity_map.png
    ├── set_A_init_food.csv
    ├── set_B_child_hunger_rate.csv
    ├── set_C_feed_amount.csv
    ├── set_D_feed_cost.csv
    └── phase3_sensitivity_summary.json
"""

import sys
import os
import csv
import json
import argparse
from datetime import datetime

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase3_survival_full.run import MotherChildSurvivalSimulation, make_config
from experiments.phase3_survival_full.config import (
    INIT_MOTHERS,
    TAIL_WINDOW,
    PHASE3_BASELINE,
    PHASE3_SENSITIVITY_SWEEPS,
    PHASE3_SENSITIVITY_SUBPLOT_CONFIG,
    HIDE_BASELINE_FOR,
)
from utils.experiment import set_seed


# ============================================================
# Core run utilities
# ============================================================

def run_one(params, seed, duration, tau=0.1, noise=0.1):
    set_seed(seed)
    cfg = make_config(params, duration)
    sim = MotherChildSurvivalSimulation(cfg, tau=tau, perceptual_noise=noise)
    return sim.run()


def pad_series(values, duration):
    arr = np.full(duration, np.nan)
    values = np.asarray(values, dtype=float)
    arr[: min(duration, len(values))] = values[:duration]
    return arr


def summarize_runs(run_results, duration, tail_window=TAIL_WINDOW):
    final_mothers = np.asarray([r["final_mothers"] for r in run_results], dtype=float)
    final_children = np.asarray([r["final_children"] for r in run_results], dtype=float)

    mean_mother_energy = np.asarray([r["mean_mother_energy"] for r in run_results], dtype=float)
    final_mother_energy = np.asarray([r["final_mother_energy"] for r in run_results], dtype=float)

    mean_child_hunger = np.asarray([r["mean_child_hunger"] for r in run_results], dtype=float)
    final_child_hunger = np.asarray([r["final_child_hunger"] for r in run_results], dtype=float)

    mean_child_distress = np.asarray([r["mean_child_distress"] for r in run_results], dtype=float)
    final_child_distress = np.asarray([r["final_child_distress"] for r in run_results], dtype=float)

    tail_mother_energy = []
    tail_child_hunger = []
    tail_child_distress = []
    tail_child_pop = []
    tail_distance = []

    for r in run_results:
        mother_energy = np.nan_to_num(pad_series(r["mother_energy_history"], duration), nan=0.0)
        child_hunger = np.nan_to_num(pad_series(r["child_hunger_history"], duration), nan=0.0)
        child_distress = np.nan_to_num(pad_series(r["child_distress_history"], duration), nan=0.0)
        child_pop = np.nan_to_num(pad_series(r["child_population_history"], duration), nan=0.0)
        distance = np.nan_to_num(pad_series(r["mother_child_distance_history"], duration), nan=0.0)

        tail_mother_energy.append(np.mean(mother_energy[-tail_window:]))
        tail_child_hunger.append(np.mean(child_hunger[-tail_window:]))
        tail_child_distress.append(np.mean(child_distress[-tail_window:]))
        tail_child_pop.append(np.mean(child_pop[-tail_window:]))
        tail_distance.append(np.mean(distance[-tail_window:]))

    tail_mother_energy = np.asarray(tail_mother_energy, dtype=float)
    tail_child_hunger = np.asarray(tail_child_hunger, dtype=float)
    tail_child_distress = np.asarray(tail_child_distress, dtype=float)
    tail_child_pop = np.asarray(tail_child_pop, dtype=float)
    tail_distance = np.asarray(tail_distance, dtype=float)

    return {
        "num_runs": int(len(run_results)),

        "mother_survival_rate_mean": float(np.mean(final_mothers) / INIT_MOTHERS),
        "mother_survival_rate_sd": float(np.std(final_mothers) / INIT_MOTHERS),
        "child_survival_rate_mean": float(np.mean(final_children) / INIT_MOTHERS),
        "child_survival_rate_sd": float(np.std(final_children) / INIT_MOTHERS),

        "final_mothers_mean": float(np.mean(final_mothers)),
        "final_mothers_sd": float(np.std(final_mothers)),
        "final_children_mean": float(np.mean(final_children)),
        "final_children_sd": float(np.std(final_children)),

        "mean_mother_energy_mean": float(np.mean(mean_mother_energy)),
        "mean_mother_energy_sd": float(np.std(mean_mother_energy)),
        "final_mother_energy_mean": float(np.mean(final_mother_energy)),
        "final_mother_energy_sd": float(np.std(final_mother_energy)),

        "mean_child_hunger_mean": float(np.mean(mean_child_hunger)),
        "mean_child_hunger_sd": float(np.std(mean_child_hunger)),
        "final_child_hunger_mean": float(np.mean(final_child_hunger)),
        "final_child_hunger_sd": float(np.std(final_child_hunger)),

        "mean_child_distress_mean": float(np.mean(mean_child_distress)),
        "mean_child_distress_sd": float(np.std(mean_child_distress)),
        "final_child_distress_mean": float(np.mean(final_child_distress)),
        "final_child_distress_sd": float(np.std(final_child_distress)),

        "tail_mother_energy_mean": float(np.mean(tail_mother_energy)),
        "tail_mother_energy_sd": float(np.std(tail_mother_energy)),
        "tail_child_hunger_mean": float(np.mean(tail_child_hunger)),
        "tail_child_hunger_sd": float(np.std(tail_child_hunger)),
        "tail_child_distress_mean": float(np.mean(tail_child_distress)),
        "tail_child_distress_sd": float(np.std(tail_child_distress)),
        "tail_child_pop_mean": float(np.mean(tail_child_pop)),
        "tail_child_pop_sd": float(np.std(tail_child_pop)),
        "tail_mother_child_distance_mean": float(np.mean(tail_distance)),
        "tail_mother_child_distance_sd": float(np.std(tail_distance)),
    }


# ============================================================
# Sweep execution
# ============================================================

def run_set(set_id, sweep, baseline, seeds, repeats, duration, tau, noise, tail_window):
    key = sweep["key"]
    results = []

    for val in sweep["values"]:
        params = dict(baseline)

        if key in {"init_food", "feed_distance", "food_respawn_per_tick"}:
            params[key] = int(val)
        else:
            params[key] = float(val)

        run_results = []

        for seed in seeds:
            for rep in range(repeats):
                run_seed = seed * 1000 + rep
                result = run_one(params, run_seed, duration, tau=tau, noise=noise)
                run_results.append(result)

        summary = summarize_runs(run_results, duration, tail_window=tail_window)
        summary["param_value"] = params[key]
        results.append(summary)

        print(
            f"  Set {set_id} [{key}={params[key]}] "
            f"runs={summary['num_runs']:02d} | "
            f"mother_surv={summary['mother_survival_rate_mean']:.2f} ± "
            f"{summary['mother_survival_rate_sd']:.2f} | "
            f"child_surv={summary['child_survival_rate_mean']:.2f} ± "
            f"{summary['child_survival_rate_sd']:.2f} | "
            f"tailE={summary['tail_mother_energy_mean']:.3f} | "
            f"childH={summary['tail_child_hunger_mean']:.3f}"
        )

    return results


def save_csv(results, path):
    if not results:
        return

    fieldnames = [
        "param_value",
        "num_runs",

        "mother_survival_rate_mean",
        "mother_survival_rate_sd",
        "child_survival_rate_mean",
        "child_survival_rate_sd",

        "final_mothers_mean",
        "final_mothers_sd",
        "final_children_mean",
        "final_children_sd",

        "mean_mother_energy_mean",
        "mean_mother_energy_sd",
        "final_mother_energy_mean",
        "final_mother_energy_sd",

        "mean_child_hunger_mean",
        "mean_child_hunger_sd",
        "final_child_hunger_mean",
        "final_child_hunger_sd",

        "mean_child_distress_mean",
        "mean_child_distress_sd",
        "final_child_distress_mean",
        "final_child_distress_sd",

        "tail_mother_energy_mean",
        "tail_mother_energy_sd",
        "tail_child_hunger_mean",
        "tail_child_hunger_sd",
        "tail_child_distress_mean",
        "tail_child_distress_sd",
        "tail_child_pop_mean",
        "tail_child_pop_sd",
        "tail_mother_child_distance_mean",
        "tail_mother_child_distance_sd",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


# ============================================================
# Plot
# ============================================================

def plot_sensitivity_map(all_results, baseline, out_dir):
    subplot_count = len(PHASE3_SENSITIVITY_SUBPLOT_CONFIG)
    cols = 2
    rows = int(np.ceil(subplot_count / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
    axes_flat = np.asarray(axes).flatten()

    child_color = "#D08770"
    mother_color = "#5E81AC"
    hunger_color = "#BF616A"
    distress_color = "#B48EAD"

    fig.suptitle(
        "Phase 3 · OVAT Sensitivity Analysis\n"
        "Mother-child survival response under one-variable-at-a-time perturbation",
        fontsize=14,
        fontweight="bold",
        y=1.01,
    )

    for idx, (set_id, key, xlabel, color) in enumerate(PHASE3_SENSITIVITY_SUBPLOT_CONFIG):
        ax_surv = axes_flat[idx]
        ax_state = ax_surv.twinx()

        data = all_results.get(set_id, [])
        if not data:
            ax_surv.set_visible(False)
            continue

        xs = np.asarray([d["param_value"] for d in data], dtype=float)

        mother_surv = np.asarray([d["mother_survival_rate_mean"] for d in data], dtype=float)
        mother_surv_sd = np.asarray([d["mother_survival_rate_sd"] for d in data], dtype=float)

        child_surv = np.asarray([d["child_survival_rate_mean"] for d in data], dtype=float)
        child_surv_sd = np.asarray([d["child_survival_rate_sd"] for d in data], dtype=float)

        child_hunger = np.asarray([d["tail_child_hunger_mean"] for d in data], dtype=float)
        child_hunger_sd = np.asarray([d["tail_child_hunger_sd"] for d in data], dtype=float)

        child_distress = np.asarray([d["tail_child_distress_mean"] for d in data], dtype=float)

        ax_surv.plot(
            xs,
            mother_surv,
            color=mother_color,
            linewidth=2.0,
            marker="o",
            markersize=3.5,
            label="Mother Survival",
        )
        ax_surv.fill_between(
            xs,
            np.clip(mother_surv - mother_surv_sd, 0.0, 1.0),
            np.clip(mother_surv + mother_surv_sd, 0.0, 1.0),
            color=mother_color,
            alpha=0.10,
        )

        ax_surv.plot(
            xs,
            child_surv,
            color=child_color,
            linewidth=2.0,
            marker="s",
            markersize=3.5,
            label="Child Survival",
        )
        ax_surv.fill_between(
            xs,
            np.clip(child_surv - child_surv_sd, 0.0, 1.0),
            np.clip(child_surv + child_surv_sd, 0.0, 1.0),
            color=child_color,
            alpha=0.10,
        )

        ax_surv.axhline(
            0.80,
            color="#BF616A",
            linestyle=":",
            linewidth=1.1,
            alpha=0.75,
            label="Survival threshold 0.80",
        )

        ax_surv.set_ylim(-0.05, 1.15)
        ax_surv.set_ylabel("Survival Rate", fontsize=9)

        ax_state.plot(
            xs,
            child_hunger,
            color=hunger_color,
            linewidth=1.8,
            linestyle="--",
            marker="^",
            markersize=3.2,
            label="Tail Child Hunger",
        )
        ax_state.fill_between(
            xs,
            np.clip(child_hunger - child_hunger_sd, 0.0, 1.0),
            np.clip(child_hunger + child_hunger_sd, 0.0, 1.0),
            color=hunger_color,
            alpha=0.07,
        )

        ax_state.plot(
            xs,
            child_distress,
            color=distress_color,
            linewidth=1.5,
            linestyle=":",
            marker="x",
            markersize=3.2,
            label="Tail Child Distress",
        )

        ax_state.axhline(
            0.35,
            color="black",
            linestyle=":",
            linewidth=1.0,
            alpha=0.45,
            label="Child hunger target",
        )

        ax_state.set_ylim(-0.05, 1.15)
        ax_state.set_ylabel("Child State", fontsize=9)

        if key not in HIDE_BASELINE_FOR and key in baseline:
            baseline_val = float(baseline[key])
            ax_surv.axvline(
                baseline_val,
                color="black",
                linestyle="--",
                linewidth=1.1,
                alpha=0.65,
                label=f"Baseline = {baseline_val:g}",
            )

        ax_surv.set_xlabel(xlabel, fontsize=9)
        ax_surv.set_title(f"Set {set_id} · {key}", fontsize=10, fontweight="bold")
        ax_surv.grid(True, linestyle="--", alpha=0.28)

        lines_surv, labels_surv = ax_surv.get_legend_handles_labels()
        lines_state, labels_state = ax_state.get_legend_handles_labels()

        ax_surv.legend(
            lines_surv + lines_state,
            labels_surv + labels_state,
            loc="lower left",
            fontsize=7,
            framealpha=0.88,
        )

    for j in range(subplot_count, len(axes_flat)):
        axes_flat[j].set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "phase3_sensitivity_map.png")
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"\nSaved Phase 3 sensitivity map → {out_path}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="OVAT Sensitivity Sweep for Phase 3 mother-child survival.")
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--seeds", type=int, default=5, help="Number of seeds starting from 42.")
    parser.add_argument("--repeats", type=int, default=3, help="Repeats per seed.")
    parser.add_argument("--sets", type=str, default="A", help="Which sets to run, e.g. A, AB, ABCD.")
    parser.add_argument("--tau", type=float, default=0.1)
    parser.add_argument("--perceptual_noise", type=float, default=0.1)
    parser.add_argument("--tail_window", type=int, default=TAIL_WINDOW)

    args = parser.parse_args()

    seeds = list(range(42, 42 + args.seeds))
    sets_to_run = [s.upper() for s in args.sets if s.upper() in PHASE3_SENSITIVITY_SWEEPS]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT,
        "outputs",
        "phase3_survival_full",
        "sensitivity",
        ts,
    )
    os.makedirs(out_dir, exist_ok=True)

    total_values = sum(len(PHASE3_SENSITIVITY_SWEEPS[s]["values"]) for s in sets_to_run)
    total_runs = total_values * len(seeds) * args.repeats

    print("=" * 70)
    print("Phase 3 · OVAT Sensitivity Sweep")
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
    print(f"Baseline         : {PHASE3_BASELINE}")
    print(f"Output           : {out_dir}")
    print("=" * 70)

    all_results = {}

    for set_id in sets_to_run:
        sweep = PHASE3_SENSITIVITY_SWEEPS[set_id]
        key = sweep["key"]

        print(f"\n── Set {set_id}: Sweeping '{key}' ──")
        print(f"   Values: {sweep['values']}")

        results = run_set(
            set_id=set_id,
            sweep=sweep,
            baseline=PHASE3_BASELINE,
            seeds=seeds,
            repeats=args.repeats,
            duration=args.duration,
            tau=args.tau,
            noise=args.perceptual_noise,
            tail_window=args.tail_window,
        )

        all_results[set_id] = results

        csv_path = os.path.join(out_dir, f"set_{set_id}_{key}.csv")
        save_csv(results, csv_path)
        print(f"   Saved CSV → {csv_path}")

    plot_sensitivity_map(all_results, PHASE3_BASELINE, out_dir)

    summary_path = os.path.join(out_dir, "phase3_sensitivity_summary.json")
    with open(summary_path, "w") as f:
        json.dump(
            {
                "baseline": PHASE3_BASELINE,
                "duration": args.duration,
                "seeds": seeds,
                "repeats": args.repeats,
                "tau": args.tau,
                "perceptual_noise": args.perceptual_noise,
                "tail_window": args.tail_window,
                "sets": sets_to_run,
                "total_values": total_values,
                "total_runs": total_runs,
                "results": all_results,
            },
            f,
            indent=2,
        )

    print(f"Saved summary JSON → {summary_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()