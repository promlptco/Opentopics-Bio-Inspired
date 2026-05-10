# experiments/phase4_weight_sweep/phase4b_run.py
"""
Phase 4b Ecology Calibration — init_food x eat_gain sweep with OPTIMAL weights.

28 combos x 10 seeds x 3 repeats = 840 runs.
Selects BEST_CALIBRATED: EASY ecology (mother_survival >= 0.80 AND C_matr >= 0.05).

Usage:
    python -m experiments.phase4_weight_sweep.phase4b_run --workers 4
    python -m experiments.phase4_weight_sweep.phase4b_run --mode single
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

from experiments.phase4_weight_sweep.phase4b_config import (
    INIT_MOTHERS, MAX_TICKS,
    INIT_FOOD_VALUES, EAT_GAIN_VALUES,
    SWEEP_SEEDS, N_REPEATS,
    MOTHER_SURVIVAL_MIN, CMATR_MIN, BEST_CALIBRATED_LABEL,
    OPTIMAL_WEIGHTS, ISM, MOVE_COST_FIXED,
    make_config,
)


# ─────────────────────────────────────────────────────────────────────────────
# Single-run wrapper
# ─────────────────────────────────────────────────────────────────────────────

def run_one(init_food: int, eat_gain: float, seed: int,
            duration: int = MAX_TICKS) -> dict:
    import random as _random
    _random.seed(seed)
    np.random.seed(seed)

    from simulation.simulation import Simulation

    cfg      = make_config(init_food, eat_gain, duration)
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

    matured = sum(
        1 for r in sim.logger.death_records
        if r.agent_type == "child" and r.cause == "matured"
    )
    hunger_deaths = [
        r for r in sim.logger.death_records
        if r.agent_type == "child" and r.cause == "hunger"
    ]
    death_ticks    = [r.tick for r in hunger_deaths]
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
        "init_food":                init_food,
        "eat_gain":                 eat_gain,
        "seed":                     seed,
        "final_pop":                len(alive_m),
        "m_surv":                   len(alive_m) / INIT_MOTHERS,
        "c_matr":                   matured / INIT_MOTHERS,
        "child_death_mu":           child_death_mu,
        "care_pct":                 care_pct,
        "forage_pct":               forage_pct,
        "self_pct":                 self_pct,
        "energy_history":           energy_hist,
        "population_history":       pop_hist,
        "child_energy_history":     child_e_hist,
        "child_population_history": child_p_hist,
    }


def _run_task(task):
    init_food, eat_gain, seed = task
    return run_one(init_food, eat_gain, seed)


def _n_workers(w: int) -> int:
    return (os.cpu_count() or 1) if w == 0 else max(1, w)


# ─────────────────────────────────────────────────────────────────────────────
# Sweep
# ─────────────────────────────────────────────────────────────────────────────

def run_sweep(workers: int = 4) -> tuple:
    """
    Run all (init_food x eat_gain) combos x SWEEP_SEEDS x N_REPEATS.
    Returns (raw_rows, summary_rows).
    """
    tasks = [
        (food, eat, s * 1000 + rep)
        for food in INIT_FOOD_VALUES
        for eat  in EAT_GAIN_VALUES
        for s    in SWEEP_SEEDS
        for rep  in range(N_REPEATS)
    ]
    n_combos = len(INIT_FOOD_VALUES) * len(EAT_GAIN_VALUES)
    print(f"\n  Running {len(tasks)} Phase 4b sweeps  "
          f"({n_combos} combos x {len(SWEEP_SEEDS)} seeds x {N_REPEATS} repeats)"
          f"  workers={workers}")

    if workers <= 1:
        raw = [_run_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            raw = list(pool.map(_run_task, tasks))

    n_per_combo  = len(SWEEP_SEEDS) * N_REPEATS
    combos       = [(f, e) for f in INIT_FOOD_VALUES for e in EAT_GAIN_VALUES]
    summary_rows = []

    for idx, (food, eat) in enumerate(combos):
        reps         = raw[idx * n_per_combo: (idx + 1) * n_per_combo]
        c_matr_vals  = np.array([r["c_matr"]        for r in reps])
        m_surv_vals  = np.array([r["m_surv"]        for r in reps])
        death_vals   = np.array([r["child_death_mu"] for r in reps])
        care_vals    = np.array([r["care_pct"]       for r in reps])
        summary_rows.append({
            "init_food":           food,
            "eat_gain":            eat,
            "c_matr_mean":         float(np.mean(c_matr_vals)),
            "c_matr_sd":           float(np.std(c_matr_vals)),
            "m_surv_mean":         float(np.mean(m_surv_vals)),
            "m_surv_sd":           float(np.std(m_surv_vals)),
            "child_death_mu_mean": float(np.mean(death_vals)),
            "child_death_mu_sd":   float(np.std(death_vals)),
            "care_pct_mean":       float(np.mean(care_vals)),
        })

    return raw, summary_rows


# ─────────────────────────────────────────────────────────────────────────────
# Selection
# ─────────────────────────────────────────────────────────────────────────────

def select_best(summary_rows: list) -> dict:
    """
    BEST_CALIBRATED: EASY ecology where mother_survival >= MOTHER_SURVIVAL_MIN
    AND C_matr >= CMATR_MIN.  Among valid combos: highest C_matr.
    Fallback: highest C_matr overall if no combo meets both gates.
    """
    valid = [
        r for r in summary_rows
        if r["m_surv_mean"] >= MOTHER_SURVIVAL_MIN and r["c_matr_mean"] >= CMATR_MIN
    ]

    if valid:
        best   = max(valid, key=lambda r: (r["c_matr_mean"], r["m_surv_mean"]))
        status = "validated"
    else:
        best   = max(summary_rows, key=lambda r: r["c_matr_mean"])
        status = "fallback_cmatr_only"

    return {
        BEST_CALIBRATED_LABEL: {
            "infant_starvation_multiplier": ISM,
            "init_food":           int(best["init_food"]),
            "eat_gain":            float(best["eat_gain"]),
            "move_cost":           MOVE_COST_FIXED,
            "rest_recovery":       0.005,
            "hunger_rate":         1.0 / 35.0,
            "perception_radius":   8,
            "food_perception_radius": 8,
            "care_weight":         OPTIMAL_WEIGHTS["care_weight"],
            "forage_weight":       OPTIMAL_WEIGHTS["forage_weight"],
            "self_weight":         OPTIMAL_WEIGHTS["self_weight"],
            "c_matr_mean":         float(best["c_matr_mean"]),
            "m_surv_mean":         float(best["m_surv_mean"]),
            "child_death_mu_mean": float(best["child_death_mu_mean"]),
            "selection_status":    status,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# CSV / JSON helpers
# ─────────────────────────────────────────────────────────────────────────────

_RAW_FIELDS = [
    "init_food", "eat_gain", "seed",
    "final_pop", "m_surv", "c_matr", "child_death_mu",
    "care_pct", "forage_pct", "self_pct",
]
_SUM_FIELDS = [
    "init_food", "eat_gain",
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
    print(f"\n  {'food':>5}  {'eat':>5}  {'C_matr':>8}  {'M_surv':>8}  "
          f"{'child_mu':>10}  care%")
    print("  " + "-" * 57)
    for r in summary_rows:
        gate = (" *" if (r["m_surv_mean"] >= MOTHER_SURVIVAL_MIN
                         and r["c_matr_mean"] >= CMATR_MIN) else "")
        print(
            f"  {r['init_food']:>5}  {r['eat_gain']:>5.2f}"
            f"  {r['c_matr_mean']:>8.3f}  {r['m_surv_mean']:>8.3f}"
            f"  {r['child_death_mu_mean']:>10.1f}"
            f"  {r['care_pct_mean']:>5.2%}{gate}"
        )
    print("  (* = passes both gates: M_surv >= {:.0%}  C_matr >= {:.2f})".format(
        MOTHER_SURVIVAL_MIN, CMATR_MIN))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_experiment(args) -> None:
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT, "outputs", "phase4_weight_sweep", f"phase4b_{ts}"
    )
    os.makedirs(out_dir, exist_ok=True)
    n_workers = _n_workers(args.workers)

    print("Phase 4b Ecology Calibration (init_food x eat_gain sweep)")
    print(f"Output dir : {out_dir}")
    print(f"Workers    : {n_workers}")
    print(f"ISM        : {ISM}")
    print(f"move_cost  : {MOVE_COST_FIXED}")
    print(f"Weights    : care={OPTIMAL_WEIGHTS['care_weight']}"
          f"  forage={OPTIMAL_WEIGHTS['forage_weight']}"
          f"  self={OPTIMAL_WEIGHTS['self_weight']}")
    n_combos = len(INIT_FOOD_VALUES) * len(EAT_GAIN_VALUES)
    print(f"Grid       : {len(INIT_FOOD_VALUES)} init_food x {len(EAT_GAIN_VALUES)} eat_gain"
          f" = {n_combos} combos")
    print(f"Total runs : {n_combos * len(SWEEP_SEEDS) * N_REPEATS}")

    if args.mode == "single":
        r = run_one(init_food=300, eat_gain=0.50, seed=42)
        print(f"\n  single run (food=300, eat=0.50): "
              f"C_matr={r['c_matr']:.3f}  M_surv={r['m_surv']:.3f}"
              f"  child_death_mu={r['child_death_mu']:.1f}")
        return

    # Full sweep
    raw, summary = run_sweep(workers=n_workers)

    _print_summary(summary)

    _save_csv(raw,     os.path.join(out_dir, "sweep_results_raw.csv"), _RAW_FIELDS)
    _save_csv(summary, os.path.join(out_dir, "sweep_summary.csv"),     _SUM_FIELDS)

    selected = select_best(summary)
    _save_json(selected, os.path.join(out_dir, "selected_ecology.json"))

    bc = selected[BEST_CALIBRATED_LABEL]
    print(f"\n  {BEST_CALIBRATED_LABEL}:")
    print(f"    init_food={bc['init_food']}  eat_gain={bc['eat_gain']:.2f}"
          f"  move_cost={bc['move_cost']:.3f}  ISM={bc['infant_starvation_multiplier']:.1f}")
    print(f"    C_matr={bc['c_matr_mean']:.3f}  M_surv={bc['m_surv_mean']:.3f}"
          f"  status={bc['selection_status']}")

    # Generate plots
    try:
        from experiments.phase4_weight_sweep.phase4b_plot import (
            plot_cmatr_heatmap,
            plot_msurv_heatmap,
            plot_scatter,
        )
        plot_cmatr_heatmap(summary, selected, out_dir)
        plot_msurv_heatmap(summary, selected, out_dir)
        plot_scatter(summary, selected, out_dir)
    except Exception as exc:
        print(f"  [warn] plots failed: {exc}")
        import traceback; traceback.print_exc()

    print(f"\nDone.  Outputs: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 4b Ecology Calibration")
    parser.add_argument("--mode",    type=str,
                        choices=["sweep", "single"], default="sweep")
    parser.add_argument("--workers", type=int, default=4)
    run_experiment(parser.parse_args())
