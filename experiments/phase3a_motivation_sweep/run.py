# experiments/phase3a_motivation_sweep/run.py
"""
Phase 3a — Motivation Sweep

Sweeps care_w × forage_w × self_w over the BALANCED Phase 2 ecology.
Selects the canonical fixed genome for Phase 3b+.

Usage
-----
# Coarse grid (default: 6×6×6 = 216 combos)
python -m experiments.phase3a_motivation_sweep.run --seeds 15 --workers 8

# Fine grid (11×11×11 = 1331 combos)
python -m experiments.phase3a_motivation_sweep.run --seeds 15 --workers 8 --grid fine
"""
import argparse
import csv
import dataclasses
import itertools
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from simulation.simulation import Simulation
from experiments.phase3a_motivation_sweep.config import (
    load_balanced_config,
    GRID_VALS,
    CHILD_SURVIVAL_MIN,
    MOTHER_SURVIVAL_MIN,
    MOTHER_ENERGY_MIN,
    CARE_CHOICE_MIN,
)


# ── Single run ────────────────────────────────────────────────────────────────

def run_one(care_w: float, forage_w: float, self_w: float, seed: int, base_config: Config) -> dict:
    config = dataclasses.replace(
        base_config,
        care_weight=care_w,
        forage_weight=forage_w,
        self_weight=self_w,
        seed=seed,
    )

    sim = Simulation(config)
    sim.run()

    # Mother metrics
    alive_mothers = [m for m in sim.mothers if m.alive]
    mother_survival_rate = len(alive_mothers) / config.init_mothers
    mean_mother_energy = (
        sum(m.energy for m in alive_mothers) / len(alive_mothers)
    ) if alive_mothers else 0.0

    # Child survival rate — denominator is init_mothers (one child spawned per mother,
    # reproduction OFF, so no new births; birth_records is always empty in Phase 3a)
    child_deaths = [r for r in sim.logger.death_records if r.agent_type == "child"]
    matured = sum(1 for r in child_deaths if r.cause == "matured")
    child_survival_rate = matured / config.init_mothers

    # Mean child final energy — energy at the moment of maturation or starvation
    mean_child_final_energy = (
        sum(r.final_energy for r in child_deaths) / len(child_deaths)
    ) if child_deaths else 0.0

    # Care activity: ChoiceRecord is logged when a distressed child is visible
    total_choices = len(sim.logger.choice_records)
    care_choices = sum(1 for r in sim.logger.choice_records if r.winner_domain == "care")
    care_choice_rate = care_choices / total_choices if total_choices > 0 else 0.0

    # Feed success rate
    total_feeds = len(sim.logger.care_records)
    feed_success = sum(1 for r in sim.logger.care_records if r.success)
    feed_success_rate = feed_success / total_feeds if total_feeds > 0 else 0.0

    return {
        "care_w": round(care_w, 2),
        "forage_w": round(forage_w, 2),
        "self_w": round(self_w, 2),
        "seed": seed,
        "mother_survival_rate": round(mother_survival_rate, 4),
        "child_survival_rate": round(child_survival_rate, 4),
        "mean_mother_energy": round(mean_mother_energy, 4),
        "mean_child_final_energy": round(mean_child_final_energy, 4),
        "care_choice_rate": round(care_choice_rate, 4),
        "feed_success_rate": round(feed_success_rate, 4),
    }


# ── Sweep ─────────────────────────────────────────────────────────────────────

def sweep(vals: list[float], seeds: int, workers: int, base_config: Config) -> list[dict]:
    tasks = [
        (c, f, s, seed, base_config)
        for c, f, s in itertools.product(vals, vals, vals)
        for seed in range(seeds)
    ]
    total = len(tasks)
    results = []

    if workers == 1:
        for i, task in enumerate(tasks, 1):
            results.append(run_one(*task))
            if i % 50 == 0 or i == total:
                print(f"  {i}/{total}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(run_one, *task): task for task in tasks}
            done = 0
            for fut in as_completed(futures):
                results.append(fut.result())
                done += 1
                if done % 50 == 0 or done == total:
                    print(f"  {done}/{total}", flush=True)

    return results


# ── Aggregate across seeds ────────────────────────────────────────────────────

def aggregate(results: list[dict]) -> list[dict]:
    buckets = defaultdict(list)
    for r in results:
        buckets[(r["care_w"], r["forage_w"], r["self_w"])].append(r)

    agg = []
    metric_keys = [
        "mother_survival_rate", "child_survival_rate",
        "mean_mother_energy", "mean_child_final_energy",
        "care_choice_rate", "feed_success_rate",
    ]
    for (care_w, forage_w, self_w), rows in sorted(buckets.items()):
        n = len(rows)
        entry = {"care_w": care_w, "forage_w": forage_w, "self_w": self_w, "n_seeds": n}
        for k in metric_keys:
            entry[k] = round(sum(r[k] for r in rows) / n, 4)
        agg.append(entry)

    return agg


# ── Canonical genome selection ────────────────────────────────────────────────

def select_canonical(agg: list[dict]) -> dict | None:
    """Apply ROADMAPS selection criteria in strict order (6 rules)."""
    passing = [
        r for r in agg
        if r["child_survival_rate"] > CHILD_SURVIVAL_MIN      # 1
        and r["mother_survival_rate"] >= MOTHER_SURVIVAL_MIN  # 2
        and r["mean_mother_energy"] > MOTHER_ENERGY_MIN       # 3
        and r["care_choice_rate"] > CARE_CHOICE_MIN           # 4
    ]
    if not passing:
        return None
    # 5. Lowest care_w  |  6. tie-break: highest mean_mother_energy
    return min(passing, key=lambda r: (r["care_w"], -r["mean_mother_energy"]))


# ── I/O helpers ───────────────────────────────────────────────────────────────

def save_csv(rows: list[dict], path: str) -> None:
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3a — Motivation Sweep")
    parser.add_argument("--seeds", type=int, default=15,
                        help="Independent seeds per genome combination (default 15)")
    parser.add_argument("--duration", type=int, default=400,
                        help="Ticks per run (default 400 — covers maturity_age=200)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers (0 = auto, 1 = sequential)")
    parser.add_argument("--grid", choices=["coarse", "fine"], default="coarse",
                        help="coarse = 6×6×6 = 216 combos (default); fine = 11×11×11 = 1331")
    args = parser.parse_args()

    if args.workers == 0:
        import os as _os
        args.workers = _os.cpu_count() or 1

    base_config = load_balanced_config()
    base_config = dataclasses.replace(base_config, max_ticks=args.duration)
    vals = GRID_VALS[args.grid]
    n_combos = len(vals) ** 3
    total_runs = n_combos * args.seeds

    print("=" * 60)
    print("Phase 3a — Motivation Sweep")
    print(f"  Grid    : {args.grid}  ({n_combos} combos × {args.seeds} seeds = {total_runs} runs)")
    print(f"  Duration: {args.duration} ticks")
    print(f"  Workers : {args.workers}")
    print("=" * 60)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = (
        PROJECT_ROOT
        / f"outputs/phase3a_motivation_sweep"
        / f"{ts}_{args.grid}_{args.seeds}seeds"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\nStep 1 — Running sweep...")
    raw = sweep(vals, args.seeds, args.workers, base_config)
    save_csv(raw, str(out_dir / "sweep_raw.csv"))
    print(f"  Raw results saved ({len(raw)} rows)")

    print("\nStep 2 — Aggregating across seeds...")
    agg = aggregate(raw)
    save_csv(agg, str(out_dir / "sweep_results.csv"))
    print(f"  Aggregated results saved ({len(agg)} rows)")

    print("\nStep 3 — Selecting canonical genome...")
    canonical = select_canonical(agg)
    if canonical:
        print(f"  care_w={canonical['care_w']}  forage_w={canonical['forage_w']}  self_w={canonical['self_w']}")
        print(f"  child_survival={canonical['child_survival_rate']:.3f}"
              f"  mother_survival={canonical['mother_survival_rate']:.3f}"
              f"  mean_mother_energy={canonical['mean_mother_energy']:.3f}"
              f"  care_choice_rate={canonical['care_choice_rate']:.3f}")
        with open(out_dir / "canonical_genome.json", "w") as f:
            json.dump(canonical, f, indent=2)
    else:
        print("  WARNING: No genome passed all selection criteria.")

    print("\nStep 4 — Generating plots...")
    from experiments.phase3a_motivation_sweep.plot import plot_all
    plot_all(agg, canonical, str(out_dir))
    print(f"  Plots saved to {out_dir}")

    print(f"\nDone. Outputs: {out_dir}")


if __name__ == "__main__":
    main()
