"""
experiments/phase2_survival_minimal/sensitivity_sweep.py

One-Variable-at-a-Time (OVAT) Sensitivity Analysis for Phase 2.

Usage:
  python experiments/phase2_survival_minimal/sensitivity_sweep.py
  python experiments/phase2_survival_minimal/sensitivity_sweep.py --duration 1000 --seeds 5 --repeats 3
  python experiments/phase2_survival_minimal/sensitivity_sweep.py --sets AB
  python experiments/phase2_survival_minimal/sensitivity_sweep.py --tau 0.1 --perceptual_noise 0.1

Outputs:
  outputs/phase2_survival_minimal/sensitivity/<timestamp>/
    ├── sensitivity_map.png
    ├── set_A_hunger_rate.csv
    ├── set_B_move_cost.csv
    ├── set_C_eat_gain.csv
    ├── set_D_init_food.csv
    ├── set_E_rest_recovery.csv
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

from experiments.phase2_survival_minimal.run import SurvivalSimulation, make_config
from experiments.phase2_survival_minimal.config import (
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

    All non-food parameters are held at BALANCED_BASELINE.  The result is
    empirically derived — no hand-picked food value is required.
    """
    base = {k: v for k, v in BALANCED_BASELINE.items() if k != "init_food"}
    food_range = range(10, food_max + food_step, food_step)

    print(f"\n-- Phase A: Food anchor sweep (target survival >= {target_survival:.0%}) --")

    anchor_food = None
    anchor_summary = None

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

        if anchor_food is None and survival >= target_survival:
            anchor_food = int(food)
            anchor_summary = summary
            print(f"\n  Anchor found: init_food = {anchor_food} (survival = {survival:.2f})")
            break

    if anchor_food is None:
        anchor_food = int(list(food_range)[-1])
        print(f"\n  Warning: no anchor found up to init_food={anchor_food}. Using last value.")

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
    n_sets = len(SENSITIVITY_SUBPLOT_CONFIG)
    n_cols = 2
    n_rows = (n_sets + n_cols - 1) // n_cols  # ceil division → always 2×2 for 4 sets

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(13, 9))
    axes_flat = axes.flatten()
    energy_color = "#2E3440"

    fig.suptitle(
        "Phase 2 · OVAT Sensitivity Analysis\n"
        "MotherAgent: Environmental Cue × Genome Weight → Softmax",
        fontsize=14,
        fontweight="bold",
        y=1.01,
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
            0.62,
            color="black",
            linestyle=":",
            linewidth=1.0,
            alpha=0.55,
            label="Target 0.62",
        )

        ax_energy.set_ylim(-0.05, 1.15)
        ax_energy.set_ylabel("Tail Mean Energy", color=energy_color, fontsize=9)
        ax_energy.tick_params(axis="y", labelcolor=energy_color)

        if key not in hide_keys:
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

    # Hide any unused slots (e.g. odd number of sets)
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
    parser.add_argument("--seeds", type=int, default=5, help="Number of seeds starting from 42.")
    parser.add_argument("--repeats", type=int, default=3, help="Repeats per seed.")
    parser.add_argument("--sets", type=str, default="".join(SENSITIVITY_SWEEPS.keys()),
                        help="Which sets to run, e.g. BC or DE.")
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

    if "D" in all_results:
        _auto_update_sweep_grid(all_results["D"], summary_path)

    print("\nDone.")


def _auto_update_sweep_grid(set_d_results, summary_path):
    """
    Detect HARSH / BALANCED / EASY zones from Set D and patch the
    init_food sweep grid in config.py automatically.

    Zone definitions (survival rate):
      HARSH    : 0.10 - 0.33
      BALANCED : 0.55 - 0.80
      EASY     : peak survival (>= 0.75, highest food values)

    Selects up to 4 representative init_food values per zone, deduplicates,
    sorts, and writes them back into the "sweep" grid in config.py.
    """
    import re

    harsh, balanced, easy = [], [], []

    for d in set_d_results:
        surv = d["survival_rate_mean"]
        food = int(round(d["param_value"]))
        if 0.10 <= surv <= 0.33:
            harsh.append(food)
        elif 0.55 <= surv <= 0.80:
            balanced.append(food)
        elif surv > 0.75:
            easy.append(food)

    def pick(lst, n=3):
        if not lst:
            return []
        lst = sorted(set(lst))
        if len(lst) <= n:
            return lst
        indices = [int(round(i)) for i in np.linspace(0, len(lst) - 1, n)]
        return [lst[i] for i in indices]

    grid = sorted(set(pick(harsh, 3) + pick(balanced, 4) + pick(easy, 3)))

    if not grid:
        print("\n[auto-update] WARNING: No init_food candidates detected -- config.py not updated.")
        return

    grid_str = "[" + ", ".join(str(v) for v in grid) + "]"

    config_path = os.path.join(PROJECT_ROOT, "experiments", "phase2_survival_minimal", "config.py")
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r'("init_food"\s*:\s*)\[[\d,\s]+\]',
        r'\g<1>' + grid_str,
        content,
    )

    if new_content == content:
        print("\n[auto-update] WARNING: Could not find init_food line in config.py -- not updated.")
        return

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    harsh_str   = str(pick(harsh, 3))  if harsh   else "[]"
    bal_str     = str(pick(balanced, 4)) if balanced else "[]"
    easy_str    = str(pick(easy, 3))  if easy    else "[]"

    print(f"\n[auto-update] config.py sweep grid updated:")
    print(f"  HARSH    candidates : {harsh_str}")
    print(f"  BALANCED candidates : {bal_str}")
    print(f"  EASY     candidates : {easy_str}")
    print(f"  Final grid          : {grid_str}")
    print(f"  Source              : {summary_path}")


if __name__ == "__main__":
    main()