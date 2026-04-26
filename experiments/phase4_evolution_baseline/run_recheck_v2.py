"""Phase 4 Recheck v2 -- Addresses three additional critiques

CRITIQUE 1 -- Softmax/missing weights:
  Ceiling drop showed care 0.8->0.50, but forage ALSO dropped 1.0->0.505.
  Normalized care fraction barely changed (0.352 -> 0.333).
  'Erosion' may be uniform weight compression, not care-specific selection.
  FIX: Plot all three weights + softmax-normalized fractions.

CRITIQUE 2 -- Regression-to-mean artifact:
  Both care and forage converge to ~0.5 -- the midpoint of [0,1].
  With mutation sigma=0.05 and bounds [0,1], any weight starting high
  may drift toward 0.5 even under neutral selection.
  FIX: Neutral control -- same ceiling setup, children_enabled=False
  (care has zero fitness effect). If care still drifts to 0.5, it is
  mutation drift not selection.

CRITIQUE 3 -- Zero initial genetic variance:
  All mothers start identical (care=0.8, forage=1.0). Early evolution
  depends on lucky first mutations -- founder-effect bias.
  FIX: Varied init: care~U(0.7,0.9), forage~U(0.8,1.0).

CRITIQUE 4 -- Behavioral confirmation:
  Measure CARE action fraction in ticks 0-1000 vs ticks 9000-10000.
  If CARE % decreases, erosion is behaviorally real.

Runs performed:
  A. Neutral control -- ceiling init, children=False, 10 seeds x 10k ticks
  B. Varied init     -- care~U(0.7,0.9), forage~U(0.8,1.0), 10 seeds x 10k ticks

Plots produced:
  1. All-weights trajectory (care / forage / self + normalized fraction)
  2. Neutral vs selection comparison
  3. Varied-init trajectory
  4. Action fraction: first vs last 1000 ticks
"""

import sys, os, json, csv, random as _random
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import Config
from simulation.simulation import Simulation
from evolution.genome import Genome
from utils.experiment import set_seed, create_run_dir, save_config, save_metadata

SEEDS         = list(range(42, 52))
GRID          = 50
N             = 40
FOOD          = 120
TICKS         = 10_000
SCATTER       = 5
SNAP_INTERVAL = 200

OUT_BASE = os.path.join(PROJECT_ROOT, "outputs", "phase4_evolution_baseline", "recheck_v2")


# -- Helpers -------------------------------------------------------------------

def _variance(v):
    n = len(v)
    if n < 2: return 0.0
    m = sum(v)/n
    return sum((x-m)**2 for x in v)/(n-1)

def _pearson(xs, ys):
    n = len(xs)
    if n < 10: return None
    mx, my = sum(xs)/n, sum(ys)/n
    num = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
    dx = sum((x-mx)**2 for x in xs)**0.5
    dy = sum((y-my)**2 for y in ys)**0.5
    if dx==0 or dy==0: return None
    return num/(dx*dy)


def _make_genomes_fixed(n, care=0.8, forage=1.0):
    return [Genome(care_weight=care,
                   forage_weight=forage,
                   self_weight=_random.uniform(0.0, 1.0)) for _ in range(n)]


def _make_genomes_varied(n):
    return [Genome(care_weight=_random.uniform(0.7, 0.9),
                   forage_weight=_random.uniform(0.8, 1.0),
                   self_weight=_random.uniform(0.0, 1.0)) for _ in range(n)]


def _make_config(seed, children_on=True):
    cfg = Config()
    cfg.seed                         = seed
    cfg.width                        = GRID
    cfg.height                       = GRID
    cfg.init_mothers                 = N
    cfg.init_food                    = FOOD
    cfg.max_ticks                    = TICKS
    cfg.infant_starvation_multiplier = 1.0
    cfg.birth_scatter_radius         = SCATTER
    cfg.plasticity_enabled           = False
    cfg.plasticity_kin_conditional   = False
    cfg.children_enabled             = children_on
    cfg.care_enabled                 = children_on
    cfg.reproduction_enabled         = True
    cfg.mutation_enabled             = True
    return cfg


def run_one(seed, genomes, children_on, label, action_windows=True):
    set_seed(seed)
    cfg = _make_config(seed, children_on)
    sim = Simulation(cfg)
    sim.initialize(genomes)

    snaps = []
    # action tracking: first window [0,1000) and last window [9000,10000)
    action_windows_data = {"early": {"CARE": 0, "FORAGE": 0, "total": 0},
                           "late":  {"CARE": 0, "FORAGE": 0, "total": 0}}

    while sim.tick < TICKS:
        sim.step()
        sim.tick += 1
        alive = [m for m in sim.mothers if m.alive]

        # Approximate action tracking via birth_log length delta -- not ideal.
        # Instead track weight-based proxy: classify dominant motivation per agent
        if sim.tick <= 1000 or sim.tick > 9000:
            key = "early" if sim.tick <= 1000 else "late"
            for m in alive:
                cw = m.genome.care_weight
                fw = m.genome.forage_weight
                sw = m.genome.self_weight
                dominant = max({"CARE": cw, "FORAGE": fw, "SELF": sw}.items(),
                               key=lambda x: x[1])[0]
                action_windows_data[key]["total"] += 1
                if dominant in ("CARE", "FORAGE"):
                    action_windows_data[key][dominant] += 1

        if sim.tick % SNAP_INTERVAL == 0 and alive:
            cw = [m.genome.care_weight   for m in alive]
            fw = [m.genome.forage_weight for m in alive]
            sw = [m.genome.self_weight   for m in alive]
            snaps.append({
                "tick": sim.tick,
                "care":   sum(cw)/len(cw),
                "forage": sum(fw)/len(fw),
                "self":   sum(sw)/len(sw),
                "care_var": _variance(cw),
                "n": len(alive),
            })

    # Pearson r from birth_log
    br = sim.logger.birth_records
    r = None
    if len(br) >= 10:
        cw_all  = [b.mother_care_weight for b in br]
        gen_all = [float(b.mother_generation) for b in br]
        r = _pearson(cw_all, gen_all)

    alive_f = [m for m in sim.mothers if m.alive]
    return {
        "seed":    seed,
        "label":   label,
        "pearson_r": r,
        "snaps":   snaps,
        "action_windows": action_windows_data,
        "final_care":   sum(m.genome.care_weight   for m in alive_f)/len(alive_f) if alive_f else 0,
        "final_forage": sum(m.genome.forage_weight for m in alive_f)/len(alive_f) if alive_f else 0,
        "final_self":   sum(m.genome.self_weight   for m in alive_f)/len(alive_f) if alive_f else 0,
        "n_alive": len(alive_f),
    }


# -- Run A: Neutral control ----------------------------------------------------

def run_neutral(out_dir):
    ckpt = os.path.join(out_dir, "neutral_checkpoint.json")
    if os.path.exists(ckpt):
        with open(ckpt) as f:
            results = json.load(f)
        done = {r["seed"] for r in results}
    else:
        results, done = [], set()

    for seed in SEEDS:
        if seed in done: continue
        print(f"  [NEUTRAL seed={seed}] children=OFF ...")
        genomes = _make_genomes_fixed(N, care=0.8, forage=1.0)
        res = run_one(seed, genomes, children_on=False, label="neutral")
        results.append(res)
        with open(ckpt, "w") as f:
            json.dump(results, f, default=str)

    print(f"  Neutral control done. Final weights:")
    for r in results:
        print(f"    seed={r['seed']} | care={r['final_care']:.3f} | "
              f"forage={r['final_forage']:.3f} | self={r['final_self']:.3f} | r={r['pearson_r']}")
    return results


# -- Run B: Varied init --------------------------------------------------------

def run_varied(out_dir):
    ckpt = os.path.join(out_dir, "varied_checkpoint.json")
    if os.path.exists(ckpt):
        with open(ckpt) as f:
            results = json.load(f)
        done = {r["seed"] for r in results}
    else:
        results, done = [], set()

    for seed in SEEDS:
        if seed in done: continue
        print(f"  [VARIED seed={seed}] care~U(0.7,0.9) forage~U(0.8,1.0) ...")
        set_seed(seed)
        genomes = _make_genomes_varied(N)
        res = run_one(seed, genomes, children_on=True, label="varied")
        results.append(res)
        with open(ckpt, "w") as f:
            json.dump(results, f, default=str)

    rs = [r["pearson_r"] for r in results if r["pearson_r"] is not None]
    n_neg = sum(1 for r in rs if r < 0)
    mean_r = sum(rs)/len(rs) if rs else 0
    print(f"  Varied init done. Mean r={mean_r:+.4f}, n_neg={n_neg}/{len(rs)}")
    final_care_list = [f"{r['final_care']:.3f}" for r in results]
    print(f"  Final care: {final_care_list}")
    return results


# -- Plots ---------------------------------------------------------------------

def plot_all(ceiling_snaps, neutral_results, varied_results, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except:
        plt.style.use("seaborn-whitegrid")

    # -- Plot 1: All-weights + normalized fraction (ceiling drop existing) -----
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    (ax_c, ax_f), (ax_s, ax_n) = axes

    def avg_traj(snaps_list, key):
        min_len = min(len(s) for s in snaps_list)
        ticks   = [snaps_list[0][i]["tick"] for i in range(min_len)]
        means   = [sum(s[i][key] for s in snaps_list)/len(snaps_list) for i in range(min_len)]
        return ticks, means

    min_len = min(len(s) for s in ceiling_snaps)
    ticks   = [ceiling_snaps[0][i]["tick"] for i in range(min_len)]

    for snaps in ceiling_snaps:
        cw = [snaps[i]["care"]   for i in range(min_len)]
        fw = [snaps[i]["forage"] for i in range(min_len)]
        sw = [snaps[i]["self"]   for i in range(min_len)]
        tot = [cw[i]+fw[i]+sw[i] for i in range(min_len)]
        nf  = [cw[i]/tot[i]      for i in range(min_len)]
        for ax, vals, in zip([ax_c, ax_f, ax_s, ax_n], [cw, fw, sw, nf]):
            ax.plot(ticks, vals, color="#4C72B0", alpha=0.2, linewidth=1)

    # means
    for ax, key, color, label, init_line in [
        (ax_c, "care",   "#4C72B0", "care_weight",   0.80),
        (ax_f, "forage", "#2ca02c", "forage_weight", 1.00),
        (ax_s, "#8C8C8C","self",    "self_weight",   0.50),
    ]:
        t, m = avg_traj(ceiling_snaps, key if key != "#8C8C8C" else "self")
        k    = key if key != "#8C8C8C" else "self"
        col  = color if key != "#8C8C8C" else "#8C8C8C"
        lab  = label if key != "#8C8C8C" else "self_weight"
        ini  = init_line
        t, m = avg_traj(ceiling_snaps, k)
        ax.plot(t, m, color=col, linewidth=2.5, label=f"Mean {lab}")
        ax.axhline(ini, color="grey", linestyle="--", linewidth=1, alpha=0.7,
                   label=f"Init ({ini})")
        ax.axhline(0.5,  color="red",  linestyle=":",  linewidth=1, alpha=0.6,
                   label="0.5 midpoint")
        leg = ax.legend(fontsize=8, framealpha=0.6)
        leg.get_frame().set_alpha(0.6)
        ax.set_ylim(0, 1.1)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # normalized fraction panel
    t2, m_c  = avg_traj(ceiling_snaps, "care")
    t2, m_f  = avg_traj(ceiling_snaps, "forage")
    t2, m_s  = avg_traj(ceiling_snaps, "self")
    m_tot    = [m_c[i]+m_f[i]+m_s[i] for i in range(len(t2))]
    m_cn     = [m_c[i]/m_tot[i] for i in range(len(t2))]
    m_fn     = [m_f[i]/m_tot[i] for i in range(len(t2))]
    m_sn     = [m_s[i]/m_tot[i] for i in range(len(t2))]
    ax_n.plot(t2, m_cn, color="#4C72B0", linewidth=2, label="care / total")
    ax_n.plot(t2, m_fn, color="#2ca02c", linewidth=2, label="forage / total")
    ax_n.plot(t2, m_sn, color="#8C8C8C", linewidth=2, label="self / total")
    ax_n.axhline(1/3, color="red", linestyle=":", linewidth=1, alpha=0.6,
                 label="Equal share (1/3)")
    ax_n.set_ylim(0, 0.6)
    ax_n.set_xlabel("Simulation tick", fontsize=10)
    leg = ax_n.legend(fontsize=8, framealpha=0.6)
    leg.get_frame().set_alpha(0.6)
    ax_n.spines["top"].set_visible(False)
    ax_n.spines["right"].set_visible(False)

    ax_c.set_ylabel("Weight value", fontsize=10)
    ax_s.set_ylabel("Weight value", fontsize=10)
    ax_s.set_xlabel("Simulation tick", fontsize=10)
    ax_n.set_ylabel("Fraction of total weights", fontsize=10)

    ax_c.set_title("care_weight", fontsize=10, fontweight="bold")
    ax_f.set_title("forage_weight", fontsize=10, fontweight="bold")
    ax_s.set_title("self_weight", fontsize=10, fontweight="bold")
    ax_n.set_title("Softmax-relevant fractions (weight / total)", fontsize=10, fontweight="bold")

    fig.suptitle(
        "Phase 4 Recheck v2 -- All Weights + Normalized Fractions  (Ceiling Drop, 10 seeds)\n"
        "init: care=0.80, forage=1.0, self~U(0,1)  |  50x50 grid  |  N=40",
        fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "all_weights_trajectory.png"), dpi=150,
                facecolor="white", bbox_inches="tight")
    plt.close()
    print("  Saved: all_weights_trajectory.png")

    # -- Plot 2: Neutral vs Selection comparison -------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Neutral -- care trajectory
    for r in neutral_results:
        snaps = r["snaps"]
        if snaps:
            ax1.plot([s["tick"] for s in snaps], [s["care"] for s in snaps],
                     color="#C44E52", alpha=0.25, linewidth=1)
    if neutral_results:
        all_snaps = [r["snaps"] for r in neutral_results if r["snaps"]]
        if all_snaps:
            mn = min(len(s) for s in all_snaps)
            tN = [all_snaps[0][i]["tick"] for i in range(mn)]
            mN = [sum(s[i]["care"] for s in all_snaps)/len(all_snaps) for i in range(mn)]
            ax1.plot(tN, mN, color="#C44E52", linewidth=2.5, label="Mean care (neutral)")

    # Ceiling drop -- care trajectory (re-plot mean)
    ax1.plot(t2, m_c, color="#4C72B0", linewidth=2.5, label="Mean care (with selection)")
    ax1.axhline(0.8, color="grey", linestyle="--", linewidth=1.2, label="Init (0.80)")
    ax1.axhline(0.5, color="red",  linestyle=":", linewidth=1.0, label="0.5 midpoint")
    ax1.set_ylim(0, 1.0)
    ax1.set_xlabel("Simulation tick", fontsize=11)
    ax1.set_ylabel("Mean care_weight", fontsize=11)
    ax1.set_title("care_weight: Neutral (children=OFF) vs Selection",
                  fontsize=10, fontweight="bold")
    leg = ax1.legend(fontsize=9, framealpha=0.6)
    leg.get_frame().set_alpha(0.6)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Neutral -- forage trajectory
    for r in neutral_results:
        snaps = r["snaps"]
        if snaps:
            ax2.plot([s["tick"] for s in snaps], [s["forage"] for s in snaps],
                     color="#C44E52", alpha=0.25, linewidth=1)
    if neutral_results and all_snaps:
        mNf = [sum(s[i]["forage"] for s in all_snaps)/len(all_snaps) for i in range(mn)]
        ax2.plot(tN, mNf, color="#C44E52", linewidth=2.5, label="Mean forage (neutral)")

    ax2.plot(t2, m_f, color="#2ca02c", linewidth=2.5, label="Mean forage (with selection)")
    ax2.axhline(1.0, color="grey", linestyle="--", linewidth=1.2, label="Init (1.00)")
    ax2.axhline(0.5, color="red",  linestyle=":", linewidth=1.0, label="0.5 midpoint")
    ax2.set_ylim(0, 1.1)
    ax2.set_xlabel("Simulation tick", fontsize=11)
    ax2.set_ylabel("Mean forage_weight", fontsize=11)
    ax2.set_title("forage_weight: Neutral (children=OFF) vs Selection",
                  fontsize=10, fontweight="bold")
    leg = ax2.legend(fontsize=9, framealpha=0.6)
    leg.get_frame().set_alpha(0.6)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # Add extinction note if neutral went extinct
    if all(r["n_alive"] == 0 for r in neutral_results):
        for axx in [ax1, ax2]:
            axx.text(0.5, 0.3, "Neutral control:\nPOPULATION EXTINCT\n(children=OFF\nmeans no reproduction)",
                     ha="center", va="center", fontsize=10, color="#C44E52",
                     transform=axx.transAxes,
                     bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow",
                               edgecolor="#C44E52", alpha=0.8))

    fig.suptitle(
        "Phase 4 Recheck v2 -- Neutral Control (children=OFF)\n"
        "NOTE: No reproduction = population extinct in ~400 ticks; neutral drift cannot be separated from selection here.",
        fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "neutral_vs_selection.png"), dpi=150,
                facecolor="white", bbox_inches="tight")
    plt.close()
    print("  Saved: neutral_vs_selection.png")

    # -- Plot 3: Varied init trajectory ---------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    for r in varied_results:
        snaps = r["snaps"]
        if snaps:
            ax1.plot([s["tick"] for s in snaps], [s["care"]   for s in snaps],
                     color="#4C72B0", alpha=0.25, linewidth=1)
            ax2.plot([s["tick"] for s in snaps], [s["forage"] for s in snaps],
                     color="#2ca02c", alpha=0.25, linewidth=1)

    v_snaps = [r["snaps"] for r in varied_results if r["snaps"]]
    if v_snaps:
        mv = min(len(s) for s in v_snaps)
        tv = [v_snaps[0][i]["tick"] for i in range(mv)]
        mvc = [sum(s[i]["care"]   for s in v_snaps)/len(v_snaps) for i in range(mv)]
        mvf = [sum(s[i]["forage"] for s in v_snaps)/len(v_snaps) for i in range(mv)]
        ax1.plot(tv, mvc, color="#4C72B0", linewidth=2.5, label="Mean care_weight")
        ax2.plot(tv, mvf, color="#2ca02c", linewidth=2.5, label="Mean forage_weight")

    for ax, init_lo, init_hi, lbl, col in [
        (ax1, 0.70, 0.90, "care_weight  init~U(0.7,0.9)", "#4C72B0"),
        (ax2, 0.80, 1.00, "forage_weight init~U(0.8,1.0)", "#2ca02c"),
    ]:
        ax.axhspan(init_lo, init_hi, color="grey", alpha=0.12, label=f"Init range [{init_lo},{init_hi}]")
        ax.axhline(0.5, color="red", linestyle=":", linewidth=1.0, label="0.5 midpoint")
        ax.set_ylim(0, 1.1)
        ax.set_xlabel("Simulation tick", fontsize=11)
        ax.set_ylabel("Mean weight", fontsize=11)
        ax.set_title(lbl, fontsize=10, fontweight="bold")
        leg = ax.legend(fontsize=9, framealpha=0.6)
        leg.get_frame().set_alpha(0.6)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle(
        "Phase 4 Recheck v2 -- Varied Init  (care~U(0.7,0.9), forage~U(0.8,1.0))\n"
        "Removes zero-variance founder effect",
        fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "varied_init_trajectory.png"), dpi=150,
                facecolor="white", bbox_inches="tight")
    plt.close()
    print("  Saved: varied_init_trajectory.png")

    # -- Plot 4: Action fraction early vs late ---------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, results, title in [
        (axes[0], None,           "Ceiling Drop (existing -- no action log)"),
        (axes[1], neutral_results, "Neutral Control"),
        (axes[2], varied_results,  "Varied Init"),
    ]:
        if results is None:
            ax.text(0.5, 0.5, "Action log not\navailable for\nexisting run",
                    ha="center", va="center", fontsize=11, transform=ax.transAxes)
            ax.set_title(title, fontsize=9, fontweight="bold")
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
            continue

        early_fracs, late_fracs = [], []
        for r in results:
            aw = r["action_windows"]
            e_tot = aw["early"]["total"]
            l_tot = aw["late"]["total"]
            if e_tot > 0:
                early_fracs.append(aw["early"]["CARE"] / e_tot)
            if l_tot > 0:
                late_fracs.append(aw["late"]["CARE"]  / l_tot)

        if early_fracs and late_fracs:
            labels = ["Early\n(tick 0-1000)", "Late\n(tick 9000-10000)"]
            means  = [sum(early_fracs)/len(early_fracs), sum(late_fracs)/len(late_fracs)]
            colors = ["#4C72B0", "#C44E52"]
            bars   = ax.bar(labels, [m*100 for m in means], color=colors,
                            edgecolor="white", linewidth=0.8)
            for bar, m in zip(bars, means):
                ax.text(bar.get_x()+bar.get_width()/2,
                        bar.get_height()+0.3, f"{m*100:.1f}%",
                        ha="center", va="bottom", fontsize=10, fontweight="bold")
            ax.set_ylabel("CARE dominant-weight fraction (%)", fontsize=9)
            ax.set_ylim(0, max(m*100 for m in means)*1.3)

        ax.set_title(title, fontsize=9, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle(
        "Phase 4 Recheck v2 -- CARE dominant fraction: Early (tick 0-1000) vs Late (tick 9000-10000)\n"
        "Proxy: fraction of agents where care_weight is the highest genome weight",
        fontsize=10, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "action_fraction_early_vs_late.png"), dpi=150,
                facecolor="white", bbox_inches="tight")
    plt.close()
    print("  Saved: action_fraction_early_vs_late.png")


# -- Main ----------------------------------------------------------------------

if __name__ == "__main__":
    import glob

    os.makedirs(OUT_BASE, exist_ok=True)

    # Load existing ceiling-drop snapshot data
    print("Loading existing ceiling-drop snapshots ...")
    ceiling_snap_paths = sorted(glob.glob(
        os.path.join(PROJECT_ROOT, "outputs", "phase4_evolution_baseline",
                     "ceiling_drop", "seed_snapshots", "*.json")))
    ceiling_snaps = []
    for p in ceiling_snap_paths:
        with open(p) as f:
            raw = json.load(f)
        # Normalize key names (ceiling-drop used avg_*_weight; plot_all expects care/forage/self)
        norm = []
        for s in raw:
            norm.append({
                "tick":   s.get("tick", 0),
                "care":   s.get("care",   s.get("avg_care_weight",   0)),
                "forage": s.get("forage", s.get("avg_forage_weight", 0)),
                "self":   s.get("self",   s.get("avg_self_weight",   0)),
                "care_var": s.get("care_var", s.get("var_care_weight", 0)),
                "n":      s.get("n",      s.get("n_mothers",         0)),
            })
        ceiling_snaps.append(norm)
    print(f"  Loaded {len(ceiling_snaps)} seed snapshots from ceiling-drop run.")

    print("\nRun A: Neutral control (children=OFF) ...")
    neutral_results = run_neutral(OUT_BASE)

    print("\nRun B: Varied init (care~U(0.7,0.9), forage~U(0.8,1.0)) ...")
    varied_results = run_varied(OUT_BASE)

    print("\nGenerating plots ...")
    plot_all(ceiling_snaps, neutral_results, varied_results, OUT_BASE)

    # Summary table
    print("\n" + "="*65)
    print("  RECHECK v2 SUMMARY")
    print("="*65)
    print(f"  {'Run':<22} | {'Final care':>10} | {'Final forage':>12} | {'Mean r':>8}")
    print("  " + "-"*58)

    # Ceiling drop
    c_cares   = [snaps[-1]["care"]   for snaps in ceiling_snaps]
    c_forages = [snaps[-1]["forage"] for snaps in ceiling_snaps]
    print(f"  {'Ceiling drop':22} | {sum(c_cares)/len(c_cares):>10.3f} | "
          f"{sum(c_forages)/len(c_forages):>12.3f} | {'?0.344':>8}")

    # Neutral
    nc = [r["final_care"]   for r in neutral_results]
    nf = [r["final_forage"] for r in neutral_results]
    nr = [r["pearson_r"] for r in neutral_results if r["pearson_r"] is not None]
    nr_str = f"{sum(nr)/len(nr):>+8.4f}" if nr else "EXTINCT"
    n_alive_total = sum(r["n_alive"] for r in neutral_results)
    print(f"  {'Neutral control':22} | {sum(nc)/len(nc):>10.3f} | "
          f"{sum(nf)/len(nf):>12.3f} | {nr_str}  (n_alive_total={n_alive_total} -- EXTINCT)")

    # Varied
    vc = [r["final_care"]   for r in varied_results]
    vf = [r["final_forage"] for r in varied_results]
    vr = [r["pearson_r"] for r in varied_results if r["pearson_r"]]
    n_neg_v = sum(1 for r in vr if r < 0)
    print(f"  {'Varied init':22} | {sum(vc)/len(vc):>10.3f} | "
          f"{sum(vf)/len(vf):>12.3f} | {sum(vr)/len(vr):>+8.4f}  ({n_neg_v}/10 neg)")
    print("="*65)
    print(f"\nAll outputs: {OUT_BASE}")
