"""Phase 4 Post-Mortem — Plot 01: Artefact Mechanism (Dual Y-Axis)

Left Y  (blue, line): Mean care_weight ± 1 SD from the BUGGY ceiling-drop run
         (Script 02: 02_ceiling_drop_erosion, 10 seeds, 10k ticks)
Right Y (red, bars):  Orphan Injection Rate — fraction of births per 1000-tick bin
         where the birth-mother died within 100 ticks (= maturity_age).
         Computed from the FIXED run's birth_log + death_log (same seeds,
         identical parameters, equivalent early dynamics).

Orphan injections are the mechanistic cause of the care crash:
children whose mother died before tick=100 inherited Genome() (care=0.50)
in the buggy simulation, silently injecting low-care genomes during the
initial population die-off (ticks 0–3000).

Output: outputs/phase4_neutral_drift_baseline/post_mortem/plot_01_artefact_mechanism.png
"""

import os, sys, csv, json
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BUGGY_SNAP_DIR  = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                                "02_ceiling_drop_erosion", "seed_snapshots")
FIXED_BASE      = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                                "05_ceiling_drop_FIXED")
OUT_DIR         = os.path.join(PROJECT_ROOT, "outputs", "phase4_neutral_drift_baseline",
                                "post_mortem")
SEEDS           = list(range(42, 52))
MATURITY_AGE    = 100
BIN_SIZE        = 1000
MAX_TICK        = 10_000

os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Load buggy-run care_weight trajectories
# ---------------------------------------------------------------------------
all_ticks, all_cw = [], []

for seed in SEEDS:
    snap_file = os.path.join(BUGGY_SNAP_DIR, f"seed{seed}.json")
    with open(snap_file) as f:
        snaps = json.load(f)
    ticks = [s["tick"] for s in snaps]
    cw    = [s["avg_care_weight"] for s in snaps]
    all_ticks.append(ticks)
    all_cw.append(cw)

# Align on common tick grid (all snapshots use same SNAPSHOT_INTERVAL)
min_len    = min(len(t) for t in all_ticks)
t_common   = all_ticks[0][:min_len]
cw_matrix  = np.array([c[:min_len] for c in all_cw])
mean_cw    = cw_matrix.mean(axis=0)
sd_cw      = cw_matrix.std(axis=0)


# ---------------------------------------------------------------------------
# 2. Compute orphan injection rate from fixed-run birth + death logs
# ---------------------------------------------------------------------------
bins = list(range(0, MAX_TICK, BIN_SIZE))   # [0, 1000, 2000, ..., 9000]
bin_births  = {b: 0 for b in bins}
bin_orphans = {b: 0 for b in bins}

# Locate fixed run directories (one per seed)
run_dirs = sorted(
    [d for d in os.listdir(FIXED_BASE) if d.startswith("run_")],
    key=lambda d: int(d.rsplit("_seed", 1)[1])
)

for run_dir in run_dirs:
    birth_log = os.path.join(FIXED_BASE, run_dir, "birth_log.csv")
    death_log = os.path.join(FIXED_BASE, run_dir, "death_log.csv")
    if not os.path.exists(birth_log) or not os.path.exists(death_log):
        continue

    # Build death dict: agent_id (mother) -> earliest death tick
    mother_death: dict[int, int] = {}
    with open(death_log) as f:
        for row in csv.DictReader(f):
            if row["agent_type"] == "mother":
                mid  = int(row["agent_id"])
                dtick = int(row["tick"])
                if mid not in mother_death or dtick < mother_death[mid]:
                    mother_death[mid] = dtick

    # Count births and orphans per bin
    with open(birth_log) as f:
        for row in csv.DictReader(f):
            btick = int(row["tick"])
            mid   = int(row["mother_id"])
            # Find bin
            b = (btick // BIN_SIZE) * BIN_SIZE
            if b not in bin_births:
                continue
            bin_births[b] += 1
            # Orphan: mother died within MATURITY_AGE ticks of birth
            if mid in mother_death and mother_death[mid] <= btick + MATURITY_AGE:
                bin_orphans[b] += 1

# Compute orphan rate per bin
orphan_rates = []
for b in bins:
    if bin_births[b] > 0:
        orphan_rates.append(bin_orphans[b] / bin_births[b])
    else:
        orphan_rates.append(0.0)

bar_centers = [b + BIN_SIZE / 2 for b in bins]


# ---------------------------------------------------------------------------
# 3. Plot — 2 stacked subplots, shared X axis
# ---------------------------------------------------------------------------
try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("seaborn-whitegrid")

col_care   = "#2166AC"
col_orphan = "#C0392B"
col_sd     = "#2166AC"

fig, (ax_top, ax_bot) = plt.subplots(
    2, 1, figsize=(12, 7),
    sharex=True,
    gridspec_kw={"hspace": 0.05, "height_ratios": [1.6, 1]}
)

# ── Top subplot: care_weight crash ──────────────────────────────────────────
ax_top.plot(t_common, mean_cw, color=col_care, linewidth=2.2,
            label="Mean care_weight  (buggy run, 10 seeds)", zorder=3)
ax_top.fill_between(t_common,
                    mean_cw - sd_cw,
                    mean_cw + sd_cw,
                    color=col_sd, alpha=0.12, label="±1 SD", zorder=2)
ax_top.axhline(0.80, color="#555555", linestyle="--", linewidth=1.2,
               label="Init ceiling (0.80)", zorder=1)
ax_top.axhline(0.50, color="#888888", linestyle=":",  linewidth=1.2,
               label="Bug-artefact attractor (~0.50)", zorder=1)

ax_top.set_ylim(0.30, 0.90)
ax_top.set_xlim(0, MAX_TICK)
ax_top.set_ylabel("Mean care_weight", fontsize=11)
ax_top.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
ax_top.legend(loc="lower right", fontsize=9, framealpha=0.92, edgecolor="#cccccc")
ax_top.spines["top"].set_visible(False)
ax_top.spines["right"].set_visible(False)
ax_top.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.6)

# label the two horizontal lines directly on the right margin
ax_top.text(MAX_TICK * 1.001, 0.80, "0.80", va="center", ha="left",
            fontsize=8.5, color="#555555")
ax_top.text(MAX_TICK * 1.001, 0.50, "0.50", va="center", ha="left",
            fontsize=8.5, color="#888888")

# ── Bottom subplot: orphan injection rate ────────────────────────────────────
max_rate_pct = max(r * 100 for r in orphan_rates)

ax_bot.bar(bar_centers, [r * 100 for r in orphan_rates],
           width=BIN_SIZE * 0.72, color=col_orphan, alpha=0.60,
           label="Orphan injection rate (per 1000-tick bin)", zorder=2)

# Annotate peak bar
peak_idx = orphan_rates.index(max(orphan_rates))
peak_x   = bar_centers[peak_idx]
peak_y   = orphan_rates[peak_idx] * 100
ax_bot.annotate(
    f"Peak {peak_y:.1f}%",
    xy=(peak_x, peak_y),
    xytext=(peak_x + BIN_SIZE * 1.4, peak_y * 0.88),
    fontsize=9, color=col_orphan,
    arrowprops=dict(arrowstyle="->", color=col_orphan, lw=1.1),
    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=col_orphan, alpha=0.85),
)

ax_bot.set_ylim(0, max_rate_pct * 1.22)
ax_bot.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax_bot.set_ylabel("Orphan rate (%)", fontsize=11)
ax_bot.set_xlabel("Simulation Tick", fontsize=11)
ax_bot.legend(loc="upper right", fontsize=9, framealpha=0.92, edgecolor="#cccccc")
ax_bot.spines["top"].set_visible(False)
ax_bot.spines["right"].set_visible(False)
ax_bot.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.6)

# ── Overall title ────────────────────────────────────────────────────────────
fig.suptitle(
    "Phase 4 Artefact: Care Weight Crash vs. Orphan Injection Window",
    fontsize=13, fontweight="bold", y=0.98
)

fig.subplots_adjust(top=0.93, bottom=0.09, left=0.08, right=0.97, hspace=0.05)
out_path = os.path.join(OUT_DIR, "plot_01_artefact_mechanism.png")
plt.savefig(out_path, dpi=150, facecolor="white")
plt.close()
print(f"Saved: {out_path}")

# Print summary stats
print(f"\nOrphan injection rate by bin (computed from fixed-run logs as proxy):")
for b, rate in zip(bins, orphan_rates):
    bar = "#" * int(rate * 50)
    print(f"  Ticks {b:5d}-{b+BIN_SIZE:5d}: {rate*100:5.1f}%  {bar}")
print(f"\nCare_weight trajectory (buggy run, 10-seed mean):")
for tick, cw_val in zip(t_common[::5], mean_cw[::5]):
    print(f"  Tick {tick:6d}: {cw_val:.3f}")
