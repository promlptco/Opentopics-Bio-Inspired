"""
Generate all academic-style figures for REPORT.md.
One consistent style applied to every figure.
Output: outputs/report_figures/
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
from scipy import stats

OUT   = Path("outputs/report_figures")
OUT.mkdir(parents=True, exist_ok=True)
BASE  = Path(".")

# ── Unified academic style ────────────────────────────────────────────────────
STYLE = {
    "font.family":          "serif",
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.grid":            True,
    "grid.alpha":           0.30,
    "grid.color":           "#bbbbbb",
    "grid.linestyle":       "--",
    "axes.labelsize":       12,
    "axes.titlesize":       12,
    "axes.titleweight":     "bold",
    "xtick.labelsize":      11,
    "ytick.labelsize":      11,
    "legend.fontsize":      10,
    "legend.framealpha":    0.85,
    "legend.edgecolor":     "#cccccc",
    "figure.dpi":           150,
    "figure.facecolor":     "white",
    "axes.facecolor":       "white",
}

COND_COLORS = {
    "mut_off_plast_off": "#4C72B0",
    "mut_on_plast_off":  "#55A868",
    "mut_off_plast_on":  "#C44E52",
    "mut_on_plast_on":   "#8172B2",
}
COND_LABELS = {
    "mut_off_plast_off": "Mut OFF / Plast OFF",
    "mut_on_plast_off":  "Mut ON / Plast OFF",
    "mut_off_plast_on":  "Mut OFF / Plast ON",
    "mut_on_plast_on":   "Mut ON / Plast ON",
}

# Extinction ticks per condition (hardcoded from summary JSONs — max_pop=500, mother_max_age=1000)
EXT_TICKS = {
    "mut_off_plast_off": [6019, 9824, 8641, 9271, 8759, 9247, 8481, 12897, 8841, 8966],
    "mut_on_plast_off":  [11289, 15324, 20762, 22707, 5116, 29975, 17239, 23970, 18900, 25703],
    "mut_off_plast_on":  [13021, 12273, 16488, 20081, 14162, 14565, 15040, 14438, 16433, 24923],
    "mut_on_plast_on":   [9459, 14054, 13561, 22227, 11324, 11392, 21546, 29214, 12986, 14808],
}

COND_DIRS = [
    ("mut_off_plast_off", "block2_main_mut_off_plast_off"),
    ("mut_on_plast_off",  "block2_main_mut_on_plast_off"),
    ("mut_off_plast_on",  "block2_main_mut_off_plast_on"),
    ("mut_on_plast_on",   "block2_main_mut_on_plast_on"),
]


def savefig(fig, name, **kw):
    fig.savefig(OUT / name, bbox_inches="tight", **kw)
    plt.close(fig)
    print(f"[ok] {name}")


def cliffs_delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    count = sum(1 if x > y else (-1 if x < y else 0) for x in a for y in b)
    return count / (len(a) * len(b))


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 1b ── Food Distribution Mechanism: uniform vs Shannon entropy
# ─────────────────────────────────────────────────────────────────────────────
def fig_food_distribution():
    W, H = 50, 50
    INIT_FOOD = 190
    N_TICKS = 400
    ALPHA = 0.02
    N_EAT = 20  # illustrative consumption rate

    def simulate(alpha, seed=42):
        rng = np.random.default_rng(seed)
        grid = np.zeros(W * H, dtype=bool)
        grid[rng.choice(W * H, size=INIT_FOOD, replace=False)] = True
        rate = alpha * np.log(2) if alpha > 0 else 0
        counts = []
        for _ in range(N_TICKS):
            counts.append(int(grid.sum()))
            food_idx = np.where(grid)[0]
            if len(food_idx):
                grid[rng.choice(food_idx, size=min(N_EAT, len(food_idx)), replace=False)] = False
            if alpha == 0:
                n_ate = min(N_EAT, len(food_idx))
                empty_idx = np.where(~grid)[0]
                if len(empty_idx) >= n_ate:
                    grid[rng.choice(empty_idx, size=n_ate, replace=False)] = True
            else:
                empty_mask = ~grid
                grid[empty_mask & (rng.random(W * H) < rate)] = True
        return np.array(counts), grid.reshape(W, H)

    counts0, snap0 = simulate(0.0)
    counts2, snap2 = simulate(ALPHA)

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(11, 9), constrained_layout=True)

        # (a) α=0 grid snapshot
        ax = axes[0, 0]
        fx0, fy0 = np.where(snap0)
        ax.scatter(fx0, fy0, s=6, c="#4C72B0", alpha=0.85)
        ax.set_xlim(-1, W); ax.set_ylim(-1, H); ax.set_aspect("equal")
        ax.set_facecolor("#F7F7F7")
        ax.set_title(f"(a) α = 0.0 — Uniform respawn\n"
                     f"{snap0.sum()} / {W*H} cells  ({100*snap0.mean():.1f}% coverage)")
        ax.set_xlabel("Grid x"); ax.set_ylabel("Grid y")

        # (b) α=0.02 grid snapshot
        ax = axes[0, 1]
        fx2, fy2 = np.where(snap2)
        ax.scatter(fx2, fy2, s=6, c="#55A868", alpha=0.85)
        ax.set_xlim(-1, W); ax.set_ylim(-1, H); ax.set_aspect("equal")
        ax.set_facecolor("#F7F7F7")
        ss_count = int(np.mean(counts2[-50:]))
        ax.set_title(f"(b) α = 0.02 — Shannon entropy\n"
                     f"{snap2.sum()} / {W*H} cells  ({100*snap2.mean():.1f}% coverage)")
        ax.set_xlabel("Grid x"); ax.set_ylabel("Grid y")

        # (c) Food count over time
        ax = axes[1, 0]
        t = np.arange(N_TICKS)
        ax.plot(t, counts0, color="#4C72B0", linewidth=1.8, label="α = 0.0 (uniform)")
        ax.plot(t, counts2, color="#55A868", linewidth=1.8, label="α = 0.02 (Shannon)")
        ax.axhline(INIT_FOOD, color="#4C72B0", linestyle="--", linewidth=0.9, alpha=0.55,
                   label=f"init_food = {INIT_FOOD}")
        ax.set_xlabel("Simulation tick")
        ax.set_ylabel("Food cells on grid")
        ax.set_title("(c) Food count dynamics")
        ax.legend(fontsize=9, loc="center right")
        ax.set_ylim(0, W * H + 100)

        # (d) Spawn probability per empty cell per tick vs α
        ax = axes[1, 1]
        alphas = np.linspace(0, 0.06, 300)
        rates  = alphas * np.log(2) * 100   # percent
        ax.plot(alphas, rates, color="#4C72B0", linewidth=2.0)
        ax.axvline(ALPHA, color="#55A868", linestyle="--", linewidth=1.3, alpha=0.85,
                   label=f"Balanced α = {ALPHA}")
        bal_rate = ALPHA * np.log(2) * 100
        ax.scatter([ALPHA], [bal_rate], color="#55A868", s=70, zorder=5)
        ax.annotate(f"  {bal_rate:.2f}% / cell / tick",
                    xy=(ALPHA, bal_rate), fontsize=9, va="center", color="#55A868")
        ax.set_xlabel("Entropy parameter α")
        ax.set_ylabel("Spawn probability per empty cell per tick (%)")
        ax.set_title("(d) Spawn rate = α · log(2)")
        ax.legend(fontsize=9)
        ax.set_ylim(bottom=0)

        fig.suptitle("Food Distribution Mechanism: Uniform Respawn vs Shannon Entropy",
                     fontsize=13, fontweight="bold")

    savefig(fig, "fig01b_food_distribution.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 2 ── Phase 2 Self-Survival Baseline (3 ecologies, data-driven)
# ─────────────────────────────────────────────────────────────────────────────
PH2_DIR = Path("outputs/phase2_survival_minimal/newmech_auto_1000_percept8")


def fig_ph2_baseline():
    ecologies = ["harsh", "balanced", "easy"]
    labels    = ["Harsh", "Balanced", "Easy"]
    colors    = ["#C44E52", "#4C72B0", "#55A868"]

    pop_data, energy_data, fail_data = [], [], []
    for eco in ecologies:
        df = pd.read_csv(PH2_DIR / f"validation_{eco}.csv")
        pop_data.append(df["final_pop"].values)
        energy_data.append(df["mean_energy"].values)
        forage_total = df["FORAGE"].replace(0, np.nan)
        fail_rate = df["FAILED_FORAGE"] / forage_total * 100
        fail_data.append(fail_rate.dropna().values)

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))

        for ax, data, ylabel, title in [
            (axes[0], pop_data,    "Final population (alive mothers)", "(a) Population"),
            (axes[1], energy_data, "Mean agent energy (0–1)",          "(b) Agent Energy"),
            (axes[2], fail_data,   "Failed forage rate (%)",           "(c) Foraging Pressure"),
        ]:
            bp = ax.boxplot(data, patch_artist=True, widths=0.5,
                            medianprops=dict(color="black", linewidth=2),
                            whiskerprops=dict(linewidth=1.2),
                            capprops=dict(linewidth=1.2),
                            flierprops=dict(marker="o", markersize=4, alpha=0.55, linestyle="none"))
            for patch, col in zip(bp["boxes"], colors):
                patch.set_facecolor(col)
                patch.set_alpha(0.72)
            ax.set_xticks(range(1, 4))
            ax.set_xticklabels(labels)
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.set_ylim(bottom=0)

        fig.suptitle("Self-Survival Baseline Across Three Ecological Difficulty Levels",
                     fontsize=13, fontweight="bold", y=1.02)
        fig.tight_layout()
    savefig(fig, "fig02_ph2_baseline.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 2b ── Phase 2 OVAT Sensitivity Analysis (4 parameters)
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph2_ovat():
    PH2_OVAT = PH2_DIR / "sensitivity_ovat"

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)

        # ── Panel (a): init_food — two lines: α=0.0 vs α=0.02 ────────────────
        ax = axes[0, 0]
        xcol = "param_value"

        df_a0 = pd.read_csv(PH2_OVAT / "set_A_fine_alpha0_init_food.csv")
        x0, y0, sd0 = df_a0[xcol].values, df_a0["tail_pop_mean"].values, df_a0["tail_pop_sd"].values
        ax.plot(x0, y0, "o-", color="#4C72B0", linewidth=1.8, markersize=6,
                markerfacecolor="#4C72B0", markeredgecolor="white", markeredgewidth=0.8,
                label="α = 0.0 (uniform respawn)")
        ax.fill_between(x0, np.maximum(0, y0 - sd0), y0 + sd0, color="#4C72B0", alpha=0.18)

        df_a2 = pd.read_csv(PH2_OVAT / "set_A_fine_alpha02_init_food.csv")
        x2, y2, sd2 = df_a2[xcol].values, df_a2["tail_pop_mean"].values, df_a2["tail_pop_sd"].values
        ax.plot(x2, y2, "s-", color="#C44E52", linewidth=1.8, markersize=6,
                markerfacecolor="#C44E52", markeredgecolor="white", markeredgewidth=0.8,
                label="α = 0.02 (Shannon entropy ON)")
        ax.fill_between(x2, np.maximum(0, y2 - sd2), y2 + sd2, color="#C44E52", alpha=0.15)

        ymax_a = float(np.max(np.concatenate([y0 + sd0, y2 + sd2])))
        ax.set_ylim(0, ymax_a + 1.5)
        ax.set_xlabel("Initial food cells")
        ax.set_ylabel("Tail-window population (mean ± SD)")
        ax.set_title("(a) Food abundance (init_food)")
        ax.legend(loc="upper left", fontsize=8.5)

        # ── Panel (b): eat_gain ───────────────────────────────────────────────
        ax = axes[0, 1]
        df_b = pd.read_csv(PH2_OVAT / "set_B_fine_eat_gain.csv")
        xb, yb, sdb = df_b[xcol].values, df_b["tail_pop_mean"].values, df_b["tail_pop_sd"].values
        ax.plot(xb, yb, "o-", color="#4C72B0", linewidth=1.8, markersize=6,
                markerfacecolor="#4C72B0", markeredgecolor="white", markeredgewidth=0.8)
        ax.fill_between(xb, np.maximum(0, yb - sdb), yb + sdb, color="#4C72B0", alpha=0.18)
        ax.set_xlabel("Energy gain per food")
        ax.set_ylabel("Tail-window population (mean ± SD)")
        ax.set_title("(b) Energy per food (eat_gain)")
        ax.set_ylim(bottom=0)

        # ── Panel (c): move_cost ──────────────────────────────────────────────
        ax = axes[1, 0]
        df_c = pd.read_csv(PH2_OVAT / "set_C_fine_move_cost.csv")
        xc, yc, sdc = df_c[xcol].values, df_c["tail_pop_mean"].values, df_c["tail_pop_sd"].values
        ax.plot(xc, yc, "o-", color="#4C72B0", linewidth=1.8, markersize=6,
                markerfacecolor="#4C72B0", markeredgecolor="white", markeredgewidth=0.8)
        ax.fill_between(xc, np.maximum(0, yc - sdc), yc + sdc, color="#4C72B0", alpha=0.18)
        ax.set_xlabel("Energy cost per move")
        ax.set_ylabel("Tail-window population (mean ± SD)")
        ax.set_title("(c) Movement cost (move_cost)")
        ax.set_ylim(bottom=0)

        # ── Panel (d): food patchiness α — single solid line ─────────────────
        ax = axes[1, 1]
        df_d = pd.read_csv(PH2_OVAT / "set_D_fine_food_entropy_alpha.csv")
        xd, yd, sdd = df_d[xcol].values, df_d["tail_pop_mean"].values, df_d["tail_pop_sd"].values
        ax.plot(xd, yd, "o-", color="#4C72B0", linewidth=1.8, markersize=6,
                markerfacecolor="#4C72B0", markeredgecolor="white", markeredgewidth=0.8)
        ax.fill_between(xd, np.maximum(0, yd - sdd), yd + sdd, color="#4C72B0", alpha=0.18)
        ax.set_xlabel("Entropy parameter α")
        ax.set_ylabel("Tail-window population (mean ± SD)")
        ax.set_title("(d) Food patchiness (α)")
        ax.set_ylim(bottom=0)

        fig.suptitle("OVAT Sensitivity: Parameter Effect on Population Stability",
                     fontsize=13, fontweight="bold")
    savefig(fig, "fig02b_ph2_ovat.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 2c ── Failed Forage Mechanism Explained
# Why does FAILED_FORAGE differ across ecologies?
# Panel (a): Forage action breakdown (PICK / MOVE / FAILED) — what failure means
# Panel (b): PICK rate vs failed_forage_rate per seed — food accessibility proxy
# Panel (c): Total food consumed (PICK count) vs population — consumption pressure
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph2_failed_forage():
    ECO_COLORS = {"harsh": "#C44E52", "balanced": "#4C72B0", "easy": "#55A868"}
    ECO_LABELS = {"harsh": "Harsh", "balanced": "Balanced", "easy": "Easy"}

    # Ecology parameters for annotation
    ECO_PARAMS = {
        "harsh":    dict(init_food=150, alpha=0.0,  move_cost=0.05,  pop=3.6),
        "balanced": dict(init_food=40,  alpha=0.02, move_cost=0.02,  pop=9.5),
        "easy":     dict(init_food=40,  alpha=0.02, move_cost=0.005, pop=13.5),
    }

    dfs = {}
    for eco in ["harsh", "balanced", "easy"]:
        df = pd.read_csv(PH2_DIR / f"validation_{eco}.csv")
        df["ff_rate"]   = df["FAILED_FORAGE"] / df["FORAGE"]
        df["pick_rate"] = df["PICK"]          / df["FORAGE"]
        df["move_rate"] = df["MOVE"]          / df["FORAGE"]
        df["ecology"]   = eco
        dfs[eco] = df

    # ── aggregate per ecology ─────────────────────────────────────────────────
    agg = {}
    for eco, df in dfs.items():
        agg[eco] = {
            "pick_mean":  df["pick_rate"].mean(),
            "move_mean":  df["move_rate"].mean(),
            "ff_mean":    df["ff_rate"].mean(),
            "pick_std":   df["pick_rate"].std(),
            "move_std":   df["move_rate"].std(),
            "ff_std":     df["ff_rate"].std(),
            "pick_total": df["PICK"].mean(),
            "pop_mean":   df["final_pop"].mean(),
        }

    ecos = ["harsh", "balanced", "easy"]

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), constrained_layout=True)

        # ── (a) Stacked proportional bar — action breakdown ───────────────────
        ax = axes[0]
        x  = np.arange(len(ecos))
        w  = 0.55

        pick_vals = [agg[e]["pick_mean"] for e in ecos]
        move_vals = [agg[e]["move_mean"] for e in ecos]
        ff_vals   = [agg[e]["ff_mean"]   for e in ecos]

        bar_pick = ax.bar(x, pick_vals, w,
                          color="#55A868", alpha=0.88, label="PICK (on food)")
        bar_move = ax.bar(x, move_vals, w, bottom=pick_vals,
                          color="#4C72B0", alpha=0.75, label="MOVE toward food")
        bot_ff   = [p + m for p, m in zip(pick_vals, move_vals)]
        bar_ff   = ax.bar(x, ff_vals, w, bottom=bot_ff,
                          color="#C44E52", alpha=0.88, label="FAILED (no food visible)")

        # annotate FAILED % on top of each bar
        for i, (bot, val) in enumerate(zip(bot_ff, ff_vals)):
            ax.text(i, bot + val + 0.003, f"{val*100:.1f}%",
                    ha="center", va="bottom", fontsize=10, color="#C44E52", fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([ECO_LABELS[e] for e in ecos])
        ax.set_ylabel("Fraction of forage attempts")
        ax.set_ylim(0, 1.08)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
        ax.set_title("(a) Forage Action Breakdown")
        ax.legend(loc="lower left", fontsize=9)

        # ── (b) PICK rate vs failed_forage_rate per seed ─────────────────────
        ax = axes[1]
        for eco in ecos:
            df = dfs[eco]
            ax.scatter(df["pick_rate"] * 100, df["ff_rate"] * 100,
                       color=ECO_COLORS[eco], alpha=0.65, s=40, zorder=3,
                       label=ECO_LABELS[eco])
            mx = agg[eco]["pick_mean"] * 100
            my = agg[eco]["ff_mean"]   * 100
            ax.scatter(mx, my, color=ECO_COLORS[eco], s=120,
                       marker="D", edgecolors="white", linewidths=1.2, zorder=5)

        ax.set_xlabel("PICK rate (% of forage on food)")
        ax.set_ylabel("Failed forage rate (%)")
        ax.set_title("(b) Food Accessibility vs. Failure Rate")

        all_pick = np.concatenate([dfs[e]["pick_rate"].values for e in ecos])
        all_ff   = np.concatenate([dfs[e]["ff_rate"].values   for e in ecos])
        slope, intercept, r, p, _ = stats.linregress(all_pick * 100, all_ff * 100)
        xfit = np.linspace(all_pick.min() * 100, all_pick.max() * 100, 100)
        ax.plot(xfit, intercept + slope * xfit, "--", color="#888888",
                linewidth=1.2, alpha=0.7, label=f"Trend  r = {r:.2f}")
        # legend bottom-left, clear of the data cluster in upper-right
        ax.legend(loc="lower left", fontsize=9)

        # ── (c) Consumption pressure: PICK total vs population ────────────────
        ax = axes[2]
        for eco in ecos:
            df = dfs[eco]
            ax.scatter(df["final_pop"], df["PICK"],
                       color=ECO_COLORS[eco], alpha=0.60, s=40, zorder=3,
                       label=ECO_LABELS[eco])
            mx = agg[eco]["pop_mean"]
            my = agg[eco]["pick_total"]
            ax.scatter(mx, my, color=ECO_COLORS[eco], s=120,
                       marker="D", edgecolors="white", linewidths=1.2, zorder=5)

        ax.set_xlabel("Final population (alive mothers)")
        ax.set_ylabel("Total food consumed (PICK count)")
        ax.set_title("(c) Consumption Pressure by Ecology")
        # legend upper-left — data clusters are centre-right and far-right
        ax.legend(loc="upper left", fontsize=9)

        fig.suptitle(
            "Why Does Failed Forage Differ Across Ecologies?\n"
            "FAILED = no food visible within perception radius (r = 8 cells)",
            fontsize=12, fontweight="bold",
        )

    savefig(fig, "fig02c_ph2_failed_forage.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 3 ── Food Mechanism: Phase 2 vs Phase 3 population + child maturation
# ─────────────────────────────────────────────────────────────────────────────
def fig_food_mechanism():
    PH3_JSON = Path("outputs/phase3_food_comparison/exp_20260516_011140/summary.json")
    with open(PH3_JSON) as f:
        ph3 = json.load(f)["conditions"]

    alpha_labels = ["F0\n(α=0.00)", "F1\n(α=0.01)", "F2\n(α=0.05)", "F3\n(α=0.10)"]
    conds = ["F0", "F1", "F2", "F3"]

    # Phase 2 self-only (hardcoded from validated Phase 2 runs)
    p2_pop = [11.7, 8.8,  7.6,  6.8]
    p2_sd  = [0.9,  1.66, 2.01, 1.99]

    # Phase 3 — mothers + mature children, care enabled, reproduction disabled
    p3_pop  = [ph3[c]["tail_mean_pop"]              for c in conds]
    p3_matr = [ph3[c]["child_maturation_rate_mean"] for c in conds]
    p3_sd   = [ph3[c]["child_maturation_rate_sd"]   for c in conds]

    x   = np.arange(4)
    w   = 0.35
    C2  = "#4C72B0"   # Phase 2 blue
    C3  = "#55A868"   # Phase 3 green

    with plt.rc_context(STYLE):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)

        # ── (a) Phase 2 vs Phase 3 population grouped bars ───────────────────
        b2 = ax1.bar(x - w/2, p2_pop, w, yerr=p2_sd, color=C2, alpha=0.80,
                     capsize=4, error_kw=dict(elinewidth=1.2, ecolor="black"),
                     label="Phase 2 — self-only (mothers, care OFF)")
        b3 = ax1.bar(x + w/2, p3_pop, w, color=C3, alpha=0.80,
                     label="Phase 3 — with care (mothers + children)")

        for bar, v in zip(b2, p2_pop):
            ax1.text(bar.get_x() + bar.get_width()/2, v + 0.4, f"{v:.1f}",
                     ha="center", va="bottom", fontsize=9.5, color=C2)
        for bar, v in zip(b3, p3_pop):
            ax1.text(bar.get_x() + bar.get_width()/2, v + 0.4, f"{v:.1f}",
                     ha="center", va="bottom", fontsize=9.5, color=C3)

        ax1.set_xticks(x); ax1.set_xticklabels(alpha_labels)
        ax1.set_ylabel("Mean alive agents (tail window)")
        ax1.set_xlabel("Food distribution condition")
        ax1.set_title("(a) Population: Phase 2 vs Phase 3")
        ax1.set_ylim(0, 36)
        ax1.legend(fontsize=8.5, loc="upper left")

        # ── (b) Phase 3 child maturation rate ────────────────────────────────
        bar_col = ["#4C72B0", "#55A868", "#DD8452", "#C44E52"]
        bars2 = ax2.bar(x, p3_matr, 0.6, yerr=p3_sd, color=bar_col, alpha=0.82,
                        capsize=4, error_kw=dict(elinewidth=1.2, ecolor="black"))
        for bar, v in zip(bars2, p3_matr):
            ax2.text(bar.get_x() + bar.get_width()/2, v + 0.02, f"{v:.3f}",
                     ha="center", va="bottom", fontsize=11)
        ax2.set_xticks(x); ax2.set_xticklabels(alpha_labels)
        ax2.set_ylabel("Child maturation rate (fraction)")
        ax2.set_xlabel("Food distribution condition")
        ax2.set_title("(b) Child maturation rate (Phase 3)")
        ax2.set_ylim(0, 1.22)
        ax2.axhline(1.0, color="#999999", linestyle="--", linewidth=0.9)

        fig.suptitle(
            "Effect of Food Replenishment Rate (α) on Population and Child Maturation",
            fontsize=13, fontweight="bold")
    savefig(fig, "fig03_food_mechanism.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 3b ── Predator-Prey / Lotka-Volterra Analogy (analytical)
# ─────────────────────────────────────────────────────────────────────────────
def fig_predator_prey_vl():
    """Analytical Lotka-Volterra reference figure for the predator-prey analogy.

    Panels:
        (a) Time series — food (prey) and agents (predator) oscillate out of phase.
        (b) Phase portrait — closed orbit around the co-existence equilibrium.
    """
    from scipy.integrate import odeint

    def lv(state, t, r, a, b, d):
        F, A = state
        return [r * F - a * F * A, b * F * A - d * A]

    # Parameters chosen for clear, stable oscillations
    r, a, b, d = 1.0, 0.10, 0.075, 0.5
    # Equilibrium: F* = d/b, A* = r/a
    F_eq, A_eq = d / b, r / a
    t = np.linspace(0, 65, 4000)
    sol = odeint(lv, [10.0, 5.0], t, args=(r, a, b, d))
    F, A = sol[:, 0], sol[:, 1]

    # Find first peaks for lag annotation
    def first_peak(arr):
        for i in range(1, len(arr) - 1):
            if arr[i] > arr[i - 1] and arr[i] > arr[i + 1]:
                return i
        return None

    i_F = first_peak(F)
    i_A = first_peak(A)

    with plt.rc_context(STYLE):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)

        # ── Panel (a): time series ──────────────────────────────────────────
        ax1.plot(t, F, color="#4C72B0", lw=2.0, label="Food (prey)")
        ax1.plot(t, A, color="#C44E52", lw=2.0, label="Agents (predator)")
        ax1.set_xlabel("Time (arbitrary units)")
        ax1.set_ylabel("Count (normalised)")
        ax1.set_title("(a) Lotka-Volterra time series")
        ax1.legend(loc="upper right")

        if i_F is not None and i_A is not None:
            y_ann = max(F[i_F], A[i_A]) + 1.8
            ax1.annotate(
                "", xy=(t[i_A], A[i_A] + 0.8), xytext=(t[i_F], F[i_F] + 0.8),
                arrowprops=dict(arrowstyle="->", color="#888888", lw=1.2))
            ax1.text(
                (t[i_F] + t[i_A]) / 2, y_ann,
                "predator peak\nlags prey peak",
                ha="center", fontsize=9, color="#666666")

        # ── Panel (b): phase portrait ───────────────────────────────────────
        ax2.plot(F, A, color="#8172B2", lw=1.5, alpha=0.85, zorder=2)
        ax2.plot(F[0], A[0], "o", color="#55A868", ms=8, zorder=3, label="Start (F=10, A=5)")
        ax2.axvline(F_eq, color="#4C72B0", lw=1.0, linestyle="--", alpha=0.55,
                    label=f"F* = {F_eq:.1f}")
        ax2.axhline(A_eq, color="#C44E52", lw=1.0, linestyle="--", alpha=0.55,
                    label=f"A* = {A_eq:.0f}")
        ax2.set_xlabel("Food count (prey F)")
        ax2.set_ylabel("Agent count (predator A)")
        ax2.set_title("(b) Phase portrait — closed orbit")
        ax2.legend(loc="upper right", fontsize=9)
        ax2.annotate(
            f"Co-existence\nequilibrium",
            xy=(F_eq, A_eq), xytext=(F_eq + 1.8, A_eq + 2.5),
            arrowprops=dict(arrowstyle="->", color="#888888", lw=1.0),
            fontsize=9, color="#555555")

        fig.suptitle(
            "Theoretical Reference: Lotka-Volterra Predator-Prey Structure",
            fontsize=13, fontweight="bold")
    savefig(fig, "fig03b_predator_prey_vl.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 3c ── Predator-Prey from OUR simulation (SimpleLVSim)
# ─────────────────────────────────────────────────────────────────────────────
def fig_predator_prey_simulation():
    """Agent-based simulation echo of the LV predator-prey analogy.

    Uses SimpleLVSim (density-dependent Shannon spawn: -α·p·ln p) from the
    lv_ecology experiment — same codebase, best-oscillating parameters.

    Panels:
        (a) Normalised time series — food and agents oscillate out of phase.
        (b) Phase portrait from seed=42, coloured by simulation tick.
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(".").resolve()))
    from experiments.lv_ecology.lv_sweep import SimpleLVSim

    ALPHA  = 0.05
    HUNGER = 0.05
    GAMMA  = 0.002
    TICKS  = 3_000
    SEEDS  = list(range(42, 52))   # 10 seeds
    REC    = 5
    FOOD_C = "#2ca02c"   # green
    AGT_C  = "#1f77b4"   # blue

    all_food, all_agt = [], []
    for s in SEEDS:
        sim = SimpleLVSim(seed=s, alpha=ALPHA, hunger=HUNGER,
                          repro_cost=GAMMA, record_every=REC)
        ft, at = sim.run(TICKS)
        all_food.append(np.array(ft, float))
        all_agt.append(np.array(at, float))

    # use shortest run to handle early extinctions
    min_len = min(len(a) for a in all_food)
    all_food = np.array([a[:min_len] for a in all_food])
    all_agt  = np.array([a[:min_len] for a in all_agt])
    tick_axis = np.arange(min_len) * REC

    # normalise to grand means for same-axis comparison
    grand_f = all_food.mean()
    grand_a = all_agt.mean()
    norm_food = all_food / grand_f
    norm_agt  = all_agt / grand_a

    mf = norm_food.mean(0);  sf = norm_food.std(0)
    ma = norm_agt.mean(0);   sa = norm_agt.std(0)

    with plt.rc_context(STYLE):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5),
                                        constrained_layout=True)

        # ── Panel (a): normalised time series ──────────────────────────────
        ax1.fill_between(tick_axis, mf - sf, mf + sf,
                         color=FOOD_C, alpha=0.18)
        ax1.plot(tick_axis, mf, color=FOOD_C, lw=2.0, label="Food (normalised)")
        ax1.fill_between(tick_axis, ma - sa, ma + sa,
                         color=AGT_C, alpha=0.18)
        ax1.plot(tick_axis, ma, color=AGT_C, lw=2.0, label="Agents (normalised)")
        ax1.axhline(1.0, color="#aaaaaa", lw=0.8, linestyle="--")
        ax1.set_xlabel("Simulation tick")
        ax1.set_ylabel("Count / grand mean")
        ax1.set_title("(a) Agent-based simulation: time series")
        ax1.legend(loc="upper right")

        # ── Panel (b): phase portrait (seed=42) ────────────────────────────
        f0 = norm_food[0]
        a0 = norm_agt[0]
        pts   = len(f0)
        cmap  = plt.get_cmap("plasma")
        colors = cmap(np.linspace(0, 1, pts - 1))
        for i in range(pts - 1):
            ax2.plot(f0[i:i+2], a0[i:i+2], color=colors[i], lw=0.8, alpha=0.75)

        sm = plt.cm.ScalarMappable(cmap=cmap,
                                   norm=plt.Normalize(0, TICKS))
        sm.set_array([])
        cb = fig.colorbar(sm, ax=ax2, shrink=0.75, pad=0.02)
        cb.set_label("Simulation tick", fontsize=10)
        cb.ax.tick_params(labelsize=9)

        ax2.plot(f0[0], a0[0], "o", color="#55A868", ms=8, zorder=5,
                 label="Start (t = 0)")
        ax2.set_xlabel("Food (normalised)")
        ax2.set_ylabel("Agents (normalised)")
        ax2.set_title("(b) Phase portrait: simulation orbit")
        ax2.legend(loc="upper right", fontsize=9)

        fig.suptitle(
            "Agent-Based Simulation Echo: Same Predator-Prey Structure"
            f"\n(alpha={ALPHA}, hunger={HUNGER}, gamma={GAMMA},"
            f"  {len(SEEDS)} seeds x {TICKS:,} ticks)",
            fontsize=12, fontweight="bold")
    savefig(fig, "fig03c_predator_prey_simulation.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 4 ── Phase 4 Weight Sweep: care_weight vs outcomes
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph4_weight_sweep():
    # maturity_age=80 re-run (consistent with Phase 3, 4c, 5)
    df = pd.read_csv(BASE / "outputs/phase4_weight_sweep/sweep_20260519_224937/sweep_summary.csv")

    # Dynamic thresholds from sweep results
    viable = df[df["c_matr_mean"] >= 0.10].sort_values(["care_weight", "forage_weight"])
    viable_cw = float(viable.iloc[0]["care_weight"])   # 0.5
    opt_row   = df.sort_values(["c_matr_mean", "m_surv_mean"], ascending=False).iloc[0]
    opt_cw    = float(opt_row["care_weight"])           # 1.5

    with plt.rc_context(STYLE):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

        sc = ax1.scatter(df["care_weight"], df["c_matr_mean"],
                         c=df["forage_weight"], cmap="viridis_r",
                         s=65, alpha=0.85, edgecolors="white", linewidths=0.4)
        cb1 = fig.colorbar(sc, ax=ax1, shrink=0.85)
        cb1.set_label("Forage weight", fontsize=10)
        ax1.axvline(viable_cw, color="#2171b5", linestyle=":", linewidth=1.2, alpha=0.8,
                    label=f"Viable min (g_c = {viable_cw})")
        ax1.axvline(opt_cw, color="#C44E52", linestyle="--", linewidth=1.2, alpha=0.8,
                    label=f"Optimal (g_c = {opt_cw})")
        ax1.set_xlabel("Care weight (g_c)")
        ax1.set_ylabel("Child maturation rate")
        ax1.set_title("(a) Care weight vs. child maturation")

        sc2 = ax2.scatter(df["care_weight"], df["m_surv_mean"],
                          c=df["forage_weight"], cmap="viridis_r",
                          s=65, alpha=0.85, edgecolors="white", linewidths=0.4)
        cb2 = fig.colorbar(sc2, ax=ax2, shrink=0.85)
        cb2.set_label("Forage weight", fontsize=10)
        ax2.axvline(viable_cw, color="#2171b5", linestyle=":", linewidth=1.2, alpha=0.8,
                    label=f"Viable min (g_c = {viable_cw})")
        ax2.axvline(opt_cw, color="#C44E52", linestyle="--", linewidth=1.2, alpha=0.8,
                    label=f"Optimal (g_c = {opt_cw})")
        ax2.set_xlabel("Care weight (g_c)")
        ax2.set_ylabel("Adult pool ratio (final adults / initial)")
        ax2.set_title("(b) Care weight vs. adult pool ratio")

        fig.suptitle(
            "Genome Weight Sweep: Care Allocation vs. Fitness Outcomes  (maturity_age = 80)",
            fontsize=13, fontweight="bold", y=1.02,
        )
        fig.tight_layout()
    savefig(fig, "fig04_ph4_weight_sweep.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 5 ── Phase 5 Extinction Timing Comparison (box + strip)
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_extinction():
    keys   = list(EXT_TICKS.keys())
    data   = [np.array(EXT_TICKS[k]) / 1000 for k in keys]
    colors = [COND_COLORS[k] for k in keys]
    labels = [COND_LABELS[k].replace(" / ", "\n") for k in keys]
    rng    = np.random.default_rng(42)

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 5))
        bp = ax.boxplot(data, patch_artist=True, widths=0.45,
                        medianprops=dict(color="black", linewidth=2),
                        whiskerprops=dict(linewidth=1.2),
                        capprops=dict(linewidth=1.2),
                        flierprops=dict(marker="o", markersize=4, linestyle="none", alpha=0.6))
        for patch, col in zip(bp["boxes"], colors):
            patch.set_facecolor(col); patch.set_alpha(0.65)

        for i, (d, col) in enumerate(zip(data, colors), 1):
            jit = rng.uniform(-0.13, 0.13, size=len(d))
            ax.scatter(i + jit, d, color=col, s=30, zorder=4,
                       alpha=0.90, edgecolors="white", linewidths=0.5)
            med = np.median(d)
            ax.text(i + 0.30, med, f" {med:.1f}k", va="center", fontsize=9.5)

        ax.set_xticks(range(1, 5))
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_ylabel("Extinction tick (x10^3)")
        ax.set_xlabel("Experimental condition")
        ax.set_ylim(0, max(max(d) for d in data) * 1.18)
        fig.suptitle("Lineage Survival Duration Across Experimental Conditions",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig05_ph5_extinction.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 6 ── Phase 5: Population dynamics — all 4 conditions in 2×2 grid
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_population_4cond():
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=False, sharey=False)
        axes_flat = axes.flatten()

        for ax, (key, folder) in zip(axes_flat, COND_DIRS):
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            color = COND_COLORS[key]

            for seed, sdf in df.groupby("seed"):
                ax.plot(sdf["tick"] / 1000, sdf["n_mothers"], color=color,
                        alpha=0.22, linewidth=0.8)

            agg = df.groupby("tick")["n_mothers"].agg(["mean", "sem"]).reset_index()
            ax.plot(agg["tick"] / 1000, agg["mean"], color=color, linewidth=2.0,
                    label="Mean")
            ax.fill_between(agg["tick"] / 1000,
                            agg["mean"] - 1.96 * agg["sem"],
                            agg["mean"] + 1.96 * agg["sem"],
                            color=color, alpha=0.20)

            ax.set_title(COND_LABELS[key], fontsize=11)
            ax.set_xlabel("Tick (x10^3)", fontsize=10)
            ax.set_ylabel("Alive mothers", fontsize=10)
            ax.set_ylim(bottom=0)

        fig.suptitle("Mother Population Dynamics Across All Four Conditions",
                     fontsize=13, fontweight="bold", y=1.01)
        fig.tight_layout()
    savefig(fig, "fig06_ph5_population_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 7 ── Phase 5: Genome care weight — all 4 conditions overlaid
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_genome_care_4cond():
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))

        for key, folder in COND_DIRS:
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            df = df[df["n_mothers"] > 0]
            color = COND_COLORS[key]

            agg = df.groupby("tick")["mean_genome_care"].agg(["mean", "sem"]).reset_index()
            ax.plot(agg["tick"] / 1000, agg["mean"], color=color, linewidth=1.8,
                    label=COND_LABELS[key])
            ax.fill_between(agg["tick"] / 1000,
                            agg["mean"] - 1.96 * agg["sem"],
                            agg["mean"] + 1.96 * agg["sem"],
                            color=color, alpha=0.15)

        ax.axhline(1/3, color="#999999", linestyle="--", linewidth=1.0,
                   label="Neutral (1/3)")
        ax.set_xlabel("Tick (x10^3)")
        ax.set_ylabel("Mean genome care weight (g_c)")
        ax.set_ylim(0.25, 0.55)
        ax.legend(loc="upper left", fontsize=9)
        fig.suptitle("Genome Care Weight Evolution Across All Four Conditions",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig07_ph5_genome_care_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 8 ── Phase 5 (mut_on plast_on): Expressed vs Genome care
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_expressed_vs_genome():
    df = pd.read_csv(BASE / "outputs/phase5_evolution/block2_main_mut_on_plast_on/snapshots.csv")
    df = df[df["n_mothers"] > 0]

    agg = df.groupby("tick")[["mean_genome_care", "mean_expressed_care"]].agg(
        ["mean", "sem"]).reset_index()
    agg.columns = ["tick", "gc_mean", "gc_sem", "ec_mean", "ec_sem"]

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))

        ax.plot(agg["tick"] / 1000, agg["gc_mean"],
                color="#2166ac", linewidth=2.0, label="Genome care weight (g_c)")
        ax.fill_between(agg["tick"] / 1000,
                        agg["gc_mean"] - 1.96 * agg["gc_sem"],
                        agg["gc_mean"] + 1.96 * agg["gc_sem"],
                        color="#2166ac", alpha=0.15)

        ax.plot(agg["tick"] / 1000, agg["ec_mean"],
                color="#d6604d", linewidth=2.0, linestyle="--",
                label="Expressed care weight (w_c)")
        ax.fill_between(agg["tick"] / 1000,
                        agg["ec_mean"] - 1.96 * agg["ec_sem"],
                        agg["ec_mean"] + 1.96 * agg["ec_sem"],
                        color="#d6604d", alpha=0.15)

        ax.axhline(1/3, color="#888888", linestyle=":", linewidth=1.0,
                   label="Neutral (1/3)")
        ax.set_xlabel("Tick (x10^3)")
        ax.set_ylabel("Weight (0-1)")
        ax.legend(loc="upper right", fontsize=9)
        ax.set_ylim(0.0, 0.55)
        fig.suptitle("Genome vs. Expressed Care Weight Over Time  (Mut ON / Plast ON)",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig08_ph5_expressed_vs_genome.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 8b ── Genome vs Expressed: all three motivations (Mut ON / Plast ON)
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_expressed_vs_genome_all():
    """3-panel genome vs expressed for care, forage, self — shows which
    motivation plasticity dominates (largest genome-expressed gap)."""
    df = pd.read_csv(
        BASE / "outputs/phase5_evolution/block2_main_mut_on_plast_on/snapshots.csv")
    df = df[df["n_mothers"] > 0]

    motives = [
        ("care",   "mean_genome_care",   "mean_expressed_care",   "#2166ac", "#d6604d", "Care (g_c / w_c)"),
        ("forage", "mean_genome_forage", "mean_expressed_forage", "#1a9850", "#f4a582", "Forage (g_f / w_f)"),
        ("self",   "mean_genome_self",   "mean_expressed_self",   "#7b2d8b", "#fdae61", "Self (g_s / w_s)"),
    ]

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.5),
                                  sharey=False, constrained_layout=True)

        for ax, (name, g_col, e_col, g_color, e_color, title) in zip(axes, motives):
            agg = df.groupby("tick")[[g_col, e_col]].agg(
                ["mean", "sem"]).reset_index()
            agg.columns = ["tick", "g_mean", "g_sem", "e_mean", "e_sem"]

            ax.plot(agg["tick"] / 1000, agg["g_mean"],
                    color=g_color, lw=2.0, label="Genome")
            ax.fill_between(agg["tick"] / 1000,
                            agg["g_mean"] - 1.96 * agg["g_sem"],
                            agg["g_mean"] + 1.96 * agg["g_sem"],
                            color=g_color, alpha=0.15)

            ax.plot(agg["tick"] / 1000, agg["e_mean"],
                    color=e_color, lw=2.0, linestyle="--", label="Expressed")
            ax.fill_between(agg["tick"] / 1000,
                            agg["e_mean"] - 1.96 * agg["e_sem"],
                            agg["e_mean"] + 1.96 * agg["e_sem"],
                            color=e_color, alpha=0.15)

            ax.axhline(1/3, color="#aaaaaa", linestyle=":", lw=1.0, label="Neutral (1/3)")
            ax.set_title(title)
            ax.set_xlabel("Tick (x10^3)")
            ax.set_ylabel("Weight (0-1)")
            ax.legend(loc="upper right", fontsize=8)
            ax.set_ylim(0.0, 0.7)

        fig.suptitle(
            "Genome vs. Expressed Weight: All Three Motivations  (Mut ON / Plast ON)",
            fontsize=13, fontweight="bold")
    savefig(fig, "fig08b_ph5_expressed_vs_genome_all.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 9 ── Phase 5: Child survival rate — all 4 conditions overlaid
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_child_survival_4cond():
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))

        for key, folder in COND_DIRS:
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            df = df[(df["n_mothers"] > 0) & (df["tick"] > 0)]
            color = COND_COLORS[key]

            agg = df.groupby("tick")["child_survival_rate"].agg(["mean","sem"]).reset_index()
            agg["smoothed"] = agg["mean"].rolling(10, min_periods=1, center=True).mean()
            ax.plot(agg["tick"] / 1000, agg["smoothed"], color=color,
                    linewidth=1.8, label=COND_LABELS[key])
            ax.fill_between(agg["tick"] / 1000,
                            (agg["mean"] - 1.96 * agg["sem"]).clip(0),
                            (agg["mean"] + 1.96 * agg["sem"]).clip(1),
                            color=color, alpha=0.12)

        ax.set_xlabel("Tick (x10^3)")
        ax.set_ylabel("Child maturation rate (0-1)")
        ax.set_ylim(0, 1.0)
        ax.legend(loc="upper right", fontsize=9)
        fig.suptitle("Child Survival Rate Over Time — All Conditions",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig09_ph5_child_survival_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 10 ── Birth Scatter Radius Sensitivity
# ─────────────────────────────────────────────────────────────────────────────
def fig_birth_scatter_sensitivity():
    r2 = [9658,12423,14653,16696,17199,17135,17240,22182,11553,23003]
    r3 = [4824,4615,4681,3798,3295,3390,3643,3875,4168,3997]
    r5 = [4217,4583,5429,3994,4369,4374,4227,3765,3892,3266]
    data   = [np.array(d)/1000 for d in [r2, r3, r5]]
    labels = ["radius = 2\n(baseline)", "radius = 3", "radius = 5"]
    colors = ["#55A868", "#DD8452", "#C44E52"]
    rng    = np.random.default_rng(7)

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8, 5))
        bp = ax.boxplot(data, patch_artist=True, widths=0.45,
                        medianprops=dict(color="black", linewidth=2),
                        whiskerprops=dict(linewidth=1.2),
                        capprops=dict(linewidth=1.2),
                        flierprops=dict(marker="o", markersize=4, linestyle="none"))
        for patch, col in zip(bp["boxes"], colors):
            patch.set_facecolor(col); patch.set_alpha(0.65)
        for i, (d, col) in enumerate(zip(data, colors), 1):
            jit = rng.uniform(-0.12, 0.12, size=len(d))
            ax.scatter(i+jit, d, color=col, s=30, zorder=4,
                       alpha=0.90, edgecolors="white", linewidths=0.5)
            ax.text(i+0.28, np.median(d), f" {np.median(d):.1f}k",
                    va="center", fontsize=10)

        ax.annotate("", xy=(1.5, 6), xytext=(2.5, 6),
                    arrowprops=dict(arrowstyle="<->", color="#C44E52", lw=1.8))
        ax.text(2.0, 6.4, "Phase transition\n(radius 2->3: -60% survival)",
                ha="center", fontsize=9, color="#C44E52")

        ax.set_xticks(range(1, 4)); ax.set_xticklabels(labels, fontsize=11)
        ax.set_ylabel("Extinction tick (x10^3)")
        ax.set_xlabel("Birth scatter radius (cells)")
        fig.suptitle("Birth Scatter Radius Sensitivity Analysis",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig10_birth_scatter_sensitivity.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 11 ── Phase 5: Plasticity & Innateness — all 4 conditions
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_plasticity_4cond():
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(13, 8))
        axes_flat = axes.flatten()

        for ax, (key, folder) in zip(axes_flat, COND_DIRS):
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            df = df[df["n_mothers"] > 0]
            color = COND_COLORS[key]

            agg = df.groupby("tick")[["mean_plasticity","innateness_index"]].agg(
                ["mean","sem"]).reset_index()
            agg.columns = ["tick","pl_m","pl_s","in_m","in_s"]

            ax.plot(agg["tick"]/1000, agg["pl_m"], color="#2166ac",
                    linewidth=1.8, label="Plasticity coeff.")
            ax.fill_between(agg["tick"]/1000,
                            agg["pl_m"]-1.96*agg["pl_s"],
                            agg["pl_m"]+1.96*agg["pl_s"],
                            color="#2166ac", alpha=0.15)
            ax.plot(agg["tick"]/1000, agg["in_m"], color="#d6a920",
                    linewidth=1.8, linestyle="--", label="Innateness index")
            ax.fill_between(agg["tick"]/1000,
                            agg["in_m"]-1.96*agg["in_s"],
                            agg["in_m"]+1.96*agg["in_s"],
                            color="#d6a920", alpha=0.15)

            ax.set_title(COND_LABELS[key], fontsize=11)
            ax.set_xlabel("Tick (x10^3)", fontsize=10)
            ax.set_ylabel("Coefficient (0-1)", fontsize=10)
            ax.set_ylim(-0.05, 1.15)
            ax.legend(fontsize=8, loc="center right")

        fig.suptitle("Plasticity Coefficient and Innateness Index Across All Four Conditions",
                     fontsize=13, fontweight="bold", y=1.01)
        fig.tight_layout()
    savefig(fig, "fig11_ph5_plasticity_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 12 ── Phase 5: Generation depth — all 4 conditions overlaid
# ─────────────────────────────────────────────────────────────────────────────
def fig_ph5_generation_4cond():
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))

        for key, folder in COND_DIRS:
            df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
            df = df[df["n_mothers"] > 0]
            color = COND_COLORS[key]

            agg = df.groupby("tick")["highest_generation"].agg(["mean","sem"]).reset_index()
            ax.plot(agg["tick"]/1000, agg["mean"], color=color,
                    linewidth=1.8, label=COND_LABELS[key])
            ax.fill_between(agg["tick"]/1000,
                            agg["mean"]-1.96*agg["sem"],
                            agg["mean"]+1.96*agg["sem"],
                            color=color, alpha=0.15)

        ax.set_xlabel("Tick (x10^3)")
        ax.set_ylabel("Highest generation reached")
        ax.legend(loc="upper left", fontsize=9)
        fig.suptitle("Generational Depth Over Time — All Conditions",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig12_ph5_generation_4cond.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 13 ── Pairwise Mann-Whitney U + Cliff's delta matrix
# ─────────────────────────────────────────────────────────────────────────────
def fig_stat_pairwise():
    keys   = list(EXT_TICKS.keys())
    labels = [COND_LABELS[k] for k in keys]
    n      = len(keys)

    # Compute Cliff's delta and p-values for all pairs
    delta_mat = np.zeros((n, n))
    pval_mat  = np.ones((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                a, b = EXT_TICKS[keys[i]], EXT_TICKS[keys[j]]
                delta_mat[i, j] = cliffs_delta(a, b)
                _, pval_mat[i, j] = stats.mannwhitneyu(a, b, alternative="two-sided")

    def sig_stars(p):
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        return "ns"

    with plt.rc_context(STYLE):
        fig, (ax_heat, ax_bar) = plt.subplots(1, 2, figsize=(13, 5),
                                               gridspec_kw={"width_ratios": [1.2, 1]})

        # Left: Cliff's delta heatmap (upper triangle only)
        mask = np.triu(np.ones((n, n), dtype=bool), k=0)
        delta_disp = np.ma.array(delta_mat, mask=~mask)
        im = ax_heat.imshow(delta_disp, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        fig.colorbar(im, ax=ax_heat, shrink=0.80, label="Cliff's delta")

        for i in range(n):
            for j in range(i, n):
                if i == j:
                    ax_heat.text(j, i, labels[i].replace(" / ", "\n"),
                                 ha="center", va="center", fontsize=7.5,
                                 color="black", fontweight="bold")
                else:
                    d = delta_mat[i, j]
                    p = pval_mat[i, j]
                    ax_heat.text(j, i, f"d={d:+.2f}\n{sig_stars(p)}",
                                 ha="center", va="center", fontsize=9,
                                 color="white" if abs(d) > 0.5 else "black")

        ax_heat.set_xticks([]); ax_heat.set_yticks([])
        ax_heat.set_title("(a) Pairwise Cliff's delta (upper triangle)", fontsize=11)
        ax_heat.spines[:].set_visible(False)

        # Right: mean ± bootstrapped 95% CI per condition
        rng = np.random.default_rng(42)
        means, ci_lo, ci_hi = [], [], []
        for k in keys:
            d = np.array(EXT_TICKS[k]) / 1000
            boot = np.array([np.mean(rng.choice(d, len(d), replace=True)) for _ in range(10000)])
            means.append(np.mean(d))
            ci_lo.append(np.mean(d) - np.percentile(boot, 2.5))
            ci_hi.append(np.percentile(boot, 97.5) - np.mean(d))

        x = np.arange(n)
        colors = [COND_COLORS[k] for k in keys]
        short_labels = ["Mut-/Pl-", "Mut+/Pl-", "Mut-/Pl+", "Mut+/Pl+"]
        for i, (m, lo, hi, col) in enumerate(zip(means, ci_lo, ci_hi, colors)):
            ax_bar.barh(i, m, xerr=[[lo], [hi]], color=col, alpha=0.80,
                        capsize=5, error_kw=dict(elinewidth=1.5, ecolor="black"))
            ax_bar.text(m + hi + 0.3, i, f"{m:.1f}k", va="center", fontsize=10)

        ax_bar.set_yticks(x); ax_bar.set_yticklabels(short_labels, fontsize=10)
        ax_bar.set_xlabel("Extinction tick (x10^3)")
        ax_bar.set_title("(b) Mean with bootstrap 95% CI", fontsize=11)
        ax_bar.invert_yaxis()

        fig.suptitle("Pairwise Statistical Comparison — Extinction Tick by Condition",
                     fontsize=13, fontweight="bold", y=1.02)
        fig.tight_layout()
    savefig(fig, "fig13_stat_pairwise.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 14 ── Regression: genome care at t=2000 vs extinction tick
# ─────────────────────────────────────────────────────────────────────────────
def fig_stat_regression():
    TARGET_TICK = 2000
    records = []

    for key, folder in COND_DIRS:
        df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
        snap = df[df["tick"] == TARGET_TICK]
        for seed, sdf in snap.groupby("seed"):
            gc = sdf["mean_genome_care"].values[0]
            ext = EXT_TICKS[key]
            seeds_order = df["seed"].unique().tolist()
            seed_idx = seeds_order.index(seed) if seed in seeds_order else 0
            # extinction tick for this seed
            ext_tick = EXT_TICKS[key][seeds_order.index(seed)] if seed in seeds_order else np.nan
            records.append({"cond": key, "genome_care": gc, "ext_tick": ext_tick / 1000})

    rdf = pd.DataFrame(records).dropna()
    x = rdf["genome_care"].values
    y = rdf["ext_tick"].values

    slope, intercept, r, p, se = stats.linregress(x, y)
    n = len(x)
    t_crit = stats.t.ppf(0.975, df=n - 2)
    x_fit = np.linspace(x.min() - 0.005, x.max() + 0.005, 200)
    y_fit = intercept + slope * x_fit
    x_bar = x.mean()
    se_fit = se * np.sqrt(1/n + (x_fit - x_bar)**2 / np.sum((x - x_bar)**2))

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8, 5))

        for key in EXT_TICKS:
            sub = rdf[rdf["cond"] == key]
            ax.scatter(sub["genome_care"], sub["ext_tick"],
                       color=COND_COLORS[key], s=55, alpha=0.85,
                       edgecolors="white", linewidths=0.6,
                       label=COND_LABELS[key], zorder=4)

        ax.plot(x_fit, y_fit, color="#333333", linewidth=1.8, zorder=3)
        ax.fill_between(x_fit, y_fit - t_crit * se_fit, y_fit + t_crit * se_fit,
                        color="#888888", alpha=0.20, zorder=2)

        sign = "+" if slope >= 0 else "-"
        ax.text(0.97, 0.95,
                f"r = {r:.2f}   p = {p:.3f}\nslope = {slope:.1f}k / unit",
                ha="right", va="top", transform=ax.transAxes,
                fontsize=10, bbox=dict(facecolor="white", edgecolor="#cccccc", alpha=0.9))

        ax.set_xlabel("Genome care weight at t = 2000 (g_c)")
        ax.set_ylabel("Extinction tick (x10^3)")
        ax.legend(loc="upper left", fontsize=9)
        fig.suptitle("Early Genome Care vs. Lineage Survival Duration",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
    savefig(fig, "fig14_stat_regression.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 15 ── Spearman correlation heatmap across outcome variables
# ─────────────────────────────────────────────────────────────────────────────
def fig_stat_correlation():
    records = []

    for key, folder in COND_DIRS:
        df = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
        seeds_order = df["seed"].unique().tolist()
        ext_ticks   = EXT_TICKS[key]

        for i, seed in enumerate(seeds_order):
            if i >= len(ext_ticks):
                continue
            sdf = df[(df["seed"] == seed) & (df["n_mothers"] > 0)]
            if sdf.empty:
                continue
            snap_2000 = df[(df["seed"] == seed) & (df["tick"] == 2000)]
            gc_2000   = snap_2000["mean_genome_care"].values[0] if len(snap_2000) else np.nan

            records.append({
                "extinction_tick":       ext_ticks[i] / 1000,
                "genome_care_t2000":     gc_2000,
                "mean_child_survival":   sdf["child_survival_rate"].mean(),
                "genome_behav_distance": sdf["genome_behavior_distance"].mean(),
                "max_generation":        sdf["highest_generation"].max(),
            })

    rdf = pd.DataFrame(records).dropna()
    var_labels = [
        "Extinction\ntick",
        "Genome care\n(t=2000)",
        "Mean child\nsurvival",
        "Genome-behav\ndistance",
        "Max\ngeneration",
    ]
    cols = list(rdf.columns)

    n_vars = len(cols)
    rho_mat = np.zeros((n_vars, n_vars))
    p_mat   = np.ones((n_vars, n_vars))
    for i in range(n_vars):
        for j in range(n_vars):
            r, p = stats.spearmanr(rdf.iloc[:, i], rdf.iloc[:, j])
            rho_mat[i, j] = r
            p_mat[i, j]   = p

    def sig_stars(p):
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        return "ns"

    # Show lower triangle only
    mask = np.tril(np.ones((n_vars, n_vars), dtype=bool), k=0)

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8, 7))

        rho_disp = np.ma.array(rho_mat, mask=~mask)
        im = ax.imshow(rho_disp, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        fig.colorbar(im, ax=ax, shrink=0.80, label="Spearman rho")

        for i in range(n_vars):
            for j in range(i + 1):
                rho = rho_mat[i, j]
                p   = p_mat[i, j]
                txt_color = "white" if abs(rho) > 0.6 else "black"
                if i == j:
                    ax.text(j, i, var_labels[i], ha="center", va="center",
                            fontsize=9, fontweight="bold", color="black")
                else:
                    ax.text(j, i, f"{rho:+.2f}\n{sig_stars(p)}",
                            ha="center", va="center", fontsize=9.5, color=txt_color)

        ax.set_xticks(range(n_vars)); ax.set_yticks(range(n_vars))
        ax.set_xticklabels(var_labels, fontsize=9)
        ax.set_yticklabels(var_labels, fontsize=9)
        ax.spines[:].set_visible(False)

        fig.suptitle("Spearman Correlation Matrix — Phase 5 Outcome Variables",
                     fontsize=13, fontweight="bold", y=1.01)
        fig.tight_layout()
    savefig(fig, "fig15_stat_correlation.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 16 -- Lens 1: Ecological Validity
# 2-panel: care action rate (flat) vs child maturation rate (3.4x jump)
# ─────────────────────────────────────────────────────────────────────────────
def fig_lens1_ecological():
    alphas     = [0.0, 0.01, 0.05, 0.10]
    xlabels    = ["F0\n(uniform)", "F1\na=0.01", "F2\na=0.05", "F3\na=0.10"]
    care_rate  = [28.24, 28.62, 33.85, 33.10]
    maturation = [28.67, 49.33, 94.00, 96.00]
    mat_sd     = [10.77, 13.73,  6.29,  5.33]
    colors     = ["#aec7e8", "#6baed6", "#2171b5", "#08519c"]
    x = np.arange(4)

    with plt.rc_context(STYLE):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5),
                                       constrained_layout=True)

        # Left: care action rate
        bars1 = ax1.bar(x, care_rate, color=colors, width=0.6, edgecolor="white")
        ax1.set_xticks(x); ax1.set_xticklabels(xlabels, fontsize=10)
        ax1.set_ylabel("Care action rate (%)")
        ax1.set_ylim(0, 48)
        ax1.set_title("(a) Care action rate vs food patchiness", fontsize=11)
        for bar, v in zip(bars1, care_rate):
            ax1.text(bar.get_x() + bar.get_width() / 2, v + 0.5,
                     f"{v:.1f}%", ha="center", va="bottom", fontsize=10)
        ax1.axhline(y=care_rate[0], color="#999999", linewidth=1, linestyle="--", zorder=0)

        # Right: child maturation rate
        bars2 = ax2.bar(x, maturation, yerr=mat_sd, color=colors, width=0.6,
                        edgecolor="white", capsize=5,
                        error_kw=dict(elinewidth=1.5, ecolor="#444444"))
        ax2.set_xticks(x); ax2.set_xticklabels(xlabels, fontsize=10)
        ax2.set_ylabel("Child maturation rate (%)")
        ax2.set_ylim(0, 118)
        ax2.set_title("(b) Child maturation rate vs food patchiness", fontsize=11)
        for bar, v, sd in zip(bars2, maturation, mat_sd):
            ax2.text(bar.get_x() + bar.get_width() / 2, v + sd + 1.5,
                     f"{v:.1f}%", ha="center", va="bottom", fontsize=10)

        # Annotate 3.4x multiplier
        y0, y2 = maturation[0], maturation[2]
        mult = y2 / y0
        ax2.annotate(
            f"x{mult:.1f}",
            xy=(2, y2 + mat_sd[2] + 2),
            xytext=(2.5, 82),
            fontsize=12, fontweight="bold", color="#d62728",
            arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.5),
        )

        fig.suptitle(
            "Lens 1: Ecology Changes Return on Investment for Care, Not Care Allocation",
            fontsize=12, fontweight="bold",
        )
    savefig(fig, "fig16_lens1_ecological.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 17 -- Lens 2: Multi-Scale Fitness
# 3-panel: population (extinction tick), individual (maturation rate),
#          behavioral (genome care drift) -- all from Phase 5
# ─────────────────────────────────────────────────────────────────────────────
def fig_lens2_multiscale():
    keys       = ["mut_off_plast_off", "mut_on_plast_off",
                  "mut_off_plast_on",  "mut_on_plast_on"]
    short_lbl  = ["Mut-/Pl-", "Mut+/Pl-", "Mut-/Pl+", "Mut+/Pl+"]
    colors_bar = [COND_COLORS[k] for k in keys]

    # ── Panel A: population scale (mean extinction tick)
    pop_means = [np.mean(np.array(EXT_TICKS[k]) / 1000) for k in keys]
    pop_se    = [np.std(np.array(EXT_TICKS[k]) / 1000, ddof=1)
                 / np.sqrt(len(EXT_TICKS[k])) for k in keys]

    # ── Panel B: individual scale (mean maturation rate from lifecycle)
    ind_means, ind_se = [], []
    for _, folder in COND_DIRS:
        path = BASE / f"outputs/phase5_evolution/{folder}/mother_lifecycle.csv"
        df   = pd.read_csv(path)
        df   = df[df["total_children"] > 0].copy()
        df["mat_rate"] = df["matured_children"] / df["total_children"]
        seed_means = df.groupby("seed")["mat_rate"].mean()
        ind_means.append(seed_means.mean())
        ind_se.append(seed_means.std(ddof=1) / np.sqrt(len(seed_means)))

    # ── Panel C: behavioral scale (mean genome care at t=2000)
    beh_means, beh_se = [], []
    TARGET = 2000
    for _, folder in COND_DIRS:
        df  = pd.read_csv(BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv")
        sub = df[df["tick"] == TARGET]
        seed_vals = sub.groupby("seed")["mean_genome_care"].mean()
        beh_means.append(seed_vals.mean())
        beh_se.append(seed_vals.std(ddof=1) / np.sqrt(len(seed_vals)))

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), constrained_layout=True)
        y = np.arange(len(keys))

        for ax, means, ses, xlabel, title in [
            (axes[0], pop_means, pop_se,
             "Mean extinction tick (x10^3)",
             "(a) Population scale\nExtinction tick"),
            (axes[1], [v * 100 for v in ind_means],
             [s * 100 for s in ind_se],
             "Mean maturation rate (%)",
             "(b) Individual scale\nChild maturation rate"),
            (axes[2], [v * 100 for v in beh_means],
             [s * 100 for s in beh_se],
             "Genome care weight (%) at t=2000",
             "(c) Behavioral scale\nGenome care weight"),
        ]:
            ax.barh(y, means, xerr=ses, color=colors_bar, alpha=0.85,
                    capsize=5, error_kw=dict(elinewidth=1.5, ecolor="black"))
            ax.set_yticks(y)
            ax.set_yticklabels(short_lbl, fontsize=10)
            ax.set_xlabel(xlabel, fontsize=10)
            ax.set_title(title, fontsize=11)
            ax.invert_yaxis()

        fig.suptitle(
            "Lens 2: Multi-Scale Fitness Hierarchy Across All Four Conditions",
            fontsize=12, fontweight="bold",
        )
    savefig(fig, "fig17_lens2_multiscale.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 18 -- Lens 3: Baldwin co-evolution
# Dual-axis: genome care weight + child maturation rate per generation
# Shows both rising together -- direct evidence drift is adaptive not random
# Data: Mut ON / Plast ON condition, pooled across all seeds
# ─────────────────────────────────────────────────────────────────────────────
def fig_lens3_baldwin():
    path = BASE / "outputs/phase5_evolution/block2_main_mut_on_plast_on/mother_lifecycle.csv"
    df   = pd.read_csv(path)
    df   = df[df["total_children"] > 0].copy()
    df["mat_rate"] = df["matured_children"] / df["total_children"]

    # Aggregate per generation (pooled across seeds)
    def se(x):
        return x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0

    gen_agg = (
        df.groupby("generation")
        .agg(
            gc_mean  = ("final_genome_care", "mean"),
            gc_se    = ("final_genome_care", se),
            mat_mean = ("mat_rate",          "mean"),
            mat_se   = ("mat_rate",          se),
            n        = ("agent_id",          "count"),
        )
        .reset_index()
    )
    # Keep only generations with enough mothers for a stable mean
    gen_agg = gen_agg[gen_agg["n"] >= 5].copy()

    # Light smoothing (rolling 3-generation window) for visual clarity
    gen_agg["gc_smooth"]  = gen_agg["gc_mean"].rolling(3, min_periods=1, center=True).mean()
    gen_agg["mat_smooth"] = gen_agg["mat_mean"].rolling(3, min_periods=1, center=True).mean()

    c1 = "#2166ac"   # genome care — blue
    c2 = "#d6604d"   # maturation  — red-orange

    with plt.rc_context(STYLE):
        fig, ax1 = plt.subplots(figsize=(9, 5))

        # ── left axis: genome care weight
        ax1.plot(gen_agg["generation"], gen_agg["gc_smooth"],
                 color=c1, linewidth=2.2, label="Genome care weight (left axis)", zorder=4)
        ax1.fill_between(
            gen_agg["generation"],
            (gen_agg["gc_smooth"] - gen_agg["gc_se"]).clip(0.25),
            (gen_agg["gc_smooth"] + gen_agg["gc_se"]).clip(None, 0.60),
            color=c1, alpha=0.20, zorder=3,
        )
        ax1.axhline(1 / 3, color=c1, linewidth=1.0, linestyle=":",
                    alpha=0.6, label="Neutral baseline (1/3)")
        ax1.set_ylabel("Mean genome care weight", color=c1, fontsize=11)
        ax1.tick_params(axis="y", labelcolor=c1)
        ax1.set_ylim(0.25, 0.60)
        ax1.set_xlabel("Generation", fontsize=11)

        # ── right axis: maturation rate (ribbon capped to ±0.12 around smoothed line)
        ax2 = ax1.twinx()
        ax2.spines["right"].set_visible(True)
        ax2.spines["top"].set_visible(False)
        ax2.spines["left"].set_visible(False)
        ax2.plot(gen_agg["generation"], gen_agg["mat_smooth"],
                 color=c2, linewidth=2.2, linestyle="--",
                 label="Child maturation rate (right axis)", zorder=4)
        ribbon_cap = 0.12  # per-generation SE is large (0/1 outcomes); cap ribbon width
        ax2.fill_between(
            gen_agg["generation"],
            (gen_agg["mat_smooth"] - ribbon_cap).clip(0),
            (gen_agg["mat_smooth"] + ribbon_cap).clip(None, 1.0),
            color=c2, alpha=0.12, zorder=3,
        )
        ax2.set_ylabel("Mean child maturation rate (fitness proxy)", color=c2, fontsize=11)
        ax2.tick_params(axis="y", labelcolor=c2)
        ax2.set_ylim(0.0, 1.0)

        # Shared legend
        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9)

        fig.suptitle(
            "Lens 3: Genome Care and Fitness Co-evolve Across Generations (Mut ON / Plast ON)",
            fontsize=12, fontweight="bold",
        )
        fig.tight_layout()
    savefig(fig, "fig18_lens3_baldwin.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 20 -- Lens 3: Baldwin bottleneck — why assimilation is incomplete
# 3-panel: (a) surviving seeds per generation, (b) genome-care diversity collapse,
# (c) care-genome drift with OLS trend.  Bottleneck zone shaded across all panels.
# ─────────────────────────────────────────────────────────────────────────────
def fig_lens3_bottleneck():
    path = BASE / "outputs/phase5_evolution/block2_main_mut_on_plast_on/mother_lifecycle.csv"
    df   = pd.read_csv(path)
    df   = df[df["total_children"] > 0].copy()

    seeds_per_gen = (
        df.groupby("generation")["seed"].nunique().reset_index(name="n_seeds")
    )

    def se(x):
        return x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0

    gen_agg = (
        df.groupby("generation")
        .agg(gc_mean=("final_genome_care", "mean"),
             gc_std =("final_genome_care", "std"),
             gc_se  =("final_genome_care", se))
        .reset_index()
    )
    gen_agg = gen_agg.merge(seeds_per_gen, on="generation")
    gen_agg["gc_std"]   = gen_agg["gc_std"].fillna(0)
    gen_agg["gc_smooth"] = gen_agg["gc_mean"].rolling(3, min_periods=1, center=True).mean()

    # OLS trend on raw mean
    slope, intercept, _, p_val, _ = stats.linregress(
        gen_agg["generation"], gen_agg["gc_mean"]
    )
    trend_y = slope * gen_agg["generation"] + intercept

    # Bottleneck: fewer than 5 seeds still alive
    BT = 5
    bt_gens = gen_agg[gen_agg["n_seeds"] < BT]["generation"].values

    def shade_bt(ax):
        if len(bt_gens) == 0:
            return
        runs, s, prev = [], bt_gens[0], bt_gens[0]
        for g in bt_gens[1:]:
            if g - prev > 1:
                runs.append((s, prev))
                s = g
            prev = g
        runs.append((s, prev))
        first = True
        for s0, e0 in runs:
            ax.axvspan(s0 - 0.5, e0 + 0.5,
                       color="#ffcccc", alpha=0.40, zorder=0,
                       label="Bottleneck zone\n(<5 lineages)" if first else "_nolegend_")
            first = False

    c_pop  = "#4C72B0"
    c_div  = "#8172B2"
    c_care = "#2166ac"
    c_bt   = "#d62728"

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(3, 1, figsize=(10, 11), constrained_layout=True)

        # (a) Surviving lineages per generation
        ax = axes[0]
        shade_bt(ax)
        ax.bar(gen_agg["generation"], gen_agg["n_seeds"],
               color=c_pop, alpha=0.75, width=0.9, zorder=2)
        ax.axhline(BT, color=c_bt, linewidth=1.5, linestyle="--", zorder=3,
                   label=f"Critical threshold ({BT} lineages)")
        ax.set_yticks([0, 2, 4, 6, 8, 10])
        ax.set_ylabel("Surviving lineages (out of 10)", fontsize=10)
        ax.set_title("(a) Population extinction — surviving lineages per generation", fontsize=11)
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, fontsize=9)

        # (b) Genetic diversity (std dev of genome care)
        ax = axes[1]
        shade_bt(ax)
        ax.fill_between(gen_agg["generation"], 0, gen_agg["gc_std"],
                        color=c_div, alpha=0.35, zorder=1)
        ax.plot(gen_agg["generation"], gen_agg["gc_std"],
                color=c_div, linewidth=1.8, zorder=2)
        ax.set_ylabel("Std dev of genome care weight", fontsize=10)
        ax.set_title(
            "(b) Genetic diversity — collapses as surviving lineages fall below threshold",
            fontsize=11,
        )

        # (c) Care genome drift with OLS trend
        ax = axes[2]
        shade_bt(ax)
        ax.plot(gen_agg["generation"], gen_agg["gc_smooth"],
                color=c_care, linewidth=2.2, zorder=3,
                label="Mean genome care (3-gen rolling)")
        ax.fill_between(
            gen_agg["generation"],
            (gen_agg["gc_smooth"] - gen_agg["gc_se"]).clip(0.25),
            (gen_agg["gc_smooth"] + gen_agg["gc_se"]).clip(None, 0.55),
            color=c_care, alpha=0.18, zorder=2,
        )
        ax.plot(gen_agg["generation"], trend_y,
                color=c_care, linewidth=1.3, linestyle="--", alpha=0.65, zorder=3,
                label=f"OLS trend (+{slope*10:.4f} per 10 gen,  p = {p_val:.3f})")
        ax.axhline(1 / 3, color="gray", linewidth=1.0, linestyle=":",
                   alpha=0.70, label="Neutral baseline (1/3)")
        ax.set_ylabel("Mean genome care weight", fontsize=10)
        ax.set_title("(c) Care genome drift — directional but incomplete assimilation", fontsize=11)
        ax.legend(fontsize=9)
        ax.set_ylim(0.25, 0.55)

        for ax in axes:
            ax.set_xlabel("Generation", fontsize=10)

        fig.suptitle(
            "Lens 3: Why Baldwin Assimilation Remained Incomplete\n"
            "Bottleneck zones erase genetic diversity before selection can fix care genes",
            fontsize=12, fontweight="bold",
        )
    savefig(fig, "fig20_lens3_bottleneck.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 19 -- Lens 2: Multi-Scale Fitness Over Time
# 3-panel time series: population size, child survival rate, genome care weight
# All four conditions plotted as mean +/- SE ribbons across seeds over ticks
# ─────────────────────────────────────────────────────────────────────────────
def fig_lens2_overtime():
    frames = []
    for cond, folder in COND_DIRS:
        p = BASE / f"outputs/phase5_evolution/{folder}/snapshots.csv"
        df = pd.read_csv(p)
        df["cond"] = cond
        frames.append(df)
    all_df = pd.concat(frames, ignore_index=True)

    def tick_agg(sub, col, smooth=False, min_seeds=5):
        grp = (
            sub.groupby("tick")[col]
            .agg(m="mean", s="std", n="count")
            .reset_index()
        )
        grp = grp[grp["n"] >= min_seeds].copy()
        grp["se"] = grp["s"] / np.sqrt(grp["n"])
        if smooth:
            grp["m"] = grp["m"].rolling(7, min_periods=1, center=True).mean()
        return grp

    # (panel_letter, col, ylabel, smooth, add_baseline, ylim)
    panels = [
        ("(a)", "population_size",     "Population size (mothers + children)", False, False, None),
        ("(b)", "child_survival_rate", "Child survival rate (7-tick rolling)",  True,  False, None),
        ("(c)", "mean_genome_care",    "Mean genome care weight",               False, True,  (0.29, 0.43)),
    ]

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(3, 1, figsize=(10, 11), constrained_layout=True)

        for ax, (lbl, col, ylabel, smooth, add_baseline, ylim) in zip(axes, panels):
            for cond in ["mut_off_plast_off", "mut_on_plast_off",
                         "mut_off_plast_on",  "mut_on_plast_on"]:
                sub = all_df[all_df["cond"] == cond].copy()
                agg = tick_agg(sub, col, smooth=smooth)
                x   = agg["tick"] / 1_000

                ax.plot(x, agg["m"],
                        color=COND_COLORS[cond], linewidth=1.8,
                        label=COND_LABELS[cond])
                ax.fill_between(
                    x,
                    (agg["m"] - agg["se"]).clip(0),
                    (agg["m"] + agg["se"]),
                    color=COND_COLORS[cond], alpha=0.13,
                )

            if add_baseline:
                ax.axhline(1 / 3, color="gray", linewidth=1.0, linestyle=":",
                           alpha=0.70, label="Neutral baseline (1/3)")

            if ylim is not None:
                ax.set_ylim(*ylim)

            ax.set_ylabel(ylabel, fontsize=10)
            ax.set_xlabel("Simulation tick (x10³)", fontsize=10)

            # panel letter as an in-axes annotation (top-left, never buried in y-label)
            ax.text(0.01, 0.97, lbl, transform=ax.transAxes,
                    va="top", ha="left", fontsize=11, fontweight="bold")

        axes[0].legend(fontsize=9, ncol=2, loc="upper right")

        fig.suptitle(
            "Lens 2: Multi-Scale Fitness Trajectories Over Time (all conditions)",
            fontsize=12, fontweight="bold",
        )
    savefig(fig, "fig19_lens2_overtime.png")


# ─────────────────────────────────────────────────────────────────────────────
# RUN ALL
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fig_food_distribution()
    fig_ph2_baseline()
    fig_ph2_ovat()
    fig_ph2_failed_forage()
    fig_food_mechanism()
    fig_predator_prey_vl()
    fig_predator_prey_simulation()
    fig_ph4_weight_sweep()
    fig_ph5_extinction()
    fig_ph5_population_4cond()
    fig_ph5_genome_care_4cond()
    fig_ph5_expressed_vs_genome()
    fig_ph5_expressed_vs_genome_all()
    fig_ph5_child_survival_4cond()
    fig_birth_scatter_sensitivity()
    fig_ph5_plasticity_4cond()
    fig_ph5_generation_4cond()
    fig_stat_pairwise()
    fig_stat_regression()
    fig_stat_correlation()
    fig_lens1_ecological()
    fig_lens2_multiscale()
    fig_lens2_overtime()
    fig_lens3_baldwin()
    fig_lens3_bottleneck()
    print("All figures saved to outputs/report_figures/")
