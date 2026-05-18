"""Phase 5 — Asynchronous Baldwin evolution runner."""

from __future__ import annotations

import argparse
import csv
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from agents.mother import MotherAgent
from evolution.genome import Genome
from experiments.phase5_evolution.config import Phase5ConfigFactory
from simulation.simulation import Simulation


# ===========================================================================
# Run parameters
# ===========================================================================

@dataclass
class RunParams:
    """Hyperparameters for one Phase 5 evolution experiment.

    All fields map directly to CLI flags so the dataclass acts as the
    single source of truth for what a run looks like.

    Attributes:
        mutation_enabled: Enable genetic mutation during reproduction.
        plasticity_enabled: Enable phenotypic learning.
        learning_rate: Initial learning_rate for all starting genomes.
        plasticity_coefficient: Initial plasticity_coefficient for genomes.
        phenotype_retention: Fraction of parent expressed value inherited.
        mutation_rate: Per-gene mutation probability.
        mutation_sigma: Gaussian std-dev for mutations.
        max_ticks: Simulation duration per seed.
        seeds: Number of independent seeds to run.
        seed_start: Value of the first seed; subsequent seeds increment by 1.
        workers: Number of parallel worker processes.
        relax_ecology: If True, inflate food for pilot runs.
        ecology_relaxation_factor: Multiplier on init_food when relax=True.
        checkpoint: Snapshot interval in ticks for writing Phase 5 metrics.
        headless: If False (default), open a live pygame grid window. Forces
            seeds=1 and runs in the main process. Set True for multi-seed runs.
        vis_every: Render one frame every N ticks (1 = every tick; 10+ = fast
            preview for long runs). Ignored when headless=True.
        cell_size: Pixels per grid cell for the live Phase 5 viewer.
        circle_world: If True, use an inscribed circular arena instead of the
            full square grid.
    """

    mutation_enabled: bool = True

    plasticity_enabled: bool = True
    learning_rate: float = 5.0
    plasticity_coefficient: float = 1.0
    phenotype_retention: float = 0.15
    mutation_rate: float = 0.05
    mutation_sigma: float = 0.02
    max_ticks: int = 40_000
    seeds: int = 10
    seed_start: int = 42
    workers: int = 4
    relax_ecology: bool = False
    ecology_relaxation_factor: float = 1.15
    checkpoint: int = 10
    headless: bool = False
    vis_every: int = 1
    cell_size: int = 15
    circle_world: bool = False
    mother_max_age: int | None = None  # None = use Phase5ConfigFactory default (400)
    food_entropy_alpha: float = 0.01
    maturity_age: int = 80


# ===========================================================================
# Evolution runner
# ===========================================================================

class EvolutionRunner:
    """Runs asynchronous Baldwin evolution over one or many seeds.

    Encapsulates initial genome construction, per-tick sampling, parallel
    execution, and result persistence. Callers only interact with the two
    public methods: run_sweep() and save().

    Example:
        params = RunParams(seeds=5, max_ticks=5_000, relax_ecology=True)
        runner = EvolutionRunner(params)
        results = runner.run_sweep(Path("outputs/phase5_evolution/pilot"))
    """

    def __init__(self, params: RunParams) -> None:
        self._params = params

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_sweep(self, output_dir: Path) -> list[dict]:
        """Run parallel evolution over all seeds defined in params.

        Args:
            output_dir: Directory to write snapshots.csv and summary.json.
                Created automatically if absent.

        Returns:
            List of per-seed result dicts, each containing:
            seed, snapshots (list), final_stats (dict), params (dict).
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self._params.headless:
            if self._params.seeds != 1:
                print(
                    f"[vis] seeds={self._params.seeds} ignored - "
                    "visualization requires 1 seed. Pass --headless for multi-seed runs."
                )
            results = [self._execute_single_visual(self._params.seed_start)]
            self.save(results, output_dir)
            return results

        seeds = range(
            self._params.seed_start,
            self._params.seed_start + self._params.seeds,
        )

        results: list[dict] = []

        with ProcessPoolExecutor(max_workers=self._params.workers) as executor:
            futures = {
                executor.submit(EvolutionRunner._run_worker, seed, self._params): seed
                for seed in seeds
            }

            for future in as_completed(futures):
                seed = futures[future]
                try:
                    results.append(future.result())
                    print(f"[ok] Seed {seed} complete")
                except Exception as exc:
                    print(f"[fail] Seed {seed} failed: {exc}")

        self.save(results, output_dir)
        return results

    def save(self, results: list[dict], output_dir: Path) -> None:
        """Write snapshots.csv, lifecycle CSVs, and summary.json to output_dir.

        Args:
            results: List of per-seed result dicts from run_sweep().
            output_dir: Target directory (created if absent).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        self._write_snapshots_csv(results, output_dir / "snapshots.csv")
        self._write_lifecycle_csv(results, output_dir / "mother_lifecycle.csv", "mother_lifecycle_rows")
        self._write_lifecycle_csv(results, output_dir / "child_lifecycle.csv", "child_lifecycle_rows")
        self._write_summary_json(results, output_dir / "summary.json")

    # ------------------------------------------------------------------
    # Private — parallel worker (must be top-level-picklable)
    # ------------------------------------------------------------------

    @staticmethod
    def _run_worker(seed: int, params: RunParams) -> dict:
        """Top-level worker submitted to ProcessPoolExecutor.

        Creates a fresh EvolutionRunner inside each worker process so
        params (a plain dataclass) is the only object that crosses the
        process boundary.

        Args:
            seed: RNG seed and identifier for this run.
            params: Full experiment parameters.

        Returns:
            Per-seed result dict from _execute_single().
        """
        return EvolutionRunner(params)._execute_single(seed)

    # ------------------------------------------------------------------
    # Private — single-seed execution
    # ------------------------------------------------------------------

    def _execute_single(self, seed: int) -> dict:
        """Run one seed end-to-end and collect snapshots.

        Args:
            seed: RNG seed and run identifier.

        Returns:
            Dict with seed, snapshots list, final_stats dict, params record.
        """
        p = self._params

        cfg = Phase5ConfigFactory.make(
            seed=seed,
            mutation_enabled=p.mutation_enabled,
            plasticity_enabled=p.plasticity_enabled,
            learning_rate=p.learning_rate,
            plasticity_coefficient=p.plasticity_coefficient,
            phenotype_retention=p.phenotype_retention,
            mutation_rate=p.mutation_rate,
            mutation_sigma=p.mutation_sigma,
            max_ticks=p.max_ticks,
            relax_ecology=p.relax_ecology,
            ecology_relaxation_factor=p.ecology_relaxation_factor,
            circle_world=p.circle_world,
            food_entropy_alpha=p.food_entropy_alpha,
            maturity_age=p.maturity_age,
        )
        if p.mother_max_age is not None:
            cfg.mother_max_age = p.mother_max_age

        sim = Simulation(cfg)
        sim.initialize(genomes=self._initial_genomes(cfg.init_mothers))

        snapshots: list[dict] = []
        final_tick = 0
        for tick in range(p.max_ticks):
            sim.step()
            final_tick = tick

            if self._should_sample_tick(tick):
                snapshots.append(self._sample(sim, tick))

            if not sim.mothers:
                print(f"Seed {seed}: extinction at tick {tick}")
                break

        mother_rows, child_rows = sim.finalize_lifecycle_rows(final_tick)

        return {
            "seed": seed,
            "snapshots": snapshots,
            "final_stats": self._sample(sim, final_tick),
            "actual_final_tick": final_tick,
            "mother_lifecycle_rows": mother_rows,
            "child_lifecycle_rows": child_rows,
            "params": self._build_params_record(cfg),
        }

    def _execute_single_visual(self, seed: int) -> dict:
        """Run one seed with live pygame grid visualization in the main process.

        Creates a Phase5GridViewer and renders every vis_every ticks. If the
        user closes the window mid-run the simulation continues headlessly to
        completion so the full snapshot record is preserved.

        The viewer import is deferred to this method so that pygame is never
        imported in subprocess worker processes (which only call _run_worker →
        _execute_single and never reach this method).

        Args:
            seed: RNG seed and run identifier.

        Returns:
            Per-seed result dict with the same schema as _execute_single().
        """
        # Deferred import: keeps pygame out of subprocess worker imports.
        from experiments.phase5_evolution.viewer import Phase5GridViewer

        p = self._params

        cfg = Phase5ConfigFactory.make(
            seed=seed,
            mutation_enabled=p.mutation_enabled,
            plasticity_enabled=p.plasticity_enabled,
            learning_rate=p.learning_rate,
            plasticity_coefficient=p.plasticity_coefficient,
            phenotype_retention=p.phenotype_retention,
            mutation_rate=p.mutation_rate,
            mutation_sigma=p.mutation_sigma,
            max_ticks=p.max_ticks,
            relax_ecology=p.relax_ecology,
            ecology_relaxation_factor=p.ecology_relaxation_factor,
            circle_world=p.circle_world,
            food_entropy_alpha=p.food_entropy_alpha,
            maturity_age=p.maturity_age,
        )

        sim = Simulation(cfg)
        sim.initialize(genomes=self._initial_genomes(cfg.init_mothers))

        condition = (
            f"mut={'ON' if p.mutation_enabled else 'OFF'}  "
            f"plast={'ON' if p.plasticity_enabled else 'OFF'}"
        )
        viewer = Phase5GridViewer(
            grid_width=cfg.width,
            grid_height=cfg.height,
            cell_size=p.cell_size,
            vis_every=p.vis_every,
            condition_label=condition,
            circle_world=p.circle_world,
        )

        snapshots: list[dict] = []
        last_snapshot: dict = {}
        window_open = True
        final_tick = 0

        try:
            for tick in range(p.max_ticks):
                sim.step()
                final_tick = tick

                if self._should_sample_tick(tick):
                    last_snapshot = self._sample(sim, tick)
                    snapshots.append(last_snapshot)

                if window_open:
                    window_open = viewer.step(sim, tick, last_snapshot)

                if not sim.mothers:
                    print(f"Seed {seed}: extinction at tick {tick}")
                    break
        finally:
            viewer.close()

        mother_rows, child_rows = sim.finalize_lifecycle_rows(final_tick)

        return {
            "seed": seed,
            "snapshots": snapshots,
            "final_stats": self._sample(sim, final_tick),
            "actual_final_tick": final_tick,
            "mother_lifecycle_rows": mother_rows,
            "child_lifecycle_rows": child_rows,
            "params": self._build_params_record(cfg),
        }

    def _should_sample_tick(self, tick: int) -> bool:
        """Return True when the current tick should be persisted as a snapshot."""
        checkpoint = max(1, int(self._params.checkpoint))
        return tick % checkpoint == 0

    def _initial_genomes(self, n: int) -> list[Genome]:
        """Build the starting population with neutral motivation weights.

        Each genome starts at care=forage=self=1/3 so any rise in
        mean_genome_care_weight is attributable to ecological selection,
        not initialization bias.

        Args:
            n: Number of genomes to create (must match cfg.init_mothers).

        Returns:
            List of n neutral Genome objects.
        """
        p = self._params
        return [
            Genome(
                care_weight=1 / 3,
                forage_weight=1 / 3,
                self_weight=1 / 3,
                learning_rate=p.learning_rate,
                plasticity_coefficient=p.plasticity_coefficient,
            )
            for _ in range(n)
        ]

    def _sample(self, sim: Simulation, tick: int) -> dict:
        """Capture all ROADMAP-specified metrics at the given tick.

        Args:
            sim: Running Simulation instance.
            tick: Current tick number (written into the snapshot).

        Returns:
            Dict with all tracked metrics for one snapshot row.
        """
        mothers  = sim.mothers
        children = sim.children

        genome_vectors    = [m.get_genome_vector()          for m in mothers]
        genome_care       = [vec[0]                         for vec in genome_vectors]
        genome_forage     = [vec[1]                         for vec in genome_vectors]
        genome_self       = [vec[2]                         for vec in genome_vectors]
        expressed_care    = [m.expressed_care_weight        for m in mothers]
        expressed_forage  = [m.expressed_forage_weight      for m in mothers]
        expressed_self    = [m.expressed_self_weight        for m in mothers]
        learning_rates    = [m.genome.learning_rate         for m in mothers]
        plasticity_coeffs = [m.genome.plasticity_coefficient for m in mothers]
        mother_energies   = [m.energy                        for m in mothers]
        learning_costs    = [m.lifetime_learning_cost        for m in mothers]
        generations       = [m.generation                    for m in mothers]

        mean_pc   = float(np.mean(plasticity_coeffs)) if plasticity_coeffs else 0.0
        distances = [m.genome_behavior_distance() for m in mothers]
        highest_generation = int(max(generations)) if generations else 0

        total_matured = sum(m.matured_children for m in mothers)
        total_born    = sum(m.total_children   for m in mothers)
        child_survival_rate = total_matured / total_born if total_born > 0 else 0.0

        return {
            "tick":                   tick,
            "n_mothers":              len(mothers),
            "n_children":             len(children),
            "mean_genome_care":       float(np.mean(genome_care))       if genome_care       else 0.0,
            "std_genome_care":        float(np.std(genome_care))        if genome_care       else 0.0,
            "mean_genome_forage":     float(np.mean(genome_forage))     if genome_forage     else 0.0,
            "std_genome_forage":      float(np.std(genome_forage))      if genome_forage     else 0.0,
            "mean_genome_self":       float(np.mean(genome_self))       if genome_self       else 0.0,
            "std_genome_self":        float(np.std(genome_self))        if genome_self       else 0.0,
            "mean_expressed_care":    float(np.mean(expressed_care))    if expressed_care    else 0.0,
            "std_expressed_care":     float(np.std(expressed_care))     if expressed_care    else 0.0,
            "mean_expressed_forage":  float(np.mean(expressed_forage))  if expressed_forage  else 0.0,
            "std_expressed_forage":   float(np.std(expressed_forage))   if expressed_forage  else 0.0,
            "mean_expressed_self":    float(np.mean(expressed_self))    if expressed_self    else 0.0,
            "std_expressed_self":     float(np.std(expressed_self))     if expressed_self    else 0.0,
            "mean_learning_rate":     float(np.mean(learning_rates))    if learning_rates    else 0.0,
            "std_learning_rate":      float(np.std(learning_rates))     if learning_rates    else 0.0,
            "mean_plasticity":        mean_pc,
            "std_plasticity":         float(np.std(plasticity_coeffs))  if plasticity_coeffs else 0.0,
            "innateness_index":       1.0 - mean_pc,
            "genome_behavior_distance": float(np.mean(distances))       if distances         else 0.0,
            "mean_learning_cost":     float(np.mean(learning_costs))    if learning_costs    else 0.0,
            "mean_mother_energy":     float(np.mean(mother_energies))   if mother_energies   else 0.0,
            "mean_child_energy":      float(np.mean([c.energy for c in children])) if children else 0.0,
            "mean_generation":        float(np.mean(generations))       if generations       else 0.0,
            "highest_generation":     highest_generation,
            "child_survival_rate":    child_survival_rate,
            "population_size":        len(mothers) + len(children),
        }

    def _build_params_record(self, cfg) -> dict:
        """Persist both run knobs and analysis horizons used by the engine."""
        p = self._params
        return {
            "mutation_enabled": p.mutation_enabled,
            "plasticity_enabled": p.plasticity_enabled,
            "mutation_rate": p.mutation_rate,
            "mutation_sigma": p.mutation_sigma,
            "learning_rate": p.learning_rate,
            "plasticity_coefficient": p.plasticity_coefficient,
            "phenotype_retention": p.phenotype_retention,
            "plasticity_local_search": "motivation_vector",
            "max_ticks": p.max_ticks,
            "relax_ecology": p.relax_ecology,
            "checkpoint": p.checkpoint,
            "cell_size": p.cell_size,
            "circle_world": p.circle_world,
            "maturity_age": cfg.maturity_age,
            "mother_max_age": cfg.mother_max_age,
            "food_entropy_alpha": cfg.food_entropy_alpha,
        }

    # ------------------------------------------------------------------
    # Private — persistence helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _write_snapshots_csv(results: list[dict], path: Path) -> None:
        """Write all per-tick snapshots from every seed into one CSV.

        A 'seed' column is added to each row so downstream analysis can
        group by seed. All seeds share the same column schema.

        Args:
            results: List of per-seed result dicts.
            path: Destination CSV file path.
        """
        with open(path, "w", newline="") as f:
            writer = None
            for result in results:
                seed = result["seed"]
                for snapshot in result["snapshots"]:
                    snapshot["seed"] = seed
                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=list(snapshot.keys()))
                        writer.writeheader()
                    writer.writerow(snapshot)
        print(f"Wrote snapshots to {path}")

    @staticmethod
    def _write_lifecycle_csv(results: list[dict], path: Path, key: str) -> None:
        """Write one combined lifecycle CSV across all seeds."""
        with open(path, "w", newline="") as f:
            writer = None
            for result in results:
                seed = result["seed"]
                for row in result.get(key, []):
                    record = dict(row)
                    record["seed"] = seed
                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=list(record.keys()))
                        writer.writeheader()
                    writer.writerow(record)
        print(f"Wrote lifecycle rows to {path}")

    @staticmethod
    def _write_summary_json(results: list[dict], path: Path) -> None:
        """Write run summary (params + per-seed final stats) to JSON.

        Args:
            results: List of per-seed result dicts.
            path: Destination JSON file path.
        """
        summary = {
            "n_seeds":    len(results),
            "seeds": [r["seed"] for r in results],
            "actual_final_ticks": [r.get("actual_final_tick", 0) for r in results],
            "final_stats": [r["final_stats"] for r in results],
            "params":      results[0]["params"] if results else {},
        }
        with open(path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Wrote summary to {path}")


# ===========================================================================
# CLI entry point
# ===========================================================================

def main() -> None:
    """CLI entry point for Phase 5 evolution experiments."""
    parser = argparse.ArgumentParser(
        description="Phase 5: Asynchronous Baldwin evolution"
    )

    parser.add_argument(
        "--mutation-enabled",
        type=lambda x: x.lower() == "true",
        default=True,
    )
    parser.add_argument(
        "--plasticity-enabled",
        type=lambda x: x.lower() == "true",
        default=True,
    )
    parser.add_argument("--learning-rate",            type=float, default=0.05)
    parser.add_argument("--plasticity-coefficient",   type=float, default=0.5)
    parser.add_argument("--phenotype-retention",      type=float, default=0.15)
    parser.add_argument("--mutation-rate",             type=float, default=0.05)
    parser.add_argument("--mutation-sigma",            type=float, default=0.02)
    parser.add_argument("--max-ticks",                 type=int,   default=40_000)
    parser.add_argument(
        "--checkpoint",
        type=int,
        default=10,
        help="Snapshot interval in ticks for snapshots.csv (default: 10).",
    )
    parser.add_argument("--seeds",                     type=int,   default=10)
    parser.add_argument("--seed-start",                type=int,   default=42)
    parser.add_argument("--workers",                   type=int,   default=4)
    parser.add_argument(
        "--relax-ecology",
        type=lambda x: x.lower() == "true",
        default=False,
    )
    parser.add_argument("--ecology-relaxation-factor", type=float, default=1.15)
    parser.add_argument("--output-dir",                type=str,   default=None)
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Disable live visualization. Required when --seeds > 1.",
    )
    parser.add_argument(
        "--vis-every",
        type=int,
        default=1,
        help="Render one frame every N ticks (1=every tick; 10+ for fast preview).",
    )
    parser.add_argument(
        "--cell-size",
        type=int,
        default=15,
        help="Pixels per grid cell in the live Phase 5 viewer.",
    )
    parser.add_argument(
        "--circle-world",
        "--circle_world",
        dest="circle_world",
        action="store_true",
        default=False,
        help="Use an inscribed circular arena instead of the full square grid.",
    )
    parser.add_argument(
        "--mother-max-age",
        type=int,
        default=None,
        help="Override mother_max_age (default: Phase5ConfigFactory value=400). "
             "Use 1000 for multi-generational Block 2 runs.",
    )
    parser.add_argument(
        "--food-entropy-alpha",
        type=float,
        default=0.01,
        help="Shannon food-entropy alpha (0.0 = simple food, 0.01 = Block 2, 0.05 = Block 3).",
    )
    parser.add_argument(
        "--maturity-age",
        type=int,
        default=80,
        help="Ticks for a child to reach maturity (default: 80).",
    )

    args = parser.parse_args()
    if args.checkpoint <= 0:
        parser.error("--checkpoint must be a positive integer")

    params = RunParams(
        mutation_enabled=args.mutation_enabled,
        plasticity_enabled=args.plasticity_enabled,
        learning_rate=args.learning_rate,
        plasticity_coefficient=args.plasticity_coefficient,
        phenotype_retention=args.phenotype_retention,
        mutation_rate=args.mutation_rate,
        mutation_sigma=args.mutation_sigma,
        max_ticks=args.max_ticks,
        checkpoint=args.checkpoint,
        seeds=args.seeds,
        seed_start=args.seed_start,
        workers=args.workers,
        relax_ecology=args.relax_ecology,
        ecology_relaxation_factor=args.ecology_relaxation_factor,
        headless=args.headless,
        vis_every=args.vis_every,
        cell_size=args.cell_size,
        circle_world=args.circle_world,
        mother_max_age=args.mother_max_age,
        food_entropy_alpha=args.food_entropy_alpha,
        maturity_age=args.maturity_age,
    )

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path(
            f"outputs/phase5_evolution/exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    )

    runner = EvolutionRunner(params)
    results = runner.run_sweep(output_dir)
    print(f"[ok] Sweep complete: {len(results)} seeds")


if __name__ == "__main__":
    main()
