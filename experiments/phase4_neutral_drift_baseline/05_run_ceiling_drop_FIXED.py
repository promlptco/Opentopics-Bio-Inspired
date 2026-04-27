"""Phase 4 -- Step 5: Ceiling-Drop Baseline (BUG-FIXED)

Re-runs Script 02 with the orphan-injection bug fixed.

BUG FIXED
---------
Original simulation.py assigned the child's genome AT MATURATION by
looking up the birth mother. If she had died, the child fell back to
Genome() (all weights = 0.5), silently injecting low-care defaults
during the initial population die-off.

FIX: Genome is now assigned AT BIRTH and stored on the child. Maturation
simply reads child.genome. The Genome() fallback can no longer trigger.
Verified via sim.genome_fallback_count == 0.

PROTOCOL (identical to Script 02)
----------------------------------
  care_weight init             = 0.80
  forage_weight init           = 1.00
  self_weight init             = U(0, 1)
  infant_starvation_multiplier = 1.0   (standard)
  feed_cost                    = 0.03  (standard)
  grid = 50x50, N=40, food=120
  plasticity = OFF, mutation = ON
  duration = 10,000 ticks, seeds 42-51
"""

import sys
import os
import json
import csv
import random as _random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata

PHASE_NAME        = "phase4_neutral_drift_baseline/05_ceiling_drop_FIXED"
INFANT_MULT       = 1.0
FEED_COST         = 0.03
BIRTH_SCATTER     = 5
INIT_CARE         = 0.8
INIT_FORAGE       = 1.0
GRID_SIZE         = 50
INIT_MOTHERS      = 40
INIT_FOOD         = 120
SNAPSHOT_INTERVAL = 200
SEEDS             = list(range(42, 52))
OUT_DIR           = os.path.join(PROJECT_ROOT, "outputs", PHASE_NAME)
SNAP_DIR          = os.path.join(OUT_DIR, "seed_snapshots")


# -- Helpers ------------------------------------------------------------------

def _variance(values):
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return sum((x - m) ** 2 for x in values) / (n - 1)


def _pearson_r(xs, ys):
    n = len(xs)
    if n < 10:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx  = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy  = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _binom_p(n, k, p=0.5):
    from math import comb
    return sum(comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


def _make_genomes(n):
    return [
        Genome(care_weight=INIT_CARE, forage_weight=INIT_FORAGE,
               self_weight=_random.uniform(0.0, 1.0))
        for _ in range(n)
    ]


# -- Single-seed run ----------------------------------------------------------

def run_one(seed):
    config = Config()
    config.seed                         = seed
    config.width                        = GRID_SIZE
    config.height                       = GRID_SIZE
    config.init_mothers                 = INIT_MOTHERS
    config.init_food                    = INIT_FOOD
    config.max_ticks                    = 10_000
    config.infant_starvation_multiplier = INFANT_MULT
    config.feed_cost                    = FEED_COST
    config.birth_scatter_radius         = BIRTH_SCATTER
    config.plasticity_enabled           = False
    config.plasticity_kin_conditional   = False
    config.children_enabled             = True
    config.care_enabled                 = True
    config.reproduction_enabled         = True
    config.mutation_enabled             = True

    set_seed(seed)
    output_dir = create_run_dir(PHASE_NAME, seed)
    save_config(config, output_dir)
    save_metadata(output_dir, phase=PHASE_NAME, seed=seed,
                  num_agents=INIT_MOTHERS * 2, note="Bug-fixed ceiling-drop baseline.")

    genomes = _make_genomes(INIT_MOTHERS)
    sim     = Simulation(config)
    sim.initialize(genomes)

    snapshots = []
    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        alive = [m for m in sim.mothers if m.alive]
        if sim.tick % SNAPSHOT_INTERVAL == 0 and alive:
            cw = [m.genome.care_weight   for m in alive]
            fw = [m.genome.forage_weight for m in alive]
            sw = [m.genome.self_weight   for m in alive]
            snapshots.append({
                "tick":              sim.tick,
                "avg_care_weight":   sum(cw) / len(cw),
                "var_care_weight":   _variance(cw),
                "min_care_weight":   min(cw),
                "max_care_weight":   max(cw),
                "avg_forage_weight": sum(fw) / len(fw),
                "avg_self_weight":   sum(sw) / len(sw),
                "avg_generation":    sum(m.generation for m in alive) / len(alive),
                "max_generation":    max(m.generation for m in alive),
                "n_mothers":         len(alive),
            })

    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(snapshots, f, indent=2)

    # Pearson r
    r = None
    birth_log = os.path.join(output_dir, "birth_log.csv")
    if os.path.exists(birth_log):
        with open(birth_log) as f:
            rows = list(csv.DictReader(f))
        if len(rows) >= 10:
            r = _pearson_r([float(x["mother_care_weight"]) for x in rows],
                           [float(x["mother_generation"])  for x in rows])

    alive_final = [m for m in sim.mothers if m.alive]
    n_alive     = len(alive_final)
    final_cw    = sum(m.genome.care_weight for m in alive_final) / n_alive if n_alive else 0.0
    fallback    = sim.genome_fallback_count

    print(f"  seed={seed} | r={r:+.4f} | final_cw={final_cw:.3f} | "
          f"n={n_alive} | genome_fallback={fallback}")

    return {
        "seed":                 seed,
        "pearson_r":            r,
        "final_cw":             final_cw,
        "init_cw":              INIT_CARE,
        "n_alive":              n_alive,
        "genome_fallback_count": fallback,
        "snapshots":            snapshots,
    }


# -- Multi-seed run -----------------------------------------------------------

def run_all():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(OUT_DIR,  exist_ok=True)
    os.makedirs(SNAP_DIR, exist_ok=True)

    ckpt = os.path.join(OUT_DIR, "checkpoint.json")
    results = []

    if os.path.exists(ckpt):
        with open(ckpt) as f:
            results = json.load(f)
        done = {r["seed"] for r in results}
        print(f"[Checkpoint] {len(done)}/10 seeds already done: {sorted(done)}")
    else:
        done = set()

    for seed in SEEDS:
        if seed in done:
            continue
        print(f"\n[seed={seed}] Running ceiling-drop FIXED ...")
        res = run_one(seed)
        results.append(res)
        # Save seed snapshot for comparison script
        with open(os.path.join(SNAP_DIR, f"seed{seed}.json"), "w") as f:
            json.dump(res["snapshots"], f)
        with open(ckpt, "w") as f:
            json.dump(results, f, indent=2, default=str)

    # -- Statistics -----------------------------------------------------------
    rs    = [r["pearson_r"] for r in results if r["pearson_r"] is not None]
    n_neg = sum(1 for r in rs if r < 0)
    n_pos = sum(1 for r in rs if r > 0)
    mean_r = sum(rs) / len(rs)
    sd_r   = _variance(rs) ** 0.5

    total_fallback = sum(r["genome_fallback_count"] for r in results)

    stats = {
        "experiment":          "05_ceiling_drop_FIXED",
        "bug_fix":             "genome assigned at birth",
        "init_care":           INIT_CARE,
        "n_seeds":             len(rs),
        "mean_r":              mean_r,
        "sd_r":                sd_r,
        "n_negative_seeds":    n_neg,
        "total_genome_fallback": total_fallback,
        "per_seed_r":          {r["seed"]: r["pearson_r"]  for r in results},
        "per_seed_final_cw":   {r["seed"]: r["final_cw"]   for r in results},
        "per_seed_fallback":   {r["seed"]: r["genome_fallback_count"] for r in results},
    }
    with open(os.path.join(OUT_DIR, "statistical_results.json"), "w") as f:
        json.dump(stats, f, indent=2)

    # -- Terminal summary table -----------------------------------------------
    print(f"\n{'='*70}")
    print(f"  Script 05 — CEILING-DROP FIXED  (infant_mult={INFANT_MULT}, feed_cost={FEED_COST})")
    print(f"{'='*70}")
    print(f"  {'Seed':>6}  {'Init care':>9}  {'Final care':>10}  {'Pearson r':>10}  {'Fallbacks':>10}")
    print(f"  {'-'*60}")
    for r in sorted(results, key=lambda x: x["seed"]):
        rval = f"{r['pearson_r']:+.4f}" if r["pearson_r"] is not None else "  N/A"
        print(f"  {r['seed']:>6}  {r['init_cw']:>9.3f}  {r['final_cw']:>10.3f}  "
              f"{rval:>10}  {r['genome_fallback_count']:>10}")
    print(f"  {'-'*60}")
    print(f"  {'MEAN':>6}  {INIT_CARE:>9.3f}  "
          f"{sum(r['final_cw'] for r in results)/len(results):>10.3f}  "
          f"{mean_r:>+10.4f}  {total_fallback:>10}")
    print(f"{'='*70}")
    print(f"  Negative seeds: {n_neg}/10  |  Total Genome() fallbacks: {total_fallback}")
    if total_fallback == 0:
        print(f"  [OK] genome_fallback_count = 0 across all seeds — bug confirmed fixed.")
    else:
        print(f"  [WARN] genome_fallback_count = {total_fallback} — investigate!")
    print(f"{'='*70}\n")

    # -- Trajectory plot ------------------------------------------------------
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("seaborn-whitegrid")

    fig, ax = plt.subplots(figsize=(10, 5))
    all_t, all_cw = [], []
    for res in results:
        snaps = res["snapshots"]
        if snaps:
            t  = [s["tick"] for s in snaps]
            cw = [s["avg_care_weight"] for s in snaps]
            ax.plot(t, cw, color="#4C72B0", alpha=0.25, linewidth=1)
            all_t.append(t); all_cw.append(cw)

    if all_cw:
        min_len = min(len(x) for x in all_cw)
        t_common = all_t[0][:min_len]
        mean_traj = [sum(c[i] for c in all_cw) / len(all_cw) for i in range(min_len)]
        sd_traj   = [(_variance([c[i] for c in all_cw])) ** 0.5 for i in range(min_len)]
        ax.plot(t_common, mean_traj, color="#4C72B0", linewidth=2.5, label="Ceiling-drop FIXED (mean)")
        ax.fill_between(t_common, [m-s for m,s in zip(mean_traj,sd_traj)],
                                  [m+s for m,s in zip(mean_traj,sd_traj)],
                        color="#4C72B0", alpha=0.15)

    ax.axhline(INIT_CARE, color="grey", linestyle="--", linewidth=1.2, label="Init ceiling (0.80)")
    ax.set_xlabel("Tick", fontsize=11)
    ax.set_ylabel("Mean care_weight", fontsize=11)
    ax.set_ylim(0, 1)
    ax.set_title(f"Script 05 — Ceiling-Drop FIXED  |  Mean r={mean_r:+.4f}  |  Fallbacks={total_fallback}",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "trajectory.png"), dpi=150, facecolor="white")
    plt.close()
    print(f"Plots saved to {OUT_DIR}")


if __name__ == "__main__":
    run_all()
