# experiments/phase4_plasticity/make_thesis_plots.py
"""
Generate the 4 cross-run thesis comparison plots.

Output: outputs/thesis_plots/
  selection_gradient_comparison.png  — care_weight vs generation (Phase3 / 4a / 4b)
  population_trough.png              — mothers alive ticks 2000-2600 (Phase4v2 vs Phase3)
  zeroshot_comparison.png            — care-window rate bar chart (Phase2 / 4a / 4b)
  phase_comparison_table.png         — all-metrics summary table

Run from project root:
  python experiments/phase4_plasticity/make_thesis_plots.py
"""
import sys, os, csv, json
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import gridspec

# ── Run directories ──────────────────────────────────────────────────────────
DIRS = {
    "p3":   "outputs/phase3_maternal/run_20260409_232012_seed42",
    "p4a":  "outputs/phase4_plasticity/run_20260410_104824_seed42",
    "p4b":  "outputs/phase4_plasticity/run_20260410_113356_seed42",
    "p2zs": "outputs/phase2_zeroshot/run_20260409_233243_seed42",
    "p4azs":"outputs/phase4_plasticity/run_20260410_105016_seed42",
    "p4bzs":"outputs/phase4_plasticity/run_20260410_113536_seed42",
}
OUT_DIR = "outputs/thesis_plots"
os.makedirs(OUT_DIR, exist_ok=True)
MATURITY_AGE = 100   # config.maturity_age


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)

def load_snapshots(run_dir):
    return load_json(os.path.join(run_dir, "generation_snapshots.json"))

def load_population(run_dir):
    d = load_json(os.path.join(run_dir, "population_history.json"))
    return d.get("population", [])

def load_birth_log(run_dir):
    return load_csv(os.path.join(run_dir, "birth_log.csv"))

def load_care_log(run_dir):
    return load_csv(os.path.join(run_dir, "care_log.csv"))

def care_window_rate(run_dir, window=MATURITY_AGE):
    care = load_care_log(run_dir)
    pop  = load_population(run_dir)
    w_care = [r for r in care
              if r.get("success", "True") in ("True", "1") and int(r["tick"]) <= window]
    w_mt   = sum(p for t, p in enumerate(pop) if t < window)
    return len(w_care) / w_mt if w_mt > 0 else 0.0

def linregress_r(x, y):
    """Pearson r and slope via numpy."""
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    if len(x) < 2:
        return 0.0, 0.0, 0.0
    slope = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    return r, slope[0], slope[1]


# ═══════════════════════════════════════════════════════════════════════════
# Plot 1 — Selection gradient comparison
# ═══════════════════════════════════════════════════════════════════════════

def plot_selection_gradient():
    configs = [
        ("Phase 3\n(no plasticity)",      "p3",  "steelblue"),
        ("Phase 4a\n(blind plasticity)",   "p4a", "coral"),
        ("Phase 4b\n(kin-conditional)",    "p4b", "seagreen"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True)
    fig.suptitle(
        "Selection Against Care: care_weight vs Generation\n"
        "(each point = one birth event; line = OLS fit)",
        fontsize=11, y=1.02,
    )

    for ax, (label, key, color) in zip(axes, configs):
        rows = load_birth_log(DIRS[key])
        if not rows:
            ax.set_title(f"{label}\nno data")
            continue

        gens = [float(r["mother_generation"]) for r in rows]
        cws  = [float(r["mother_care_weight"]) for r in rows]
        r, slope, intercept = linregress_r(gens, cws)

        ax.scatter(gens, cws, alpha=0.25, s=8, color=color, rasterized=True)
        x_line = np.linspace(min(gens), max(gens), 200)
        ax.plot(x_line, slope * x_line + intercept,
                color="black", linewidth=1.8, label=f"r = {r:.4f}")

        ax.axhline(0.500, color="gray", linestyle="--", linewidth=1.0,
                   label="Gen 0 start (0.500)")
        ax.set_xlabel("Mother generation")
        ax.set_ylabel("care_weight at birth" if ax == axes[0] else "")
        ax.set_ylim(0, 1)
        ax.set_title(label, fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.25)

        ax.annotate(f"n={len(rows)}", xy=(0.97, 0.04),
                    xycoords="axes fraction", ha="right", fontsize=8, color="gray")

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "selection_gradient_comparison.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ═══════════════════════════════════════════════════════════════════════════
# Plot 2 — Population trough
# ═══════════════════════════════════════════════════════════════════════════

def plot_population_trough():
    p3_pop  = load_population(DIRS["p3"])
    p4b_pop = load_population(DIRS["p4b"])
    p4b_snaps = load_snapshots(DIRS["p4b"])

    t_start, t_end = 1800, 2800
    ticks = list(range(t_start, t_end + 1))

    p3_slice  = [p3_pop[t - 1]  for t in ticks if t - 1 < len(p3_pop)]
    p4b_slice = [p4b_pop[t - 1] for t in ticks if t - 1 < len(p4b_pop)]
    ticks_trim = ticks[:min(len(p3_slice), len(p4b_slice))]
    p3_slice   = p3_slice[:len(ticks_trim)]
    p4b_slice  = p4b_slice[:len(ticks_trim)]

    # care_weight from snapshots (100-tick resolution) for trough overlay
    snap_ticks = [s["tick"] for s in p4b_snaps if t_start <= s["tick"] <= t_end]
    snap_care  = [s["avg_care_weight"] for s in p4b_snaps if t_start <= s["tick"] <= t_end]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.suptitle(
        "Population Stability Through the Care_Weight Trough (Phase 4b vs Phase 3)\n"
        "Ticks 2000–2600: care_weight dips below R0 survivor avg (0.365) — was population at risk?",
        fontsize=10,
    )

    # ── Panel 1: population ──
    ax1.plot(ticks_trim, p4b_slice, color="seagreen",  linewidth=1.5, label="Phase 4b (kin-cond.)")
    ax1.plot(ticks_trim, p3_slice,  color="steelblue", linewidth=1.5, linestyle="--", label="Phase 3 (no plast.)")
    ax1.axvspan(2000, 2600, alpha=0.10, color="salmon", label="Trough window")
    ax1.axhline(10, color="red", linewidth=0.8, linestyle=":", label="Floor = 10 (min observed: 11)")
    ax1.set_ylabel("Mothers alive")
    ax1.set_ylim(0, 35)
    ax1.legend(fontsize=8, loc="upper right")
    ax1.grid(True, alpha=0.25)

    p4b_trough = [p4b_pop[t - 1] for t in range(2000, 2601)]
    p3_trough  = [p3_pop[t - 1]  for t in range(2000, 2601)]
    ax1.annotate(
        f"Phase 4b min={min(p4b_trough)}, avg={sum(p4b_trough)/len(p4b_trough):.1f}\n"
        f"Phase 3  min={min(p3_trough)},  avg={sum(p3_trough)/len(p3_trough):.1f}",
        xy=(2300, 6), fontsize=8, color="black",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="gray"),
    )

    # ── Panel 2: care_weight ──
    ax2.plot(snap_ticks, snap_care, color="seagreen", linewidth=2, marker="o",
             markersize=4, label="Phase 4b avg care_weight")
    ax2.axhline(0.365, color="crimson", linestyle=":", linewidth=1.4,
                label="R0 survivor avg (0.365)")
    ax2.axhline(0.500, color="gray",   linestyle="--", linewidth=1.0,
                label="Gen 0 start (0.500)")
    ax2.axvspan(2000, 2600, alpha=0.10, color="salmon")
    ax2.set_xlabel("Tick")
    ax2.set_ylabel("care_weight")
    ax2.set_ylim(0.2, 0.6)
    ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(True, alpha=0.25)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "population_trough.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ═══════════════════════════════════════════════════════════════════════════
# Plot 3 — Zero-shot care-window comparison
# ═══════════════════════════════════════════════════════════════════════════

def plot_zeroshot_comparison():
    rates = {
        "Phase 2\n(Phase 3 genomes\nno plasticity)":        care_window_rate(DIRS["p2zs"]),
        "Phase 4a\n(blind plasticity\nlineage-blind)":      care_window_rate(DIRS["p4azs"]),
        "Phase 4b\n(kin-conditional\nplasticity)":          care_window_rate(DIRS["p4bzs"]),
    }

    labels = list(rates.keys())
    values = list(rates.values())
    colors = ["steelblue", "coral", "seagreen"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor="white", linewidth=1.2)

    # Baseline reference line (Phase 2)
    ax.axhline(values[0], color="steelblue", linestyle="--", linewidth=1.2, alpha=0.6)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.002,
                f"{val:.5f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Delta annotations for 4a and 4b
    for i, (bar, val) in enumerate(zip(bars[1:], values[1:]), 1):
        delta = val - values[0]
        pct   = delta / values[0] * 100
        sign  = "+" if delta >= 0 else ""
        color = "seagreen" if delta >= 0 else "crimson"
        ax.text(bar.get_x() + bar.get_width() / 2,
                val + 0.006,
                f"{sign}{pct:.1f}% vs Phase 2",
                ha="center", va="bottom", fontsize=8, color=color)

    ax.set_ylabel("Care events / alive-mother-tick\n(ticks 0–100, care window only)", fontsize=9)
    ax.set_title(
        "Zero-Shot Transfer: Care Rate in Care Window (ticks 0–100)\n"
        "Fair comparison — removes dormancy confound",
        fontsize=10,
    )
    ax.set_ylim(0, max(values) * 1.25)
    ax.grid(True, axis="y", alpha=0.3)

    # Legend explaining metric
    ax.annotate(
        "Metric: successful care events ÷ mother-ticks in ticks 0–100\n"
        "Removes dormancy confound (mothers alive with no children after maturation)",
        xy=(0.5, -0.22), xycoords="axes fraction",
        ha="center", fontsize=8, color="gray",
    )

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "zeroshot_comparison.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ═══════════════════════════════════════════════════════════════════════════
# Plot 4 — Phase comparison table
# ═══════════════════════════════════════════════════════════════════════════

def plot_phase_comparison_table():
    # Pre-computed metrics (from session logs + calculations above)
    # Rows: metric name | Phase 3 | Phase 4a | Phase 4b
    rows = [
        # Label                        Phase3        Phase4a       Phase4b
        ("care_weight (start)",         "0.500",      "0.506",      "0.501"),
        ("care_weight (final)",         "0.420",      "0.432",      "0.436"),
        ("care_weight (Δ)",             "−0.080",     "−0.068",     "−0.065"),
        ("care_weight trough",          "0.365 (end)","0.434",      "0.355 @ t2300"),
        ("care_weight recovery?",       "No",         "No",         "Yes → 0.436"),
        ("learning_rate (final)",       "0.100",      "0.141",      "0.170"),
        ("learning_rate (Δ)",           "—",          "+0.041",     "+0.066"),
        ("learning_rate trajectory",    "—",          "Noisy / drift","Late sweep (t3600+)"),
        ("forage_weight (Δ)",           "—",          "+0.078",     "+0.014"),
        ("Selection r (care vs gen)",   "−0.178",     "−0.2158",    "−0.1887"),
        ("Care events (5000 ticks)",    "1174",       "1887",       "1147"),
        ("Hamilton rB − C (own)",       "—",          "−0.0052",    "−0.0004"),
        ("Hamilton rB > C (%)",         "44.7%",      "31.0%",      "39.7%"),
        ("Own-lineage care rate",        "10.5%",      "9.8%",       "10.5%"),
        ("ZS window rate (ticks 0–100)","0.09069",    "0.07171",    "0.09933"),
        ("ZS improvement vs Phase 2",   "baseline",   "−21%",       "+9.5%"),
        ("ZS last alive tick",          "697",        "999",        "575"),
        ("Pop trough min (t2000–2600)", "12",         "—",          "11"),
    ]

    col_labels  = ["Metric", "Phase 3\n(no plasticity)", "Phase 4a\n(blind plasticity)", "Phase 4b\n(kin-conditional)"]
    n_rows = len(rows)
    n_cols = 4

    # Cell colours: highlight Phase 4b column for key rows
    highlight_rows = {0, 1, 2, 5, 6, 9, 14, 15}   # indices of key comparison rows
    cell_colours = []
    for i, row in enumerate(rows):
        c_row = ["white"] * n_cols
        if i in highlight_rows:
            c_row[3] = "#d4edda"  # light green for Phase 4b column
            c_row[2] = "#fde8e0"  # light coral for Phase 4a column
        cell_colours.append(c_row)

    fig, ax = plt.subplots(figsize=(14, n_rows * 0.42 + 1.5))
    ax.axis("off")

    table_data = [[r[0], r[1], r[2], r[3]] for r in rows]

    tbl = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
        cellColours=cell_colours,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
    tbl.scale(1, 1.35)

    # Style header row
    for j in range(n_cols):
        tbl[0, j].set_facecolor("#2c3e50")
        tbl[0, j].set_text_props(color="white", fontweight="bold")

    # Style metric column (col 0)
    for i in range(1, n_rows + 1):
        tbl[i, 0].set_facecolor("#f0f0f0")
        tbl[i, 0].set_text_props(ha="left", fontweight="normal")
        tbl[i, 0].PAD = 0.05

    ax.set_title(
        "Phase Comparison: Key Metrics Across Phase 3 and Phase 4 (seed=42)\n"
        "Green = Phase 4b best value | Coral = Phase 4a comparison",
        fontsize=10, pad=12,
    )

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "phase_comparison_table.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {out}")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"Generating thesis plots -> {OUT_DIR}/")
    plot_selection_gradient()
    plot_population_trough()
    plot_zeroshot_comparison()
    plot_phase_comparison_table()
    print("Done.")
