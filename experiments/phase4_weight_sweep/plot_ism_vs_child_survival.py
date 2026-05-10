# experiments/phase4_weight_sweep/plot_ism_vs_child_survival.py
"""
Plot ISM vs child maturation rate (child survival) across the three Phase 4 sweeps.

Reads:
  outputs/phase4_weight_sweep/sweep_ism1/sweep_summary.csv      (ISM=1.0)
  outputs/phase4_weight_sweep/sweep_ism1p2/sweep_summary.csv    (ISM=1.2)
  outputs/phase4_weight_sweep/sweep_ism2p33/sweep_summary.csv   (ISM=2.33)

Outputs:
  outputs/phase4_weight_sweep/ism_vs_child_survival.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
OUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase4_weight_sweep")

ISM_SWEEPS = [
    (1.0,  "sweep_ism1"),
    (1.2,  "sweep_ism1p2"),
    (2.33, "sweep_ism2p33"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────────────────────────
records = []
for ism, folder in ISM_SWEEPS:
    path = os.path.join(OUT_DIR, folder, "sweep_summary.csv")
    df = pd.read_csv(path)
    df["ism"] = ism
    records.append(df)

data = pd.concat(records, ignore_index=True)

# Per-ISM aggregates across all weight combos
agg = (
    data.groupby("ism")["c_matr_mean"]
    .agg(max_c_matr="max", mean_c_matr="mean", median_c_matr="median")
    .reset_index()
)

# Best weight combo per ISM (highest c_matr_mean)
best_rows = data.loc[data.groupby("ism")["c_matr_mean"].idxmax()].copy()

# ─────────────────────────────────────────────────────────────────────────────
# Figure — two panels
# ─────────────────────────────────────────────────────────────────────────────
ISM_VALS   = [1.0, 1.2, 2.33]
ISM_LABELS = ["ISM=1.0", "ISM=1.2", "ISM=2.33"]
x          = np.array(ISM_VALS)
x_ticks    = x
COLORS     = {"max": "#2196F3", "mean": "#FF9800", "box": "#90CAF9"}

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle(
    "Phase 4 — Infant Starvation Multiplier vs Child Maturation Rate",
    fontsize=13, fontweight="bold", y=1.01
)

# ── Panel A: line plot (max & mean) ──────────────────────────────────────────
ax = axes[0]

max_vals  = agg.set_index("ism").loc[x, "max_c_matr"].values
mean_vals = agg.set_index("ism").loc[x, "mean_c_matr"].values

ax.plot(x, max_vals,  "o-", color=COLORS["max"],  lw=2.2, ms=8,
        label="Best combo (max C_matr)")
ax.plot(x, mean_vals, "s--", color=COLORS["mean"], lw=1.8, ms=7,
        label="Mean across all combos")

# Annotate best combo labels
for ism, row in best_rows.set_index("ism").iterrows():
    label = f"cw={row['care_weight']:.1f}\nfw={row['forage_weight']:.1f}"
    ax.annotate(
        label,
        xy=(ism, row["c_matr_mean"]),
        xytext=(8, 6), textcoords="offset points",
        fontsize=7.5, color=COLORS["max"],
    )

ax.set_xticks(x)
ax.set_xticklabels(ISM_LABELS)
ax.set_xlabel("Infant Starvation Multiplier (ISM)", fontsize=11)
ax.set_ylabel("Child Maturation Rate (C_matr)", fontsize=11)
ax.set_title("(A) Best & Mean Child Survival vs ISM", fontsize=11)
ax.set_ylim(-0.02, max(max_vals) * 1.25)
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.35)
ax.axhline(0.10, color="gray", lw=1, ls=":", label="Viability threshold (0.10)")
ax.legend(fontsize=9)

# ── Panel B: box plot — full distribution per ISM ────────────────────────────
ax = axes[1]

box_data = [
    data.loc[data["ism"] == ism, "c_matr_mean"].values
    for ism in ISM_VALS
]

bp = ax.boxplot(
    box_data,
    tick_labels=ISM_LABELS,
    patch_artist=True,
    medianprops=dict(color="#E91E63", lw=2),
    boxprops=dict(facecolor=COLORS["box"], alpha=0.8),
    whiskerprops=dict(color="#555"),
    capprops=dict(color="#555"),
    flierprops=dict(marker="o", color="#888", ms=5, alpha=0.7),
)

# Overlay individual points
for i, (ism, vals) in enumerate(zip(ISM_VALS, box_data), start=1):
    jitter = np.random.default_rng(42).uniform(-0.08, 0.08, len(vals))
    ax.scatter(
        np.full(len(vals), i) + jitter,
        vals,
        color="#1565C0", alpha=0.55, s=22, zorder=3
    )

ax.axhline(0.10, color="gray", lw=1, ls=":", label="Viability threshold (0.10)")
ax.set_xlabel("Infant Starvation Multiplier (ISM)", fontsize=11)
ax.set_ylabel("Child Maturation Rate (C_matr)", fontsize=11)
ax.set_title("(B) Distribution of C_matr Across Weight Combos", fontsize=11)
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.35)

plt.tight_layout()
out_path = os.path.join(OUT_DIR, "ism_vs_child_survival.png")
plt.savefig(out_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {out_path}")

# ─────────────────────────────────────────────────────────────────────────────
# Console summary
# ─────────────────────────────────────────────────────────────────────────────
print("\nISM vs Child Maturation Rate Summary")
print("=" * 50)
for ism in ISM_VALS:
    sub = data[data["ism"] == ism]
    best = sub.loc[sub["c_matr_mean"].idxmax()]
    print(
        f"ISM={ism:.2f}  max={best['c_matr_mean']:.4f}  "
        f"mean={sub['c_matr_mean'].mean():.4f}  "
        f"best_weights=cw{best['care_weight']:.1f}_fw{best['forage_weight']:.1f}"
    )
