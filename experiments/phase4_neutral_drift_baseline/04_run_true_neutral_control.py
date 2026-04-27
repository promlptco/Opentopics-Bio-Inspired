"""Phase 4 -- Step 4: True Neutral Control

PURPOSE
-------
Resolve the open question from Steps 02 and 03:

  Is the 0.80 -> 0.50 erosion of care_weight genuine natural selection
  (care is metabolically costly) or pure bounded mutation drift
  (any weight above 0.50 drifts toward the [0,1] midpoint)?

Previous neutral attempt (03) used children=OFF, which caused extinction
because reproduction was removed. No generational turnover = no drift to
measure.

FIX -- True Neutral: keep reproduction fully active, but strip BOTH sides
of care's fitness effect:
  - infant_starvation_multiplier = 0.0  (children never accumulate hunger;
    CARE confers zero benefit -- child survival is unconditional)
  - feed_cost = 0.0                     (mothers lose zero energy when caring;
    CARE has zero metabolic cost)

With both levers at zero, care_weight is INVISIBLE to selection. Any
trajectory change is PURELY bounded mutation drift.

HYPOTHESIS
----------
  Drift theory TRUE  -> care_weight still erodes 0.80 -> ~0.50,
                        matching the ceiling-drop baseline (02).
  Selection TRUE     -> care_weight stays near 0.80 (no pressure to erode).

PROTOCOL
--------
  care_weight init             = 0.80  (identical to 02)
  forage_weight init           = 1.00  (identical to 02)
  self_weight init             = U(0, 1)
  grid                         = 50 x 50
  init_mothers                 = 40
  init_food                    = 120
  infant_starvation_multiplier = 0.0   <-- KEY CHANGE
  feed_cost                    = 0.0   <-- KEY CHANGE
  birth_scatter_radius         = 5
  plasticity                   = OFF
  mutation                     = ON
  duration                     = 10,000 ticks
  seeds                        = 42-51 (10 seeds)

OUTPUTS
-------
  outputs/phase4_neutral_drift_baseline/04_true_neutral_control/
    trajectory_all_weights.png   -- care/forage/self trajectories (neutral)
    comparison_vs_baseline.png   -- neutral care vs ceiling-drop care overlay
    statistical_results.json     -- per-seed Pearson r, final weights
    checkpoint.json              -- resumable checkpoint
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

PHASE_NAME        = "phase4_neutral_drift_baseline/04_true_neutral_control"
INFANT_MULT       = 0.0   # children never starve -- zero benefit from care
FEED_COST         = 0.0   # mothers lose no energy from caring -- zero cost
BIRTH_SCATTER     = 5
INIT_CARE         = 0.8
INIT_FORAGE       = 1.0
GRID_SIZE         = 50
INIT_MOTHERS      = 40
INIT_FOOD         = 120
SNAPSHOT_INTERVAL = 200
SEEDS             = list(range(42, 52))
OUT_DIR           = os.path.join(PROJECT_ROOT, "outputs", PHASE_NAME)

BASELINE_SNAPS_GLOB = os.path.join(
    PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
    "02_ceiling_drop_erosion", "seed_snapshots", "*.json"
)


# -- Helpers ------------------------------------------------------------------

def _variance(values: list) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return sum((x - m) ** 2 for x in values) / (n - 1)


def _pearson_r(xs: list, ys: list):
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


def _binom_p(n: int, k: int, p: float = 0.5) -> float:
    from math import comb
    return sum(comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


def _make_genomes(n: int) -> list:
    return [
        Genome(
            care_weight=INIT_CARE,
            forage_weight=INIT_FORAGE,
            self_weight=_random.uniform(0.0, 1.0),
        )
        for _ in range(n)
    ]


# -- Single-seed run ----------------------------------------------------------

def run_one(seed: int) -> dict:
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
    save_metadata(
        output_dir,
        phase=PHASE_NAME,
        seed=seed,
        num_agents=INIT_MOTHERS * 2,
        infant_starvation_multiplier=INFANT_MULT,
        feed_cost=FEED_COST,
        note=(
            "Phase 4 True Neutral Control. "
            "infant_starvation_multiplier=0.0 (children invincible), "
            "feed_cost=0.0 (no CARE energy cost). "
            "care_weight has ZERO fitness effect. "
            f"care_init={INIT_CARE}, forage_init={INIT_FORAGE}, "
            f"grid={GRID_SIZE}x{GRID_SIZE}, N={INIT_MOTHERS}, food={INIT_FOOD}."
        ),
    )

    genomes = _make_genomes(INIT_MOTHERS)
    sim     = Simulation(config)
    sim.initialize(genomes)

    generation_snapshots = []

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        alive_m = [m for m in sim.mothers if m.alive]

        if sim.tick % SNAPSHOT_INTERVAL == 0 and alive_m:
            cw = [m.genome.care_weight   for m in alive_m]
            fw = [m.genome.forage_weight for m in alive_m]
            sw = [m.genome.self_weight   for m in alive_m]
            generation_snapshots.append({
                "tick":              sim.tick,
                "avg_care_weight":   sum(cw) / len(cw),
                "var_care_weight":   _variance(cw),
                "avg_forage_weight": sum(fw) / len(fw),
                "avg_self_weight":   sum(sw) / len(sw),
                "avg_generation":    sum(m.generation for m in alive_m) / len(alive_m),
                "max_generation":    max(m.generation for m in alive_m),
                "n_mothers":         len(alive_m),
            })

    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(generation_snapshots, f, indent=2)

    # Pearson r(care_weight, generation) from birth_log
    birth_log = os.path.join(output_dir, "birth_log.csv")
    r = None
    if os.path.exists(birth_log):
        with open(birth_log) as f:
            rows = list(csv.DictReader(f))
        if len(rows) >= 10:
            cw_all  = [float(row["mother_care_weight"]) for row in rows]
            gen_all = [float(row["mother_generation"])  for row in rows]
            r = _pearson_r(cw_all, gen_all)

    alive_final = [m for m in sim.mothers if m.alive]
    n_alive     = len(alive_final)
    final_cw    = sum(m.genome.care_weight   for m in alive_final) / n_alive if n_alive else 0.0
    final_fw    = sum(m.genome.forage_weight for m in alive_final) / n_alive if n_alive else 0.0
    final_sw    = sum(m.genome.self_weight   for m in alive_final) / n_alive if n_alive else 0.0
    final_gen   = max(m.generation for m in alive_final) if alive_final else 0

    r_str = f"{r:+.4f}" if r is not None else "None"
    print(f"  seed={seed} | r={r_str} | "
          f"care={final_cw:.3f} | forage={final_fw:.3f} | self={final_sw:.3f} | "
          f"n={n_alive} | max_gen={final_gen}")

    return {
        "seed":        seed,
        "output_dir":  output_dir,
        "pearson_r":   r,
        "final_care":  final_cw,
        "final_forage": final_fw,
        "final_self":  final_sw,
        "n_alive":     n_alive,
        "final_gen":   final_gen,
        "snapshots":   generation_snapshots,
    }


# -- Load baseline (02) snapshots for comparison ------------------------------

def _load_baseline_snaps():
    paths = sorted(glob.glob(BASELINE_SNAPS_GLOB))
    if not paths:
        print(f"  WARNING: No baseline snapshots found at {BASELINE_SNAPS_GLOB}")
        return []
    snaps = []
    for p in paths:
        with open(p) as f:
            raw = json.load(f)
        # Normalize keys to avg_care_weight (already in that format)
        snaps.append(raw)
    return snaps


# -- Averaging helper ---------------------------------------------------------

def _avg_traj(snaps_list, key):
    min_len = min(len(s) for s in snaps_list)
    ticks   = [snaps_list[0][i]["tick"] for i in range(min_len)]
    means   = [sum(s[i][key] for s in snaps_list) / len(snaps_list) for i in range(min_len)]
    return ticks, means


# -- Plots --------------------------------------------------------------------

def plot_all(results, baseline_snaps):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("seaborn-whitegrid")

    neutral_snaps = [r["snapshots"] for r in results if r["snapshots"]]

    # -- Plot 1: All-weights trajectory (neutral control) ---------------------
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)

    weight_cfg = [
        ("avg_care_weight",   "#4C72B0", "care_weight",   INIT_CARE,   axes[0]),
        ("avg_forage_weight", "#2ca02c", "forage_weight", INIT_FORAGE, axes[1]),
        ("avg_self_weight",   "#8C8C8C", "self_weight",   0.50,        axes[2]),
    ]

    for key, color, label, init_val, ax in weight_cfg:
        for snaps in neutral_snaps:
            t = [s["tick"]  for s in snaps]
            v = [s[key]     for s in snaps]
            ax.plot(t, v, color=color, alpha=0.2, linewidth=1)

        if neutral_snaps:
            t_m, m_vals = _avg_traj(neutral_snaps, key)
            ax.plot(t_m, m_vals, color=color, linewidth=2.5, label=f"Mean {label}")

        ax.axhline(init_val, color="grey",  linestyle="--", linewidth=1.2,
                   label=f"Init ({init_val})")
        ax.axhline(0.5,      color="red",   linestyle=":",  linewidth=1.0,
                   label="0.5 midpoint")
        ax.set_ylim(0, 1.1)
        ax.set_xlabel("Simulation tick", fontsize=10)
        ax.set_ylabel("Mean weight",     fontsize=10)
        ax.set_title(label, fontsize=10, fontweight="bold")
        leg = ax.legend(fontsize=8, framealpha=0.6)
        leg.get_frame().set_alpha(0.6)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle(
        "Phase 4 -- True Neutral Control  "
        "(infant_starvation_mult=0.0, feed_cost=0.0)\n"
        "care_weight has ZERO fitness effect -- any change is pure mutation drift",
        fontsize=11, fontweight="bold"
    )
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "trajectory_all_weights.png"),
                dpi=150, facecolor="white", bbox_inches="tight")
    plt.close()
    print("  Saved: trajectory_all_weights.png")

    # -- Plot 2: Comparison -- neutral care vs ceiling-drop care --------------
    fig, ax = plt.subplots(figsize=(11, 6))

    # Neutral trajectories (individual seeds, faint)
    for snaps in neutral_snaps:
        t = [s["tick"]            for s in snaps]
        v = [s["avg_care_weight"] for s in snaps]
        ax.plot(t, v, color="#C44E52", alpha=0.18, linewidth=1)

    # Neutral mean trajectory
    if neutral_snaps:
        t_n, m_n = _avg_traj(neutral_snaps, "avg_care_weight")
        sd_n = [_variance([s[i]["avg_care_weight"] for s in neutral_snaps]) ** 0.5
                for i in range(len(t_n))]
        ax.plot(t_n, m_n, color="#C44E52", linewidth=2.5,
                label="True Neutral mean care  (cost=0, benefit=0)")
        ax.fill_between(t_n,
                        [m - s for m, s in zip(m_n, sd_n)],
                        [m + s for m, s in zip(m_n, sd_n)],
                        color="#C44E52", alpha=0.12)

    # Baseline (02 ceiling-drop) trajectories (individual seeds, faint)
    for snaps in baseline_snaps:
        t = [s["tick"]            for s in snaps]
        v = [s["avg_care_weight"] for s in snaps]
        ax.plot(t, v, color="#4C72B0", alpha=0.18, linewidth=1)

    # Baseline mean trajectory
    if baseline_snaps:
        t_b, m_b = _avg_traj(baseline_snaps, "avg_care_weight")
        sd_b = [_variance([s[i]["avg_care_weight"] for s in baseline_snaps]) ** 0.5
                for i in range(len(t_b))]
        ax.plot(t_b, m_b, color="#4C72B0", linewidth=2.5,
                label="Ceiling-drop baseline mean care  (cost=0.03, mult=1.0)")
        ax.fill_between(t_b,
                        [m - s for m, s in zip(m_b, sd_b)],
                        [m + s for m, s in zip(m_b, sd_b)],
                        color="#4C72B0", alpha=0.12)

    ax.axhline(INIT_CARE, color="grey", linestyle="--", linewidth=1.2,
               label=f"Init ceiling ({INIT_CARE})")
    ax.axhline(0.5, color="black", linestyle=":", linewidth=1.0,
               label="0.5 midpoint (drift attractor)")

    ax.set_ylim(0.3, 0.95)
    ax.set_xlabel("Simulation tick", fontsize=12)
    ax.set_ylabel("Mean care_weight", fontsize=12)
    ax.set_title(
        "Phase 4 -- True Neutral vs Ceiling-Drop Baseline\n"
        "If curves OVERLAP: erosion is pure drift.  "
        "If neutral STAYS HIGH: erosion was selection.",
        fontsize=11, fontweight="bold", linespacing=1.6
    )
    leg = ax.legend(fontsize=10, framealpha=0.7, loc="upper right")
    leg.get_frame().set_alpha(0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "comparison_vs_baseline.png"),
                dpi=150, facecolor="white", bbox_inches="tight")
    plt.close()
    print("  Saved: comparison_vs_baseline.png")


# -- Main ---------------------------------------------------------------------

def run_all():
    os.makedirs(OUT_DIR, exist_ok=True)

    ckpt = os.path.join(OUT_DIR, "checkpoint.json")
    results = []

    if os.path.exists(ckpt):
        with open(ckpt) as f:
            results = json.load(f)
        done = {r["seed"] for r in results}
        print(f"[Checkpoint] {len(done)}/10 seeds already done: {sorted(done)}")
    else:
        done = set()

    print(f"\nTrue Neutral Control -- infant_mult={INFANT_MULT}, feed_cost={FEED_COST}")
    print(f"Grid={GRID_SIZE}x{GRID_SIZE}, N={INIT_MOTHERS}, food={INIT_FOOD}, ticks=10k\n")

    for seed in SEEDS:
        if seed in done:
            continue
        print(f"[seed={seed}] Running ...")
        res = run_one(seed)
        results.append(res)
        with open(ckpt, "w") as f:
            json.dump(results, f, indent=2, default=str)

    # Statistics
    rs    = [r["pearson_r"] for r in results if r["pearson_r"] is not None]
    n_neg = sum(1 for r in rs if r < 0)
    n_pos = sum(1 for r in rs if r > 0)
    mean_r = sum(rs) / len(rs) if rs else 0.0
    sd_r   = _variance(rs) ** 0.5 if rs else 0.0
    binom_neg = _binom_p(len(rs), n_neg) if rs else 1.0

    stats = {
        "experiment":              "true_neutral_control",
        "infant_starvation_mult":  INFANT_MULT,
        "feed_cost":               FEED_COST,
        "init_care":               INIT_CARE,
        "grid":                    f"{GRID_SIZE}x{GRID_SIZE}",
        "init_mothers":            INIT_MOTHERS,
        "n_seeds":                 len(rs),
        "mean_r":                  mean_r,
        "sd_r":                    sd_r,
        "n_negative_seeds":        n_neg,
        "n_positive_seeds":        n_pos,
        "binom_p_negative":        binom_neg,
        "per_seed_r":              {r["seed"]: r["pearson_r"] for r in results},
        "per_seed_final_care":     {r["seed"]: r["final_care"]  for r in results},
        "per_seed_final_forage":   {r["seed"]: r["final_forage"] for r in results},
        "per_seed_final_self":     {r["seed"]: r["final_self"]   for r in results},
    }
    with open(os.path.join(OUT_DIR, "statistical_results.json"), "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n{'='*62}")
    print(f"  TRUE NEUTRAL CONTROL -- Phase 4")
    print(f"  infant_mult={INFANT_MULT}  feed_cost={FEED_COST}")
    print(f"  Mean r = {mean_r:+.4f}  (SD={sd_r:.4f})")
    print(f"  Negative seeds: {n_neg}/10  (p={binom_neg:.4f})")
    per_r  = [f"{r['pearson_r']:+.3f}" if r["pearson_r"] is not None else "None"
              for r in results]
    per_c  = [f"{r['final_care']:.3f}"   for r in results]
    per_f  = [f"{r['final_forage']:.3f}" for r in results]
    print(f"  Per-seed r:          {per_r}")
    print(f"  Final care_weight:   {per_c}")
    print(f"  Final forage_weight: {per_f}")

    if n_neg >= 9:
        verdict = "DRIFT CONFIRMED -- care erodes even with zero fitness effect"
    elif n_pos >= 9:
        verdict = "STAYS HIGH -- erosion was selection-driven, not drift"
    else:
        verdict = "MIXED -- partial drift, partial selection"
    print(f"  Verdict: {verdict}")
    print(f"{'='*62}\n")

    print("Loading baseline snapshots for comparison plot ...")
    baseline_snaps = _load_baseline_snaps()
    print(f"  Baseline seeds loaded: {len(baseline_snaps)}")

    print("Generating plots ...")
    plot_all(results, baseline_snaps)
    print(f"\nAll outputs: {OUT_DIR}")


if __name__ == "__main__":
    run_all()
