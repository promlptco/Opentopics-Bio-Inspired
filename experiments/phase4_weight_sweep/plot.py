# experiments/phase4_weight_sweep/plot.py
"""
Phase 4 Weight Sweep — Evidence plots (academic white style).

Figures produced:
  1. threshold_curve.png     — C_matr and M_surv vs care_weight (primary result)
  2. ovat_sensitivity.png    — care / forage / self weight panels
  3. grid_heatmap.png        — care_weight × forage_weight → C_matr
  4a. mother_energy.png      — VIABLE_MIN validation: mother energy trajectory
  4b. child_energy.png       — VIABLE_MIN validation: child energy trajectory
  4c. mother_population.png  — VIABLE_MIN validation: mother population
  4d. child_population.png   — VIABLE_MIN validation: child population
  5. action_rate.png         — CARE / FORAGE / SELF% vs care_weight

Usage (standalone):
    python -m experiments.phase4_weight_sweep.plot
"""
import csv
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase4_weight_sweep.config import (
    SWEEP_GRID, OVAT_SWEEPS, VALIDATION_SEEDS,
    CARE_WEIGHT_VALUES, make_config,
)

OUT_DIR  = PROJECT_ROOT / "outputs" / "phase4_weight_sweep"
PLOT_DIR = OUT_DIR / "plots"
MAX_TICKS = 400
DPI       = 200

# ── Academic palette ──────────────────────────────────────────────────────────
C_RED    = "#b33a3a"
C_BLUE   = "#3a6fb3"
C_GREEN  = "#3a8f3a"
C_GREY   = "#999999"
C_DARK   = "#333333"
C_CARE   = "#3a6fb3"
C_FORAGE = "#5e8f45"
C_SELF   = "#c8c8c8"

# care_weight sequential blues
CW_COLORS = {
    0.1: "#deebf7", 0.2: "#c6dbef", 0.3: "#9ecae1", 0.4: "#6baed6",
    0.5: "#4292c6", 0.6: "#2171b5", 0.7: "#08519c", 0.8: "#08306b",
    0.9: "#041f5e", 1.0: "#020c2e",
}


# ── Style ──────────────────────────────────────────────────────────────────────

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
        ax.set_title(title, fontsize=12)


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

def collect_histories(care_weight: float, forage_weight: float,
                      self_weight: float, seeds: list[int]) -> dict:
    from simulation.simulation import Simulation
    hist = {"mom_e": [], "child_e": [], "mom_pop": [], "child_pop": []}
    for seed in seeds:
        cfg = make_config(care_weight, forage_weight, self_weight, seed)
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


# ── Figure 1 — care_weight threshold curve ────────────────────────────────────

def fig1_threshold_curve() -> None:
    rows = load_csv(OUT_DIR / "threshold_raw.csv")
    if not rows:
        return

    groups = group_by(rows, "care_weight")
    xs     = sorted(groups.keys())

    c_mus, c_sds = [], []
    m_mus, m_sds = [], []
    feed_mus     = []

    for x in xs:
        g = groups[x]
        cm, cs = mu_sd(g, "child_maturation")
        mm, ms = mu_sd(g, "mother_survival")
        c_mus.append(cm); c_sds.append(cs)
        m_mus.append(mm); m_sds.append(ms)
        feed_mus.append(np.mean([r["feeds_per_child"] for r in g]))

    xs_a = np.array(xs)
    c_a  = np.array(c_mus); c_s = np.array(c_sds)
    m_a  = np.array(m_mus); m_s = np.array(m_sds)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")

    # Left — C_matr and M_surv
    ax = axes[0]
    ax.plot(xs_a, c_a, "o-", color=C_BLUE, lw=2, ms=6, label="child maturation rate")
    ax.fill_between(xs_a,
                    np.clip(c_a - c_s, 0, 1),
                    np.clip(c_a + c_s, 0, 1),
                    alpha=0.15, color=C_BLUE)
    ax.plot(xs_a, m_a, "s--", color=C_RED, lw=2, ms=6, label="mother survival rate")
    ax.fill_between(xs_a,
                    np.clip(m_a - m_s, 0, 1),
                    np.clip(m_a + m_s, 0, 1),
                    alpha=0.12, color=C_RED)
    ax.axhline(0, color=C_DARK, lw=0.8, ls=":")
    ax.set_ylim(-0.03, 1.08)
    ax.legend(loc="upper left")
    style_axes(ax, xlabel="care_weight", ylabel="Rate",
               title="C_matr and M_surv vs care_weight")

    # Right — feeds per child
    ax2 = axes[1]
    ax2.bar(xs_a, feed_mus, width=0.18, color=C_BLUE, alpha=0.75,
            edgecolor=C_DARK, linewidth=0.5)
    ax2.axhline(8.4, color=C_RED, lw=1.5, ls="--",
                label="feeds needed (ISM=1.2, eat_gain=0.7)")
    ax2.set_xticks(xs_a)
    ax2.legend(loc="upper left")
    style_axes(ax2, xlabel="care_weight", ylabel="Mean feeds per child",
               title="Feeds delivered vs threshold")

    fig.suptitle("Phase 4 — care_weight threshold scan  (forage = self = 0.5, independent weights)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    save_fig(fig, "threshold_curve.png")


# ── Figure 2 — OVAT sensitivity ───────────────────────────────────────────────

def fig2_ovat_sensitivity() -> None:
    # xlabel shows the swept variable; fixed values shown in parentheses
    panel_info = [
        ("ovat_set_A_care_weight_raw.csv",  "care_weight",   "care_weight\n(forage=0.5, self=0.5 fixed)",   "Set A — care_weight"),
        ("ovat_set_B_forage_weight_raw.csv", "forage_weight", "forage_weight\n(care=0.5, self=0.5 fixed)",   "Set B — forage_weight"),
        ("ovat_set_C_self_weight_raw.csv",   "self_weight",   "self_weight\n(care=0.5, forage=0.5 fixed)",   "Set C — self_weight"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor("white")

    for ax, (fname, col, xlabel, title) in zip(axes, panel_info):
        rows = load_csv(OUT_DIR / fname)
        if not rows:
            style_axes(ax, xlabel=xlabel, title=title)
            continue

        groups = group_by(rows, col)
        xs     = sorted(groups.keys())

        c_mus, c_sds = [], []
        m_mus, m_sds = [], []
        for x in xs:
            g = groups[x]
            cm, cs = mu_sd(g, "child_maturation")
            mm, ms = mu_sd(g, "mother_survival")
            c_mus.append(cm); c_sds.append(cs)
            m_mus.append(mm); m_sds.append(ms)

        xs_a = np.array(xs)
        c_a  = np.array(c_mus); c_s = np.array(c_sds)
        m_a  = np.array(m_mus); m_s = np.array(m_sds)

        ax.plot(xs_a, c_a, "o-", color=C_BLUE, lw=2, ms=5, label="child maturation")
        ax.fill_between(xs_a,
                        np.clip(c_a - c_s, 0, 1),
                        np.clip(c_a + c_s, 0, 1),
                        alpha=0.15, color=C_BLUE)
        ax.plot(xs_a, m_a, "s--", color=C_RED, lw=2, ms=5, label="mother survival")
        ax.fill_between(xs_a,
                        np.clip(m_a - m_s, 0, 1),
                        np.clip(m_a + m_s, 0, 1),
                        alpha=0.12, color=C_RED)
        ax.axhline(0, color=C_DARK, lw=0.8, ls=":")
        ax.set_ylim(-0.03, 1.08)
        ax.legend(loc="upper left", fontsize=9)
        style_axes(ax, xlabel=xlabel, ylabel="Rate", title=title)

    fig.suptitle("Phase 4 — OVAT sensitivity  (C_matr and M_surv)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    save_fig(fig, "ovat_sensitivity.png")


# ── Figure 2b — Self-weight refinement ────────────────────────────────────────

def fig2b_self_refinement() -> None:
    rows = load_csv(OUT_DIR / "self_refinement_raw.csv")
    if not rows:
        return

    groups = group_by(rows, "self_weight")
    xs     = sorted(groups.keys())
    cw_val = rows[0]["care_weight"]
    fw_val = rows[0]["forage_weight"]

    c_mus, c_sds, m_mus, m_sds, j_mus = [], [], [], [], []
    for x in xs:
        g = groups[x]
        cm, cs = mu_sd(g, "child_maturation")
        mm, ms = mu_sd(g, "mother_survival")
        c_mus.append(cm); c_sds.append(cs)
        m_mus.append(mm); m_sds.append(ms)
        j_mus.append(cm * mm)

    xs_a = np.array(xs)
    c_a  = np.array(c_mus); c_s = np.array(c_sds)
    m_a  = np.array(m_mus); m_s = np.array(m_sds)
    j_a  = np.array(j_mus)

    best_idx = int(np.argmax(j_a))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("white")

    ax = axes[0]
    ax.plot(xs_a, c_a, "o-", color=C_BLUE, lw=2, ms=5, label="child maturation")
    ax.fill_between(xs_a, np.clip(c_a-c_s, 0, 1), np.clip(c_a+c_s, 0, 1),
                    alpha=0.15, color=C_BLUE)
    ax.plot(xs_a, m_a, "s--", color=C_RED, lw=2, ms=5, label="mother survival")
    ax.fill_between(xs_a, np.clip(m_a-m_s, 0, 1), np.clip(m_a+m_s, 0, 1),
                    alpha=0.12, color=C_RED)
    ax.axvline(xs_a[best_idx], color="#e6a817", lw=1.5, ls="--",
               label=f"best self={xs_a[best_idx]:.1f}")
    ax.set_ylim(-0.03, 1.08)
    ax.legend(fontsize=9)
    style_axes(ax, xlabel="self_weight", ylabel="Rate", title="C_matr and M_surv")

    ax2 = axes[1]
    ax2.plot(xs_a, j_a, "D-", color=C_GREEN, lw=2, ms=6)
    ax2.axvline(xs_a[best_idx], color="#e6a817", lw=1.5, ls="--",
                label=f"best self={xs_a[best_idx]:.1f}")
    ax2.set_ylim(bottom=0)
    ax2.legend(fontsize=9)
    style_axes(ax2, xlabel="self_weight", ylabel="Joint fitness (C_matr × M_surv)",
               title="Joint fitness")

    fig.suptitle(
        f"Phase 4 — self_weight refinement  (care={cw_val}, forage={fw_val} fixed)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout()
    save_fig(fig, "self_refinement.png")


# ── Figure 3 — Grid heatmap ───────────────────────────────────────────────────

def fig3_grid_heatmap() -> None:
    rows = load_csv(OUT_DIR / "grid_sweep.csv")
    if not rows:
        return

    cws  = sorted(SWEEP_GRID["care_weight"])
    fws  = sorted(SWEEP_GRID["forage_weight"])

    heat_c = np.zeros((len(cws), len(fws)))
    heat_m = np.zeros((len(cws), len(fws)))

    for i, cw in enumerate(cws):
        for j, fw in enumerate(fws):
            vals_c = [r["c_matr_mean"] for r in rows
                      if abs(r["care_weight"] - cw) < 1e-6
                      and abs(r["forage_weight"] - fw) < 1e-6]
            vals_m = [r["m_surv_mean"] for r in rows
                      if abs(r["care_weight"] - cw) < 1e-6
                      and abs(r["forage_weight"] - fw) < 1e-6]
            heat_c[i, j] = np.mean(vals_c) if vals_c else 0.0
            heat_m[i, j] = np.mean(vals_m) if vals_m else 0.0

    # Find OPTIMAL cell: highest joint fitness = c_matr × m_surv
    viable = [
        (i, j, heat_c[i, j], heat_m[i, j])
        for i in range(len(cws))
        for j in range(len(fws))
        if heat_c[i, j] > 0.0 and heat_m[i, j] >= 0.10
    ]
    opt_i, opt_j = None, None
    if viable:
        opt_i, opt_j, _, _ = max(viable, key=lambda x: x[2] * x[3])

    heat_j = heat_c * heat_m  # joint fitness

    fig, axes = plt.subplots(1, 3, figsize=(19, 6))
    fig.patch.set_facecolor("white")

    for ax, heat, label, cmap in [
        (axes[0], heat_c, "Child maturation rate",       "Blues"),
        (axes[1], heat_m, "Mother survival rate",        "Reds"),
        (axes[2], heat_j, "Joint fitness (C_matr×M_surv)", "Greens"),
    ]:
        vmax = max(0.02, float(heat.max()))
        fmt  = ".3f" if vmax < 0.1 else ".2f"
        im = ax.imshow(heat, aspect="auto", origin="lower",
                       vmin=0, vmax=vmax, cmap=cmap,
                       extent=[-0.5, len(fws) - 0.5, -0.5, len(cws) - 0.5])
        cbar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.046)
        cbar.set_label(label, fontsize=10)

        for i in range(len(cws)):
            for j in range(len(fws)):
                val = heat[i, j]
                ax.text(j, i, f"{val:{fmt}}",
                        ha="center", va="center", fontsize=9,
                        color="white" if val > 0.6 * vmax else C_DARK)

        # Mark OPTIMAL cell with a gold border on both panels
        if opt_i is not None:
            from matplotlib.patches import Rectangle
            rect = Rectangle(
                (opt_j - 0.5, opt_i - 0.5), 1.0, 1.0,
                linewidth=2.5, edgecolor="#e6a817", facecolor="none",
                zorder=5,
            )
            ax.add_patch(rect)
            # Label only on the C_matr panel (left)
            if label == "Child maturation rate":
                ax.text(
                    opt_j, opt_i + 0.38,
                    "OPTIMAL",
                    ha="center", va="center", fontsize=7.5,
                    color="#e6a817", fontweight="bold", zorder=6,
                )

        ax.set_xticks(range(len(fws)))
        ax.set_xticklabels([str(fw) for fw in fws])
        ax.set_yticks(range(len(cws)))
        ax.set_yticklabels([str(cw) for cw in cws])
        style_axes(ax, xlabel="forage_weight  (self_weight = 0.5 fixed)",
                   ylabel="care_weight", title=label)

    # Subtitle showing selected weights
    opt_label = ""
    if opt_i is not None:
        oc = cws[opt_i]; of = fws[opt_j]
        opt_label = f"  |  OPTIMAL: care={oc}, forage={of}, self=0.5"
    fig.suptitle(
        f"Phase 4 — care_weight × forage_weight grid  (self = 0.5 fixed, independent weights){opt_label}",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout()
    save_fig(fig, "grid_heatmap.png")


# ── Figure 4 — Validation timeseries ─────────────────────────────────────────

def _plot_timeseries_panel(y_mu, y_sd, y_mat, ticks, n,
                           ylabel, title, fname, color, ylim,
                           vline=None, y_locator=None,
                           suptitle="") -> None:
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
        ax.axvline(vline, color=C_DARK, lw=1.2, ls="--",
                   label=f"maturity (tick {vline})")

    if y_locator is not None:
        ax.yaxis.set_major_locator(y_locator)

    ax.set_ylim(ylim)
    ax.legend(loc="upper right", fontsize=9)
    style_axes(ax, xlabel="Simulation tick", ylabel=ylabel, title=title)
    if suptitle:
        fig.suptitle(suptitle, fontsize=12, fontweight="bold")
    fig.tight_layout()
    save_fig(fig, fname)


def fig4_validation_timeseries(selected: dict) -> None:
    cfg = selected.get("VIABLE_MIN") or selected.get("OPTIMAL")
    if cfg is None:
        print("  [skip] no regime for validation timeseries")
        return

    cw, fw, sw = cfg["care_weight"], cfg["forage_weight"], cfg["self_weight"]
    print(f"  Running validation simulations: care={cw}, forage={fw}, self={sw}, "
          f"n={len(VALIDATION_SEEDS)} seeds...")
    hist = collect_histories(cw, fw, sw, VALIDATION_SEEDS)

    ticks                       = np.arange(MAX_TICKS)
    mom_mu,  mom_sd,  mom_mat  = _stack(hist["mom_e"])
    chi_mu,  chi_sd,  chi_mat  = _stack(hist["child_e"])
    popm_mu, popm_sd, popm_mat = _stack(hist["mom_pop"])
    popc_mu, popc_sd, popc_mat = _stack(hist["child_pop"])
    n    = MAX_TICKS
    sup  = (f"Phase 4 VIABLE_MIN — care={cw}, forage={fw}, self={sw},  "
            f"n={len(VALIDATION_SEEDS)}")

    _plot_timeseries_panel(
        mom_mu, mom_sd, mom_mat, ticks, n,
        ylabel="Mean energy", title="Mother energy",
        fname="mother_energy.png", color=C_RED,
        ylim=(-0.02, 1.08), suptitle=sup,
    )
    _plot_timeseries_panel(
        chi_mu, chi_sd, chi_mat, ticks, n,
        ylabel="Mean energy", title="Child energy",
        fname="child_energy.png", color=C_BLUE,
        ylim=(-0.05, 1.08), vline=200, suptitle=sup,
    )
    _plot_timeseries_panel(
        popm_mu, popm_sd, popm_mat, ticks, n,
        ylabel="Count", title="Mother population",
        fname="mother_population.png", color=C_RED,
        ylim=(0, 16), y_locator=mticker.MultipleLocator(3), suptitle=sup,
    )
    _plot_timeseries_panel(
        popc_mu, popc_sd, popc_mat, ticks, n,
        ylabel="Count", title="Child population",
        fname="child_population.png", color=C_BLUE,
        ylim=(0, 16), vline=200,
        y_locator=mticker.MultipleLocator(3), suptitle=sup,
    )


# ── Figure 5 — Action rate vs care_weight ────────────────────────────────────

def fig5_action_rate() -> None:
    rows = load_csv(OUT_DIR / "threshold_raw.csv")
    if not rows:
        return

    groups = group_by(rows, "care_weight")
    xs     = sorted(groups.keys())

    care_m, forage_m, self_m = [], [], []
    for x in xs:
        g = groups[x]
        care_m.append(np.mean([r["care_pct"]   for r in g]))
        forage_m.append(np.mean([r["forage_pct"] for r in g]))
        self_m.append(np.mean([r["self_pct"]   for r in g]))

    xs_a = np.array(xs)
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("white")

    ax.stackplot(xs_a,
                 np.array(care_m),
                 np.array(forage_m),
                 np.array(self_m),
                 labels=["CARE", "FORAGE", "SELF"],
                 colors=[C_CARE, C_FORAGE, C_SELF],
                 alpha=0.85)

    ax.set_ylim(0, 100)
    ax.set_xticks(xs_a)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(loc="upper right", fontsize=9)
    style_axes(ax, xlabel="care_weight",
               ylabel="Action share (%)",
               title="CARE / FORAGE / SELF distribution vs care_weight bias")

    fig.suptitle("Phase 4 — Action rate  (forage = self = 0.5, independent weights)",
                 fontsize=13, fontweight="bold")
    fig.text(0.5, -0.02,
             "Note: choices logged only when child.distress ≥ 0.3 — CARE% is over-represented relative to all-tick average.",
             ha="center", fontsize=8, style="italic", color=C_GREY)
    fig.tight_layout()
    save_fig(fig, "action_rate.png")


# ── Master ────────────────────────────────────────────────────────────────────

def generate_all_plots(out_dir: Path, ovat_results: dict, threshold_results: list,
                       grid_results: list, val_results: dict, selected: dict) -> None:
    print("\n[Plots] Generating Phase 4 figures...")
    fig1_threshold_curve()
    fig2_ovat_sensitivity()
    fig2b_self_refinement()
    fig3_grid_heatmap()
    fig4_validation_timeseries(selected)
    fig5_action_rate()
    print("  All plots done.")


# ── Standalone ────────────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("Phase 4 — generating plots from saved CSVs")

    # Load selected.json to get VIABLE_MIN for timeseries
    selected: dict = {}
    json_path = OUT_DIR / "selected_weights.json"
    if json_path.exists():
        import json
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.get("regimes", {}).items():
            selected[k] = {
                "care_weight":   v["care_weight"],
                "forage_weight": v["forage_weight"],
                "self_weight":   v["self_weight"],
                "c_matr":        v["c_matr"],
                "m_surv":        v["m_surv"],
                "child_death_mu": v["child_death_mu"],
            }

    fig1_threshold_curve()
    fig2_ovat_sensitivity()
    fig3_grid_heatmap()
    fig4_validation_timeseries(selected)
    fig5_action_rate()
    print("Done.")


if __name__ == "__main__":
    main()
