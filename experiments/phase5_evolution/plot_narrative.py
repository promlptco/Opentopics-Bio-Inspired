"""Narrative presentation figure — Simple Food → Shannon Food → Evolution.

Three-panel landscape figure telling the causal story:

  Panel A  (Block 1 — LV Ecology)
      Left sub-panel : α = 0.0  simple food — food depletes, agents crash.
      Right sub-panel: α = 0.05 Shannon food — sustained predator–prey oscillations.

  Panel B  (Block 2/3 — Population Survival)
      Mean + SD population (mothers) over ticks for all three α conditions.
      Extinction earlier under simple food; Shannon food prolongs evolution.

  Panel C  (Block 2/3 — Genome Care Evolution)
      Mean + SD genome-care weight over ticks.
      Only Shannon conditions show directional selection above neutral (1/3).

Usage:
    python -m experiments.phase5_evolution.plot_narrative
    python -m experiments.phase5_evolution.plot_narrative --out-dir outputs/presentation
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ── project root ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.lv_ecology.lv_sweep import SimpleLVSim

# ── academic style (serif, per project convention) ────────────────────────────
matplotlib.rcParams.update({
    "font.family"       : "serif",
    "font.serif"        : ["DejaVu Serif", "Times New Roman", "serif"],
    "figure.facecolor"  : "white",
    "axes.facecolor"    : "white",
    "axes.spines.top"   : False,
    "axes.spines.right" : False,
    "axes.linewidth"    : 0.9,
    "axes.edgecolor"    : "#888888",
    "xtick.direction"   : "out",
    "ytick.direction"   : "out",
    "xtick.major.size"  : 4.0,
    "ytick.major.size"  : 4.0,
    "xtick.color"       : "#555555",
    "ytick.color"       : "#555555",
    "xtick.labelsize"   : 9,
    "ytick.labelsize"   : 9,
    "font.size"         : 10,
    "axes.titlesize"    : 11,
    "axes.titleweight"  : "bold",
    "axes.labelsize"    : 10,
    "legend.frameon"    : True,
    "legend.framealpha" : 0.92,
    "legend.edgecolor"  : "#DDDDDD",
    "legend.fontsize"   : 8.5,
})

# ── colour palette (consistent across all panels) ─────────────────────────────
C_SIMPLE  = "#888888"   # α = 0.0  — simple food (grey)
C_B2      = "#2196F3"   # α = 0.01 — Block 2 Shannon (blue)
C_B3      = "#E65100"   # α = 0.05 — Block 3 Shannon (deep orange)
C_FOOD    = "#4CAF50"   # food line in LV panels (green)
C_NEUTRAL = "#C62828"   # neutral 1/3 reference (dark red)

# ── run directories ───────────────────────────────────────────────────────────
EVO_ROOT = PROJECT_ROOT / "outputs" / "phase5_evolution"
RUNS = {
    "simple": EVO_ROOT / "block2_simple_mut_on_plast_off",
    "b2"    : EVO_ROOT / "block2_main_mut_on_plast_off",
    "b3"    : EVO_ROOT / "block3_shannon05_mut_on_plast_off",
}
LABELS = {
    "simple": r"Simple food  ($\alpha = 0.00$)",
    "b2"    : r"Shannon B2   ($\alpha = 0.01$)",
    "b3"    : r"Shannon B3   ($\alpha = 0.05$)",
}
COLORS = {"simple": C_SIMPLE, "b2": C_B2, "b3": C_B3}

# ── LV ecology simulation settings ───────────────────────────────────────────
LV_TICKS    = 3000
LV_SEED     = 42
LV_HUNGER   = 0.05
LV_REPRO    = 0.002
LV_SKIP     = 200   # burn-in ticks (not shown)
LV_SMOOTH   = 60    # Gaussian smoothing σ (ticks)
N_CELLS     = 30 * 30


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _smooth(ts: np.ndarray, sigma: float) -> np.ndarray:
    try:
        from scipy.ndimage import gaussian_filter1d
        return gaussian_filter1d(ts.astype(float), sigma=sigma)
    except ImportError:
        hw = int(4 * sigma)
        x = np.arange(-hw, hw + 1, dtype=float)
        k = np.exp(-x ** 2 / (2 * sigma ** 2)); k /= k.sum()
        return np.convolve(np.pad(ts, hw, mode="edge"), k, mode="valid")[: len(ts)]


def _run_lv(alpha: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (ticks, food_frac, agent_density) after burn-in."""
    sim = SimpleLVSim(
        seed=LV_SEED, alpha=alpha,
        hunger=LV_HUNGER, repro_cost=LV_REPRO,
        record_every=1,
    )
    food_ts, agt_ts = sim.run(LV_TICKS)
    food_arr = np.array(food_ts, dtype=float)
    agt_arr  = np.array(agt_ts,  dtype=float)
    ticks    = np.arange(len(food_arr))
    # trim burn-in
    food_arr = food_arr[LV_SKIP:]
    agt_arr  = agt_arr[LV_SKIP:]
    ticks    = ticks[LV_SKIP:] - LV_SKIP
    return ticks, food_arr / N_CELLS, agt_arr / N_CELLS


def _load_evo(key: str) -> pd.DataFrame:
    path = RUNS[key] / "snapshots.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    return pd.read_csv(path)


def _agg(df: pd.DataFrame, col: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (ticks, mean, std) aggregated across seeds."""
    g = df.groupby("tick")[col].agg(["mean", "std"]).reset_index().sort_values("tick")
    g["std"] = g["std"].fillna(0.0)
    return g["tick"].values, g["mean"].values, g["std"].values


# ══════════════════════════════════════════════════════════════════════════════
# Panel helpers
# ══════════════════════════════════════════════════════════════════════════════

FIG_W, FIG_H = 9, 5.5   # size for each standalone figure


def _make_lv_fig(alpha: float, title: str) -> plt.Figure:
    """Build a standalone LV ecology figure."""
    ticks, food_frac, agt_dens = _run_lv(alpha)
    food_sm = _smooth(food_frac, LV_SMOOTH)
    agt_sm  = _smooth(agt_dens,  LV_SMOOTH)

    def _norm(a):
        mn, mx = a.min(), a.max()
        return (a - mn) / (mx - mn + 1e-12)

    agent_color = C_SIMPLE if alpha == 0.0 else C_B3

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.plot(ticks, _norm(food_sm), color=C_FOOD,    linewidth=2.0,
            label="Food density",  zorder=3)
    ax.plot(ticks, _norm(agt_sm),  color=agent_color,
            linewidth=2.0, label="Agent density", zorder=3)

    ax.set_title(title, pad=8)
    ax.set_xlabel("Simulation tick")
    ax.set_ylabel("Normalised density")
    ax.set_ylim(-0.08, 1.15)
    ax.set_xlim(0, ticks[-1])
    ax.legend(loc="upper right", fontsize=9)

    regime = "Unsustainable" if alpha == 0.0 else "Oscillating"
    color  = "#B71C1C" if alpha == 0.0 else "#1B5E20"
    ax.text(0.98, 0.06, regime, transform=ax.transAxes,
            ha="right", va="bottom", fontsize=10, color=color,
            fontstyle="italic", fontweight="bold")

    fig.tight_layout()
    return fig


def _make_pop_fig(dfs: dict) -> plt.Figure:
    """Build a standalone population survival figure."""
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for key in ("simple", "b2", "b3"):
        t, mu, sd = _agg(dfs[key], "n_mothers")
        lo = np.clip(mu - sd, 0, None)
        hi = mu + sd
        ax.fill_between(t, lo, hi, color=COLORS[key], alpha=0.18, zorder=2)
        ax.plot(t, mu, color=COLORS[key], linewidth=2.2,
                label=LABELS[key], zorder=3)

    ax.set_xlabel("Simulation tick")
    ax.set_ylabel("Mean mothers (population)")
    ax.set_title("Population Survival", pad=8)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    return fig


def _make_care_fig(dfs: dict) -> plt.Figure:
    """Build a standalone genome care evolution figure."""
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    ax.axhline(1 / 3, color=C_NEUTRAL, linewidth=1.4, linestyle="--",
               alpha=0.85, zorder=2, label="Neutral (1/3)")

    for key in ("simple", "b2", "b3"):
        t, mu, sd = _agg(dfs[key], "mean_genome_care")
        lo = np.clip(mu - sd, 0, 1)
        hi = np.clip(mu + sd, 0, 1)
        ax.fill_between(t, lo, hi, color=COLORS[key], alpha=0.18, zorder=3)
        ax.plot(t, mu, color=COLORS[key], linewidth=2.2,
                label=LABELS[key], zorder=4)

    ax.set_xlabel("Simulation tick")
    ax.set_ylabel("Mean genome care weight")
    ax.set_title("Genome Care Evolution", pad=8)
    ax.set_ylim(0.0, 0.65)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Main — save 4 separate figures
# ══════════════════════════════════════════════════════════════════════════════

def make_figure(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading evolution data ...")
    dfs = {k: _load_evo(k) for k in ("simple", "b2", "b3")}

    print("Running LV ecology simulations ...")

    figures = [
        (
            _make_lv_fig(
                alpha=0.0,
                title=r"Block 1 — Simple food ($\alpha = 0.0$): food depletes, agents crash",
            ),
            "fig_A_lv_simple.png",
        ),
        (
            _make_lv_fig(
                alpha=0.05,
                title=r"Block 1 — Shannon food ($\alpha = 0.05$): sustained predator–prey oscillations",
            ),
            "fig_B_lv_shannon.png",
        ),
        (_make_pop_fig(dfs),  "fig_C_population_survival.png"),
        (_make_care_fig(dfs), "fig_D_genome_care.png"),
    ]

    for fig, fname in figures:
        path = out_dir / fname
        fig.savefig(path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved -> {path}")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Narrative figure: Simple Food → Shannon Food → Evolution"
    )
    parser.add_argument(
        "--out-dir", type=str,
        default=str(EVO_ROOT / "narrative_plots"),
        help="Output directory for the figure (default: outputs/phase5_evolution/narrative_plots)",
    )
    args = parser.parse_args()
    make_figure(Path(args.out_dir))


if __name__ == "__main__":
    main()
