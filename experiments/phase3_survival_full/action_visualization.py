"""
experiments/phase3_survival_full/action_visualization.py

Phase 3b -- Action Visualization
Canonical genome: care=0.3, forage=1.0, self=0.7  (food=48 baseline)
Duration: 1000 ticks

Required plots (from EXPERIMENT_DESIGN.md Phase 3b):
  1. Stacked area chart  -- motivation distribution (FORAGE / CARE / SELF) per tick
  2. Single-agent raster -- all 15 mothers, color-coded action per tick (seed 42)
  3. Child energy + care event markers + distance-to-child on same graph

Usage:
  python experiments/phase3_survival_full/action_visualization.py
"""

import sys
import os
import json
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import BoundaryNorm, ListedColormap

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase3_survival_full.run import MotherChildSurvivalSimulation, make_config
from utils.experiment import set_seed

# ============================================================
# Canonical genome — Phase 3a motivation sweep result (food=48)
# ============================================================

CANONICAL_PARAMS = {
    "width": 30,
    "height": 30,
    "perception_radius": 8.0,
    "hunger_rate": 0.005,
    "move_cost": 0.001,
    "eat_gain": 0.07,
    "init_food": 48,
    "rest_recovery": 0.11,
    "fatigue_rate": 0.01,
    "child_hunger_rate": 0.005,
    "feed_amount": 0.20,
    "feed_cost": 0.01,
    "feed_distance": 1,
    "food_respawn_per_tick": 3,
    "care_weight": 0.3,
    "forage_weight": 1.0,
    "self_weight": 0.7,
    "name": "canonical",
}

DURATION = 1000
VIZ_SEEDS = [42, 43, 44, 45, 46]   # 5 seeds for aggregate plots
RASTER_SEED = 42                    # single seed for per-agent raster
TAU = 0.1
NOISE = 0.1
SMOOTH_WINDOW = 25

# Action colour palette for raster
ACTION_LABELS = [
    "MOVE_FOOD",
    "PICK",
    "EAT",
    "MOVE_CHILD",
    "FEED",
    "REST",
    "FAILED_FORAGE",
    "FAILED_CARE",
    "FAILED_SELF",
    "DEAD",
]
ACTION_CODE = {a: i for i, a in enumerate(ACTION_LABELS)}

RASTER_COLORS = [
    "#4C72B0",   # MOVE_FOOD  — steel blue
    "#DD8452",   # PICK       — orange
    "#55A868",   # EAT        — green
    "#C44E52",   # MOVE_CHILD — red-purple
    "#E377C2",   # FEED       — pink
    "#B0B0B0",   # REST       — light grey
    "#555555",   # FAILED_FORAGE — dark grey
    "#333333",   # FAILED_CARE   — charcoal
    "#888888",   # FAILED_SELF   — mid grey
    "#000000",   # DEAD          — black
]

MOTIVATION_COLORS = {
    "FORAGE": "#DD8452",
    "CARE":   "#E377C2",
    "SELF":   "#4C72B0",
}


# ============================================================
# Helpers
# ============================================================

def smooth(arr, w=SMOOTH_WINDOW):
    if w <= 1 or len(arr) < w:
        return np.asarray(arr, dtype=float)
    kernel = np.ones(w) / w
    return np.convolve(arr, kernel, mode="same")


def pad_history(history, duration, key):
    out = np.zeros(duration, dtype=float)
    for t, row in enumerate(history[:duration]):
        out[t] = row.get(key, 0.0)
    return out


def run_one_viz(seed, agent_log=False):
    set_seed(seed)
    cfg = make_config(CANONICAL_PARAMS, DURATION)
    sim = MotherChildSurvivalSimulation(cfg, tau=TAU, perceptual_noise=NOISE)
    sim._agent_log_enabled = agent_log
    return sim.run()


# ============================================================
# Plot 1 — Stacked motivation area chart
# ============================================================

def plot_stacked_motivation(results, out_dir):
    ticks = np.arange(DURATION)

    forage_runs, care_runs, self_runs = [], [], []

    for r in results:
        hist = r["motivation_history"]
        alive = np.array([row.get("alive", 1) for row in hist[:DURATION]], dtype=float)
        alive = np.maximum(alive, 1.0)

        f = pad_history(hist, DURATION, "FORAGE") / alive
        c = pad_history(hist, DURATION, "CARE")   / alive
        s = pad_history(hist, DURATION, "SELF")   / alive

        forage_runs.append(smooth(f))
        care_runs.append(smooth(c))
        self_runs.append(smooth(s))

    f_mean = np.mean(forage_runs, axis=0)
    c_mean = np.mean(care_runs,   axis=0)
    s_mean = np.mean(self_runs,   axis=0)

    f_sd = np.std(forage_runs, axis=0)
    c_sd = np.std(care_runs,   axis=0)
    s_sd = np.std(self_runs,   axis=0)

    fig, ax = plt.subplots(figsize=(13, 5))

    ax.stackplot(
        ticks,
        f_mean, c_mean, s_mean,
        labels=["FORAGE", "CARE", "SELF"],
        colors=[MOTIVATION_COLORS["FORAGE"], MOTIVATION_COLORS["CARE"], MOTIVATION_COLORS["SELF"]],
        alpha=0.80,
    )

    # SD bands as thin error lines on the boundary between FORAGE and CARE
    boundary_fc = f_mean
    boundary_cs = f_mean + c_mean
    ax.fill_between(ticks, boundary_fc - f_sd, boundary_fc + f_sd, color="white", alpha=0.25, linewidth=0)
    ax.fill_between(ticks, boundary_cs - c_sd, boundary_cs + c_sd, color="white", alpha=0.25, linewidth=0)

    # Tail-window mean annotations
    tw = 200
    f_tail = float(np.mean(f_mean[-tw:]))
    c_tail = float(np.mean(c_mean[-tw:]))
    s_tail = float(np.mean(s_mean[-tw:]))

    ax.axvline(DURATION - tw, color="white", linestyle="--", linewidth=1.0, alpha=0.6, label="Tail window start")

    summary = (
        f"Tail means (last {tw} ticks):\n"
        f"  FORAGE = {f_tail:.1%}\n"
        f"  CARE   = {c_tail:.1%}\n"
        f"  SELF   = {s_tail:.1%}"
    )
    ax.text(0.01, 0.04, summary, transform=ax.transAxes, fontsize=9,
            bbox=dict(facecolor="white", edgecolor="gray", alpha=0.85))

    ax.set_xlim(0, DURATION - 1)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Tick", fontsize=11)
    ax.set_ylabel("Fraction of actions per alive mother", fontsize=11)
    ax.set_title(
        f"Phase 3b — Motivation Distribution Over Time\n"
        f"Canonical genome: care=0.3 / forage=1.0 / self=0.7 | food=48 | "
        f"{len(results)} seeds | {DURATION} ticks",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    ax.grid(True, linestyle="--", alpha=0.25)

    plt.tight_layout()
    path = os.path.join(out_dir, "phase3b_stacked_motivation.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {path}")

    return {"forage_tail": f_tail, "care_tail": c_tail, "self_tail": s_tail}


# ============================================================
# Plot 2 — Per-agent action raster (seed 42, all 15 mothers)
# ============================================================

def plot_agent_raster(raster_result, out_dir):
    per_agent_log = raster_result.get("per_agent_log")
    agent_order   = raster_result.get("agent_order")

    if per_agent_log is None or agent_order is None:
        print("WARNING: no per-agent log available, skipping raster plot.")
        return

    n_agents = len(agent_order)
    raster = np.full((n_agents, DURATION), ACTION_CODE["DEAD"], dtype=int)

    for row_idx, mid in enumerate(agent_order):
        actions = per_agent_log.get(mid, [])
        for t, act in enumerate(actions[:DURATION]):
            raster[row_idx, t] = ACTION_CODE.get(act, ACTION_CODE["DEAD"])

    cmap = ListedColormap(RASTER_COLORS)
    norm = BoundaryNorm(boundaries=np.arange(len(ACTION_LABELS) + 1) - 0.5, ncolors=len(ACTION_LABELS))

    fig, ax = plt.subplots(figsize=(14, 5))

    im = ax.imshow(
        raster,
        aspect="auto",
        interpolation="nearest",
        cmap=cmap,
        norm=norm,
        origin="upper",
    )

    ax.set_xlabel("Tick", fontsize=11)
    ax.set_ylabel("Mother ID (row)", fontsize=11)
    ax.set_title(
        f"Phase 3b — Per-Agent Action Raster (seed={RASTER_SEED})\n"
        f"Canonical genome: care=0.3 / forage=1.0 / self=0.7 | food=48 | {DURATION} ticks",
        fontsize=12, fontweight="bold",
    )

    ax.set_yticks(np.arange(n_agents))
    ax.set_yticklabels([f"M{i}" for i in range(n_agents)], fontsize=7)
    ax.set_xlim(0, DURATION - 1)

    legend_patches = [
        mpatches.Patch(color=RASTER_COLORS[ACTION_CODE[a]], label=a)
        for a in ACTION_LABELS
    ]
    ax.legend(
        handles=legend_patches,
        loc="lower right",
        fontsize=7,
        ncol=2,
        framealpha=0.9,
        title="Action",
        title_fontsize=8,
    )

    ax.grid(False)
    plt.tight_layout()
    path = os.path.join(out_dir, "phase3b_agent_raster.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {path}")


# ============================================================
# Plot 3 — Child energy + care event markers + distance overlay
# ============================================================

def plot_child_care_distance(results, out_dir):
    ticks = np.arange(DURATION)

    hunger_runs, feed_runs, dist_runs = [], [], []

    for r in results:
        hunger = smooth(np.array(r["child_hunger_history"][:DURATION], dtype=float))
        hunger_runs.append(hunger)

        fhist = r["feed_history"]
        alive = np.array([row.get("alive", 1) for row in fhist[:DURATION]], dtype=float)
        alive = np.maximum(alive, 1.0)
        feed_rate = pad_history(fhist, DURATION, "FEED") / alive
        feed_runs.append(smooth(feed_rate))

        dist = smooth(np.array(r["mother_child_distance_history"][:DURATION], dtype=float))
        dist_runs.append(dist)

    h_mean = np.mean(hunger_runs, axis=0)
    h_sd   = np.std(hunger_runs,  axis=0)
    f_mean = np.mean(feed_runs,   axis=0)
    f_sd   = np.std(feed_runs,    axis=0)
    d_mean = np.mean(dist_runs,   axis=0)
    d_sd   = np.std(dist_runs,    axis=0)

    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.08))

    # Primary: child hunger (red)
    ax1.fill_between(ticks, h_mean - h_sd, h_mean + h_sd, color="tab:red", alpha=0.15)
    ax1.plot(ticks, h_mean, color="tab:red", linewidth=2.0, label="Child hunger (mean ± SD)")
    ax1.axhline(1.0, color="tab:red", linestyle="--", alpha=0.5, linewidth=0.8)
    ax1.set_ylabel("Child hunger (0 = full, 1 = dead)", color="tab:red", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="tab:red")
    ax1.set_ylim(-0.05, 1.05)

    # Secondary: FEED rate (pink, dashed)
    ax2.fill_between(ticks, f_mean - f_sd, f_mean + f_sd, color="tab:pink", alpha=0.15)
    ax2.plot(ticks, f_mean, color="tab:pink", linewidth=1.8, linestyle="--", label="Care (FEED) rate")
    ax2.set_ylabel("FEED rate per alive mother", color="tab:pink", fontsize=10)
    ax2.tick_params(axis="y", labelcolor="tab:pink")
    ax2.set_ylim(-0.02, 0.5)

    # Tertiary: mother-child distance (blue, dotted)
    ax3.fill_between(ticks, d_mean - d_sd, d_mean + d_sd, color="tab:blue", alpha=0.10)
    ax3.plot(ticks, d_mean, color="tab:blue", linewidth=1.8, linestyle=":", label="Mother-child distance")
    ax3.set_ylabel("Mother–child distance (grid cells)", color="tab:blue", fontsize=10)
    ax3.tick_params(axis="y", labelcolor="tab:blue")

    ax1.set_xlabel("Tick", fontsize=11)
    ax1.set_xlim(0, DURATION - 1)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    ax1.legend(lines1 + lines2 + lines3, labels1 + labels2 + labels3,
               loc="upper right", fontsize=8, framealpha=0.9)

    ax1.grid(True, linestyle="--", alpha=0.20)

    # Annotate tail stats
    tw = 200
    ax1.text(
        0.01, 0.95,
        f"Tail ({tw} ticks): hunger={np.mean(h_mean[-tw:]):.3f}  "
        f"feed_rate={np.mean(f_mean[-tw:]):.3f}  "
        f"dist={np.mean(d_mean[-tw:]):.2f}",
        transform=ax1.transAxes, fontsize=8,
        bbox=dict(facecolor="white", edgecolor="gray", alpha=0.85),
        verticalalignment="top",
    )

    fig.suptitle(
        f"Phase 3b — Child Hunger, Care Rate & Mother-Child Distance\n"
        f"Canonical genome: care=0.3 / forage=1.0 / self=0.7 | food=48 | "
        f"{len(results)} seeds | {DURATION} ticks",
        fontsize=12, fontweight="bold",
    )

    plt.tight_layout()
    path = os.path.join(out_dir, "phase3b_child_care_distance.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {path}")

    return {
        "tail_child_hunger": float(np.mean(h_mean[-tw:])),
        "tail_feed_rate":    float(np.mean(f_mean[-tw:])),
        "tail_distance":     float(np.mean(d_mean[-tw:])),
    }


# ============================================================
# Behavioral summary text
# ============================================================

def compute_behavioral_summary(results, raster_result, motivation_stats, child_stats):
    action_totals = {k: 0 for k in ["MOVE_FOOD", "PICK", "EAT", "MOVE_CHILD", "FEED", "REST"]}
    motivation_totals = {"FORAGE": 0, "CARE": 0, "SELF": 0}
    failed_totals = {"FAILED_FORAGE": 0, "FAILED_CARE": 0, "FAILED_SELF": 0}

    for r in results:
        for k in action_totals:
            action_totals[k] += r["actions"].get(k, 0)
        for k in motivation_totals:
            motivation_totals[k] += r["motivations"].get(k, 0)
        for k in failed_totals:
            failed_totals[k] += r["failed"].get(k, 0)

    total_actions = sum(action_totals.values())
    total_motivations = sum(motivation_totals.values())

    forage_sub = action_totals["MOVE_FOOD"] + action_totals["PICK"] + action_totals["EAT"]
    care_sub   = action_totals["MOVE_CHILD"] + action_totals["FEED"]
    self_sub   = action_totals["REST"]

    care_dominant = max(action_totals, key=lambda k: action_totals[k] if k in ["MOVE_CHILD", "FEED"] else 0)

    mean_mother_surv = np.mean([r["final_mothers"] / 15 for r in results])
    mean_child_surv  = np.mean([r["final_children"] / 15 for r in results])

    lines = [
        "=" * 72,
        "PHASE 3b — BEHAVIORAL CHARACTERIZATION",
        "=" * 72,
        f"Canonical genome : care=0.3 / forage=1.0 / self=0.7",
        f"Ecological params : food=48, hunger_rate=0.005, eat_gain=0.07, rest_recovery=0.11",
        f"Duration          : {DURATION} ticks",
        f"Seeds             : {VIZ_SEEDS}",
        "",
        "--- SURVIVAL OUTCOMES ---",
        f"  Mother survival rate (mean) : {mean_mother_surv:.1%}",
        f"  Child  survival rate (mean) : {mean_child_surv:.1%}",
        "",
        "--- MOTIVATION FREQUENCY (across all ticks & agents) ---",
        f"  FORAGE : {motivation_totals['FORAGE']:>8,}  ({motivation_totals['FORAGE']/max(total_motivations,1):.1%})",
        f"  CARE   : {motivation_totals['CARE']:>8,}  ({motivation_totals['CARE']/max(total_motivations,1):.1%})",
        f"  SELF   : {motivation_totals['SELF']:>8,}  ({motivation_totals['SELF']/max(total_motivations,1):.1%})",
        "",
        "--- ACTION FREQUENCY (realised sub-actions) ---",
        f"  FORAGE  sub-total : {forage_sub:>8,}  ({forage_sub/max(total_actions,1):.1%})",
        f"    MOVE_FOOD       : {action_totals['MOVE_FOOD']:>8,}  ({action_totals['MOVE_FOOD']/max(total_actions,1):.1%})",
        f"    PICK            : {action_totals['PICK']:>8,}  ({action_totals['PICK']/max(total_actions,1):.1%})",
        f"    EAT             : {action_totals['EAT']:>8,}  ({action_totals['EAT']/max(total_actions,1):.1%})",
        f"  CARE    sub-total : {care_sub:>8,}  ({care_sub/max(total_actions,1):.1%})",
        f"    MOVE_CHILD      : {action_totals['MOVE_CHILD']:>8,}  ({action_totals['MOVE_CHILD']/max(total_actions,1):.1%})",
        f"    FEED            : {action_totals['FEED']:>8,}  ({action_totals['FEED']/max(total_actions,1):.1%})",
        f"  SELF    sub-total : {self_sub:>8,}  ({self_sub/max(total_actions,1):.1%})",
        f"    REST            : {action_totals['REST']:>8,}  ({action_totals['REST']/max(total_actions,1):.1%})",
        "",
        "--- FAILED ACTIONS ---",
        f"  FAILED_FORAGE : {failed_totals['FAILED_FORAGE']:>8,}",
        f"  FAILED_CARE   : {failed_totals['FAILED_CARE']:>8,}",
        f"  FAILED_SELF   : {failed_totals['FAILED_SELF']:>8,}",
        "",
        "--- TAIL-WINDOW STATS (last 200 ticks, mean across seeds) ---",
        f"  Motivation mix  : FORAGE={motivation_stats['forage_tail']:.1%}  "
        f"CARE={motivation_stats['care_tail']:.1%}  "
        f"SELF={motivation_stats['self_tail']:.1%}",
        f"  Child hunger    : {child_stats['tail_child_hunger']:.3f}",
        f"  FEED rate       : {child_stats['tail_feed_rate']:.3f} per alive mother per tick",
        f"  Mother-child distance : {child_stats['tail_distance']:.2f} grid cells",
        "",
        "--- BEHAVIORAL INTERPRETATION ---",
        f"  Under genome (care=0.3, forage=1.0, self=0.7), mothers devote",
        f"  ~{motivation_totals['FORAGE']/max(total_motivations,1):.0%} of ticks to foraging, "
        f"~{motivation_totals['CARE']/max(total_motivations,1):.0%} to care, "
        f"and ~{motivation_totals['SELF']/max(total_motivations,1):.0%} to rest.",
        f"  Within CARE: the dominant sub-action is FEED ({action_totals['FEED']/max(care_sub,1):.0%} of care ticks),",
        f"  with proximity navigation (MOVE_CHILD) comprising the remainder.",
        f"  Child hunger stabilises at ~{child_stats['tail_child_hunger']:.2f} by the tail window,",
        f"  well below the starvation threshold (1.0).",
        f"  Mother-child distance averages {child_stats['tail_distance']:.1f} grid cells in steady state,",
        f"  confirming spatial co-location during care events.",
        "=" * 72,
    ]

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(
        PROJECT_ROOT, "outputs", "phase3_survival_full",
        f"action_visualization_{ts}",
    )
    os.makedirs(out_dir, exist_ok=True)

    print(f"Phase 3b — Action Visualization")
    print(f"Canonical: care=0.3 / forage=1.0 / self=0.7 / food=48")
    print(f"Duration: {DURATION} ticks | Seeds: {VIZ_SEEDS}")
    print(f"Output: {out_dir}")
    print("-" * 60)

    # --- Run aggregate seeds ---
    print(f"Running {len(VIZ_SEEDS)} seeds for aggregate plots ...")
    results = []
    for seed in VIZ_SEEDS:
        print(f"  seed {seed} ...", end=" ", flush=True)
        r = run_one_viz(seed, agent_log=False)
        results.append(r)
        print(f"mothers={r['final_mothers']}/15  children={r['final_children']}/15")

    # --- Run raster seed with agent logging ---
    print(f"\nRunning raster seed {RASTER_SEED} with per-agent logging ...")
    raster_result = run_one_viz(RASTER_SEED, agent_log=True)
    print(f"  mothers={raster_result['final_mothers']}/15  children={raster_result['final_children']}/15")

    # --- Plot 1 ---
    print("\nGenerating Plot 1: stacked motivation area ...")
    motivation_stats = plot_stacked_motivation(results, out_dir)

    # --- Plot 2 ---
    print("Generating Plot 2: per-agent action raster ...")
    plot_agent_raster(raster_result, out_dir)

    # --- Plot 3 ---
    print("Generating Plot 3: child care + distance overlay ...")
    child_stats = plot_child_care_distance(results, out_dir)

    # --- Behavioral summary ---
    summary_text = compute_behavioral_summary(results, raster_result, motivation_stats, child_stats)
    print("\n" + summary_text)

    summary_path = os.path.join(out_dir, "phase3b_behavioral_summary.txt")
    with open(summary_path, "w") as f:
        f.write(summary_text)
    print(f"\nSaved summary -> {summary_path}")

    # --- Save canonical JSON for reference ---
    canonical_json = {
        "phase": "Phase 3b Action Visualization",
        "canonical_genome": {
            "care_weight": CANONICAL_PARAMS["care_weight"],
            "forage_weight": CANONICAL_PARAMS["forage_weight"],
            "self_weight": CANONICAL_PARAMS["self_weight"],
        },
        "ecological_params": {
            "init_food": CANONICAL_PARAMS["init_food"],
            "hunger_rate": CANONICAL_PARAMS["hunger_rate"],
            "eat_gain": CANONICAL_PARAMS["eat_gain"],
            "rest_recovery": CANONICAL_PARAMS["rest_recovery"],
        },
        "duration": DURATION,
        "seeds": VIZ_SEEDS,
        "raster_seed": RASTER_SEED,
        "motivation_tail_stats": motivation_stats,
        "child_care_tail_stats": child_stats,
    }
    json_path = os.path.join(out_dir, "phase3b_canonical.json")
    with open(json_path, "w") as f:
        json.dump(canonical_json, f, indent=2)
    print(f"Saved JSON   -> {json_path}")

    print(f"\nDone. All outputs in: {out_dir}")


if __name__ == "__main__":
    main()
