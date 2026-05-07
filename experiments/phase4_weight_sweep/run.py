# experiments/phase4_weight_sweep/run.py
"""
Phase 4 Motivation Weight Sweep — 7-step standalone pipeline.

Steps:
  1. care_weight threshold scan  — [1.0..4.0] × 5 seeds; find first C_matr > 0
  2-4. OVAT sets A/B/C           — care / forage / self weight (5 seeds each)
  5. Full 2D grid                — care_weight × forage_weight (30 combos × 5 seeds)
  6. Regime selection            — VIABLE (min care_weight with C_matr > 0) + OPTIMAL
  7. Validation                  — 10 seeds × selected configs
  8. Save JSON + plots

Usage:
    python -m experiments.phase4_weight_sweep.run
    python -m experiments.phase4_weight_sweep.run --workers 4
    python -m experiments.phase4_weight_sweep.run --skip_ovat --skip_grid
    python -m experiments.phase4_weight_sweep.run --plot_only
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import csv
import json
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase4_weight_sweep.config import (
    INIT_MOTHERS, MAX_TICKS,
    THRESHOLD_SEEDS, OVAT_SEEDS, GRID_SEEDS, VALIDATION_SEEDS,
    VIABLE_MIN_C_MATR, VIABLE_MIN_M_SURV,
    make_config, expand_threshold, expand_ovat, expand_grid, feeds_needed,
    OVAT_SWEEPS, BEST_ECO,
)

OUT_DIR = PROJECT_ROOT / "outputs" / "phase4_weight_sweep"


# ── Single run — fast summary ──────────────────────────────────────────────────

def run_one(care_weight: float, forage_weight: float, self_weight: float,
            seed: int) -> dict:
    from simulation.simulation import Simulation
    cfg = make_config(care_weight, forage_weight, self_weight, seed)
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

    choices    = sim.logger.choice_records
    n_ch       = len(choices)
    care_pct   = 100 * sum(1 for r in choices if r.winner_domain == "care")   / n_ch if n_ch else 0
    forage_pct = 100 * sum(1 for r in choices if r.winner_domain == "forage") / n_ch if n_ch else 0
    self_pct   = 100 * sum(1 for r in choices if r.winner_domain == "self")   / n_ch if n_ch else 0

    return {
        "care_weight":        care_weight,
        "forage_weight":      forage_weight,
        "self_weight":        self_weight,
        "seed":               seed,
        "mother_survival":    alive_m / INIT_MOTHERS,
        "child_maturation":   matured / INIT_MOTHERS,
        "matured_count":      matured,
        "feeds":              feeds,
        "feeds_per_child":    feeds / INIT_MOTHERS,
        "care_pct":           care_pct,
        "forage_pct":         forage_pct,
        "self_pct":           self_pct,
        "child_death_tick_mean": (sum(death_ticks) / len(death_ticks)
                                  if death_ticks else float(MAX_TICKS)),
        "child_death_tick_min":  min(death_ticks) if death_ticks else MAX_TICKS,
        "child_death_tick_max":  max(death_ticks) if death_ticks else MAX_TICKS,
    }


def _fast_task(args):
    care_weight, forage_weight, self_weight, seed = args
    return run_one(care_weight, forage_weight, self_weight, seed)


# ── Single run — full histories (validation) ──────────────────────────────────

def run_one_full(care_weight: float, forage_weight: float, self_weight: float,
                 seed: int) -> dict:
    from simulation.simulation import Simulation
    cfg = make_config(care_weight, forage_weight, self_weight, seed)
    sim = Simulation(cfg)
    sim.initialize()
    original_mother_ids = {m.id for m in sim.mothers}

    mom_e_h, child_e_h, pop_m_h, pop_c_h = [], [], [], []

    while sim.tick < cfg.max_ticks:
        am = [m for m in sim.mothers  if m.alive]
        ac = [c for c in sim.children if c.alive]
        mom_e_h.append(np.mean([m.energy for m in am]) if am else np.nan)
        child_e_h.append(np.mean([c.energy for c in ac]) if ac else np.nan)
        pop_m_h.append(len(am))
        pop_c_h.append(len(ac))
        sim.step()
        sim.tick += 1

    alive_m  = sum(1 for m in sim.mothers if m.alive and m.id in original_mother_ids)
    matured  = sum(1 for r in sim.logger.death_records
                   if r.agent_type == "child" and r.cause == "matured")
    feeds    = len(sim.logger.care_records)
    hunger_deaths = [r for r in sim.logger.death_records
                     if r.agent_type == "child" and r.cause == "hunger"]
    death_ticks   = [r.tick for r in hunger_deaths]

    return {
        "care_weight":        care_weight,
        "forage_weight":      forage_weight,
        "self_weight":        self_weight,
        "seed":               seed,
        "mother_survival":    alive_m / INIT_MOTHERS,
        "child_maturation":   matured / INIT_MOTHERS,
        "matured_count":      matured,
        "feeds":              feeds,
        "feeds_per_child":    feeds / INIT_MOTHERS,
        "child_death_tick_mean": (sum(death_ticks) / len(death_ticks)
                                  if death_ticks else float(MAX_TICKS)),
        "mother_energy_history": mom_e_h,
        "child_energy_history":  child_e_h,
        "mother_pop_history":    pop_m_h,
        "child_pop_history":     pop_c_h,
    }


def _full_task(args):
    care_weight, forage_weight, self_weight, seed = args
    return run_one_full(care_weight, forage_weight, self_weight, seed)


# ── Aggregation ───────────────────────────────────────────────────────────────

def _mu(rows, key):
    return float(np.mean([r[key] for r in rows]))


def aggregate(rows: list[dict]) -> dict:
    r0 = rows[0]
    return {
        "care_weight":      r0["care_weight"],
        "forage_weight":    r0["forage_weight"],
        "self_weight":      r0["self_weight"],
        "n":                len(rows),
        "m_surv_mean":      _mu(rows, "mother_survival"),
        "c_matr_mean":      _mu(rows, "child_maturation"),
        "matured_total":    sum(r["matured_count"] for r in rows),
        "feeds_mean":       _mu(rows, "feeds"),
        "feeds_per_child":  _mu(rows, "feeds_per_child"),
        "care_pct_mean":    _mu(rows, "care_pct"),
        "forage_pct_mean":  _mu(rows, "forage_pct"),
        "self_pct_mean":    _mu(rows, "self_pct"),
        "child_death_mu":   _mu(rows, "child_death_tick_mean"),
        "child_death_min":  min(r["child_death_tick_min"] for r in rows),
        "child_death_max":  max(r["child_death_tick_max"] for r in rows),
    }


def group_and_aggregate(results: list[dict]) -> list[dict]:
    groups: dict[tuple, list] = {}
    for r in results:
        key = (r["care_weight"], r["forage_weight"], r["self_weight"])
        groups.setdefault(key, []).append(r)
    return [aggregate(rows) for rows in groups.values()]


# ── CSV helpers ───────────────────────────────────────────────────────────────

def save_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
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
    done    = 0
    with ProcessPoolExecutor(max_workers=workers) as exe:
        futs = {exe.submit(fn, t): t for t in tasks}
        for fut in as_completed(futs):
            results.append(fut.result())
            done += 1
            if done % max(1, n // 10) == 0 or done == n:
                print(f"    {done}/{n}", end="\r")
    print(f"    {n}/{n} done")
    return results


# ── Step 1 — care_weight threshold scan ──────────────────────────────────────

def step1_threshold(workers: int) -> list[dict]:
    print("\n[Step 1] care_weight threshold scan  (forage = self = 0.5 fixed)")
    combos  = expand_threshold()
    tasks   = [(c["care_weight"], c["forage_weight"], c["self_weight"], s)
               for c in combos for s in THRESHOLD_SEEDS]
    results = run_sweep(tasks, workers, "threshold")

    agg = group_and_aggregate(results)
    save_csv(results, OUT_DIR / "threshold_raw.csv")
    save_csv(agg,     OUT_DIR / "threshold.csv")

    print(f"\n  {'care_weight':>12} {'C_matr':>8} {'M_surv':>8} "
          f"{'feeds/child':>12} {'CARE%':>7} {'C_death_mu':>11}")
    for a in sorted(agg, key=lambda x: x["care_weight"]):
        print(f"  {a['care_weight']:>12.2f} {a['c_matr_mean']:>8.3f} "
              f"{a['m_surv_mean']:>8.3f} {a['feeds_per_child']:>12.2f} "
              f"{a['care_pct_mean']:>7.1f} {a['child_death_mu']:>11.1f}")

    viable = [a for a in agg if a["c_matr_mean"] > VIABLE_MIN_C_MATR]
    if viable:
        min_cw = min(a["care_weight"] for a in viable)
        print(f"\n  VIABLE threshold: care_weight >= {min_cw}")
    else:
        print("\n  No C_matr > 0 found in threshold scan — extend CARE_WEIGHT_VALUES.")
    return results


# ── Steps 2-4 — OVAT sets ─────────────────────────────────────────────────────

def step2_4_ovat(workers: int) -> dict[str, list[dict]]:
    ovat_results = {}
    label_map = {"A": "care_weight", "B": "forage_weight", "C": "self_weight"}
    for set_key, sw in OVAT_SWEEPS.items():
        step_n = {"A": 2, "B": 3, "C": 4}[set_key]
        print(f"\n[Step {step_n}] OVAT Set {set_key} — sweep {sw['label']}")
        combos  = expand_ovat(set_key)
        tasks   = [(c["care_weight"], c["forage_weight"], c["self_weight"], s)
                   for c in combos for s in OVAT_SEEDS]
        results = run_sweep(tasks, workers, f"OVAT-{set_key}")
        agg     = group_and_aggregate(results)
        fname   = {
            "A": "ovat_set_A_care_weight",
            "B": "ovat_set_B_forage_weight",
            "C": "ovat_set_C_self_weight",
        }[set_key]
        save_csv(results, OUT_DIR / f"{fname}_raw.csv")
        save_csv(agg,     OUT_DIR / f"{fname}.csv")
        ovat_results[set_key] = results

        col = label_map[set_key]
        print(f"\n  Set {set_key} results:")
        print(f"  {sw['label']:>14} {'C_matr':>8} {'M_surv':>8} "
              f"{'CARE%':>7} {'C_death_mu':>11}")
        for a in sorted(agg, key=lambda x: x[col]):
            print(f"  {a[col]:>14.2f} {a['c_matr_mean']:>8.3f} "
                  f"{a['m_surv_mean']:>8.3f} {a['care_pct_mean']:>7.1f} "
                  f"{a['child_death_mu']:>11.1f}")
    return ovat_results


# ── Step 5 — Full 2D grid ─────────────────────────────────────────────────────

def step5_grid(workers: int) -> list[dict]:
    print("\n[Step 5] Full 2D grid — care_weight × forage_weight  (self = 0.5 fixed)")
    combos = expand_grid()
    tasks  = [(c["care_weight"], c["forage_weight"], c["self_weight"], s)
              for c in combos for s in GRID_SEEDS]
    print(f"  {len(combos)} combos × {len(GRID_SEEDS)} seeds = {len(tasks)} runs")
    results = run_sweep(tasks, workers, "grid")
    agg     = group_and_aggregate(results)
    save_csv(results, OUT_DIR / "grid_sweep_raw.csv")
    save_csv(agg,     OUT_DIR / "grid_sweep.csv")

    viable = [a for a in agg if a["c_matr_mean"] > VIABLE_MIN_C_MATR]
    print(f"\n  Grid: {len(agg)} combos, {len(viable)} with C_matr > 0")
    if viable:
        best = max(viable, key=lambda x: (x["c_matr_mean"], x["m_surv_mean"]))
        print(f"  Best: care_weight={best['care_weight']}, "
              f"forage_weight={best['forage_weight']}, "
              f"C_matr={best['c_matr_mean']:.3f}, M_surv={best['m_surv_mean']:.3f}")
    return results


# ── Step 5b — Self-weight refinement at grid OPTIMAL ─────────────────────────

def step5b_self(grid_results: list[dict], workers: int) -> list[dict]:
    """Sweep self_weight at the grid-optimal (care, forage) to validate self=0.5."""
    if not grid_results:
        print("\n[Step 5b] Skipped — no grid results available")
        return []

    agg = group_and_aggregate(grid_results)
    viable = [a for a in agg
              if a["c_matr_mean"] > VIABLE_MIN_C_MATR
              and a["m_surv_mean"] >= VIABLE_MIN_M_SURV]
    if not viable:
        print("\n[Step 5b] Skipped — no viable grid combos")
        return []

    best = max(viable, key=lambda x: x["c_matr_mean"] * x["m_surv_mean"])
    cw, fw = best["care_weight"], best["forage_weight"]
    self_values = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]

    print(f"\n[Step 5b] Self-weight refinement at care={cw}, forage={fw}")
    tasks = [(cw, fw, sw, s) for sw in self_values for s in GRID_SEEDS]
    results = run_sweep(tasks, workers, "self-refinement")
    agg_self = group_and_aggregate(results)
    save_csv(results, OUT_DIR / "self_refinement_raw.csv")
    save_csv(agg_self, OUT_DIR / "self_refinement.csv")

    print(f"\n  {'self_weight':>12} {'C_matr':>8} {'M_surv':>8} {'joint':>8}")
    for a in sorted(agg_self, key=lambda x: x["self_weight"]):
        joint = a["c_matr_mean"] * a["m_surv_mean"]
        print(f"  {a['self_weight']:>12.2f} {a['c_matr_mean']:>8.3f} "
              f"{a['m_surv_mean']:>8.3f} {joint:>8.3f}")
    return results


# ── Step 6 — Regime selection ─────────────────────────────────────────────────

def step6_select(threshold_results: list[dict],
                 grid_results: list[dict],
                 self_results: list[dict] | None = None) -> dict:
    print("\n[Step 6] Regime selection")

    # VIABLE_MIN: lowest care_weight (forage=self=1.0) with C_matr > 0
    thresh_agg = group_and_aggregate(threshold_results)
    viable_thresh = [a for a in thresh_agg
                     if a["c_matr_mean"] > VIABLE_MIN_C_MATR
                     and a["m_surv_mean"] >= VIABLE_MIN_M_SURV]

    # OPTIMAL: best C_matr × M_surv across full grid
    grid_agg = group_and_aggregate(grid_results) if grid_results else []
    viable_grid = [a for a in grid_agg
                   if a["c_matr_mean"] > VIABLE_MIN_C_MATR
                   and a["m_surv_mean"] >= VIABLE_MIN_M_SURV]

    selected = {"CHILD_MATURATION_POSSIBLE": len(viable_thresh) > 0}

    if viable_thresh:
        vmin = min(viable_thresh, key=lambda x: x["care_weight"])
        selected["VIABLE_MIN"] = {
            "care_weight":   vmin["care_weight"],
            "forage_weight": vmin["forage_weight"],
            "self_weight":   vmin["self_weight"],
            "c_matr":        vmin["c_matr_mean"],
            "m_surv":        vmin["m_surv_mean"],
            "child_death_mu": vmin["child_death_mu"],
        }
        print(f"  VIABLE_MIN: care_weight={vmin['care_weight']}, "
              f"C_matr={vmin['c_matr_mean']:.3f}, M_surv={vmin['m_surv_mean']:.3f}")
    else:
        selected["VIABLE_MIN"] = None
        print("  VIABLE_MIN: None — no care_weight produced C_matr > 0 with M_surv >= 0.10")
        print("  -> Consider extending CARE_WEIGHT_VALUES range.")

    if viable_grid:
        # Step 1: find best (care, forage) from 2D grid by joint fitness
        opt = max(viable_grid, key=lambda x: x["c_matr_mean"] * x["m_surv_mean"])

        # Step 2: if Step 5b self-refinement ran, find best self_weight at that point
        best_self = opt["self_weight"]  # default = 0.5
        if self_results:
            self_agg = group_and_aggregate(self_results)
            self_viable = [a for a in self_agg
                           if a["c_matr_mean"] > VIABLE_MIN_C_MATR
                           and a["m_surv_mean"] >= VIABLE_MIN_M_SURV]
            if self_viable:
                best_self_row = max(self_viable,
                                    key=lambda x: x["c_matr_mean"] * x["m_surv_mean"])
                best_self = best_self_row["self_weight"]
                print(f"  Self refinement: best self_weight={best_self} "
                      f"(joint={best_self_row['c_matr_mean']*best_self_row['m_surv_mean']:.3f})")

        selected["OPTIMAL"] = {
            "care_weight":   opt["care_weight"],
            "forage_weight": opt["forage_weight"],
            "self_weight":   best_self,
            "c_matr":        opt["c_matr_mean"],
            "m_surv":        opt["m_surv_mean"],
            "child_death_mu": opt["child_death_mu"],
        }
        joint = opt["c_matr_mean"] * opt["m_surv_mean"]
        print(f"  OPTIMAL:    care={opt['care_weight']}, forage={opt['forage_weight']}, "
              f"self={best_self},  C_matr={opt['c_matr_mean']:.3f}, "
              f"M_surv={opt['m_surv_mean']:.3f},  joint={joint:.3f}")
    else:
        # Fall back to best child_death_mu from threshold scan
        fallback = max(thresh_agg, key=lambda x: (x["child_death_mu"], x["m_surv_mean"]))
        selected["OPTIMAL"] = {
            "care_weight":   fallback["care_weight"],
            "forage_weight": fallback["forage_weight"],
            "self_weight":   fallback["self_weight"],
            "c_matr":        fallback["c_matr_mean"],
            "m_surv":        fallback["m_surv_mean"],
            "child_death_mu": fallback["child_death_mu"],
        }
        print(f"  OPTIMAL (fallback best child longevity): "
              f"care_weight={fallback['care_weight']}, "
              f"child_death_mu={fallback['child_death_mu']:.1f}")

    return selected


# ── Step 7 — Validation ───────────────────────────────────────────────────────

def step7_validate(selected: dict, workers: int) -> dict[str, list[dict]]:
    print("\n[Step 7] Validation — 10 seeds per selected config")
    val_results = {}
    for regime, cfg in selected.items():
        if regime == "CHILD_MATURATION_POSSIBLE" or cfg is None:
            continue
        print(f"  Validating {regime}: care_weight={cfg['care_weight']}, "
              f"forage_weight={cfg['forage_weight']}")
        tasks = [
            (cfg["care_weight"], cfg["forage_weight"], cfg["self_weight"], s)
            for s in VALIDATION_SEEDS
        ]
        results = run_sweep(tasks, workers, f"validation-{regime}", full=True)
        save_csv(results, OUT_DIR / f"validation_{regime.lower()}.csv")
        val_results[regime] = results
    return val_results


# ── Step 8 — Save JSON ────────────────────────────────────────────────────────

def step8_save_json(selected: dict) -> None:
    out = {
        "experiment":                "phase4_weight_sweep",
        "child_maturation_possible": selected["CHILD_MATURATION_POSSIBLE"],
        "ecological_baseline":       BEST_ECO,
        "regimes":                   {},
    }
    for regime in ("VIABLE_MIN", "OPTIMAL"):
        cfg = selected.get(regime)
        if cfg is None:
            continue
        out["regimes"][regime] = {
            "care_weight":   cfg["care_weight"],
            "forage_weight": cfg["forage_weight"],
            "self_weight":   cfg["self_weight"],
            "c_matr":        cfg["c_matr"],
            "m_surv":        cfg["m_surv"],
            "child_death_mu": cfg["child_death_mu"],
        }
    path = OUT_DIR / "selected_weights.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Selected weights saved: {path}")


# ── Summary table ─────────────────────────────────────────────────────────────

def print_summary(selected: dict) -> None:
    w = 80
    print(f"\n{'='*w}")
    print("Phase 4 Motivation Weight Sweep — Summary")
    print(f"{'='*w}")
    possible = selected["CHILD_MATURATION_POSSIBLE"]
    print(f"  Child maturation possible with motivational bias: "
          f"{'YES' if possible else 'NO'}")
    print()
    for regime in ("VIABLE_MIN", "OPTIMAL"):
        cfg = selected.get(regime)
        if cfg is None:
            print(f"  {regime}: None")
            continue
        print(f"  {regime}:")
        print(f"    care_weight={cfg['care_weight']}, "
              f"forage_weight={cfg['forage_weight']}, "
              f"self_weight={cfg['self_weight']}")
        print(f"    C_matr={cfg['c_matr']:.3f}, M_surv={cfg['m_surv']:.3f}, "
              f"child_death_mu={cfg['child_death_mu']:.1f}")
    feeds_th = feeds_needed(
        BEST_ECO["infant_starvation_multiplier"], BEST_ECO["eat_gain"]
    )
    print(f"\n  Theoretical feeds needed (ISM={BEST_ECO['infant_starvation_multiplier']}, "
          f"eat_gain={BEST_ECO['eat_gain']}): {feeds_th:.1f}")
    print(f"{'='*w}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 4 motivation weight sweep")
    parser.add_argument("--workers",        type=int, default=4)
    parser.add_argument("--skip_threshold", action="store_true")
    parser.add_argument("--skip_ovat",      action="store_true")
    parser.add_argument("--skip_grid",      action="store_true")
    parser.add_argument("--skip_self",      action="store_true",
                        help="Skip Step 5b self-weight refinement")
    parser.add_argument("--skip_val",       action="store_true")
    parser.add_argument("--plot_only",      action="store_true",
                        help="Skip all simulation steps, just generate plots from saved CSVs")
    args = parser.parse_args()

    if args.plot_only:
        from experiments.phase4_weight_sweep.plot import generate_all_plots
        generate_all_plots(OUT_DIR, ovat_results={}, threshold_results=[],
                           grid_results=[], val_results={}, selected={})
        return

    print("Phase 4 Motivation Weight Sweep")
    print(f"  Research question: minimum care_weight bias to enable child maturation")
    print(f"  Ecological baseline: ISM={BEST_ECO['infant_starvation_multiplier']}, "
          f"eat_gain={BEST_ECO['eat_gain']}, init_food={BEST_ECO['init_food']}")
    print(f"  Output directory: {OUT_DIR}")

    # Step 1 — threshold scan
    threshold_results = []
    if not args.skip_threshold:
        threshold_results = step1_threshold(args.workers)

    # Steps 2-4 — OVAT
    ovat_results = {}
    if not args.skip_ovat:
        ovat_results = step2_4_ovat(args.workers)

    # Step 5 — grid
    grid_results = []
    if not args.skip_grid:
        grid_results = step5_grid(args.workers)

    # Step 5b — self-weight refinement at grid optimal
    self_results = []
    if not args.skip_self:
        self_results = step5b_self(grid_results, args.workers)

    # Load from CSV if steps were skipped
    def _load_raw(fname):
        path = OUT_DIR / fname
        if not path.exists():
            return []
        import csv as _csv
        with open(path, encoding="utf-8") as f:
            rows = list(_csv.DictReader(f))
        cast = []
        for row in rows:
            r = {}
            for k, v in row.items():
                try:
                    r[k] = float(v)
                except (ValueError, TypeError):
                    r[k] = v
            for ki in ("matured_count", "child_death_tick_min", "child_death_tick_max"):
                if ki in r:
                    r[ki] = int(r[ki])
            cast.append(r)
        return cast

    if not threshold_results:
        threshold_results = _load_raw("threshold_raw.csv")
    if not grid_results:
        grid_results = _load_raw("grid_sweep_raw.csv")
    if not self_results:
        self_results = _load_raw("self_refinement_raw.csv")

    selected = step6_select(threshold_results, grid_results, self_results)

    # Step 7 — validation
    val_results = {}
    if not args.skip_val and any(
        v is not None for k, v in selected.items()
        if k != "CHILD_MATURATION_POSSIBLE"
    ):
        val_results = step7_validate(selected, args.workers)

    # Step 8 — save JSON + plots
    step8_save_json(selected)
    print_summary(selected)

    from experiments.phase4_weight_sweep.plot import generate_all_plots
    generate_all_plots(OUT_DIR, ovat_results, threshold_results, grid_results,
                       val_results, selected)


if __name__ == "__main__":
    main()
