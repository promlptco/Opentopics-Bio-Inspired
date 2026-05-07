# experiments/phase3b_calibration/plot.py
"""
Phase 3b Calibration — Evidence plots (academic white style).

Figures produced:
  1. ovat_sensitivity.png     — M_surv + child_death_mu/400 across OVAT sets A/B/C
  2. action_rate.png          — CARE/FORAGE/SELF% stacked across OVAT sets A/B/C
  3. feasibility_heatmap.png  — ISM x eat_gain heatmap of child_death_mu (clean, no contours)
  4a. mother_energy.png       — best ecological validation: mother energy trajectory
  4b. child_energy.png        — best ecological validation: child energy trajectory
  4c. mother_population.png   — best ecological validation: mother population trajectory
  4d. child_population.png    — best ecological validation: child population trajectory
  5. care_trap_scatter.png    — child longevity by ISM across all grid combos

Usage:
    python -m experiments.phase3_survival_full.phase3b_calibration.plot
"""
import csv
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase3_survival_full.phase3b_calibration.config import (
    SWEEP_GRID, VALIDATION_SEEDS, make_config,
)

OUT_DIR   = PROJECT_ROOT / "outputs" / "phase3_survival_full" / "phase3b_calibration"
PLOT_DIR  = OUT_DIR / "plots"
MAX_TICKS = 400
DPI       = 200

best_eco = {"ism": 1.2, "eat_gain": 0.70, "init_food": 600}

# ── Restrained academic palette ───────────────────────────────────────────────
C_RED    = "#b33a3a"   # muted red — mother metrics
C_BLUE   = "#3a6fb3"   # steel blue — child metrics
C_GREY   = "#999999"   # seed lines, secondary
C_DARK   = "#333333"   # threshold lines, spines
C_CARE   = "#3a6fb3"   # CARE action
C_FORAGE = "#5e8f45"   # FORAGE action (muted green)
C_SELF   = "#c8c8c8"   # SELF action (light grey)

# ISM sequential blues (light → dark)
ISM_COLORS = {1.2: "#9ecae1", 1.5: "#4292c6", 2.0: "#2171b5", 2.33: "#084594"}


# ── Style helpers ──────────────────────────────────────────────────────────────

def _apply_rcparams():
    plt.rcParams.update({
        "font.family":        "sans-serif",
        "axes.facecolor":     "white",
        "figure.facecolor":   "white",
        "xtick.direction":    "in",
        "ytick.direction":    "in",
        "xtick.labelsize":    10,
        "ytick.labelsize":    10,
        "axes.labelsize":     11,
        "axes.titlesize":     12,
        "figure.titlesize":   13,
        "figure.titleweight": "bold",
        "legend.fontsize":    9,
        "legend.frameon":     False,
    })

_apply_rcparams()


def style_axes(ax, xlabel="", ylabel="", title=""):
    ax.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(direction="in", colors="#444444", labelsize=10)
    ax.yaxis.set_minor_locator(mticker.AutoMinorLocator())
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11)
    if title:
        ax.set_title(title, fontsize=12, fontweight="bold")


def save_fig(fig, fname: str) -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    path = PLOT_DIR / fname
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {path.name}")


# ── CSV helpers ────────────────────────────────────────────────────────────────

def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  [warn] not found: {path.name}")
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


def group_by(rows: list[dict], key: str) -> dict:
    g: dict = {}
    for r in rows:
        g.setdefault(r[key], []).append(r)
    return g


def mu_sd(rows, key):
    vals = [r[key] for r in rows]
    return float(np.mean(vals)), float(np.std(vals))


# ── History collector ──────────────────────────────────────────────────────────

def collect_histories(ism: float, eat_gain: float, init_food: int,
                      seeds: list[int]) -> dict:
    from simulation.simulation import Simulation
    hist = {"mom_e": [], "child_e": [], "mom_pop": [], "child_pop": []}
    for seed in seeds:
        cfg = make_config(ism, eat_gain, init_food, seed)
        sim = Simulation(cfg)
        sim.initialize()
        me, ce, mp, cp = [], [], [], []
        while sim.tick < cfg.max_ticks:
            am = [m for m in sim.mothers  if m.alive]
            ac = [c for c in sim.children if c.alive]
            me.append(np.mean([m.energy for m in am]) if am else np.nan)
            ce.append(np.mean([c.energy for c in ac]) if ac else np.nan)
            mp.append(len(am))
            cp.append(len(ac))
            sim.step()
            sim.tick += 1
        hist["mom_e"].append(me)
        hist["child_e"].append(ce)
        hist["mom_pop"].append(mp)
        hist["child_pop"].append(cp)
    return hist


def _stack(arrays: list[list]) -> tuple:
    arrs   = [np.array(a, dtype=float) for a in arrays]
    length = min(len(a) for a in arrs)
    mat    = np.vstack([a[:length] for a in arrs])
    return np.nanmean(mat, axis=0), np.nanstd(mat, axis=0), mat


def _shared_legend(fig, axes):
    """Place one legend outside the right edge, collecting from the first non-empty panel."""
    handles, labels = [], []
    for ax in axes:
        h, l = ax.get_legend_handles_labels()
        if h:
            handles, labels = h, l
            break
    for ax in axes:
        leg = ax.get_legend()
        if leg:
            leg.remove()
    if handles:
        fig.legend(handles, labels, loc="center left",
                   bbox_to_anchor=(1.01, 0.5), fontsize=9, frameon=False)


# ── Figure 1 — OVAT Sensitivity ───────────────────────────────────────────────

def fig1_ovat_sensitivity() -> None:
    panel_info = [
        ("ovat_set_A_ism_raw.csv",       "ism",       "ISM",       "Set A — ISM"),
        ("ovat_set_B_eat_gain_raw.csv",  "eat_gain",  "eat_gain",  "Set B — eat_gain"),
        ("ovat_set_C_init_food_raw.csv", "init_food", "init_food", "Set C — init_food"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.patch.set_facecolor("white")

    for ax, (fname, col, xlabel, title) in zip(axes, panel_info):
        rows = load_csv(OUT_DIR / fname)
        if not rows:
            style_axes(ax, xlabel=xlabel, title=title)
            continue

        groups = group_by(rows, col)
        xs     = sorted(groups.keys())

        m_mus, m_sds   = [], []
        cd_mus, cd_sds = [], []
        for x in xs:
            g = groups[x]
            mm, ms = mu_sd(g, "mother_survival")
            cm, cs = mu_sd(g, "child_death_tick_mean")
            m_mus.append(mm);  m_sds.append(ms)
            cd_mus.append(cm); cd_sds.append(cs)

        xs_a = np.array(xs)
        m_a  = np.array(m_mus);  m_s  = np.array(m_sds)
        cd_a = np.array(cd_mus); cd_s = np.array(cd_sds)
        cd_n = cd_a / MAX_TICKS

        ax.plot(xs_a, m_a, "o-", color=C_RED, lw=2, ms=5, label="mother survival")
        ax.fill_between(xs_a,
                        np.clip(m_a - m_s, 0, 1),
                        np.clip(m_a + m_s, 0, 1),
                        alpha=0.15, color=C_RED)

        ax.plot(xs_a, cd_n, "s--", color=C_BLUE, lw=2, ms=5,
                label="child longevity / 400")
        ax.fill_between(xs_a,
                        np.clip(cd_n - cd_s / MAX_TICKS, 0, 1),
                        np.clip(cd_n + cd_s / MAX_TICKS, 0, 1),
                        alpha=0.12, color=C_BLUE)

        ax.axhline(200 / MAX_TICKS, color=C_DARK, lw=1, ls=":",
                   label="maturity threshold")

        ax.set_ylim(-0.03, 1.08)
        ax.legend(loc="upper left", fontsize=9)  # temp — replaced by shared legend
        style_axes(ax, xlabel=xlabel, ylabel="Rate / normalised tick", title=title)

    _shared_legend(fig, axes)
    fig.suptitle("Phase 3b — OVAT sensitivity  (mother survival and child longevity)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    save_fig(fig, "ovat_sensitivity.png")


# ── Figure 2 — Action Rate ─────────────────────────────────────────────────────

def fig2_action_rate() -> None:
    panel_info = [
        ("ovat_set_A_ism_raw.csv",       "ism",       "ISM",       "Set A — ISM"),
        ("ovat_set_B_eat_gain_raw.csv",  "eat_gain",  "eat_gain",  "Set B — eat_gain"),
        ("ovat_set_C_init_food_raw.csv", "init_food", "init_food", "Set C — init_food"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.patch.set_facecolor("white")

    for ax, (fname, col, xlabel, title) in zip(axes, panel_info):
        rows = load_csv(OUT_DIR / fname)
        if not rows:
            style_axes(ax, xlabel=xlabel, title=title)
            continue

        groups = group_by(rows, col)
        xs     = sorted(groups.keys())

        care_m, forage_m, self_m = [], [], []
        for x in xs:
            g = groups[x]
            care_m.append(np.mean([r["care_pct"]   for r in g]))
            forage_m.append(np.mean([r["forage_pct"] for r in g]))
            self_m.append(np.mean([r["self_pct"]   for r in g]))

        xs_a = np.array(xs)
        ax.stackplot(xs_a,
                     np.array(care_m),
                     np.array(forage_m),
                     np.array(self_m),
                     labels=["CARE", "FORAGE", "SELF"],
                     colors=[C_CARE, C_FORAGE, C_SELF],
                     alpha=0.85)

        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter())
        ax.legend(loc="upper right", fontsize=9)  # temp — replaced by shared legend
        style_axes(ax, xlabel=xlabel, ylabel="Action share (%)", title=title)

    _shared_legend(fig, axes)
    fig.suptitle("Phase 3b — Action rate  (CARE / FORAGE / SELF)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    save_fig(fig, "action_rate.png")


# ── Figure 3 — Feasibility Heatmap ────────────────────────────────────────────

def fig3_feasibility_heatmap() -> None:
    rows = load_csv(OUT_DIR / "grid_sweep.csv")
    if not rows:
        return

    isms      = sorted(SWEEP_GRID["infant_starvation_multiplier"])
    eat_gains = sorted(SWEEP_GRID["eat_gain"])

    heat = np.zeros((len(isms), len(eat_gains)))
    for i, ism in enumerate(isms):
        for j, eg in enumerate(eat_gains):
            vals = [r["child_death_mu"] for r in rows
                    if abs(r["ism"] - ism) < 1e-6 and abs(r["eat_gain"] - eg) < 1e-6]
            heat[i, j] = np.mean(vals) if vals else 0.0

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("white")

    im = ax.imshow(heat, aspect="auto", origin="lower",
                   vmin=0, vmax=MAX_TICKS,
                   cmap="Blues",
                   extent=[-0.5, len(eat_gains) - 0.5,
                           -0.5, len(isms) - 0.5])

    cbar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.046)
    cbar.set_label("Mean child longevity (ticks, avg over init_food)", fontsize=10)

    for i in range(len(isms)):
        for j in range(len(eat_gains)):
            val = heat[i, j]
            ax.text(j, i, f"{val:.0f}",
                    ha="center", va="center", fontsize=10,
                    color="white" if val > 220 else C_DARK,
                    fontweight="bold")

    ax.set_xticks(range(len(eat_gains)))
    ax.set_xticklabels([str(eg) for eg in eat_gains])
    ax.set_yticks(range(len(isms)))
    ax.set_yticklabels([str(ism) for ism in isms])
    style_axes(ax, xlabel="eat_gain", ylabel="ISM",
               title="Mean child longevity by ISM and eat_gain")
    fig.suptitle("Phase 3b — Feasibility heatmap  (ISM × eat_gain)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    save_fig(fig, "feasibility_heatmap.png")


# ── Figure 4 — Validation timeseries (4 individual plots) ─────────────────────

def _plot_timeseries_panel(y_mu, y_sd, y_mat, ticks, n,
                           ylabel, title, fname, color, ylim,
                           vline=None, y_locator=None) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("white")

    for row in y_mat:
        ax.plot(ticks, row[:n], color=C_GREY, lw=0.5, alpha=0.35)

    ax.plot(ticks, y_mu[:n], color=color, lw=2, label="mean")
    ax.fill_between(ticks,
                    np.clip(y_mu[:n] - y_sd[:n], ylim[0], ylim[1]),
                    np.clip(y_mu[:n] + y_sd[:n], ylim[0], ylim[1]),
                    alpha=0.15, color=color, label="±1 SD")

    if vline is not None:
        ax.axvline(vline, color=C_DARK, lw=1.2, ls="--", label=f"tick {vline}")

    if y_locator is not None:
        ax.yaxis.set_major_locator(y_locator)

    ax.set_ylim(ylim)
    ax.legend(loc="upper right", fontsize=9)
    style_axes(ax, xlabel="Simulation tick", ylabel=ylabel, title=title)

    n_seeds = y_mat.shape[0]
    fig.suptitle(
        f"Phase 3b — best ecological regime — validation  "
        f"(ism={best_eco['ism']}, eat_gain={best_eco['eat_gain']}, "
        f"init_food={int(best_eco['init_food'])},  n={n_seeds})",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout()
    save_fig(fig, fname)


def fig4_validation_timeseries() -> None:
    print(f"  Running best ecological simulations for timeseries "
          f"({len(VALIDATION_SEEDS)} seeds)...")
    hist = collect_histories(
        best_eco["ism"], best_eco["eat_gain"], int(best_eco["init_food"]),
        VALIDATION_SEEDS,
    )

    ticks                        = np.arange(MAX_TICKS)
    mom_mu,  mom_sd,  mom_mat   = _stack(hist["mom_e"])
    chi_mu,  chi_sd,  chi_mat   = _stack(hist["child_e"])
    popm_mu, popm_sd, popm_mat  = _stack(hist["mom_pop"])
    popc_mu, popc_sd, popc_mat  = _stack(hist["child_pop"])
    n = MAX_TICKS

    _plot_timeseries_panel(
        mom_mu, mom_sd, mom_mat, ticks, n,
        ylabel="Mean energy", title="Mother energy",
        fname="mother_energy.png", color=C_RED,
        ylim=(-0.02, 1.08),
    )
    _plot_timeseries_panel(
        chi_mu, chi_sd, chi_mat, ticks, n,
        ylabel="Mean energy", title="Child energy",
        fname="child_energy.png", color=C_BLUE,
        ylim=(-0.05, 1.08), vline=200,
    )
    _plot_timeseries_panel(
        popm_mu, popm_sd, popm_mat, ticks, n,
        ylabel="Count", title="Mother population",
        fname="mother_population.png", color=C_RED,
        ylim=(0, 16), y_locator=mticker.MultipleLocator(3),
    )
    _plot_timeseries_panel(
        popc_mu, popc_sd, popc_mat, ticks, n,
        ylabel="Count", title="Child population",
        fname="child_population.png", color=C_BLUE,
        ylim=(0, 16), vline=200,
        y_locator=mticker.MultipleLocator(3),
    )


# ── Figure 5 — Care Trap — Child longevity by ISM ─────────────────────────────

def fig5_care_trap_scatter() -> None:
    rows = load_csv(OUT_DIR / "grid_sweep.csv")
    if not rows:
        return

    isms = sorted(SWEEP_GRID["infant_starvation_multiplier"])
    rng  = np.random.default_rng(42)

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("white")

    for ism in isms:
        sub    = [r for r in rows if abs(r["ism"] - ism) < 1e-6]
        y_vals = np.array([r["child_death_mu"] for r in sub])
        jitter = rng.uniform(-0.05, 0.05, size=len(y_vals))

        ax.scatter(np.full(len(y_vals), ism) + jitter, y_vals,
                   color=ISM_COLORS[ism], s=45,
                   alpha=0.7, edgecolors=C_DARK, linewidths=0.3,
                   zorder=3)

        mu  = np.mean(y_vals)
        err = np.std(y_vals)
        ax.errorbar(ism, mu, yerr=err,
                    fmt="D", color=ISM_COLORS[ism], ms=9,
                    markeredgecolor=C_DARK, markeredgewidth=0.8,
                    ecolor=C_DARK, elinewidth=1.2, capsize=4,
                    label=f"ISM = {ism}", zorder=5)

    ax.axhline(200, color=C_DARK, lw=1.2, ls="--", label="maturity threshold")

    ax.set_xticks(isms)
    ax.set_ylim(0, MAX_TICKS + 10)
    ax.legend(loc="upper right", fontsize=9)

    style_axes(ax, xlabel="ISM",
               ylabel="Ticks",
               title="Child longevity across parameter space")

    fig.suptitle("Phase 3b — Care trap evidence  (all grid combos)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    save_fig(fig, "care_trap_scatter.png")


# ── Master (called from run.py) ────────────────────────────────────────────────

def generate_all_plots(out_dir: Path, ovat_results: dict, grid_results: list,
                       val_results: dict, selected: dict) -> None:
    print("\n[Step 8] Generating plots...")
    fig1_ovat_sensitivity()
    fig2_action_rate()
    fig3_feasibility_heatmap()
    fig4_validation_timeseries()
    fig5_care_trap_scatter()
    print("  All plots done.")


# ── Standalone entry ───────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("Phase 3b — generating all plots from saved CSVs")
    fig1_ovat_sensitivity()
    fig2_action_rate()
    fig3_feasibility_heatmap()
    fig4_validation_timeseries()
    fig5_care_trap_scatter()
    print("Done.")


if __name__ == "__main__":
    main()
