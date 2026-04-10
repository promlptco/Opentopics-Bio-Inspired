# utils/plotting.py
"""Minimal diagnostic plots for each phase."""
import os
import json
import csv
from typing import Optional

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
    print("Warning: matplotlib not installed, plotting disabled")


def ensure_plot_dir(output_dir: str) -> str:
    """Create plots subdirectory."""
    plot_dir = os.path.join(output_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    return plot_dir


def load_csv(filepath: str) -> list[dict]:
    """Load CSV as list of dicts."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_json(filepath: str) -> dict:
    """Load JSON file."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r") as f:
        return json.load(f)


# =============================================================================
# CORE PLOTS (Always available)
# =============================================================================

def plot_population(population_history: list[int], output_dir: str) -> None:
    """Plot population over time."""
    if plt is None or not population_history:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    plt.figure(figsize=(8, 4))
    plt.plot(population_history)
    plt.xlabel("Tick")
    plt.ylabel("Population")
    plt.title("Population vs Time")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "population.png"))
    plt.close()


def plot_energy(energy_history: list[float], output_dir: str) -> None:
    """Plot average energy over time."""
    if plt is None or not energy_history:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    plt.figure(figsize=(8, 4))
    plt.plot(energy_history)
    plt.xlabel("Tick")
    plt.ylabel("Avg Energy")
    plt.title("Average Energy vs Time")
    plt.ylim(0, 1)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "energy.png"))
    plt.close()


def plot_population_and_energy(
    population_history: list[int],
    energy_history: list[float],
    output_dir: str
) -> None:
    """Combined population and energy plot."""
    if plt is None:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    
    ax1.plot(population_history, color="blue")
    ax1.set_ylabel("Population")
    ax1.set_title("Population & Energy vs Time")
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(energy_history, color="orange")
    ax2.set_xlabel("Tick")
    ax2.set_ylabel("Avg Energy")
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "population_energy.png"))
    plt.close()


# =============================================================================
# CARE PLOTS (When care enabled)
# =============================================================================

def plot_care_frequency(care_records: list[dict], max_tick: int, output_dir: str, bin_size: int = 20) -> None:
    """Plot care events over time (binned)."""
    if plt is None or not care_records:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    # Bin care events
    ticks = [int(r["tick"]) for r in care_records]
    bins = list(range(0, max_tick + bin_size, bin_size))
    
    plt.figure(figsize=(8, 4))
    plt.hist(ticks, bins=bins, edgecolor="black", alpha=0.7)
    plt.xlabel("Tick")
    plt.ylabel("Care Events")
    plt.title("Care Frequency Over Time")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "care_frequency.png"))
    plt.close()


def plot_care_distance_histogram(choice_records: list[dict], output_dir: str) -> None:
    """Histogram of distance at care selection."""
    if plt is None or not choice_records:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    # Filter care choices with valid distance
    distances = []
    for r in choice_records:
        if r.get("winner_domain") == "care" and r.get("chosen_distance"):
            try:
                distances.append(float(r["chosen_distance"]))
            except (ValueError, TypeError):
                pass
    
    if not distances:
        return
    
    plt.figure(figsize=(8, 4))
    plt.hist(distances, bins=20, edgecolor="black", alpha=0.7)
    plt.xlabel("Distance")
    plt.ylabel("Count")
    plt.title("Care Distance Distribution")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "care_distance_hist.png"))
    plt.close()


def plot_care_success_rate(care_records: list[dict], output_dir: str, bin_size: int = 20) -> None:
    """Plot care success rate over time."""
    if plt is None or not care_records:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    # Group by tick bins
    max_tick = max(int(r["tick"]) for r in care_records)
    bins = {}
    
    for r in care_records:
        tick = int(r["tick"])
        bin_idx = tick // bin_size
        if bin_idx not in bins:
            bins[bin_idx] = {"success": 0, "total": 0}
        bins[bin_idx]["total"] += 1
        if r.get("success") == "True" or r.get("success") is True:
            bins[bin_idx]["success"] += 1
    
    x = sorted(bins.keys())
    y = [bins[b]["success"] / bins[b]["total"] if bins[b]["total"] > 0 else 0 for b in x]
    x = [b * bin_size for b in x]
    
    plt.figure(figsize=(8, 4))
    plt.plot(x, y, marker="o", markersize=3)
    plt.xlabel("Tick")
    plt.ylabel("Success Rate")
    plt.title("Care Success Rate Over Time")
    plt.ylim(0, 1)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "care_success_rate.png"))
    plt.close()


# =============================================================================
# RELATEDNESS PLOTS (Hamilton analysis)
# =============================================================================

def plot_care_by_relatedness(care_records: list[dict], output_dir: str) -> None:
    """Plot care frequency by relatedness."""
    if plt is None or not care_records:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    # Group by r
    r_groups = {}
    for r in care_records:
        try:
            rel = float(r["r"])
        except (ValueError, TypeError, KeyError):
            continue
        
        # Bin r values
        r_bin = round(rel, 1)
        if r_bin not in r_groups:
            r_groups[r_bin] = 0
        r_groups[r_bin] += 1
    
    if not r_groups:
        return
    
    x = sorted(r_groups.keys())
    y = [r_groups[r] for r in x]
    
    plt.figure(figsize=(8, 4))
    plt.bar(x, y, width=0.08, edgecolor="black", alpha=0.7)
    plt.xlabel("Relatedness (r)")
    plt.ylabel("Care Count")
    plt.title("Care Events by Relatedness")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "care_by_relatedness.png"))
    plt.close()


def plot_chosen_by_distance(choice_records: list[dict], output_dir: str) -> None:
    """Plot selection probability by distance."""
    if plt is None or not choice_records:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    # Group by distance
    dist_groups = {}
    for r in choice_records:
        if r.get("winner_domain") != "care":
            continue
        try:
            dist = int(float(r["chosen_distance"]))
        except (ValueError, TypeError, KeyError):
            continue
        
        if dist not in dist_groups:
            dist_groups[dist] = 0
        dist_groups[dist] += 1
    
    if not dist_groups:
        return
    
    x = sorted(dist_groups.keys())
    y = [dist_groups[d] for d in x]
    
    plt.figure(figsize=(8, 4))
    plt.bar(x, y, edgecolor="black", alpha=0.7)
    plt.xlabel("Distance")
    plt.ylabel("Times Chosen")
    plt.title("Care Selection by Distance")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "chosen_by_distance.png"))
    plt.close()


# =============================================================================
# HAMILTON ANALYSIS (Split: own-lineage vs foreign-lineage)
# =============================================================================

def analyze_hamilton_split(output_dir: str) -> dict:
    """
    Hamilton's rule split analysis on care_log.csv.

    Own-lineage (is_own_child=True, r > 0):
      Per-event rB vs C; fraction where rB > C.
      Produces: scatter rB vs C, histogram of (rB - C).

    Foreign-lineage (is_own_child=False):
      Frequency count only — NOT Hamilton-analyzed (r ≈ 0,
      by-product of proximity; see SESSION_CONTEXT for rationale).

    Returns summary dict (also printed to stdout).
    """
    care_records = load_csv(os.path.join(output_dir, "care_log.csv"))
    if not care_records:
        return {}

    own, foreign = [], []
    for rec in care_records:
        try:
            r_val = float(rec["r"])
            B = float(rec["benefit"])
            C = float(rec["cost"])
            is_own = rec.get("is_own_child", "False").strip() == "True"
        except (ValueError, TypeError, KeyError):
            continue
        entry = {"r": r_val, "B": B, "C": C, "rB": r_val * B}
        if is_own:
            own.append(entry)
        else:
            foreign.append(entry)

    summary: dict = {
        "n_own": len(own),
        "n_foreign": len(foreign),
        "n_total": len(own) + len(foreign),
    }

    if own:
        rB_vals = [e["rB"] for e in own]
        C_vals = [e["C"] for e in own]
        rB_minus_C = [e["rB"] - e["C"] for e in own]
        n_altruistic = sum(1 for x in rB_minus_C if x > 0)

        summary.update({
            "mean_rB": sum(rB_vals) / len(rB_vals),
            "mean_C": sum(C_vals) / len(C_vals),
            "mean_rB_minus_C": sum(rB_minus_C) / len(rB_minus_C),
            "frac_rB_gt_C": n_altruistic / len(own),
        })

        if plt is not None:
            plot_dir = ensure_plot_dir(output_dir)

            # 1. Scatter: rB vs C (own-lineage)
            plt.figure(figsize=(6, 5))
            plt.scatter(C_vals, rB_vals, alpha=0.3, s=10, color="steelblue")
            lim = max(max(C_vals), max(rB_vals)) * 1.05
            plt.plot([0, lim], [0, lim], "r--", linewidth=1, label="rB = C (break-even)")
            plt.xlabel("Cost C")
            plt.ylabel("rB (relatedness × benefit)")
            plt.title("Hamilton rB vs C — Own-lineage Care")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(plot_dir, "hamilton_rB_vs_C.png"))
            plt.close()

            # 2. Histogram: rB - C distribution
            plt.figure(figsize=(7, 4))
            plt.hist(rB_minus_C, bins=30, edgecolor="black", alpha=0.7, color="steelblue")
            plt.axvline(0, color="red", linestyle="--", linewidth=1.5, label="Break-even (rB-C=0)")
            plt.xlabel("rB − C")
            plt.ylabel("Count")
            plt.title("Hamilton (rB − C) Distribution — Own-lineage Care")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(plot_dir, "hamilton_rB_minus_C.png"))
            plt.close()

    # 3. Bar: own-lineage vs foreign-lineage counts
    if plt is not None and (own or foreign):
        plot_dir = ensure_plot_dir(output_dir)
        labels = ["Own-lineage\n(r > 0)", "Foreign-lineage\n(r ≈ 0)"]
        counts = [len(own), len(foreign)]
        colors = ["steelblue", "lightcoral"]
        pct_own = 100.0 * len(own) / max(len(own) + len(foreign), 1)

        plt.figure(figsize=(5, 4))
        bars = plt.bar(labels, counts, color=colors, edgecolor="black", alpha=0.8)
        for bar, count in zip(bars, counts):
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                     str(count), ha="center", va="bottom", fontsize=9)
        plt.ylabel("Care Events")
        plt.title(f"Own vs Foreign Lineage Care\n({pct_own:.1f}% own-lineage)")
        plt.grid(True, alpha=0.3, axis="y")
        plt.tight_layout()
        plt.savefig(os.path.join(plot_dir, "hamilton_own_vs_foreign.png"))
        plt.close()

    # Print summary
    print("\n=== Hamilton Split Analysis ===")
    print(f"  Own-lineage events  : {summary.get('n_own', 0)}")
    print(f"  Foreign-lineage     : {summary.get('n_foreign', 0)}")
    if "mean_rB" in summary:
        pct_own = 100.0 * summary["n_own"] / max(summary["n_total"], 1)
        print(f"  Own-lineage rate    : {pct_own:.1f}%  "
              f"(proximity by-product — no kin recognition in agents)")
        print(f"  Mean rB (own)       : {summary['mean_rB']:.4f}  "
              f"(r=0.5 correct; rB weak because B=hunger_reduced is bounded by child's hunger at event time)")
        print(f"  Mean C  (own)       : {summary['mean_C']:.4f}")
        print(f"  Mean rB-C (own)     : {summary['mean_rB_minus_C']:.4f}")
        print(f"  Fraction rB > C     : {summary['frac_rB_gt_C']:.3f}")
    print("  NOTE: Agents have no kin recognition. Hamilton rB>C is post-hoc fitness")
    print("        accounting only, not a causal mechanism for care in this model.")
    print("================================\n")

    return summary


def plot_lineage_fitness(output_dir: str) -> None:
    """
    Bar chart of surviving descendants per founding lineage.
    B_social = total living descendants at simulation end.
    Reads surviving_lineages.json saved by run.py.
    """
    if plt is None:
        return

    data = load_json(os.path.join(output_dir, "surviving_lineages.json"))
    if not data:
        return

    plot_dir = ensure_plot_dir(output_dir)

    lineage_ids = sorted(data.keys(), key=lambda x: int(x))
    totals = [data[lid]["total"] for lid in lineage_ids]
    mothers = [data[lid]["mothers"] for lid in lineage_ids]
    children = [data[lid]["children"] for lid in lineage_ids]
    x = list(range(len(lineage_ids)))

    plt.figure(figsize=(max(6, len(x) // 2), 5))
    plt.bar(x, totals, label="Total (B_social)", color="steelblue", edgecolor="black", alpha=0.8)
    plt.bar(x, mothers, label="Mothers", color="orange", edgecolor="black", alpha=0.8)
    plt.bar(x, children, bottom=mothers, label="Children", color="lightgreen",
            edgecolor="black", alpha=0.8)
    plt.xticks(x, [f"L{lid}" for lid in lineage_ids], rotation=45, ha="right", fontsize=7)
    plt.xlabel("Founding Lineage")
    plt.ylabel("Living Descendants")
    plt.title("Lineage Fitness (B_social) — Surviving Descendants per Lineage")
    plt.legend()
    plt.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "lineage_fitness.png"))
    plt.close()


# =============================================================================
# EVOLUTION PLOTS (When evolution enabled)
# =============================================================================

def plot_reproductive_success_by_genotype(output_dir: str) -> dict:
    """
    Two-panel genotype fitness analysis using birth_log.csv + death_log.csv.

    Panel 1 — care_weight vs generation (at birth time).
      If evolution selects against care, later-generation mothers should
      have lower care_weight. Negative slope = directional selection.

    Panel 2 — care_weight vs survival time after first reproduction.
      Joins birth_log (first birth tick) with death_log (death tick).
      If care is costly, high-care mothers should die sooner.

    NOTE: Offspring count ≈ 1 per mother in this model (reproduction
    throttled by cooldown + energy cost), so fecundity is not the
    differentiating fitness axis — generation depth and survival are.
    """
    if plt is None:
        return {}

    birth_records = load_csv(os.path.join(output_dir, "birth_log.csv"))
    death_records = load_csv(os.path.join(output_dir, "death_log.csv"))

    if not birth_records:
        print("  [reproductive success] birth_log.csv missing — skipping")
        return {}

    # ── Panel 1: care_weight vs generation ──
    cw_gen   = [float(r["mother_care_weight"]) for r in birth_records]
    gen_vals = [int(r["mother_generation"])     for r in birth_records]

    def pearson(xs, ys):
        n = len(xs)
        if n < 3:
            return 0.0, 0.0, 0.0
        mx, my = sum(xs) / n, sum(ys) / n
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
        sx  = (sum((x - mx) ** 2 for x in xs) / n) ** 0.5
        sy  = (sum((y - my) ** 2 for y in ys) / n) ** 0.5
        r   = cov / (sx * sy) if sx > 0 and sy > 0 else 0.0
        slope = cov / (sx ** 2) if sx > 0 else 0.0
        return r, slope, my - slope * mx

    r1, slope1, intercept1 = pearson(gen_vals, cw_gen)

    # ── Panel 2: care_weight vs survival after first birth ──
    # death_tick per mother
    death_tick: dict[int, int] = {}
    for d in death_records:
        if d.get("agent_type") == "mother":
            death_tick[int(d["agent_id"])] = int(d["tick"])

    # first birth tick per mother
    from collections import defaultdict
    first_birth: dict[int, dict] = {}
    for row in birth_records:
        mid = int(row["mother_id"])
        if mid not in first_birth or int(row["tick"]) < int(first_birth[mid]["tick"]):
            first_birth[mid] = row

    cw_surv, survival_ticks = [], []
    for mid, row in first_birth.items():
        if mid in death_tick:
            surv = death_tick[mid] - int(row["tick"])
            if surv >= 0:
                cw_surv.append(float(row["mother_care_weight"]))
                survival_ticks.append(surv)

    r2, slope2, intercept2 = pearson(cw_surv, survival_ticks)

    # ── Plot ──
    plot_dir = ensure_plot_dir(output_dir)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    def add_regression(ax, xs, ys, r, slope, intercept, xlabel, ylabel, title, color="steelblue"):
        ax.scatter(xs, ys, alpha=0.25, s=12, color=color)
        if xs:
            xl = [min(xs), max(xs)]
            ax.plot(xl, [slope * x + intercept for x in xl],
                    color="crimson", linewidth=1.8, label=f"regression (r={r:+.3f})")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=9)
        interp = ("↓ selection against care" if r < -0.1
                  else "↑ selection for care" if r > 0.1
                  else "no directional selection")
        ax.text(0.97, 0.97, f"r = {r:+.3f}\n{interp}",
                transform=ax.transAxes, ha="right", va="top", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    add_regression(ax1, gen_vals, cw_gen, r1, slope1, intercept1,
                   "Mother generation",
                   "care_weight (at birth)",
                   f"care_weight over generations\n(n={len(cw_gen)} births)")

    add_regression(ax2, cw_surv, survival_ticks, r2, slope2, intercept2,
                   "care_weight (at first birth)",
                   "Ticks alive after first birth",
                   f"Does care hurt survival?\n(n={len(cw_surv)} mothers)",
                   color="darkorange")

    fig.suptitle("Reproductive Fitness by Genotype", fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "reproductive_success_by_genotype.png"), dpi=120)
    plt.close()

    summary = {
        "n_births": len(cw_gen),
        "care_vs_generation_r": r1,
        "care_vs_survival_r": r2,
    }
    print(f"\n=== Reproductive Fitness by Genotype ===")
    print(f"  Births logged         : {len(cw_gen)}")
    print(f"  care vs generation r  : {r1:+.4f}  "
          f"({'selection against care' if r1 < -0.1 else 'selection for care' if r1 > 0.1 else 'no directional selection'})")
    print(f"  care vs survival r    : {r2:+.4f}  "
          f"({'care costs survival' if r2 < -0.1 else 'care aids survival' if r2 > 0.1 else 'no clear effect'})")
    print("=========================================\n")
    return summary


def plot_weight_vs_survival(genomes: list[dict], output_dir: str) -> None:
    """Scatter plot: weights vs survival."""
    if plt is None or not genomes:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    care = [g.get("care_weight", 0) for g in genomes]
    forage = [g.get("forage_weight", 0) for g in genomes]
    survival = [g.get("lifetime", 0) for g in genomes]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    ax1.scatter(care, survival, alpha=0.5)
    ax1.set_xlabel("care_weight")
    ax1.set_ylabel("Lifetime")
    ax1.set_title("Care Weight vs Survival")
    ax1.grid(True, alpha=0.3)
    
    ax2.scatter(forage, survival, alpha=0.5)
    ax2.set_xlabel("forage_weight")
    ax2.set_ylabel("Lifetime")
    ax2.set_title("Forage Weight vs Survival")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "weight_vs_survival.png"))
    plt.close()


def plot_learning_rate_trajectory(
    snapshots: list[dict],
    output_dir: str,
    gen0_lr: float = 0.1,
) -> None:
    """
    Plot avg_learning_rate over ticks (phase4 Baldwin effect signature plot).

    If learning_rate is selected upward, it means plasticity provides real fitness
    benefit and the population is evolving to exploit it — classic Baldwin effect.
    If flat/declining, plasticity is neutral or costly.
    """
    if plt is None or not snapshots:
        return
    if not any("avg_learning_rate" in s for s in snapshots):
        return

    plot_dir = ensure_plot_dir(output_dir)

    valid = [s for s in snapshots if s.get("avg_learning_rate") is not None]
    if not valid:
        return

    ticks = [s["tick"]                                    for s in valid]
    lr    = [s["avg_learning_rate"]                       for s in valid]
    lr_lo = [s.get("min_learning_rate", s["avg_learning_rate"]) for s in valid]
    lr_hi = [s.get("max_learning_rate", s["avg_learning_rate"]) for s in valid]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(ticks, lr, color="mediumpurple", linewidth=2,
            label="mean learning_rate", zorder=3)
    ax.fill_between(ticks, lr_lo, lr_hi, alpha=0.18, color="mediumpurple",
                    label="min/max range")
    ax.axhline(gen0_lr, color="gray", linestyle="--", linewidth=1.2,
               label=f"Gen 0 start ({gen0_lr:.2f})")
    ax.set_xlabel("Tick  (≈ generation every 100 ticks)")
    ax.set_ylabel("learning_rate")
    ax.set_title("Learning Rate Evolution — Baldwin Effect Signature\n"
                 "(rising = plasticity fitness benefit selected; flat/falling = neutral/costly)")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "learning_rate_trajectory.png"), dpi=120)
    plt.close()


def plot_evolution_trajectory(
    snapshots: list[dict],
    output_dir: str,
    r0_baseline: float = 0.365,
    gen0_care: float = 0.500,
) -> None:
    """
    3-panel evolution trajectory answering three analysis questions:
      Panel 1 — care_weight over ticks with phase annotations and reference lines
      Panel 2 — forage_weight over ticks (confirms independence from care)
      Panel 3 — population over ticks (confirms care decline ≠ survival harm)

    Reference lines:
      gen0_care    : neutral start (default Genome = 0.5)
      r0_baseline  : R0 survivor avg care (lifetime filter, no evolution)
    """
    if plt is None or not snapshots:
        return

    plot_dir = ensure_plot_dir(output_dir)

    ticks   = [s["tick"]              for s in snapshots]
    care    = [s["avg_care_weight"]   for s in snapshots]
    c_min   = [s["min_care_weight"]   for s in snapshots]
    c_max   = [s["max_care_weight"]   for s in snapshots]
    forage  = [s["avg_forage_weight"] for s in snapshots]
    n_moth  = [s["n_mothers"]         for s in snapshots]

    # Phase boundaries (tick-based, derived from trajectory inspection)
    phase_bounds = [
        (0,   600,  "Growth\n(boom)",      "lightgreen"),
        (600, 1500, "Crash\n(cap pressure)", "lightyellow"),
        (1500, ticks[-1], "Slow erosion",  "lightsalmon"),
    ]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 9), sharex=True)

    # ── Panel 1: care_weight ──
    for t_start, t_end, label, color in phase_bounds:
        ax1.axvspan(t_start, t_end, alpha=0.12, color=color, label=label)
    ax1.plot(ticks, care, color="steelblue", linewidth=2, label="mean care_weight", zorder=3)
    ax1.fill_between(ticks, c_min, c_max, alpha=0.18, color="steelblue", label="min/max range")
    ax1.axhline(gen0_care, color="gray",      linestyle="--", linewidth=1.2,
                label=f"Gen 0 start ({gen0_care:.3f})")
    ax1.axhline(r0_baseline, color="crimson", linestyle=":",  linewidth=1.4,
                label=f"R0 survivors ({r0_baseline:.3f})")
    ax1.set_ylabel("care_weight")
    ax1.set_title("Evolution Trajectory — care vs forage over 5000 ticks")
    ax1.set_ylim(0, 1)
    ax1.legend(loc="upper right", fontsize=7, ncol=2)
    ax1.grid(True, alpha=0.3)

    # ── Panel 2: forage_weight ──
    ax2.plot(ticks, forage, color="darkorange", linewidth=2, label="mean forage_weight")
    ax2.axhline(0.500, color="gray", linestyle="--", linewidth=1.2, label="Gen 0 start (0.500)")
    ax2.set_ylabel("forage_weight")
    ax2.set_ylim(0, 1)
    ax2.legend(loc="upper right", fontsize=7)
    ax2.grid(True, alpha=0.3)

    # ── Panel 3: population ──
    ax3.plot(ticks, n_moth, color="seagreen", linewidth=2, label="n_mothers alive")
    ax3.set_xlabel("Tick  (≈ generation every 100 ticks)")
    ax3.set_ylabel("Mothers alive")
    ax3.legend(loc="upper right", fontsize=7)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "evolution_trajectory.png"), dpi=120)
    plt.close()


def plot_start_vs_end_multiseed(
    summary: list[dict],
    output_dir: str,
    gen0_care: float = 0.500,
    r0_baseline: float = 0.365,
) -> None:
    """
    Per-seed bar chart: Gen 0 care vs Gen 50 final care.

    Each bar = final care for one seed.
    Color: steelblue if care declined (9/10 expected), coral if rose.
    Reference lines: Gen 0 start (0.500) and R0 survivors (0.365).
    Answers Q3: Gen 0 vs Gen 50 is the fair evolutionary comparison.
    """
    if plt is None or not summary:
        return

    plot_dir = ensure_plot_dir(output_dir)

    seeds       = [s["seed"]            for s in summary]
    final_care  = [s["final_care_mean"] for s in summary]
    deltas      = [fc - gen0_care       for fc in final_care]
    colors      = ["steelblue" if d < 0 else "coral" for d in deltas]

    x = list(range(len(seeds)))
    mean_final = sum(final_care) / len(final_care)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(x, final_care, color=colors, edgecolor="black", alpha=0.85, width=0.6)

    # Annotate each bar with delta
    for bar, delta, fc in zip(bars, deltas, final_care):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.008,
                f"{delta:+.3f}",
                ha="center", va="bottom", fontsize=7.5,
                color="darkblue" if delta < 0 else "darkred")

    ax.axhline(gen0_care,   color="gray",    linestyle="--", linewidth=1.5,
               label=f"Gen 0 start ({gen0_care:.3f}) — all seeds")
    ax.axhline(r0_baseline, color="crimson", linestyle=":",  linewidth=1.5,
               label=f"R0 survivors ({r0_baseline:.3f}) — lifetime filter")
    ax.axhline(mean_final,  color="steelblue", linestyle="-.", linewidth=1.5,
               label=f"Cross-seed mean final ({mean_final:.3f})")

    ax.set_xticks(x)
    ax.set_xticklabels([f"seed {s}" for s in seeds], rotation=30, ha="right")
    ax.set_ylabel("Final care_weight (Gen 50)")
    ax.set_title(
        "Gen 0 → Gen 50: Does evolution favor care?\n"
        "Blue = declined (rB < C), Coral = rose (rB ≥ C)",
        fontsize=10
    )
    ax.set_ylim(0, 0.75)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.text(
        0.5, -0.04,
        "Seed 48 (coral): low foraging competition → no population compression → care drifted up.\n"
        "Confirms decline in other 9 seeds is driven by energetic competition, not a fixed penalty on care.",
        ha="center", fontsize=7.5, color="dimgray", style="italic"
    )
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "start_vs_end_multiseed.png"), dpi=120, bbox_inches="tight")
    plt.close()


def plot_generation_trend(snapshots: list[dict], output_dir: str) -> None:
    """Plot genome trends over time.

    Top panel  : care_weight mean with min/max shading.
    Bottom panel: forage_weight mean (rules out hitchhiking).
    Secondary X-axis label shows avg_generation alongside tick.
    """
    if plt is None or not snapshots:
        return

    plot_dir = ensure_plot_dir(output_dir)

    ticks   = [s.get("tick", 0)            for s in snapshots]
    care    = [s.get("avg_care_weight", 0) for s in snapshots]
    c_min   = [s.get("min_care_weight", 0) for s in snapshots]
    c_max   = [s.get("max_care_weight", 0) for s in snapshots]
    forage  = [s.get("avg_forage_weight", 0) for s in snapshots]
    avg_gen = [s.get("avg_generation", 0)  for s in snapshots]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    # Top: care_weight
    ax1.plot(ticks, care, color="steelblue", linewidth=2, label="mean care_weight")
    ax1.fill_between(ticks, c_min, c_max, alpha=0.2, color="steelblue", label="min/max range")
    ax1.set_ylabel("care_weight")
    ax1.set_title("Genome Evolution Over Time (selection vs drift check)")
    ax1.set_ylim(0, 1)
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # Annotate avg generation at a few key ticks
    step = max(1, len(ticks) // 5)
    for i in range(0, len(ticks), step):
        ax1.annotate(f"gen~{avg_gen[i]:.1f}",
                     xy=(ticks[i], care[i]),
                     xytext=(0, 8), textcoords="offset points",
                     fontsize=7, color="steelblue", ha="center")

    # Bottom: forage_weight
    ax2.plot(ticks, forage, color="darkorange", linewidth=2, label="mean forage_weight")
    ax2.set_xlabel("Tick")
    ax2.set_ylabel("forage_weight")
    ax2.set_ylim(0, 1)
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "generation_trend.png"))
    plt.close()


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def generate_all_plots(output_dir: str, **kwargs) -> None:
    """Generate all applicable plots for a run."""
    if plt is None:
        print("Plotting skipped: matplotlib not available")
        return
    
    print(f"Generating plots in {output_dir}/plots/")
    
    # Load data
    choice_records = load_csv(os.path.join(output_dir, "choice_log.csv"))
    care_records = load_csv(os.path.join(output_dir, "care_log.csv"))
    history = load_json(os.path.join(output_dir, "population_history.json"))
    snapshots = load_json(os.path.join(output_dir, "generation_snapshots.json"))
    
    population = history.get("population", kwargs.get("population_history", []))
    energy = history.get("energy", kwargs.get("energy_history", []))
    max_tick = len(population) if population else kwargs.get("max_tick", 300)
    
    # Core plots
    if population:
        plot_population(population, output_dir)
    if energy:
        plot_energy(energy, output_dir)
    if population and energy:
        plot_population_and_energy(population, energy, output_dir)
    
    # Care plots
    if care_records:
        plot_care_frequency(care_records, max_tick, output_dir)
        plot_care_success_rate(care_records, output_dir)
        plot_care_by_relatedness(care_records, output_dir)
    
    if choice_records:
        plot_care_distance_histogram(choice_records, output_dir)
        plot_chosen_by_distance(choice_records, output_dir)
    
    # Evolution plots
    if snapshots:
        plot_generation_trend(snapshots, output_dir)
        plot_evolution_trajectory(snapshots, output_dir)
        plot_learning_rate_trajectory(snapshots, output_dir)  # phase4 Baldwin evidence
    plot_reproductive_success_by_genotype(output_dir)

    # Hamilton split analysis (own-lineage vs foreign)
    if care_records:
        analyze_hamilton_split(output_dir)

    # Lineage fitness (B_social)
    plot_lineage_fitness(output_dir)

    print("Plots generated.")