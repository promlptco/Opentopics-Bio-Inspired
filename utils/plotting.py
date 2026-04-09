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
        print(f"  Mean rB (own)       : {summary['mean_rB']:.4f}")
        print(f"  Mean C  (own)       : {summary['mean_C']:.4f}")
        print(f"  Mean rB-C (own)     : {summary['mean_rB_minus_C']:.4f}")
        print(f"  Fraction rB > C     : {summary['frac_rB_gt_C']:.3f}")
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

    # Hamilton split analysis (own-lineage vs foreign)
    if care_records:
        analyze_hamilton_split(output_dir)

    # Lineage fitness (B_social)
    plot_lineage_fitness(output_dir)

    print("Plots generated.")