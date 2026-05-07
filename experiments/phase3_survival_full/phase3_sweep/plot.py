# experiments/phase3_sweep/plot.py
"""
Phase 3 Sensitivity Sweep — Visualisations.

Generates three figures:
  1. Sweep summary  — init_food vs feeds / mother survival / child death tick / action split
  2. Time-series    — per-tick population, mother energy, child energy (10 seeds, food=900)
  3. Phase 2 vs 3  — mother survival and mean energy comparison (10 seeds each)

Usage:
    python -m experiments.phase3_survival_full.phase3_sweep.plot
    python -m experiments.phase3_survival_full.phase3_sweep.plot --baseline percept15
    python -m experiments.phase3_survival_full.phase3_sweep.plot --no_show   # save only
"""
import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Paths (resolved after argument parsing) ───────────────────────────────────
_PHASE2_CSV = {
    "percept8":  PROJECT_ROOT / "outputs/phase2_survival_minimal/auto_400_percept8/validation_balanced.csv",
    "percept15": PROJECT_ROOT / "outputs/phase2_survival_minimal/auto_400_percept15/validation_balanced.csv",
}
_PHASE2_JSON = {
    "percept8":  PROJECT_ROOT / "outputs/phase2_survival_minimal/auto_400_percept8/selected_ecologies.json",
    "percept15": PROJECT_ROOT / "outputs/phase2_survival_minimal/auto_400_percept15/selected_ecologies.json",
}

# ── Phase 2 style ─────────────────────────────────────────────────────────────
matplotlib.rcParams.update({
    "font.family":        "sans-serif",
    "font.sans-serif":    ["DejaVu Sans", "Arial", "Helvetica"],
    "axes.titlesize":     12,
    "axes.labelsize":     11,
    "xtick.labelsize":    9,
    "ytick.labelsize":    9,
    "xtick.direction":    "in",
    "ytick.direction":    "in",
    "xtick.top":          False,
    "ytick.right":        False,
    "legend.fontsize":    9,
    "legend.frameon":     True,
    "legend.edgecolor":   "#cccccc",
    "figure.facecolor":   "white",
    "savefig.facecolor":  "white",
})

C_FORAGE = "#d45b13"   # action FORAGE
C_SELF   = "#7b4ea0"   # action SELF
C_CARE   = "#c7443a"   # action CARE / threshold line
C_MOM    = "#1f77b4"   # mother / Phase 2 reference
C_CHILD  = "#2ca02c"   # child / Phase 3
C_INDIV  = "#aaaaaa"   # individual seed runs (background)

_LEGEND_KW = dict(fontsize=9, framealpha=0.95, edgecolor="#aaaaaa", fancybox=False)
_ANNOT_BOX = dict(
    boxstyle="square,pad=0.5", facecolor="white",
    edgecolor="#aaaaaa", alpha=0.95, linewidth=0.8,
)


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.4, color="#888888")
    ax.grid(True, which="minor", linestyle=":",  linewidth=0.3, alpha=0.2, color="#aaaaaa")
    ax.minorticks_on()
    ax.tick_params(which="major", labelsize=9, length=5, width=0.8, direction="in")
    ax.tick_params(which="minor", labelsize=0, length=2.5, width=0.5, direction="in")
    ax.set_facecolor("white")
    ax.xaxis.label.set_size(11)
    ax.yaxis.label.set_size(11)
    ax.title.set_size(12)


def save_figure(fig, path: Path) -> None:
    fig.patch.set_facecolor("white")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {path}")


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_sweep(path: Path) -> list[dict]:
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append({k: float(v) for k, v in r.items()})
    return rows


def aggregate_sweep(rows: list[dict]) -> dict[int, dict]:
    foods = sorted({int(r["init_food"]) for r in rows})
    agg = {}
    for f in foods:
        sub = [r for r in rows if int(r["init_food"]) == f]
        def mu(key):  return np.mean([r[key] for r in sub])
        def sd(key):  return np.std([r[key]  for r in sub])
        agg[f] = {
            "mother_survival_mu": mu("mother_survival"),
            "mother_survival_sd": sd("mother_survival"),
            "feeds_mu":           mu("feeds"),
            "feeds_sd":           sd("feeds"),
            "care_pct_mu":        mu("care_pct"),
            "forage_pct_mu":      mu("forage_pct"),
            "self_pct_mu":        mu("self_pct"),
            "child_death_mu":     mu("child_death_tick_mean"),
            "child_death_sd":     sd("child_death_tick_mean"),
            "child_death_min":    min(r["child_death_tick_min"] for r in sub),
            "child_death_max":    max(r["child_death_tick_max"] for r in sub),
        }
    return agg


def load_phase2_survival(path: Path) -> list[float]:
    surv = []
    with open(path) as f:
        for r in csv.DictReader(f):
            surv.append(float(r["final_pop"]) / 15.0)
    return surv


# ── Per-tick simulation helpers ───────────────────────────────────────────────

def run_timeseries(init_food: int, seed: int, baseline: str = "percept8") -> dict:
    from experiments.phase3_survival_full.phase3_sweep.config import load_sweep_config
    from simulation.simulation import Simulation

    cfg = load_sweep_config(init_food, seed, baseline)
    sim = Simulation(cfg)
    sim.initialize()

    ticks, n_mothers, n_children = [], [], []
    mu_mom_e, mu_child_e = [], []

    while sim.tick < cfg.max_ticks:
        am = [m for m in sim.mothers if m.alive]
        ac = [c for c in sim.children if c.alive]
        ticks.append(sim.tick)
        n_mothers.append(len(am))
        n_children.append(len(ac))
        mu_mom_e.append(np.mean([m.energy for m in am]) if am else np.nan)
        mu_child_e.append(np.mean([c.energy for c in ac]) if ac else np.nan)
        sim.step()
        sim.tick += 1

    return {
        "ticks":      np.array(ticks),
        "n_mothers":  np.array(n_mothers, dtype=float),
        "n_children": np.array(n_children, dtype=float),
        "mu_mom_e":   np.array(mu_mom_e,   dtype=float),
        "mu_child_e": np.array(mu_child_e,  dtype=float),
    }


def run_phase2_timeseries(seed: int, baseline: str = "percept8") -> dict:
    """Run BALANCED baseline without children (Phase 2 reference)."""
    import json
    from config import Config
    from simulation.simulation import Simulation

    ph2_json = _PHASE2_JSON[baseline]
    with open(ph2_json) as f:
        data = json.load(f)
    ec = data["balanced"]["selected_config"]

    cfg = Config(
        perception_radius    = float(ec["perception_radius"]),
        hunger_rate          = float(ec["hunger_rate"]),
        move_cost            = float(ec["move_cost"]),
        eat_gain             = float(ec["eat_gain"]),
        rest_recovery        = float(ec["rest_recovery"]),
        init_food            = int(ec["init_food"]),
        food_perception_radius = int(ec["perception_radius"]),
        children_enabled     = False,
        care_enabled         = False,
        reproduction_enabled = False,
        mutation_enabled     = False,
        plasticity_enabled   = False,
        max_ticks            = 400,
        init_mothers         = 15,
        seed                 = seed,
    )
    sim = Simulation(cfg)
    sim.initialize()

    ticks, n_mothers, mu_mom_e = [], [], []
    while sim.tick < cfg.max_ticks:
        am = [m for m in sim.mothers if m.alive]
        ticks.append(sim.tick)
        n_mothers.append(len(am))
        mu_mom_e.append(np.mean([m.energy for m in am]) if am else np.nan)
        sim.step()
        sim.tick += 1

    return {
        "ticks":     np.array(ticks),
        "n_mothers": np.array(n_mothers, dtype=float),
        "mu_mom_e":  np.array(mu_mom_e,  dtype=float),
    }


def _stack(ts_list: list[dict], key: str, n: int = 400) -> np.ndarray:
    """Stack per-seed 1-D arrays into (n_seeds, n) matrix, padding NaN."""
    mat = np.full((len(ts_list), n), np.nan)
    for i, ts in enumerate(ts_list):
        arr = ts[key]
        length = min(len(arr), n)
        mat[i, :length] = arr[:length]
    return mat


# ── Figure 1 — Sweep summary ──────────────────────────────────────────────────

def fig_sweep_summary(agg: dict[int, dict], out: Path, baseline: str = "percept8") -> None:
    foods  = sorted(agg.keys())
    x      = np.arange(len(foods))
    labels = [str(f) for f in foods]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(
        f"Phase 3 Sensitivity Sweep — init_food  |  {baseline} BALANCED, ISM=2.33, weights=1.0",
        fontsize=14, fontweight="bold", y=0.98,
    )
    fig.patch.set_facecolor("white")

    # ── Panel A: Feeds ────────────────────────────────────────────────────────
    ax = axes[0, 0]
    mu = [agg[f]["feeds_mu"] for f in foods]
    sd = [agg[f]["feeds_sd"] for f in foods]
    bars = ax.bar(x, mu, color=C_CHILD, alpha=0.8, width=0.6, zorder=3)
    ax.errorbar(x, mu, yerr=sd, fmt="none", color="#555555", capsize=4, linewidth=1.2, zorder=4)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel("init_food"); ax.set_ylabel("Feeds (mean ± SD)")
    ax.set_title("A — Total child feeds per simulation")
    for bar, v in zip(bars, mu):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.4, f"{v:.0f}",
                ha="center", va="bottom", fontsize=8, color="#333333")
    ax.annotate(
        "62 feeds needed\nfor maturity_age=200",
        xy=(0.97, 0.95), xycoords="axes fraction",
        ha="right", va="top", fontsize=8, bbox=_ANNOT_BOX,
    )
    style_axes(ax)

    # ── Panel B: Mother survival ──────────────────────────────────────────────
    ax = axes[0, 1]
    mu = [agg[f]["mother_survival_mu"] for f in foods]
    sd = [agg[f]["mother_survival_sd"] for f in foods]
    ax.bar(x, mu, color=C_MOM, alpha=0.8, width=0.6, zorder=3)
    ax.errorbar(x, mu, yerr=sd, fmt="none", color="#555555", capsize=4, linewidth=1.2, zorder=4)
    ax.axhline(0.628, color="#888888", linestyle="--", linewidth=1.2,
               label="Phase 2 BALANCED (62.8%)")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel("init_food"); ax.set_ylabel("Fraction alive at tick 400")
    ax.set_title("B — Mother survival")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    ax.legend(**_LEGEND_KW)
    style_axes(ax)

    # ── Panel C: Child death tick ─────────────────────────────────────────────
    ax = axes[1, 0]
    mu   = [agg[f]["child_death_mu"]  for f in foods]
    dmin = [agg[f]["child_death_min"] for f in foods]
    dmax = [agg[f]["child_death_max"] for f in foods]
    ax.plot(x, mu, color=C_CHILD, marker="o", linewidth=2, zorder=4, label="Mean death tick")
    ax.fill_between(x, dmin, dmax, color=C_CHILD, alpha=0.15, label="Observed range")
    ax.axhline(200, color=C_CARE, linestyle="--", linewidth=1.5, label="maturity_age=200")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel("init_food"); ax.set_ylabel("Tick")
    ax.set_title("C — Child death tick  (mean + observed range)")
    ax.legend(**_LEGEND_KW)
    ax.annotate(
        "No child reached\nmaturity_age=200",
        xy=(0.97, 0.95), xycoords="axes fraction",
        ha="right", va="top", fontsize=8, bbox=_ANNOT_BOX,
    )
    style_axes(ax)

    # ── Panel D: Action split ─────────────────────────────────────────────────
    ax = axes[1, 1]
    care_p   = [agg[f]["care_pct_mu"]   for f in foods]
    forage_p = [agg[f]["forage_pct_mu"] for f in foods]
    self_p   = [agg[f]["self_pct_mu"]   for f in foods]
    ax.bar(x, care_p,   label="CARE",   color=C_CARE,   width=0.6, zorder=3)
    ax.bar(x, forage_p, bottom=care_p,  label="FORAGE", color=C_FORAGE, width=0.6, zorder=3, alpha=0.9)
    bot = [c + f for c, f in zip(care_p, forage_p)]
    ax.bar(x, self_p,   bottom=bot,     label="SELF",   color=C_SELF,   width=0.6, zorder=3, alpha=0.9)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel("init_food"); ax.set_ylabel("% of logged choices")
    ax.set_title("D — Action distribution (when child distressed)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0))
    ax.legend(**_LEGEND_KW)
    style_axes(ax)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save_figure(fig, out)


# ── Figure 2 — Time-series (multi-seed) ───────────────────────────────────────

def fig_timeseries(ts_list: list[dict], out: Path, baseline: str = "percept8") -> None:
    n_ticks = 400
    t = np.arange(n_ticks)

    mom_e_mat   = _stack(ts_list, "mu_mom_e",   n_ticks)
    child_e_mat = _stack(ts_list, "mu_child_e", n_ticks)
    n_mom_mat   = _stack(ts_list, "n_mothers",  n_ticks)
    n_child_mat = _stack(ts_list, "n_children", n_ticks)

    with np.errstate(all="ignore"):
        mom_e_mu    = np.nanmean(mom_e_mat,   axis=0)
        mom_e_sd    = np.nanstd(mom_e_mat,    axis=0)
        child_e_mu  = np.nanmean(child_e_mat, axis=0)
        child_e_sd  = np.nanstd(child_e_mat,  axis=0)
        n_mom_mu    = np.nanmean(n_mom_mat,   axis=0)
        n_mom_sd    = np.nanstd(n_mom_mat,    axis=0)
        n_child_mu  = np.nanmean(n_child_mat, axis=0)
        n_child_sd  = np.nanstd(n_child_mat,  axis=0)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(
        f"Phase 3 Time-Series  |  {baseline} BALANCED, init_food=900, ISM=2.33, weights=1.0  (10 seeds)",
        fontsize=14, fontweight="bold", y=0.98,
    )
    fig.patch.set_facecolor("white")

    # ── Panel A: Population ───────────────────────────────────────────────────
    ax = axes[0, 0]
    for ts in ts_list:
        n = min(len(ts["n_mothers"]), n_ticks)
        ax.plot(t[:n], ts["n_mothers"][:n],  color=C_INDIV, lw=0.8, alpha=0.3)
        ax.plot(t[:n], ts["n_children"][:n], color=C_INDIV, lw=0.8, alpha=0.15)
    ax.plot(t, n_mom_mu,   color=C_MOM,   lw=2, label="Mothers (mean)")
    ax.fill_between(t, n_mom_mu - n_mom_sd, n_mom_mu + n_mom_sd, color=C_MOM,   alpha=0.15)
    ax.plot(t, n_child_mu, color=C_CHILD, lw=2, label="Children (mean)")
    ax.fill_between(t, n_child_mu - n_child_sd, n_child_mu + n_child_sd, color=C_CHILD, alpha=0.15)
    ax.set_xlabel("Tick"); ax.set_ylabel("Count")
    ax.set_title("A — Population over time")
    ax.legend(**_LEGEND_KW)
    style_axes(ax)

    # ── Panel B: Mother energy ────────────────────────────────────────────────
    ax = axes[0, 1]
    for ts in ts_list:
        n = min(len(ts["mu_mom_e"]), n_ticks)
        ax.plot(t[:n], ts["mu_mom_e"][:n], color=C_INDIV, lw=0.8, alpha=0.3)
    ax.plot(t, mom_e_mu, color=C_MOM, lw=2, label="Mean ± 1 SD")
    ax.fill_between(t, mom_e_mu - mom_e_sd, mom_e_mu + mom_e_sd, color=C_MOM, alpha=0.15)
    ax.axhline(0, color="#888888", linestyle="--", lw=1, alpha=0.6)
    ax.set_xlabel("Tick"); ax.set_ylabel("Mean energy")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("B — Mean mother energy")
    ax.legend(**_LEGEND_KW)
    style_axes(ax)

    # ── Panel C: Child energy ─────────────────────────────────────────────────
    ax = axes[1, 0]
    for ts in ts_list:
        vals  = ts["mu_child_e"]
        valid = ~np.isnan(vals)
        n     = min(len(vals), n_ticks)
        if valid[:n].any():
            ax.plot(t[:n][valid[:n]], vals[:n][valid[:n]], color=C_INDIV, lw=0.8, alpha=0.3)
    child_valid = ~np.isnan(child_e_mu)
    if child_valid.any():
        ax.plot(t[child_valid], child_e_mu[child_valid], color=C_CHILD, lw=2, label="Mean ± 1 SD")
        ax.fill_between(
            t[child_valid],
            (child_e_mu - child_e_sd)[child_valid],
            (child_e_mu + child_e_sd)[child_valid],
            color=C_CHILD, alpha=0.15,
        )
        last_tick = int(t[child_valid][-1])
        ax.annotate(
            f"Children extinct\n(tick ≈ {last_tick})",
            xy=(last_tick, 0.02),
            xytext=(max(last_tick - 60, 10), 0.30),
            fontsize=8, bbox=_ANNOT_BOX,
            arrowprops=dict(arrowstyle="->", color="#555555", lw=1),
        )
    ax.axhline(0, color="#888888", linestyle="--", lw=1, alpha=0.6)
    ax.set_xlabel("Tick"); ax.set_ylabel("Mean energy")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("C — Mean child energy  (until last child dies)")
    ax.legend(**_LEGEND_KW)
    style_axes(ax)

    # ── Panel D: Overlay ──────────────────────────────────────────────────────
    ax = axes[1, 1]
    ax.fill_between(t, 0, n_child_mu, color=C_CHILD, alpha=0.25, label="Children alive (mean)")
    ax2 = ax.twinx()
    ax2.plot(t, mom_e_mu, color=C_MOM, lw=2, label="Mother energy (mean)")
    ax2.fill_between(t, mom_e_mu - mom_e_sd, mom_e_mu + mom_e_sd, color=C_MOM, alpha=0.1)
    ax2.set_ylim(-0.05, 1.05)
    ax2.set_ylabel("Mean mother energy", fontsize=10)
    ax2.tick_params(which="major", direction="in", labelsize=9, length=5, width=0.8)
    ax2.tick_params(which="minor", direction="in", labelsize=0, length=2.5, width=0.5)
    ax2.spines["top"].set_visible(False)
    ax.set_xlabel("Tick"); ax.set_ylabel("Alive children", fontsize=10)
    ax.set_title("D — Children alive & mother energy overlay")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, **_LEGEND_KW, loc="upper right")
    style_axes(ax)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save_figure(fig, out)


# ── Figure 3 — Phase 2 vs Phase 3 ─────────────────────────────────────────────

def fig_phase2_vs_3(
    ts2_list: list[dict],
    ts3_list: list[dict],
    p2_surv:  list[float],
    agg3:     dict[int, dict],
    out:      Path,
    baseline: str = "percept8",
) -> None:
    n_ticks = 400
    t = np.arange(n_ticks)

    ph2_e_mat = _stack(ts2_list, "mu_mom_e", n_ticks)
    ph3_e_mat = _stack(ts3_list, "mu_mom_e", n_ticks)
    with np.errstate(all="ignore"):
        ph2_mu = np.nanmean(ph2_e_mat, axis=0)
        ph2_sd = np.nanstd(ph2_e_mat,  axis=0)
        ph3_mu = np.nanmean(ph3_e_mat, axis=0)
        ph3_sd = np.nanstd(ph3_e_mat,  axis=0)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(
        f"Phase 2 vs Phase 3  |  {baseline} BALANCED ecology  (mean ± 1 SD, 10 seeds)",
        fontsize=14, fontweight="bold", y=0.98,
    )
    fig.patch.set_facecolor("white")

    # ── Panel A: Mother survival ──────────────────────────────────────────────
    ax = axes[0]
    foods    = sorted(agg3.keys())
    ph3_surv = [agg3[f]["mother_survival_mu"] for f in foods]
    ph3_sd_s = [agg3[f]["mother_survival_sd"] for f in foods]
    x        = np.arange(len(foods))

    ph2_mean = np.mean(p2_surv)
    ph2_std  = np.std(p2_surv)
    ax.axhline(ph2_mean, color=C_MOM, linestyle="--", linewidth=1.8,
               label=f"Phase 2 BALANCED mean ({ph2_mean*100:.1f}%)")
    ax.fill_between([-0.5, len(foods) - 0.5],
                    ph2_mean - ph2_std, ph2_mean + ph2_std,
                    color=C_MOM, alpha=0.1)
    ax.errorbar(x, ph3_surv, yerr=ph3_sd_s, fmt="o-",
                color=C_CHILD, linewidth=2, capsize=4, label="Phase 3 (with children)")
    ax.set_xticks(x); ax.set_xticklabels([str(f) for f in foods])
    ax.set_xlabel("init_food"); ax.set_ylabel("Mother survival fraction")
    ax.set_title("A — Mother survival: Phase 2 vs Phase 3")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    ax.legend(**_LEGEND_KW)
    ax.annotate(
        f"Phase 2: {ph2_mean*100:.1f}% (no children)\n"
        f"Phase 3 best: {max(ph3_surv)*100:.1f}% (food=900)",
        xy=(0.03, 0.05), xycoords="axes fraction",
        ha="left", va="bottom", fontsize=8, bbox=_ANNOT_BOX,
    )
    style_axes(ax)

    # ── Panel B: Energy trajectory ────────────────────────────────────────────
    ax = axes[1]
    for ts in ts2_list:
        n = min(len(ts["mu_mom_e"]), n_ticks)
        ax.plot(t[:n], ts["mu_mom_e"][:n], color=C_INDIV, lw=0.8, alpha=0.25)
    ax.plot(t, ph2_mu, color=C_MOM, lw=2, label="Phase 2 (no children)")
    ax.fill_between(t, ph2_mu - ph2_sd, ph2_mu + ph2_sd, color=C_MOM, alpha=0.15)

    for ts in ts3_list:
        n = min(len(ts["mu_mom_e"]), n_ticks)
        ax.plot(t[:n], ts["mu_mom_e"][:n], color=C_INDIV, lw=0.8, alpha=0.15)
    ax.plot(t, ph3_mu, color=C_CHILD, lw=2, label="Phase 3 (with children, food=900)")
    ax.fill_between(t, ph3_mu - ph3_sd, ph3_mu + ph3_sd, color=C_CHILD, alpha=0.15)

    ax.axhline(0, color="#888888", linestyle="--", lw=1, alpha=0.6)
    ax.set_xlabel("Tick"); ax.set_ylabel("Mean mother energy")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("B — Mother energy trajectory  (mean ± 1 SD, 10 seeds)")
    ax.legend(**_LEGEND_KW)
    style_axes(ax)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save_figure(fig, out)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=str, default="percept8",
                        choices=["percept8", "percept15"],
                        help="Phase 2 ecology baseline to use (default: percept8)")
    parser.add_argument("--no_show", action="store_true")
    args = parser.parse_args()

    from experiments.phase3_survival_full.phase3_sweep.config import SWEEP_SEEDS

    sweep_csv = PROJECT_ROOT / "outputs" / "phase3_survival_full" / "phase3_sweep" / args.baseline / "raw_results.csv"
    out_dir   = PROJECT_ROOT / "outputs" / "phase3_survival_full" / "phase3_sweep" / args.baseline / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Baseline: {args.baseline}")
    print("Loading Phase 3 sweep CSV...")
    rows = load_sweep(sweep_csv)
    agg  = aggregate_sweep(rows)

    print("Loading Phase 2 BALANCED survival data...")
    p2_surv = load_phase2_survival(_PHASE2_CSV[args.baseline])

    print(f"Running Phase 3 time-series (food=900, {len(SWEEP_SEEDS)} seeds)...")
    ts3_list = [run_timeseries(900, s, args.baseline) for s in SWEEP_SEEDS]

    print(f"Running Phase 2 baseline time-series ({len(SWEEP_SEEDS)} seeds)...")
    ts2_list = [run_phase2_timeseries(s, args.baseline) for s in SWEEP_SEEDS]

    print("Generating Figure 1 — Sweep summary...")
    fig_sweep_summary(agg, out_dir / "fig1_sweep_summary.png", args.baseline)

    print("Generating Figure 2 — Time-series...")
    fig_timeseries(ts3_list, out_dir / "fig2_timeseries.png", args.baseline)

    print("Generating Figure 3 — Phase 2 vs Phase 3 comparison...")
    fig_phase2_vs_3(ts2_list, ts3_list, p2_surv, agg, out_dir / "fig3_phase2_vs_3.png", args.baseline)

    print(f"\nAll plots saved to: {out_dir}")


if __name__ == "__main__":
    main()
