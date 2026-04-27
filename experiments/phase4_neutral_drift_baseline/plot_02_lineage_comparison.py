"""Phase 4 Post-Mortem — Plot 02: Lineage Fitness Scatter (Buggy vs. Fixed)

Scatter plot: X = lineage mean care_weight, Y = total descendants (birth events)

BUGGY  (Script 02 — '02_ceiling_drop_erosion'):
  Lineage data loaded from checkpoint.json (per-seed dicts with mean_cares, n_descs).
  Expected: Pearson r ≈ −0.67 (high-care lineages have fewer descendants).

FIXED  (Script 05 — '05_ceiling_drop_FIXED'):
  Lineage data computed on-the-fly from birth_log.csv for each seed's run dir.
  Expected: Pearson r ≈ 0 (care_weight does not predict descendants).

Output: outputs/phase4_neutral_drift_baseline/post_mortem/plot_02_lineage_comparison.png
"""

import os, sys, csv, json
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BUGGY_CKPT  = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                            "02_ceiling_drop_erosion", "checkpoint.json")
FIXED_BASE  = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                            "05_ceiling_drop_FIXED")
OUT_DIR     = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                            "post_mortem")
SEEDS       = list(range(42, 52))

os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def pearson_r(xs, ys):
    xs, ys = np.array(xs, dtype=float), np.array(ys, dtype=float)
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = xs.mean(), ys.mean()
    num = ((xs - mx) * (ys - my)).sum()
    dx  = np.sqrt(((xs - mx) ** 2).sum())
    dy  = np.sqrt(((ys - my) ** 2).sum())
    if dx == 0 or dy == 0:
        return float("nan")
    return float(num / (dx * dy))


# ---------------------------------------------------------------------------
# 1. Buggy-run lineage data (from checkpoint.json)
# ---------------------------------------------------------------------------
with open(BUGGY_CKPT) as f:
    ckpt2 = json.load(f)

buggy_cares, buggy_descs = [], []
for entry in ckpt2:
    lin = entry.get("lineage", {})
    mean_cares = lin.get("mean_cares", [])
    n_descs    = lin.get("n_descs", [])
    buggy_cares.extend(mean_cares)
    buggy_descs.extend(n_descs)

r_buggy = pearson_r(buggy_cares, buggy_descs)
print(f"Buggy run: {len(buggy_cares)} lineages pooled across 10 seeds")
print(f"  Pearson r = {r_buggy:+.4f}")


# ---------------------------------------------------------------------------
# 2. Fixed-run lineage data (computed from birth_log.csv)
# ---------------------------------------------------------------------------
run_dirs = sorted(
    [d for d in os.listdir(FIXED_BASE) if d.startswith("run_")],
    key=lambda d: int(d.rsplit("_seed", 1)[1])
)

fixed_cares, fixed_descs = [], []

for run_dir in run_dirs:
    birth_log = os.path.join(FIXED_BASE, run_dir, "birth_log.csv")
    if not os.path.exists(birth_log):
        continue

    # Group births by lineage_id
    lineage_cares: dict[int, list[float]] = defaultdict(list)
    with open(birth_log) as f:
        for row in csv.DictReader(f):
            lid = int(row["mother_lineage_id"])
            cw  = float(row["mother_care_weight"])
            lineage_cares[lid].append(cw)

    # Per-lineage: mean care_weight and total births (= descendants)
    for lid, cares in lineage_cares.items():
        fixed_cares.append(float(np.mean(cares)))
        fixed_descs.append(len(cares))

r_fixed = pearson_r(fixed_cares, fixed_descs)
print(f"\nFixed run: {len(fixed_cares)} lineages pooled across {len(run_dirs)} seeds")
print(f"  Pearson r = {r_fixed:+.4f}")


# ---------------------------------------------------------------------------
# 3. Plot — side-by-side scatter
# ---------------------------------------------------------------------------
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("seaborn-whitegrid")

fig, (ax_bug, ax_fix) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=False)

col_bug = "#D6604D"
col_fix = "#4393C3"

def _add_trendline(ax, xs, ys, color):
    xs_arr, ys_arr = np.array(xs), np.array(ys)
    if len(xs_arr) < 2:
        return
    m, b = np.polyfit(xs_arr, ys_arr, 1)
    x_line = np.linspace(xs_arr.min(), xs_arr.max(), 200)
    ax.plot(x_line, m * x_line + b, color=color, linewidth=1.8,
            linestyle="--", alpha=0.85, zorder=3)


# --- Buggy panel ---
ax_bug.scatter(buggy_cares, buggy_descs, color=col_bug, alpha=0.55,
               s=30, edgecolors="none", label="Lineage", zorder=2)
_add_trendline(ax_bug, buggy_cares, buggy_descs, col_bug)
ax_bug.set_xlabel("Lineage mean care_weight", fontsize=11)
ax_bug.set_ylabel("Total descendants (birth events)", fontsize=11)
ax_bug.set_title(
    f"BUGGY run (Script 02)\nArtefact selection  |  r = {r_buggy:+.3f}",
    fontsize=11, fontweight="bold", color=col_bug
)
ax_bug.text(0.97, 0.97, f"n = {len(buggy_cares)} lineages\nr = {r_buggy:+.3f}",
            transform=ax_bug.transAxes, ha="right", va="top", fontsize=10,
            color=col_bug, bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8))
ax_bug.spines["top"].set_visible(False)
ax_bug.spines["right"].set_visible(False)

# --- Fixed panel ---
ax_fix.scatter(fixed_cares, fixed_descs, color=col_fix, alpha=0.55,
               s=30, edgecolors="none", label="Lineage", zorder=2)
_add_trendline(ax_fix, fixed_cares, fixed_descs, col_fix)
ax_fix.set_xlabel("Lineage mean care_weight", fontsize=11)
ax_fix.set_ylabel("Total descendants (birth events)", fontsize=11)
ax_fix.set_title(
    f"FIXED run (Script 05)\nTrue neutrality  |  r = {r_fixed:+.3f}",
    fontsize=11, fontweight="bold", color=col_fix
)
ax_fix.text(0.97, 0.97, f"n = {len(fixed_cares)} lineages\nr = {r_fixed:+.3f}",
            transform=ax_fix.transAxes, ha="right", va="top", fontsize=10,
            color=col_fix, bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8))
ax_fix.spines["top"].set_visible(False)
ax_fix.spines["right"].set_visible(False)

fig.suptitle(
    "Lineage Fitness: Artefact Selection (r < 0) vs. True Neutrality (r ≈ 0)\n"
    "X = lineage mean care_weight  |  Y = total births in lineage  |  pooled across 10 seeds",
    fontsize=11, fontweight="bold", y=1.01
)
plt.tight_layout()

out_path = os.path.join(OUT_DIR, "plot_02_lineage_comparison.png")
plt.savefig(out_path, dpi=150, facecolor="white", bbox_inches="tight")
plt.close()
print(f"\nSaved: {out_path}")

# Summary
print("\n=== Lineage Summary ===")
print(f"Buggy  | n={len(buggy_cares):4d} lineages | r={r_buggy:+.4f} | "
      f"mean_care={np.mean(buggy_cares):.3f} | "
      f"mean_descs={np.mean(buggy_descs):.1f}")
print(f"Fixed  | n={len(fixed_cares):4d} lineages | r={r_fixed:+.4f} | "
      f"mean_care={np.mean(fixed_cares):.3f} | "
      f"mean_descs={np.mean(fixed_descs):.1f}")
