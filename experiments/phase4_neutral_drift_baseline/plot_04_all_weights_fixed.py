"""Phase 4 — Plot 04: All-Weights Stability Check (Fixed Baseline)

Three stacked subplots showing the trajectory of each motivation weight
over 10,000 ticks from Script 05 (ceiling-drop FIXED, 10 seeds).

  Top    — care_weight   (Blue):   Most stable; barely moves from init=0.80 (Delta ~-0.01)
  Middle — forage_weight (Green):  Larger decline from init=1.0 (Delta ~-0.10) — expected
            bounded mutation drift; forage starts further from the midpoint so
            regresses more, confirming the neutral-drift signature
  Bottom — self_weight   (Purple): Near-neutral from init~0.50; minimal movement

Purpose: Confirm that evolution IS active (forage drifts noticeably, self shifts)
but is NOT selecting against care — care is the MOST STABLE weight, confirming
near-neutrality under the fixed baseline.

Output: outputs/phase4_neutral_drift_baseline/post_mortem/plot_04_all_weights_fixed.png
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
SNAP_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                         "05_ceiling_drop_FIXED", "seed_snapshots")
OUT_DIR  = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                         "post_mortem")
SEEDS    = list(range(42, 52))
INIT_CARE   = 0.80
INIT_FORAGE = 1.00

os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Load all seeds
# ---------------------------------------------------------------------------
all_ticks = []
all_care, all_forage, all_self = [], [], []

for seed in SEEDS:
    with open(os.path.join(SNAP_DIR, f"seed{seed}.json")) as f:
        snaps = json.load(f)
    all_ticks.append([s["tick"] for s in snaps])
    all_care.append([s["avg_care_weight"]   for s in snaps])
    all_forage.append([s["avg_forage_weight"] for s in snaps])
    all_self.append([s["avg_self_weight"]   for s in snaps])

min_len   = min(len(t) for t in all_ticks)
t_common  = all_ticks[0][:min_len]

care_mat   = np.array([c[:min_len] for c in all_care])
forage_mat = np.array([c[:min_len] for c in all_forage])
self_mat   = np.array([c[:min_len] for c in all_self])

mean_care,   sd_care   = care_mat.mean(0),   care_mat.std(0)
mean_forage, sd_forage = forage_mat.mean(0), forage_mat.std(0)
mean_self,   sd_self   = self_mat.mean(0),   self_mat.std(0)

final_care   = float(care_mat[:, -1].mean())
final_forage = float(forage_mat[:, -1].mean())
final_self   = float(self_mat[:, -1].mean())

print(f"Final (tick {t_common[-1]}):  "
      f"care={final_care:.3f}  forage={final_forage:.3f}  self={final_self:.3f}")
print(f"Delta from init:            "
      f"care={final_care-INIT_CARE:+.3f}  forage={final_forage-INIT_FORAGE:+.3f}  self={final_self-0.5:+.3f}")


# ---------------------------------------------------------------------------
# Plot — 3 stacked subplots, shared X
# ---------------------------------------------------------------------------
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("seaborn-whitegrid")

col_care   = "#2166AC"   # Blue
col_forage = "#27AE60"   # Green
col_self   = "#7D3C98"   # Purple

PANEL_H = {"height_ratios": [1, 1, 1]}
fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True,
                         gridspec_kw={"hspace": 0.06, **PANEL_H})
ax_care, ax_forage, ax_self = axes
MAX_TICK = t_common[-1]


def _draw_panel(ax, mat, mean, sd, color, init_val, label, ylabel, ylim):
    # Light seed lines
    for row in mat:
        ax.plot(t_common, row, color=color, alpha=0.10, linewidth=0.7, zorder=1)
    # SD band
    ax.fill_between(t_common, mean - sd, mean + sd,
                    color=color, alpha=0.15, zorder=2)
    # Mean line
    ax.plot(t_common, mean, color=color, linewidth=2.2, zorder=3, label=label)
    # Init reference
    ax.axhline(init_val, color="#666666", linestyle="--", linewidth=1.0,
               label=f"Init = {init_val:.2f}", zorder=1)
    # Final annotation
    final_val = float(mean[-1])
    ax.annotate(
        f"Final = {final_val:.3f}  ({final_val - init_val:+.3f})",
        xy=(MAX_TICK, final_val),
        xytext=(MAX_TICK * 0.72, ylim[0] + (ylim[1] - ylim[0]) * 0.10),
        fontsize=9, color=color,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.88),
    )
    ax.set_ylim(ylim)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92, edgecolor="#cccccc")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, which="major", linestyle="--", linewidth=0.45, alpha=0.6)
    ax.tick_params(axis="x", which="both", labelbottom=False)


# Top: care_weight
_draw_panel(ax_care, care_mat, mean_care, sd_care,
            col_care, INIT_CARE,
            "care_weight  (10 seeds)", "care_weight",
            ylim=(0.50, 0.95))

# Middle: forage_weight
_draw_panel(ax_forage, forage_mat, mean_forage, sd_forage,
            col_forage, INIT_FORAGE,
            "forage_weight  (10 seeds)", "forage_weight",
            ylim=(0.50, 1.08))

# Bottom: self_weight (no fixed init — starts ~U(0,1), mean ≈ 0.5)
_draw_panel(ax_self, self_mat, mean_self, sd_self,
            col_self, 0.50,
            "self_weight  (10 seeds)", "self_weight",
            ylim=(0.20, 0.80))

# X-axis label only on bottom panel
ax_self.tick_params(axis="x", labelbottom=True)
ax_self.set_xlabel("Simulation Tick", fontsize=11)

# Overall title
fig.suptitle(
    "Motivation Weights Trajectory (Fixed Baseline): Care remains near-neutral",
    fontsize=12, fontweight="bold", y=0.995
)

fig.subplots_adjust(top=0.965, bottom=0.07, left=0.09, right=0.97, hspace=0.06)
out_path = os.path.join(OUT_DIR, "plot_04_all_weights_fixed.png")
plt.savefig(out_path, dpi=150, facecolor="white")
plt.close()
print(f"Saved: {out_path}")
