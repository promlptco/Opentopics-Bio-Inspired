# experiments/phase6_plasticity_test/plot_phase6.py
"""Phase 6 — Post-run visualisation (run after run_multi_seed.py completes)

Two figures saved to: outputs/phase6_plasticity_test/multi_seed/

Figure 1 — Motivation weights trajectory  (Phase 4 style)
  Panel 1 (top):    genetic care_weight (solid) + expressed_care_weight (dashed)
  Panel 2 (middle): forage_weight
  Panel 3 (bottom): learning_rate (genetic assimilation signal)

Figure 2 — Population dynamics             (Phase 2 style + children)
  Panel 1 (top):    number of alive mothers
  Panel 2 (middle): mean mother energy
  Panel 3 (bottom): mean child energy
"""
import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COMBINED_DIR   = os.path.join(PROJECT_ROOT, "outputs", "phase6_plasticity_test", "multi_seed")
RUN_DIRS_FILE  = os.path.join(COMBINED_DIR, "run_dirs.json")

INIT_CARE   = 0.30
INIT_FORAGE = 1.0
INIT_LR     = 0.10
INIT_LC     = 0.05   # genome.learning_cost initial value

COL_CARE   = "#1a7a3f"   # dark green  — genetic care
COL_EXPR   = "#e07b00"   # orange      — expressed care (phenotypic, old mothers)
COL_FORAGE = "#2980b9"   # blue        — forage weight
COL_LR     = "#8e44ad"   # purple      — learning rate
COL_LC     = "#c0392b"   # dark red    — learning cost
COL_POP    = "#2ca02c"   # green       — population count
COL_ME     = "#1f77b4"   # steel blue  — mother energy
COL_CE     = "#d62728"   # red         — child energy

try:
    plt.style.use("seaborn-v0_8-whitegrid")
except OSError:
    plt.style.use("seaborn-whitegrid")


# =============================================================================
# Data loading
# =============================================================================

def _load_all_snapshots():
    if not os.path.exists(RUN_DIRS_FILE):
        raise FileNotFoundError(
            f"run_dirs.json not found at {RUN_DIRS_FILE}\n"
            "Run experiments/phase6_plasticity_test/run_multi_seed.py first."
        )
    with open(RUN_DIRS_FILE) as f:
        manifest = json.load(f)
    seeds    = manifest["seeds"]
    run_dirs = manifest["run_dirs"]

    all_snaps = {}
    for seed in seeds:
        rd = run_dirs.get(str(seed))
        if rd is None:
            continue
        path = os.path.join(rd, "generation_snapshots.json")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            snaps = json.load(f)
        if snaps:
            all_snaps[seed] = snaps
    return seeds, all_snaps


def _common_ticks(all_snaps: dict) -> list:
    if not all_snaps:
        return []
    tick_sets = [set(s["tick"] for s in snaps) for snaps in all_snaps.values()]
    return sorted(set.intersection(*tick_sets))


def _extract(all_snaps: dict, ticks: list, key: str, default: float = 0.0) -> np.ndarray:
    tick_idx = {t: i for i, t in enumerate(ticks)}
    rows = []
    for snaps in all_snaps.values():
        row = np.full(len(ticks), default)
        for s in snaps:
            if s["tick"] in tick_idx:
                row[tick_idx[s["tick"]]] = s.get(key, default)
        rows.append(row)
    return np.array(rows)   # shape: (n_seeds, n_ticks)


# =============================================================================
# Shared drawing helpers
# =============================================================================

def _style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, which="major", linestyle="--", linewidth=0.45, alpha=0.55)
    ax.tick_params(which="major", labelsize=9)


def _band(ax, t, mat, color, label):
    mean = mat.mean(0)
    sd   = mat.std(0)
    for row in mat:
        ax.plot(t, row, color=color, alpha=0.10, linewidth=0.65, zorder=1)
    ax.fill_between(t, mean - sd, mean + sd, color=color, alpha=0.18, zorder=2)
    ax.plot(t, mean, color=color, linewidth=2.2, zorder=3, label=label)
    return mean


def _annotate_final(ax, t, mean, color, ylim, fmt=".3f"):
    fv = float(mean[-1])
    ax.annotate(
        f"Final = {fv:{fmt}}",
        xy=(t[-1], fv),
        xytext=(t[-1] * 0.68, ylim[0] + (ylim[1] - ylim[0]) * 0.08),
        fontsize=8.5, color=color,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.88),
    )


# =============================================================================
# Figure 1 — Motivation weights
# =============================================================================

def plot_motivation_weights(all_snaps, ticks, out_dir, n_seeds):
    if not ticks or not all_snaps:
        print("  [Fig 1] No data - skipping.")
        return

    t  = np.array(ticks)
    n  = len(all_snaps)

    cw_mat  = _extract(all_snaps, ticks, "avg_care_weight",          INIT_CARE)
    # avg_expressed_care_weight is now old-mothers-only (artifact-free); fall back to all if missing
    ecw_mat = _extract(all_snaps, ticks, "avg_expressed_care_weight", INIT_CARE)
    fw_mat  = _extract(all_snaps, ticks, "avg_forage_weight",         INIT_FORAGE)
    lr_mat  = _extract(all_snaps, ticks, "avg_learning_rate",         INIT_LR)
    lc_mat  = _extract(all_snaps, ticks, "avg_learning_cost",         INIT_LC)

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(
        4, 1, figsize=(12, 13), sharex=True,
        gridspec_kw={"height_ratios": [1, 1, 1, 1], "hspace": 0.06},
    )

    # Panel 1: care — genetic (solid) vs expressed old-mothers (dashed)
    mean_cw  = _band(ax1, t, cw_mat, COL_CARE, f"genetic care_weight  ({n} seeds)")
    mean_ecw = ecw_mat.mean(0)
    sd_ecw   = ecw_mat.std(0)
    ax1.fill_between(t, mean_ecw - sd_ecw, mean_ecw + sd_ecw, color=COL_EXPR, alpha=0.12, zorder=2)
    ax1.plot(t, mean_ecw, color=COL_EXPR, linewidth=2.0, linestyle="--", zorder=3,
             label="expressed care_weight (old mothers, age>=100)")
    ax1.axhline(INIT_CARE, color="#666", linestyle=":", linewidth=1.0, label=f"Init = {INIT_CARE:.2f}")
    _annotate_final(ax1, t, mean_cw, COL_CARE, ylim=(0.0, 0.90))
    ax1.set_ylim(0.0, 0.90)
    ax1.set_ylabel("care_weight", fontsize=10)
    ax1.legend(loc="upper left", fontsize=8.5, framealpha=0.92, edgecolor="#ccc")
    _style(ax1)
    ax1.tick_params(axis="x", labelbottom=False)

    # Panel 2: forage weight
    mean_fw = _band(ax2, t, fw_mat, COL_FORAGE, "forage_weight  (hitchhiking check)")
    ax2.axhline(INIT_FORAGE, color="#666", linestyle=":", linewidth=1.0, label=f"Init = {INIT_FORAGE:.2f}")
    _annotate_final(ax2, t, mean_fw, COL_FORAGE, ylim=(0.5, 1.10))
    ax2.set_ylim(0.5, 1.10)
    ax2.set_ylabel("forage_weight", fontsize=10)
    ax2.legend(loc="upper right", fontsize=8.5, framealpha=0.92, edgecolor="#ccc")
    _style(ax2)
    ax2.tick_params(axis="x", labelbottom=False)

    # Panel 3: learning rate (genetic assimilation signal)
    mean_lr = _band(ax3, t, lr_mat, COL_LR, "learning_rate  (genetic assimilation signal)")
    ax3.axhline(INIT_LR, color="#666", linestyle=":", linewidth=1.0, label=f"Init = {INIT_LR:.2f}")
    _annotate_final(ax3, t, mean_lr, COL_LR, ylim=(0.0, 0.50))
    ax3.set_ylim(0.0, 0.50)
    ax3.set_ylabel("learning_rate", fontsize=10)
    ax3.legend(loc="upper right", fontsize=8.5, framealpha=0.92, edgecolor="#ccc")
    _style(ax3)
    ax3.tick_params(axis="x", labelbottom=False)

    # Panel 4: learning cost (metabolic cost of plasticity — should drop in Phase 7 after assimilation)
    mean_lc = _band(ax4, t, lc_mat, COL_LC, "learning_cost  (metabolic cost of plasticity)")
    ax4.axhline(INIT_LC, color="#666", linestyle=":", linewidth=1.0, label=f"Init = {INIT_LC:.2f}")
    _annotate_final(ax4, t, mean_lc, COL_LC, ylim=(0.0, 0.30))
    ax4.set_ylim(0.0, 0.30)
    ax4.set_ylabel("learning_cost", fontsize=10)
    ax4.set_xlabel("Simulation Tick", fontsize=11)
    ax4.legend(loc="upper right", fontsize=8.5, framealpha=0.92, edgecolor="#ccc")
    _style(ax4)

    fig.suptitle(
        "Phase 6 — Motivation Weights Trajectory\n"
        f"Kin-conditional plasticity | {n}/{n_seeds} seeds survived | "
        f"init: care={INIT_CARE}, forage={INIT_FORAGE}, lr={INIT_LR}, lc={INIT_LC}",
        fontsize=11, fontweight="bold", y=0.998,
    )
    fig.subplots_adjust(top=0.955, bottom=0.06, left=0.09, right=0.97)

    out_path = os.path.join(out_dir, "phase6_motivation_weights.png")
    fig.savefig(out_path, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


# =============================================================================
# Figure 2 — Population dynamics (pop + mother energy + child energy)
# =============================================================================

def plot_population_dynamics(all_snaps, ticks, out_dir, n_seeds):
    if not ticks or not all_snaps:
        print("  [Fig 2] No data - skipping.")
        return

    t  = np.array(ticks)
    n  = len(all_snaps)

    pop_mat = _extract(all_snaps, ticks, "n_mothers",        0.0)
    me_mat  = _extract(all_snaps, ticks, "avg_mother_energy", 0.0)
    ce_mat  = _extract(all_snaps, ticks, "avg_child_energy",  0.0)

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(12, 10), sharex=True,
        gridspec_kw={"height_ratios": [1, 1, 1], "hspace": 0.06},
    )

    # Panel 1: population
    mean_pop = _band(ax1, t, pop_mat, COL_POP, f"alive mothers  ({n} seeds)")
    ax1.axhline(0, color="tab:red", linestyle="--", linewidth=0.9, alpha=0.6, label="Extinction")
    _annotate_final(ax1, t, mean_pop, COL_POP, ylim=(0, pop_mat.max() * 1.15 + 1), fmt=".1f")
    ax1.set_ylim(0, pop_mat.max() * 1.15 + 1)
    ax1.set_ylabel("alive mothers", fontsize=10)
    ax1.legend(loc="upper right", fontsize=8.5, framealpha=0.92, edgecolor="#ccc")
    _style(ax1)
    ax1.tick_params(axis="x", labelbottom=False)

    # Panel 2: mother energy
    mean_me = _band(ax2, t, me_mat, COL_ME, "mean mother energy")
    ax2.axhline(0.70, color=COL_ME, linestyle=":", linewidth=1.0, alpha=0.7, label="Target E = 0.70")
    ax2.axhline(0.0,  color="tab:red", linestyle="--", linewidth=0.8, alpha=0.5, label="Death")
    _annotate_final(ax2, t, mean_me, COL_ME, ylim=(0.0, 1.05))
    ax2.set_ylim(0.0, 1.05)
    ax2.set_ylabel("mother energy", fontsize=10)
    ax2.legend(loc="upper right", fontsize=8.5, framealpha=0.92, edgecolor="#ccc")
    _style(ax2)
    ax2.tick_params(axis="x", labelbottom=False)

    # Panel 3: child energy
    mean_ce = _band(ax3, t, ce_mat, COL_CE, "mean child energy")
    ax3.axhline(0.0, color="tab:red", linestyle="--", linewidth=0.8, alpha=0.5, label="Starvation")
    _annotate_final(ax3, t, mean_ce, COL_CE, ylim=(0.0, 1.05))
    ax3.set_ylim(0.0, 1.05)
    ax3.set_ylabel("child energy", fontsize=10)
    ax3.set_xlabel("Simulation Tick", fontsize=11)
    ax3.legend(loc="upper right", fontsize=8.5, framealpha=0.92, edgecolor="#ccc")
    _style(ax3)

    fig.suptitle(
        "Phase 6 — Population & Energy Dynamics\n"
        f"Kin-conditional plasticity | {n}/{n_seeds} seeds survived | "
        "Population, mother energy, and child energy over 10 000 ticks",
        fontsize=11, fontweight="bold", y=0.998,
    )
    fig.subplots_adjust(top=0.955, bottom=0.07, left=0.09, right=0.97)

    out_path = os.path.join(out_dir, "phase6_population_dynamics.png")
    fig.savefig(out_path, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


# =============================================================================
# Entry point
# =============================================================================

def main():
    print(f"\nPhase 6 - plotting from: {COMBINED_DIR}")
    seeds, all_snaps = _load_all_snapshots()
    ticks = _common_ticks(all_snaps)

    print(f"  Seeds with data : {len(all_snaps)}/{len(seeds)}")
    print(f"  Common ticks    : {len(ticks)}  ({ticks[0] if ticks else 'N/A'} -> {ticks[-1] if ticks else 'N/A'})")

    os.makedirs(COMBINED_DIR, exist_ok=True)
    plot_motivation_weights(all_snaps, ticks, COMBINED_DIR, len(seeds))
    plot_population_dynamics(all_snaps, ticks, COMBINED_DIR, len(seeds))
    print(f"\nDone. Plots saved to: {COMBINED_DIR}")


if __name__ == "__main__":
    main()
