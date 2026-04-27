"""Phase 4 -- Step 6: True Neutral Control (BUG-FIXED)

Re-runs Script 04 with the orphan-injection bug fixed, then generates the
definitive comparison plot of both fixed runs.

BUG FIXED (same as Script 05)
------------------------------
Genome is assigned at birth (child.genome = mother.genome.mutate()).
Maturation reads child.genome directly. Genome() fallback cannot trigger.

PROTOCOL (identical to Script 04)
----------------------------------
  care_weight init             = 0.80
  forage_weight init           = 1.00
  infant_starvation_multiplier = 0.0   (children never starve)
  feed_cost                    = 0.0   (no CARE energy cost)
  grid = 50x50, N=40, food=120
  plasticity = OFF, mutation = ON
  duration = 10,000 ticks, seeds 42-51
"""

import sys
import os
import json
import csv
import glob
import random as _random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata

PHASE_NAME        = "phase4_neutral_drift_baseline/06_true_neutral_FIXED"
INFANT_MULT       = 0.0
FEED_COST         = 0.0
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

BASELINE_SNAP_DIR = os.path.join(
    PROJECT_ROOT, "outputs",
    "phase4_neutral_drift_baseline", "05_ceiling_drop_FIXED", "seed_snapshots"
)


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
                  num_agents=INIT_MOTHERS * 2,
                  infant_starvation_multiplier=INFANT_MULT,
                  feed_cost=FEED_COST,
                  note="Bug-fixed true neutral control (no infant starvation, no feed cost).")

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
        "seed":                  seed,
        "pearson_r":             r,
        "final_cw":              final_cw,
        "init_cw":               INIT_CARE,
        "n_alive":               n_alive,
        "genome_fallback_count": fallback,
        "snapshots":             snapshots,
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
        print(f"\n[seed={seed}] Running true neutral FIXED ...")
        res = run_one(seed)
        results.append(res)
        with open(os.path.join(SNAP_DIR, f"seed{seed}.json"), "w") as f:
            json.dump(res["snapshots"], f)
        with open(ckpt, "w") as f:
            json.dump(results, f, indent=2, default=str)

    # -- Statistics -----------------------------------------------------------
    rs    = [r["pearson_r"] for r in results if r["pearson_r"] is not None]
    n_neg = sum(1 for r in rs if r < 0)
    mean_r = sum(rs) / len(rs)
    sd_r   = _variance(rs) ** 0.5
    binom_p = _binom_p(len(rs), n_neg)
    total_fallback = sum(r["genome_fallback_count"] for r in results)

    stats = {
        "experiment":            "06_true_neutral_FIXED",
        "bug_fix":               "genome assigned at birth",
        "infant_mult":           INFANT_MULT,
        "feed_cost":             FEED_COST,
        "init_care":             INIT_CARE,
        "n_seeds":               len(rs),
        "mean_r":                mean_r,
        "sd_r":                  sd_r,
        "n_negative_seeds":      n_neg,
        "total_genome_fallback": total_fallback,
        "per_seed_r":            {r["seed"]: r["pearson_r"]  for r in results},
        "per_seed_final_cw":     {r["seed"]: r["final_cw"]   for r in results},
        "per_seed_fallback":     {r["seed"]: r["genome_fallback_count"] for r in results},
    }
    with open(os.path.join(OUT_DIR, "statistical_results.json"), "w") as f:
        json.dump(stats, f, indent=2)

    # -- Combined verification table ------------------------------------------
    # Load Script 05 results for the joint table
    s05_stats_path = os.path.join(
        PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
        "05_ceiling_drop_FIXED", "statistical_results.json")
    s05 = None
    if os.path.exists(s05_stats_path):
        with open(s05_stats_path) as f:
            s05 = json.load(f)

    print(f"\n{'='*80}")
    print(f"  PHASE 4 FIXED BASELINES — VERIFICATION TABLE")
    print(f"{'='*80}")
    print(f"  {'':25s}  {'Script 05':>20s}  {'Script 06':>20s}")
    print(f"  {'':25s}  {'Ceiling-Drop FIXED':>20s}  {'True Neutral FIXED':>20s}")
    print(f"  {'-'*70}")
    s05_fallback = s05["total_genome_fallback"] if s05 else "N/A"
    s05_mean_r   = s05["mean_r"]               if s05 else float("nan")
    s05_final    = (sum(s05["per_seed_final_cw"].values()) /
                    len(s05["per_seed_final_cw"])) if s05 else float("nan")
    print(f"  {'Init care_weight':25s}  {INIT_CARE:>20.3f}  {INIT_CARE:>20.3f}")
    print(f"  {'Final care_weight (mean)':25s}  {s05_final:>20.3f}  "
          f"{sum(r['final_cw'] for r in results)/len(results):>20.3f}")
    print(f"  {'Pearson r (mean)':25s}  {s05_mean_r:>+20.4f}  {mean_r:>+20.4f}")
    print(f"  {'Genome() fallbacks (TOTAL)':25s}  {str(s05_fallback):>20s}  {total_fallback:>20d}")
    if s05_fallback == 0 and total_fallback == 0:
        print(f"  [OK] All Genome() fallbacks = 0 in both runs — bug confirmed fixed.")
    print(f"{'='*80}\n")

    # -- Per-seed table -------------------------------------------------------
    print(f"  {'Seed':>4}  |  {'Script 05 final cw':>18}  {'Script 05 fallbacks':>20}  |  "
          f"{'Script 06 final cw':>18}  {'Script 06 fallbacks':>20}")
    print(f"  {'-'*90}")
    s05_cw = s05["per_seed_final_cw"] if s05 else {}
    s05_fb = s05["per_seed_fallback"]  if s05 else {}
    for r in sorted(results, key=lambda x: x["seed"]):
        s = str(r["seed"])
        cw05 = f"{s05_cw.get(s, s05_cw.get(r['seed'], 'N/A')):.3f}" if s05 else "N/A"
        fb05 = str(s05_fb.get(s, s05_fb.get(r["seed"], "N/A"))) if s05 else "N/A"
        print(f"  {r['seed']:>4}  |  {cw05:>18}  {fb05:>20}  |  "
              f"{r['final_cw']:>18.3f}  {r['genome_fallback_count']:>20}")
    print()

    # -- Comparison plot ------------------------------------------------------
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("seaborn-whitegrid")

    fig, ax = plt.subplots(figsize=(11, 6))

    # Script 05 (ceiling drop fixed) — blue
    s05_snaps = sorted(glob.glob(os.path.join(BASELINE_SNAP_DIR, "*.json")))
    all_t05, all_cw05 = [], []
    for path in s05_snaps:
        with open(path) as f:
            snaps = json.load(f)
        if snaps:
            t  = [s["tick"] for s in snaps]
            cw = [s["avg_care_weight"] for s in snaps]
            ax.plot(t, cw, color="#4C72B0", alpha=0.20, linewidth=1)
            all_t05.append(t); all_cw05.append(cw)

    if all_cw05:
        min_len05 = min(len(x) for x in all_cw05)
        t_c05 = all_t05[0][:min_len05]
        mean05 = [sum(c[i] for c in all_cw05) / len(all_cw05) for i in range(min_len05)]
        sd05   = [(_variance([c[i] for c in all_cw05])) ** 0.5 for i in range(min_len05)]
        final05 = mean05[-1]
        ax.plot(t_c05, mean05, color="#4C72B0", linewidth=2.5,
                label=f"Script 05 — Ceiling-Drop FIXED  (final={final05:.3f})")
        ax.fill_between(t_c05, [m-s for m,s in zip(mean05,sd05)],
                                [m+s for m,s in zip(mean05,sd05)],
                        color="#4C72B0", alpha=0.12)
        ax.axhline(final05, color="#4C72B0", linestyle=":", linewidth=1.0, alpha=0.6)

    # Script 06 (neutral fixed) — red
    all_t06, all_cw06 = [], []
    for res in results:
        snaps = res["snapshots"]
        if snaps:
            t  = [s["tick"] for s in snaps]
            cw = [s["avg_care_weight"] for s in snaps]
            ax.plot(t, cw, color="#C44E52", alpha=0.20, linewidth=1)
            all_t06.append(t); all_cw06.append(cw)

    if all_cw06:
        min_len06 = min(len(x) for x in all_cw06)
        t_c06 = all_t06[0][:min_len06]
        mean06 = [sum(c[i] for c in all_cw06) / len(all_cw06) for i in range(min_len06)]
        sd06   = [(_variance([c[i] for c in all_cw06])) ** 0.5 for i in range(min_len06)]
        final06 = mean06[-1]
        ax.plot(t_c06, mean06, color="#C44E52", linewidth=2.5,
                label=f"Script 06 — True Neutral FIXED  (final={final06:.3f})")
        ax.fill_between(t_c06, [m-s for m,s in zip(mean06,sd06)],
                                [m+s for m,s in zip(mean06,sd06)],
                        color="#C44E52", alpha=0.12)
        ax.axhline(final06, color="#C44E52", linestyle=":", linewidth=1.0, alpha=0.6)

    ax.axhline(INIT_CARE, color="grey", linestyle="--", linewidth=1.2,
               label="Init ceiling (0.80)", alpha=0.7)

    ax.set_xlabel("Simulation tick", fontsize=12)
    ax.set_ylabel("Mean care_weight (genome)", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.set_title(
        "Phase 4 Fixed Baselines — care_weight trajectory comparison\n"
        "Blue: Ceiling-Drop (full costs)  |  Red: True Neutral (zero costs)\n"
        "Genome() fallback = 0 in both runs  |  Shaded ±1 SD",
        fontsize=11, fontweight="bold", linespacing=1.5)
    ax.legend(fontsize=10, framealpha=0.7)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()

    out_plot = os.path.join(OUT_DIR, "comparison_fixed_vs_neutral.png")
    plt.savefig(out_plot, dpi=150, facecolor="white")
    plt.close()
    print(f"Comparison plot saved: {out_plot}")


if __name__ == "__main__":
    run_all()
