#!/usr/bin/env python3
"""
Baldwin Effect Analysis — Fitness and Plasticity Over Evolutionary Time

This script reads data from Phase 6/7 evolution runs and generates three plots:
  1. Fitness over time
  2. Phenotypic plasticity over time
  3. Combined comparison figure (qualitative Baldwin-effect inspection)

═══════════════════════════════════════════════════════════════════════════
FITNESS DEFINITION
═══════════════════════════════════════════════════════════════════════════
There is no direct fitness variable in this simulation.

  Proxy: ROLLING CHILD SURVIVAL RATE (window = ROLLING_WINDOW ticks)
  ─────────────────────────────────────────────────────────────────────
  For each tick t:
    births_in_window    = children born in [t - W, t]
    hunger_deaths       = children who died from hunger (cause="hunger") in [t - W, t]
    child_survival[t]   = 1 - hunger_deaths / max(1, births_in_window)

  Justification: The project goal is for maternal care to emerge as a heritable
  behavior that improves child survival. In this simulation, a caring lineage
  produces children that survive to maturity, become new mothers, and continue
  the lineage. Child survival rate therefore directly couples care behavior to
  reproductive success and evolutionary persistence. It is the most ecologically
  justified fitness proxy available without a pre-defined fitness function.

  If birth records are absent (no reproduction phase has run), a fallback
  proxy is reported:
    alive_children[t] / (alive_children[t] + cum_hunger_deaths[t])

═══════════════════════════════════════════════════════════════════════════
PHENOTYPIC PLASTICITY DEFINITION
═══════════════════════════════════════════════════════════════════════════
  Proxy: MEAN LEARNED CARE INCREMENT
  ─────────────────────────────────────────────────────────────────────
    delta_care[t] = mean( expressed_care_weight[t] - genome_care_weight[t] )
    averaged across all living mothers at tick t.

  Interpretation:
    • Large delta_care → mothers are relying on lifetime learning on top of
      their inherited baseline; plasticity is doing significant adaptive work.
    • Shrinking delta_care → genome.care_weight has risen to match expressed
      behavior; genetic assimilation has occurred; plasticity becoming redundant.
    • delta_care ≈ 0 throughout → treatment has plasticity disabled, or no
      assimilation pressure exists.

  For the plasticity-OFF treatment: delta_care ≡ 0 (expressed == genome
  by design). The plasticity-OFF line is kept as a reference baseline.

═══════════════════════════════════════════════════════════════════════════
EXPECTED BALDWIN-EFFECT PATTERN (qualitative reference only)
═══════════════════════════════════════════════════════════════════════════
  1. Fitness increases over evolutionary time and plateaus.
  2. Plasticity (delta_care) is high early, decreases in the later stage.
  3. Two-step interpretation:
       Step 1 — plasticity helps early generations survive and reproduce.
       Step 2 — genome.care_weight rises, reducing the need for lifetime
                learning; delta_care shrinks; fitness is maintained by
                inherited instinct, not just learned behavior.

  The script checks for this pattern quantitatively and reports honestly
  whether it is present, absent, or ambiguous.

═══════════════════════════════════════════════════════════════════════════
EXPECTED INPUT FILES (produced by Phase 6/7 evolution runs)
═══════════════════════════════════════════════════════════════════════════
  evolution_tick_log.csv — one row per (tick, seed):
    Required columns:
      tick, seed, treatment (str: "plasticity_on" | "plasticity_off"),
      n_alive_mothers, n_alive_children,
      mean_genome_care_weight, mean_expressed_care_weight,
      n_births_this_tick, n_child_deaths_hunger_this_tick

  All columns must be present for full analysis. If some are missing the
  script reports which plots can/cannot be generated and why.

  Multiple seeds are aggregated automatically (mean ± SD across seeds).

═══════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════
  python experiments/baldwin_analysis/plot_baldwin_effect.py \\
    --data  outputs/phase7_evolution_plasticity/20XXXXXX/evolution_tick_log.csv \\
    --out   outputs/baldwin_analysis/

  The CSV must contain a 'treatment' column with values "plasticity_on" and/or
  "plasticity_off". If both are present, a direct comparison is shown.
  If only one is present, only that treatment is plotted.
"""

import argparse
import csv
import math
import os
import sys
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# ─── Tuneable constants ───────────────────────────────────────────────────────

ROLLING_WINDOW = 500    # ticks for rolling fitness / plasticity averages
MIN_BIRTHS_FOR_RATE = 1  # denominator guard for child survival rate
COLORS = {
    "plasticity_on":  "#2196F3",   # blue — plasticity enabled
    "plasticity_off": "#F44336",   # red  — no plasticity (genetic only)
    "delta_care":     "#4CAF50",   # green — learned care increment
    "genome_care":    "#FF9800",   # orange — inherited care weight
}

# ─── Required columns ─────────────────────────────────────────────────────────

REQUIRED_COLS = {
    "tick", "seed", "treatment",
    "n_alive_mothers", "n_alive_children",
    "mean_genome_care_weight", "mean_expressed_care_weight",
    "n_births_this_tick", "n_child_deaths_hunger_this_tick",
}


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_columns(rows: list[dict], path: str) -> tuple[set[str], set[str]]:
    if not rows:
        print(f"ERROR: {path} is empty.")
        sys.exit(1)
    present = set(rows[0].keys())
    missing = REQUIRED_COLS - present
    return present, missing


def parse_float(v: str) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return float("nan")


def to_array(rows: list[dict], col: str) -> np.ndarray:
    return np.array([parse_float(r[col]) for r in rows])


# ─── Aggregation ─────────────────────────────────────────────────────────────

def aggregate_by_tick(rows: list[dict], present: set[str]) -> dict[int, dict]:
    """
    Group rows by tick. For each tick: compute mean ± SD across seeds for
    all numeric columns.
    """
    from collections import defaultdict
    by_tick: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_tick[int(r["tick"])].append(r)

    numeric_cols = (present & REQUIRED_COLS) - {"tick", "seed", "treatment"}
    result: dict[int, dict] = {}
    for tick, tick_rows in sorted(by_tick.items()):
        entry = {"tick": tick, "n_seeds": len(tick_rows)}
        for col in numeric_cols:
            vals = [parse_float(r[col]) for r in tick_rows]
            vals = [v for v in vals if not math.isnan(v)]
            entry[f"{col}_mean"] = float(np.mean(vals)) if vals else float("nan")
            entry[f"{col}_sd"] = float(np.std(vals)) if vals else float("nan")
        result[tick] = entry
    return result


# ─── Rolling metrics ──────────────────────────────────────────────────────────

def rolling_child_survival(agg: dict[int, dict], window: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute rolling child survival rate.
    Returns (ticks, mean_survival, sd_survival).

    survival[t] = 1 - rolling_hunger_deaths[t] / max(1, rolling_births[t])

    Note: per-tick births and deaths are accumulated within each window.
    This uses the tick-level means (averaged across seeds), then computes
    the rate.  Seed-level variance cannot be recovered from aggregated
    means; the SD is set to NaN when seed-level data is not available.
    """
    ticks_sorted = sorted(agg.keys())
    ticks = np.array(ticks_sorted)

    births_col = "n_births_this_tick_mean"
    deaths_col = "n_child_deaths_hunger_this_tick_mean"

    if births_col not in agg[ticks_sorted[0]] or deaths_col not in agg[ticks_sorted[0]]:
        return ticks, np.full(len(ticks), float("nan")), np.full(len(ticks), float("nan"))

    births_arr = np.array([agg[t].get(births_col, float("nan")) for t in ticks_sorted])
    deaths_arr = np.array([agg[t].get(deaths_col, float("nan")) for t in ticks_sorted])

    survival = np.full(len(ticks), float("nan"))
    for i, t in enumerate(ticks_sorted):
        # Window: [t - window, t]
        idx_start = max(0, i - window)
        w_births = np.nansum(births_arr[idx_start:i + 1])
        w_deaths = np.nansum(deaths_arr[idx_start:i + 1])
        if w_births >= MIN_BIRTHS_FOR_RATE:
            survival[i] = 1.0 - w_deaths / w_births
        # else: not enough births yet — nan

    return ticks, survival, np.full(len(ticks), float("nan"))


def rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
    result = np.full_like(arr, fill_value=float("nan"), dtype=float)
    for i in range(len(arr)):
        idx_start = max(0, i - window + 1)
        chunk = arr[idx_start:i + 1]
        valid = chunk[~np.isnan(chunk)]
        if len(valid) > 0:
            result[i] = float(np.mean(valid))
    return result


def extract_series(agg: dict[int, dict], col_mean: str, col_sd: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract mean and SD arrays for a column, indexed by sorted tick."""
    ticks = np.array(sorted(agg.keys()))
    means = np.array([agg[t].get(col_mean, float("nan")) for t in sorted(agg.keys())])
    sds   = np.array([agg[t].get(col_sd,   float("nan")) for t in sorted(agg.keys())])
    return ticks, means, sds


# ─── Baldwin pattern verdict ──────────────────────────────────────────────────

def baldwin_verdict(
    ticks: np.ndarray,
    fitness: np.ndarray,
    delta_care: np.ndarray,
) -> dict:
    """
    Quantitative check for the three qualitative Baldwin-effect signatures.

    Returns a dict with:
      fitness_increases     : bool  — fitness trend is positive overall
      fitness_plateaus      : bool  — growth rate in second half < first half
      plasticity_early_high : bool  — mean delta_care in first third > last third
      plasticity_decreases  : bool  — delta_care trend is negative overall
      pattern_present       : bool  — all three signatures present
      notes                 : list[str]
    """
    notes = []
    valid_f = ~np.isnan(fitness)
    valid_p = ~np.isnan(delta_care)

    fitness_increases = False
    fitness_plateaus = False
    plasticity_early_high = False
    plasticity_decreases = False

    if valid_f.sum() < 20:
        notes.append("Insufficient fitness data points for verdict (< 20 valid ticks).")
    else:
        f_valid = fitness[valid_f]
        n = len(f_valid)
        first_half_mean = float(np.mean(f_valid[: n // 2]))
        second_half_mean = float(np.mean(f_valid[n // 2 :]))

        # Overall trend: is final mean > initial mean?
        fitness_increases = second_half_mean > first_half_mean + 0.02
        notes.append(
            f"Fitness: first-half mean={first_half_mean:.3f}, "
            f"second-half mean={second_half_mean:.3f}."
        )

        # Plateau: growth rate decelerating?
        q1 = float(np.mean(f_valid[: n // 4]))
        q2 = float(np.mean(f_valid[n // 4 : n // 2]))
        q3 = float(np.mean(f_valid[n // 2 : 3 * n // 4]))
        q4 = float(np.mean(f_valid[3 * n // 4 :]))
        early_growth = q2 - q1
        late_growth  = q4 - q3
        fitness_plateaus = late_growth < early_growth
        notes.append(
            f"Fitness growth: early={early_growth:+.3f}, late={late_growth:+.3f} "
            f"({'decelerating — consistent with plateau' if fitness_plateaus else 'not decelerating'})."
        )

    if valid_p.sum() < 20:
        notes.append("Insufficient plasticity data points for verdict (< 20 valid ticks).")
    else:
        p_valid = delta_care[valid_p]
        n = len(p_valid)
        early_mean = float(np.mean(p_valid[: n // 3]))
        late_mean  = float(np.mean(p_valid[2 * n // 3 :]))
        plasticity_early_high = early_mean > late_mean + 0.02
        plasticity_decreases  = late_mean < early_mean
        notes.append(
            f"Delta_care: early mean={early_mean:.4f}, late mean={late_mean:.4f} "
            f"({'decreasing — consistent with assimilation' if plasticity_decreases else 'not decreasing'})."
        )

    pattern_present = fitness_increases and fitness_plateaus and plasticity_decreases
    if pattern_present:
        notes.append("VERDICT: Baldwin-effect pattern IS PRESENT in data.")
    else:
        missing = []
        if not fitness_increases:
            missing.append("fitness did not increase")
        if not fitness_plateaus:
            missing.append("fitness did not plateau / decelerate")
        if not plasticity_decreases:
            missing.append("plasticity contribution did not decrease")
        notes.append(f"VERDICT: Baldwin-effect pattern NOT CONFIRMED. Missing: {'; '.join(missing)}.")

    return {
        "fitness_increases": fitness_increases,
        "fitness_plateaus": fitness_plateaus,
        "plasticity_early_high": plasticity_early_high,
        "plasticity_decreases": plasticity_decreases,
        "pattern_present": pattern_present,
        "notes": notes,
    }


# ─── Plots ────────────────────────────────────────────────────────────────────

def _shade(ax, ticks, mean, sd, color, label, alpha=0.20):
    valid = ~np.isnan(mean)
    if valid.sum() < 2:
        ax.plot([], [], color=color, label=f"{label} (no data)")
        return
    ax.plot(ticks[valid], mean[valid], color=color, linewidth=2.0, label=label)
    if sd is not None and not np.all(np.isnan(sd)):
        sd_valid = np.where(np.isnan(sd), 0.0, sd)
        ax.fill_between(
            ticks[valid],
            (mean - sd_valid)[valid],
            (mean + sd_valid)[valid],
            alpha=alpha, color=color,
        )


def plot_fitness(treatments: dict[str, dict], out_dir: str) -> str:
    """
    Plot 1: Fitness (rolling child survival rate) over evolutionary time.

    fitness = 1 - rolling_hunger_deaths / rolling_births  (window=ROLLING_WINDOW ticks)

    One line per treatment (plasticity_on, plasticity_off) if both available.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    for treat, d in treatments.items():
        ticks, surv, surv_sd = d["fitness_ticks"], d["fitness_mean"], d["fitness_sd"]
        color = COLORS.get(treat, "#888888")
        label = "Plasticity ON" if treat == "plasticity_on" else "Plasticity OFF (genetic only)"
        _shade(ax, ticks, surv, surv_sd, color, label)

    ax.set_xlabel("Tick (evolutionary time)")
    ax.set_ylabel(f"Child Survival Rate  (rolling {ROLLING_WINDOW}-tick window)")
    ax.set_title(
        "Plot 1 — Fitness Over Evolutionary Time\n"
        "Proxy: rolling child survival rate  "
        "(1 − hunger deaths / births in window)"
    )
    ax.set_ylim(-0.05, 1.10)
    ax.axhline(0.5, color="gray", linestyle=":", linewidth=0.8, alpha=0.5)
    ax.legend()

    ax.text(
        0.01, 0.02,
        "Fitness proxy: child survival rate.\nNo direct fitness variable exists in this simulation.\n"
        "See script docstring for full justification.",
        transform=ax.transAxes, fontsize=7, color="gray",
        verticalalignment="bottom",
    )

    plt.tight_layout()
    path = os.path.join(out_dir, "01_fitness_over_time.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def plot_plasticity(treatments: dict[str, dict], out_dir: str) -> str:
    """
    Plot 2: Phenotypic plasticity (mean learned care increment) over time.

    delta_care[t] = mean(expressed_care_weight - genome_care_weight)
    across all living mothers at tick t, then rolling-smoothed.

    Also shows genome.care_weight trajectory (inherited component rising =
    genetic assimilation in progress).
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: delta_care per treatment
    ax = axes[0]
    for treat, d in treatments.items():
        ticks = d["ticks"]
        dc = d["delta_care_mean"]
        color = COLORS.get(treat, "#888888")
        label = "Plasticity ON" if treat == "plasticity_on" else "Plasticity OFF"
        _shade(ax, ticks, dc, d["delta_care_sd"], color, label)

    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Mean learned care increment\n(expressed − genome care weight)")
    ax.set_title("Plasticity Contribution Over Time\n(↓ = assimilation occurring)")
    ax.legend()
    ax.text(
        0.01, 0.98,
        "delta_care = expressed_care_weight − genome_care_weight\n"
        "Shrinking gap → genetic assimilation",
        transform=ax.transAxes, fontsize=7, color="gray",
        verticalalignment="top",
    )

    # Right: genome.care_weight trajectory (the inherited component)
    ax2 = axes[1]
    for treat, d in treatments.items():
        ticks = d["ticks"]
        gc = d["genome_care_mean"]
        color = COLORS.get(treat, "#888888")
        label = "Plasticity ON" if treat == "plasticity_on" else "Plasticity OFF"
        _shade(ax2, ticks, gc, d["genome_care_sd"], color, label)

    ax2.set_xlabel("Tick")
    ax2.set_ylabel("Mean inherited care weight (genome.care_weight)")
    ax2.set_title("Inherited Care Weight Over Time\n(↑ = genetic assimilation)")
    ax2.set_ylim(-0.02, 1.05)
    ax2.legend()

    fig.suptitle("Plot 2 — Phenotypic Plasticity Over Evolutionary Time")
    plt.tight_layout()
    path = os.path.join(out_dir, "02_plasticity_over_time.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def plot_combined(treatments: dict[str, dict], verdicts: dict[str, dict], out_dir: str) -> str:
    """
    Plot 3: Combined qualitative inspection figure.

    Shows fitness and normalized plasticity on the same time axis for the
    plasticity_on treatment (the treatment where both signals are present).

    The two-step Baldwin pattern should be visible as:
      - Phase 1 (early): delta_care is high, fitness rising
      - Phase 2 (late):  delta_care falls, fitness plateaus (maintained by genome)
    """
    treat = "plasticity_on" if "plasticity_on" in treatments else list(treatments.keys())[0]
    d = treatments[treat]

    ticks = d["ticks"]
    fitness = d["fitness_mean"]
    dc_raw  = d["delta_care_mean"]
    gc      = d["genome_care_mean"]

    # Normalize delta_care to [0, 1] range for overlay visibility
    dc_max = np.nanmax(dc_raw) if not np.all(np.isnan(dc_raw)) else 1.0
    dc_norm = dc_raw / max(dc_max, 1e-9)

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    # Fitness (left axis)
    valid_f = ~np.isnan(fitness)
    if valid_f.sum() > 1:
        ax1.plot(ticks[valid_f], fitness[valid_f],
                 color=COLORS["plasticity_on"], linewidth=2.5,
                 label="Fitness (child survival rate)", zorder=3)
    else:
        ax1.plot([], [], color=COLORS["plasticity_on"],
                 label="Fitness — insufficient data")

    # Inherited care weight (left axis, dashed)
    valid_gc = ~np.isnan(gc)
    if valid_gc.sum() > 1:
        ax1.plot(ticks[valid_gc], gc[valid_gc],
                 color=COLORS["genome_care"], linewidth=1.8, linestyle="--",
                 label="Inherited care weight (genome)", zorder=2)

    # Plasticity contribution (right axis, green)
    valid_dc = ~np.isnan(dc_norm)
    if valid_dc.sum() > 1:
        ax2.fill_between(ticks[valid_dc], 0, dc_norm[valid_dc],
                         color=COLORS["delta_care"], alpha=0.25,
                         label="Plasticity contribution (normalised)")
        ax2.plot(ticks[valid_dc], dc_norm[valid_dc],
                 color=COLORS["delta_care"], linewidth=1.5, alpha=0.8)

    ax1.set_xlabel("Tick (evolutionary time)")
    ax1.set_ylabel("Fitness / Genome care weight  [0 – 1]")
    ax2.set_ylabel("Normalised plasticity contribution  [0 – 1]", color=COLORS["delta_care"])
    ax2.tick_params(axis="y", labelcolor=COLORS["delta_care"])
    ax2.set_ylim(-0.05, 1.20)
    ax1.set_ylim(-0.05, 1.10)

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    from matplotlib.patches import Patch
    lines2 = [Patch(color=COLORS["delta_care"], alpha=0.5, label="Plasticity contribution (normalised)")]
    ax1.legend(lines1 + lines2, labels1 + [lines2[0].get_label()], loc="upper left", fontsize=9)

    # Annotate expected steps
    x_mid = (ticks[-1] - ticks[0]) * 0.25 + ticks[0] if len(ticks) > 0 else 0
    x_late = (ticks[-1] - ticks[0]) * 0.65 + ticks[0] if len(ticks) > 0 else 0
    ax1.axvline(x_mid, color="gray", linestyle=":", linewidth=1.0, alpha=0.5)
    ax1.text(x_mid + 10, 0.05, "← Step 1\nPlasticity\nscaffolds", fontsize=8, color="gray")
    ax1.text(x_late + 10, 0.05, "← Step 2\nGenetic\nassimilation", fontsize=8, color="gray")

    # Verdict
    v = verdicts.get(treat, {})
    verdict_str = (
        "Baldwin pattern: PRESENT" if v.get("pattern_present")
        else "Baldwin pattern: NOT CONFIRMED"
    )
    notes_str = "\n".join(v.get("notes", []))
    ax1.text(
        0.01, 1.01,
        f"{verdict_str}\n{notes_str}",
        transform=ax1.transAxes, fontsize=6.5, color="black",
        verticalalignment="bottom",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
    )

    ax1.set_title(
        "Plot 3 — Combined Baldwin Effect Inspection\n"
        "(Qualitative reference — do not force data to match expected pattern)"
    )

    plt.tight_layout()
    path = os.path.join(out_dir, "03_combined_baldwin_comparison.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


# ─── Data preparation ─────────────────────────────────────────────────────────

def prepare_treatment(rows: list[dict], present: set[str]) -> dict:
    """
    From a list of rows (single treatment), compute all signals needed for plots.
    Returns a dict of arrays indexed by tick.
    """
    agg = aggregate_by_tick(rows, present)
    ticks = np.array(sorted(agg.keys()))

    def get_series(col):
        m = np.array([agg[t].get(f"{col}_mean", float("nan")) for t in sorted(agg.keys())])
        s = np.array([agg[t].get(f"{col}_sd",   float("nan")) for t in sorted(agg.keys())])
        return m, s

    # Genome care weight (inherited)
    gc_m, gc_s = get_series("mean_genome_care_weight")

    # Expressed care weight (phenotypic)
    ec_m, ec_s = get_series("mean_expressed_care_weight")

    # Delta care (plasticity contribution) = expressed - inherited
    dc_m = ec_m - gc_m
    dc_s = np.sqrt(np.where(np.isnan(gc_s), 0, gc_s**2) + np.where(np.isnan(ec_s), 0, ec_s**2))
    # Smooth delta_care with rolling window for display
    dc_m_smooth = rolling_mean(dc_m, ROLLING_WINDOW)
    gc_m_smooth = rolling_mean(gc_m, ROLLING_WINDOW)

    # Fitness: rolling child survival rate
    f_ticks, f_mean, f_sd = rolling_child_survival(agg, ROLLING_WINDOW)

    return {
        "ticks":            ticks,
        "fitness_ticks":    f_ticks,
        "fitness_mean":     f_mean,
        "fitness_sd":       f_sd,
        "genome_care_mean": gc_m_smooth,
        "genome_care_sd":   gc_s,
        "delta_care_mean":  dc_m_smooth,
        "delta_care_sd":    dc_s,
        "expressed_care_mean": ec_m,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Baldwin-effect fitness and plasticity plots.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to evolution_tick_log.csv (from Phase 6/7 evolution run). "
             "Must contain a 'treatment' column.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory for plots (default: same directory as --data).",
    )
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"ERROR: --data file not found: {args.data}")
        print(
            "\nThis script requires output from Phase 6/7 evolution runs.\n"
            "Run the appropriate phase first, then call this script.\n"
            "Expected file: evolution_tick_log.csv (see script docstring for columns)."
        )
        return 1

    out_dir = args.out or os.path.dirname(os.path.abspath(args.data))
    os.makedirs(out_dir, exist_ok=True)

    # Load and validate
    print(f"Loading: {args.data}")
    all_rows = load_csv(args.data)
    present, missing = check_columns(all_rows, args.data)

    if missing:
        print(f"\nWARNING: Missing columns: {sorted(missing)}")
        print("Some metrics cannot be computed. Available analysis will continue.")
        print("To fix: ensure Phase 6/7 per-tick logging includes all required columns.")

    # Split by treatment
    treatment_names = sorted({r.get("treatment", "unknown") for r in all_rows})
    print(f"Treatments found: {treatment_names}")

    if not treatment_names or all(t == "unknown" for t in treatment_names):
        print("ERROR: 'treatment' column missing or empty. Cannot split by treatment.")
        return 1

    treatments: dict[str, dict] = {}
    for treat in treatment_names:
        rows_t = [r for r in all_rows if r.get("treatment") == treat]
        print(f"  {treat}: {len(rows_t)} rows, "
              f"{len({r['seed'] for r in rows_t})} seeds, "
              f"{len({r['tick'] for r in rows_t})} ticks")
        treatments[treat] = prepare_treatment(rows_t, present)

    # Verdicts per treatment
    verdicts: dict[str, dict] = {}
    for treat, d in treatments.items():
        v = baldwin_verdict(d["fitness_ticks"], d["fitness_mean"], d["delta_care_mean"])
        verdicts[treat] = v
        print(f"\n--- Baldwin verdict: {treat} ---")
        for note in v["notes"]:
            print(f"  {note}")

    # Generate plots
    p1 = plot_fitness(treatments, out_dir)
    p2 = plot_plasticity(treatments, out_dir)
    p3 = plot_combined(treatments, verdicts, out_dir)

    print(f"\nPlots saved:")
    print(f"  {p1}")
    print(f"  {p2}")
    print(f"  {p3}")

    # Overall verdict
    any_present = any(v.get("pattern_present", False) for v in verdicts.values())
    print(
        f"\n{'═' * 60}\n"
        f"FINAL BALDWIN ANALYSIS RESULT: "
        f"{'PATTERN PRESENT' if any_present else 'PATTERN NOT CONFIRMED'}\n"
        f"{'═' * 60}"
    )
    print("NOTE: This is a qualitative inspection against an expected pattern.")
    print("If the result does not match the expected shape, that is a valid scientific")
    print("finding — report it honestly as stated in the project instructions.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
