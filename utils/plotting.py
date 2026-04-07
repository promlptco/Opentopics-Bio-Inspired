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
    """Plot genome trends over generations."""
    if plt is None or not snapshots:
        return
    
    plot_dir = ensure_plot_dir(output_dir)
    
    ticks = [s.get("tick", 0) for s in snapshots]
    care = [s.get("avg_care_weight", 0) for s in snapshots]
    forage = [s.get("avg_forage_weight", 0) for s in snapshots]
    learning = [s.get("avg_learning_rate", 0) for s in snapshots]
    
    plt.figure(figsize=(10, 4))
    plt.plot(ticks, care, label="care_weight")
    plt.plot(ticks, forage, label="forage_weight")
    plt.plot(ticks, learning, label="learning_rate")
    plt.xlabel("Tick")
    plt.ylabel("Average Value")
    plt.title("Genome Trends Over Time")
    plt.legend()
    plt.grid(True, alpha=0.3)
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
    
    print("Plots generated.")