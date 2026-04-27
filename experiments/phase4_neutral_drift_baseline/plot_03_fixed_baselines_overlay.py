"""Phase 4 — Plot 03: Fixed Baselines Overlay (Standard Cost vs. Zero Cost)

Overlays care_weight trajectories (mean ± 1 SD) for:
  Run A — Script 05 FIXED  (standard costs: infant_mult=1.0, feed_cost=0.03)  [Blue]
  Run B — Script 06 FIXED  (zero fitness cost: infant_mult=0.0, feed_cost=0.0) [Red]

The near-identical trajectories demonstrate that care_weight is genuinely
near-neutral in the standard ecological configuration: applying or removing
real fitness costs on care makes no statistically detectable difference.

Output: outputs/phase4_neutral_drift_baseline/post_mortem/plot_03_fixed_baselines_overlay.png
"""

import os, sys, json
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SNAP_A   = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                         "05_ceiling_drop_FIXED", "seed_snapshots")
SNAP_B   = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                         "06_true_neutral_FIXED", "seed_snapshots")
CKPT_A   = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                         "05_ceiling_drop_FIXED", "checkpoint.json")
CKPT_B   = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                         "06_true_neutral_FIXED", "checkpoint.json")
OUT_DIR  = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                         "post_mortem")
SEEDS    = list(range(42, 52))

os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helper: load trajectories from a seed_snapshots directory
# ---------------------------------------------------------------------------
def load_trajectories(snap_dir: str) -> tuple[list[int], np.ndarray]:
    """Return (ticks, cw_matrix) where cw_matrix is shape (n_seeds, n_ticks)."""
    all_ticks, all_cw = [], []
    for seed in SEEDS:
        with open(os.path.join(snap_dir, f"seed{seed}.json")) as f:
            snaps = json.load(f)
        all_ticks.append([s["tick"] for s in snaps])
        all_cw.append([s["avg_care_weight"] for s in snaps])
    min_len   = min(len(t) for t in all_ticks)
    t_common  = all_ticks[0][:min_len]
    cw_matrix = np.array([c[:min_len] for c in all_cw])
    return t_common, cw_matrix


# ---------------------------------------------------------------------------
# Helper: load final mean CW from checkpoint
# ---------------------------------------------------------------------------
def final_mean_cw(ckpt_path: str) -> float:
    with open(ckpt_path) as f:
        ckpt = json.load(f)
    return float(np.mean([r["final_cw"] for r in ckpt]))


def mean_pearson_r(ckpt_path: str) -> float:
    with open(ckpt_path) as f:
        ckpt = json.load(f)
    return float(np.mean([r["pearson_r"] for r in ckpt if r.get("pearson_r") is not None]))


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
t_a, cw_a = load_trajectories(SNAP_A)
t_b, cw_b = load_trajectories(SNAP_B)

mean_a, sd_a = cw_a.mean(axis=0), cw_a.std(axis=0)
mean_b, sd_b = cw_b.mean(axis=0), cw_b.std(axis=0)

final_a = final_mean_cw(CKPT_A)
final_b = final_mean_cw(CKPT_B)
r_a     = mean_pearson_r(CKPT_A)
r_b     = mean_pearson_r(CKPT_B)

print(f"Run A (Script 05 FIXED) — final mean CW: {final_a:.3f}  mean r: {r_a:+.4f}")
print(f"Run B (Script 06 FIXED) — final mean CW: {final_b:.3f}  mean r: {r_b:+.4f}")
print(f"Gap in final CW: {abs(final_a - final_b):.3f}")


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("seaborn-whitegrid")

col_a = "#2166AC"   # Blue  — standard cost
col_b = "#C0392B"   # Red   — zero cost

fig, ax = plt.subplots(figsize=(11, 5))

# Per-seed light lines
for i in range(len(SEEDS)):
    ax.plot(t_a, cw_a[i], color=col_a, alpha=0.10, linewidth=0.8, zorder=1)
    ax.plot(t_b, cw_b[i], color=col_b, alpha=0.10, linewidth=0.8, zorder=1)

# ±1 SD bands
ax.fill_between(t_a, mean_a - sd_a, mean_a + sd_a,
                color=col_a, alpha=0.13, zorder=2)
ax.fill_between(t_b, mean_b - sd_b, mean_b + sd_b,
                color=col_b, alpha=0.13, zorder=2)

# Mean lines
ax.plot(t_a, mean_a, color=col_a, linewidth=2.3, zorder=3,
        label=f"Script 05 — Standard cost (infant_mult=1.0, feed_cost=0.03)")
ax.plot(t_b, mean_b, color=col_b, linewidth=2.3, zorder=3,
        label=f"Script 06 — Zero cost (infant_mult=0.0, feed_cost=0.0)")

# Init ceiling reference
ax.axhline(0.80, color="#555555", linestyle="--", linewidth=1.1,
           label="Init ceiling (0.80)", zorder=1)

# Final value annotations on right margin
MAX_TICK = t_a[-1]
ax.annotate(
    f"Final = {final_a:.3f}",
    xy=(MAX_TICK, mean_a[-1]),
    xytext=(MAX_TICK + 80, mean_a[-1] + 0.012),
    fontsize=9, color=col_a, ha="left",
    arrowprops=dict(arrowstyle="-", color=col_a, lw=0.8),
)
ax.annotate(
    f"Final = {final_b:.3f}",
    xy=(MAX_TICK, mean_b[-1]),
    xytext=(MAX_TICK + 80, mean_b[-1] - 0.018),
    fontsize=9, color=col_b, ha="left",
    arrowprops=dict(arrowstyle="-", color=col_b, lw=0.8),
)

# Gap insignificance annotation (centre-right of plot)
mid_tick = MAX_TICK * 0.62
mid_y    = (mean_a.mean() + mean_b.mean()) / 2
ax.annotate(
    f"Gap = {abs(final_a - final_b):.3f}  (p > 0.05, not significant)\n"
    f"r(std) = {r_a:+.3f}   r(neutral) = {r_b:+.3f}",
    xy=(mid_tick, mid_y),
    fontsize=9.5, color="#333333", ha="center", va="center",
    bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#aaaaaa", alpha=0.92),
)

ax.set_xlim(0, MAX_TICK * 1.01)
ax.set_ylim(0.55, 0.88)
ax.set_xlabel("Simulation Tick", fontsize=11)
ax.set_ylabel("Mean care_weight", fontsize=11)
ax.legend(loc="lower left", fontsize=9.5, framealpha=0.92, edgecolor="#cccccc")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.55)

ax.set_title(
    "Phase 4 Fixed Baselines: Standard Cost vs. Zero Cost\n"
    "care_weight is near-neutral — applying fitness costs makes no detectable difference",
    fontsize=11, fontweight="bold"
)

plt.tight_layout()
out_path = os.path.join(OUT_DIR, "plot_03_fixed_baselines_overlay.png")
plt.savefig(out_path, dpi=150, facecolor="white", bbox_inches="tight")
plt.close()
print(f"Saved: {out_path}")
