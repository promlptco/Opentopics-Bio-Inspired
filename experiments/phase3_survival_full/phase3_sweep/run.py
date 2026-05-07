# experiments/phase3_sweep/run.py
"""
Phase 3 init_food Sensitivity Sweep.

Sweeps init_food across 7 values x 10 seeds = 70 runs.
Reports mother survival, child maturation, feeds, and action distribution.

Usage:
    python -m experiments.phase3_survival_full.phase3_sweep.run
    python -m experiments.phase3_survival_full.phase3_sweep.run --baseline percept15
    python -m experiments.phase3_survival_full.phase3_sweep.run --workers 4
    python -m experiments.phase3_survival_full.phase3_sweep.run --workers 1   # for debugging
"""
import argparse
import csv
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase3_survival_full.phase3_sweep.config import (
    INIT_FOOD_VALUES, SWEEP_SEEDS,
    MOTHER_SURVIVAL_MIN, CHILD_MATURATION_MIN,
    load_sweep_config,
)


# ── Single run ────────────────────────────────────────────────────────────────

def run_one(init_food: int, seed: int, baseline: str) -> dict:
    from simulation.simulation import Simulation
    cfg = load_sweep_config(init_food, seed, baseline)
    sim = Simulation(cfg)
    sim.run()

    alive_m = sum(1 for m in sim.mothers if m.alive)
    matured = sum(1 for r in sim.logger.death_records
                  if r.agent_type == "child" and r.cause == "matured")
    feeds   = len(sim.logger.care_records)

    choices    = sim.logger.choice_records
    n_choices  = len(choices)
    care_pct   = 100 * sum(1 for r in choices if r.winner_domain == "care")   / n_choices if n_choices else 0
    forage_pct = 100 * sum(1 for r in choices if r.winner_domain == "forage") / n_choices if n_choices else 0
    self_pct   = 100 * sum(1 for r in choices if r.winner_domain == "self")   / n_choices if n_choices else 0

    hunger_deaths = [r for r in sim.logger.death_records
                     if r.agent_type == "child" and r.cause == "hunger"]
    death_ticks   = [r.tick for r in hunger_deaths]

    return {
        "init_food":             init_food,
        "seed":                  seed,
        "mother_survival":       alive_m / cfg.init_mothers,
        "child_maturation":      matured / cfg.init_mothers,
        "matured_count":         matured,
        "feeds":                 feeds,
        "care_pct":              care_pct,
        "forage_pct":            forage_pct,
        "self_pct":              self_pct,
        "child_death_tick_mean": sum(death_ticks) / len(death_ticks) if death_ticks else 400.0,
        "child_death_tick_min":  min(death_ticks) if death_ticks else 400,
        "child_death_tick_max":  max(death_ticks) if death_ticks else 400,
    }


def _task(args):
    init_food, seed, baseline = args
    return run_one(init_food, seed, baseline)


# ── Aggregation helper ────────────────────────────────────────────────────────

def _mean(lst):
    return sum(lst) / len(lst) if lst else 0.0


def aggregate(results: list[dict], init_food: int) -> dict:
    rows = [r for r in results if r["init_food"] == init_food]
    return {
        "init_food":             init_food,
        "n":                     len(rows),
        "mother_survival_mean":  _mean([r["mother_survival"]       for r in rows]),
        "child_maturation_mean": _mean([r["child_maturation"]      for r in rows]),
        "matured_total":         sum(r["matured_count"]            for r in rows),
        "feeds_mean":            _mean([r["feeds"]                  for r in rows]),
        "care_pct_mean":         _mean([r["care_pct"]               for r in rows]),
        "forage_pct_mean":       _mean([r["forage_pct"]             for r in rows]),
        "self_pct_mean":         _mean([r["self_pct"]               for r in rows]),
        "child_death_mu":        _mean([r["child_death_tick_mean"]  for r in rows]),
        "child_death_min":       min(r["child_death_tick_min"]      for r in rows),
        "child_death_max":       max(r["child_death_tick_max"]      for r in rows),
    }


# ── Output ────────────────────────────────────────────────────────────────────

def print_summary(agg_rows: list[dict], baseline: str) -> None:
    w = 90
    print(f"\n{'='*w}")
    print(f"Phase 3 Sensitivity Sweep — init_food  ({baseline} BALANCED, ISM=2.33, weights=1.0)")
    print(f"{'='*w}")
    print(f"{'food':>5} | {'M_surv':>7} | {'C_matr':>7} | {'C_mat#':>6} | "
          f"{'Feeds':>6} | {'CARE%':>5} | {'FOR%':>5} | {'SELF%':>5} | "
          f"{'C_mu':>5} | {'C_rng':>12} | {'Viable':>6}")
    print(f"{'-'*w}")

    viable = []
    for a in agg_rows:
        is_viable = (a["mother_survival_mean"] >= MOTHER_SURVIVAL_MIN
                     and a["child_maturation_mean"] > CHILD_MATURATION_MIN)
        if is_viable:
            viable.append(a["init_food"])
        flag = "YES" if is_viable else ""
        rng  = f"{a['child_death_min']}-{a['child_death_max']}"
        print(f"  {a['init_food']:>3} | {a['mother_survival_mean']:>7.3f} | "
              f"{a['child_maturation_mean']:>7.3f} | {a['matured_total']:>6} | "
              f"{a['feeds_mean']:>6.0f} | {a['care_pct_mean']:>5.1f} | "
              f"{a['forage_pct_mean']:>5.1f} | {a['self_pct_mean']:>5.1f} | "
              f"{a['child_death_mu']:>5.1f} | {rng:>12} | {flag:>6}")

    print()
    if viable:
        print(f"Viable configs (M_surv>={MOTHER_SURVIVAL_MIN}, C_matr>0): "
              f"init_food in {viable}")
        print(f"Minimum viable init_food: {min(viable)}")
    else:
        print("No viable configs found — no init_food value produced child maturation.")
        print("Consider extending the upper bound or reviewing other parameters.")
    print()


def save_csv(results: list[dict], path: Path) -> None:
    if not results:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"Raw results saved to: {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 3 init_food sensitivity sweep")
    parser.add_argument("--baseline", type=str, default="percept8",
                        choices=["percept8", "percept15"],
                        help="Phase 2 ecology baseline to use (default: percept8)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel worker processes (default 4)")
    parser.add_argument("--no_save", action="store_true",
                        help="Skip saving CSV output")
    args = parser.parse_args()

    tasks = [(f, s, args.baseline) for f in INIT_FOOD_VALUES for s in SWEEP_SEEDS]
    n_total = len(tasks)
    print(f"Phase 3 init_food sweep [{args.baseline}]: {len(INIT_FOOD_VALUES)} values x "
          f"{len(SWEEP_SEEDS)} seeds = {n_total} runs  (workers={args.workers})")
    print(f"init_food values: {INIT_FOOD_VALUES}")
    print(f"Seeds: {SWEEP_SEEDS[0]}–{SWEEP_SEEDS[-1]}")

    results = []
    completed = 0
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(_task, t): t for t in tasks}
        for fut in as_completed(futures):
            results.append(fut.result())
            completed += 1
            if completed % 10 == 0 or completed == n_total:
                print(f"  {completed}/{n_total} done", end="\r")

    print(f"  {n_total}/{n_total} done")

    agg_rows = [aggregate(results, f) for f in INIT_FOOD_VALUES]
    print_summary(agg_rows, args.baseline)

    if not args.no_save:
        out_dir = PROJECT_ROOT / "outputs" / "phase3_survival_full" / "phase3_sweep" / args.baseline
        save_csv(results, out_dir / "raw_results.csv")


if __name__ == "__main__":
    main()
