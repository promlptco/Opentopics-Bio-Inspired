"""
experiments/phase2_survival_minimal/sensitivity_sweep.py

One-Variable-at-a-Time (OVAT) Sensitivity Analysis for Phase 2.

This script varies each ecological parameter one at a time while holding the
other parameters fixed at the selected Balanced baseline.

Outputs:
  outputs/phase2_survival_minimal/sensitivity/<timestamp>/
    ├── sensitivity_map.png
    ├── set_A_hunger_rate.csv
    ├── set_B_move_cost.csv
    ├── set_C_eat_gain.csv
    ├── set_D_init_food.csv
    ├── set_E_rest_recovery.csv
    └── sensitivity_summary.json

Usage:
  python experiments/phase2_survival_minimal/sensitivity_sweep.py
  python experiments/phase2_survival_minimal/sensitivity_sweep.py --duration 1000 --seeds 5 --repeats 3
  python experiments/phase2_survival_minimal/sensitivity_sweep.py --sets AB
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

from experiments.phase2_survival_minimal.run import SurvivalSimulation, make_config
from utils.experiment import set_seed


# Confirmed Balanced baseline from auto-sweep: baseline_20260415_015935
BASELINE = {
    "hunger_rate": 0.005,
    "move_cost": 0.001,
    "eat_gain": 0.07,
    "init_food": 70,
    "rest_recovery": 0.005,
}


# High-resolution OVAT sweep ranges.
# These ranges intentionally use finer resolution near expected transition zones.
SWEEPS = {
    "A": {
        "label": "hunger_rate",
        "key": "hunger_rate",
        # np.unique() guarantees dedup on float64 arrays; set() is unreliable on floats.
        "values": np.unique(np.round(np.concatenate([
            np.arange(0.001, 0.004, 0.001),
            np.arange(0.004, 0.0085, 0.0005),
            np.arange(0.009, 0.016, 0.001),
        ]), 5)).tolist(),
    },
    "B": {
        "label": "move_cost",
        "key": "move_cost",
        "values": np.unique(np.round(np.concatenate([
            np.arange(0.0005, 0.001, 0.0002),
            np.arange(0.001, 0.0045, 0.0005),
            np.arange(0.005, 0.0086, 0.001),
        ]), 5)).tolist(),
    },
    "C": {
        "label": "eat_gain",
        "key": "eat_gain",
        "values": np.unique(np.round(np.concatenate([
            np.arange(0.03, 0.05, 0.01),
            np.arange(0.05, 0.085, 0.005),
            np.arange(0.09, 0.165, 0.01),
        ]), 5)).tolist(),
    },
    "D": {
        "label": "init_food",
        "key": "init_food",
        "values": np.unique(np.concatenate([
            np.arange(20, 30, 5),
            np.arange(30, 65, 2),
            np.arange(65, 106, 5),
        ]).astype(int)).tolist(),
    },
    "E": {
        "label": "rest_recovery",
        "key": "rest_recovery",
        "values": list(np.round(np.arange(0.005, 0.111, 0.005), 4)),
    },
}


SUBPLOT_CONFIG = [
    ("A", "hunger_rate", "Hunger Rate (per tick)", "#4C566A"),
    ("B", "move_cost", "Move Cost (per step)", "#5E81AC"),
    ("C", "eat_gain", "Eat Gain (energy per food)", "#8FBCBB"),
    ("D", "init_food", "Initial Food Count", "#D08770"),
    ("E", "rest_recovery", "Rest Recovery (per tick)", "#B48EAD"),
]


def run_one(params, seed, duration, tau=0.1, noise=0.1):
    set_seed(seed)
    cfg = make_config(params, duration)
    sim = SurvivalSimulation(cfg, tau=tau, perceptual_noise=noise)
    return sim.run()


def pad_series(values, duration):
    arr = np.full(duration, np.nan)
    values = np.asarray(values, dtype=float)
    arr[:min(duration, len(values))] = values[:duration]
    return arr


def summarize_runs(run_results, duration, tail_window=200):
    """
    Summarize repeated stochastic runs.

    Tail mean energy is used because whole-episode mean energy can be biased
    by the initial energy value. Tail energy better reflects late-run stability.
    """
    final_pops = np.asarray([r["final_pop"] for r in run_results], dtype=float)
    mean_energies = np.asarray([r["mean_energy"] for r in run_results], dtype=float)
    final_energies = np.asarray([r["final_energy"] for r in run_results], dtype=float)

    tail_energy_means = []
    tail_pop_means = []

    for r in run_results:
        energy = pad_series(r["energy_history"], duration)
        pop = pad_series(r["population_history"], duration)

        # Convert post-extinction padding from NaN to 0.0.
        # This ensures early-collapse runs contribute late-run energy/population = 0,
        # instead of contaminating the tail summary with NaN.
        energy = np.nan_to_num(energy, nan=0.0)
        pop = np.nan_to_num(pop, nan=0.0)

        tail_energy = energy[-tail_window:]
        tail_pop = pop[-tail_window:]

        tail_energy_means.append(np.mean(tail_energy))
        tail_pop_means.append(np.mean(tail_pop))

    tail_energy_means = np.asarray(tail_energy_means, dtype=float)
    tail_pop_means = np.asarray(tail_pop_means, dtype=float)

    return {
        "num_runs": int(len(run_results)),
        "survival_rate_mean": float(np.mean(final_pops) / 15.0),
        "survival_rate_sd": float(np.std(final_pops) / 15.0),
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


def run_set(set_id, sweep, baseline, seeds, repeats, duration, tau, noise, tail_window):
    key = sweep["key"]
    results = []

    for val in sweep["values"]:
        params = dict(baseline)
        params[key] = int(val) if key == "init_food" else float(val)

        run_results = []

        for seed in seeds:
            for rep in range(repeats):
                # Deterministic repeat seed: reproducible but unique per seed-repeat pair.
                run_seed = seed * 1000 + rep
                result = run_one(params, run_seed, duration, tau=tau, noise=noise)
                run_results.append(result)

        summary = summarize_runs(run_results, duration, tail_window=tail_window)
        summary["param_value"] = params[key]
        results.append(summary)

        print(
            f"  Set {set_id} [{key}={params[key]}] "
            f"runs={summary['num_runs']:02d} | "
            f"survival={summary['survival_rate_mean']:.2f} ± {summary['survival_rate_sd']:.2f} | "
            f"tailE={summary['tail_energy_mean']:.3f} ± {summary['tail_energy_sd']:.3f}"
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


def plot_sensitivity_map(all_results, baseline, out_dir):
    fig, axes = plt.subplots(2, 3, figsize=(17, 10))
    axes_flat = axes.flatten()

    energy_color = "#2E3440"

    fig.suptitle(
        "Phase 2 · OVAT Sensitivity Analysis\n"
        "Effect of Individual Parameters on Survival Rate and Late-Run Mean Energy",
        fontsize=14,
        fontweight="bold",
        y=1.01,
    )

    for idx, (set_id, key, xlabel, color) in enumerate(SUBPLOT_CONFIG):
        ax_surv = axes_flat[idx]
        ax_energy = ax_surv.twinx()

        data = all_results[set_id]
        xs = np.asarray([d["param_value"] for d in data], dtype=float)

        surv = np.asarray([d["survival_rate_mean"] for d in data], dtype=float)
        surv_sd = np.asarray([d["survival_rate_sd"] for d in data], dtype=float)

        # Use tail energy instead of whole-episode mean energy for stability analysis.
        energy = np.asarray([d["tail_energy_mean"] for d in data], dtype=float)
        energy_sd = np.asarray([d["tail_energy_sd"] for d in data], dtype=float)

        ax_surv.plot(
            xs,
            surv,
            color=color,
            linewidth=2.0,
            marker="o",
            markersize=3.5,
            label="Survival Rate",
        )
        ax_surv.fill_between(
            xs,
            np.clip(surv - surv_sd, 0.0, 1.0),
            np.clip(surv + surv_sd, 0.0, 1.0),
            color=color,
            alpha=0.10,
        )

        ax_surv.axhline(
            0.80,
            color="#BF616A",
            linestyle=":",
            linewidth=1.1,
            alpha=0.75,
            label="Collapse threshold",
        )

        ax_surv.set_ylim(-0.05, 1.15)
        ax_surv.set_ylabel("Survival Rate", color=color, fontsize=9)
        ax_surv.tick_params(axis="y", labelcolor=color)

        ax_energy.plot(
            xs,
            energy,
            color=energy_color,
            linewidth=1.7,
            linestyle="--",
            marker="s",
            markersize=3.2,
            label="Tail Mean Energy",
        )
        ax_energy.fill_between(
            xs,
            np.clip(energy - energy_sd, 0.0, 1.0),
            np.clip(energy + energy_sd, 0.0, 1.0),
            color=energy_color,
            alpha=0.07,
        )

        ax_energy.axhline(
            0.70,
            color="black",
            linestyle=":",
            linewidth=1.0,
            alpha=0.55,
            label="Target 0.70",
        )
        ax_energy.axhline(
            0.75,
            color="black",
            linestyle="--",
            linewidth=1.0,
            alpha=0.35,
            label="Target 0.75",
        )

        ax_energy.set_ylim(-0.05, 1.15)
        ax_energy.set_ylabel("Tail Mean Energy", color=energy_color, fontsize=9)
        ax_energy.tick_params(axis="y", labelcolor=energy_color)

        # Baseline is shown as a clean vertical reference line, without star marker.
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
        lines_energy, labels_energy = ax_energy.get_legend_handles_labels()

        ax_surv.legend(
            lines_surv + lines_energy,
            labels_surv + labels_energy,
            loc="lower left",
            fontsize=7,
            framealpha=0.88,
        )

    axes_flat[5].set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "sensitivity_map.png")
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"\nSaved sensitivity map → {out_path}")


def main():
    parser = argparse.ArgumentParser(description="OVAT Sensitivity Sweep for Phase 2.")
    parser.add_argument("--duration", type=int, default=1000)
    parser.add_argument("--seeds", type=int, default=5, help="Number of seeds starting from 42.")
    parser.add_argument("--repeats", type=int, default=3, help="Repeats per seed.")
    parser.add_argument("--sets", type=str, default="ABCDE", help="Which sets to run, e.g. AB or CDE.")
    parser.add_argument("--tau", type=float, default=0.1)
    parser.add_argument("--perceptual_noise", type=float, default=0.1)
    parser.add_argument("--tail_window", type=int, default=200)

    args = parser.parse_args()

    seeds = list(range(42, 42 + args.seeds))
    sets_to_run = [s.upper() for s in args.sets if s.upper() in SWEEPS]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT,
        "outputs",
        "phase2_survival_minimal",
        "sensitivity",
        ts,
    )
    os.makedirs(out_dir, exist_ok=True)

    total_values = sum(len(SWEEPS[s]["values"]) for s in sets_to_run)
    total_runs = total_values * len(seeds) * args.repeats

    print("=" * 70)
    print("Phase 2 · OVAT Sensitivity Sweep")
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
    print(f"Baseline         : {BASELINE}")
    print(f"Output           : {out_dir}")
    print("=" * 70)

    all_results = {}

    for set_id in sets_to_run:
        sweep = SWEEPS[set_id]
        key = sweep["key"]

        print(f"\n── Set {set_id}: Sweeping '{key}' ──")
        print(f"   Values: {sweep['values']}")

        results = run_set(
            set_id=set_id,
            sweep=sweep,
            baseline=BASELINE,
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

    if all(s in all_results for s in "ABCDE"):
        plot_sensitivity_map(all_results, BASELINE, out_dir)
    else:
        missing = [s for s in "ABCDE" if s not in all_results]
        print(f"\nSkipping full sensitivity map — missing sets: {missing}")

    summary_path = os.path.join(out_dir, "sensitivity_summary.json")
    with open(summary_path, "w") as f:
        json.dump(
            {
                "baseline": BASELINE,
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

    print(f"Saved summary JSON → {summary_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()