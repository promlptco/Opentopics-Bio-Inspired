# experiments/phase5_evolution/run.py
"""
Phase 5 — Block 2 Baldwin Emergence runner.

Modes:
  sweep  — all 4 conditions × 10 seeds = 40 runs  (default)
  single — one run (mut_on_plast_off, seed=42) for quick diagnostics

Usage:
  python -m experiments.phase5_evolution.run --mode sweep --workers 4
  python -m experiments.phase5_evolution.run --mode single
"""

import os
import sys
import csv
import json
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import numpy as np

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase5_evolution.config import (
    CONDITIONS, SWEEP_SEEDS, MAX_TICKS, SAMPLE_WINDOW,
    INIT_MOTHERS, SUCCESS_CARE_THRESHOLD, BEST_ECOLOGICAL,
    make_config,
)


# ─────────────────────────────────────────────────────────────────────────────
# Single-run wrapper
# ─────────────────────────────────────────────────────────────────────────────

def run_one(condition: str, seed: int) -> dict:
    import random as _random
    _random.seed(seed)
    np.random.seed(seed)

    from simulation.simulation import Simulation

    cfg = make_config(condition, seed)
    sim = Simulation(cfg)
    sim.initialize()

    snapshots = []

    for t in range(cfg.max_ticks):
        # Sample genome state before step
        if t % SAMPLE_WINDOW == 0:
            alive_m = [m for m in sim.mothers if m.alive]
            if alive_m:
                cares   = [m.genome.care_weight   for m in alive_m]
                forages = [m.genome.forage_weight  for m in alive_m]
                selfs   = [m.genome.self_weight    for m in alive_m]
                snapshots.append({
                    "tick":        t,
                    "n_mothers":   len(alive_m),
                    "mean_care":   float(np.mean(cares)),
                    "sd_care":     float(np.std(cares)),
                    "mean_forage": float(np.mean(forages)),
                    "mean_self":   float(np.mean(selfs)),
                })
            else:
                snapshots.append({
                    "tick": t, "n_mothers": 0,
                    "mean_care": float("nan"), "sd_care": float("nan"),
                    "mean_forage": float("nan"), "mean_self": float("nan"),
                })

        sim.step()
        sim.tick += 1

        if not any(m.alive for m in sim.mothers):
            break

    alive_m      = [m for m in sim.mothers if m.alive]
    total_matured = sum(
        1 for r in sim.logger.death_records
        if r.agent_type == "child" and r.cause == "matured"
    )
    final_care = (
        float(np.mean([m.genome.care_weight for m in alive_m]))
        if alive_m else float("nan")
    )

    return {
        "condition":         condition,
        "seed":              seed,
        "snapshots":         snapshots,
        "final_pop":         len(alive_m),
        "final_care_weight": final_care,
        "total_matured":     total_matured,
        "last_tick":         sim.tick,
    }


def _run_task(args):
    condition, seed = args
    return run_one(condition, seed)


def _n_workers(w: int) -> int:
    return (os.cpu_count() or 1) if w == 0 else max(1, w)


# ─────────────────────────────────────────────────────────────────────────────
# Sweep
# ─────────────────────────────────────────────────────────────────────────────

def run_sweep(workers: int = 4) -> list:
    tasks = [
        (cond, seed)
        for cond in CONDITIONS
        for seed in SWEEP_SEEDS
    ]
    print(f"\n  Running {len(tasks)} Phase 5 runs"
          f"  ({len(CONDITIONS)} conditions × {len(SWEEP_SEEDS)} seeds)"
          f"  workers={workers}")

    if workers <= 1:
        return [_run_task(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_run_task, tasks))


# ─────────────────────────────────────────────────────────────────────────────
# Aggregation
# ─────────────────────────────────────────────────────────────────────────────

def summarize(results: list) -> dict:
    """Group by condition; compute mean trajectory and final stats across seeds."""
    by_condition = {c: [] for c in CONDITIONS}
    for r in results:
        by_condition[r["condition"]].append(r)

    summary = {}
    for cond, runs in by_condition.items():
        final_cares = [r["final_care_weight"] for r in runs
                       if not np.isnan(r["final_care_weight"])]
        final_pops  = [r["final_pop"]    for r in runs]
        total_mat   = [r["total_matured"] for r in runs]

        # Build common tick axis and aggregate care trajectories
        all_ticks = sorted({s["tick"] for r in runs for s in r["snapshots"]})
        care_mat  = []
        pop_mat   = []
        for r in runs:
            snap = {s["tick"]: s for s in r["snapshots"]}
            care_mat.append([snap[t]["mean_care"]  if t in snap else float("nan") for t in all_ticks])
            pop_mat.append( [snap[t]["n_mothers"]  if t in snap else float("nan") for t in all_ticks])
        care_arr = np.array(care_mat, dtype=float)
        pop_arr  = np.array(pop_mat,  dtype=float)

        summary[cond] = {
            "mean_final_care":      float(np.mean(final_cares)) if final_cares else float("nan"),
            "sd_final_care":        float(np.std(final_cares))  if final_cares else float("nan"),
            "mean_final_pop":       float(np.mean(final_pops)),
            "mean_total_matured":   float(np.mean(total_mat)),
            "success":              bool(np.nanmean(final_cares) > SUCCESS_CARE_THRESHOLD)
                                    if final_cares else False,
            "trajectory_ticks":     all_ticks,
            "trajectory_mean_care": np.nanmean(care_arr, axis=0).tolist(),
            "trajectory_sd_care":   np.nanstd(care_arr,  axis=0).tolist(),
            "trajectory_mean_pop":  np.nanmean(pop_arr,  axis=0).tolist(),
        }

    return summary


# ─────────────────────────────────────────────────────────────────────────────
# I/O helpers
# ─────────────────────────────────────────────────────────────────────────────

_RAW_FIELDS = [
    "condition", "seed",
    "final_care_weight", "final_pop", "total_matured", "last_tick",
]


def _save_csv(rows: list, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_RAW_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  Saved: {os.path.basename(path)}")


def _save_json(obj, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"  Saved: {os.path.basename(path)}")


def _print_summary(summary: dict) -> None:
    neutral = SUCCESS_CARE_THRESHOLD
    print(f"\n  {'Condition':<20}  {'FinalCare':>10}  {'FinalPop':>9}"
          f"  {'Matured':>8}  {'Success':>8}")
    print("  " + "-" * 63)
    for cond, s in summary.items():
        fc = s["mean_final_care"]
        print(
            f"  {cond:<20}  {fc:>10.3f}  {s['mean_final_pop']:>9.1f}"
            f"  {s['mean_total_matured']:>8.0f}"
            f"  {'YES ✓' if s['success'] else 'no':>8}"
        )
    print(f"\n  Neutral baseline = {neutral:.3f}  "
          f"(mean_genome_care_weight must exceed this to count as success)")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_experiment(args) -> None:
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase5_evolution", f"evo_{ts}")
    os.makedirs(out_dir, exist_ok=True)
    n_workers = _n_workers(args.workers)

    print("Phase 5 — Block 2 Baldwin Emergence")
    print(f"Output dir : {out_dir}")
    print(f"Workers    : {n_workers}")
    print(f"Max ticks  : {MAX_TICKS:,}")
    eco = BEST_ECOLOGICAL
    print(f"Ecology    : ISM={eco['infant_starvation_multiplier']:.2f}"
          f"  eat={eco['eat_gain']:.2f}"
          f"  food={eco['init_food']}"
          f"  cost={eco['move_cost']:.4f}")
    print(f"Conditions : {', '.join(CONDITIONS)}")

    if args.mode == "single":
        print("\n  Running single diagnostic (mut_on_plast_off, seed=42) ...")
        r = run_one("mut_on_plast_off", seed=42)
        print(f"  care={r['final_care_weight']:.4f}  pop={r['final_pop']}"
              f"  matured={r['total_matured']}  ticks={r['last_tick']:,}")
        # Print trajectory sample
        snaps = r["snapshots"]
        print(f"\n  Genome trajectory (every {SAMPLE_WINDOW} ticks):")
        print(f"  {'tick':>6}  {'n_mothers':>9}  {'mean_care':>10}")
        for s in snaps[::max(1, len(snaps)//10)]:   # show ~10 points
            print(f"  {s['tick']:>6}  {s['n_mothers']:>9}"
                  f"  {s['mean_care']:>10.4f}")
        return

    # Full sweep
    results = run_sweep(n_workers)
    summary = summarize(results)

    _print_summary(summary)

    # Save trajectories separately (per-seed detail)
    trajectories = [
        {"condition": r["condition"], "seed": r["seed"], "snapshots": r["snapshots"]}
        for r in results
    ]
    _save_json(trajectories, os.path.join(out_dir, "evo_trajectories.json"))
    _save_csv(results,       os.path.join(out_dir, "evo_results_raw.csv"))
    _save_json(summary,      os.path.join(out_dir, "evo_summary.json"))

    try:
        from experiments.phase5_evolution.plot import plot_care_evolution, plot_final_distribution
        plot_care_evolution(summary,  out_dir)
        plot_final_distribution(summary, out_dir)
    except Exception as exc:
        print(f"  [warn] plots failed: {exc}")
        import traceback; traceback.print_exc()

    print(f"\nDone.  Outputs: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 5 Block 2 Baldwin Emergence")
    parser.add_argument("--mode",    choices=["sweep", "single"], default="sweep")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel workers (0=auto cpu_count)")
    run_experiment(parser.parse_args())
