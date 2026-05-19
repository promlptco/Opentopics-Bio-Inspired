"""Phase 4c — Ecological Viability Screen.

Sweeps ecology_relaxation_factor × infant_starvation_multiplier (ISM) to find
the tightest ecology where Block 2 populations remain viable past tick 6 000.

Grid : 4 relax factors × 3 ISM values = 12 cells
       5 seeds per cell, 6 000 ticks, mut_on_plast_off only

Per-cell metrics
  SVR     Seed Viability Rate — fraction of seeds with n_mothers > 3 at T_end
  G_depth mean highest_generation across seeds at T_end
  PSC     Population Stability Coefficient — std/mean of n_mothers, ticks 2000–T_end

Lock rule: tightest cell (lowest relax_factor, highest ISM) where
  SVR >= 0.60 AND G_depth >= 10 AND PSC < 0.50
"""

from __future__ import annotations

import argparse
import csv
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np

from evolution.genome import Genome
from experiments.phase5_evolution.config import Phase5ConfigFactory
from simulation.simulation import Simulation


# ---------------------------------------------------------------------------
# Grid constants
# ---------------------------------------------------------------------------

RELAX_FACTORS: list[float] = [1.0, 1.5, 2.0, 3.0]
ISM_VALUES: list[float] = [1.0, 0.7, 0.5]
SEEDS_PER_CELL: int = 5
MAX_TICKS: int = 6_000
STABILITY_START: int = 2_000
SNAPSHOT_INTERVAL: int = 50
MIN_FINAL_POP: int = 3

SVR_MIN: float = 0.60
G_DEPTH_MIN: float = 10.0
PSC_MAX: float = 0.50


# ---------------------------------------------------------------------------
# Worker (top-level for multiprocessing pickling)
# ---------------------------------------------------------------------------

def _cell_seed_worker(args: tuple) -> dict:
    """Run one seed for one grid cell. Returns per-seed metrics dict."""
    relax_factor, ism, seed, max_ticks, stability_start = args

    cfg = Phase5ConfigFactory.make(
        seed=seed,
        mutation_enabled=True,
        plasticity_enabled=False,
        learning_rate=0.5,
        plasticity_coefficient=0.5,
        mutation_rate=0.05,
        mutation_sigma=0.02,
        max_ticks=max_ticks,
        infant_starvation_multiplier=ism,
    )
    eco = Phase5ConfigFactory.load_ecology()
    cfg.init_food = int(eco.get("init_food", Phase5ConfigFactory._FALLBACK["init_food"]) * relax_factor)

    genomes = [
        Genome(
            care_weight=1 / 3,
            forage_weight=1 / 3,
            self_weight=1 / 3,
            learning_rate=0.5,
            plasticity_coefficient=0.5,
        )
        for _ in range(cfg.init_mothers)
    ]

    sim = Simulation(cfg)
    sim.initialize(genomes=genomes)

    pop_over_time: list[tuple[int, int]] = []
    final_tick = 0

    for tick in range(max_ticks):
        sim.step()
        final_tick = tick

        if tick % SNAPSHOT_INTERVAL == 0:
            pop_over_time.append((tick, len(sim.mothers)))

        if not sim.mothers:
            break

    final_pop = len(sim.mothers)
    generations = [m.generation for m in sim.mothers] if sim.mothers else [0]
    highest_gen = int(max(generations)) if generations else 0

    stability_pops = [n for t, n in pop_over_time if t >= stability_start]
    mean_pop = float(np.mean(stability_pops)) if stability_pops else 0.0
    psc = float(np.std(stability_pops) / mean_pop) if mean_pop > 0 else 9.99

    return {
        "relax_factor": relax_factor,
        "ism": ism,
        "seed": seed,
        "final_tick": final_tick,
        "final_pop": final_pop,
        "survived": final_pop > MIN_FINAL_POP,
        "highest_gen": highest_gen,
        "psc": psc,
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class EcoExploreRunner:
    """Runs the Phase 4c ecological viability screen."""

    def __init__(
        self,
        relax_factors: list[float] = RELAX_FACTORS,
        ism_values: list[float] = ISM_VALUES,
        seeds_per_cell: int = SEEDS_PER_CELL,
        max_ticks: int = MAX_TICKS,
        stability_start: int = STABILITY_START,
        workers: int = 4,
    ) -> None:
        self._relax_factors = relax_factors
        self._ism_values = ism_values
        self._seeds_per_cell = seeds_per_cell
        self._max_ticks = max_ticks
        self._stability_start = stability_start
        self._workers = workers

    def run(self, output_dir: Path) -> list[dict]:
        """Run all cells and return per-cell aggregated results."""
        output_dir.mkdir(parents=True, exist_ok=True)

        seed_base = 42
        jobs: list[tuple] = [
            (rf, ism, seed_base + i, self._max_ticks, self._stability_start)
            for rf in self._relax_factors
            for ism in self._ism_values
            for i in range(self._seeds_per_cell)
        ]

        n_cells = len(self._relax_factors) * len(self._ism_values)
        print(f"[eco-explore] {len(jobs)} seed runs across {n_cells} cells")

        seed_results: list[dict] = []
        with ProcessPoolExecutor(max_workers=self._workers) as executor:
            futures = {executor.submit(_cell_seed_worker, job): job for job in jobs}
            for future in as_completed(futures):
                rf, ism, seed = futures[future][:3]
                try:
                    seed_results.append(future.result())
                    print(f"  [ok] relax={rf} ISM={ism} seed={seed}")
                except Exception as exc:
                    print(f"  [fail] relax={rf} ISM={ism} seed={seed}: {exc}")

        cell_results = self._aggregate(seed_results)
        self._save(cell_results, seed_results, output_dir)
        return cell_results

    def _aggregate(self, seed_results: list[dict]) -> list[dict]:
        cells: dict[tuple, list[dict]] = {}
        for r in seed_results:
            cells.setdefault((r["relax_factor"], r["ism"]), []).append(r)

        aggregated: list[dict] = []
        for (rf, ism), results in sorted(cells.items()):
            svr = sum(1 for r in results if r["survived"]) / len(results)
            g_depth = float(np.mean([r["highest_gen"] for r in results]))
            psc_vals = [r["psc"] for r in results if r["psc"] < 9.0]
            psc = float(np.mean(psc_vals)) if psc_vals else 9.99
            passes = svr >= SVR_MIN and g_depth >= G_DEPTH_MIN and psc < PSC_MAX

            aggregated.append({
                "relax_factor": rf,
                "ism": ism,
                "svr": round(svr, 3),
                "g_depth": round(g_depth, 2),
                "psc": round(psc, 3),
                "passes": passes,
                "n_seeds": len(results),
            })

        return aggregated

    def lock_best(self, cell_results: list[dict]) -> dict | None:
        """Tightest passing cell: lowest relax_factor, then highest ISM."""
        passing = [c for c in cell_results if c["passes"]]
        if not passing:
            return None
        passing.sort(key=lambda c: (c["relax_factor"], -c["ism"]))
        return passing[0]

    def _save(self, cell_results: list[dict], seed_results: list[dict], output_dir: Path) -> None:
        if cell_results:
            with open(output_dir / "viability_table.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(cell_results[0].keys()))
                writer.writeheader()
                writer.writerows(cell_results)
            print(f"Wrote {output_dir / 'viability_table.csv'}")

        if seed_results:
            with open(output_dir / "seed_results.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(seed_results[0].keys()))
                writer.writeheader()
                writer.writerows(seed_results)
            print(f"Wrote {output_dir / 'seed_results.csv'}")

        best = self.lock_best(cell_results)
        summary = {
            "best_viable_ecology": best,
            "thresholds": {"svr_min": SVR_MIN, "g_depth_min": G_DEPTH_MIN, "psc_max": PSC_MAX},
            "grid": {
                "relax_factors": self._relax_factors,
                "ism_values": self._ism_values,
                "seeds_per_cell": self._seeds_per_cell,
                "max_ticks": self._max_ticks,
            },
            "cells": cell_results,
        }
        with open(output_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Wrote {output_dir / 'summary.json'}")

        if best:
            print(f"\n[BEST_VIABLE_ECOLOGY] relax_factor={best['relax_factor']}  ISM={best['ism']}")
            print(f"  SVR={best['svr']:.2f}  G_depth={best['g_depth']:.1f}  PSC={best['psc']:.3f}")
        else:
            print("\n[WARNING] No cell passed all thresholds — widen the grid or lower thresholds.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4c: Ecological Viability Screen")
    parser.add_argument("--relax-factors", nargs="+", type=float, default=RELAX_FACTORS,
                        help="init_food multipliers to sweep (default: 1.0 1.5 2.0 3.0)")
    parser.add_argument("--ism-values", nargs="+", type=float, default=ISM_VALUES,
                        help="infant_starvation_multiplier values (default: 1.0 0.7 0.5)")
    parser.add_argument("--seeds-per-cell", type=int, default=SEEDS_PER_CELL)
    parser.add_argument("--max-ticks", type=int, default=MAX_TICKS)
    parser.add_argument("--stability-start", type=int, default=STABILITY_START)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path(f"outputs/phase_eco_explore/exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    )

    runner = EcoExploreRunner(
        relax_factors=args.relax_factors,
        ism_values=args.ism_values,
        seeds_per_cell=args.seeds_per_cell,
        max_ticks=args.max_ticks,
        stability_start=args.stability_start,
        workers=args.workers,
    )
    runner.run(output_dir)
    print(f"\n[ok] Eco-explore complete — results in {output_dir}")


if __name__ == "__main__":
    main()
