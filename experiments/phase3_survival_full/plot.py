# experiments/phase3_survival_full/plot.py
"""
Phase 3 Plots — same visual style as Phase 2, extended with child panels.

Figures produced:
  multiseed_{name}.png         — mother energy/population + child energy/population (4 panels)
  motivation_split_{name}.png  — FORAGE/SELF/CARE action share bar chart
  ovat_sensitivity.png         — 4-row × 3-col OVAT sensitivity map (mother + child metrics)

Usage (standalone — reads saved CSVs):
  python -m experiments.phase3_survival_full.plot
"""

import os
import sys
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase3_survival_full.config import (
    INIT_MOTHERS, TAIL_WINDOW, SENSITIVITY_SWEEPS, SENSITIVITY_SUBPLOT_CONFIG,
    MAX_TICKS,
)

# ─────────────────────────────────────────────────────────────────────────────
# Global rcParams (same academic style as Phase 2)
# ─────────────────────────────────────────────────────────────────────────────
matplotlib.rcParams.update({
    "font.family":       "sans-serif",
    "font.sans-serif":   ["DejaVu Sans", "Arial", "Helvetica"],
    "axes.titlesize":    12,
    "axes.labelsize":    11,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "xtick.direction":   "in",
    "ytick.direction":   "in",
    "xtick.top":         False,
    "ytick.right":       False,
    "legend.fontsize":   9,
    "legend.frameon":    True,
    "legend.edgecolor":  "#cccccc",
    "figure.facecolor":  "white",
    "savefig.facecolor": "white",
})

# Colour palette (same as Phase 2 where applicable)
C_MOTHER  = "#1f77b4"   # blue — mother metrics
C_CHILD   = "#2ca02c"   # green — child metrics
C_FORAGE  = "#D08770"   # warm orange — FORAGE
C_SELF    = "#8FBCBB"   # muted teal — SELF
C_CARE    = "#B48EAD"   # muted purple — CARE
C_ENERGY  = "#2E3440"   # dark slate — energy (secondary axis)
C_SURV    = "#5E81AC"   # steel blue — survival


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def safe(value, nan: float = 0.0) -> float:
    return float(np.nan_to_num(value, nan=nan))


def pad(x, duration: int) -> np.ndarray:
    arr = np.full(duration, np.nan)
    x = np.asarray(x, dtype=float)
    arr[: min(duration, len(x))] = x[:duration]
    return arr


def _smooth(series: list, window: int) -> np.ndarray:
    arr = np.asarray(series, dtype=float)
    if window <= 1 or len(arr) < window:
        return arr
    kernel = np.ones(window) / window
    # TRIAL: edge-replication padding — preserves tick-0 true value, no zero-pad spike.
    # To revert: comment the 3 lines below and uncomment the original line.
    pad = window // 2
    padded = np.pad(arr, pad, mode="edge")
    return np.convolve(padded, kernel, mode="valid")[:len(arr)]
    # return np.convolve(arr, kernel, mode="same")  # original (zero-pad, causes spike)


def _style_ax(ax, xlabel: str = "", ylabel: str = "", title: str = "") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(direction="in", colors="#444444")
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, fontweight="bold")


def _save(fig, path: str, dpi: int = 200) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {os.path.basename(path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Figure 1 — Multiseed condition overview (4 panels)
# ─────────────────────────────────────────────────────────────────────────────

def plot_multiseed_condition_phase3(name: str, results: list, params: dict,
                                     run_labels: list, duration: int,
                                     out_dir: str, window: int = 25) -> None:
    """
    4-panel overview for one condition (HARSH / BALANCED / EASY / single).

    Panel layout:
      [0] Mother energy over time (population-weighted)
      [1] Mother population over time
      [2] Child energy over time (mean over alive children)
      [3] Child population over time
    """
    ticks = np.arange(duration)

    # Collect per-seed histories
    m_e_all, m_pop_all = [], []
    c_e_all, c_pop_all = [], []

    for r in results:
        m_e_all.append(pad(r.get("energy_history",   []), duration))
        m_pop_all.append(pad(r.get("population_history", []), duration))
        c_e_all.append(pad(r.get("child_energy_history",     []), duration))
        c_pop_all.append(pad(r.get("child_population_history", []), duration))

    def _stats(arrays):
        mat = np.vstack(arrays)
        return np.nanmean(mat, axis=0), np.nanstd(mat, axis=0), mat

    me_mu, me_sd, me_mat   = _stats(m_e_all)
    mp_mu, mp_sd, mp_mat   = _stats(m_pop_all)
    ce_mu, ce_sd, ce_mat   = _stats(c_e_all)
    cp_mu, cp_sd, cp_mat   = _stats(c_pop_all)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    ax_me, ax_mp, ax_ce, ax_cp = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    for ax, mu, sd, mat, color, ylabel, title in [
        (ax_me, me_mu, me_sd, me_mat, C_MOTHER, "Energy (pop-weighted)", "Mother energy"),
        (ax_mp, mp_mu, mp_sd, mp_mat, C_MOTHER, "Count",                 "Mother population"),
        (ax_ce, ce_mu, ce_sd, ce_mat, C_CHILD,  "Energy (mean alive)",   "Child energy"),
        (ax_cp, cp_mu, cp_sd, cp_mat, C_CHILD,  "Count",                 "Child population"),
    ]:
        for row in mat:
            ax.plot(ticks, _smooth(row, window), color="#cccccc", lw=0.4, alpha=0.4)
        mu_s = _smooth(mu, window)
        ax.plot(ticks, mu_s, color=color, lw=2, label="mean")
        ax.fill_between(
            ticks,
            np.clip(_smooth(mu - sd, window), 0, None),
            np.clip(_smooth(mu + sd, window), None, None),
            alpha=0.15, color=color, label="±1 SD",
        )
        if title.startswith("Child"):
            ax.axvline(200, color="#888888", lw=1, ls="--", label="maturity (200 ticks)")
        ax.legend(loc="upper right", fontsize=8)
        _style_ax(ax, xlabel="Simulation tick", ylabel=ylabel, title=title)

    # Annotate mother population with INIT_MOTHERS reference
    ax_mp.axhline(INIT_MOTHERS, color="#888888", lw=1, ls=":", label=f"init ({INIT_MOTHERS})")
    ax_mp.legend(loc="upper right", fontsize=8)

    fig.suptitle(
        f"Phase 3 — {name.upper()}  |  "
        f"food={params.get('init_food','?')}  eat={params.get('eat_gain','?'):.2f}  "
        f"cost={params.get('move_cost','?'):.4f}  n={len(results)}",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    _save(fig, os.path.join(out_dir, f"multiseed_{name}.png"))


# ─────────────────────────────────────────────────────────────────────────────
# Figure 2 — Motivation split bar chart
# ─────────────────────────────────────────────────────────────────────────────

def plot_motivation_split(name: str, results: list, out_dir: str) -> None:
    """
    Stacked bar: FORAGE / SELF / CARE motivation share per seed,
    plus mean bar on the right.
    """
    n = len(results)
    forage = [r.get("forage_pct", 0.0) * 100 for r in results]
    self_  = [r.get("self_pct",   0.0) * 100 for r in results]
    care   = [r.get("care_pct",   0.0) * 100 for r in results]

    labels = [str(r.get("base_seed", i)) for i, r in enumerate(results)] + ["MEAN"]
    forage.append(float(np.mean(forage[:-1])) if forage[:-1] else 0.0)
    self_.append(float(np.mean(self_[:-1]))   if self_[:-1]  else 0.0)
    care.append(float(np.mean(care[:-1]))     if care[:-1]   else 0.0)

    x     = np.arange(len(labels))
    width = 0.6

    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 0.5 + 2), 5))
    b1 = ax.bar(x, forage, width, label="FORAGE", color=C_FORAGE)
    b2 = ax.bar(x, self_,  width, bottom=forage, label="SELF", color=C_SELF)
    bottom2 = [f + s for f, s in zip(forage, self_)]
    ax.bar(x, care, width, bottom=bottom2, label="CARE", color=C_CARE)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Motivation share (%)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter())
    ax.legend(loc="upper right", fontsize=9)
    _style_ax(ax, title=f"Phase 3 — {name.upper()}  motivation split")

    fig.tight_layout()
    _save(fig, os.path.join(out_dir, f"motivation_split_{name}.png"))


# ─────────────────────────────────────────────────────────────────────────────
# Figure 3 — OVAT Sensitivity Map (Phase 3 extended: 4 rows × 3 columns)
# ─────────────────────────────────────────────────────────────────────────────

def plot_ovat_sensitivity_map(ovat_all: dict, baseline: dict, out_dir: str) -> None:
    """
    4-row × 3-column OVAT sensitivity map.

    Row 0: Mother survival rate (same as Phase 2 primary metric)
    Row 1: Tail mean energy (same as Phase 2 secondary metric)
    Row 2: Child maturation rate (C_matr)
    Row 3: Child mean death tick (longevity)

    Columns: Set A (init_food), Set B (eat_gain), Set C (move_cost).
    """
    n_rows, n_cols = 4, 3
    row_labels = [
        ("survival_rate_mean",         "survival_rate_sd",        "Mother survival rate",    C_SURV),
        ("tail_energy_mean",           "tail_energy_sd",           "Tail mean energy",        C_ENERGY),
        ("child_maturation_rate_mean", "child_maturation_rate_sd", "Child maturation (C_matr)", C_CHILD),
        ("child_death_tick_mean_mean", "child_death_tick_mean_sd", "Child mean death tick",   C_MOTHER),
    ]

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 14), sharex="col")
    fig.patch.set_facecolor("white")

    for col_idx, (set_id, key, xlabel, color) in enumerate(SENSITIVITY_SUBPLOT_CONFIG):
        data = ovat_all.get(set_id, [])
        if not data:
            for row_idx in range(n_rows):
                axes[row_idx, col_idx].set_visible(False)
            continue

        xs = np.array([d["param_value"] for d in data], dtype=float)

        for row_idx, (mu_key, sd_key, ylabel, row_color) in enumerate(row_labels):
            ax = axes[row_idx, col_idx]
            ax.set_facecolor("white")

            mu_vals = np.array([float(d.get(mu_key, 0)) for d in data], dtype=float)
            sd_vals = np.array([float(d.get(sd_key, 0)) for d in data], dtype=float)

            ax.plot(xs, mu_vals, "o-", color=row_color, lw=2, ms=5)
            ax.fill_between(
                xs,
                np.clip(mu_vals - sd_vals, 0, None),
                mu_vals + sd_vals,
                alpha=0.12, color=row_color,
            )

            # Reference lines
            if row_idx == 0:
                ax.axhline(0.25, color="#e0a070", lw=1, ls=":", alpha=0.7, label="HARSH 0.25")
                ax.axhline(0.625, color="#70a0e0", lw=1, ls=":", alpha=0.7, label="BAL 0.625")
                ax.axhline(0.90, color="#70c090", lw=1, ls=":", alpha=0.7, label="EASY 0.90")
                ax.set_ylim(-0.05, 1.1)
            elif row_idx == 1:
                ax.set_ylim(-0.05, 1.1)
            elif row_idx == 2:
                ax.axhline(0.10, color="#888888", lw=1, ls="--", alpha=0.6, label="EASY floor")
                ax.set_ylim(-0.02, max(1.05, float(np.nanmax(mu_vals)) + 0.1))
            elif row_idx == 3:
                ax.axhline(200, color="#888888", lw=1, ls="--", alpha=0.6, label="maturity 200")
                ax.set_ylim(0, MAX_TICKS + 20)

            # Labels
            if row_idx == n_rows - 1:
                _style_ax(ax, xlabel=xlabel, ylabel=ylabel)
            else:
                _style_ax(ax, ylabel=ylabel)
                ax.set_xlabel("")

            if row_idx == 0:
                ax.set_title(f"Set {set_id} — {key}", fontweight="bold", fontsize=11)

    fig.suptitle(
        "Phase 3 — OVAT Sensitivity  |  Mother & Child metrics  "
        "(unbiased weights, children enabled)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    _save(fig, os.path.join(out_dir, "ovat_sensitivity.png"), dpi=200)


# ─────────────────────────────────────────────────────────────────────────────
# Care-trap diagnostic plots (Workstream 1) — 5 standalone PNGs
# ─────────────────────────────────────────────────────────────────────────────

def plot_caretrap_motivation_scores(diag: dict, out_dir: str,
                                     window: int = 15) -> None:
    """
    Figure CT-1: Mean motivation SCORES (before softmax) across alive mothers
    per tick.  Three smooth lines — FORAGE flatly dominates.
    """
    T    = diag["duration"]
    ticks = np.arange(T)

    fig, ax = plt.subplots(figsize=(10, 4))

    for arr, label, color in [
        (diag["score_forage"], "FORAGE", C_FORAGE),
        (diag["score_care"],   "CARE",   C_CARE),
        (diag["score_self"],   "SELF",   C_SELF),
    ]:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mu = np.nanmean(arr, axis=1)      # mean across mothers; NaN = dead
        mu = np.where(np.isnan(mu), 0.0, mu)
        ax.plot(ticks, _smooth(mu, window), color=color, lw=2, label=label)

    ax.set_ylim(-0.02, 0.65)
    ax.legend(loc="upper right", fontsize=9)
    _style_ax(ax,
              xlabel="Simulation tick",
              ylabel="Mean motivation score (0–1)",
              title="CT-1  Motivation scores over time"
                    "  (unbiased weights 1/1/1, seed=42)")
    fig.tight_layout()
    _save(fig, os.path.join(out_dir, "caretrap_motivation_scores.png"))


def plot_caretrap_action_strip(diag: dict, out_dir: str) -> None:
    """
    Figure CT-2: Categorical colour strip — one cell per (tick × mother).
    Colour encodes the chosen domain; shows FORAGE-dominated pattern.
    """
    import matplotlib.patches as mpatches

    domain_idx = diag["domain_idx"]   # shape (T, n_mothers)
    T, n_m     = domain_idx.shape

    # RGB colour map: -1=dead (light grey), 0=FORAGE, 1=CARE, 2=SELF
    _col = {
        -1: np.array([0.88, 0.88, 0.88]),
         0: np.array(matplotlib.colors.to_rgb(C_FORAGE)),
         1: np.array(matplotlib.colors.to_rgb(C_CARE)),
         2: np.array(matplotlib.colors.to_rgb(C_SELF)),
    }
    img = np.zeros((n_m, T, 3))
    for mi in range(n_m):
        for t in range(T):
            img[mi, t, :] = _col.get(domain_idx[t, mi], _col[-1])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.imshow(img, aspect="auto", interpolation="nearest", origin="upper")
    ax.set_xlabel("Simulation tick")
    ax.set_ylabel("Mother index")
    ax.set_yticks(range(n_m))
    ax.set_yticklabels([str(i + 1) for i in range(n_m)], fontsize=7)

    patches = [
        mpatches.Patch(color=C_FORAGE,  label="FORAGE"),
        mpatches.Patch(color=C_CARE,    label="CARE"),
        mpatches.Patch(color=C_SELF,    label="SELF"),
        mpatches.Patch(color="#e0e0e0", label="dead"),
    ]
    ax.legend(handles=patches, loc="upper right", fontsize=8,
              framealpha=0.9)
    _style_ax(ax, title="CT-2  Action sequence strip"
                        "  (unbiased weights 1/1/1, seed=42)")
    fig.tight_layout()
    _save(fig, os.path.join(out_dir, "caretrap_action_strip.png"))


def plot_caretrap_held_food(diag: dict, out_dir: str,
                             mother_idx: int = 0) -> None:
    """
    Figure CT-3: Step function of held_food (0 or 1) for one representative
    mother.  Red ✗ markers where CARE was chosen while held_food=0.
    """
    T        = diag["duration"]
    hf_raw   = diag["held_food"][:, mother_idx]
    fc_raw   = diag["failed_care"][:, mother_idx]
    ticks    = np.arange(T)

    # -1 = dead → NaN so matplotlib masks the line
    hf = hf_raw.astype(float)
    hf[hf < 0] = np.nan

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.step(ticks, hf, where="post", color="#1f77b4", lw=1.5, label="held_food")
    ax.set_ylim(-0.2, 1.5)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["0 (empty)", "1 (holding)"])

    failed_ticks = np.where(fc_raw)[0]
    if len(failed_ticks):
        ax.scatter(
            failed_ticks,
            np.full(len(failed_ticks), 0.5),
            color="red", marker="x", s=35, zorder=5, linewidths=1.2,
            label=f"CARE chosen, held_food=0  (n={len(failed_ticks)})",
        )

    ax.legend(fontsize=8)
    _style_ax(ax,
              xlabel="Simulation tick",
              ylabel="held_food",
              title=f"CT-3  held_food — mother {mother_idx + 1}"
                    f"  (unbiased weights 1/1/1, seed=42)")
    fig.tight_layout()
    _save(fig, os.path.join(out_dir, "caretrap_held_food.png"))


def plot_caretrap_child_energy(diag: dict, out_dir: str) -> None:
    """
    Figure CT-4: Per-child energy trajectories.  Vertical dashes where CARE
    fired; red dots at death ticks.
    """
    import matplotlib.lines as mlines
    import matplotlib.patches as mpatches

    child_energy = diag["child_energy"]     # (T, n_c)
    child_death  = diag["child_death_tick"]
    domain_idx   = diag["domain_idx"]       # (T, n_m)
    T            = diag["duration"]
    n_c          = diag["n_children"]
    ticks        = np.arange(T)

    # Ticks where any mother chose CARE
    care_ticks = np.where(np.any(domain_idx == 1, axis=1))[0]

    fig, ax = plt.subplots(figsize=(10, 5))

    # CARE tick background lines (subsampled to avoid visual clutter)
    for ct in care_ticks[::max(1, len(care_ticks) // 60)]:
        ax.axvline(ct, color=C_CARE, lw=0.5, alpha=0.25)

    for ci in range(n_c):
        energy = child_energy[:, ci].copy()
        ax.plot(ticks, energy, lw=0.9, alpha=0.6, color=C_CHILD)

        dt = child_death[ci]
        if not np.isnan(dt):
            dt_i = int(dt)
            ax.scatter(dt_i, 0.0, color="red", s=22, zorder=5)

    ax.set_xlim(0, T)
    ax.set_ylim(-0.05, 1.05)
    ax.axvline(200, color="#888888", lw=1, ls="--", alpha=0.6)
    ax.text(202, 0.95, "maturity\n(200)", fontsize=7, color="#888888", va="top")

    leg = [
        mlines.Line2D([], [], color=C_CHILD, lw=1, label="child energy"),
        mlines.Line2D([], [], color="red", marker="o", ms=5, lw=0,
                      label="child death"),
        mlines.Line2D([], [], color=C_CARE, lw=1.5, alpha=0.6,
                      label="CARE fired (any mother)"),
    ]
    ax.legend(handles=leg, fontsize=8, loc="upper right")
    _style_ax(ax,
              xlabel="Simulation tick",
              ylabel="Child energy (0–1)",
              title="CT-4  Child energy trajectories"
                    "  (unbiased weights 1/1/1, seed=42)")
    fig.tight_layout()
    _save(fig, os.path.join(out_dir, "caretrap_child_energy.png"))


def plot_caretrap_failed_care_bar(diag: dict, out_dir: str) -> None:
    """
    Figure CT-5: Per-mother bar chart — % of CARE-selection ticks where
    held_food=0 (failed delivery).  Population-level evidence of the trap.
    """
    domain_idx  = diag["domain_idx"]    # (T, n_m)
    failed_care = diag["failed_care"]   # (T, n_m)
    n_m         = diag["n_mothers"]

    pct_failed = []
    for mi in range(n_m):
        care_mask = domain_idx[:, mi] == 1
        n_care    = int(care_mask.sum())
        n_failed  = int(failed_care[:, mi].sum())
        pct_failed.append((n_failed / n_care * 100) if n_care > 0 else 0.0)

    overall = float(np.mean([p for p in pct_failed if p > 0])) if any(
        p > 0 for p in pct_failed
    ) else 0.0

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(n_m)
    ax.bar(x, pct_failed, color=C_CARE, edgecolor="white", linewidth=0.5)
    ax.axhline(overall, color="#333333", lw=1.5, ls="--",
               label=f"mean = {overall:.0f}%")

    ax.set_xticks(x)
    ax.set_xticklabels([str(i + 1) for i in range(n_m)], fontsize=8)
    ax.set_ylim(0, 110)
    ax.set_xlabel("Mother index")
    ax.set_ylabel("Failed CARE attempts (%)")
    ax.legend(fontsize=8)
    _style_ax(ax,
              title=f"CT-5  % CARE attempts where held_food=0"
                    f"  (mean={overall:.0f}%, seed=42)")
    fig.tight_layout()
    _save(fig, os.path.join(out_dir, "caretrap_failed_care_bar.png"))


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2-style validation suite — academic style with minor grid
# ─────────────────────────────────────────────────────────────────────────────

_ANNOT_BOX = dict(boxstyle="square,pad=0.5", facecolor="white",
                  edgecolor="#aaaaaa", alpha=0.95, linewidth=0.8)
_LEGEND_KW = dict(fontsize=9, framealpha=0.95, edgecolor="#aaaaaa", fancybox=False)

_MOTIV_COLORS = {
    "FORAGE": "#d45b13",
    "SELF":   "#7b4ea0",
    "CARE":   "#B48EAD",
}


def style_axes(ax):
    """Full academic style with minor grid — identical to Phase 2."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.4, color="#888888")
    ax.grid(True, which="minor", linestyle=":", linewidth=0.3, alpha=0.2, color="#aaaaaa")
    ax.minorticks_on()
    ax.tick_params(which="major", labelsize=9, length=5, width=0.8, direction="in")
    ax.tick_params(which="minor", labelsize=0, length=2.5, width=0.5, direction="in")
    ax.set_facecolor("white")
    ax.xaxis.label.set_size(11)
    ax.yaxis.label.set_size(11)
    ax.title.set_size(12)


def save_figure(fig, out_dir: str, filename: str, dpi: int = 200) -> None:
    fig.patch.set_facecolor("white")
    path = os.path.join(out_dir, filename)
    os.makedirs(out_dir, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {filename}")


def _motiv_share_matrix(results: list, key: str, duration: int, window: int) -> np.ndarray:
    """
    Per-tick SHARE of logged choices that chose `key` (FORAGE/SELF/CARE).
    Denominator = FORAGE+SELF+CARE (all logged choices that tick) so shares sum to 1.
    """
    matrix = []
    for r in results:
        hist = r.get("motivation_history", [])
        share = np.full(duration, np.nan)
        for t, row in enumerate(hist[:duration]):
            total = row.get("FORAGE", 0) + row.get("SELF", 0) + row.get("CARE", 0)
            if total > 0:
                share[t] = row.get(key, 0) / total
        valid = np.nan_to_num(share, nan=0.0)
        matrix.append(_smooth(valid, window))
    return np.asarray(matrix, dtype=float)


def _food_avail_matrix(results: list, duration: int, window: int) -> np.ndarray:
    """Food available per tick. Returns (n_runs, duration)."""
    matrix = []
    for r in results:
        hist = r.get("food_history", [])
        vals = np.zeros(duration, dtype=float)
        for t, row in enumerate(hist[:duration]):
            vals[t] = row.get("food_available", 0.0)
        matrix.append(_smooth(vals, window))
    return np.asarray(matrix, dtype=float)


# ─── 1. Validation overview (Phase 2 style: 2-panel mother energy + pop) ────

def plot_validation_p3(name: str, results: list, params: dict,
                       duration: int, out_dir: str) -> None:
    """Phase 2-style 2-panel mother validation. → validation_{name}.png"""
    from experiments.phase3_survival_full.config import SELECTION_TARGETS
    ticks = np.arange(duration)

    e_mat = np.asarray(
        [np.nan_to_num(pad(r["energy_history"], duration), nan=0.0) for r in results]
    )
    p_mat = np.asarray(
        [np.nan_to_num(pad(r["population_history"], duration), nan=0.0) for r in results]
    )
    mean_e, std_e = np.mean(e_mat, axis=0), np.std(e_mat, axis=0)
    mean_p, std_p = np.mean(p_mat, axis=0), np.std(p_mat, axis=0)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    fig.suptitle(
        f"Phase 3 Multi-Seed Validation — {name.upper()}  |  MotherAgent  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold", y=0.98,
    )
    fig.text(
        0.5, 0.955,
        (f"food={params.get('init_food','?')}  eat={params.get('eat_gain','?'):.2f}  "
         f"cost={params.get('move_cost','?'):.4f}  "
         f"care_w={params.get('care_weight',1.0):.1f}  "
         f"forage_w={params.get('forage_weight',1.0):.1f}  "
         f"self_w={params.get('self_weight',1.0):.1f}"),
        ha="center", va="top", fontsize=9, color="#444444",
    )

    for i in range(len(results)):
        lbl = "Individual runs" if i == 0 else "_nolegend_"
        ax1.plot(ticks, e_mat[i], alpha=0.2, lw=0.7, color="#aaaaaa", label=lbl)
        ax2.step(ticks, p_mat[i], where="post", alpha=0.2, lw=0.7, color="#aaaaaa", label=lbl)

    ax1.fill_between(ticks, mean_e - std_e, mean_e + std_e,
                     color="#2ca02c", alpha=0.18, label="Mean ± 1 SD")
    ax1.plot(ticks, mean_e, color="#2ca02c", lw=2.2, label="Group mean")
    ax2.fill_between(ticks, mean_p - std_p, mean_p + std_p,
                     color="#1f77b4", alpha=0.18, label="Mean ± 1 SD")
    ax2.plot(ticks, mean_p, color="#1f77b4", lw=2.2, label="Group mean")

    _t = SELECTION_TARGETS.get(name, {})
    target_e  = _t.get("target_energy", 0.35)
    ceiling_e = _t.get("energy_high", _t.get("min_energy", 0.80))
    ax1.axhline(target_e,  color="#555555", ls=":",  lw=1.2, label=f"Target energy = {target_e:.2f}")
    ax1.axhline(ceiling_e, color="#555555", ls="--", lw=1.0, alpha=0.6,
                label=f"Energy ceiling = {ceiling_e:.2f}")
    ax1.axhline(0.0, color="#d62728", ls="--", lw=1.0, alpha=0.6, label="Death threshold (E = 0)")
    ax2.axhline(0.0, color="#d62728", ls="--", lw=1.0, alpha=0.6, label="Extinction (n = 0)")
    ax2.axhline(INIT_MOTHERS, color="#555555", ls=":", lw=1.2,
                label=f"Initial cohort (n = {INIT_MOTHERS})")

    ax1.set_title("Population-weighted energy trajectory  (green = group mean ± 1 SD)")
    ax1.set_ylabel("Population-weighted mean energy")
    ax1.set_ylim(-0.05, 1.05)
    ax2.set_title("Alive population over time  (blue = group mean ± 1 SD)")
    ax2.set_ylabel("Number of alive mothers")
    ax2.set_xlabel("Simulation tick")
    ax2.set_ylim(-0.5, INIT_MOTHERS + 1.5)

    summary = (
        f"final alive mean = {np.mean(p_mat[:, -1]):.2f}/{INIT_MOTHERS}\n"
        f"final energy mean = {mean_e[-1]:.3f}\n"
        f"final energy SD = {std_e[-1]:.3f}"
    )
    ax1.text(0.01, 0.04, summary, transform=ax1.transAxes, fontsize=9, bbox=_ANNOT_BOX)
    for ax in (ax1, ax2):
        style_axes(ax)
        ax.legend(loc="lower left", **_LEGEND_KW)

    plt.tight_layout()
    save_figure(fig, out_dir, f"validation_{name}.png")


# ─── 2 & 3. Motivation / action selection over time ──────────────────────────

def _plot_motivation_over_time(name: str, results: list, duration: int,
                                out_dir: str, filename_prefix: str,
                                title_prefix: str, window: int = 25) -> None:
    """
    FORAGE/SELF/CARE selection share over time (per-tick fraction of logged choices).
    """
    ticks = np.arange(duration)
    matrices = {k: _motiv_share_matrix(results, k, duration, window)
                for k in ["FORAGE", "SELF", "CARE"]}

    fig, ax = plt.subplots(figsize=(13, 6))
    first = True
    for key, matrix in matrices.items():
        for i in range(matrix.shape[0]):
            ax.plot(ticks, matrix[i], alpha=0.2, lw=0.5, color="#aaaaaa",
                    label="Individual runs" if first else "_nolegend_")
            first = False

    for key, matrix in matrices.items():
        mu  = np.mean(matrix, axis=0)
        sd  = np.std(matrix,  axis=0)
        col = _MOTIV_COLORS[key]
        ax.fill_between(ticks, mu - sd, mu + sd, alpha=0.15, color=col,
                        label=f"{key} mean ± 1 SD")
        ax.plot(ticks, mu, lw=2.2, color=col, label=f"{key} group mean")

    ax.axvline(200, color="#888888", lw=1, ls="--", alpha=0.6, label="maturity (200)")
    ax.set_ylim(-0.05, 1.05)
    fig.suptitle(
        f"{title_prefix} Over Time — {name.upper()}  |  Phase 3  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    ax.set_title(
        f"Share of logged care-conditional choices  |  smoothing window = {window} ticks"
    )
    ax.set_xlabel("Simulation tick")
    ax.set_ylabel("Share of logged choices (FORAGE+SELF+CARE = 1)")
    style_axes(ax)
    ax.legend(loc="upper right", **_LEGEND_KW)
    plt.tight_layout()
    save_figure(fig, out_dir, f"{filename_prefix}_{name}.png")


def plot_motivation_selection_over_time_p3(name: str, results: list, duration: int,
                                            out_dir: str, window: int = 25) -> None:
    """→ motivation_selection_{name}.png"""
    _plot_motivation_over_time(name, results, duration, out_dir,
                               "motivation_selection", "Motivation Selection", window)


def plot_action_selection_over_time_p3(name: str, results: list, duration: int,
                                        out_dir: str, window: int = 25) -> None:
    """→ action_selection_{name}.png  (Phase 3: action = motivation choice)"""
    _plot_motivation_over_time(name, results, duration, out_dir,
                               "action_selection", "Action Selection (Motivation Proxy)", window)


# ─── 4. Stacked motivation area ───────────────────────────────────────────────

def plot_stacked_motivation_p3(name: str, results: list, duration: int,
                                out_dir: str, window: int = 25) -> None:
    """Stacked area: mean FORAGE/SELF/CARE share per tick. → stacked_motivation_{name}.png"""
    ticks = np.arange(duration)
    keys  = ["FORAGE", "SELF", "CARE"]
    means = {k: np.mean(_motiv_share_matrix(results, k, duration, window), axis=0) for k in keys}

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.stackplot(
        ticks,
        [means[k] for k in keys],
        labels=keys,
        colors=[_MOTIV_COLORS[k] for k in keys],
        alpha=0.82,
    )
    ax.axvline(200, color="#333333", lw=1, ls="--", alpha=0.7, label="maturity (200)")
    ax.set_ylim(0.0, 1.15)
    fig.suptitle(
        f"Stacked Motivation Selection — {name.upper()}  |  Phase 3  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    ax.set_title(f"Mean share stacked  |  smoothing window = {window} ticks")
    ax.set_xlabel("Simulation tick")
    ax.set_ylabel("Share of logged choices")
    style_axes(ax)
    ax.legend(loc="upper right", ncol=2, **_LEGEND_KW)
    plt.tight_layout()
    save_figure(fig, out_dir, f"stacked_action_failed_{name}.png")


# ─── 5. Care rate vs child energy correlation ─────────────────────────────────

def plot_care_child_energy_correlation_p3(name: str, results: list, duration: int,
                                           out_dir: str, window: int = 25) -> None:
    """
    Scatter: per-tick CARE share vs mean child energy.
    Phase 3 analogue of Phase 2's FAILED_FORAGE vs energy-drop correlation.
    → correlation_failed_forage_energy_{name}.png
    """
    xs, ys = [], []
    for r in results:
        hist_m = r.get("motivation_history", [])
        hist_c = r.get("child_energy_history", [])
        for t in range(min(duration, len(hist_m), len(hist_c))):
            row  = hist_m[t]
            total = row.get("FORAGE", 0) + row.get("SELF", 0) + row.get("CARE", 0)
            ce    = hist_c[t] if t < len(hist_c) else float("nan")
            if total > 0 and not (isinstance(ce, float) and np.isnan(ce)):
                xs.append(row.get("CARE", 0) / total)
                ys.append(float(ce))

    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    valid = np.isfinite(xs) & np.isfinite(ys)
    xs, ys = xs[valid], ys[valid]

    can_fit = (len(xs) >= 3 and np.std(xs) > 1e-12 and np.std(ys) > 1e-12)
    corr = float(np.corrcoef(xs, ys)[0, 1]) if can_fit else 0.0

    fig, ax = plt.subplots(figsize=(8, 6))
    if len(xs) > 0:
        ax.scatter(xs, ys, alpha=0.06, s=10, color="steelblue", label="Tick samples")
    if can_fit:
        try:
            coef = np.polyfit(xs, ys, 1)
            xfit = np.linspace(float(xs.min()), float(xs.max()), 100)
            ax.plot(xfit, coef[0] * xfit + coef[1], color="tab:red", lw=2.0, label="Linear fit")
        except np.linalg.LinAlgError:
            pass
    else:
        ax.text(0.02, 0.95, "Linear fit skipped: insufficient variance",
                transform=ax.transAxes, fontsize=9, va="top", bbox=_ANNOT_BOX)

    fig.suptitle(
        f"CARE Share vs Child Energy — {name.upper()}  |  Pearson r = {corr:.3f}  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    ax.set_title("Correlation diagnostic  |  grey dots = tick samples, red = linear fit")
    ax.set_xlabel("CARE share (fraction of logged choices)")
    ax.set_ylabel("Mean child energy (0–1)")
    style_axes(ax)
    ax.legend(loc="upper right", **_LEGEND_KW)
    plt.tight_layout()
    save_figure(fig, out_dir, f"correlation_failed_forage_energy_{name}.png")


# ─── 6. Forage rate vs mother energy correlation ──────────────────────────────

def plot_forage_energy_correlation_p3(name: str, results: list, duration: int,
                                       out_dir: str, window: int = 25) -> None:
    """
    Scatter: per-tick FORAGE share vs mother energy drop.
    → correlation_failed_self_energy_{name}.png
    """
    xs, ys = [], []
    for r in results:
        hist_m  = r.get("motivation_history", [])
        e_arr   = np.nan_to_num(pad(r["energy_history"], duration), nan=0.0)
        e_delta = np.diff(e_arr, prepend=e_arr[0])
        e_drop  = _smooth(np.maximum(0.0, -e_delta), window)

        for t in range(min(duration, len(hist_m))):
            row   = hist_m[t]
            total = row.get("FORAGE", 0) + row.get("SELF", 0) + row.get("CARE", 0)
            if total > 0 and t < len(e_drop):
                xs.append(row.get("FORAGE", 0) / total)
                ys.append(float(e_drop[t]))

    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    valid = np.isfinite(xs) & np.isfinite(ys)
    xs, ys = xs[valid], ys[valid]

    can_fit = (len(xs) >= 3 and np.std(xs) > 1e-12 and np.std(ys) > 1e-12)
    corr = float(np.corrcoef(xs, ys)[0, 1]) if can_fit else 0.0

    fig, ax = plt.subplots(figsize=(8, 6))
    if len(xs) > 0:
        ax.scatter(xs, ys, alpha=0.06, s=10, color="steelblue", label="Tick samples")
    if can_fit:
        try:
            coef = np.polyfit(xs, ys, 1)
            xfit = np.linspace(float(xs.min()), float(xs.max()), 100)
            ax.plot(xfit, coef[0] * xfit + coef[1], color="tab:red", lw=2.0, label="Linear fit")
        except np.linalg.LinAlgError:
            pass
    else:
        ax.text(0.02, 0.95, "Linear fit skipped: insufficient variance",
                transform=ax.transAxes, fontsize=9, va="top", bbox=_ANNOT_BOX)

    fig.suptitle(
        f"FORAGE Share vs Mother Energy Decay — {name.upper()}  |  Pearson r = {corr:.3f}  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    ax.set_title("Correlation diagnostic  |  grey dots = tick samples, red = linear fit")
    ax.set_xlabel("FORAGE share (fraction of logged choices)")
    ax.set_ylabel("Mother energy drop per tick (smoothed)")
    style_axes(ax)
    ax.legend(loc="upper right", **_LEGEND_KW)
    plt.tight_layout()
    save_figure(fig, out_dir, f"correlation_failed_self_energy_{name}.png")


# ─── 7. Rate sum check ────────────────────────────────────────────────────────

def plot_rate_sum_check_p3(name: str, results: list, duration: int,
                            out_dir: str) -> None:
    """
    Verify FORAGE+SELF+CARE shares sum to 1 per tick.
    → rate_sum_check_{name}.png
    """
    ticks = np.arange(duration)
    sum_runs = []
    for r in results:
        hist = r.get("motivation_history", [])
        total_share = np.full(duration, np.nan)
        for t, row in enumerate(hist[:duration]):
            total = row.get("FORAGE", 0) + row.get("SELF", 0) + row.get("CARE", 0)
            if total > 0:
                total_share[t] = 1.0
        sum_runs.append(total_share)

    forage_runs = [_motiv_share_matrix([r], "FORAGE", duration, 1)[0] for r in results]
    self_runs   = [_motiv_share_matrix([r], "SELF",   duration, 1)[0] for r in results]
    care_runs   = [_motiv_share_matrix([r], "CARE",   duration, 1)[0] for r in results]

    f_mat = np.asarray(forage_runs)
    s_mat = np.asarray(self_runs)
    c_mat = np.asarray(care_runs)
    sum_mat = f_mat + s_mat + c_mat

    fig, ax = plt.subplots(figsize=(13, 6))
    curves = [
        ("FORAGE share", f_mat,   "tab:orange", "-"),
        ("SELF share",   s_mat,   "tab:purple",  "--"),
        ("CARE share",   c_mat,   "#B48EAD",     "-."),
        ("Total (F+S+C)", sum_mat, "tab:green",  "-"),
    ]
    for label, matrix, color, ls in curves:
        mu  = np.nanmean(matrix, axis=0)
        sd  = np.nanstd(matrix,  axis=0)
        ax.fill_between(ticks, mu - sd, mu + sd, color=color, alpha=0.10,
                        label=f"{label} Mean ± SD")
        ax.plot(ticks, mu, color=color, ls=ls, lw=2.2, label=f"{label} Group Mean")

    ax.axhline(1.0, color="black", ls="--", lw=1.2, alpha=0.75,
               label="Expected normalized total = 1.0")
    ax.set_ylim(-0.05, 1.25)
    fig.suptitle(
        f"Rate Sum Check — {name.upper()}  |  Phase 3  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    ax.set_title("Share completeness check  |  denominator = F+S+C logged choices  |  no smoothing")
    ax.set_xlabel("Simulation tick")
    ax.set_ylabel("Share sum per processed mother")
    style_axes(ax)
    ax.legend(loc="upper right", ncol=2, **_LEGEND_KW)
    plt.tight_layout()
    save_figure(fig, out_dir, f"rate_sum_check_{name}.png")


# ─── 8. State-space: energy vs motivation ────────────────────────────────────

def plot_state_space_energy_motivation_p3(name: str, results: list, duration: int,
                                           out_dir: str, window: int = 25) -> None:
    """
    4-panel scatter: mother energy vs FORAGE/SELF/CARE shares + child energy.
    → state_space_energy_action_{name}.png
    """
    e_all = np.concatenate(
        [np.nan_to_num(pad(r["energy_history"], duration), nan=0.0) for r in results]
    )
    plot_items = [
        ("FORAGE share",  _motiv_share_matrix(results, "FORAGE", duration, window), "tab:orange"),
        ("SELF share",    _motiv_share_matrix(results, "SELF",   duration, window), "tab:purple"),
        ("CARE share",    _motiv_share_matrix(results, "CARE",   duration, window), "#B48EAD"),
        ("Child energy",
         np.asarray([
             _smooth(np.nan_to_num(pad(r.get("child_energy_history", []), duration), nan=0.0), window)
             for r in results
         ]), C_CHILD),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharex=True)
    axes_flat = axes.flatten()

    for ax, (label, matrix, color) in zip(axes_flat, plot_items):
        rate_all = matrix.reshape(-1)
        ax.scatter(e_all, rate_all, alpha=0.06, s=8, color=color)

        bins = np.linspace(0.0, 1.0, 21)
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        bin_means = []
        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (e_all >= lo) & (e_all < hi)
            bin_means.append(float(np.mean(rate_all[mask])) if np.any(mask) else np.nan)

        ax.plot(bin_centers, bin_means, color="black", lw=2.0, label="Binned mean")
        ax.set_title(f"Energy vs {label}  (black = binned mean)")
        ax.set_xlabel("Population-weighted mean energy")
        ax.set_ylabel("Value (0–1)")
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.05, 1.05)
        style_axes(ax)
        ax.legend(loc="upper right", **_LEGEND_KW)

    fig.suptitle(
        f"State Space: Energy vs Motivation — {name.upper()}  |  Phase 3  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout()
    save_figure(fig, out_dir, f"state_space_energy_action_{name}.png")


# ─── 9. Food consumption over time ───────────────────────────────────────────

def plot_food_consumption_p3(name: str, results: list, duration: int,
                              out_dir: str, window: int = 25) -> None:
    """
    Food available over time (right axis) + CARE/FORAGE share (left axis).
    → food_consumption_rate_{name}.png
    """
    ticks = np.arange(duration)
    food_mat   = _food_avail_matrix(results, duration, window)
    forage_mat = _motiv_share_matrix(results, "FORAGE", duration, window)
    care_mat   = _motiv_share_matrix(results, "CARE",   duration, window)

    food_mu,   food_sd   = np.mean(food_mat,   axis=0), np.std(food_mat,   axis=0)
    forage_mu, forage_sd = np.mean(forage_mat, axis=0), np.std(forage_mat, axis=0)
    care_mu,   care_sd   = np.mean(care_mat,   axis=0), np.std(care_mat,   axis=0)

    fig, ax1 = plt.subplots(figsize=(13, 6))
    ax2 = ax1.twinx()

    for i in range(forage_mat.shape[0]):
        ax1.plot(ticks, forage_mat[i], alpha=0.2, lw=0.6, color="#aaaaaa",
                 label="Individual runs" if i == 0 else "_nolegend_")

    ax1.fill_between(ticks, forage_mu - forage_sd, forage_mu + forage_sd,
                     color=_MOTIV_COLORS["FORAGE"], alpha=0.12, label="FORAGE Mean ± SD")
    ax1.plot(ticks, forage_mu, color=_MOTIV_COLORS["FORAGE"], lw=2.2, label="FORAGE Group Mean")
    ax1.fill_between(ticks, care_mu - care_sd, care_mu + care_sd,
                     color=_MOTIV_COLORS["CARE"], alpha=0.12, label="CARE Mean ± SD")
    ax1.plot(ticks, care_mu, color=_MOTIV_COLORS["CARE"], lw=2.2, label="CARE Group Mean")

    ax2.fill_between(ticks, food_mu - food_sd, food_mu + food_sd,
                     color="tab:blue", alpha=0.08, label="Food Count Mean ± SD")
    ax2.plot(ticks, food_mu, color="tab:blue", ls="--", lw=2.0, label="Food Available")

    fig.suptitle(
        f"Food Available & Motivation Over Time — {name.upper()}  |  n = {len(results)} runs  |  window = {window} ticks",
        fontsize=14, fontweight="bold",
    )
    ax1.set_title("FORAGE/CARE share (left axis) and food count (right axis, dashed)")
    ax1.set_xlabel("Simulation tick")
    ax1.set_ylabel("Motivation share (0–1)")
    ax2.set_ylabel("Food items available on grid")
    ax1.set_ylim(-0.05, 1.05)

    style_axes(ax1)
    style_axes(ax2)
    lines1, lbl1 = ax1.get_legend_handles_labels()
    lines2, lbl2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, lbl1 + lbl2, loc="upper right", **_LEGEND_KW)
    plt.tight_layout()
    save_figure(fig, out_dir, f"food_consumption_rate_{name}.png")


# ─── 10. Spatial heatmap ──────────────────────────────────────────────────────

def plot_spatial_heatmap_p3(name: str, results: list, out_dir: str) -> None:
    """Mother spatial heatmap — identical template to Phase 2. → spatial_heatmap_population_{name}.png"""
    heatmaps = [np.asarray(r["spatial_heatmap"], dtype=float)
                for r in results if r.get("spatial_heatmap") is not None]
    if not heatmaps:
        return
    mean_hm = np.mean(np.asarray(heatmaps, dtype=float), axis=0)
    if np.max(mean_hm) > 0:
        mean_hm = mean_hm / np.max(mean_hm)

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(mean_hm, origin="lower", interpolation="nearest", aspect="equal")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Normalized visit density", fontsize=9)
    fig.suptitle(
        f"Spatial Heatmap of Mother Population — {name.upper()}  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    ax.set_title("Mean normalised visit density across all runs")
    ax.set_xlabel("Grid x-coordinate")
    ax.set_ylabel("Grid y-coordinate")
    style_axes(ax)
    plt.tight_layout()
    save_figure(fig, out_dir, f"spatial_heatmap_population_{name}.png")


# ─── 11. Energy expenditure breakdown ────────────────────────────────────────

def plot_energy_expenditure_breakdown_p3(name: str, results: list, out_dir: str) -> None:
    """
    Bar chart: mean motivation shares + mean energy metrics.
    Phase 3 equivalent of Phase 2's energy expenditure breakdown.
    → energy_expenditure_breakdown_{name}.png
    """
    forage_pcts = np.array([r.get("forage_pct", 0.0) * 100 for r in results])
    self_pcts   = np.array([r.get("self_pct",   0.0) * 100 for r in results])
    care_pcts   = np.array([r.get("care_pct",   0.0) * 100 for r in results])
    mean_es     = np.array([r.get("mean_energy", 0.0) for r in results])
    final_es    = np.array([r.get("final_energy", 0.0) for r in results])

    # Child mean energy per run
    child_es = []
    for r in results:
        hist = r.get("child_energy_history", [])
        if hist:
            arr = np.asarray(hist, dtype=float)
            child_es.append(float(np.nanmean(arr)) if not np.all(np.isnan(arr)) else 0.0)
        else:
            child_es.append(0.0)
    child_es = np.array(child_es)

    labels = ["FORAGE %", "SELF %", "CARE %",
              "Mother\nmean E", "Mother\nfinal E", "Child\nmean E"]
    means  = [forage_pcts.mean(), self_pcts.mean(), care_pcts.mean(),
               mean_es.mean() * 100, final_es.mean() * 100, child_es.mean() * 100]
    sds    = [forage_pcts.std(), self_pcts.std(), care_pcts.std(),
               mean_es.std()   * 100, final_es.std()   * 100, child_es.std()   * 100]
    colors = [_MOTIV_COLORS["FORAGE"], _MOTIV_COLORS["SELF"], _MOTIV_COLORS["CARE"],
              "#1f77b4", "#5E81AC", C_CHILD]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=sds, capsize=5, color=colors, alpha=0.82)
    ax.axhline(0.0, color="black", lw=1.0, alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Value (% for motivation shares; energy × 100 for energy metrics)")

    summary = (
        f"FORAGE = {forage_pcts.mean():.1f}%\n"
        f"SELF   = {self_pcts.mean():.1f}%\n"
        f"CARE   = {care_pcts.mean():.1f}%\n"
        f"mom_E  = {mean_es.mean():.3f}\n"
        f"child_E= {child_es.mean():.3f}"
    )
    ax.text(0.02, 0.96, summary, transform=ax.transAxes, fontsize=9, va="top", bbox=_ANNOT_BOX)

    fig.suptitle(
        f"Energy & Motivation Breakdown — {name.upper()}  |  Mean ± SD  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    ax.set_title("Motivation shares (%) and energy metrics (×100) across all validation runs")
    style_axes(ax)
    plt.tight_layout()
    save_figure(fig, out_dir, f"energy_expenditure_breakdown_{name}.png")


# ─── 12. Homeostatic balance ──────────────────────────────────────────────────

def plot_homeostatic_balance_p3(name: str, results: list, duration: int,
                                 out_dir: str, window: int = 25) -> None:
    """
    Mother energy (blue, left) vs fatigue (red, right) dual-axis.
    → homeostatic_balance_{name}.png
    """
    ticks = np.arange(duration)

    e_mat = np.asarray([
        _smooth(np.nan_to_num(pad(r["energy_history"], duration), nan=0.0), window)
        for r in results
    ], dtype=float)
    f_mat = np.asarray([
        _smooth(np.nan_to_num(pad(r.get("fatigue_history", []), duration), nan=0.0), window)
        for r in results
    ], dtype=float)

    mu_e, sd_e = np.mean(e_mat, axis=0), np.std(e_mat, axis=0)
    mu_f, sd_f = np.mean(f_mat, axis=0), np.std(f_mat, axis=0)

    fig, ax_e = plt.subplots(figsize=(13, 6))
    ax_f = ax_e.twinx()

    for i in range(len(results)):
        lbl = "Individual runs" if i == 0 else "_nolegend_"
        ax_e.plot(ticks, e_mat[i], color="#aaaaaa", alpha=0.2, lw=0.7, label=lbl)
        ax_f.plot(ticks, f_mat[i], color="#aaaaaa", alpha=0.2, lw=0.7)

    ax_e.fill_between(ticks, mu_e - sd_e, mu_e + sd_e, color="#1f77b4", alpha=0.15,
                      label="Energy mean ± 1 SD")
    ax_e.plot(ticks, mu_e, color="#1f77b4", lw=2.3, label="Mean energy")
    ax_f.fill_between(ticks, mu_f - sd_f, mu_f + sd_f, color="#d62728", alpha=0.12,
                      label="Fatigue mean ± 1 SD")
    ax_f.plot(ticks, mu_f, color="#d62728", ls="--", lw=2.3, label="Mean fatigue")

    ax_e.axhline(0.35, color="#1f77b4", ls=":", alpha=0.55, lw=1.2, label="Energy target = 0.35")
    ax_f.axhline(0.0,  color="#d62728", ls=":", alpha=0.35, lw=1.0, label="Fatigue baseline = 0")

    fig.suptitle(
        f"Homeostatic Balance: Energy vs Fatigue — {name.upper()}  |  Phase 3  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    ax_e.set_title(f"Energy (blue, left) vs fatigue (red, right)  |  smoothing window = {window} ticks")
    ax_e.set_xlabel("Simulation tick")
    ax_e.set_ylabel("Population-weighted mean energy", color="#1f77b4")
    ax_f.set_ylabel("Population-weighted mean fatigue", color="#d62728")
    ax_e.tick_params(axis="y", labelcolor="#1f77b4")
    ax_f.tick_params(axis="y", labelcolor="#d62728")
    ax_e.set_ylim(-0.05, 1.05)
    ax_f.set_ylim(-0.05, 1.05)
    style_axes(ax_e)
    style_axes(ax_f)

    lines_e, lbl_e = ax_e.get_legend_handles_labels()
    lines_f, lbl_f = ax_f.get_legend_handles_labels()
    ax_e.legend(lines_e + lines_f, lbl_e + lbl_f, loc="upper right", **_LEGEND_KW)
    plt.tight_layout()
    save_figure(fig, out_dir, f"homeostatic_balance_{name}.png")


# ─── 13. Child metrics panel (Phase 3 specific) ───────────────────────────────

def plot_child_metrics_p3(name: str, results: list, duration: int, out_dir: str,
                           window: int = 25) -> None:
    """
    4-panel child diagnostic:
      [0] Child energy over time (mean ± SD)
      [1] Child population over time
      [2] Child death tick distribution (histogram)
      [3] CARE rate over time (for context)
    → child_metrics_{name}.png
    """
    ticks = np.arange(duration)

    ce_mat = np.asarray([
        np.nan_to_num(pad(r.get("child_energy_history",     []), duration), nan=0.0)
        for r in results
    ], dtype=float)
    cp_mat = np.asarray([
        np.nan_to_num(pad(r.get("child_population_history", []), duration), nan=0.0)
        for r in results
    ], dtype=float)
    care_mat = _motiv_share_matrix(results, "CARE", duration, window)

    death_ticks = [r.get("child_death_tick_mean", float(duration)) for r in results]

    mu_ce, sd_ce = np.nanmean(ce_mat, axis=0), np.nanstd(ce_mat, axis=0)
    mu_cp, sd_cp = np.mean(cp_mat, axis=0), np.std(cp_mat, axis=0)
    mu_cr, sd_cr = np.mean(care_mat, axis=0), np.std(care_mat, axis=0)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    ax_ce, ax_cp, ax_dt, ax_cr = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    # Child energy
    for row in ce_mat:
        ax_ce.plot(ticks, _smooth(row, window), color="#cccccc", lw=0.4, alpha=0.4)
    ax_ce.fill_between(ticks, np.clip(mu_ce - sd_ce, 0, None), mu_ce + sd_ce,
                       alpha=0.18, color=C_CHILD, label="Mean ± 1 SD")
    ax_ce.plot(ticks, _smooth(mu_ce, window), color=C_CHILD, lw=2.2, label="Group mean")
    ax_ce.axvline(200, color="#888888", lw=1, ls="--", label="maturity (200)")
    ax_ce.axhline(0.0, color="#d62728", ls="--", lw=1.0, alpha=0.6)
    ax_ce.set_ylim(-0.05, 1.05)
    ax_ce.set_title("Child energy over time")
    ax_ce.set_ylabel("Mean alive child energy")
    ax_ce.set_xlabel("Simulation tick")
    style_axes(ax_ce)
    ax_ce.legend(loc="upper right", **_LEGEND_KW)

    # Child population
    for row in cp_mat:
        ax_cp.step(ticks, row, where="post", color="#cccccc", lw=0.4, alpha=0.4)
    ax_cp.fill_between(ticks, np.clip(mu_cp - sd_cp, 0, None), mu_cp + sd_cp,
                       alpha=0.18, color=C_CHILD, label="Mean ± 1 SD")
    ax_cp.step(ticks, mu_cp, where="post", color=C_CHILD, lw=2.2, label="Group mean")
    ax_cp.axhline(INIT_MOTHERS, color="#555555", ls=":", lw=1.2,
                  label=f"Initial (n = {INIT_MOTHERS})")
    ax_cp.axvline(200, color="#888888", lw=1, ls="--", label="maturity (200)")
    ax_cp.set_ylim(-0.5, INIT_MOTHERS + 1.5)
    ax_cp.set_title("Child population over time")
    ax_cp.set_ylabel("Number of alive children")
    ax_cp.set_xlabel("Simulation tick")
    style_axes(ax_cp)
    ax_cp.legend(loc="upper right", **_LEGEND_KW)

    # Death tick histogram
    finite_deaths = [d for d in death_ticks if d < duration]
    if finite_deaths:
        ax_dt.hist(finite_deaths, bins=15, color=C_CHILD, alpha=0.75, edgecolor="white")
        ax_dt.axvline(float(np.mean(finite_deaths)), color="#d62728", lw=2.0, ls="--",
                      label=f"mean = {np.mean(finite_deaths):.1f}")
        ax_dt.axvline(200, color="#888888", lw=1.5, ls=":", label="maturity (200)")
    else:
        ax_dt.text(0.5, 0.5, "No child deaths\n(all survived / no data)",
                   transform=ax_dt.transAxes, ha="center", va="center", fontsize=11)
    ax_dt.set_title("Child death tick distribution")
    ax_dt.set_xlabel("Death tick (per seed mean)")
    ax_dt.set_ylabel("Count")
    style_axes(ax_dt)
    ax_dt.legend(loc="upper right", **_LEGEND_KW)

    # CARE rate over time
    for row in care_mat:
        ax_cr.plot(ticks, row, color="#cccccc", lw=0.4, alpha=0.4)
    ax_cr.fill_between(ticks, np.clip(mu_cr - sd_cr, 0, None), mu_cr + sd_cr,
                       alpha=0.18, color=_MOTIV_COLORS["CARE"], label="Mean ± 1 SD")
    ax_cr.plot(ticks, mu_cr, color=_MOTIV_COLORS["CARE"], lw=2.2, label="CARE share")
    ax_cr.axvline(200, color="#888888", lw=1, ls="--", label="maturity (200)")
    ax_cr.set_ylim(-0.05, 1.05)
    ax_cr.set_title("CARE motivation share over time")
    ax_cr.set_ylabel("Share of logged choices")
    ax_cr.set_xlabel("Simulation tick")
    style_axes(ax_cr)
    ax_cr.legend(loc="upper right", **_LEGEND_KW)

    fig.suptitle(
        f"Phase 3 Child Metrics — {name.upper()}  |  n = {len(results)} runs",
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    save_figure(fig, out_dir, f"child_metrics_{name}.png")


# ─────────────────────────────────────────────────────────────────────────────
# Standalone entry (re-generates plots from saved CSVs)
# ─────────────────────────────────────────────────────────────────────────────

def _load_csv(path: str) -> list:
    if not os.path.exists(path):
        print(f"  [warn] not found: {path}")
        return []
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        cast = {}
        for k, v in row.items():
            try:
                cast[k] = float(v)
            except (ValueError, TypeError):
                cast[k] = v
        out.append(cast)
    return out


def _load_ovat_from_csvs(ovat_dir: str) -> dict:
    ovat_all = {}
    for set_id, key_str, *_ in SENSITIVITY_SUBPLOT_CONFIG:
        path = os.path.join(ovat_dir, f"set_{set_id}_{key_str}.csv")
        rows = _load_csv(path)
        if rows:
            ovat_all[set_id] = rows
    return ovat_all


def main():
    """Re-generate all Phase 3 plots from saved CSV outputs."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", type=str,
                        default=os.path.join(PROJECT_ROOT, "outputs", "phase3_survival_full"))
    args = parser.parse_args()

    print("Phase 3 — generating plots from saved outputs")

    ovat_dir = os.path.join(args.out_dir, "sensitivity_ovat")
    ovat_all = _load_ovat_from_csvs(ovat_dir)
    if ovat_all:
        from experiments.phase3_survival_full.config import BALANCED_BASELINE
        plot_ovat_sensitivity_map(ovat_all, BALANCED_BASELINE, ovat_dir)
    else:
        print("  [info] No OVAT CSVs found — skipping OVAT sensitivity map.")

    print("Done.")


if __name__ == "__main__":
    main()
