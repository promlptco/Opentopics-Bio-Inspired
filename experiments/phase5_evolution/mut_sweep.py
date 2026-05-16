"""Phase 5 mutation_rate / sigma / tau 1-D sweeps.

Tests how sensitive the Baldwin Effect signal is to:
  - mutation_rate (per-gene mutation probability): [0.05, 0.10, 0.30, 0.50]
  - mutation_sigma (Gaussian std-dev of gene change):  [0.01, 0.02, 0.05, 0.10]
  - softmax_tau (action selection stochasticity):       [0.05, 0.10, 0.20, 0.50]

Each sweep runs the mut_on_plast_on condition over 5 seeds at 20k ticks
(shorter than full block2 but enough to see trajectory direction).

Output:
  outputs/phase5_evolution/mut_sweep/
    rate_sweep/    -- one subdir per mutation_rate value
    sigma_sweep/   -- one subdir per mutation_sigma value
    tau_sweep/     -- one subdir per softmax_tau value
    comparison_rate.png
    comparison_sigma.png
    comparison_tau.png

Usage:
  python -m experiments.phase5_evolution.mut_sweep
  python -m experiments.phase5_evolution.mut_sweep --seeds 5 --ticks 20000 --workers 8
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Sweep grids
RATE_VALUES:  list[float] = [0.05, 0.10, 0.30, 0.50]
SIGMA_VALUES: list[float] = [0.01, 0.02, 0.05, 0.10]
TAU_VALUES:   list[float] = [0.05, 0.10, 0.20, 0.50]

NEUTRAL = 1.0 / 3.0


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def _worker(args: tuple) -> dict:
    """Worker for ProcessPoolExecutor — returns snapshots CSV rows."""
    seed, mutation_rate, mutation_sigma, tau, max_ticks, checkpoint, relax_ecology = args

    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

    from experiments.phase5_evolution.config import Phase5ConfigFactory
    from experiments.phase5_evolution.run import EvolutionRunner, RunParams
    from evolution.genome import Genome
    from simulation.simulation import Simulation

    params = RunParams(
        mutation_enabled=True,
        plasticity_enabled=True,
        learning_rate=1.0,
        plasticity_coefficient=1.0,
        phenotype_retention=0.15,
        mutation_rate=mutation_rate,
        mutation_sigma=mutation_sigma,
        max_ticks=max_ticks,
        seeds=1,
        seed_start=seed,
        workers=1,
        relax_ecology=relax_ecology,
        ecology_relaxation_factor=1.2,
        checkpoint=checkpoint,
        headless=True,
    )

    cfg = Phase5ConfigFactory.make(
        seed=seed,
        mutation_enabled=True,
        plasticity_enabled=True,
        learning_rate=1.0,
        plasticity_coefficient=1.0,
        phenotype_retention=0.15,
        mutation_rate=mutation_rate,
        mutation_sigma=mutation_sigma,
        max_ticks=max_ticks,
        relax_ecology=relax_ecology,
        ecology_relaxation_factor=1.2,
    )
    cfg.softmax_tau = tau

    runner = EvolutionRunner(params)
    genomes = runner._initial_genomes(cfg.init_mothers)

    sim = Simulation(cfg)
    sim.initialize(genomes=genomes)

    snapshots: list[dict] = []
    final_tick = 0
    for tick in range(max_ticks):
        sim.step()
        final_tick = tick
        if tick % checkpoint == 0:
            snap = runner._sample(sim, tick)
            snap["seed"] = seed
            snap["mutation_rate"] = mutation_rate
            snap["mutation_sigma"] = mutation_sigma
            snap["tau"] = tau
            snapshots.append(snap)
        if not sim.mothers:
            break

    return {
        "seed": seed,
        "mutation_rate": mutation_rate,
        "mutation_sigma": mutation_sigma,
        "tau": tau,
        "final_tick": final_tick,
        "extinct": final_tick < max_ticks - 1,
        "snapshots": snapshots,
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _plot_sweep_comparison(
    results: list[dict],
    param_key: str,
    param_values: list[float],
    out: Path,
    title_prefix: str,
) -> None:
    """Plot mean_genome_care trajectory for each param value."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("%s sweep (mut_on / plast_on)" % title_prefix, fontsize=13, fontweight="bold")

    metrics = ["mean_genome_care", "mean_expressed_care", "n_mothers"]
    ylabels = ["Genome care weight", "Expressed care weight", "N mothers alive"]

    colors = plt.cm.viridis(np.linspace(0.15, 0.90, len(param_values)))

    for ax, metric, ylabel in zip(axes, metrics, ylabels):
        for pval, color in zip(param_values, colors):
            subset = [r for r in results if abs(r[param_key] - pval) < 1e-9]
            if not subset:
                continue

            all_snaps: list[dict] = []
            for r in subset:
                all_snaps.extend(r["snapshots"])

            if not all_snaps:
                continue

            df = pd.DataFrame(all_snaps)
            grouped = df.groupby("tick")[metric]
            ticks = grouped.mean().index.to_numpy()
            means = grouped.mean().to_numpy()
            sems = (grouped.std() / np.sqrt(grouped.count())).to_numpy()

            label = "%s=%.2f" % (param_key, pval)
            ax.plot(ticks, means, color=color, linewidth=1.5, label=label)
            ax.fill_between(ticks, means - sems, means + sems, color=color, alpha=0.2)

        if metric == "mean_genome_care":
            ax.axhline(NEUTRAL, color="red", linestyle="--", linewidth=1, alpha=0.7, label="neutral 1/3")

        ax.set_xlabel("Tick")
        ax.set_ylabel(ylabel)
        ax.set_title(metric.replace("_", " ").title())
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fname = out / ("comparison_%s.png" % param_key)
    fig.savefig(str(fname), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved -> %s" % fname)


def _save_snapshots_csv(results: list[dict], path: Path) -> None:
    import csv
    rows: list[dict] = []
    for r in results:
        rows.extend(r["snapshots"])
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("Snapshots -> %s" % path)


# ---------------------------------------------------------------------------
# Run one sweep axis
# ---------------------------------------------------------------------------

def _run_axis(
    sweep_name: str,
    param_key: str,
    param_values: list[float],
    fixed_rate: float,
    fixed_sigma: float,
    fixed_tau: float,
    seeds: int,
    max_ticks: int,
    workers: int,
    checkpoint: int,
    relax_ecology: bool,
    out: Path,
) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)

    jobs = []
    for pval in param_values:
        rate  = pval if param_key == "mutation_rate"  else fixed_rate
        sigma = pval if param_key == "mutation_sigma" else fixed_sigma
        tau   = pval if param_key == "tau"            else fixed_tau
        for seed in range(42, 42 + seeds):
            jobs.append((seed, rate, sigma, tau, max_ticks, checkpoint, relax_ecology))

    results: list[dict] = []

    print("\n[%s] running %d jobs with workers=%d..." % (sweep_name, len(jobs), workers))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, j): j for j in jobs}
        for future in as_completed(futures):
            j = futures[future]
            try:
                r = future.result()
                results.append(r)
                status = "EXTINCT@%d" % r["final_tick"] if r["extinct"] else "ok tick=%d" % r["final_tick"]
                print("  seed=%d  %s=%.2f  %s" % (
                    j[0], param_key,
                    j[1] if param_key == "mutation_rate" else
                    j[2] if param_key == "mutation_sigma" else j[3],
                    status,
                ))
            except Exception as exc:
                print("  [FAIL] seed=%d: %s" % (j[0], exc))

    _save_snapshots_csv(results, out / ("snapshots_%s.csv" % param_key))
    _plot_sweep_comparison(results, param_key, param_values, out.parent, sweep_name)
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(
    seeds: int = 5,
    max_ticks: int = 20_000,
    workers: int = 4,
    checkpoint: int = 100,
    relax_ecology: bool = True,
    output_dir: Path | None = None,
) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = output_dir or (PROJECT_ROOT / "outputs" / "phase5_evolution" / ("mut_sweep_%s" % ts))
    out.mkdir(parents=True, exist_ok=True)

    print("[phase5_mutation_sweep]")
    print("  seeds=%d  ticks=%d  workers=%d  relax_ecology=%s" % (
        seeds, max_ticks, workers, relax_ecology))
    print("  mutation_rate values: %s" % RATE_VALUES)
    print("  mutation_sigma values: %s" % SIGMA_VALUES)
    print("  tau values: %s" % TAU_VALUES)
    print("  output: %s" % out)

    # 1. mutation_rate sweep (fixed sigma=0.02, tau=0.10)
    _run_axis(
        "mutation_rate", "mutation_rate", RATE_VALUES,
        fixed_rate=0.5, fixed_sigma=0.02, fixed_tau=0.10,
        seeds=seeds, max_ticks=max_ticks, workers=workers,
        checkpoint=checkpoint, relax_ecology=relax_ecology,
        out=out / "rate_sweep",
    )

    # 2. mutation_sigma sweep (fixed rate=0.5, tau=0.10)
    _run_axis(
        "mutation_sigma", "mutation_sigma", SIGMA_VALUES,
        fixed_rate=0.5, fixed_sigma=0.02, fixed_tau=0.10,
        seeds=seeds, max_ticks=max_ticks, workers=workers,
        checkpoint=checkpoint, relax_ecology=relax_ecology,
        out=out / "sigma_sweep",
    )

    # 3. tau sweep (fixed rate=0.5, sigma=0.02)
    _run_axis(
        "tau", "tau", TAU_VALUES,
        fixed_rate=0.5, fixed_sigma=0.02, fixed_tau=0.10,
        seeds=seeds, max_ticks=max_ticks, workers=workers,
        checkpoint=checkpoint, relax_ecology=relax_ecology,
        out=out / "tau_sweep",
    )

    print("\n[ok] Mutation sweep complete -- %s" % out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5 mutation/sigma/tau sweep")
    parser.add_argument("--seeds",   type=int,   default=5)
    parser.add_argument("--ticks",   type=int,   default=20_000)
    parser.add_argument("--workers", type=int,   default=4)
    parser.add_argument("--checkpoint", type=int, default=100)
    parser.add_argument(
        "--relax-ecology",
        type=lambda x: x.lower() == "true",
        default=True,
    )
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    run(
        seeds=args.seeds,
        max_ticks=args.ticks,
        workers=max(1, args.workers),
        checkpoint=args.checkpoint,
        relax_ecology=args.relax_ecology,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )


if __name__ == "__main__":
    main()
