# experiments/phase3b_calibration/run.py
"""
Phase 3b Ecological Calibration — 8-step standalone sweep.

Steps:
  1. Feasibility anchor  — ISM x eat_gain at init_food=600 (3 seeds)
  2-4. OVAT sets A/B/C   — ISM / eat_gain / init_food (5 seeds each)
  5. Full 3D grid         — 64 combos x 5 seeds = 320 runs
  6. Regime selection     — VIABLE (C_matr > 0, M_surv >= 0.30) + BEST_ECOLOGICAL
  7. Validation           — 10 seeds x selected configs
  8. Save JSON + CSVs

Usage:
    python -m experiments.phase3_survival_full.phase3b_calibration.run
    python -m experiments.phase3_survival_full.phase3b_calibration.run --workers 4
    python -m experiments.phase3_survival_full.phase3b_calibration.run --skip_anchor --skip_ovat
    python -m experiments.phase3_survival_full.phase3b_calibration.run --skip_anchor --skip_ovat --skip_grid
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import csv
import json
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase3_survival_full.phase3b_calibration.config import (
    INIT_MOTHERS, MAX_TICKS,
    ANCHOR_SEEDS, OVAT_SEEDS, GRID_SEEDS, VALIDATION_SEEDS,
    VIABLE_MIN_M_SURV, VIABLE_MIN_C_MATR,
    make_config, expand_anchor, expand_ovat, expand_grid, feeds_needed,
    OVAT_SWEEPS,
)

OUT_DIR = PROJECT_ROOT / "outputs" / "phase3_survival_full" / "phase3b_calibration"


# ── Single run — fast summary ─────────────────────────────────────────────────

def run_one(ism: float, eat_gain: float, init_food: int, seed: int) -> dict:
    from simulation.simulation import Simulation
    cfg = make_config(ism, eat_gain, init_food, seed)
    sim = Simulation(cfg)
    sim.initialize()
    original_mother_ids = {m.id for m in sim.mothers}
    while sim.tick < cfg.max_ticks:
        sim.step()
        sim.tick += 1

    alive_m  = sum(1 for m in sim.mothers if m.alive and m.id in original_mother_ids)
    matured  = sum(1 for r in sim.logger.death_records
                   if r.agent_type == "child" and r.cause == "matured")
    feeds    = len(sim.logger.care_records)

    hunger_deaths = [r for r in sim.logger.death_records
                     if r.agent_type == "child" and r.cause == "hunger"]
    death_ticks   = [r.tick for r in hunger_deaths]

    choices   = sim.logger.choice_records
    n_ch      = len(choices)
    care_pct   = 100 * sum(1 for r in choices if r.winner_domain == "care")   / n_ch if n_ch else 0
    forage_pct = 100 * sum(1 for r in choices if r.winner_domain == "forage") / n_ch if n_ch else 0
    self_pct   = 100 * sum(1 for r in choices if r.winner_domain == "self")   / n_ch if n_ch else 0

    return {
        "ism":              ism,
        "eat_gain":         eat_gain,
        "init_food":        init_food,
        "seed":             seed,
        "mother_survival":  alive_m / INIT_MOTHERS,
        "child_maturation": matured / INIT_MOTHERS,
        "matured_count":    matured,
        "feeds":            feeds,
        "feeds_per_child":  feeds / INIT_MOTHERS,
        "care_pct":         care_pct,
        "forage_pct":       forage_pct,
        "self_pct":         self_pct,
        "child_death_tick_mean": sum(death_ticks) / len(death_ticks) if death_ticks else float(MAX_TICKS),
        "child_death_tick_min":  min(death_ticks) if death_ticks else MAX_TICKS,
        "child_death_tick_max":  max(death_ticks) if death_ticks else MAX_TICKS,
    }


def _fast_task(args):
    ism, eat_gain, init_food, seed = args
    return run_one(ism, eat_gain, init_food, seed)


# ── Single run — full histories (validation) ──────────────────────────────────

def run_one_full(ism: float, eat_gain: float, init_food: int, seed: int) -> dict:
    from simulation.simulation import Simulation
    cfg = make_config(ism, eat_gain, init_food, seed)
    sim = Simulation(cfg)
    sim.initialize()

    mom_e_h, child_e_h, pop_m_h, pop_c_h = [], [], [], []

    while sim.tick < cfg.max_ticks:
        am = [m for m in sim.mothers if m.alive]
        ac = [c for c in sim.children if c.alive]
        mom_e_h.append(np.mean([m.energy for m in am]) if am else np.nan)
        child_e_h.append(np.mean([c.energy for c in ac]) if ac else np.nan)
        pop_m_h.append(len(am))
        pop_c_h.append(len(ac))
        sim.step()
        sim.tick += 1

    alive_m  = sum(1 for m in sim.mothers if m.alive)
    matured  = sum(1 for r in sim.logger.death_records
                   if r.agent_type == "child" and r.cause == "matured")
    feeds    = len(sim.logger.care_records)
    hunger_deaths = [r for r in sim.logger.death_records
                     if r.agent_type == "child" and r.cause == "hunger"]
    death_ticks   = [r.tick for r in hunger_deaths]

    return {
        "ism":              ism,
        "eat_gain":         eat_gain,
        "init_food":        init_food,
        "seed":             seed,
        "mother_survival":  alive_m / INIT_MOTHERS,
        "child_maturation": matured / INIT_MOTHERS,
        "matured_count":    matured,
        "feeds":            feeds,
        "feeds_per_child":  feeds / INIT_MOTHERS,
        "child_death_tick_mean": sum(death_ticks) / len(death_ticks) if death_ticks else float(MAX_TICKS),
        "mother_energy_history": mom_e_h,
        "child_energy_history":  child_e_h,
        "mother_pop_history":    pop_m_h,
        "child_pop_history":     pop_c_h,
    }


def _full_task(args):
    ism, eat_gain, init_food, seed = args
    return run_one_full(ism, eat_gain, init_food, seed)


# ── Aggregation ───────────────────────────────────────────────────────────────

def _mu(rows, key):
    return float(np.mean([r[key] for r in rows]))


def aggregate(rows: list[dict]) -> dict:
    """Aggregate summary rows that share same (ism, eat_gain, init_food)."""
    r0 = rows[0]
    return {
        "ism":               r0["ism"],
        "eat_gain":          r0["eat_gain"],
        "init_food":         r0["init_food"],
        "n":                 len(rows),
        "m_surv_mean":       _mu(rows, "mother_survival"),
        "c_matr_mean":       _mu(rows, "child_maturation"),
        "matured_total":     sum(r["matured_count"] for r in rows),
        "feeds_mean":        _mu(rows, "feeds"),
        "care_pct_mean":     _mu(rows, "care_pct"),
        "forage_pct_mean":   _mu(rows, "forage_pct"),
        "self_pct_mean":     _mu(rows, "self_pct"),
        "child_death_mu":    _mu(rows, "child_death_tick_mean"),
        "child_death_min":   min(r["child_death_tick_min"] for r in rows),
        "child_death_max":   max(r["child_death_tick_max"] for r in rows),
        "feeds_needed_th":   feeds_needed(r0["ism"], r0["eat_gain"]),
    }


def group_and_aggregate(results: list[dict]) -> list[dict]:
    """Group by (ism, eat_gain, init_food) and aggregate."""
    groups: dict[tuple, list] = {}
    for r in results:
        key = (r["ism"], r["eat_gain"], r["init_food"])
        groups.setdefault(key, []).append(r)
    return [aggregate(rows) for rows in groups.values()]


# ── CSV helpers ───────────────────────────────────────────────────────────────

def save_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    # Exclude list-valued history columns
    scalar_keys = [k for k, v in rows[0].items() if not isinstance(v, list)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=scalar_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved: {path}")


# ── Parallel sweep runner ─────────────────────────────────────────────────────

def run_sweep(tasks: list[tuple], workers: int, label: str,
              full: bool = False) -> list[dict]:
    fn = _full_task if full else _fast_task
    n  = len(tasks)
    print(f"  {label}: {n} runs (workers={workers})")
    results = []
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as exe:
        futs = {exe.submit(fn, t): t for t in tasks}
        for fut in as_completed(futs):
            results.append(fut.result())
            done += 1
            if done % max(1, n // 10) == 0 or done == n:
                print(f"    {done}/{n}", end="\r")
    print(f"    {n}/{n} done")
    return results


# ── Step 1 — Feasibility anchor ───────────────────────────────────────────────

def step1_anchor(workers: int) -> list[dict]:
    print("\n[Step 1] Feasibility anchor — ISM x eat_gain at init_food=600")
    combos = expand_anchor()
    tasks  = [(c["infant_starvation_multiplier"], c["eat_gain"], c["init_food"], s)
              for c in combos for s in ANCHOR_SEEDS]
    results = run_sweep(tasks, workers, "anchor")

    agg = group_and_aggregate(results)
    save_csv(results, OUT_DIR / "anchor_sweep_raw.csv")
    save_csv(agg,     OUT_DIR / "anchor_sweep.csv")

    print(f"\n  Anchor results (init_food={combos[0]['init_food']}):")
    print(f"  {'ISM':>5} {'eat_gain':>9} {'C_matr':>8} {'M_surv':>8} {'C_death_mu':>11} {'feeds_th':>9}")
    for a in sorted(agg, key=lambda x: (x["ism"], x["eat_gain"])):
        print(f"  {a['ism']:>5.2f} {a['eat_gain']:>9.2f} {a['c_matr_mean']:>8.3f} "
              f"{a['m_surv_mean']:>8.3f} {a['child_death_mu']:>11.1f} {a['feeds_needed_th']:>9.1f}")

    viable = [a for a in agg if a["c_matr_mean"] > 0]
    if viable:
        print(f"\n  VIABLE combos found: {len(viable)}")
        print(f"  Min ISM with C_matr>0: {min(a['ism'] for a in viable)}")
        print(f"  Min eat_gain with C_matr>0: {min(a['eat_gain'] for a in viable)}")
    else:
        print("\n  No viable combos found in anchor — OVAT will probe further.")
    return results


# ── Steps 2-4 — OVAT sets ─────────────────────────────────────────────────────

def step2_4_ovat(workers: int) -> dict[str, list[dict]]:
    ovat_results = {}
    for key, sw in OVAT_SWEEPS.items():
        label = sw["label"]
        print(f"\n[Step {ord(key)-62}] OVAT Set {key} — sweep {label}")
        combos = expand_ovat(key)
        tasks  = [(c["infant_starvation_multiplier"], c["eat_gain"], c["init_food"], s)
                  for c in combos for s in OVAT_SEEDS]
        results = run_sweep(tasks, workers, f"OVAT-{key}")
        agg     = group_and_aggregate(results)
        fname   = {"A": "ovat_set_A_ism", "B": "ovat_set_B_eat_gain", "C": "ovat_set_C_init_food"}[key]
        save_csv(results, OUT_DIR / f"{fname}_raw.csv")
        save_csv(agg,     OUT_DIR / f"{fname}.csv")
        ovat_results[key] = results

        # Map full param name → shortened agg dict key
        _key_map = {"infant_starvation_multiplier": "ism", "eat_gain": "eat_gain", "init_food": "init_food"}
        agg_key  = _key_map.get(sw["key"], sw["key"])

        print(f"\n  Set {key} results:")
        print(f"  {label:>12} {'C_matr':>8} {'M_surv':>8} {'C_death_mu':>11}")
        for a in sorted(agg, key=lambda x: x[agg_key]):
            print(f"  {a[agg_key]:>12} {a['c_matr_mean']:>8.3f} "
                  f"{a['m_surv_mean']:>8.3f} {a['child_death_mu']:>11.1f}")
    return ovat_results


# ── Step 5 — Full 3D grid ─────────────────────────────────────────────────────

def step5_grid(workers: int) -> list[dict]:
    print("\n[Step 5] Full 3D grid — ISM x eat_gain x init_food")
    combos = expand_grid()
    tasks  = [(c["infant_starvation_multiplier"], c["eat_gain"], c["init_food"], s)
              for c in combos for s in GRID_SEEDS]
    print(f"  {len(combos)} combos x {len(GRID_SEEDS)} seeds = {len(tasks)} runs")
    results = run_sweep(tasks, workers, "grid")
    agg     = group_and_aggregate(results)
    save_csv(results, OUT_DIR / "grid_sweep_raw.csv")
    save_csv(agg,     OUT_DIR / "grid_sweep.csv")

    viable = [a for a in agg if a["c_matr_mean"] > VIABLE_MIN_C_MATR]
    print(f"\n  Grid: {len(agg)} combos, {len(viable)} with C_matr > 0")
    if viable:
        best = max(viable, key=lambda x: (x["c_matr_mean"], x["child_death_mu"], x["m_surv_mean"]))
        print(f"  Best VIABLE: ISM={best['ism']}, eat_gain={best['eat_gain']}, "
              f"init_food={best['init_food']}, C_matr={best['c_matr_mean']:.3f}, "
              f"M_surv={best['m_surv_mean']:.3f}")
    return results


# ── Step 6 — Regime selection ─────────────────────────────────────────────────

def step6_select(grid_results: list[dict]) -> dict:
    """
    Select VIABLE and BEST_ECOLOGICAL configs.
    Priority: C_matr (desc) -> child_death_mu (desc) -> M_surv (desc)
    VIABLE requires M_surv >= VIABLE_MIN_M_SURV and C_matr > 0.
    BEST_ECOLOGICAL = best child_death_mu regardless of C_matr.
    """
    print("\n[Step 6] Regime selection")
    agg = group_and_aggregate(grid_results)

    viable_cands = [a for a in agg
                    if a["c_matr_mean"] > VIABLE_MIN_C_MATR
                    and a["m_surv_mean"] >= VIABLE_MIN_M_SURV]

    best_eco = max(agg, key=lambda x: (x["child_death_mu"], x["m_surv_mean"]))

    selected = {
        "CHILD_SURVIVAL_POSSIBLE": len(viable_cands) > 0,
        "BEST_ECOLOGICAL": {
            "ism":       best_eco["ism"],
            "eat_gain":  best_eco["eat_gain"],
            "init_food": best_eco["init_food"],
            "c_matr":    best_eco["c_matr_mean"],
            "m_surv":    best_eco["m_surv_mean"],
            "child_death_mu": best_eco["child_death_mu"],
        },
    }

    if viable_cands:
        viable = max(viable_cands,
                     key=lambda x: (x["c_matr_mean"], x["child_death_mu"], x["m_surv_mean"]))
        selected["VIABLE"] = {
            "ism":       viable["ism"],
            "eat_gain":  viable["eat_gain"],
            "init_food": viable["init_food"],
            "c_matr":    viable["c_matr_mean"],
            "m_surv":    viable["m_surv_mean"],
            "child_death_mu": viable["child_death_mu"],
        }
        print(f"  VIABLE:          ISM={viable['ism']}, eat_gain={viable['eat_gain']}, "
              f"init_food={viable['init_food']}, C_matr={viable['c_matr_mean']:.3f}, "
              f"M_surv={viable['m_surv_mean']:.3f}")
    else:
        selected["VIABLE"] = None
        print("  VIABLE:          None — no combo produced C_matr > 0 with M_surv >= 0.30")
        print("  -> Phase 4 motivation sweep is scientifically necessary.")

    print(f"  BEST_ECOLOGICAL: ISM={best_eco['ism']}, eat_gain={best_eco['eat_gain']}, "
          f"init_food={best_eco['init_food']}, child_death_mu={best_eco['child_death_mu']:.1f}, "
          f"M_surv={best_eco['m_surv_mean']:.3f}")
    return selected


# ── Step 7 — Validation ───────────────────────────────────────────────────────

def step7_validate(selected: dict, workers: int) -> dict[str, list[dict]]:
    print("\n[Step 7] Validation — 10 seeds per selected config")
    val_results = {}
    for regime, cfg in selected.items():
        if regime == "CHILD_SURVIVAL_POSSIBLE" or cfg is None:
            continue
        print(f"  Validating {regime}: ISM={cfg['ism']}, eat_gain={cfg['eat_gain']}, "
              f"init_food={cfg['init_food']}")
        tasks = [(cfg["ism"], cfg["eat_gain"], cfg["init_food"], s)
                 for s in VALIDATION_SEEDS]
        results = run_sweep(tasks, workers, f"validation-{regime}", full=True)
        fname   = f"validation_{regime.lower()}.csv"
        save_csv(results, OUT_DIR / fname)
        val_results[regime] = results
    return val_results


# ── Step 8 — Save selected_ecologies.json ────────────────────────────────────

def step8_save_json(selected: dict) -> None:
    out = {
        "experiment":               "phase3b_calibration",
        "child_survival_possible":  selected["CHILD_SURVIVAL_POSSIBLE"],
        "regimes":                  {},
    }
    for regime in ("VIABLE", "BEST_ECOLOGICAL"):
        cfg = selected.get(regime)
        if cfg is None:
            continue
        out["regimes"][regime] = {
            "infant_starvation_multiplier": cfg["ism"],
            "eat_gain":                     cfg["eat_gain"],
            "init_food":                    cfg["init_food"],
            "move_cost":                    0.005,
            "rest_recovery":                0.005,
            "c_matr":                       cfg["c_matr"],
            "m_surv":                       cfg["m_surv"],
            "child_death_mu":               cfg["child_death_mu"],
        }
    path = OUT_DIR / "selected_ecologies.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Selected ecologies saved: {path}")


# ── Summary table ─────────────────────────────────────────────────────────────

def print_summary(selected: dict) -> None:
    w = 80
    print(f"\n{'='*w}")
    print("Phase 3b Ecological Calibration — Summary")
    print(f"{'='*w}")
    print(f"  Child survival possible with unbiased weights: "
          f"{'YES' if selected['CHILD_SURVIVAL_POSSIBLE'] else 'NO'}")
    print()
    for regime in ("VIABLE", "BEST_ECOLOGICAL"):
        cfg = selected.get(regime)
        if cfg is None:
            print(f"  {regime}: None")
            continue
        print(f"  {regime}:")
        print(f"    ISM={cfg['ism']}, eat_gain={cfg['eat_gain']}, init_food={cfg['init_food']}")
        print(f"    C_matr={cfg['c_matr']:.3f}, M_surv={cfg['m_surv']:.3f}, "
              f"child_death_mu={cfg['child_death_mu']:.1f}")
    print(f"{'='*w}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 3b ecological calibration")
    parser.add_argument("--workers",     type=int, default=4)
    parser.add_argument("--skip_anchor", action="store_true")
    parser.add_argument("--skip_ovat",   action="store_true")
    parser.add_argument("--skip_grid",   action="store_true")
    parser.add_argument("--skip_val",    action="store_true")
    parser.add_argument("--plot_only",   action="store_true",
                        help="Skip all simulation steps, just generate plots from saved CSVs")
    args = parser.parse_args()

    if args.plot_only:
        from experiments.phase3_survival_full.phase3b_calibration.plot import generate_all_plots
        generate_all_plots(OUT_DIR, ovat_results={}, grid_results=[], val_results={}, selected={})
        return

    print("Phase 3b Ecological Calibration")
    print(f"  Research question: can eco pressure alone (weights=1.0) produce child maturation?")
    print(f"  Output directory: {OUT_DIR}")

    # Step 1 — anchor
    if not args.skip_anchor:
        step1_anchor(args.workers)

    # Steps 2-4 — OVAT
    ovat_results = {}
    if not args.skip_ovat:
        ovat_results = step2_4_ovat(args.workers)

    # Step 5 — grid
    grid_results = []
    if not args.skip_grid:
        grid_results = step5_grid(args.workers)

    # Step 6 — regime selection (load from CSV if grid was skipped)
    if not grid_results and (OUT_DIR / "grid_sweep_raw.csv").exists():
        import csv as _csv
        with open(OUT_DIR / "grid_sweep_raw.csv", encoding="utf-8") as f:
            reader = _csv.DictReader(f)
            grid_results = [{k: (float(v) if k not in ("seed",) else int(float(v)))
                             for k, v in row.items()} for row in reader]
        # Re-cast numeric keys
        for r in grid_results:
            for k in ("ism", "eat_gain", "mother_survival", "child_maturation",
                      "feeds", "feeds_per_child", "care_pct", "forage_pct", "self_pct",
                      "child_death_tick_mean"):
                if k in r:
                    r[k] = float(r[k])
            for k in ("init_food", "matured_count", "child_death_tick_min", "child_death_tick_max"):
                if k in r:
                    r[k] = int(float(r[k]))

    selected = step6_select(grid_results) if grid_results else {
        "CHILD_SURVIVAL_POSSIBLE": False,
        "VIABLE": None,
        "BEST_ECOLOGICAL": None,
    }

    # Step 7 — validation
    val_results = {}
    if not args.skip_val and any(v is not None for k, v in selected.items()
                                 if k != "CHILD_SURVIVAL_POSSIBLE"):
        val_results = step7_validate(selected, args.workers)

    # Step 8 — save JSON + plots
    step8_save_json(selected)
    print_summary(selected)

    from experiments.phase3_survival_full.phase3b_calibration.plot import generate_all_plots
    generate_all_plots(OUT_DIR, ovat_results, grid_results, val_results, selected)


if __name__ == "__main__":
    main()
