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
import matplotlib.patches as mpatches
import numpy as np

OUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "publication_figures")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Canonical run directories ────────────────────────────────────────────────
P3_CANONICAL      = os.path.join(PROJECT_ROOT, "outputs", "phase3_erosion", "run_20260409_232012_seed42")
P4B_CANONICAL     = os.path.join(PROJECT_ROOT, "outputs", "phase4_plasticity", "run_20260410_113356_seed42")
P3_MULTI_DIR      = os.path.join(PROJECT_ROOT, "outputs", "phase3_erosion",   "multi_seed_evolution")
P4B_MULTI_DIR     = os.path.join(PROJECT_ROOT, "outputs", "phase4_plasticity", "multi_seed_evolution")
P5_MULTI_DIR      = os.path.join(PROJECT_ROOT, "outputs", "phase5a_reversal",  "multi_seed_evolution")

PHASE3_ZS_BASELINE = 0.09069   # Phase 2 / Phase 3 zero-shot window rate
MATURITY_AGE       = 100


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
    """Load run_dirs list from a multi-seed manifest JSON."""
    data = _load_json(manifest_json)
    dirs = data.get("run_dirs", [])
    return [os.path.join(PROJECT_ROOT, d.replace("\\", os.sep)) for d in dirs]

def _resolve_run_dirs_dict(manifest_json: str, key: str) -> dict[str, str]:
    """Load evo/ctrl/zs run_dirs dict keyed by seed string."""
    data = _load_json(manifest_json)
    raw  = data.get(key, {})
    return {k: os.path.join(PROJECT_ROOT, v.replace("\\", os.sep)) for k, v in raw.items()}


# ── Figure 1: Phase 3 Care Erosion ───────────────────────────────────────────

def figure1_phase3_erosion() -> None:
    print("Generating Figure 1 — Phase 3 Care Erosion...")

    p3_run_dirs = _resolve_run_dirs(os.path.join(P3_MULTI_DIR, "run_dirs.json"))

    # Panel A: multi-seed CI trajectory
    ticks, mean, lo, hi = _multi_seed_ci(p3_run_dirs, "avg_care_weight")

    # Panel B: birth_log scatter (care_weight vs generation) from canonical run
    birth_rows = _load_csv(os.path.join(P3_CANONICAL, "birth_log.csv"))
    cw_vals  = [float(r["mother_care_weight"]) for r in birth_rows]
    gen_vals = [float(r["mother_generation"])  for r in birth_rows]
    r_val    = _pearson_r(gen_vals, cw_vals)

    # Regression line
    if gen_vals:
        g_arr = np.array(gen_vals)
        c_arr = np.array(cw_vals)
        slope, intercept = np.polyfit(g_arr, c_arr, 1)
        g_line = np.linspace(g_arr.min(), g_arr.max(), 100)
        c_line = slope * g_line + intercept

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "Figure 1 — Phase 3: Evolutionary Erosion of Maternal Care\n"
        "Selection against care when infant B is marginal and effective r ≈ 0",
        fontsize=11,
    )

    # ── Panel A ──────────────────────────────────────────────────────────────
    # Per-seed traces
    for d in p3_run_dirs:
        snaps = _snapshots(d)
        if snaps:
            t_i = [s["tick"]            for s in snaps]
            c_i = [s["avg_care_weight"] for s in snaps]
            ax1.plot(t_i, c_i, color="steelblue", alpha=0.15, linewidth=1)

    if ticks:
        ax1.plot(ticks, mean, color="steelblue", linewidth=2.5,
                 label=f"Mean care_weight (n={len(p3_run_dirs)} seeds)")
        ax1.fill_between(ticks, lo, hi, alpha=0.25, color="steelblue",
                         label="95% CI")
    ax1.axhline(0.500, color="gray",   linestyle="--", linewidth=1.0, alpha=0.7,
                label="Init mean (0.500)")
    ax1.axhline(0.420, color="crimson", linestyle=":",  linewidth=1.2,
                label="Final mean (~0.420)")
    ax1.annotate(
        "Selection gradient r = -0.178\n(9/10 seeds decline)",
        xy=(0.97, 0.55), xycoords="axes fraction",
        ha="right", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="lightyellow", edgecolor="gray"),
    )
    ax1.set_xlabel("Tick  (≈ 100 ticks per generation)")
    ax1.set_ylabel("Mean care_weight (genome)")
    ax1.set_ylim(0.0, 0.75)
    ax1.set_title("(A)  Multi-Seed care_weight Trajectory (seeds 42–51)")
    ax1.legend(loc="lower left", fontsize=8)
    ax1.grid(True, alpha=0.2)

    # ── Panel B ──────────────────────────────────────────────────────────────
    ax2.scatter(gen_vals, cw_vals, color="steelblue", alpha=0.25, s=8,
                label=f"Birth events (n={len(cw_vals)})")
    if gen_vals:
        ax2.plot(g_line, c_line, color="crimson", linewidth=2.0,
                 label=f"Regression  r = {r_val:+.3f}")
    ax2.set_xlabel("Mother generation at birth")
    ax2.set_ylabel("Mother care_weight at birth")
    ax2.set_title("(B)  Selection Proof: care_weight vs Generation\n(seed=42 canonical run)")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.2)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "figure1_phase3_erosion.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Figure 2: Phase 4 Baldwin Effect & Zero-Shot ─────────────────────────────

def figure2_phase4_plasticity() -> None:
    print("Generating Figure 2 — Phase 4 Baldwin Effect & Zero-Shot Transfer...")

    # Panel A: Phase 3 vs Phase 4b single-seed trajectories (generation snapshots)
    p3_snaps  = _snapshots(P3_CANONICAL)
    p4b_snaps = _snapshots(P4B_CANONICAL)

    # Panel B: zero-shot multi-seed bar chart from Phase 4b stats
    zs_data   = _load_json(os.path.join(P4B_MULTI_DIR, "statistical_tests.json"))
    p_value   = zs_data.get("paired_ttest", {}).get("p_value",
                zs_data.get("paired_ttest", {}).get("p_value", 0.8145))
    # handle nested structure
    if isinstance(zs_data.get("paired_ttest"), dict):
        p_value = zs_data["paired_ttest"].get("p_value", 0.8145)
    per_seed  = zs_data.get("per_seed", [])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "Figure 2 — Phase 4: Kin-Conditional Baldwin Effect\n"
        "Plasticity slows care erosion but does not achieve genetic assimilation at population scale",
        fontsize=11,
    )

    # ── Panel A ──────────────────────────────────────────────────────────────
    if p3_snaps:
        t3 = [s["tick"]            for s in p3_snaps]
        c3 = [s["avg_care_weight"] for s in p3_snaps]
        ax1.plot(t3, c3, color="steelblue", linewidth=2.5, linestyle="-",
                 label="Phase 3 — no plasticity  (final 0.420)")

    if p4b_snaps:
        t4 = [s["tick"]            for s in p4b_snaps]
        c4 = [s["avg_care_weight"] for s in p4b_snaps]
        ax1.plot(t4, c4, color="seagreen", linewidth=2.5, linestyle="-",
                 label="Phase 4b — kin-conditional plasticity  (final 0.436)")

        # Annotate care_weight trough and recovery
        trough_idx = c4.index(min(c4))
        ax1.annotate(
            f"Trough: {min(c4):.3f}\n@ tick {t4[trough_idx]}",
            xy=(t4[trough_idx], min(c4)),
            xytext=(t4[trough_idx] + 200, min(c4) + 0.05),
            arrowprops=dict(arrowstyle="->", color="seagreen"),
            fontsize=8, color="seagreen",
        )
        ax1.annotate(
            "Recovery (Baldwin signature)\nlr sweep tick 3600+",
            xy=(t4[-1], c4[-1]),
            xytext=(t4[-1] - 900, c4[-1] + 0.06),
            arrowprops=dict(arrowstyle="->", color="seagreen"),
            fontsize=8, color="seagreen",
        )

    ax1.set_xlabel("Tick  (≈ 100 ticks per generation)")
    ax1.set_ylabel("Mean care_weight (genome)")
    ax1.set_ylim(0.20, 0.65)
    ax1.set_title("(A)  care_weight Trajectory: Phase 3 vs Phase 4b (seed=42)")
    ax1.legend(fontsize=9, loc="lower left")
    ax1.grid(True, alpha=0.2)

    # ── Panel B ──────────────────────────────────────────────────────────────
    if per_seed:
        seeds   = sorted(s["seed"] for s in per_seed)
        by_seed = {s["seed"]: s for s in per_seed}
        p4b_rates = [by_seed[s]["p4b_rate"] for s in seeds]
        p2_rates  = [by_seed[s]["p2_rate"]  for s in seeds]
        colors    = ["seagreen" if by_seed[s]["diff"] > 0 else "coral" for s in seeds]

        x     = list(range(len(seeds)))
        width = 0.38
        ax2.bar([xi - width / 2 for xi in x], p2_rates,  width,
                label="Phase 2 baseline (no plasticity)",
                color="steelblue", alpha=0.8, edgecolor="white")
        bars = ax2.bar([xi + width / 2 for xi in x], p4b_rates, width,
                       label="Phase 4b zero-shot (evolved+plastic genomes)",
                       color=colors, alpha=0.9, edgecolor="white")
        for bar, val in zip(bars, p4b_rates):
            ax2.text(bar.get_x() + bar.get_width() / 2, val + 0.001,
                     f"{val:.4f}", ha="center", va="bottom", fontsize=6.5)

        ax2.set_xticks(x)
        ax2.set_xticklabels([f"s{s}" for s in seeds], fontsize=8)
        ax2.set_ylabel("Care / mother-tick (ticks 0–100)")
        ax2.set_title("(B)  Zero-Shot Window Rate: Phase 4b vs Phase 2 Baseline\n"
                      "(Green = above baseline; Coral = below)")
        ax2.annotate(
            f"Paired t-test: p = {p_value:.4f}\n(H0 not rejected — no assimilation at pop. scale)",
            xy=(0.5, 0.92), xycoords="axes fraction", ha="center", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="lightyellow", edgecolor="gray"),
        )
        ax2.legend(fontsize=8, loc="lower right")
        ax2.set_ylim(0, max(max(p4b_rates), max(p2_rates)) * 1.45)
        ax2.grid(True, axis="y", alpha=0.3)
    else:
        ax2.text(0.5, 0.5, "per_seed data not found\n(re-run phase4 multi-seed)",
                 ha="center", va="center", transform=ax2.transAxes, fontsize=10)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "figure2_phase4_plasticity.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Figure 3: Phase 5 Ecological Emergence ───────────────────────────────────

def figure3_phase5_reversal() -> None:
    print("Generating Figure 3 — Phase 5 Ecological Emergence (Gradient Reversal)...")

    p5_manifest = os.path.join(P5_MULTI_DIR, "run_dirs.json")
    p5_data     = _load_json(p5_manifest)
    p5_evo_dirs  = list(_resolve_run_dirs_dict(p5_manifest, "evo_run_dirs").values())
    p5_ctrl_dirs = list(_resolve_run_dirs_dict(p5_manifest, "ctrl_run_dirs").values())

    # Phase 3 multi-seed overlay
    p3_run_dirs = _resolve_run_dirs(os.path.join(P3_MULTI_DIR, "run_dirs.json"))

    # CI trajectories
    t5, m5, lo5, hi5 = _multi_seed_ci(p5_evo_dirs,  "avg_care_weight")
    tc, mc, loc, hic = _multi_seed_ci(p5_ctrl_dirs, "avg_care_weight")
    t3, m3, lo3, hi3 = _multi_seed_ci(p3_run_dirs,  "avg_care_weight")

    # Panel B: per-seed gradient r values
    summary = _load_json(os.path.join(P5_MULTI_DIR, "summary.json")) or []
    seeds_g  = [s["seed"]             for s in summary if s.get("selection_grad_r") is not None]
    grads_g  = [s["selection_grad_r"] for s in summary if s.get("selection_grad_r") is not None]
    stats    = _load_json(os.path.join(P5_MULTI_DIR, "statistical_tests.json"))
    grt      = stats.get("gradient_reversal_test", {})
    mean_r   = grt.get("mean_r", 0.0)
    p_val    = grt.get("ttest_vs_zero", {}).get("p_value", 0.0)
    cohens_d = grt.get("cohens_d", 0.0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "Figure 3 — Phase 5: Ecological Emergence of Maternal Care\n"
        "Gradient REVERSAL: existential infant dependency + natal philopatry (scatter=2) vs. dispersal control (scatter=8)",
        fontsize=11,
    )

    # ── Panel A ──────────────────────────────────────────────────────────────
    for d in p5_evo_dirs:
        snaps = _snapshots(d)
        if snaps:
            ax1.plot([s["tick"] for s in snaps],
                     [s["avg_care_weight"] for s in snaps],
                     color="seagreen", alpha=0.12, linewidth=1)

    if t5:
        ax1.plot(t5, m5, color="seagreen", linewidth=2.5,
                 label=f"Phase 5a — natal philopatry (scatter=2, n={len(p5_evo_dirs)})")
        ax1.fill_between(t5, lo5, hi5, alpha=0.25, color="seagreen", label="Phase 5a 95% CI")
    if tc:
        ax1.plot(tc, mc, color="darkorange", linewidth=1.8, linestyle="--",
                 label="Phase 5b — dispersal control (scatter=8)")
        ax1.fill_between(tc, loc, hic, alpha=0.12, color="darkorange")
    if t3:
        ax1.plot(t3, m3, color="steelblue", linewidth=1.5, linestyle=":",
                 label="Phase 3 — no ecology (reference)", zorder=4)

    ax1.axhline(0.25,  color="gray",   linestyle="--", linewidth=0.9, alpha=0.6,
                label="Phase 5 init mean (0.25)")
    ax1.axhline(0.420, color="crimson", linestyle=":",  linewidth=1.1,
                label="Phase 3 final (0.420)")

    ax1.annotate(
        f"Phase 5a gradient r = +{mean_r:.4f}\n"
        f"p = {p_val:.4f}, d = {cohens_d:.2f}\n"
        f"(Phase 3 reference: -0.178)",
        xy=(0.03, 0.65), xycoords="axes fraction", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="lightyellow", edgecolor="gray"),
    )
    ax1.set_xlabel("Tick  (≈ 100 ticks per generation)")
    ax1.set_ylabel("Mean care_weight (genome)")
    ax1.set_ylim(0.0, 0.75)
    ax1.set_title("(A)  care_weight Trajectory: Phase 5a vs 5b vs Phase 3")
    ax1.legend(loc="upper left", fontsize=8, ncol=1)
    ax1.grid(True, alpha=0.2)

    # ── Panel B ──────────────────────────────────────────────────────────────
    colors_b = ["seagreen" if g > 0 else "coral" for g in grads_g]
    ax2.bar(range(len(seeds_g)), grads_g, color=colors_b, edgecolor="white", alpha=0.85)
    ax2.axhline(0.0,    color="black",   linewidth=1.2, linestyle="-",
                label="Zero (no selection)")
    ax2.axhline(-0.178, color="steelblue", linewidth=1.5, linestyle="--",
                label="Phase 3 reference (r = -0.178)")
    ax2.axhline(mean_r, color="seagreen", linewidth=1.5, linestyle="-.",
                label=f"Phase 5a mean (r = +{mean_r:.4f})")
    ax2.set_xticks(range(len(seeds_g)))
    ax2.set_xticklabels([f"s{s}" for s in seeds_g], fontsize=8)
    ax2.set_ylabel("Selection gradient r  (birth_log: care_weight vs generation)")
    ax2.set_title(
        f"(B)  Per-Seed Selection Gradient — Phase 5a\n"
        f"Green = positive (care builds) | {sum(g > 0 for g in grads_g)}/{len(grads_g)} seeds positive"
    )
    ax2.legend(fontsize=8, loc="lower right")
    ax2.grid(True, axis="y", alpha=0.3)
    ax2.set_ylim(min(min(grads_g) * 1.4 - 0.03, -0.21), max(grads_g) * 1.5)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "figure3_phase5_reversal.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Output directory: {OUT_DIR}\n")
    figure1_phase3_erosion()
    figure2_phase4_plasticity()
    figure3_phase5_reversal()
    print("\nAll publication figures generated.")
