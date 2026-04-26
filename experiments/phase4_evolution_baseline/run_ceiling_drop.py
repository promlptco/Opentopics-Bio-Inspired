"""Phase 4 Recheck: Ceiling Drop Experiment

Addresses three methodological critiques of the original Phase 4 result
(mean r = +0.0593, 8/10 seeds positive, p = 0.055):

  1. Floor effect: U(0,1) init leaves care<0.3 non-viable (Phase 3 shows
     lethal below 0.10, transitional 0.10-0.25). Mutants that drop below
     the floor die, so the surviving mean can only bounce UP — confounding
     any erosion signal.
     FIX: Initialize all mothers at care=0.8. If care is costly, it must
     erode DOWN toward the floor. No floor-bounce can produce a spurious
     positive r from this ceiling.

  2. Genetic drift: N=12 mothers → small population → early generations
     dominated by drift, not selection.
     FIX: init_mothers=40, grid=50x50, init_food=120 (same density).

  3. Hitchhiking / lineage test: Seed-level Pearson r is coarse. Need
     per-lineage correlation between founder care_weight and total
     descendants produced (reproductive success).
     FIX: Analyse birth_log by lineage_id — correlate mean lineage
     care_weight vs lineage descendant count.

Protocol:
  care_weight init         = 0.8 (all mothers identical)
  forage_weight init       = 1.0 (all mothers identical)
  self_weight init         = U(0, 1)
  grid                     = 50 x 50
  init_mothers             = 40
  init_food                = 120
  infant_starvation_mult   = 1.0
  birth_scatter_radius     = 5
  plasticity               = OFF
  mutation                 = ON  (rate=0.1, sigma=0.05)
  duration                 = 10,000 ticks
  seeds                    = 42–51 (10 seeds)

Primary question:
  Does care_weight erode from 0.8 toward the viable minimum (~0.3)?
  YES => care IS costly; original r>0 was a floor-bounce artefact.
  NO  => care is genuinely near-neutral at this ecology.
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

PHASE_NAME       = "phase4_evolution_baseline"
INFANT_MULT      = 1.0
BIRTH_SCATTER    = 5
INIT_CARE        = 0.8
INIT_FORAGE      = 1.0
GRID_SIZE        = 50
INIT_MOTHERS     = 40
INIT_FOOD        = 120
SNAPSHOT_INTERVAL = 200
SEEDS            = list(range(42, 52))
OUT_DIR          = os.path.join(PROJECT_ROOT, "outputs", PHASE_NAME, "ceiling_drop")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_ceiling_genomes(n: int) -> list:
    return [
        Genome(
            care_weight=INIT_CARE,
            forage_weight=INIT_FORAGE,
            self_weight=_random.uniform(0.0, 1.0),
        )
        for _ in range(n)
    ]


def _variance(values: list) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return sum((x - m) ** 2 for x in values) / (n - 1)


def _pearson_r(xs: list, ys: list) -> float | None:
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
    """P(X >= k) for Binomial(n, p)."""
    from math import comb
    return sum(comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


# ── Lineage analysis from birth_log ──────────────────────────────────────────

def analyse_lineage(birth_log_path: str) -> dict:
    """
    Per-lineage analysis:
      - mean_care:   mean care_weight of all births from that lineage
      - n_desc:      total births (descendants) from that lineage
    Returns Pearson r(mean_care, n_desc).
    """
    if not os.path.exists(birth_log_path):
        return {"r_care_vs_descendants": None, "n_lineages": 0}

    lineage_births: dict[int, list] = {}
    with open(birth_log_path) as f:
        for row in csv.DictReader(f):
            lid = int(row["mother_lineage_id"])
            cw  = float(row["mother_care_weight"])
            lineage_births.setdefault(lid, []).append(cw)

    if len(lineage_births) < 5:
        return {"r_care_vs_descendants": None, "n_lineages": len(lineage_births)}

    mean_cares = [sum(v) / len(v) for v in lineage_births.values()]
    n_descs    = [len(v) for v in lineage_births.values()]

    r = _pearson_r(mean_cares, n_descs)
    return {
        "r_care_vs_descendants": r,
        "n_lineages": len(lineage_births),
        "mean_cares": mean_cares,
        "n_descs":    n_descs,
    }


# ── Single-seed run ───────────────────────────────────────────────────────────

def run_one(seed: int) -> dict:
    config = Config()
    config.seed                         = seed
    config.width                        = GRID_SIZE
    config.height                       = GRID_SIZE
    config.init_mothers                 = INIT_MOTHERS
    config.init_food                    = INIT_FOOD
    config.max_ticks                    = 10_000
    config.infant_starvation_multiplier = INFANT_MULT
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
        birth_scatter_radius=BIRTH_SCATTER,
        plasticity_enabled=False,
        note=(
            "Phase 4 Recheck — Ceiling Drop. "
            f"care_init={INIT_CARE}, forage_init={INIT_FORAGE}, "
            f"grid={GRID_SIZE}x{GRID_SIZE}, N={INIT_MOTHERS}, food={INIT_FOOD}."
        ),
    )

    genomes = _make_ceiling_genomes(INIT_MOTHERS)
    sim     = Simulation(config)
    sim.initialize(genomes)

    population_history   = []
    energy_history       = []
    generation_snapshots = []

    while sim.tick < config.max_ticks:
        sim.step()
        sim.tick += 1
        alive_m = [m for m in sim.mothers if m.alive]
        population_history.append(len(alive_m))
        energy_history.append(
            sum(m.energy for m in alive_m) / len(alive_m) if alive_m else 0.0
        )
        if sim.tick % SNAPSHOT_INTERVAL == 0 and alive_m:
            cw = [m.genome.care_weight   for m in alive_m]
            fw = [m.genome.forage_weight for m in alive_m]
            sw = [m.genome.self_weight   for m in alive_m]
            generation_snapshots.append({
                "tick":              sim.tick,
                "avg_care_weight":   sum(cw) / len(cw),
                "var_care_weight":   _variance(cw),
                "min_care_weight":   min(cw),
                "max_care_weight":   max(cw),
                "avg_forage_weight": sum(fw) / len(fw),
                "avg_self_weight":   sum(sw) / len(sw),
                "avg_generation":    sum(m.generation for m in alive_m) / len(alive_m),
                "max_generation":    max(m.generation for m in alive_m),
                "n_mothers":         len(alive_m),
            })

    sim.logger.save_all(output_dir)
    with open(os.path.join(output_dir, "population_history.json"), "w") as f:
        json.dump({"population": population_history, "energy": energy_history}, f)
    with open(os.path.join(output_dir, "generation_snapshots.json"), "w") as f:
        json.dump(generation_snapshots, f, indent=2)

    birth_log = os.path.join(output_dir, "birth_log.csv")

    # Pearson r(care_weight, generation)
    r = None
    if os.path.exists(birth_log):
        with open(birth_log) as f:
            rows = list(csv.DictReader(f))
        if len(rows) >= 10:
            cw_all  = [float(r["mother_care_weight"]) for r in rows]
            gen_all = [float(r["mother_generation"])  for r in rows]
            r = _pearson_r(cw_all, gen_all)

    lineage = analyse_lineage(birth_log)

    alive_final = [m for m in sim.mothers if m.alive]
    n_alive     = len(alive_final)
    final_cw    = sum(m.genome.care_weight for m in alive_final) / n_alive if n_alive else 0.0
    final_gen   = max(m.generation for m in alive_final) if alive_final else 0

    tag = "eroding" if (r is not None and r < -0.02) else (
          "building" if (r is not None and r > 0.02) else "neutral")

    print(f"  seed={seed} | r={r:+.4f} ({tag}) | "
          f"final_cw={final_cw:.3f} | n={n_alive} | max_gen={final_gen} | "
          f"lineage_r={lineage['r_care_vs_descendants']}")

    return {
        "seed":             seed,
        "output_dir":       output_dir,
        "pearson_r":        r,
        "final_cw":         final_cw,
        "n_alive":          n_alive,
        "final_gen":        final_gen,
        "snapshots":        generation_snapshots,
        "lineage":          lineage,
    }


# ── Multi-seed run + plots ────────────────────────────────────────────────────

def run_all():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

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

    for seed in SEEDS:
        if seed in done:
            continue
        print(f"\n[seed={seed}] Running ceiling-drop ...")
        res = run_one(seed)
        results.append(res)
        with open(ckpt, "w") as f:
            json.dump(results, f, indent=2, default=str)

    # ── Statistics ───────────────────────────────────────────────
    rs         = [r["pearson_r"] for r in results if r["pearson_r"] is not None]
    n_pos      = sum(1 for r in rs if r > 0)
    n_neg      = sum(1 for r in rs if r < 0)
    mean_r     = sum(rs) / len(rs)
    sd_r       = (_variance(rs)) ** 0.5
    binom_neg  = _binom_p(len(rs), n_neg)
    binom_pos  = _binom_p(len(rs), n_pos)

    if n_neg >= 9:
        interp = "EROSION CONFIRMED — care declines from ceiling"
    elif n_pos >= 9:
        interp = "BUILDING from ceiling (unexpected — near-neutral or positive)"
    else:
        interp = "NEAR-NEUTRAL from ceiling"

    stats = {
        "experiment":       "ceiling_drop",
        "init_care":        INIT_CARE,
        "init_forage":      INIT_FORAGE,
        "grid":             f"{GRID_SIZE}x{GRID_SIZE}",
        "init_mothers":     INIT_MOTHERS,
        "init_food":        INIT_FOOD,
        "n_seeds":          len(rs),
        "mean_r":           mean_r,
        "sd_r":             sd_r,
        "n_negative_seeds": n_neg,
        "n_positive_seeds": n_pos,
        "binom_p_negative": binom_neg,
        "binom_p_positive": binom_pos,
        "interpretation":   interp,
        "per_seed_r":       {r["seed"]: r["pearson_r"] for r in results},
        "per_seed_final_cw": {r["seed"]: r["final_cw"] for r in results},
    }
    with open(os.path.join(OUT_DIR, "statistical_results.json"), "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  CEILING DROP RECHECK — Phase 4")
    print(f"  Init: care={INIT_CARE}, forage={INIT_FORAGE}, grid={GRID_SIZE}x{GRID_SIZE}, N={INIT_MOTHERS}")
    print(f"  Mean r = {mean_r:+.4f}  (SD={sd_r:.4f})")
    print(f"  Negative seeds: {n_neg}/10  (p={binom_neg:.4f})")
    print(f"  Positive seeds: {n_pos}/10  (p={binom_pos:.4f})")
    per_seed_r  = [f"{r['pearson_r']:+.3f}" for r in results]
    per_seed_cw = [f"{r['final_cw']:.3f}"  for r in results]
    print(f"  Per-seed r: {per_seed_r}")
    print(f"  Final care_weight: {per_seed_cw}")
    print(f"  Interpretation: {interp}")
    print(f"{'='*60}\n")

    # ── Plots ────────────────────────────────────────────────────
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("seaborn-whitegrid")

    # — Plot 1: care_weight trajectory ————————————————————————————
    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(10, 7), sharex=True,
                                          gridspec_kw={"height_ratios": [3, 1]})

    all_ticks, all_cw_means, all_cw_vars = [], [], []
    for res in results:
        snaps = res["snapshots"]
        if snaps:
            t   = [s["tick"] for s in snaps]
            cw  = [s["avg_care_weight"] for s in snaps]
            var = [s["var_care_weight"] for s in snaps]
            ax_top.plot(t, cw, color="#4C72B0", alpha=0.25, linewidth=1)
            all_ticks.append(t)
            all_cw_means.append(cw)
            all_cw_vars.append(var)

    # Average trajectory
    if all_cw_means:
        min_len = min(len(x) for x in all_cw_means)
        ticks_common = all_ticks[0][:min_len]
        mean_traj = [sum(c[i] for c in all_cw_means) / len(all_cw_means)
                     for i in range(min_len)]
        sd_traj   = [(_variance([c[i] for c in all_cw_means])) ** 0.5
                     for i in range(min_len)]
        ax_top.plot(ticks_common, mean_traj, color="#4C72B0", linewidth=2.5,
                    label="Mean care_weight +/- SD  (n=10 seeds)")
        ax_top.fill_between(ticks_common,
                            [m - s for m, s in zip(mean_traj, sd_traj)],
                            [m + s for m, s in zip(mean_traj, sd_traj)],
                            color="#4C72B0", alpha=0.15)

    ax_top.axhline(INIT_CARE, color="grey", linestyle="--", linewidth=1.2,
                   label=f"Init ceiling ({INIT_CARE})")
    ax_top.axhline(0.30, color="#C44E52", linestyle=":", linewidth=1.2,
                   label="Phase 3 floor (care=0.30)")
    ax_top.set_ylabel("Mean care_weight (genome)", fontsize=11)
    ax_top.set_ylim(0, 1.0)
    leg = ax_top.legend(loc="upper right", fontsize=9, framealpha=0.6)
    leg.get_frame().set_alpha(0.6)
    ax_top.set_title(
        f"Phase 4 Recheck -- Ceiling Drop  |  care_weight trajectory\n"
        f"Init care={INIT_CARE}  |  {GRID_SIZE}x{GRID_SIZE} grid  |  N={INIT_MOTHERS}  |  10 seeds",
        fontsize=11, fontweight="bold", linespacing=1.5)
    ax_top.spines["top"].set_visible(False)
    ax_top.spines["right"].set_visible(False)

    # Variance subplot
    if all_cw_vars:
        mean_var = [sum(v[i] for v in all_cw_vars) / len(all_cw_vars)
                    for i in range(min_len)]
        ax_bot.plot(ticks_common, mean_var, color="#C44E52", linewidth=1.8,
                    label="Intra-population variance of care_weight (mean across seeds)")
        ax_bot.set_ylabel("Variance", fontsize=10)
        ax_bot.set_xlabel("Simulation tick", fontsize=11)
        leg2 = ax_bot.legend(loc="upper right", fontsize=8, framealpha=0.6)
        leg2.get_frame().set_alpha(0.6)
        ax_bot.spines["top"].set_visible(False)
        ax_bot.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "ceiling_drop_trajectory.png"), dpi=150, facecolor="white")
    plt.close()

    # — Plot 2: Pearson r distribution ————————————————————————————
    fig, ax = plt.subplots(figsize=(8, 5))
    for i, res in enumerate(results):
        r_val = res["pearson_r"]
        if r_val is None:
            continue
        color = "#2ca02c" if r_val < 0 else "#C44E52"
        ax.scatter(r_val, i, color=color, s=150, zorder=5)
        ax.text(r_val + 0.002, i, f"seed {res['seed']}", va="center", fontsize=8.5)

    ax.axvline(0, color="black", linewidth=1)
    ax.axvline(mean_r, color="#4C72B0", linestyle="--", linewidth=1.5,
               label=f"Mean r = {mean_r:+.4f}")
    ax.axvline(0.0593, color="grey", linestyle=":", linewidth=1.2,
               label="Original Phase 4 mean r = +0.0593")
    ax.set_xlabel("Pearson r  (care_weight vs generation)", fontsize=11)
    ax.set_title(
        f"Phase 4 Recheck -- Pearson r distribution  (Ceiling Drop)\n"
        f"Green = r<0 (erosion, expected)  |  Red = r>0  |  n_neg={n_neg}/10  p={binom_neg:.4f}",
        fontsize=10, fontweight="bold", linespacing=1.5)
    ax.set_yticks([])
    leg = ax.legend(fontsize=9, framealpha=0.6)
    leg.get_frame().set_alpha(0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "ceiling_drop_pearson_r.png"), dpi=150, facecolor="white")
    plt.close()

    # — Plot 3: Lineage scatter (care vs descendants) ─────────────
    fig, ax = plt.subplots(figsize=(7, 5))
    all_cares, all_descs = [], []
    for res in results:
        lin = res["lineage"]
        if lin.get("mean_cares") and lin.get("n_descs"):
            all_cares.extend(lin["mean_cares"])
            all_descs.extend(lin["n_descs"])

    if all_cares:
        ax.scatter(all_cares, all_descs, color="#4C72B0", alpha=0.5, s=40, zorder=3)
        lin_r = _pearson_r(all_cares, all_descs)
        if lin_r is not None:
            # regression line
            m_x = sum(all_cares) / len(all_cares)
            m_y = sum(all_descs) / len(all_descs)
            b = sum((all_cares[i]-m_x)*(all_descs[i]-m_y) for i in range(len(all_cares))) / \
                sum((x-m_x)**2 for x in all_cares)
            a = m_y - b * m_x
            xs = [min(all_cares), max(all_cares)]
            ax.plot(xs, [a + b * x for x in xs], color="#C44E52", linewidth=1.8,
                    label=f"Regression  r = {lin_r:+.4f}")
        ax.axvline(0.30, color="#C44E52", linestyle=":", linewidth=1.2,
                   label="Phase 3 floor (care=0.30)")
        ax.set_xlabel("Mean lineage care_weight", fontsize=11)
        ax.set_ylabel("Lineage descendant count", fontsize=11)
        ax.set_title(
            "Phase 4 Recheck -- Lineage Analysis\n"
            "Mean care_weight per lineage vs total descendants  (pooled across 10 seeds)",
            fontsize=10, fontweight="bold", linespacing=1.5)
        leg = ax.legend(fontsize=9, framealpha=0.6)
        leg.get_frame().set_alpha(0.6)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()

    plt.savefig(os.path.join(OUT_DIR, "ceiling_drop_lineage.png"), dpi=150, facecolor="white")
    plt.close()

    print(f"Plots saved to: {OUT_DIR}")
    print(f"  ceiling_drop_trajectory.png")
    print(f"  ceiling_drop_pearson_r.png")
    print(f"  ceiling_drop_lineage.png")


if __name__ == "__main__":
    run_all()
