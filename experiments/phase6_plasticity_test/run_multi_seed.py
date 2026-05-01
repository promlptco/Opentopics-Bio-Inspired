# experiments/phase6_plasticity_test/run_multi_seed.py
"""
Phase 6 — multi-seed runner (10 seeds, kin-conditional plasticity).

Compares Phase 6a (plasticity ON, kin-conditional) against Phase 5 result
(plasticity OFF, all extinct). Tests the Baldwin Effect hypothesis:
phenotypic plasticity bridges the bistability gap that caused Phase 5 extinction.

Outputs per seed:
  - generation_snapshots.json  (care/forage/self/learning_rate trajectories)
  - birth_log.csv              (Pearson r source)
  - config.json, metadata.json

Aggregate outputs (COMBINED_DIR):
  - checkpoint.json            (resume-safe)
  - summary.json               (per-seed: survival, final_cw, final_lr, Pearson r)
  - phase6_care_trajectory.png (care + learning_rate + forage, 10 seeds + CI)
  - phase6_pearson_r.png       (r distribution vs Phase 4 neutral baseline)

Baldwin classification per seed:
  - care_recovery: final_cw - min_cw >= 0.05
  - lr_sweep:      final_lr - init_lr >= 0.03
  - is_baldwin:    both criteria met
"""
import sys
import os
import csv
import json
import math
from concurrent.futures import ProcessPoolExecutor, as_completed

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


def _run_seed_worker(packed):
    """Top-level picklable worker for ProcessPoolExecutor (Windows spawn-safe)."""
    seed, project_root = packed
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import json as _json
    from experiments.phase6_plasticity_test.run import run_evolution, _pearson_r

    evo_dir   = run_evolution(seed=seed, kin_conditional=True)
    snap_path = os.path.join(evo_dir, "generation_snapshots.json")
    snaps     = _json.load(open(snap_path)) if os.path.exists(snap_path) else []
    grad_r    = _pearson_r(os.path.join(evo_dir, "birth_log.csv"))

    final_cw, final_lr, survived = 0.0, 0.0, False
    if snaps:
        last     = snaps[-1]
        final_cw = last["avg_care_weight"]
        final_lr = last["avg_learning_rate"]
        survived = last["n_mothers"] >= 10

    return {"seed": seed, "evo_dir": evo_dir, "survived": survived,
            "final_cw": final_cw, "final_lr": final_lr, "pearson_r": grad_r}

from experiments.phase6_plasticity_test.run import run_evolution, _pearson_r, MULT, INIT_CARE

try:
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 10, "axes.titlesize": 10, "axes.labelsize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "legend.fontsize": 9, "legend.framealpha": 0.93, "legend.edgecolor": "0.6",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.8, "grid.alpha": 0.22, "grid.linewidth": 0.5,
        "lines.linewidth": 2.0, "figure.facecolor": "white", "axes.facecolor": "white",
    })
    HAS_PLT = True
except ImportError:
    HAS_PLT = False

try:
    from scipy import stats as _scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

SEEDS        = list(range(42, 52))
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase6_plasticity_test", "multi_seed")
CHECKPOINT   = os.path.join(COMBINED_DIR, "checkpoint.json")

PHASE3_CANONICAL_CW  = 0.30
PHASE3_CANONICAL_LR  = 0.10
PHASE4_NEUTRAL_R     = -0.034   # Phase 4 definitive neutral baseline (mean r, no pressure)
BALDWIN_CARE_MIN     = 0.05     # care recovery threshold for Baldwin classification
BALDWIN_LR_MIN       = 0.03     # learning_rate sweep threshold


# =============================================================================
# Helpers
# =============================================================================

def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _ci95(values):
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    var = sum((x - m) ** 2 for x in values) / (n - 1)
    return 1.96 * math.sqrt(var / n)


def _load_snapshots(run_dir):
    path = os.path.join(run_dir, "generation_snapshots.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _classify_baldwin(snaps, final_lr):
    if not snaps:
        return {"is_baldwin": False, "reason": "no snapshots (extinct)"}
    care_vals   = [s["avg_care_weight"]   for s in snaps]
    trough      = min(care_vals)
    final_care  = care_vals[-1]
    recovery    = final_care - trough
    lr_delta    = final_lr - PHASE3_CANONICAL_LR

    care_recovered = recovery  >= BALDWIN_CARE_MIN
    lr_swept       = lr_delta  >= BALDWIN_LR_MIN
    return {
        "is_baldwin":     care_recovered and lr_swept,
        "care_trough":    trough,
        "care_final":     final_care,
        "care_recovery":  recovery,
        "lr_start":       PHASE3_CANONICAL_LR,
        "lr_final":       final_lr,
        "lr_delta":       lr_delta,
        "care_recovered": care_recovered,
        "lr_swept":       lr_swept,
    }


# =============================================================================
# Checkpoint
# =============================================================================

def _load_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {"completed": [], "run_dirs": {}, "summaries": []}


def _save_checkpoint(cp):
    os.makedirs(COMBINED_DIR, exist_ok=True)
    with open(CHECKPOINT, "w") as f:
        json.dump(cp, f, indent=2)


# =============================================================================
# Plots
# =============================================================================

def _plot_trajectories(all_snaps, seeds, summaries, output_dir):
    if not HAS_PLT or not all_snaps:
        return

    tick_sets    = [set(s["tick"] for s in snaps) for snaps in all_snaps if snaps]
    common_ticks = sorted(set.intersection(*tick_sets)) if tick_sets else []
    if not common_ticks:
        print("  [plot] No common ticks across seeds — skipping trajectory plot.")
        return

    def get(snaps, t, key):
        for s in snaps:
            if s["tick"] == t:
                return s.get(key, 0.0)
        return 0.0

    care_by_seed   = [[get(snaps, t, "avg_care_weight")   for t in common_ticks] for snaps in all_snaps if snaps]
    lr_by_seed     = [[get(snaps, t, "avg_learning_rate") for t in common_ticks] for snaps in all_snaps if snaps]
    forage_by_seed = [[get(snaps, t, "avg_forage_weight") for t in common_ticks] for snaps in all_snaps if snaps]

    care_mean   = [_mean([s[i] for s in care_by_seed])   for i in range(len(common_ticks))]
    lr_mean     = [_mean([s[i] for s in lr_by_seed])     for i in range(len(common_ticks))]
    forage_mean = [_mean([s[i] for s in forage_by_seed]) for i in range(len(common_ticks))]
    care_ci     = [_ci95([s[i] for s in care_by_seed])   for i in range(len(common_ticks))]
    lr_ci       = [_ci95([s[i] for s in lr_by_seed])     for i in range(len(common_ticks))]

    n_survived  = sum(1 for s in summaries if s.get("survived"))
    n_baldwin   = sum(1 for s in summaries if s.get("is_baldwin"))

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
    fig.suptitle(
        f"Phase 6 — Kin-Conditional Plasticity (Baldwin Effect Test)\n"
        f"Phase 3 canonical init: care={INIT_CARE} | mult={MULT} | scatter=2 | {len(seeds)} seeds\n"
        f"Survived: {n_survived}/{len(seeds)}  |  Baldwin classified: {n_baldwin}/{len(seeds)}",
        fontsize=10,
    )

    # Panel 1: care_weight
    for snaps in all_snaps:
        if snaps:
            t_i = [s["tick"] for s in snaps]
            c_i = [s["avg_care_weight"] for s in snaps]
            ax1.plot(t_i, c_i, color="#2ca02c", alpha=0.12, linewidth=0.9)

    lo = [m - c for m, c in zip(care_mean, care_ci)]
    hi = [m + c for m, c in zip(care_mean, care_ci)]
    ax1.fill_between(common_ticks, lo, hi, alpha=0.22, color="#2ca02c")
    ax1.plot(common_ticks, care_mean, color="#2ca02c", linewidth=2.2,
             label=f"Phase 6a mean ± 95% CI  (n={len(all_snaps)} survived seeds)")
    ax1.axhline(PHASE3_CANONICAL_CW, color="crimson", linestyle="--", linewidth=1.4,
                label=f"Phase 3 canonical init ({PHASE3_CANONICAL_CW})")
    ax1.axhline(0.59, color="steelblue", linestyle=":", linewidth=1.1,
                label="Phase 4 neutral drift attractor (~0.59)")
    ax1.set_ylabel("Mean care_weight")
    ax1.set_ylim(0, 1)
    ax1.legend(loc="upper left", frameon=True, ncol=2)
    ax1.grid(True)

    # Panel 2: learning_rate (genetic assimilation signal)
    for snaps in all_snaps:
        if snaps:
            t_i = [s["tick"] for s in snaps]
            l_i = [s["avg_learning_rate"] for s in snaps]
            ax2.plot(t_i, l_i, color="mediumpurple", alpha=0.12, linewidth=0.9)

    lo2 = [m - c for m, c in zip(lr_mean, lr_ci)]
    hi2 = [m + c for m, c in zip(lr_mean, lr_ci)]
    ax2.fill_between(common_ticks, lo2, hi2, alpha=0.22, color="mediumpurple")
    ax2.plot(common_ticks, lr_mean, color="mediumpurple", linewidth=2.2,
             label=f"Phase 6a mean ± 95% CI  (n={len(all_snaps)} survived seeds)")
    ax2.axhline(PHASE3_CANONICAL_LR, color="gray", linestyle="--", linewidth=1.2,
                label=f"Genome init ({PHASE3_CANONICAL_LR})")
    ax2.set_ylabel("Mean learning_rate (genetic assimilation signal)")
    ax2.set_ylim(0, 0.5)
    ax2.legend(loc="upper left", frameon=True, ncol=2)
    ax2.grid(True)
    n_lr_swept = sum(1 for s in summaries if s.get("lr_swept"))
    ax2.annotate(
        f"LR sweep ≥ {BALDWIN_LR_MIN}: {n_lr_swept}/{len(summaries)} seeds",
        xy=(0.97, 0.06), xycoords="axes fraction",
        ha="right", va="bottom", fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow",
                  edgecolor="0.65", linewidth=0.7),
    )

    # Panel 3: forage (hitchhiking check)
    ax3.plot(common_ticks, forage_mean, color="#d95f02", linewidth=2.2,
             label="Phase 6a mean forage_weight")
    ax3.axhline(PHASE3_CANONICAL_CW, color="gray", linestyle="--", linewidth=0.9, alpha=0.6,
                label="Phase 3 canonical init (1.0 not shown — use left axis)")
    ax3.axhline(1.0, color="gray", linestyle="--", linewidth=0.9, alpha=0.6)
    ax3.set_xlabel("Simulation tick  (~100 ticks per generation)")
    ax3.set_ylabel("Mean forage_weight (hitchhiking check)")
    ax3.set_ylim(0, 1)
    ax3.legend(loc="upper right", frameon=True)
    ax3.grid(True)

    fig.tight_layout()
    path = os.path.join(output_dir, "phase6_care_trajectory.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def _plot_pearson_r(summaries, output_dir):
    if not HAS_PLT or not summaries:
        return

    r_vals = [s.get("pearson_r") for s in summaries if s.get("pearson_r") is not None]
    seeds  = [s["seed"] for s in summaries if s.get("pearson_r") is not None]
    if not r_vals:
        print("  [plot] No Pearson r values (all seeds extinct) — skipping r plot.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["seagreen" if r > 0 else "crimson" for r in r_vals]
    ax.scatter(seeds, r_vals, color=colors, s=80, zorder=5)
    ax.axhline(0, color="black", linewidth=1.0, label="r = 0")
    ax.axhline(_mean(r_vals), color="seagreen", linestyle="--", linewidth=1.4,
               label=f"Phase 6a mean r = {_mean(r_vals):+.4f}")
    ax.axhline(PHASE4_NEUTRAL_R, color="steelblue", linestyle=":", linewidth=1.2,
               label=f"Phase 4 neutral baseline (r={PHASE4_NEUTRAL_R:+.3f})")
    ax.set_xlabel("Seed")
    ax.set_ylabel("Pearson r (care_weight vs generation)")
    ax.set_title(
        "Phase 6a — Selection Gradient per Seed\n"
        "Green = positive (care rising) | Red = negative (care eroding)"
    )
    ax.legend(loc="lower right", frameon=True)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    path = os.path.join(output_dir, "phase6_pearson_r.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =============================================================================
# Main
# =============================================================================

def run_all(seeds=SEEDS, max_workers=None):
    os.makedirs(COMBINED_DIR, exist_ok=True)

    if max_workers is None:
        max_workers = min(len(seeds), os.cpu_count() or 4)

    # ── Parallel path ─────────────────────────────────────────────────────────
    if max_workers > 1:
        print(f"\nPhase 6 multi-seed ({len(seeds)} seeds) — PARALLEL (workers={max_workers})")
        print(f"  Ecology: mult={MULT}, scatter=2, care_init={INIT_CARE}")
        print(f"  Note: per-seed output is interleaved below\n")

        raw_results = {}
        packed = [(s, PROJECT_ROOT) for s in seeds]
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_run_seed_worker, p): p[0] for p in packed}
            for fut in as_completed(futures):
                r = fut.result()
                raw_results[r["seed"]] = r
                print(f"  [done] seed={r['seed']}  survived={r['survived']}  "
                      f"final_cw={r['final_cw']:.4f}  final_lr={r['final_lr']:.4f}")

        run_dirs  = {str(r["seed"]): r["evo_dir"] for r in raw_results.values()}
        summaries = []
        for seed in seeds:
            r     = raw_results[seed]
            snaps = _load_snapshots(r["evo_dir"])
            bald  = _classify_baldwin(snaps, r["final_lr"])
            summaries.append({
                "seed":           seed,
                "survived":       r["survived"],
                "final_cw":       r["final_cw"],
                "final_lr":       r["final_lr"],
                "pearson_r":      r["pearson_r"],
                "is_baldwin":     bald["is_baldwin"],
                "care_recovery":  bald.get("care_recovery", 0.0),
                "lr_delta":       bald.get("lr_delta", 0.0),
                "lr_swept":       bald.get("lr_swept", False),
                "care_recovered": bald.get("care_recovered", False),
                "run_dir":        r["evo_dir"],
            })

        cp = {"completed": seeds, "run_dirs": run_dirs, "summaries": summaries}
        _save_checkpoint(cp)

    # ── Sequential path (checkpoint-safe) ────────────────────────────────────
    else:
        cp        = _load_checkpoint()
        done      = set(cp["completed"])
        run_dirs  = dict(cp["run_dirs"])
        summaries = list(cp["summaries"])

        print(f"\nPhase 6 multi-seed ({len(seeds)} seeds): {seeds}")
        print(f"  Condition: kin-conditional plasticity (phase6a)")
        print(f"  Ecology:   mult={MULT}, scatter=2, care_init={INIT_CARE}")
        if done:
            print(f"  [checkpoint] Resuming — completed: {sorted(done)}")
        print()

        for seed in seeds:
            if seed in done:
                print(f"  [checkpoint] seed={seed} already done, skipping.")
                continue

            print(f"--- seed={seed} ---")
            evo_dir = run_evolution(seed=seed, kin_conditional=True)
            run_dirs[str(seed)] = evo_dir

            snaps  = _load_snapshots(evo_dir)
            grad_r = _pearson_r(os.path.join(evo_dir, "birth_log.csv"))

            final_cw, final_lr, survived = 0.0, 0.0, False
            if snaps:
                last     = snaps[-1]
                final_cw = last["avg_care_weight"]
                final_lr = last["avg_learning_rate"]
                survived = last["n_mothers"] >= 10

            bald = _classify_baldwin(snaps, final_lr)

            summaries.append({
                "seed":           seed,
                "survived":       survived,
                "final_cw":       final_cw,
                "final_lr":       final_lr,
                "pearson_r":      grad_r,
                "is_baldwin":     bald["is_baldwin"],
                "care_recovery":  bald.get("care_recovery", 0.0),
                "lr_delta":       bald.get("lr_delta", 0.0),
                "lr_swept":       bald.get("lr_swept", False),
                "care_recovered": bald.get("care_recovered", False),
                "run_dir":        evo_dir,
            })

            cp["completed"] = list(done | {seed})
            cp["run_dirs"]  = run_dirs
            cp["summaries"] = summaries
            done.add(seed)
            _save_checkpoint(cp)
            print(f"  [checkpoint] seed={seed} saved.\n")

    # ── Save manifest ────────────────────────────────────────────────────────
    with open(os.path.join(COMBINED_DIR, "run_dirs.json"), "w") as f:
        json.dump({"seeds": seeds, "run_dirs": run_dirs}, f, indent=2)
    with open(os.path.join(COMBINED_DIR, "summary.json"), "w") as f:
        json.dump(summaries, f, indent=2)

    # ── Statistical test: are r values significantly > 0? ────────────────────
    r_vals = [s["pearson_r"] for s in summaries if s.get("pearson_r") is not None]
    stat_results = {}
    if r_vals and HAS_SCIPY:
        t_res = _scipy_stats.ttest_1samp(r_vals, popmean=0.0)
        stat_results = {
            "n_seeds_with_r":  len(r_vals),
            "mean_r":          _mean(r_vals),
            "ci95_r":          [_mean(r_vals) - _ci95(r_vals), _mean(r_vals) + _ci95(r_vals)],
            "ttest_vs_zero":   {"t": float(t_res.statistic), "p": float(t_res.pvalue)},
            "n_positive":      sum(1 for r in r_vals if r > 0),
            "n_negative":      sum(1 for r in r_vals if r < 0),
        }
        with open(os.path.join(COMBINED_DIR, "statistical_results.json"), "w") as f:
            json.dump(stat_results, f, indent=2)

    # ── Plots ─────────────────────────────────────────────────────────────────
    all_snaps = [_load_snapshots(run_dirs[str(s)]) for s in seeds if str(s) in run_dirs]
    _plot_trajectories([s for s in all_snaps if s], seeds, summaries, COMBINED_DIR)
    _plot_pearson_r(summaries, COMBINED_DIR)

    # ── Summary table ─────────────────────────────────────────────────────────
    print("\n=== Phase 6a Multi-Seed Summary ===")
    print(f"{'Seed':>5}  {'Surv':>6}  {'care_w':>7}  {'learn_r':>8}  {'Pears_r':>9}  {'Baldwin':>8}")
    print("-" * 58)
    for s in summaries:
        r_str  = f"{s['pearson_r']:+.4f}" if s.get("pearson_r") is not None else "   N/A"
        bald   = "YES" if s.get("is_baldwin") else "no"
        surv   = "YES" if s.get("survived") else "EXTINCT"
        print(f"{s['seed']:>5}  {surv:>6}  {s['final_cw']:>7.4f}  {s['final_lr']:>8.4f}  {r_str:>9}  {bald:>8}")

    n_surv    = sum(1 for s in summaries if s.get("survived"))
    n_baldwin = sum(1 for s in summaries if s.get("is_baldwin"))
    cw_vals   = [s["final_cw"] for s in summaries if s.get("survived")]
    lr_vals   = [s["final_lr"] for s in summaries if s.get("survived")]
    print("-" * 58)
    print(f"  Survived   : {n_surv}/{len(summaries)} seeds")
    print(f"  Baldwin    : {n_baldwin}/{len(summaries)} seeds")
    if cw_vals:
        print(f"  Mean care_w: {_mean(cw_vals):.4f} +/- {_ci95(cw_vals):.4f} (95% CI, survived seeds)")
        print(f"  Mean learn_r: {_mean(lr_vals):.4f} +/- {_ci95(lr_vals):.4f} (95% CI, survived seeds)")
    if stat_results:
        t  = stat_results["ttest_vs_zero"]
        print(f"\n  Pearson r vs 0: t={t['t']:+.4f}, p={t['p']:.4f}  "
              f"({'SIGNIFICANT' if t['p'] < 0.05 else 'NOT significant'}, one-sample t-test)")
        print(f"  Mean r = {stat_results['mean_r']:+.4f}  "
              f"({stat_results['n_positive']}/{stat_results['n_seeds_with_r']} positive)")
        print(f"  Phase 4 neutral baseline: r={PHASE4_NEUTRAL_R:+.3f}")
    print(f"\n  Combined output: {COMBINED_DIR}")


if __name__ == "__main__":
    run_all(max_workers=None)  # None = auto-detect CPU count
