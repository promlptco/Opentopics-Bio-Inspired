"""Publication-quality LV Shannon plots.

Generates two publication-quality figures matching the reference style:

  fig_timeseries.png  — overlaid predator (red) / prey (blue) oscillations,
                        multiple gamma values shown as solid vs dashed lines,
                        ggplot-like gray background.

  fig_phase.png       — 2×2 panel of phase portraits (spiral LV attractors)
                        across four alpha×hunger combinations, colored by time.

Usage:
  python -m experiments.lv_ecology.lv_plot_pub
"""
from __future__ import annotations

import math
import random
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.collections import LineCollection

# ── Global academic sans-serif style ─────────────────────────────────────────
matplotlib.rcParams.update({
    "font.family"      : "serif",
    "font.serif"       : ["DejaVu Serif", "Times New Roman", "serif"],
    "figure.facecolor" : "white",
    "axes.facecolor"   : "white",
    "axes.spines.top"  : False,
    "axes.spines.right": False,
    "axes.grid"        : False,
    "grid.color"       : "#EBEBEB",
    "grid.linewidth"   : 0.8,
    "axes.linewidth"   : 0.8,
    "axes.edgecolor"   : "#AAAAAA",
    "xtick.direction"  : "out",
    "ytick.direction"  : "out",
    "xtick.major.size" : 4.0,
    "ytick.major.size" : 4.0,
    "xtick.color"      : "#555555",
    "ytick.color"      : "#555555",
    "font.size"        : 11,
    "axes.titlesize"   : 13,
    "axes.titleweight" : "bold",
    "axes.labelsize"   : 11,
    "xtick.labelsize"  : 10,
    "ytick.labelsize"  : 10,
    "legend.frameon"   : True,
    "legend.framealpha": 0.92,
    "legend.edgecolor" : "#DDDDDD",
    "legend.fontsize"  : 10,
})


def _academic_style(ax: plt.Axes) -> None:
    """Clean academic style for 2-D axes (matches sans-serif reference)."""
    ax.set_facecolor("white")
    ax.tick_params(direction="out", length=4, colors="#555555")
    ax.yaxis.grid(True,  color="#EBEBEB", linewidth=0.8, zorder=0)
    ax.xaxis.grid(False)
    for spine_name in ("left", "bottom"):
        ax.spines[spine_name].set_color("#AAAAAA")
        ax.spines[spine_name].set_linewidth(0.8)


def _academic_style_3d(ax) -> None:
    """Clean academic style for 3-D axes."""
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("#DDDDDD")
    ax.tick_params(labelsize=9, colors="#555555")
    ax.xaxis.line.set_color("#AAAAAA")
    ax.yaxis.line.set_color("#AAAAAA")
    ax.zaxis.line.set_color("#AAAAAA")


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.lv_ecology.lv_sweep import SimpleLVSim

# ── Output directory ──────────────────────────────────────────────────────────
OUT_DIR = PROJECT_ROOT / "outputs" / "lv_ecology" / f"pub_{datetime.now():%Y%m%d_%H%M%S}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Simulation knobs (best oscillating regime from sweep) ─────────────────────
ALPHA   = 0.05        # Shannon spawn scale
HUNGER  = 0.05        # energy lost per tick (predator mortality pressure)
TICKS   = 3000        # run length  (shows ~15 clean oscillation cycles)
SEED_A  = 42
SEED_B  = 43

# Hunger values to compare — hunger is analogous to predator death rate (γ in ODE LV).
# Higher hunger → agents die faster → longer oscillation period (like reference image).
GAMMAS        = [0.05, 0.07, 0.10]
GAMMA_LABELS  = [r"$h=0.05$", r"$h=0.07$", r"$h=0.10$"]
GAMMA_STYLES  = ["-", "--", ":"]       # solid, dashed, dotted
GAMMA_ALPHAS  = [1.0, 0.85, 0.70]

# Phase-portrait panel grid: (alpha, hunger) combos
PHASE_CONFIGS = [
    (0.05, 0.05, 0.002),
    (0.05, 0.10, 0.002),
    (0.02, 0.10, 0.002),
    (0.05, 0.05, 0.010),
]
PHASE_LABELS = [
    r"$\alpha=0.05,\ h=0.05,\ \gamma=0.002$",
    r"$\alpha=0.05,\ h=0.10,\ \gamma=0.002$",
    r"$\alpha=0.02,\ h=0.10,\ \gamma=0.002$",
    r"$\alpha=0.05,\ h=0.05,\ \gamma=0.010$",
]
N_CELLS = 30 * 30    # grid size for density conversion


# ══════════════════════════════════════════════════════════════════════════════
# Run helpers
# ══════════════════════════════════════════════════════════════════════════════

def run_sim(alpha: float, hunger: float, gamma: float, seed: int, ticks: int,
            record_every: int = 1):
    sim = SimpleLVSim(seed=seed, alpha=alpha, hunger=hunger, repro_cost=gamma,
                      record_every=record_every)
    food_ts, agt_ts = sim.run(ticks)
    return np.array(food_ts, dtype=float), np.array(agt_ts, dtype=float)


def gaussian_smooth(ts: np.ndarray, sigma: float = 80.0) -> np.ndarray:
    """Gaussian kernel smoothing (σ in samples). Falls back to numpy if scipy absent."""
    try:
        from scipy.ndimage import gaussian_filter1d
        return gaussian_filter1d(ts.astype(float), sigma=sigma)
    except ImportError:
        hw = int(4 * sigma)
        x = np.arange(-hw, hw + 1, dtype=float)
        kernel = np.exp(-x ** 2 / (2 * sigma ** 2))
        kernel /= kernel.sum()
        padded = np.pad(ts, hw, mode="edge")
        return np.convolve(padded, kernel, mode="valid")[: len(ts)]


def minmax_scale(ts: np.ndarray, lo: float = 0.0, hi: float = 9.0) -> np.ndarray:
    """Stretch series to [lo, hi] so troughs reach lo and peaks reach hi."""
    mn, mx = ts.min(), ts.max()
    if mx - mn < 1e-9:
        return np.full_like(ts, (lo + hi) / 2)
    return (ts - mn) / (mx - mn) * (hi - lo) + lo


# ══════════════════════════════════════════════════════════════════════════════
# Figure 1: publication-quality time series (matches reference style)
# ══════════════════════════════════════════════════════════════════════════════

def make_timeseries_fig() -> Path:
    print("Running simulations for time-series figure ...")
    # Record every tick (record_every=1) for smooth curves.
    # Each oscillation cycle is ~300–500 ticks; Gaussian σ=50 removes within-tick
    # stochasticity while preserving the cycle shape.
    FIXED_GAMMA = 0.002
    SKIP_TICKS  = 800    # burn-in to reach sustained oscillation
    SHOW_TICKS  = 3500   # display window (≈8–12 clean cycles)
    SIGMA       = 80.0   # Gaussian smoothing sigma (ticks)

    data: list[tuple[np.ndarray, np.ndarray, str, str, float]] = []
    TOTAL_TICKS = SKIP_TICKS + SHOW_TICKS + 200   # enough data for full window
    for hunger_val, label, ls, alpha_v in zip(GAMMAS, GAMMA_LABELS, GAMMA_STYLES, GAMMA_ALPHAS):
        food, agt = run_sim(ALPHA, hunger_val, FIXED_GAMMA, SEED_A, TOTAL_TICKS,
                            record_every=1)
        data.append((food, agt, label, ls, alpha_v))

    skip_n = SKIP_TICKS
    show_n = SHOW_TICKS
    tick_axis = np.arange(show_n)   # x-axis in ticks (0 … SHOW_TICKS-1)

    # ── colour palette ────────────────────────────────────────────────────────
    PREY_COLOR = "#4472C4"      # blue  (food)
    PRED_COLOR = "#C0504D"      # red   (agents)
    BG_COLOR   = "#EBEBEB"

    fig, ax = plt.subplots(figsize=(11, 5.5))
    fig.patch.set_facecolor("white")

    # ggplot-like background
    ax.set_facecolor(BG_COLOR)
    ax.grid(color="white", linewidth=0.8, zorder=0)
    for sp in ax.spines.values():
        sp.set_visible(False)

    for food, agt, label, ls, al in data:
        food_window = food[skip_n: skip_n + show_n]
        agt_window  = agt[skip_n:  skip_n + show_n]

        # Gaussian smooth → min-max stretch to [0,9] so troughs near 0, peaks at 9
        food_s = minmax_scale(gaussian_smooth(food_window, SIGMA))
        agt_s  = minmax_scale(gaussian_smooth(agt_window,  SIGMA))

        ax.plot(tick_axis, food_s, color=PREY_COLOR, linestyle=ls,
                linewidth=1.8, alpha=al, zorder=2)
        ax.plot(tick_axis, agt_s,  color=PRED_COLOR, linestyle=ls,
                linewidth=1.8, alpha=al, zorder=2)

    ax.set_xlabel("Time (ticks)", fontsize=12, labelpad=6)
    ax.set_ylabel("Population density\n(min–max normalised, [0–9])", fontsize=12, labelpad=6)
    ax.set_title(
        "Shannon Lotka–Volterra predator–prey model\n"
        r"Increasing hunger rate $h$ leads to longer oscillation period"
        r"$\quad(\alpha=0.05,\ \gamma=0.002)$",
        fontsize=12, fontweight="bold", pad=10,
    )
    ax.set_xlim(tick_axis[0], tick_axis[-1])
    ax.set_ylim(-0.3, 9.5)

    # ── Legend: Species + gamma ───────────────────────────────────────────────
    prey_patch = mlines.Line2D([], [], color=PREY_COLOR, linewidth=2.0, label="Prey  (food)")
    pred_patch = mlines.Line2D([], [], color=PRED_COLOR, linewidth=2.0, label="Predator (agents)")
    species_legend = ax.legend(
        handles=[prey_patch, pred_patch],
        loc="upper left", fontsize=10, framealpha=0.85,
        title="Species", title_fontsize=10,
    )
    ax.add_artist(species_legend)

    gamma_handles = [
        mlines.Line2D([], [], color="black", linestyle=ls, linewidth=1.8, label=lbl)
        for lbl, ls in zip(GAMMA_LABELS, GAMMA_STYLES)
    ]
    ax.legend(
        handles=gamma_handles,
        loc="upper right", fontsize=10, framealpha=0.85,
        title=r"Hunger rate $h$", title_fontsize=10,
    )

    fig.tight_layout()
    out_path = OUT_DIR / "fig_timeseries.png"
    fig.savefig(str(out_path), dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# Figure 2: 2×2 phase portrait panel (matches reference panel style)
# ══════════════════════════════════════════════════════════════════════════════

def make_phase_fig() -> Path:
    """2×2 phase-portrait panel — clean academic style, plasma colormap."""
    print("Running simulations for phase-portrait figure ...")

    cmap = plt.cm.plasma
    START_COLOR = "#1A73E8"   # blue filled circle
    END_COLOR   = "#D93025"   # red filled circle

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "Shannon Lotka–Volterra  —  Phase Portraits\n"
        r"$\dot{x}=$ Shannon spawn $-$ consumption"
        r"$\quad\dot{y}=$ reproduction $-$ starvation",
        fontsize=13, fontweight="bold",
    )
    panel_labels = ["(a)", "(b)", "(c)", "(d)"]

    for ax, (alpha, hunger, gamma), param_label, panel_lbl in zip(
        axes.flat, PHASE_CONFIGS, PHASE_LABELS, panel_labels
    ):
        food_a, agt_a = run_sim(alpha, hunger, gamma, SEED_A, TICKS, record_every=10)
        food_b, agt_b = run_sim(alpha, hunger, gamma, SEED_B, TICKS, record_every=10)

        n      = len(food_a)
        t_vals = np.linspace(0, 1, n)

        # Both seeds coloured by time (plasma); seed B thinner + more transparent
        for food, agt, al, lw in (
            (food_a, agt_a, 0.82, 1.4),
            (food_b, agt_b, 0.36, 0.8),
        ):
            pts  = np.column_stack([food, agt])
            segs = np.stack([pts[:-1], pts[1:]], axis=1)
            lc   = LineCollection(segs, cmap=cmap, alpha=al, linewidth=lw)
            lc.set_array(t_vals[:-1])
            lc.set_clim(0, 1)
            ax.add_collection(lc)

        # Start / end — small filled circles (both seeds)
        ax.plot(food_a[0],  agt_a[0],  "o", ms=5, color=START_COLOR,
                zorder=6, label="Start")
        ax.plot(food_b[0],  agt_b[0],  "o", ms=5, color=START_COLOR, zorder=6)
        ax.plot(food_a[-1], agt_a[-1], "o", ms=5, color=END_COLOR,
                zorder=6, label="End")
        ax.plot(food_b[-1], agt_b[-1], "o", ms=5, color=END_COLOR,   zorder=6)

        food_all = np.concatenate([food_a, food_b])
        agt_all  = np.concatenate([agt_a,  agt_b])
        pad_f = max((food_all.max() - food_all.min()) * 0.04, 2.0)
        pad_a = max((agt_all.max()  - agt_all.min())  * 0.04, 1.0)
        ax.set_xlim(max(0, food_all.min() - pad_f), food_all.max() + pad_f)
        ax.set_ylim(max(0, agt_all.min()  - pad_a), agt_all.max()  + pad_a)

        _academic_style(ax)
        ax.set_xlabel("Food count",  fontsize=10)
        ax.set_ylabel("Agent count", fontsize=10)
        ax.set_title(f"{panel_lbl}  {param_label}", fontsize=10)
        ax.legend(fontsize=9, loc="upper left", framealpha=0.92,
                  handlelength=0.6, markerscale=1.2)

    # Shared colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, TICKS))
    sm.set_array([])
    fig.subplots_adjust(right=0.87, hspace=0.35, wspace=0.28, top=0.88, bottom=0.07)
    cax = fig.add_axes([0.90, 0.15, 0.018, 0.65])
    cb  = fig.colorbar(sm, cax=cax)
    cb.set_label("Simulation tick", fontsize=10)
    cb.ax.tick_params(labelsize=9)

    out_path = OUT_DIR / "fig_phase.png"
    fig.savefig(str(out_path), dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# Figure 3: 3D phase portrait on Shannon entropy surface
# ══════════════════════════════════════════════════════════════════════════════

def make_3d_entropy_fig() -> Path:
    """3D scatter: food density × agent density × Shannon H(p).

    Sweeps 40 initial conditions (8 food fractions × 5 agent counts) to fill
    the entropy dome and show convergence to the same limit cycle.
    Color = normalised time per trajectory (dark=start, bright=converged).
    """
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3d projection
    from experiments.lv_ecology.lv_sweep import SimpleLVSim as _Sim

    print("Running simulations for 3D entropy figure (initial-condition sweep) ...")

    FIXED_ALPHA  = 0.05
    FIXED_HUNGER = 0.05
    FIXED_GAMMA  = 0.002
    TOTAL_TICKS  = 3500
    RECORD_EVERY = 3          # keep point count manageable (~1200 pts / traj)
    SEED         = 42

    # 8 food fractions × 5 agent counts = 40 trajectories
    FOOD_FRACS   = [0.10, 0.20, 0.30, 0.368, 0.50, 0.60, 0.75, 0.90]
    AGENT_COUNTS = [5, 10, 20, 35, 55]

    all_p, all_q, all_H, all_t = [], [], [], []

    n_total = len(FOOD_FRACS) * len(AGENT_COUNTS)
    for i, food_frac in enumerate(FOOD_FRACS):
        for j, n_agents in enumerate(AGENT_COUNTS):
            idx = i * len(AGENT_COUNTS) + j + 1
            print(f"  [{idx}/{n_total}]  food_frac={food_frac:.3f}  agents={n_agents}")
            sim = _Sim(
                seed=SEED,
                alpha=FIXED_ALPHA,
                hunger=FIXED_HUNGER,
                repro_cost=FIXED_GAMMA,
                init_food_frac=food_frac,
                init_agents=n_agents,
                record_every=RECORD_EVERY,
            )
            food_ts, agt_ts = sim.run(TOTAL_TICKS)
            food_ts = np.array(food_ts, float)
            agt_ts  = np.array(agt_ts,  float)

            p = food_ts / N_CELLS
            q = agt_ts  / N_CELLS
            H = -np.clip(p, 1e-10, 1.0) * np.log(np.clip(p, 1e-10, 1.0))
            t = np.linspace(0.0, 1.0, len(p))   # 0=start, 1=end per trajectory

            all_p.append(p)
            all_q.append(q)
            all_H.append(H)
            all_t.append(t)

    all_p = np.concatenate(all_p)
    all_q = np.concatenate(all_q)
    all_H = np.concatenate(all_H)
    all_t = np.concatenate(all_t)

    # Save trajectory data for re-plotting without re-running simulations
    npz_path = OUT_DIR / "fig_3d_entropy_data.npz"
    np.savez_compressed(str(npz_path), p=all_p, q=all_q, H=all_H, t=all_t)
    print(f"  Data saved -> {npz_path}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(10, 8))
    fig.patch.set_facecolor("white")
    ax  = fig.add_subplot(111, projection="3d")
    _academic_style_3d(ax)

    ax.scatter(
        all_p, all_q, all_H,
        c=all_t, cmap="plasma",
        vmin=0.0, vmax=1.0,
        s=0.9, alpha=0.35,
        depthshade=True,
    )

    # Theoretical dome projected onto q=0 for reference
    p_ref = np.linspace(0.005, 0.995, 500)
    H_ref = -p_ref * np.log(p_ref)
    ax.plot(p_ref, np.zeros_like(p_ref), H_ref,
            color="#333333", linewidth=1.0, alpha=0.55, zorder=10,
            label=r"$H(p)=-p\ln p$  (q = 0 projection)")

    ax.set_xlabel(r"Food density  $p$", fontsize=10, labelpad=8)
    ax.set_ylabel(r"Agent density  $q$", fontsize=10, labelpad=8)
    ax.set_zlabel(r"Shannon  $H(p) = -p\ln p$", fontsize=10, labelpad=8)
    ax.set_title(
        "Shannon LV  —  Basin of Attraction (3D)\n"
        r"40 initial conditions converging to the same limit cycle"
        "\n" r"$\alpha=0.05,\quad h=0.05,\quad \gamma=0.002$",
        fontsize=12, fontweight="bold", pad=14,
    )

    ax.view_init(elev=25, azim=135)
    ax.legend(fontsize=9, loc="upper left")

    sm = plt.cm.ScalarMappable(cmap="plasma", norm=plt.Normalize(0, 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.50, aspect=15, pad=0.08)
    cbar.set_ticks([0.0, 0.5, 1.0])
    cbar.set_ticklabels(["Start", "Mid", "Converged"])
    cbar.set_label("Trajectory progress", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    fig.tight_layout()
    out_path = OUT_DIR / "fig_3d_entropy.png"
    fig.savefig(str(out_path), dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# Figure 4: Takens' delay embedding  food(t) × food(t-τ) × food(t-2τ)
# ══════════════════════════════════════════════════════════════════════════════

def make_3d_delay_embedding_fig() -> Path:
    """Reconstruct the LV attractor from food counts alone via Takens' theorem.

    Coordinates:
        x = food(t)        y = food(t − τ)        z = food(t − 2τ)
    τ = 100 ticks  ≈  ¼ oscillation period  → maximises axis spread.
    One long trajectory (20 000 ticks) fills the attractor surface continuously.
    """
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    print("Running simulation for Takens delay-embedding figure ...")

    FIXED_ALPHA  = 0.05
    FIXED_HUNGER = 0.05
    FIXED_GAMMA  = 0.002
    TOTAL_TICKS  = 20_000
    SKIP_TICKS   = 3_000   # discard startup transient (longer to cover all seeds)
    SEEDS        = list(range(42, 72))   # 30 seeds
    TAU          = 100     # lag in ticks (record_every=1 so 1 sample = 1 tick)

    all_x, all_y, all_z = [], [], []

    for seed in SEEDS:
        print(f"  seed={seed} ...")
        food, _ = run_sim(FIXED_ALPHA, FIXED_HUNGER, FIXED_GAMMA,
                          seed, TOTAL_TICKS, record_every=1)
        food = np.array(food, float)[SKIP_TICKS:]

        # Smooth before embedding — removes tick-level ABM noise while
        # preserving the oscillation cycle needed for Takens' reconstruction.
        food = gaussian_smooth(food, sigma=20.0)

        n = len(food)
        all_x.append(food[2 * TAU:] / N_CELLS)          # food(t)
        all_y.append(food[TAU : n - TAU] / N_CELLS)     # food(t − τ)
        all_z.append(food[: n - 2 * TAU] / N_CELLS)     # food(t − 2τ)

    x_d = np.concatenate(all_x)
    y_d = np.concatenate(all_y)
    z_d = np.concatenate(all_z)

    # Remove points where any seed escaped to the extinction/flood regime
    # (food density > 0.5 means agents died and food is unchecked)
    mask = (x_d < 0.5) & (y_d < 0.5) & (z_d < 0.5)
    x_d, y_d, z_d = x_d[mask], y_d[mask], z_d[mask]
    print(f"  kept {mask.sum():,} / {len(mask):,} points after attractor filter")

    # Save filtered embedding data for re-plotting without re-running simulations
    npz_path = OUT_DIR / "fig_3d_delay_embedding_data.npz"
    np.savez_compressed(str(npz_path), x=x_d, y=y_d, z=z_d)
    print(f"  Data saved -> {npz_path}")

    # ── Plot — colour by z = food(t−2τ) to reveal height layers ─────────────
    fig = plt.figure(figsize=(10, 8))
    fig.patch.set_facecolor("white")
    ax  = fig.add_subplot(111, projection="3d")
    _academic_style_3d(ax)

    ax.scatter(
        x_d, y_d, z_d,
        c=z_d, cmap="plasma",
        vmin=z_d.min(), vmax=z_d.max(),
        s=2.0, alpha=0.35,
        depthshade=True,
    )

    ax.set_xlabel(r"Food$(t)\ /\ N_\mathrm{cells}$",       fontsize=10, labelpad=8)
    ax.set_ylabel(r"Food$(t-\tau)\ /\ N_\mathrm{cells}$",  fontsize=10, labelpad=8)
    ax.set_zlabel(r"Food$(t-2\tau)\ /\ N_\mathrm{cells}$", fontsize=10, labelpad=8)
    ax.set_title(
        "Takens Delay Embedding  —  Food Attractor\n"
        r"$x=p(t),\quad y=p(t-\tau),\quad z=p(t-2\tau)$"
        r"$\quad \tau=100\ \mathrm{ticks}$"
        "\n"
        r"$\alpha=0.05,\quad h=0.05,\quad \gamma=0.002$"
        r"$\quad 30\ \mathrm{seeds}\times 20\,000\ \mathrm{ticks}$",
        fontsize=12, fontweight="bold", pad=14,
    )

    ax.view_init(elev=30, azim=45)

    sm = plt.cm.ScalarMappable(cmap="plasma",
                               norm=plt.Normalize(z_d.min(), z_d.max()))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.50, aspect=15, pad=0.08)
    cbar.set_label(r"Food$(t-2\tau)\ /\ N_\mathrm{cells}$", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    fig.tight_layout()
    out_path = OUT_DIR / "fig_3d_delay_embedding.png"
    fig.savefig(str(out_path), dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# Figure 5 + 6: 30-seed time series & phase portrait (academic clean style)
# ══════════════════════════════════════════════════════════════════════════════

def make_multiseed_figs(out_dir: Path | None = None) -> tuple[Path, Path, Path]:
    """Run 30 seeds × 20 000 ticks once; produce three figures.

    Returns (timeseries_20k, timeseries_1k, phase_portrait).
    """
    if out_dir is None:
        out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    FIXED_ALPHA  = 0.05
    FIXED_HUNGER = 0.05
    FIXED_GAMMA  = 0.002
    TOTAL_TICKS  = 20_000
    SEEDS        = list(range(42, 72))   # 30 seeds
    RECORD_EVERY = 5                     # → 4 000 pts/seed
    N_1K         = 1_000 // RECORD_EVERY # 200 pts = first 1 000 ticks

    FOOD_COLOR   = "#2ca02c"   # forest green
    AGT_COLOR    = "#1f77b4"   # steel blue
    START_COLOR  = "#1A73E8"   # blue circles = start
    END_COLOR    = "#D93025"   # red circles  = end

    from matplotlib.ticker import FuncFormatter
    _kfmt = FuncFormatter(
        lambda x, _: f"{int(x / 1000)}k" if x >= 1000 else str(int(x))
    )

    def _draw_ts(ax1: plt.Axes, ax2: plt.Axes,
                 food_arr: np.ndarray, agt_arr: np.ndarray,
                 ticks: np.ndarray) -> None:
        m_f = food_arr.mean(0);  s_f = food_arr.std(0)
        m_a = agt_arr.mean(0);   s_a = agt_arr.std(0)
        gf  = float(m_f.mean()); ga  = float(m_a.mean())

        for food in food_arr:
            ax1.plot(ticks, food, color=FOOD_COLOR, alpha=0.13,
                     linewidth=0.5, rasterized=True)
        ax1.fill_between(ticks, m_f - s_f, m_f + s_f,
                         color=FOOD_COLOR, alpha=0.18, label=r"Mean $\pm$ 1 SD")
        ax1.plot(ticks, m_f, color=FOOD_COLOR, linewidth=2.2,
                 label="Mean (30 seeds)")
        ax1.axhline(gf, color=FOOD_COLOR, linestyle="--", linewidth=1.0,
                    alpha=0.50, label=f"Grand mean = {gf:.0f}")

        for agt in agt_arr:
            ax2.plot(ticks, agt, color=AGT_COLOR, alpha=0.13,
                     linewidth=0.5, rasterized=True)
        ax2.fill_between(ticks, m_a - s_a, m_a + s_a,
                         color=AGT_COLOR, alpha=0.18, label=r"Mean $\pm$ 1 SD")
        ax2.plot(ticks, m_a, color=AGT_COLOR, linewidth=2.2,
                 label="Mean (30 seeds)")
        ax2.axhline(ga, color=AGT_COLOR, linestyle="--", linewidth=1.0,
                    alpha=0.50, label=f"Grand mean = {ga:.1f}")

        for ax, ylabel in ((ax1, "Food count"), (ax2, "Agent count")):
            _academic_style(ax)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.legend(fontsize=9, framealpha=0.92, loc="upper right",
                      handlelength=1.6)
        ax2.set_xlabel("Simulation tick", fontsize=11)
        ax1.set_xlim(ticks[0], ticks[-1])
        ax2.set_xlim(ticks[0], ticks[-1])

    # ── Run simulations ───────────────────────────────────────────────────────
    print("Running 30-seed simulations (20 000 ticks, record_every=5) ...")
    all_food, all_agt = [], []
    for seed in SEEDS:
        print(f"  seed={seed} ...")
        food, agt = run_sim(FIXED_ALPHA, FIXED_HUNGER, FIXED_GAMMA,
                            seed, TOTAL_TICKS, record_every=RECORD_EVERY)
        all_food.append(food)
        all_agt.append(agt)

    all_food  = np.array(all_food, float)   # (30, 4000)
    all_agt   = np.array(all_agt,  float)
    tick_axis = np.arange(all_food.shape[1]) * RECORD_EVERY

    # ── Figure 5a: 20k-tick time series ──────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
                                    gridspec_kw={"hspace": 0.08})
    _draw_ts(ax1, ax2, all_food, all_agt, tick_axis)
    ax2.xaxis.set_major_formatter(_kfmt)
    fig.suptitle(
        "LV Shannon  —  30-Seed Oscillation\n"
        r"$\alpha = 0.05\quad h = 0.05\quad \gamma_r = 0.002"
        r"\quad 30\ \mathrm{seeds}\times 20{,}000\ \mathrm{ticks}$",
        fontsize=13, fontweight="bold", y=1.02,
    )
    ts_path = out_dir / "fig_multiseed_timeseries.png"
    fig.savefig(str(ts_path), dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {ts_path}")

    # ── Figure 5b: 1k-tick time series (transient + early oscillation) ───────
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True,
                                    gridspec_kw={"hspace": 0.08})
    _draw_ts(ax1, ax2,
             all_food[:, :N_1K], all_agt[:, :N_1K], tick_axis[:N_1K])
    fig.suptitle(
        "LV Shannon  —  30-Seed Transient  (ticks 0–1 000)\n"
        r"$\alpha = 0.05\quad h = 0.05\quad \gamma_r = 0.002"
        r"\quad 30\ \mathrm{seeds}$",
        fontsize=13, fontweight="bold", y=1.02,
    )
    ts1k_path = out_dir / "fig_multiseed_timeseries_1k.png"
    fig.savefig(str(ts1k_path), dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {ts1k_path}")

    # ── Figure 6: multi-seed phase portrait with start / end clusters ────────
    cmap   = plt.cm.plasma
    norm   = plt.Normalize(0, TOTAL_TICKS)
    t_vals = np.linspace(0, TOTAL_TICKS, all_food.shape[1])

    fig2, ax = plt.subplots(figsize=(9, 8))
    for food, agt in zip(all_food, all_agt):
        pts  = np.column_stack([food, agt])
        segs = np.stack([pts[:-1], pts[1:]], axis=1)
        lc   = LineCollection(segs, cmap=cmap, norm=norm,
                              alpha=0.22, linewidth=0.65, rasterized=True)
        lc.set_array(t_vals[:-1])
        ax.add_collection(lc)

    # All-30-seed start and end clusters (small filled circles)
    ax.scatter(all_food[:, 0], all_agt[:, 0],
               s=14, color=START_COLOR, alpha=0.85, zorder=6,
               label="Start  (t = 0)")
    ax.scatter(all_food[:, -1], all_agt[:, -1],
               s=14, color=END_COLOR,   alpha=0.85, zorder=6,
               label="End  (t = 20 000)")

    ax.autoscale_view()
    _academic_style(ax)
    ax.set_xlabel("Food count",  fontsize=11)
    ax.set_ylabel("Agent count", fontsize=11)
    ax.set_title(
        "Phase Portrait (Food vs Agents)  —  LV Shannon\n"
        r"$\alpha = 0.05\quad h = 0.05\quad \gamma_r = 0.002"
        r"\quad 30\ \mathrm{seeds}\times 20{,}000\ \mathrm{ticks}$",
        fontsize=13, fontweight="bold",
    )
    ax.legend(fontsize=10, framealpha=0.92, loc="upper right",
              markerscale=1.4, handlelength=0.6)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig2.colorbar(sm, ax=ax, shrink=0.85, aspect=20)
    cbar.set_label("Simulation tick", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    fig2.tight_layout()
    pp_path = out_dir / "fig_multiseed_phase.png"
    fig2.savefig(str(pp_path), dpi=180, bbox_inches="tight")
    plt.close(fig2)
    print(f"Saved -> {pp_path}")

    return ts_path, ts1k_path, pp_path


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse as _ap
    _parser = _ap.ArgumentParser()
    _parser.add_argument(
        "--out-dir", type=Path, default=None,
        help="Directory for output figures (default: auto-timestamped)",
    )
    _parser.add_argument(
        "--only-multiseed", action="store_true",
        help="Skip fig1–4; generate only the 30-seed figures",
    )
    _args = _parser.parse_args()

    target = Path(_args.out_dir) if _args.out_dir else OUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    print(f"\n[lv_plot_pub]  output -> {target}\n")

    if not _args.only_multiseed:
        p2 = make_phase_fig()
        p3 = make_3d_entropy_fig()
        p4 = make_3d_delay_embedding_fig()
        print(f"\nBase figures saved to: {OUT_DIR}")
        for p in (p2, p3, p4):
            print(f"  {p.name}")

    p5, p6, p7 = make_multiseed_figs(target)
    print(f"\nMulti-seed figures saved to: {target}")
    print(f"  {p5.name}")
    print(f"  {p6.name}")
    print(f"  {p7.name}")
