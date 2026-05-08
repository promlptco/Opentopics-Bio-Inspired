# experiments/phase4_weight_sweep/run.py
"""
Phase 4 Motivation Weight Sweep.

Sweeps care_weight × forage_weight (5×5 = 25 combos × 5 seeds = 125 runs)
over the Phase 3b BEST_ECOLOGICAL ecology.  Both Phase 4 structural fixes
(Approach A + E) are already baked into simulation.simulation.Simulation.

Modes:
  sweep   — full 25-combo grid (default)
  single  — single run (care=1.0, forage=1.0) for quick diagnostic

Usage:
  python -m experiments.phase4_weight_sweep.run --mode sweep --workers 4
  python -m experiments.phase4_weight_sweep.run --mode single
"""

import sys
import os
import argparse
import csv
import json
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import numpy as np

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase4_weight_sweep.config import (
    INIT_MOTHERS, MATURITY_AGE, MAX_TICKS,
    CARE_WEIGHT_VALUES, FORAGE_WEIGHT_VALUES, SELF_WEIGHT_FIXED,
    SWEEP_SEEDS, VALIDATION_SEEDS,
    VIABLE_MIN_C_MATR, VIABLE_LABEL, OPTIMAL_LABEL,
    BEST_ECOLOGICAL, make_config,
)


# ─────────────────────────────────────────────────────────────────────────────
# Single-run wrapper
# ─────────────────────────────────────────────────────────────────────────────

def run_one(care_weight: float, forage_weight: float, seed: int,
            self_weight: float = SELF_WEIGHT_FIXED,
            duration: int = MAX_TICKS) -> dict:
    import random as _random
    _random.seed(seed)
    np.random.seed(seed)

    from simulation.simulation import Simulation

    cfg      = make_config(care_weight, forage_weight, self_weight, duration)
    cfg.seed = seed
    sim      = Simulation(cfg)
    sim.initialize()

    energy_hist  = []
    pop_hist     = []
    child_e_hist = []
    child_p_hist = []

    for t in range(cfg.max_ticks):
        alive_m = [m for m in sim.mothers  if m.alive]
        alive_c = [c for c in sim.children if c.alive]

        energy_hist.append(
            sum(m.energy for m in alive_m) / cfg.init_mothers
        )
        pop_hist.append(len(alive_m))
        child_e_hist.append(
            float(np.nanmean([c.energy for c in alive_c]))
            if alive_c else float("nan")
        )
        child_p_hist.append(len(alive_c))

        sim.step()
        sim.tick += 1

        if not any(m.alive for m in sim.mothers):
            break

    alive_m = [m for m in sim.mothers if m.alive]

    matured      = sum(
        1 for r in sim.logger.death_records
        if r.agent_type == "child" and r.cause == "matured"
    )
    hunger_deaths = [
        r for r in sim.logger.death_records
        if r.agent_type == "child" and r.cause == "hunger"
    ]
    death_ticks  = [r.tick for r in hunger_deaths]
    child_death_mu = (
        float(sum(death_ticks) / len(death_ticks))
        if death_ticks else float(cfg.max_ticks)
    )

    choices    = sim.logger.choice_records
    n_ch       = len(choices)
    care_pct   = sum(1 for r in choices if r.winner_domain == "care")   / n_ch if n_ch else 0.0
    forage_pct = sum(1 for r in choices if r.winner_domain == "forage") / n_ch if n_ch else 0.0
    self_pct   = sum(1 for r in choices if r.winner_domain == "self")   / n_ch if n_ch else 0.0

    return {
        "care_weight":            care_weight,
        "forage_weight":          forage_weight,
        "self_weight":            self_weight,
        "seed":                   seed,
        "final_pop":              len(alive_m),
        "m_surv":                 len(alive_m) / INIT_MOTHERS,
        "c_matr":                 matured / INIT_MOTHERS,
        "child_death_mu":         child_death_mu,
        "care_pct":               care_pct,
        "forage_pct":             forage_pct,
        "self_pct":               self_pct,
        "energy_history":         energy_hist,
        "population_history":     pop_hist,
        "child_energy_history":   child_e_hist,
        "child_population_history": child_p_hist,
    }


def _run_task(task):
    care, forage, seed = task
    return run_one(care, forage, seed)


def _n_workers(w: int) -> int:
    return (os.cpu_count() or 1) if w == 0 else max(1, w)


# ─────────────────────────────────────────────────────────────────────────────
# Sweep
# ─────────────────────────────────────────────────────────────────────────────

def run_sweep(workers: int = 4) -> tuple:
    """
    Run all 25 combos × 5 seeds = 125 runs.

    Returns (raw_rows, summary_rows) where each row is a dict.
    """
    tasks = [
        (c, f, s)
        for c in CARE_WEIGHT_VALUES
        for f in FORAGE_WEIGHT_VALUES
        for s in SWEEP_SEEDS
    ]
    total = len(tasks)
    print(f"\n  Running {total} Phase 4 sweeps  "
          f"({len(CARE_WEIGHT_VALUES)}x{len(FORAGE_WEIGHT_VALUES)} combos"
          f" x {len(SWEEP_SEEDS)} seeds)  workers={workers}")

    if workers <= 1:
        raw = [_run_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            raw = list(pool.map(_run_task, tasks))

    # Aggregate per (care, forage) combo
    combos = [(c, f) for c in CARE_WEIGHT_VALUES for f in FORAGE_WEIGHT_VALUES]
    n_seeds = len(SWEEP_SEEDS)
    summary_rows = []

    for idx, (care, forage) in enumerate(combos):
        reps = raw[idx * n_seeds: (idx + 1) * n_seeds]
        c_matr_vals  = np.array([r["c_matr"]        for r in reps])
        m_surv_vals  = np.array([r["m_surv"]        for r in reps])
        death_vals   = np.array([r["child_death_mu"] for r in reps])
        care_pct_vals = np.array([r["care_pct"]     for r in reps])
        summary_rows.append({
            "care_weight":          care,
            "forage_weight":        forage,
            "c_matr_mean":          float(np.mean(c_matr_vals)),
            "c_matr_sd":            float(np.std(c_matr_vals)),
            "m_surv_mean":          float(np.mean(m_surv_vals)),
            "m_surv_sd":            float(np.std(m_surv_vals)),
            "child_death_mu_mean":  float(np.mean(death_vals)),
            "child_death_mu_sd":    float(np.std(death_vals)),
            "care_pct_mean":        float(np.mean(care_pct_vals)),
        })

    return raw, summary_rows


# ─────────────────────────────────────────────────────────────────────────────
# Selection
# ─────────────────────────────────────────────────────────────────────────────

def select_weights(summary_rows: list) -> dict:
    """
    VIABLE_MIN: lowest care_weight combo with c_matr_mean >= VIABLE_MIN_C_MATR.
    OPTIMAL: combo with highest c_matr_mean (ties broken by highest m_surv_mean).
    """
    viable = [r for r in summary_rows if r["c_matr_mean"] >= VIABLE_MIN_C_MATR]

    if viable:
        # Sort by care_weight asc, then forage_weight asc (lowest bias that works)
        viable_sorted = sorted(viable, key=lambda r: (r["care_weight"], r["forage_weight"]))
        viable_min    = viable_sorted[0]
    else:
        # Fallback: closest to VIABLE_MIN_C_MATR
        viable_min = max(summary_rows, key=lambda r: r["c_matr_mean"])

    optimal = max(summary_rows,
                  key=lambda r: (r["c_matr_mean"], r["m_surv_mean"]))

    return {
        VIABLE_LABEL: {
            "care_weight":   viable_min["care_weight"],
            "forage_weight": viable_min["forage_weight"],
            "self_weight":   SELF_WEIGHT_FIXED,
            "c_matr_mean":   viable_min["c_matr_mean"],
            "m_surv_mean":   viable_min["m_surv_mean"],
        },
        OPTIMAL_LABEL: {
            "care_weight":   optimal["care_weight"],
            "forage_weight": optimal["forage_weight"],
            "self_weight":   SELF_WEIGHT_FIXED,
            "c_matr_mean":   optimal["c_matr_mean"],
            "m_surv_mean":   optimal["m_surv_mean"],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# CSV / JSON helpers
# ─────────────────────────────────────────────────────────────────────────────

_RAW_FIELDS = [
    "care_weight", "forage_weight", "self_weight", "seed",
    "final_pop", "m_surv", "c_matr", "child_death_mu",
    "care_pct", "forage_pct", "self_pct",
]
_SUM_FIELDS = [
    "care_weight", "forage_weight",
    "c_matr_mean", "c_matr_sd",
    "m_surv_mean", "m_surv_sd",
    "child_death_mu_mean", "child_death_mu_sd",
    "care_pct_mean",
]


def _save_csv(rows: list, path: str, fields: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  Saved: {os.path.basename(path)}")


def _save_json(obj: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"  Saved: {os.path.basename(path)}")


def _print_summary(summary_rows: list) -> None:
    print(f"\n  {'care':>6}  {'forage':>7}  {'C_matr':>8}  {'M_surv':>8}  "
          f"{'child_mu':>10}  care%")
    print("  " + "-" * 55)
    for r in summary_rows:
        print(
            f"  {r['care_weight']:>6.1f}  {r['forage_weight']:>7.1f}"
            f"  {r['c_matr_mean']:>8.3f}  {r['m_surv_mean']:>8.3f}"
            f"  {r['child_death_mu_mean']:>10.1f}"
            f"  {r['care_pct_mean']:>5.2%}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_experiment(args) -> None:
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT, "outputs", "phase4_weight_sweep", f"sweep_{ts}"
    )
    os.makedirs(out_dir, exist_ok=True)
    n_workers = _n_workers(args.workers)

    print("Phase 4 Motivation Weight Sweep")
    print(f"Output dir : {out_dir}")
    print(f"Workers    : {n_workers}")
    print(f"Ecology    : ISM={BEST_ECOLOGICAL['infant_starvation_multiplier']:.2f}  "
          f"eat={BEST_ECOLOGICAL['eat_gain']:.2f}  "
          f"food={BEST_ECOLOGICAL['init_food']}  "
          f"cost={BEST_ECOLOGICAL['move_cost']:.4f}")

    if args.mode == "single":
        r = run_one(1.0, 1.0, seed=42)
        print(f"\n  single run: C_matr={r['c_matr']:.3f}  M_surv={r['m_surv']:.3f}"
              f"  child_death_mu={r['child_death_mu']:.1f}")
        return

    # Full sweep
    raw, summary = run_sweep(workers=n_workers)

    _print_summary(summary)

    _save_csv(raw,     os.path.join(out_dir, "sweep_results_raw.csv"),  _RAW_FIELDS)
    _save_csv(summary, os.path.join(out_dir, "sweep_summary.csv"),      _SUM_FIELDS)

    selected = select_weights(summary)
    _save_json(selected, os.path.join(out_dir, "selected_weights.json"))

    print(f"\n  {VIABLE_LABEL} : care={selected[VIABLE_LABEL]['care_weight']:.1f}"
          f"  forage={selected[VIABLE_LABEL]['forage_weight']:.1f}"
          f"  C_matr={selected[VIABLE_LABEL]['c_matr_mean']:.3f}")
    print(f"  {OPTIMAL_LABEL}  : care={selected[OPTIMAL_LABEL]['care_weight']:.1f}"
          f"  forage={selected[OPTIMAL_LABEL]['forage_weight']:.1f}"
          f"  C_matr={selected[OPTIMAL_LABEL]['c_matr_mean']:.3f}")

    # Generate plots
    try:
        from experiments.phase4_weight_sweep.plot import (
            plot_sweep_3d_surface,
            plot_sweep_heatmap,
            plot_sweep_mother_survival,
        )
        plot_sweep_3d_surface(summary, selected, out_dir)
        plot_sweep_heatmap(summary, selected, out_dir)
        plot_sweep_mother_survival(summary, selected, out_dir)
    except Exception as exc:
        print(f"  [warn] plots failed: {exc}")
        import traceback; traceback.print_exc()

    print(f"\nDone.  Outputs: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 4 Weight Sweep")
    parser.add_argument("--mode",    type=str,
                        choices=["sweep", "single"], default="sweep")
    parser.add_argument("--workers", type=int, default=4)
    run_experiment(parser.parse_args())
