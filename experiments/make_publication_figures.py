# experiments/make_publication_figures.py
"""
Generate publication-ready figures for the thesis Results section.

Figure 1 — Phase 3: Care Erosion
  Panel A: 10-seed care_weight trajectory, 95% CI, r=-0.178 annotation
  Panel B: birth_log scatter (care_weight vs generation) — selection proof

Figure 2 — Phase 4: Baldwin Effect & Zero-Shot Transfer
  Panel A: care_weight trajectory Phase 3 vs Phase 4b (kin-conditional)
  Panel B: zero-shot window rate per seed (Phase 4b vs Phase 2), p=0.815 annotation

Figure 3 — Phase 5: Ecological Emergence (Gradient Reversal)
  Panel A: 10-seed Phase 5a care_weight CI + Phase 5b control + Phase 3 overlay
  Panel B: per-seed selection gradient r (Phase 5 vs Phase 3 reference line)

Run from project root:
  python experiments/make_publication_figures.py

Outputs: outputs/publication_figures/
"""
import sys
import os
import csv
import json
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "publication_figures")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Canonical run directories ────────────────────────────────────────────────
P3_CANONICAL      = os.path.join(PROJECT_ROOT, "outputs", "phase3_erosion",    "run_20260409_232012_seed42")
P4B_CANONICAL     = os.path.join(PROJECT_ROOT, "outputs", "phase4_plasticity", "run_20260410_113356_seed42")
P3_MULTI_DIR      = os.path.join(PROJECT_ROOT, "outputs", "phase3_erosion",    "multi_seed_evolution")
P4B_MULTI_DIR     = os.path.join(PROJECT_ROOT, "outputs", "phase4_plasticity", "multi_seed_evolution")
P5_MULTI_DIR      = os.path.join(PROJECT_ROOT, "outputs", "phase5a_reversal",  "multi_seed_evolution")

PHASE3_ZS_BASELINE = 0.09069
MATURITY_AGE       = 100

# ── Academic rcParams (applied globally) ─────────────────────────────────────
_RC = {
    'font.size':         10,
    'axes.titlesize':    10,
    'axes.labelsize':    10,
    'xtick.labelsize':    9,
    'ytick.labelsize':    9,
    'legend.fontsize':    9,
    'legend.framealpha':  0.93,
    'legend.edgecolor':  '0.6',
    'legend.borderpad':   0.5,
    'legend.labelspacing': 0.4,
    'axes.spines.top':   False,
    'axes.spines.right': False,
    'axes.linewidth':     0.8,
    'grid.alpha':         0.22,
    'grid.linewidth':     0.5,
    'lines.linewidth':    2.0,
    'figure.facecolor':  'white',
    'axes.facecolor':    'white',
}
plt.rcParams.update(_RC)

# ── Consistent colour palette ────────────────────────────────────────────────
_C_P3  = "steelblue"
_C_P4B = "#2ca02c"       # seagreen-family, slightly richer
_C_P5A = "#2ca02c"
_C_P5B = "#d95f02"       # burnt orange
_C_ANN = "#444444"


# ── Data helpers ─────────────────────────────────────────────────────────────

def _load_json(path: str) -> dict | list:
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)

def _load_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))

def _snapshots(run_dir: str) -> list[dict]:
    return _load_json(os.path.join(run_dir, "generation_snapshots.json")) or []

def _mean(v: list) -> float:
    return sum(v) / len(v) if v else 0.0

def _ci95(v: list) -> float:
    n = len(v)
    if n < 2:
        return 0.0
    m = _mean(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    return 1.96 * sd / math.sqrt(n)

def _pearson_r(x: list, y: list) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mx, my = _mean(x), _mean(y)
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    dx  = math.sqrt(sum((v - mx) ** 2 for v in x))
    dy  = math.sqrt(sum((v - my) ** 2 for v in y))
    return num / (dx * dy) if dx > 0 and dy > 0 else 0.0

def _multi_seed_ci(run_dirs: list[str], key: str) -> tuple[list, list, list, list]:
    """Extract mean ± 95% CI over tick for a given snapshot key across seeds."""
    all_snaps = [_snapshots(d) for d in run_dirs if os.path.isdir(d)]
    all_snaps = [s for s in all_snaps if s]
    if not all_snaps:
        return [], [], [], []
    tick_sets    = [set(s["tick"] for s in snaps) for snaps in all_snaps]
    common_ticks = sorted(set.intersection(*tick_sets))
    by_seed = [
        [next(s.get(key, 0.0) for s in snaps if s["tick"] == t) for t in common_ticks]
        for snaps in all_snaps
    ]
    mean = [_mean([row[i] for row in by_seed]) for i in range(len(common_ticks))]
    ci   = [_ci95([row[i] for row in by_seed]) for i in range(len(common_ticks))]
    lo   = [m - c for m, c in zip(mean, ci)]
    hi   = [m + c for m, c in zip(mean, ci)]
    return common_ticks, mean, lo, hi

def _resolve_run_dirs(manifest_json: str) -> list[str]:
    data = _load_json(manifest_json)
    dirs = data.get("run_dirs", [])
    return [os.path.join(PROJECT_ROOT, d.replace("\\", os.sep)) for d in dirs]

def _resolve_run_dirs_dict(manifest_json: str, key: str) -> dict[str, str]:
    data = _load_json(manifest_json)
    raw  = data.get(key, {})
    return {k: os.path.join(PROJECT_ROOT, v.replace("\\", os.sep)) for k, v in raw.items()}


# ── Figure 1: Phase 3 Care Erosion ───────────────────────────────────────────

def figure1_phase3_erosion() -> None:
    print("Generating Figure 1 — Phase 3 Care Erosion...")

    p3_run_dirs = _resolve_run_dirs(os.path.join(P3_MULTI_DIR, "run_dirs.json"))

    # Panel A data
    ticks, mean, lo, hi = _multi_seed_ci(p3_run_dirs, "avg_care_weight")

    # Panel B data: birth_log scatter
    birth_rows = _load_csv(os.path.join(P3_CANONICAL, "birth_log.csv"))
    cw_vals  = [float(r["mother_care_weight"]) for r in birth_rows]
    gen_vals = [float(r["mother_generation"])  for r in birth_rows]
    r_val    = _pearson_r(gen_vals, cw_vals)

    # Regression line
    g_line = c_line = None
    if gen_vals:
        g_arr = np.array(gen_vals)
        c_arr = np.array(cw_vals)
        slope, intercept = np.polyfit(g_arr, c_arr, 1)
        g_line = np.linspace(g_arr.min(), g_arr.max(), 200)
        c_line = slope * g_line + intercept

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "Figure 1 — Phase 3: Evolutionary Erosion of Maternal Care",
        fontsize=11, y=1.01,
    )

    # ── Panel A ──────────────────────────────────────────────────────────────
    # Ghost traces (individual seeds, no legend entry)
    for d in p3_run_dirs:
        snaps = _snapshots(d)
        if snaps:
            ax1.plot([s["tick"] for s in snaps],
                     [s["avg_care_weight"] for s in snaps],
                     color=_C_P3, alpha=0.12, linewidth=0.9)

    if ticks:
        ax1.fill_between(ticks, lo, hi, alpha=0.22, color=_C_P3)
        ax1.plot(ticks, mean, color=_C_P3, linewidth=2.2,
                 label=f"Mean care_weight ± 95% CI  (n = {len(p3_run_dirs)} seeds)")

    ax1.axhline(0.500, color="gray",    linestyle="--", linewidth=1.0,
                label="Initial mean (0.500)", alpha=0.7)
    ax1.axhline(0.420, color="crimson", linestyle=":",  linewidth=1.2,
                label="Final mean (~0.420)")

    # Annotation — lower right (data never reaches below 0.35, right side is ~0.42)
    ax1.annotate(
        "Pearson's r = \u22120.178\n9/10 seeds decline",
        xy=(0.97, 0.07), xycoords="axes fraction",
        ha="right", va="bottom", fontsize=9, color=_C_ANN,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="lightyellow",
                  edgecolor="0.65", linewidth=0.8),
    )

    ax1.set_xlabel("Simulation tick  (\u2248 100 ticks per generation)")
    ax1.set_ylabel("Mean care_weight (genome parameter)")
    ax1.set_ylim(0.0, 0.75)
    ax1.set_title("(A)  Multi-seed care_weight trajectory  (seeds 42\u201351)")
    # Legend in lower left — data lives in 0.35–0.55 range, lower-left corner is clear
    ax1.legend(loc="lower left", frameon=True)
    ax1.grid(True)

    # ── Panel B ──────────────────────────────────────────────────────────────
    ax2.scatter(gen_vals, cw_vals, color=_C_P3, alpha=0.22, s=7, rasterized=True,
                label=f"Birth events  (n = {len(cw_vals)})")
    if g_line is not None:
        ax2.plot(g_line, c_line, color="crimson", linewidth=2.0,
                 label=f"OLS fit  Pearson\u2019s r = {r_val:+.3f}")

    ax2.set_xlabel("Mother generation at birth")
    ax2.set_ylabel("Mother care_weight at birth")
    ax2.set_title("(B)  Selection proof: care_weight vs. generation\n"
                  "(seed = 42 canonical run)")
    # Legend in upper right — regression line descends left→right, upper right is clear
    ax2.legend(loc="upper right", frameon=True)
    ax2.grid(True)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "figure1_phase3_erosion.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ── Figure 2: Phase 4 Baldwin Effect & Zero-Shot ─────────────────────────────

def figure2_phase4_plasticity() -> None:
    print("Generating Figure 2 — Phase 4 Baldwin Effect & Zero-Shot Transfer...")

    p3_snaps  = _snapshots(P3_CANONICAL)
    p4b_snaps = _snapshots(P4B_CANONICAL)

    zs_data  = _load_json(os.path.join(P4B_MULTI_DIR, "statistical_tests.json"))
    p_value  = zs_data.get("paired_ttest", {}).get("p_value", 0.8145)
    if isinstance(zs_data.get("paired_ttest"), dict):
        p_value = zs_data["paired_ttest"].get("p_value", 0.8145)
    per_seed = zs_data.get("per_seed", [])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "Figure 2 — Phase 4: Kin-Conditional Baldwin Effect",
        fontsize=11, y=1.01,
    )

    # ── Panel A ──────────────────────────────────────────────────────────────
    if p3_snaps:
        ax1.plot([s["tick"] for s in p3_snaps],
                 [s["avg_care_weight"] for s in p3_snaps],
                 color=_C_P3, linewidth=2.2, linestyle="-",
                 label="Phase 3 — no plasticity  (final 0.420)")

    if p4b_snaps:
        t4 = [s["tick"]            for s in p4b_snaps]
        c4 = [s["avg_care_weight"] for s in p4b_snaps]
        ax1.plot(t4, c4, color=_C_P4B, linewidth=2.2, linestyle="-",
                 label="Phase 4b — kin-conditional plasticity  (final 0.436)")

        trough_idx = c4.index(min(c4))
        # Trough annotation: point is in middle of plot; text placed lower-left to stay clear
        ax1.annotate(
            f"Trough: {min(c4):.3f}  (tick {t4[trough_idx]})",
            xy=(t4[trough_idx], min(c4)),
            xytext=(500, 0.28),
            arrowprops=dict(arrowstyle="->", color=_C_P4B, lw=1.0),
            fontsize=8.5, color=_C_P4B,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="0.65", linewidth=0.7),
        )
        # Recovery annotation: text placed well above data in upper-right area
        ax1.annotate(
            "Recovery — Baldwin Effect signature\n(lr sweep tick 3600+)",
            xy=(t4[-1], c4[-1]),
            xytext=(3200, 0.58),
            arrowprops=dict(arrowstyle="->", color=_C_P4B, lw=1.0),
            fontsize=8.5, color=_C_P4B,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="0.65", linewidth=0.7),
        )

    ax1.set_xlabel("Simulation tick  (\u2248 100 ticks per generation)")
    ax1.set_ylabel("Mean care_weight (genome parameter)")
    ax1.set_ylim(0.20, 0.68)
    ax1.set_title("(A)  care_weight trajectory: Phase 3 vs. Phase 4b  (seed = 42)")
    # Lower left: below 0.28 both trajectories are above — lower-left corner is empty
    ax1.legend(loc="lower left", frameon=True)
    ax1.grid(True)

    # ── Panel B ──────────────────────────────────────────────────────────────
    if per_seed:
        seeds   = sorted(s["seed"] for s in per_seed)
        by_seed = {s["seed"]: s for s in per_seed}
        p4b_rates = [by_seed[s]["p4b_rate"] for s in seeds]
        p2_rates  = [by_seed[s]["p2_rate"]  for s in seeds]
        bar_colors = ["#2ca02c" if by_seed[s]["diff"] > 0 else "#d62728" for s in seeds]

        x     = list(range(len(seeds)))
        width = 0.38
        ax2.bar([xi - width / 2 for xi in x], p2_rates, width,
                label="Phase 2 baseline (no plasticity)",
                color=_C_P3, alpha=0.80, edgecolor="white", linewidth=0.5)
        bars = ax2.bar([xi + width / 2 for xi in x], p4b_rates, width,
                       label="Phase 4b zero-shot (evolved + plastic genomes)",
                       color=bar_colors, alpha=0.88, edgecolor="white", linewidth=0.5)

        for bar, val in zip(bars, p4b_rates):
            ax2.text(bar.get_x() + bar.get_width() / 2,
                     val + 0.001, f"{val:.4f}",
                     ha="center", va="bottom", fontsize=6.5, color="0.3")

        ax2.set_xticks(x)
        ax2.set_xticklabels([f"s{s}" for s in seeds], fontsize=8)
        ax2.set_ylabel("Care events / alive-mother-tick  (ticks 0\u2013100)")
        ax2.set_title("(B)  Zero-shot window rate: Phase 4b vs. Phase 2\n"
                      "(green = above baseline; red = below)")

        y_top = max(max(p4b_rates), max(p2_rates)) * 1.45
        ax2.set_ylim(0, y_top)

        # p-value annotation — placed just inside upper centre, above bars
        ax2.annotate(
            f"Paired t-test:  p = {p_value:.4f}\n"
            "H\u2080 not rejected — no population-level assimilation",
            xy=(0.50, 0.96), xycoords="axes fraction",
            ha="center", va="top", fontsize=8.5, color=_C_ANN,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="lightyellow",
                      edgecolor="0.65", linewidth=0.8),
        )
        # Legend in lower right — bar heights are < 0.12, lower-right corner is clear
        ax2.legend(loc="lower right", frameon=True)
        ax2.grid(True, axis="y")
    else:
        ax2.text(0.5, 0.5, "per_seed data not found\n(re-run phase4 multi-seed)",
                 ha="center", va="center", transform=ax2.transAxes, fontsize=10)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "figure2_phase4_plasticity.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ── Figure 3: Phase 5 Ecological Emergence ───────────────────────────────────

def figure3_phase5_reversal() -> None:
    print("Generating Figure 3 — Phase 5 Ecological Emergence (Gradient Reversal)...")

    p5_manifest  = os.path.join(P5_MULTI_DIR, "run_dirs.json")
    p5_evo_dirs  = list(_resolve_run_dirs_dict(p5_manifest, "evo_run_dirs").values())
    p5_ctrl_dirs = list(_resolve_run_dirs_dict(p5_manifest, "ctrl_run_dirs").values())
    p3_run_dirs  = _resolve_run_dirs(os.path.join(P3_MULTI_DIR, "run_dirs.json"))

    t5, m5, lo5, hi5 = _multi_seed_ci(p5_evo_dirs,  "avg_care_weight")
    tc, mc, loc, hic = _multi_seed_ci(p5_ctrl_dirs, "avg_care_weight")
    t3, m3, lo3, hi3 = _multi_seed_ci(p3_run_dirs,  "avg_care_weight")

    summary  = _load_json(os.path.join(P5_MULTI_DIR, "summary.json")) or []
    seeds_g  = [s["seed"]             for s in summary if s.get("selection_grad_r") is not None]
    grads_g  = [s["selection_grad_r"] for s in summary if s.get("selection_grad_r") is not None]
    stats    = _load_json(os.path.join(P5_MULTI_DIR, "statistical_tests.json"))
    grt      = stats.get("gradient_reversal_test", {})
    mean_r   = grt.get("mean_r", 0.0)
    p_val    = grt.get("ttest_vs_zero", {}).get("p_value", 0.0)
    cohens_d = grt.get("cohens_d", 0.0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "Figure 3 — Phase 5: Ecological Emergence of Maternal Care  (Gradient Reversal)",
        fontsize=11, y=1.01,
    )

    # ── Panel A ──────────────────────────────────────────────────────────────
    # Ghost traces — Phase 5a individual seeds (no legend entry)
    for d in p5_evo_dirs:
        snaps = _snapshots(d)
        if snaps:
            ax1.plot([s["tick"] for s in snaps],
                     [s["avg_care_weight"] for s in snaps],
                     color=_C_P5A, alpha=0.10, linewidth=0.9)

    if t5:
        ax1.fill_between(t5, lo5, hi5, alpha=0.20, color=_C_P5A)
        ax1.plot(t5, m5, color=_C_P5A, linewidth=2.2,
                 label=f"Phase 5a — natal philopatry, scatter=2  "
                       f"(mean ± 95% CI, n = {len(p5_evo_dirs)})")
    if tc:
        ax1.fill_between(tc, loc, hic, alpha=0.10, color=_C_P5B)
        ax1.plot(tc, mc, color=_C_P5B, linewidth=1.8, linestyle="--",
                 label="Phase 5b — dispersal control, scatter=8")
    if t3:
        ax1.plot(t3, m3, color=_C_P3, linewidth=1.5, linestyle=":",
                 label="Phase 3 — standard ecology (reference)", zorder=4)

    ax1.axhline(0.25,  color="gray",    linestyle="--", linewidth=0.9, alpha=0.65,
                label="Phase 5 init mean (0.25)")
    ax1.axhline(0.420, color="crimson", linestyle=":",  linewidth=1.1,
                label="Phase 3 final (0.420)")

    # Annotation — lower right, well below all trajectories after tick ~1000
    ax1.annotate(
        f"Pearson\u2019s r = +{mean_r:.4f}  (Phase 3: \u22120.178)\n"
        f"p = {p_val:.4f},  Cohen\u2019s d = {cohens_d:.2f}",
        xy=(0.97, 0.06), xycoords="axes fraction",
        ha="right", va="bottom", fontsize=9, color=_C_ANN,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="lightyellow",
                  edgecolor="0.65", linewidth=0.8),
    )

    ax1.set_xlabel("Simulation tick  (\u2248 100 ticks per generation)")
    ax1.set_ylabel("Mean care_weight (genome parameter)")
    ax1.set_ylim(0.0, 0.75)
    ax1.set_title("(A)  care_weight trajectory: Phase 5a vs. 5b vs. Phase 3")

    # Legend in upper right — Phase 5 lines start at 0.25 and rise to ~0.35;
    # Phase 3 lines start at 0.50 and fall to ~0.42; upper right (above 0.50 after
    # early ticks) is clear of all trajectories.
    ax1.legend(loc="upper right", frameon=True, fontsize=8.5)
    ax1.grid(True)

    # ── Panel B ──────────────────────────────────────────────────────────────
    bar_colors = [_C_P5A if g > 0 else "#d62728" for g in grads_g]
    ax2.bar(range(len(seeds_g)), grads_g,
            color=bar_colors, edgecolor="white", linewidth=0.5, alpha=0.88)

    ax2.axhline(0.0,    color="black",   linewidth=1.2, linestyle="-",
                label="Zero (no net selection)")
    ax2.axhline(-0.178, color=_C_P3,    linewidth=1.5, linestyle="--",
                label="Phase 3 reference  (r = \u22120.178)")
    ax2.axhline(mean_r, color=_C_P5A,   linewidth=1.5, linestyle="-.",
                label=f"Phase 5a mean  (r = +{mean_r:.4f})")

    ax2.set_xticks(range(len(seeds_g)))
    ax2.set_xticklabels([f"s{s}" for s in seeds_g], fontsize=8)
    ax2.set_ylabel("Pearson\u2019s r  (care_weight vs. generation at birth)")
    ax2.set_title(
        f"(B)  Per-seed selection gradient \u2014 Phase 5a\n"
        f"Green = positive (care builds)  |  "
        f"{sum(g > 0 for g in grads_g)}/{len(grads_g)} seeds positive"
    )

    y_lo = min(min(grads_g) * 1.4 - 0.03, -0.21)
    y_hi = max(grads_g) * 1.5
    ax2.set_ylim(y_lo, y_hi)

    # Legend in upper right — bars do not reach above ~0.12; reference line at -0.178
    # sits below most positive bars. Upper right (above 0.13) is clear.
    ax2.legend(loc="upper right", frameon=True)
    ax2.grid(True, axis="y")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "figure3_phase5_reversal.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Output directory: {OUT_DIR}\n")
    figure1_phase3_erosion()
    figure2_phase4_plasticity()
    figure3_phase5_reversal()
    print("\nAll publication figures generated.")
