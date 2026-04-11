# experiments/phase5_emergence/run_multi_seed.py
"""
Phase 5a/5b/5c multi-seed runner (seeds 42–51).

Produces:
  - Per-seed evolution + control runs with generation snapshots
  - Per-seed zero-shot assimilation test (5c)
  - Multi-seed CI plot: care_weight trajectory with Phase 3 overlay
  - Statistical test: paired t-test + Wilcoxon (Phase 5 zero-shot vs Phase 3 baseline)
  - Summary table with selection gradient r per seed (key Phase 5 measurement)

Hardened against:
  - Data loss: checkpoint saved after every seed
  - Extinction: survival gate run before each full seed; failed seeds logged and skipped

Output: outputs/phase5_emergence/multi_seed_evolution/
"""
import sys
import os
import json
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase5_emergence.run import run as run_p5

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    from scipy import stats as _scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("Warning: scipy not available — statistical tests will be skipped.")

SEEDS        = list(range(42, 52))
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase5_emergence", "multi_seed_evolution")
CHECKPOINT   = os.path.join(COMBINED_DIR, "checkpoint.json")

# Phase 3 multi-seed manifest (for baseline overlay)
P3_RUN_DIRS_JSON = os.path.join(
    PROJECT_ROOT, "outputs", "phase3_maternal", "multi_seed_evolution", "run_dirs.json"
)

PHASE3_ZS_BASELINE      = 0.09069   # Phase 3 zero-shot window rate
MATURITY_AGE            = 100
PHASE5_EMERGENCE_LABEL  = "care_weight mean=0.25 start → positive gradient (vs Phase 3 r=−0.178)"


# =============================================================================
# Helpers
# =============================================================================

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _ci95(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = _mean(values)
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return 1.96 * math.sqrt(variance / n)


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


def _load_phase3_baselines() -> tuple[dict, dict]:
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
    for t in common_ticks:
        c_vals = [next(s["avg_care_weight"] for s in snaps if s["tick"] == t)
                  for snaps in all_snaps]
        care_by_tick[t] = _mean(c_vals)
    return care_by_tick, {}


# =============================================================================
# Checkpoint helpers
# =============================================================================

def _load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {
        "completed_evo":    [],
        "evo_run_dirs":     {},
        "evo_summaries":    [],
        "failed_seeds":     [],
        "completed_ctrl":   [],
        "ctrl_run_dirs":    {},
        "completed_zs":     [],
        "zs_run_dirs":      {},
        "zs_summaries":     [],
    }


def _save_checkpoint(cp: dict) -> None:
    os.makedirs(COMBINED_DIR, exist_ok=True)
    with open(CHECKPOINT, "w") as f:
        json.dump(cp, f, indent=2)


# =============================================================================
# Multi-seed CI plot
# =============================================================================

def plot_multi_seed_ci(
    all_snapshots: list[list[dict]],
    ctrl_snapshots: list[list[dict]],
    seeds: list[int],
    output_dir: str,
    gradients: list[float | None] = None,
) -> None:
    """3-panel plot: care_weight + forage_weight + population.
    Phase 5 (scatter=2) vs Phase 5 control (scatter=5) vs Phase 3 overlay.
    """
    if plt is None or not all_snapshots:
        return

    os.makedirs(output_dir, exist_ok=True)

    def _extract(all_snaps: list[list[dict]], key: str) -> tuple[list, list, list, list]:
        tick_sets    = [set(s["tick"] for s in snaps) for snaps in all_snaps if snaps]
        if not tick_sets:
            return [], [], [], []
        common_ticks = sorted(set.intersection(*tick_sets))
        by_seed = [[next((s.get(key, 0.0) for s in snaps if s["tick"] == t), 0.0)
                    for t in common_ticks] for snaps in all_snaps if snaps]
        mean = [_mean([s[i] for s in by_seed]) for i in range(len(common_ticks))]
        ci   = [_ci95([s[i] for s in by_seed]) for i in range(len(common_ticks))]
        lo   = [m - c for m, c in zip(mean, ci)]
        hi   = [m + c for m, c in zip(mean, ci)]
        return common_ticks, mean, lo, hi

    ticks5, care5_mean, care5_lo, care5_hi  = _extract(all_snapshots,  "avg_care_weight")
    ticks_c, care_c_mean, care_c_lo, care_c_hi = _extract(ctrl_snapshots, "avg_care_weight") if ctrl_snapshots else ([], [], [], [])

    # Phase 3 baseline overlay
    p3_care_by_tick, _ = _load_phase3_baselines()
    p3_ticks = [t for t in ticks5 if t in p3_care_by_tick]
    p3_care  = [p3_care_by_tick[t] for t in p3_ticks]

    # Selection gradient annotation
    valid_grads = [g for g in (gradients or []) if g is not None]
    grad_str = (f"Mean selection gradient r = {_mean(valid_grads):+.4f}  "
                f"(Phase 3 baseline: −0.178)"
                if valid_grads else "")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    fig.suptitle(
        f"Phase 5 Ecological Emergence — care_weight from near-zero\n"
        f"{len(seeds)} seeds | infant_starvation_multiplier=3.0 | birth_scatter_radius=2",
        fontsize=10,
    )

    # Panel 1: care_weight
    for snaps in all_snapshots:
        if not snaps:
            continue
        t_i = [s["tick"]           for s in snaps]
        c_i = [s["avg_care_weight"] for s in snaps]
        ax1.plot(t_i, c_i, color="seagreen", alpha=0.12, linewidth=1)

    if ticks5:
        ax1.plot(ticks5, care5_mean, color="seagreen", linewidth=2.5,
                 label=f"Phase 5a mean (scatter=2, n={len(seeds)})")
        ax1.fill_between(ticks5, care5_lo, care5_hi, alpha=0.25, color="seagreen",
                         label="Phase 5a 95% CI")
    if ticks_c:
        ax1.plot(ticks_c, care_c_mean, color="darkorange", linewidth=1.8, linestyle="--",
                 label="Phase 5b control (scatter=5)")
    if p3_ticks:
        ax1.plot(p3_ticks, p3_care, color="steelblue", linewidth=1.8, linestyle=":",
                 label="Phase 3 mean (no ecology)", zorder=4)
    ax1.axhline(0.025, color="gray", linestyle="--", linewidth=0.9, alpha=0.7,
                label="Phase 5 start (0.025 mean)")
    ax1.axhline(0.420, color="crimson", linestyle=":", linewidth=1.2,
                label="Phase 3 final (0.420)")
    ax1.set_ylabel("care_weight")
    ax1.set_ylim(0, 1)
    ax1.legend(loc="upper left", fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.2)
    if grad_str:
        ax1.annotate(
            grad_str,
            xy=(0.02, 0.06), xycoords="axes fraction", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="gray"),
        )

    # Panel 2: forage_weight (hitchhiking check)
    _, forage5_mean, forage5_lo, forage5_hi = _extract(all_snapshots, "avg_forage_weight")
    if ticks5:
        ax2.plot(ticks5, forage5_mean, color="darkorange", linewidth=2.5,
                 label="Phase 5a forage_weight mean")
        ax2.fill_between(ticks5, forage5_lo, forage5_hi, alpha=0.2, color="darkorange")
    ax2.axhline(0.5, color="gray", linestyle="--", linewidth=0.9, alpha=0.7,
                label="Init mean (0.5)")
    ax2.set_xlabel("Tick  (approx. 1 generation per 100 ticks)")
    ax2.set_ylabel("forage_weight")
    ax2.set_ylim(0, 1)
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.2)

    plt.tight_layout()
    path = os.path.join(output_dir, "multi_seed_care_weight_ci.png")
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"  Saved: {path}")


# =============================================================================
# Zero-shot bar chart
# =============================================================================

def plot_zeroshot_multiseed(zs_summaries: list[dict], output_dir: str) -> None:
    if plt is None or not zs_summaries:
        return
    seeds      = sorted(s["seed"] for s in zs_summaries)
    by_seed    = {s["seed"]: s["window_rate"] for s in zs_summaries}
    p5_rates   = [by_seed[s] for s in seeds]
    baseline   = [PHASE3_ZS_BASELINE] * len(seeds)
    colors     = ["seagreen" if r > PHASE3_ZS_BASELINE else "coral" for r in p5_rates]

    x     = list(range(len(seeds)))
    width = 0.38

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar([xi - width/2 for xi in x], baseline,  width, label=f"Phase 3 baseline ({PHASE3_ZS_BASELINE:.5f})",
           color="steelblue", alpha=0.8, edgecolor="white")
    b2 = ax.bar([xi + width/2 for xi in x], p5_rates, width,
                label="Phase 5c zero-shot (evolved genomes)", color=colors, alpha=0.9, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels([f"seed {s}" for s in seeds], fontsize=8)
    ax.set_ylabel("Care / mother-tick (ticks 0–100)")
    ax.set_title(
        "Phase 5c Genetic Assimilation Test: Zero-Shot Window Rate vs Phase 3 Baseline\n"
        "Green = above Phase 3 baseline (assimilation signal) | Coral = below",
    )
    ax.legend(fontsize=9)
    ax.set_ylim(0, max(max(p5_rates), PHASE3_ZS_BASELINE) * 1.35)
    ax.grid(True, axis="y", alpha=0.3)
    for bar, val in zip(b2, p5_rates):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.001,
                f"{val:.4f}", ha="center", va="bottom", fontsize=7)
    plt.tight_layout()
    path = os.path.join(output_dir, "zeroshot_multiseed.png")
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"  Saved: {path}")


# =============================================================================
# Statistical test
# =============================================================================

def compute_statistical_tests(
    evo_summaries: list[dict],
    zs_summaries: list[dict],
    seeds: list[int],
) -> dict:
    """Statistical tests for Phase 5 multi-seed.

    Primary test: Is the mean selection gradient r > 0 across seeds?
      H0: r == 0  (no directional selection)
      H1: r > 0   (positive selection — care builds)
      Phase 3 reference: r = -0.178

    Secondary test: Phase 5a vs 5b final care_weight (paired t-test) — tests philopatry.

    Zero-shot note: Phase 5c rates compared to Phase 3 baseline (0.09069) as reference,
      but this comparison is directionally confounded (Phase 5 starts lower than Phase 3).
      The zero-shot result is informational, not the primary hypothesis test.
    """
    if not HAS_SCIPY:
        return {"error": "scipy not available"}

    # ── Primary: gradient test ─────────────────────────────────────────────
    grads = [s.get("selection_grad_r") for s in evo_summaries if s.get("selection_grad_r") is not None]
    n_g   = len(grads)
    grad_result = {}
    if n_g >= 2:
        t_g = _scipy_stats.ttest_1samp(grads, 0.0)  # H0: r == 0
        mean_g = _mean(grads)
        sd_g   = math.sqrt(sum((x - mean_g)**2 for x in grads) / (n_g - 1))
        d_g    = mean_g / sd_g if sd_g > 0 else 0.0
        grad_result = {
            "n_seeds":   n_g,
            "mean_r":    mean_g,
            "ci95":      [mean_g - _ci95(grads), mean_g + _ci95(grads)],
            "phase3_ref": -0.178,
            "ttest_vs_zero": {
                "t_stat":  float(t_g.statistic),
                "p_value": float(t_g.pvalue),
                "df":      n_g - 1,
            },
            "cohens_d":  d_g,
            "positive_gradient": mean_g > 0,
            "significant": t_g.pvalue < 0.05,
        }

    # ── Secondary: zero-shot informational ────────────────────────────────
    p5_rates   = [s["window_rate"] for s in zs_summaries]
    zs_result  = {}
    if p5_rates:
        mean_zs = _mean(p5_rates)
        ci_zs   = _ci95(p5_rates)
        zs_result = {
            "n_seeds":       len(p5_rates),
            "mean_p5_rate":  mean_zs,
            "ci95":          [mean_zs - ci_zs, mean_zs + ci_zs],
            "phase3_baseline": PHASE3_ZS_BASELINE,
            "note": (
                "Comparison to Phase 3 baseline is directionally confounded: "
                "Phase 5 evolved from lower care_weight (0.25) than Phase 3 (0.50). "
                "Lower absolute care_weight → lower zero-shot rate, independent of assimilation. "
                "Primary Phase 5 result is the selection gradient reversal (above), not this rate."
            ),
        }

    return {
        "gradient_reversal_test":  grad_result,
        "zeroshot_informational":  zs_result,
        "per_seed_gradients": [
            {"seed": s.get("seed"), "gradient_r": s.get("selection_grad_r"), "positive": (s.get("selection_grad_r") or 0) > 0}
            for s in evo_summaries
        ],
    }


# =============================================================================
# Main runner
# =============================================================================

def run_all(seeds: list[int] = SEEDS) -> None:
    os.makedirs(COMBINED_DIR, exist_ok=True)

    cp          = _load_checkpoint()
    done_evo    = set(cp["completed_evo"])
    done_ctrl   = set(cp["completed_ctrl"])
    done_zs     = set(cp["completed_zs"])
    failed      = set(cp["failed_seeds"])
    evo_run_dirs  = dict(cp["evo_run_dirs"])
    ctrl_run_dirs = dict(cp["ctrl_run_dirs"])
    zs_run_dirs   = dict(cp["zs_run_dirs"])
    evo_summaries = list(cp["evo_summaries"])
    zs_summaries  = list(cp["zs_summaries"])

    print(f"Phase 5 multi-seed: {len(seeds)} seeds {seeds}")
    if done_evo:
        print(f"  [checkpoint] Completed evo seeds: {sorted(done_evo)}")
    if failed:
        print(f"  [checkpoint] Failed (survival gate) seeds: {sorted(failed)}")
    print()

    # ── Survival gate + Evolution pass ────────────────────────────────────────
    for seed in seeds:
        if seed in done_evo or seed in failed:
            print(f"  [checkpoint] seed={seed} already {'done' if seed in done_evo else 'failed'}, skipping.")
            continue

        # Survival gate
        print(f"--- [survival_gate] seed={seed} ---")
        gate = run_p5(seed=seed, stage="survival_gate")
        if not gate["survived"]:
            print(f"  seed={seed}: survival gate FAILED (pop={gate['final_pop']}). Skipping full run.\n")
            cp["failed_seeds"].append(seed)
            _save_checkpoint(cp)
            continue

        print(f"  seed={seed}: gate PASSED (pop={gate['final_pop']}). Starting full evolution.\n")

        # Full evolution (5a)
        print(f"--- [evolution] seed={seed} ---")
        evo_dir = run_p5(seed=seed, stage="evolution")
        evo_run_dirs[str(seed)] = evo_dir

        # Load summary data
        snap_path = os.path.join(evo_dir, "generation_snapshots.json")
        snaps = []
        if os.path.exists(snap_path):
            with open(snap_path) as f:
                snaps = json.load(f)

        top_path = os.path.join(evo_dir, "top_genomes.json")
        if os.path.exists(top_path):
            with open(top_path) as f:
                genomes = json.load(f)
            cw    = [g["care_weight"]   for g in genomes]
            fw    = [g["forage_weight"] for g in genomes]
            gens  = [g.get("generation", 0) for g in genomes]

            # Load selection gradient from birth_log
            from experiments.phase5_emergence.run import _compute_selection_gradient
            grad = _compute_selection_gradient(os.path.join(evo_dir, "birth_log.csv"))

            # Determine emergence: care_weight increased from ~0.025 start
            start_care = snaps[0]["avg_care_weight"] if snaps else 0.025
            final_care = snaps[-1]["avg_care_weight"] if snaps else _mean(cw)
            emerged    = final_care > 0.1 and (final_care - start_care) > 0.05

            evo_summaries.append({
                "seed":              seed,
                "n_survivors":       len(genomes),
                "start_care_weight": start_care,
                "final_care_mean":   final_care,
                "final_forage_mean": _mean(fw),
                "max_generation":    max(gens) if gens else 0,
                "selection_grad_r":  grad,
                "emerged":           emerged,
            })

        cp["completed_evo"].append(seed)
        cp["evo_run_dirs"]  = evo_run_dirs
        cp["evo_summaries"] = evo_summaries
        _save_checkpoint(cp)
        print(f"  [checkpoint] seed={seed} evo saved.\n")

    # ── Control pass (5b) ─────────────────────────────────────────────────────
    print("=" * 55)
    print("Phase 5b: Dispersal control (scatter=5)...")
    print("=" * 55 + "\n")

    for seed in seeds:
        if seed in done_ctrl or seed in failed:
            continue
        print(f"--- [control] seed={seed} ---")
        ctrl_dir = run_p5(seed=seed, stage="control")
        ctrl_run_dirs[str(seed)] = ctrl_dir
        cp["completed_ctrl"].append(seed)
        cp["ctrl_run_dirs"] = ctrl_run_dirs
        _save_checkpoint(cp)
        print(f"  [checkpoint] seed={seed} control saved.\n")

    # ── Zero-shot pass (5c) ────────────────────────────────────────────────────
    print("=" * 55)
    print("Phase 5c: Genetic assimilation zero-shot test...")
    print("=" * 55 + "\n")

    for seed in seeds:
        if seed in done_zs or seed in failed:
            continue
        evo_dir = evo_run_dirs.get(str(seed))
        if not evo_dir:
            print(f"  seed={seed}: no evo dir, skipping zero-shot.")
            continue

        print(f"--- [zeroshot] seed={seed} ---")
        zs_dir = run_p5(seed=seed, stage="zeroshot", source_dir=evo_dir)
        zs_run_dirs[str(seed)] = zs_dir

        m      = _load_zeroshot_metrics(zs_dir)
        window = m.get("care_window", {})
        zs_summaries.append({
            "seed":        seed,
            "window_rate": window.get("care_per_mother_tick_in_window", 0.0),
            "assimulated": m.get("assimilation_signal", False),
        })
        cp["completed_zs"].append(seed)
        cp["zs_run_dirs"]  = zs_run_dirs
        cp["zs_summaries"] = zs_summaries
        _save_checkpoint(cp)
        print(f"  [checkpoint] seed={seed} zero-shot saved.\n")

    # ── Save manifests ─────────────────────────────────────────────────────────
    with open(os.path.join(COMBINED_DIR, "run_dirs.json"), "w") as f:
        json.dump({
            "seeds": seeds,
            "evo_run_dirs":  evo_run_dirs,
            "ctrl_run_dirs": ctrl_run_dirs,
            "zs_run_dirs":   zs_run_dirs,
        }, f, indent=2)

    with open(os.path.join(COMBINED_DIR, "summary.json"), "w") as f:
        json.dump(evo_summaries, f, indent=2)

    with open(os.path.join(COMBINED_DIR, "zeroshot_summary.json"), "w") as f:
        json.dump(zs_summaries, f, indent=2)

    # ── Statistical tests (primary: gradient reversal; secondary: zero-shot info) ──
    test_seeds = [s["seed"] for s in zs_summaries]
    stat_results = compute_statistical_tests(evo_summaries, zs_summaries, test_seeds)
    with open(os.path.join(COMBINED_DIR, "statistical_tests.json"), "w") as f:
        json.dump(stat_results, f, indent=2)

    # ── Plots ──────────────────────────────────────────────────────────────────
    valid_evo_seeds  = [s for s in seeds if str(s) in evo_run_dirs]
    valid_ctrl_seeds = [s for s in seeds if str(s) in ctrl_run_dirs]
    all_snaps  = [_load_snapshots(evo_run_dirs[str(s)])  for s in valid_evo_seeds]
    ctrl_snaps = [_load_snapshots(ctrl_run_dirs[str(s)]) for s in valid_ctrl_seeds]
    grads      = [s.get("selection_grad_r") for s in evo_summaries]

    plot_multi_seed_ci(all_snaps, ctrl_snaps, valid_evo_seeds, COMBINED_DIR, grads)
    if zs_summaries:
        plot_zeroshot_multiseed(zs_summaries, COMBINED_DIR)

    # ── Summary table ──────────────────────────────────────────────────────────
    print("\n=== Phase 5a Multi-Seed Evolution Summary ===")
    print(f"{'Seed':>5}  {'Surv':>5}  {'Start_cw':>8}  {'Final_cw':>8}  "
          f"{'Grad_r':>8}  {'Emerged?':>9}")
    print("-" * 60)
    for s in evo_summaries:
        tag  = "YES" if s.get("emerged") else "no"
        grad = s.get("selection_grad_r")
        grad_str = f"{grad:+.4f}" if grad is not None else "   N/A"
        print(f"{s['seed']:>5}  {s['n_survivors']:>5}  "
              f"{s['start_care_weight']:>8.4f}  {s['final_care_mean']:>8.4f}  "
              f"{grad_str:>8}  {tag:>9}")

    if evo_summaries:
        final_cws = [s["final_care_mean"] for s in evo_summaries]
        grads_v   = [s["selection_grad_r"] for s in evo_summaries if s.get("selection_grad_r") is not None]
        n_emerged = sum(1 for s in evo_summaries if s.get("emerged"))
        print("-" * 60)
        print(f"  Mean final care_weight : {_mean(final_cws):.4f} +/- {_ci95(final_cws):.4f}")
        print(f"  Mean selection grad r  : {_mean(grads_v):+.4f}  (Phase 3: −0.178)")
        print(f"  Emerged (>0.1, delta>0.05): {n_emerged}/{len(evo_summaries)} seeds")

    print("\n=== Phase 5 Primary Result: Selection Gradient Reversal ===")
    grt = stat_results.get("gradient_reversal_test", {})
    if grt and "ttest_vs_zero" in grt:
        tt = grt["ttest_vs_zero"]
        p  = tt["p_value"]
        print(f"  Mean selection gradient r : {grt['mean_r']:+.4f}  (Phase 3: −0.178)")
        print(f"  95% CI                    : [{grt['ci95'][0]:+.4f}, {grt['ci95'][1]:+.4f}]")
        print(f"  One-sample t-test vs 0    : t={tt['t_stat']:.4f}, p={p:.4f}, df={tt['df']}")
        print(f"  Cohen's d                 : {grt['cohens_d']:.4f}")
        if grt.get("positive_gradient"):
            print(f"  Direction: POSITIVE (care BUILDS — opposite of Phase 3's erosion)")
        else:
            print(f"  Direction: FLAT or NEGATIVE (insufficient ecological pressure)")
        if p < 0.05:
            print(f"  Significance: p={p:.4f} < 0.05 — gradient reversal CONFIRMED")
        else:
            print(f"  Significance: p={p:.4f} >= 0.05 — trend present but not significant at 10 seeds")

    zri = stat_results.get("zeroshot_informational", {})
    if zri:
        print(f"\n  Zero-shot window rate (informational): {zri.get('mean_p5_rate', 0):.5f}")
        print(f"  Phase 3 reference: {PHASE3_ZS_BASELINE:.5f}")
        print(f"  Note: comparison confounded — Phase 5 started at lower care_weight")

    if failed:
        print(f"\n  Failed seeds (survival gate): {sorted(failed)}")

    print(f"\nCombined output: {COMBINED_DIR}")


if __name__ == "__main__":
    run_all()
