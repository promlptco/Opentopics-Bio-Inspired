# experiments/phase6_plasticity_test/plot_phase6_baldwin.py
"""Baldwin Effect comparison plot — mirrors the classic internet diagram.

Two curves on the same axes:
  Solid  — Fitness proxy      : avg_care_weight (genetic, heritable)
  Dashed — Phenotypic Plasticity : avg_expressed_care_weight - avg_care_weight
                                   (the plastic deviation; zero when assimilation is complete)

Both are min-max normalised across the run so they sit on the same [0, 1] scale,
matching the style of the canonical Baldwin-Effect diagram.
"""
import os
import sys
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

COMBINED_DIR  = os.path.join(PROJECT_ROOT, "outputs", "phase6_plasticity_test", "multi_seed")
RUN_DIRS_FILE = os.path.join(COMBINED_DIR, "run_dirs.json")

COL_FITNESS   = "#1a7a3f"   # dark green  — genetic fitness
COL_PLASTIC   = "#e07b00"   # orange      — phenotypic plasticity deviation


def _load():
    with open(RUN_DIRS_FILE) as f:
        manifest = json.load(f)
    seeds    = manifest["seeds"]
    run_dirs = manifest["run_dirs"]
    all_snaps = {}
    for seed in seeds:
        rd   = run_dirs.get(str(seed))
        path = os.path.join(rd, "generation_snapshots.json")
        if rd and os.path.exists(path):
            with open(path) as f:
                snaps = json.load(f)
            if snaps:
                all_snaps[seed] = snaps
    return seeds, all_snaps


def _common_ticks(all_snaps):
    tick_sets = [set(s["tick"] for s in snaps) for snaps in all_snaps.values()]
    return sorted(set.intersection(*tick_sets))


def _extract_matrix(all_snaps, ticks, key, default=0.0):
    idx = {t: i for i, t in enumerate(ticks)}
    rows = []
    for snaps in all_snaps.values():
        row = np.full(len(ticks), default)
        for s in snaps:
            if s["tick"] in idx:
                row[idx[s["tick"]]] = s.get(key, default)
        rows.append(row)
    return np.array(rows)


def _normalise(arr):
    lo, hi = arr.min(), arr.max()
    if hi == lo:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


def main():
    seeds, all_snaps = _load()
    ticks = _common_ticks(all_snaps)
    t     = np.array(ticks)
    n     = len(all_snaps)

    # avg_expressed_care_weight is now old-mothers-only (artifact-free).
    # avg_care_weight_old is the matching genetic baseline for the same old-mother subset.
    # Fall back to all-mothers avg_care_weight if old-mothers field not in data (old runs).
    ecw_mat = _extract_matrix(all_snaps, ticks, "avg_expressed_care_weight", 0.30)
    first_snap = next(iter(all_snaps.values()))[0]
    gcw_key  = "avg_care_weight_old" if "avg_care_weight_old" in first_snap else "avg_care_weight"
    gcw_mat  = _extract_matrix(all_snaps, ticks, gcw_key, 0.30)
    gap_mat  = ecw_mat - gcw_mat   # plastic deviation (expressed - genetic) per seed

    # Mean across seeds
    gcw_mean = gcw_mat.mean(0)
    gap_mean = gap_mat.mean(0)

    # Normalise for visual comparison
    gcw_norm = _normalise(gcw_mean)
    gap_norm = _normalise(np.clip(gap_mean, 0, None))   # clip negatives to 0

    # Per-seed normalised lines (faint, for band effect)
    gcw_norm_seeds = np.array([_normalise(row) for row in gcw_mat])
    gap_norm_seeds = np.array([_normalise(np.clip(row, 0, None)) for row in gap_mat])

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("seaborn-whitegrid")

    fig, ax = plt.subplots(figsize=(11, 5.5))

    # --- per-seed faint lines ---
    for row in gcw_norm_seeds:
        ax.plot(t, row, color=COL_FITNESS, alpha=0.10, linewidth=0.7, zorder=1)
    for row in gap_norm_seeds:
        ax.plot(t, row, color=COL_PLASTIC, alpha=0.10, linewidth=0.7,
                linestyle="--", zorder=1)

    # --- mean SD bands ---
    gcw_sd = gcw_norm_seeds.std(0)
    gap_sd = gap_norm_seeds.std(0)
    ax.fill_between(t, gcw_norm - gcw_sd, gcw_norm + gcw_sd,
                    color=COL_FITNESS, alpha=0.15, zorder=2)
    ax.fill_between(t, gap_norm - gap_sd, gap_norm + gap_sd,
                    color=COL_PLASTIC, alpha=0.15, zorder=2)

    # --- mean lines ---
    ax.plot(t, gcw_norm, color=COL_FITNESS, linewidth=2.5, zorder=3,
            label=f"Fitness  (genetic care_weight, normalised)   [{n} seeds]")
    ax.plot(t, gap_norm, color=COL_PLASTIC, linewidth=2.5, linestyle="--", zorder=3,
            label="Phenotypic Plasticity  (expressed - genetic, normalised)")

    # --- annotations ---
    ax.axhline(0, color="#aaa", linewidth=0.8, linestyle=":", zorder=0)

    # mark where gap peaks (max plasticity)
    peak_tick = t[np.argmax(gap_norm)]
    ax.axvline(peak_tick, color="#999", linewidth=1.0, linestyle="--", alpha=0.6)
    ax.annotate(
        f"Peak plasticity\n(tick {peak_tick})",
        xy=(peak_tick, gap_norm.max()),
        xytext=(peak_tick + 300, 0.75),
        fontsize=8.5, color=COL_PLASTIC,
        arrowprops=dict(arrowstyle="->", color=COL_PLASTIC, lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=COL_PLASTIC, alpha=0.85),
    )

    ax.set_xlabel("Simulation Tick", fontsize=12)
    ax.set_ylabel("Normalised Level  (0 = min, 1 = max)", fontsize=11)
    ax.set_ylim(-0.08, 1.12)
    ax.set_xlim(t[0], t[-1])
    ax.legend(loc="lower right", fontsize=9.5, framealpha=0.92, edgecolor="#ccc")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)

    fig.suptitle(
        "Phase 6 — Baldwin Effect Pattern\n"
        "Fitness rises; Phenotypic Plasticity peaks then declines as genetic assimilation proceeds",
        fontsize=11, fontweight="bold", y=1.01,
    )
    fig.tight_layout()

    out_path = os.path.join(COMBINED_DIR, "phase6_baldwin_comparison.png")
    fig.savefig(out_path, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")

    # --- print summary table ---
    print(f"\nBaldwin trajectory summary (mean across {n} seeds):")
    print(f"  {'Tick':>6}  {'genetic_cw':>10}  {'gap(expr-gen)':>14}  {'gap_norm':>9}")
    step = max(1, len(ticks) // 10)
    for i in range(0, len(ticks), step):
        print(f"  {t[i]:6.0f}  {gcw_mean[i]:.4f}      {gap_mean[i]:+.5f}        {gap_norm[i]:.4f}")


if __name__ == "__main__":
    main()
