# experiments/p4_plasticity_intro/run_multi_seed.py
"""
Run Phase 4b (kin-conditional Baldwin Effect) across 10 seeds and produce:
  - Per-seed full outputs (generation_snapshots, top_genomes, logs, plots)
  - Per-seed zero-shot transfer (zeroshot_plastic_kin stage)
  - Phase 2 baselines: Phase 3 genomes + no plasticity, per-seed (for paired stats)
  - Multi-seed CI plots: care_weight + learning_rate + forage, with Phase 3 overlay
  - Paired statistical tests (t-test + Wilcoxon) comparing Phase 4b vs Phase 2 window rates
  - Summary table with Baldwin Effect classification per seed

Hardened against:
  - Data loss: checkpoint saved after every seed
  - High variance: mean+CI plus per-seed Baldwin classification annotation
  - Baseline isolation: Phase 3 mean overlaid on CI plot panels
  - Statistical weakness: formal paired tests with p-value and Cohen's d
"""
import sys
import os
import json
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.p4_plasticity_intro.run import run as run_p4b
from experiments.p3_care_erosion.measure_baseline import run as run_p2zs
from utils.plotting import plot_start_vs_end_multiseed

try:
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        'font.size': 10, 'axes.titlesize': 10, 'axes.labelsize': 10,
        'xtick.labelsize': 9, 'ytick.labelsize': 9,
        'legend.fontsize': 9, 'legend.framealpha': 0.93, 'legend.edgecolor': '0.6',
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': 0.8, 'grid.alpha': 0.22, 'grid.linewidth': 0.5,
        'lines.linewidth': 2.0, 'figure.facecolor': 'white', 'axes.facecolor': 'white',
    })
except ImportError:
    plt = None

try:
    from scipy import stats as _scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("Warning: scipy not available — statistical tests will be skipped.")

SEEDS        = list(range(42, 52))
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase06_baldwin_effect", "multi_seed_evolution")
CHECKPOINT   = os.path.join(COMBINED_DIR, "checkpoint.json")

# Phase 3 multi-seed manifest (for baseline overlay + Phase 2 paired baselines)
P3_RUN_DIRS_JSON = os.path.join(
    PROJECT_ROOT, "outputs", "phase04_care_erosion", "multi_seed_evolution", "run_dirs.json"
)

# Baldwin Effect classification thresholds
BALDWIN_RECOVERY_MIN = 0.03   # care_weight must recover >= 0.03 from trough to final
BALDWIN_LR_MIN       = 0.03   # learning_rate must increase >= 0.03 from start to final

MATURITY_AGE = 100            # config.maturity_age


# =============================================================================
# Helpers
# =============================================================================

def _load_snapshots(run_dir: str) -> list[dict]:
    path = os.path.join(run_dir, "generation_snapshots.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _load_zeroshot_metrics(run_dir: str) -> dict:
    path = os.path.join(run_dir, "zeroshot_metrics.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def _care_window_rate_from_dir(run_dir: str) -> float:
    """Extract care-window rate from a zero-shot run dir."""
    m = _load_zeroshot_metrics(run_dir)
    w = m.get("care_window", {})
    return w.get("care_per_mother_tick_in_window", 0.0)


def _ci95(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return 1.96 * math.sqrt(variance / n)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _classify_baldwin(snaps: list[dict]) -> dict:
    """
    Classify a seed as showing Baldwin Effect based on:
      - care_weight recovered: min(care) to final(care) >= BALDWIN_RECOVERY_MIN
      - learning_rate swept: final(lr) - first(lr) >= BALDWIN_LR_MIN
    Returns dict with classification details.
    """
    if not snaps:
        return {"is_baldwin": False, "reason": "no snapshots"}

    care_vals = [s["avg_care_weight"]   for s in snaps]
    lr_vals   = [s["avg_learning_rate"] for s in snaps]

    trough        = min(care_vals)
    final_care    = care_vals[-1]
    recovery      = final_care - trough
    lr_start      = lr_vals[0]
    lr_final      = lr_vals[-1]
    lr_delta      = lr_final - lr_start

    care_recovered = recovery >= BALDWIN_RECOVERY_MIN
    lr_swept       = lr_delta >= BALDWIN_LR_MIN

    return {
        "is_baldwin":     care_recovered and lr_swept,
        "care_trough":    trough,
        "care_final":     final_care,
        "care_recovery":  recovery,
        "lr_start":       lr_start,
        "lr_final":       lr_final,
        "lr_delta":       lr_delta,
        "care_recovered": care_recovered,
        "lr_swept":       lr_swept,
    }


# =============================================================================
# Checkpoint helpers
# =============================================================================

def _load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {
        "completed_evo": [],
        "evo_run_dirs":  {},
        "evo_summaries": [],
        "completed_zs":  [],
        "zs_run_dirs":   {},
        "zs_summaries":  [],
    }


def _save_checkpoint(cp: dict) -> None:
    os.makedirs(COMBINED_DIR, exist_ok=True)
    with open(CHECKPOINT, "w") as f:
        json.dump(cp, f, indent=2)


# =============================================================================
# Load Phase 3 baselines for overlay
# =============================================================================

def _load_phase04_baselines() -> dict:
    """
    Load Phase 3 multi-seed snapshots and return mean trajectories per tick.
    Returns {tick: avg_care_weight} and {tick: avg_learning_rate}.
    """
    if not os.path.exists(P3_RUN_DIRS_JSON):
        return {}, {}

    with open(P3_RUN_DIRS_JSON) as f:
        rd = json.load(f)

    all_snaps = []
    for d in rd.get("run_dirs", []):
        snaps = _load_snapshots(d)
        if snaps:
            all_snaps.append(snaps)

    if not all_snaps:
        return {}, {}

    tick_sets    = [set(s["tick"] for s in snaps) for snaps in all_snaps]
    common_ticks = sorted(set.intersection(*tick_sets))

    care_by_tick = {}
    lr_by_tick   = {}
    for t in common_ticks:
        c_vals = [
            next(s["avg_care_weight"]   for s in snaps if s["tick"] == t)
            for snaps in all_snaps
        ]
        l_vals = [
            next(s.get("avg_learning_rate", 0.1) for s in snaps if s["tick"] == t)
            for snaps in all_snaps
        ]
        care_by_tick[t] = _mean(c_vals)
        lr_by_tick[t]   = _mean(l_vals)

    return care_by_tick, lr_by_tick


# =============================================================================
# Multi-seed CI plot (3 panels + Phase 3 overlay + Baldwin annotation)
# =============================================================================

def plot_multi_seed_ci(
    all_snapshots: list[list[dict]],
    seeds: list[int],
    output_dir: str,
    baldwin_classifications: list[dict] = None,
) -> None:
    """
    3-panel CI plot with Phase 3 baseline overlay and Baldwin annotation.
      Panel 1 — care_weight: mean +/- 95% CI + Phase 3 mean dashed
      Panel 2 — learning_rate: mean +/- 95% CI + Phase 3 mean dashed
      Panel 3 — forage_weight: mean (hitchhiking check)
    """
    if plt is None or not all_snapshots:
        return

    os.makedirs(output_dir, exist_ok=True)

    tick_sets    = [set(s["tick"] for s in snaps) for snaps in all_snapshots]
    common_ticks = sorted(set.intersection(*tick_sets))
    if not common_ticks:
        print("No common ticks across seeds — skipping CI plot.")
        return

    def get_val(snaps: list[dict], t: int, key: str) -> float:
        for s in snaps:
            if s["tick"] == t:
                return s.get(key, 0.0)
        return 0.0

    care_by_seed   = [[get_val(snaps, t, "avg_care_weight")   for t in common_ticks] for snaps in all_snapshots]
    lr_by_seed     = [[get_val(snaps, t, "avg_learning_rate") for t in common_ticks] for snaps in all_snapshots]
    forage_by_seed = [[get_val(snaps, t, "avg_forage_weight") for t in common_ticks] for snaps in all_snapshots]

    care_mean  = [_mean([s[i] for s in care_by_seed])   for i in range(len(common_ticks))]
    lr_mean    = [_mean([s[i] for s in lr_by_seed])     for i in range(len(common_ticks))]
    forage_mean= [_mean([s[i] for s in forage_by_seed]) for i in range(len(common_ticks))]
    care_ci    = [_ci95([s[i] for s in care_by_seed])   for i in range(len(common_ticks))]
    lr_ci      = [_ci95([s[i] for s in lr_by_seed])     for i in range(len(common_ticks))]

    care_lo = [m - c for m, c in zip(care_mean, care_ci)]
    care_hi = [m + c for m, c in zip(care_mean, care_ci)]
    lr_lo   = [m - c for m, c in zip(lr_mean, lr_ci)]
    lr_hi   = [m + c for m, c in zip(lr_mean, lr_ci)]

    # Phase 3 baseline overlay
    p3_care_by_tick, p3_lr_by_tick = _load_phase04_baselines()
    p3_ticks = [t for t in common_ticks if t in p3_care_by_tick]
    p3_care  = [p3_care_by_tick[t] for t in p3_ticks]
    p3_lr    = [p3_lr_by_tick.get(t, 0.1) for t in p3_ticks]

    # Baldwin classification counts
    n_care_recovered = n_lr_swept = n_baldwin = 0
    if baldwin_classifications:
        n_care_recovered = sum(1 for c in baldwin_classifications if c.get("care_recovered"))
        n_lr_swept       = sum(1 for c in baldwin_classifications if c.get("lr_swept"))
        n_baldwin        = sum(1 for c in baldwin_classifications if c.get("is_baldwin"))

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
    fig.suptitle(
        f"Phase 4b (Kin-Conditional Plasticity) vs Phase 3 (No Plasticity)\n"
        f"{len(seeds)} Seeds — Baldwin Effect: care_weight recovery + learning_rate sweep",
        fontsize=10,
    )

    # ── Panel 1: care_weight ──
    for snaps in all_snapshots:
        t_i = [s["tick"] for s in snaps if s["tick"] in set(common_ticks)]
        c_i = [get_val(snaps, t, "avg_care_weight") for t in t_i]
        ax1.plot(t_i, c_i, color="#2ca02c", alpha=0.10, linewidth=0.9)

    ax1.fill_between(common_ticks, care_lo, care_hi, alpha=0.22, color="#2ca02c")
    ax1.plot(common_ticks, care_mean, color="#2ca02c", linewidth=2.2,
             label=f"Phase 4b mean ± 95% CI  (n = {len(seeds)} seeds)")
    if p3_ticks:
        ax1.plot(p3_ticks, p3_care, color="steelblue", linewidth=1.8,
                 linestyle="--", label="Phase 3 mean (no plasticity)", zorder=4)
    ax1.axhline(0.500, color="gray",    linestyle="--", linewidth=0.9, alpha=0.7,
                label="Gen 0 start (0.500)")
    ax1.axhline(0.365, color="crimson", linestyle=":",  linewidth=1.2,
                label="R0 survivors (0.365)")
    ax1.set_ylabel("Mean care_weight (genome parameter)")
    ax1.set_ylim(0, 1)
    # Lower left clear — care data lives in 0.35–0.55 range throughout
    ax1.legend(loc="lower left", frameon=True, ncol=2)
    ax1.grid(True)
    if baldwin_classifications:
        # Annotation in lower right (below data region, after care plateau)
        ax1.annotate(
            f"Care recovery \u2265 0.03: {n_care_recovered}/{len(seeds)} seeds",
            xy=(0.97, 0.06), xycoords="axes fraction",
            ha="right", va="bottom", fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow",
                      edgecolor="0.65", linewidth=0.7),
        )

    # ── Panel 2: learning_rate ──
    for snaps in all_snapshots:
        t_i = [s["tick"] for s in snaps if s["tick"] in set(common_ticks)]
        l_i = [get_val(snaps, t, "avg_learning_rate") for t in t_i]
        ax2.plot(t_i, l_i, color="mediumpurple", alpha=0.10, linewidth=0.9)

    ax2.fill_between(common_ticks, lr_lo, lr_hi, alpha=0.22, color="mediumpurple")
    ax2.plot(common_ticks, lr_mean, color="mediumpurple", linewidth=2.2,
             label=f"Phase 4b mean ± 95% CI  (n = {len(seeds)} seeds)")
    if p3_ticks:
        ax2.plot(p3_ticks, p3_lr, color="gray", linewidth=1.8,
                 linestyle="--", label="Phase 3 mean (\u2248 0.100, fixed)", zorder=4)
    ax2.axhline(0.100, color="gray", linestyle="--", linewidth=0.9, alpha=0.7,
                label="Gen 0 start (0.100)")
    ax2.set_ylabel("Mean learning_rate (genome parameter)")
    ax2.set_ylim(0, 0.5)
    # Upper left: learning_rate starts at 0.10 and rises; upper-left above 0.40 is clear
    ax2.legend(loc="upper left", frameon=True, ncol=2)
    ax2.grid(True)
    if baldwin_classifications:
        # Annotation in lower right
        ax2.annotate(
            f"LR sweep \u2265 0.03: {n_lr_swept}/{len(seeds)} seeds  |  "
            f"Full Baldwin: {n_baldwin}/{len(seeds)}",
            xy=(0.97, 0.06), xycoords="axes fraction",
            ha="right", va="bottom", fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow",
                      edgecolor="0.65", linewidth=0.7),
        )

    # ── Panel 3: forage (hitchhiking check) ──
    ax3.plot(common_ticks, forage_mean, color="#d95f02", linewidth=2.2,
             label="Phase 4b mean forage_weight")
    ax3.axhline(0.500, color="gray", linestyle="--", linewidth=0.9, alpha=0.7,
                label="Gen 0 start (0.500)")
    ax3.set_xlabel("Simulation tick  (\u2248 100 ticks per generation)")
    ax3.set_ylabel("Mean forage_weight (genome parameter)")
    ax3.set_ylim(0, 1)
    # Upper left: forage hovers near 0.5; above 0.8 is clear
    ax3.legend(loc="upper left", frameon=True)
    ax3.grid(True)

    fig.tight_layout()
    path = os.path.join(output_dir, "multi_seed_care_weight_ci.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =============================================================================
# Zero-shot bar chart
# =============================================================================

def plot_zeroshot_multiseed(
    zs_summaries: list[dict],
    p2_summaries: list[dict],
    output_dir: str,
) -> None:
    """Per-seed bar chart: Phase 4b vs Phase 2 window rates side by side."""
    if plt is None or not zs_summaries:
        return

    os.makedirs(os.path.join(output_dir, "plots"), exist_ok=True)

    p4b_by_seed = {s["seed"]: s["window_rate"] for s in zs_summaries}
    p2_by_seed  = {s["seed"]: s["window_rate"] for s in p2_summaries}
    seeds       = sorted(p4b_by_seed.keys())

    p4b_rates = [p4b_by_seed[s] for s in seeds]
    p2_rates  = [p2_by_seed.get(s, 0.0) for s in seeds]

    x      = list(range(len(seeds)))
    width  = 0.38
    p4b_colors = ["seagreen" if p4b_by_seed[s] >= p2_by_seed.get(s, 0) else "coral"
                  for s in seeds]

    fig, ax = plt.subplots(figsize=(12, 5))
    b1 = ax.bar([xi - width/2 for xi in x], p2_rates,  width, label="Phase 2 (no plasticity)",
                color="steelblue", alpha=0.8, edgecolor="white")
    b2 = ax.bar([xi + width/2 for xi in x], p4b_rates, width, label="Phase 4b (kin-cond. plasticity)",
                color=p4b_colors, alpha=0.9, edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels([f"s{s}" for s in seeds], fontsize=8)
    ax.set_ylabel("Care events / alive-mother-tick  (ticks 0\u2013100)")
    ax.set_title(
        "Zero-shot window rate: Phase 4b vs. Phase 2 baseline\n"
        "Green = Phase 4b above baseline | Red = below",
    )
    # Upper right: bars are short (< 0.12), upper right is clear
    ax.legend(loc="upper right", frameon=True)
    ax.set_ylim(0, max(max(p4b_rates), max(p2_rates)) * 1.35)
    ax.grid(True, axis="y")

    for bar, val in zip(b2, p4b_rates):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.001,
                f"{val:.4f}", ha="center", va="bottom", fontsize=7, color="0.3")

    fig.tight_layout()
    path = os.path.join(output_dir, "zeroshot_multiseed.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =============================================================================
# Statistical tests
# =============================================================================

def compute_statistical_tests(
    p4b_rates: list[float],
    p2_rates: list[float],
    seeds: list[int],
) -> dict:
    """
    Paired t-test + Wilcoxon signed-rank + Cohen's d.
    p4b_rates[i] vs p2_rates[i] are matched by seed.
    """
    if not HAS_SCIPY:
        return {"error": "scipy not available"}

    diffs = [b - a for b, a in zip(p4b_rates, p2_rates)]
    n     = len(diffs)
    mean_diff = _mean(diffs)
    ci_diff   = _ci95(diffs)

    t_result = _scipy_stats.ttest_rel(p4b_rates, p2_rates)
    w_result = _scipy_stats.wilcoxon(diffs) if n >= 6 else None

    # Cohen's d for paired design
    sd_diffs  = math.sqrt(sum((d - mean_diff)**2 for d in diffs) / (n - 1)) if n > 1 else 0
    cohens_d  = mean_diff / sd_diffs if sd_diffs > 0 else 0.0

    return {
        "n_pairs":           n,
        "mean_difference":   mean_diff,
        "ci95_difference":   [mean_diff - ci_diff, mean_diff + ci_diff],
        "paired_ttest": {
            "t_stat":  float(t_result.statistic),
            "p_value": float(t_result.pvalue),
            "df":      n - 1,
        },
        "wilcoxon": {
            "W_stat":  float(w_result.statistic) if w_result else None,
            "p_value": float(w_result.pvalue)    if w_result else None,
        },
        "cohens_d": cohens_d,
        "effect_size_label": (
            "large" if abs(cohens_d) >= 0.8 else
            "medium" if abs(cohens_d) >= 0.5 else
            "small"
        ),
        "per_seed": [
            {"seed": s, "p4b_rate": b, "p2_rate": a, "diff": b - a}
            for s, b, a in zip(seeds, p4b_rates, p2_rates)
        ],
    }


# =============================================================================
# Phase 2 multi-seed baseline runner
# =============================================================================

def run_phase05_baselines(seeds: list[int], phase3_run_dirs: dict) -> list[dict]:
    """
    For each seed, run Phase 2 zero-shot using Phase 3 evolved genomes (no plasticity).
    Returns per-seed window rates for paired statistical test.
    """
    import csv

    summaries = []
    for seed in seeds:
        p3_dir = phase04_run_dirs.get(str(seed))
        if not p3_dir or not os.path.exists(p3_dir):
            print(f"  [p2 baseline] seed={seed}: Phase 3 dir not found, skipping")
            continue

        print(f"--- [p2 baseline] seed={seed} ---")
        zs_dir = run_p2zs(seed=seed, source_run_dir=p3_dir)

        # Compute window rate from care_log.csv + population_history.json
        care_log = os.path.join(zs_dir, "care_log.csv")
        pop_file = os.path.join(zs_dir, "population_history.json")

        window_rate = 0.0
        if os.path.exists(care_log) and os.path.exists(pop_file):
            with open(care_log) as f:
                care = list(csv.DictReader(f))
            with open(pop_file) as f:
                pop = json.load(f)["population"]
            w_care = [r for r in care
                      if r.get("success", "True") in ("True", "1")
                      and int(r["tick"]) <= MATURITY_AGE]
            w_mt   = sum(p for t, p in enumerate(pop) if t < MATURITY_AGE)
            window_rate = len(w_care) / w_mt if w_mt > 0 else 0.0

        summaries.append({
            "seed":        seed,
            "window_rate": window_rate,
            "run_dir":     zs_dir,
        })
        print(f"    window_rate={window_rate:.5f}\n")

    return summaries


# =============================================================================
# Main runner
# =============================================================================

def run_all(seeds: list[int] = SEEDS) -> None:
    os.makedirs(COMBINED_DIR, exist_ok=True)

    # ── Load checkpoint (resume if crash recovery) ─────────────────────────
    cp = _load_checkpoint()
    done_evo = set(cp["completed_evo"])
    done_zs  = set(cp["completed_zs"])

    evo_run_dirs  = dict(cp["evo_run_dirs"])
    evo_summaries = list(cp["evo_summaries"])
    zs_run_dirs   = dict(cp["zs_run_dirs"])
    zs_summaries  = list(cp["zs_summaries"])

    print(f"Phase 4b multi-seed: {len(seeds)} seeds {seeds}")
    if done_evo:
        print(f"  [checkpoint] Resuming. Completed evo seeds: {sorted(done_evo)}")
    print()

    # ── Evolution pass ─────────────────────────────────────────────────────
    for seed in seeds:
        if seed in done_evo:
            print(f"  [checkpoint] seed={seed} evo already done, skipping.")
            continue

        print(f"--- [evolution] seed={seed} ---")
        evo_dir = run_p4b(seed=seed, stage="evolution_plastic_kin")
        evo_run_dirs[str(seed)] = evo_dir

        top_path = os.path.join(evo_dir, "top_genomes.json")
        if os.path.exists(top_path):
            with open(top_path) as f:
                genomes = json.load(f)
            cw   = [g["care_weight"]   for g in genomes]
            fw   = [g["forage_weight"] for g in genomes]
            lr   = [g["learning_rate"] for g in genomes]
            lc   = [g["learning_cost"] for g in genomes]
            gens = [g.get("generation", 0) for g in genomes]

            snaps = _load_snapshots(evo_dir)
            bald  = _classify_baldwin(snaps)

            evo_summaries.append({
                "seed":                    seed,
                "n_survivors":             len(genomes),
                "final_care_mean":         _mean(cw),
                "final_forage_mean":       _mean(fw),
                "final_learning_rate_mean":_mean(lr),
                "final_learning_cost_mean":_mean(lc),
                "max_generation":          max(gens) if gens else 0,
                "is_baldwin":              bald["is_baldwin"],
                "care_recovery":           bald.get("care_recovery", 0),
                "lr_delta":                bald.get("lr_delta", 0),
            })

        cp["completed_evo"].append(seed)
        cp["evo_run_dirs"]  = evo_run_dirs
        cp["evo_summaries"] = evo_summaries
        _save_checkpoint(cp)
        print(f"  [checkpoint] seed={seed} evo saved.\n")

    # ── Zero-shot pass ────────────────────────────────────────────────────
    print("=" * 55)
    print("Starting Phase 4b zero-shot pass...")
    print("=" * 55 + "\n")

    for seed in seeds:
        if seed in done_zs:
            print(f"  [checkpoint] seed={seed} zero-shot already done, skipping.")
            continue

        evo_dir = evo_run_dirs.get(str(seed))
        if not evo_dir:
            print(f"  seed={seed}: no evo dir found, skipping zero-shot.")
            continue

        print(f"--- [zeroshot_plastic_kin] seed={seed} ---")
        zs_dir = run_p4b(seed=seed, stage="zeroshot_plastic_kin", source_dir=evo_dir)
        zs_run_dirs[str(seed)] = zs_dir

        m      = _load_zeroshot_metrics(zs_dir)
        window = m.get("care_window", {})
        zs_summaries.append({
            "seed":        seed,
            "window_rate": window.get("care_per_mother_tick_in_window", 0.0),
            "window_care": window.get("care_events_in_window", 0),
            "last_alive":  m.get("last_alive_tick", 0),
            "run_dir":     zs_dir,
        })

        cp["completed_zs"].append(seed)
        cp["zs_run_dirs"]  = zs_run_dirs
        cp["zs_summaries"] = zs_summaries
        _save_checkpoint(cp)
        print(f"  [checkpoint] seed={seed} zero-shot saved.\n")

    # ── Phase 2 baseline pass (for paired stats) ──────────────────────────
    print("=" * 55)
    print("Running Phase 2 baselines (Phase 3 genomes, no plasticity)...")
    print("=" * 55 + "\n")

    p3_phase04_run_dirs = {}
    if os.path.exists(P3_RUN_DIRS_JSON):
        with open(P3_RUN_DIRS_JSON) as f:
            rd = json.load(f)
        for s, d in zip(rd["seeds"], rd["run_dirs"]):
            p3_phase04_run_dirs[str(s)] = d

    p2_summaries = run_phase05_baselines(seeds, p3_phase04_run_dirs)

    # ── Save manifests ────────────────────────────────────────────────────
    with open(os.path.join(COMBINED_DIR, "run_dirs.json"), "w") as f:
        json.dump({
            "seeds": seeds,
            "evo_run_dirs": evo_run_dirs,
            "zs_run_dirs":  zs_run_dirs,
        }, f, indent=2)

    with open(os.path.join(COMBINED_DIR, "summary.json"), "w") as f:
        json.dump(evo_summaries, f, indent=2)

    with open(os.path.join(COMBINED_DIR, "zeroshot_summary.json"), "w") as f:
        json.dump(zs_summaries, f, indent=2)

    with open(os.path.join(COMBINED_DIR, "phase05_baseline_summary.json"), "w") as f:
        json.dump(p2_summaries, f, indent=2)

    # ── Statistical tests ─────────────────────────────────────────────────
    p4b_rates = [s["window_rate"] for s in zs_summaries]
    p2_rates  = [s["window_rate"] for s in p2_summaries]
    test_seeds = [s["seed"] for s in zs_summaries]

    if len(p4b_rates) == len(p2_rates) and len(p4b_rates) > 0:
        stat_results = compute_statistical_tests(p4b_rates, p2_rates, test_seeds)
        with open(os.path.join(COMBINED_DIR, "statistical_tests.json"), "w") as f:
            json.dump(stat_results, f, indent=2)
    else:
        stat_results = {}
        print("Warning: mismatched Phase 4b / Phase 2 sample sizes — skipping stats.")

    # ── Plots ─────────────────────────────────────────────────────────────
    all_snapshots = [_load_snapshots(evo_run_dirs[str(s)]) for s in seeds if str(s) in evo_run_dirs]
    bald_class    = [s for s in evo_summaries]  # already have is_baldwin per seed

    plot_multi_seed_ci(all_snapshots, seeds, COMBINED_DIR, bald_class)
    plot_start_vs_end_multiseed(evo_summaries, COMBINED_DIR)
    if p2_summaries:
        plot_zeroshot_multiseed(zs_summaries, p2_summaries, COMBINED_DIR)

    # ── Summary table ─────────────────────────────────────────────────────
    print("\n=== Phase 4b Multi-Seed Evolution Summary ===")
    print(f"{'Seed':>5}  {'Surv':>5}  {'care_w':>7}  {'forage':>7}  {'lr':>7}  {'Baldwin?':>9}")
    print("-" * 55)
    for s in evo_summaries:
        tag = "YES" if s.get("is_baldwin") else "no"
        print(f"{s['seed']:>5}  {s['n_survivors']:>5}  "
              f"{s['final_care_mean']:>7.4f}  {s['final_forage_mean']:>7.4f}  "
              f"{s['final_learning_rate_mean']:>7.4f}  {tag:>9}")

    care_finals = [s["final_care_mean"]          for s in evo_summaries]
    lr_finals   = [s["final_learning_rate_mean"] for s in evo_summaries]
    n_baldwin   = sum(1 for s in evo_summaries if s.get("is_baldwin"))
    print("-" * 55)
    print(f"  Mean care_weight : {_mean(care_finals):.4f} +/- {_ci95(care_finals):.4f} (95% CI)")
    print(f"  Mean learn_rate  : {_mean(lr_finals):.4f} +/- {_ci95(lr_finals):.4f} (95% CI)")
    print(f"  Baldwin Effect   : {n_baldwin}/{len(evo_summaries)} seeds")

    print("\n=== Zero-Shot Statistical Test (Phase 4b vs Phase 2, paired) ===")
    if stat_results and "paired_ttest" in stat_results:
        pt = stat_results["paired_ttest"]
        wt = stat_results["wilcoxon"]
        print(f"  Mean difference  : {stat_results['mean_difference']:+.5f}")
        print(f"  95% CI of diff   : [{stat_results['ci95_difference'][0]:.5f}, {stat_results['ci95_difference'][1]:.5f}]")
        print(f"  Paired t-test    : t={pt['t_stat']:.4f}, p={pt['p_value']:.4f}, df={pt['df']}")
        print(f"  Wilcoxon         : W={wt['W_stat']}, p={wt['p_value']:.4f}" if wt["W_stat"] else "  Wilcoxon: n too small")
        print(f"  Cohen's d        : {stat_results['cohens_d']:.4f} ({stat_results['effect_size_label']})")

        p = pt["p_value"]
        if p < 0.05:
            print(f"  Result: SIGNIFICANT (p={p:.4f} < 0.05) — Phase 4b window rate reliably higher")
        else:
            print(f"  Result: NOT significant (p={p:.4f} >= 0.05) — difference not reliable")

    print(f"\nCombined output: {COMBINED_DIR}")


if __name__ == "__main__":
    run_all()
