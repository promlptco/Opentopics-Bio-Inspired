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
    return np.convolve(arr, kernel, mode="same")


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
