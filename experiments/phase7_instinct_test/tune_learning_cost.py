# experiments/phase7_instinct_test/tune_learning_cost.py
"""Mini-sweep: find the plasticity_energy_cost sweet spot.

Sweeps config.plasticity_energy_cost over COST_VALS using 3 seeds for
Stage 1 only (5 000 ticks, plasticity ON). Reports survival and how much
the *genetic* care_weight rises — the signal that assimilation is happening.

Sweet spot: population survives (mean pop >= 10) AND mean final
genetic care_weight >= 0.38 (meaningfully above the 0.325 start).

Usage:
    python experiments/phase7_instinct_test/tune_learning_cost.py
"""
import sys
import os
import json
import math
from concurrent.futures import ProcessPoolExecutor, as_completed

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase7_instinct_test.run import (
    INIT_CARE, INIT_DS, INIT_CR, INIT_LR, INIT_LC,
    PLASTIC_GAIN, MLE_MULT, STAGE1_TICKS, SNAPSHOT_INTERVAL,
    _make_genomes, _build_config,
)

try:
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 11, "axes.labelsize": 11,
        "axes.spines.top": False, "axes.spines.right": False,
        "lines.linewidth": 2.2, "figure.facecolor": "white",
        "axes.facecolor": "white", "grid.alpha": 0.25,
    })
    HAS_PLT = True
except ImportError:
    HAS_PLT = False

COST_VALS = [0.0, 0.002, 0.005, 0.01, 0.02]
SEEDS     = [42, 43, 44]
OUT_DIR   = os.path.join(PROJECT_ROOT, "outputs", "phase7_instinct_test", "tune_learning_cost")

MIN_OLD = 100


def _mean(vals):
    return sum(vals) / len(vals) if vals else float("nan")


def _run_worker(packed):
    cost, seed, project_root = packed
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from config import Config
    from simulation.simulation import Simulation
    from utils.experiment import set_seed
    from experiments.phase7_instinct_test.run import (
        STAGE1_TICKS, SNAPSHOT_INTERVAL, MIN_OLD, INIT_CARE,
        _make_genomes, _build_config,
    )

    set_seed(seed)
    cfg = _build_config(seed, plasticity_energy_cost=cost)
    cfg.max_ticks = STAGE1_TICKS

    genomes = _make_genomes(cfg.init_mothers)
    sim = Simulation(cfg)
    sim.initialize(genomes)

    snaps = []
    while sim.tick < STAGE1_TICKS:
        sim.step()
        sim.tick += 1

        if sim.tick % SNAPSHOT_INTERVAL == 0:
            alive = [m for m in sim.mothers if m.alive]
            if not alive:
                break
            snaps.append({
                "tick":                      sim.tick,
                "n_mothers":                 len(alive),
                "avg_care_weight":           sum(m.genome.care_weight for m in alive) / len(alive),
                "avg_expressed_care_weight": sum(m.expressed_care_weight for m in alive) / len(alive),
                "avg_learning_cost":         sum(m.genome.learning_cost for m in alive) / len(alive),
            })

    alive = [m for m in sim.mothers if m.alive]
    n = len(alive)
    final_cw  = sum(m.genome.care_weight for m in alive) / n if n else 0.0
    final_ecw = sum(m.expressed_care_weight for m in alive) / n if n else 0.0
    final_lc  = sum(m.genome.learning_cost for m in alive) / n if n else 0.0

    return {
        "cost": cost, "seed": seed,
        "final_pop": n, "survived": n >= 10,
        "final_cw": final_cw, "final_ecw": final_ecw,
        "final_lc": final_lc,
        "snaps": snaps,
    }


def _plot(results_by_cost, out_dir):
    if not HAS_PLT:
        return

    costs = sorted(results_by_cost.keys())
    colors = plt.cm.viridis([i / max(len(costs) - 1, 1) for i in range(len(costs))])

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(
        f"Phase 7 — plasticity_energy_cost sweep  (Stage 1, {STAGE1_TICKS} ticks, {len(SEEDS)} seeds)\n"
        f"Goal: population survives AND genetic care_weight rises above 0.38",
        fontsize=11,
    )

    ax_pop, ax_cw, ax_gap = axes

    for i, cost in enumerate(costs):
        rlist = results_by_cost[cost]
        label = f"cost={cost}"
        c = colors[i]

        for r in rlist:
            ticks = [s["tick"] for s in r["snaps"]]
            if not ticks:
                continue
            ax_pop.plot(ticks, [s["n_mothers"] for s in r["snaps"]],
                        color=c, alpha=0.35, linewidth=1.2)
            ax_cw.plot(ticks, [s["avg_care_weight"] for s in r["snaps"]],
                       color=c, alpha=0.35, linewidth=1.2)
            ax_gap.plot(
                ticks,
                [s["avg_expressed_care_weight"] - s["avg_care_weight"] for s in r["snaps"]],
                color=c, alpha=0.35, linewidth=1.2,
            )

        # Bold mean line
        all_ticks = sorted(set(t for r in rlist for s in r["snaps"] for t in [s["tick"]]))
        def get_mean(key, t):
            vals = [s[key] for r in rlist for s in r["snaps"] if s["tick"] == t]
            return _mean(vals) if vals else float("nan")

        if all_ticks:
            pop_m = [get_mean("n_mothers", t) for t in all_ticks]
            cw_m  = [get_mean("avg_care_weight", t) for t in all_ticks]
            gap_m = [get_mean("avg_expressed_care_weight", t) - get_mean("avg_care_weight", t)
                     for t in all_ticks]
            ax_pop.plot(all_ticks, pop_m, color=c, linewidth=2.5, label=label)
            ax_cw.plot(all_ticks, cw_m,  color=c, linewidth=2.5, label=label)
            ax_gap.plot(all_ticks, gap_m, color=c, linewidth=2.5, label=label)

    ax_pop.axhline(10, color="crimson", linestyle=":", linewidth=1.2, label="Survival threshold")
    ax_pop.set_title("Population size")
    ax_pop.set_ylabel("n_mothers")
    ax_pop.set_xlabel("Tick")
    ax_pop.legend(fontsize=9, loc="lower left")
    ax_pop.grid(True)

    ax_cw.axhline(INIT_CARE, color="gray", linestyle=":", linewidth=1.2, label=f"Start ({INIT_CARE})")
    ax_cw.axhline(0.38, color="seagreen", linestyle="--", linewidth=1.2, label="Target (0.38)")
    ax_cw.set_title("Genetic care_weight (instinct floor)")
    ax_cw.set_ylabel("avg_care_weight")
    ax_cw.set_xlabel("Tick")
    ax_cw.legend(fontsize=9, loc="upper left")
    ax_cw.grid(True)

    ax_gap.axhline(0, color="gray", linewidth=0.8)
    ax_gap.set_title("Plastic gap (expressed - genetic)")
    ax_gap.set_ylabel("expressed - genetic")
    ax_gap.set_xlabel("Tick")
    ax_gap.grid(True)

    fig.tight_layout()
    path = os.path.join(out_dir, "tune_learning_cost.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    packed = [(cost, seed, PROJECT_ROOT) for cost in COST_VALS for seed in SEEDS]
    max_workers = min(len(packed), os.cpu_count() or 4)

    print(f"\nPhase 7 — plasticity_energy_cost sweep")
    print(f"  Costs  : {COST_VALS}")
    print(f"  Seeds  : {SEEDS}")
    print(f"  Ticks  : {STAGE1_TICKS} (Stage 1 only)")
    print(f"  Workers: {max_workers}\n")

    all_results = []
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_worker, p): p for p in packed}
        for fut in as_completed(futures):
            r = fut.result()
            all_results.append(r)
            print(f"  [done] cost={r['cost']}  seed={r['seed']}  "
                  f"pop={r['final_pop']}  cw={r['final_cw']:.4f}  "
                  f"gap={r['final_ecw']-r['final_cw']:.4f}  "
                  f"lc={r['final_lc']:.4f}")

    results_by_cost = {}
    for r in all_results:
        results_by_cost.setdefault(r["cost"], []).append(r)

    _plot(results_by_cost, OUT_DIR)

    print("\n=== Sweep Summary ===")
    print(f"  {'Cost':>7}  {'Surv':>5}  {'MeanPop':>8}  {'MeanCW':>8}  {'MeanGap':>9}  {'MeanLC':>8}")
    print("-" * 58)

    best_cost = None
    best_score = -1.0
    for cost in sorted(results_by_cost.keys()):
        rlist = results_by_cost[cost]
        n_surv = sum(1 for r in rlist if r["survived"])
        mean_pop = _mean([r["final_pop"] for r in rlist])
        mean_cw  = _mean([r["final_cw"]  for r in rlist])
        mean_gap = _mean([r["final_ecw"] - r["final_cw"] for r in rlist])
        mean_lc  = _mean([r["final_lc"]  for r in rlist])
        print(f"  {cost:>7}  {n_surv}/{len(rlist)}  {mean_pop:>8.1f}  {mean_cw:>8.4f}  {mean_gap:>9.4f}  {mean_lc:>8.4f}")

        # Score: must survive, genetic cw should be high
        if n_surv == len(SEEDS) and mean_cw > best_score:
            best_score = mean_cw
            best_cost = cost

    print("-" * 58)
    if best_cost is not None:
        print(f"\n  Sweet spot : plasticity_energy_cost = {best_cost}")
        print(f"  (all {len(SEEDS)} seeds survived, highest mean genetic care_weight)")
    else:
        print("\n  No cost value achieved full survival — lower the range.")

    with open(os.path.join(OUT_DIR, "sweep_results.json"), "w") as f:
        json.dump(
            {str(c): [
                {k: v for k, v in r.items() if k != "snaps"} for r in rlist
            ] for c, rlist in results_by_cost.items()},
            f, indent=2,
        )
    print(f"\n  Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
