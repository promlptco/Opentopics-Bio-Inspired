"""Phase 3 perception sweep comparison plots.

Loads spatial heatmap data across perception levels [8, 15, 25, 50] and
produces side-by-side comparison panels showing CMR and care_pct per condition.

Usage:
  python -m experiments.phase3_food_comparison.percept_comparison_plot
  python -m experiments.phase3_food_comparison.percept_comparison_plot --sweep-dir outputs/phase3_percept_sweep
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

ALPHA_LABELS = ["F0", "F1", "F2", "F3"]
ALPHA_VALUES = [0.00, 0.01, 0.05, 0.10]
PERCEPT_DIRS = {
    8:  "percept08",
    15: "percept15",
    25: "percept25",
    50: "percept50",
}
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]


def _load_results(sweep_dir: Path, percept: int, label: str) -> list[dict]:
    """Try to load validation_<label>.png-associated data from heatmap CSVs.
    Fallback: parse the log file for printed CMR values.
    """
    # Each run subdir has percept_XX/label/*.png and the log file
    percept_dir = sweep_dir / PERCEPT_DIRS[percept]
    log_file = sweep_dir / ("%s.log" % PERCEPT_DIRS[percept])
    results = []
    if not log_file.exists():
        return results
    # Parse log for "seed=XX  final_pop=XX  cmr=XX  care_pct=XX" lines
    import re
    pattern = re.compile(
        r"seed=(\d+)\s+final_pop=(\d+)\s+cmr=([\d.]+)\s+care_pct=([\d.]+)"
    )
    in_label_block = False
    with open(log_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            if ("[%s]" % label) in line:
                in_label_block = True
                results = []  # reset for this block
            elif in_label_block and line.startswith("  ["):
                # New block started
                break
            elif in_label_block:
                m = pattern.search(line)
                if m:
                    results.append({
                        "seed": int(m.group(1)),
                        "final_pop": int(m.group(2)),
                        "cmr": float(m.group(3)),
                        "care_pct": float(m.group(4)),
                    })
    return results


def plot_comparison(sweep_dir: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    percept_list = [p for p in PERCEPT_DIRS if (sweep_dir / PERCEPT_DIRS[p]).exists()]

    # --- CMR bar chart: one group per alpha level, one bar per perception ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Phase 3 Perception Sweep (alpha=0.10, prior=0.37)\n"
                 "Effect of perception_radius on Child Maturation Rate",
                 fontsize=12, fontweight="bold")

    width = 0.18
    x = np.arange(len(ALPHA_LABELS))
    colors = plt.cm.plasma(np.linspace(0.2, 0.85, len(percept_list)))

    for ax_idx, (metric, ylabel, title) in enumerate([
        ("cmr", "Child Maturation Rate (CMR)", "CMR by Alpha Level"),
        ("care_pct", "Fraction of ticks as CARE", "Care% by Alpha Level"),
    ]):
        ax = axes[ax_idx]
        for p_idx, percept in enumerate(sorted(percept_list)):
            means = []
            sems = []
            for label in ALPHA_LABELS:
                recs = _load_results(sweep_dir, percept, label)
                vals = [r[metric] for r in recs] if recs else [0.0]
                means.append(float(np.mean(vals)))
                sems.append(float(np.std(vals) / max(1, len(vals) ** 0.5)))
            offset = (p_idx - len(percept_list) / 2.0 + 0.5) * width
            bars = ax.bar(x + offset, means, width, label="percept=%d" % percept,
                          color=colors[p_idx], alpha=0.85)
            ax.errorbar(x + offset, means, yerr=sems, fmt="none",
                        color="black", linewidth=1, capsize=3)

        ax.set_xticks(x)
        ax.set_xticklabels(["F%d\nalpha=%.2f" % (i, v) for i, v in enumerate(ALPHA_VALUES)])
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.set_ylim(0, 1.1)
        ax.axhline(1.0, color="red", linestyle="--", linewidth=0.8, alpha=0.5, label="ceiling")
        ax.legend(fontsize=8)
        ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    fname = out / "perception_cmr_comparison.png"
    fig.savefig(str(fname), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved -> %s" % fname)

    # --- Line plot: CMR vs perception for each alpha ---
    fig2, axes2 = plt.subplots(1, 2, figsize=(12, 5))
    fig2.suptitle("Phase 3 Perception Sweep — CMR vs perception_radius",
                  fontsize=12, fontweight="bold")
    percept_sorted = sorted(percept_list)

    for ax_idx, (metric, ylabel, title) in enumerate([
        ("cmr", "CMR", "CMR vs perception_radius"),
        ("care_pct", "Care fraction", "Care% vs perception_radius"),
    ]):
        ax = axes2[ax_idx]
        for a_idx, (label, alpha) in enumerate(zip(ALPHA_LABELS, ALPHA_VALUES)):
            means = []
            sems = []
            for percept in percept_sorted:
                recs = _load_results(sweep_dir, percept, label)
                vals = [r[metric] for r in recs] if recs else [0.0]
                means.append(float(np.mean(vals)))
                sems.append(float(np.std(vals) / max(1, len(vals) ** 0.5)))
            ax.plot(percept_sorted, means, "o-", color=COLORS[a_idx],
                    linewidth=2, markersize=7, label="%s (alpha=%.2f)" % (label, alpha))
            ax.fill_between(percept_sorted,
                            [m - s for m, s in zip(means, sems)],
                            [m + s for m, s in zip(means, sems)],
                            color=COLORS[a_idx], alpha=0.15)

        ax.set_xlabel("perception_radius")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.set_ylim(0, 1.1)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(percept_sorted)

    plt.tight_layout()
    fname2 = out / "perception_line_comparison.png"
    fig2.savefig(str(fname2), dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print("Saved -> %s" % fname2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 perception sweep comparison plot")
    parser.add_argument("--sweep-dir", type=str,
                        default="outputs/phase3_percept_sweep")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    sweep_dir = PROJECT_ROOT / args.sweep_dir
    out = Path(args.output_dir) if args.output_dir else sweep_dir
    plot_comparison(sweep_dir, out)
    print("[ok] Perception comparison plots saved to %s" % out)


if __name__ == "__main__":
    main()
