# experiments/phase6d_biology_test/run_multi_seed.py
"""
Phase 6d — multi-seed runner (10 seeds, Options A+D, MLE=1.10).

Tests whether lowering MLE from 1.25 (Phase 6c) to 1.10 allows the combined
distress_sensitivity + care_recovery mechanism to complete genetic assimilation
without demographic collapse.

Baldwin classification per seed:
  care_recovered : final_cw - min_cw >= 0.05
  lr_swept       : final_lr - 0.10   >= 0.03  (learning_rate eroded → assimilation)
  is_baldwin     : care_recovered AND lr_swept
"""
import sys
import os
import json
import math
from concurrent.futures import ProcessPoolExecutor, as_completed

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


def _run_seed_worker(packed):
    """Top-level picklable worker — Windows spawn-safe."""
    seed, project_root = packed
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import json as _json
    from experiments.phase6d_biology_test.run import run_phase6d, _pearson_r

    out_dir   = run_phase6d(seed=seed)
    snap_path = os.path.join(out_dir, "generation_snapshots.json")
    snaps     = _json.load(open(snap_path)) if os.path.exists(snap_path) else []
    grad_r    = _pearson_r(os.path.join(out_dir, "birth_log.csv"))

    final_cw = final_lr = final_ds = final_cr = 0.0
    survived = False
    if snaps:
        last     = snaps[-1]
        final_cw = last.get("avg_care_weight", 0.0)
        final_lr = last.get("avg_learning_rate", 0.0)
        final_ds = last.get("avg_distress_sensitivity", 0.0)
        final_cr = last.get("avg_care_recovery", 0.0)
        survived = last["n_mothers"] >= 10

    return {
        "seed": seed, "out_dir": out_dir, "survived": survived,
        "final_cw": final_cw, "final_lr": final_lr,
        "final_ds": final_ds, "final_cr": final_cr,
        "pearson_r": grad_r,
    }


from experiments.phase6d_biology_test.run import (
    run_phase6d, _pearson_r, MULT, INIT_CARE, INIT_DS, INIT_CR,
)

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
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase6d_biology_test", "multi_seed")
CHECKPOINT   = os.path.join(COMBINED_DIR, "checkpoint.json")

PHASE3_CANONICAL_LR = 0.10
PHASE4_NEUTRAL_R    = -0.034
BALDWIN_CARE_MIN    = 0.05
BALDWIN_LR_MIN      = 0.03


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
    care_vals       = [s["avg_care_weight"] for s in snaps]
    trough          = min(care_vals)
    final_care      = care_vals[-1]
    recovery        = final_care - trough
    lr_delta        = final_lr - PHASE3_CANONICAL_LR
    care_recovered  = recovery >= BALDWIN_CARE_MIN
    lr_swept        = lr_delta >= BALDWIN_LR_MIN
    return {
        "is_baldwin":    care_recovered and lr_swept,
        "care_trough":   trough,
        "care_final":    final_care,
        "care_recovery": recovery,
        "lr_start":      PHASE3_CANONICAL_LR,
        "lr_final":      final_lr,
        "lr_delta":      lr_delta,
        "care_recovered": care_recovered,
        "lr_swept":       lr_swept,
    }


def _load_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {"completed": [], "run_dirs": {}, "summaries": []}


def _save_checkpoint(cp):
    os.makedirs(COMBINED_DIR, exist_ok=True)
    with open(CHECKPOINT, "w") as f:
        json.dump(cp, f, indent=2)


def _plot_trajectories(all_snaps, seeds, summaries, output_dir):
    if not HAS_PLT or not all_snaps:
        return

    tick_sets    = [set(s["tick"] for s in snaps) for snaps in all_snaps if snaps]
    common_ticks = sorted(set.intersection(*tick_sets)) if tick_sets else []
    if not common_ticks:
        print("  [plot] No common ticks — skipping trajectory plot.")
        return

    def get(snaps, t, key):
        for s in snaps:
            if s["tick"] == t:
                return s.get(key, 0.0)
        return 0.0

    care_by_seed = [[get(snaps, t, "avg_care_weight")          for t in common_ticks] for snaps in all_snaps if snaps]
    ds_by_seed   = [[get(snaps, t, "avg_distress_sensitivity") for t in common_ticks] for snaps in all_snaps if snaps]
    cr_by_seed   = [[get(snaps, t, "avg_care_recovery")        for t in common_ticks] for snaps in all_snaps if snaps]
    lr_by_seed   = [[get(snaps, t, "avg_learning_rate")        for t in common_ticks] for snaps in all_snaps if snaps]

    care_mean = [_mean([s[i] for s in care_by_seed]) for i in range(len(common_ticks))]
    ds_mean   = [_mean([s[i] for s in ds_by_seed])   for i in range(len(common_ticks))]
    cr_mean   = [_mean([s[i] for s in cr_by_seed])   for i in range(len(common_ticks))]
    lr_mean   = [_mean([s[i] for s in lr_by_seed])   for i in range(len(common_ticks))]
    care_ci   = [_ci95([s[i] for s in care_by_seed]) for i in range(len(common_ticks))]
    ds_ci     = [_ci95([s[i] for s in ds_by_seed])   for i in range(len(common_ticks))]
    cr_ci     = [_ci95([s[i] for s in cr_by_seed])   for i in range(len(common_ticks))]

    n_survived = sum(1 for s in summaries if s.get("survived"))
    n_baldwin  = sum(1 for s in summaries if s.get("is_baldwin"))

    fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)
    fig.suptitle(
        f"Phase 6d — Options A+D: distress_sensitivity + care_recovery\n"
        f"Phase 3 init: care={INIT_CARE}, DS={INIT_DS}, CR={INIT_CR} | "
        f"mult={MULT} | scatter=2 | {len(seeds)} seeds\n"
        f"Survived: {n_survived}/{len(seeds)}  |  Baldwin: {n_baldwin}/{len(seeds)}",
        fontsize=10,
    )

    ax = axes[0]
    for snaps in all_snaps:
        if snaps:
            ax.plot([s["tick"] for s in snaps], [s["avg_care_weight"] for s in snaps],
                    color="#2ca02c", alpha=0.12, linewidth=0.9)
    lo = [m - c for m, c in zip(care_mean, care_ci)]
    hi = [m + c for m, c in zip(care_mean, care_ci)]
    ax.fill_between(common_ticks, lo, hi, alpha=0.22, color="#2ca02c")
    ax.plot(common_ticks, care_mean, color="#2ca02c", linewidth=2.2,
            label=f"Phase 6d mean ± 95% CI  (n={len(all_snaps)} seeds)")
    ax.axhline(INIT_CARE, color="crimson", linestyle="--", linewidth=1.4,
               label=f"Phase 3 canonical init ({INIT_CARE})")
    ax.set_ylabel("Mean care_weight (genetic)")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left", frameon=True, ncol=2)
    ax.grid(True)

    ax = axes[1]
    for snaps in all_snaps:
        if snaps:
            ax.plot([s["tick"] for s in snaps],
                    [s.get("avg_distress_sensitivity", 0) for s in snaps],
                    color="coral", alpha=0.12, linewidth=0.9)
    lo2 = [m - c for m, c in zip(ds_mean, ds_ci)]
    hi2 = [m + c for m, c in zip(ds_mean, ds_ci)]
    ax.fill_between(common_ticks, lo2, hi2, alpha=0.22, color="coral")
    ax.plot(common_ticks, ds_mean, color="coral", linewidth=2.2,
            label="distress_sensitivity mean ± 95% CI  (Option A)")
    ax.axhline(INIT_DS, color="gray", linestyle="--", linewidth=1.2,
               label=f"Genome init ({INIT_DS})")
    ax.set_ylabel("distress_sensitivity")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True)

    ax = axes[2]
    for snaps in all_snaps:
        if snaps:
            ax.plot([s["tick"] for s in snaps],
                    [s.get("avg_care_recovery", 0) for s in snaps],
                    color="steelblue", alpha=0.12, linewidth=0.9)
    lo3 = [m - c for m, c in zip(cr_mean, cr_ci)]
    hi3 = [m + c for m, c in zip(cr_mean, cr_ci)]
    ax.fill_between(common_ticks, lo3, hi3, alpha=0.22, color="steelblue")
    ax.plot(common_ticks, cr_mean, color="steelblue", linewidth=2.2,
            label="care_recovery mean ± 95% CI  (Option D)")
    ax.axhline(INIT_CR, color="gray", linestyle="--", linewidth=1.2,
               label=f"Genome init ({INIT_CR})")
    ax.set_ylabel("care_recovery")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True)

    ax = axes[3]
    ax.plot(common_ticks, lr_mean, color="mediumpurple", linewidth=2.2,
            label="learning_rate mean  (genetic assimilation signal)")
    ax.axhline(PHASE3_CANONICAL_LR, color="gray", linestyle="--", linewidth=1.2,
               label=f"Genome init ({PHASE3_CANONICAL_LR})")
    ax.set_xlabel("Simulation tick  (~100 ticks per generation)")
    ax.set_ylabel("learning_rate")
    ax.set_ylim(0, 0.5)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True)

    fig.tight_layout()
    path = os.path.join(output_dir, "phase6d_care_trajectory.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def _plot_pearson_r(summaries, output_dir):
    if not HAS_PLT or not summaries:
        return
    r_vals = [s.get("pearson_r") for s in summaries if s.get("pearson_r") is not None]
    seeds  = [s["seed"] for s in summaries if s.get("pearson_r") is not None]
    if not r_vals:
        print("  [plot] No Pearson r values — skipping r plot.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["seagreen" if r > 0 else "crimson" for r in r_vals]
    ax.scatter(seeds, r_vals, color=colors, s=80, zorder=5)
    ax.axhline(0, color="black", linewidth=1.0, label="r = 0")
    ax.axhline(_mean(r_vals), color="seagreen", linestyle="--", linewidth=1.4,
               label=f"Phase 6d mean r = {_mean(r_vals):+.4f}")
    ax.axhline(PHASE4_NEUTRAL_R, color="steelblue", linestyle=":", linewidth=1.2,
               label=f"Phase 4 neutral baseline (r={PHASE4_NEUTRAL_R:+.3f})")
    ax.set_xlabel("Seed")
    ax.set_ylabel("Pearson r (care_weight vs generation)")
    ax.set_title(
        "Phase 6d — Selection Gradient per Seed (Options A+D, MLE=1.10)\n"
        "Green = positive (care rising) | Red = negative (care eroding)"
    )
    ax.legend(loc="lower right", frameon=True)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path = os.path.join(output_dir, "phase6d_pearson_r.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def run_all(seeds=SEEDS, max_workers=None):
    os.makedirs(COMBINED_DIR, exist_ok=True)

    if max_workers is None:
        max_workers = min(len(seeds), os.cpu_count() or 4)

    if max_workers > 1:
        print(f"\nPhase 6d multi-seed ({len(seeds)} seeds) — PARALLEL (workers={max_workers})")
        print(f"  Options A+D: distress_sensitivity={INIT_DS}, care_recovery={INIT_CR}")
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
                      f"cw={r['final_cw']:.4f}  ds={r['final_ds']:.4f}  cr={r['final_cr']:.4f}")

        run_dirs  = {str(r["seed"]): r["out_dir"] for r in raw_results.values()}
        summaries = []
        for seed in seeds:
            r     = raw_results[seed]
            snaps = _load_snapshots(r["out_dir"])
            bald  = _classify_baldwin(snaps, r["final_lr"])
            summaries.append({
                "seed": seed, "survived": r["survived"],
                "final_cw": r["final_cw"], "final_lr": r["final_lr"],
                "final_ds": r["final_ds"], "final_cr": r["final_cr"],
                "pearson_r": r["pearson_r"],
                "is_baldwin": bald["is_baldwin"],
                "care_recovery_delta": bald.get("care_recovery", 0.0),
                "lr_delta": bald.get("lr_delta", 0.0),
                "lr_swept": bald.get("lr_swept", False),
                "care_recovered": bald.get("care_recovered", False),
                "run_dir": r["out_dir"],
            })

        cp = {"completed": seeds, "run_dirs": run_dirs, "summaries": summaries}
        _save_checkpoint(cp)

    else:
        cp        = _load_checkpoint()
        done      = set(cp["completed"])
        run_dirs  = dict(cp["run_dirs"])
        summaries = list(cp["summaries"])

        print(f"\nPhase 6d multi-seed ({len(seeds)} seeds): {seeds}")
        print(f"  Options A+D: distress_sensitivity={INIT_DS}, care_recovery={INIT_CR}")
        print(f"  Ecology: mult={MULT}, scatter=2, care_init={INIT_CARE}")
        if done:
            print(f"  [checkpoint] Resuming — completed: {sorted(done)}")
        print()

        for seed in seeds:
            if seed in done:
                print(f"  [checkpoint] seed={seed} already done, skipping.")
                continue
            print(f"--- seed={seed} ---")
            out_dir = run_phase6d(seed=seed)
            run_dirs[str(seed)] = out_dir

            snaps  = _load_snapshots(out_dir)
            grad_r = _pearson_r(os.path.join(out_dir, "birth_log.csv"))

            final_cw = final_lr = final_ds = final_cr = 0.0
            survived = False
            if snaps:
                last     = snaps[-1]
                final_cw = last.get("avg_care_weight", 0.0)
                final_lr = last.get("avg_learning_rate", 0.0)
                final_ds = last.get("avg_distress_sensitivity", 0.0)
                final_cr = last.get("avg_care_recovery", 0.0)
                survived = last["n_mothers"] >= 10

            bald = _classify_baldwin(snaps, final_lr)
            summaries.append({
                "seed": seed, "survived": survived,
                "final_cw": final_cw, "final_lr": final_lr,
                "final_ds": final_ds, "final_cr": final_cr,
                "pearson_r": grad_r,
                "is_baldwin": bald["is_baldwin"],
                "care_recovery_delta": bald.get("care_recovery", 0.0),
                "lr_delta": bald.get("lr_delta", 0.0),
                "lr_swept": bald.get("lr_swept", False),
                "care_recovered": bald.get("care_recovered", False),
                "run_dir": out_dir,
            })

            done.add(seed)
            cp["completed"] = list(done)
            cp["run_dirs"]  = run_dirs
            cp["summaries"] = summaries
            _save_checkpoint(cp)
            print(f"  [checkpoint] seed={seed} saved.\n")

    with open(os.path.join(COMBINED_DIR, "run_dirs.json"), "w") as f:
        json.dump({"seeds": seeds, "run_dirs": run_dirs}, f, indent=2)
    with open(os.path.join(COMBINED_DIR, "summary.json"), "w") as f:
        json.dump(summaries, f, indent=2)

    r_vals = [s["pearson_r"] for s in summaries if s.get("pearson_r") is not None]
    stat_results = {}
    if r_vals and HAS_SCIPY:
        t_res = _scipy_stats.ttest_1samp(r_vals, popmean=0.0)
        stat_results = {
            "n_seeds_with_r": len(r_vals),
            "mean_r":         _mean(r_vals),
            "ttest_vs_zero":  {"t": float(t_res.statistic), "p": float(t_res.pvalue)},
            "n_positive":     sum(1 for r in r_vals if r > 0),
        }
        with open(os.path.join(COMBINED_DIR, "statistical_results.json"), "w") as f:
            json.dump(stat_results, f, indent=2)

    all_snaps = [_load_snapshots(run_dirs[str(s)]) for s in seeds if str(s) in run_dirs]
    _plot_trajectories([s for s in all_snaps if s], seeds, summaries, COMBINED_DIR)
    _plot_pearson_r(summaries, COMBINED_DIR)

    print("\n=== Phase 6d Multi-Seed Summary (Options A+D, MLE=1.10) ===")
    print(f"{'Seed':>5}  {'Surv':>6}  {'care_w':>7}  {'DS':>7}  {'CR':>7}  {'learn_r':>8}  {'Pears_r':>9}  {'Baldwin':>8}")
    print("-" * 72)
    for s in summaries:
        r_str = f"{s['pearson_r']:+.4f}" if s.get("pearson_r") is not None else "   N/A"
        bald  = "YES" if s.get("is_baldwin") else "no"
        surv  = "YES" if s.get("survived") else "EXTINCT"
        print(f"{s['seed']:>5}  {surv:>6}  {s['final_cw']:>7.4f}  "
              f"{s['final_ds']:>7.4f}  {s['final_cr']:>7.4f}  "
              f"{s['final_lr']:>8.4f}  {r_str:>9}  {bald:>8}")

    n_surv    = sum(1 for s in summaries if s.get("survived"))
    n_baldwin = sum(1 for s in summaries if s.get("is_baldwin"))
    cw_vals   = [s["final_cw"] for s in summaries if s.get("survived")]
    print("-" * 72)
    print(f"  Survived : {n_surv}/{len(summaries)} seeds")
    print(f"  Baldwin  : {n_baldwin}/{len(summaries)} seeds")
    if cw_vals:
        print(f"  Mean care_w (survived): {_mean(cw_vals):.4f} +/- {_ci95(cw_vals):.4f}")
    if stat_results:
        t = stat_results["ttest_vs_zero"]
        print(f"\n  Pearson r vs 0: t={t['t']:+.4f}, p={t['p']:.4f}  "
              f"({'SIGNIFICANT' if t['p'] < 0.05 else 'NOT significant'})")
        print(f"  Mean r = {stat_results['mean_r']:+.4f}  "
              f"({stat_results['n_positive']}/{stat_results['n_seeds_with_r']} positive)")
        print(f"  Phase 4 neutral baseline: r={PHASE4_NEUTRAL_R:+.3f}")
    print(f"\n  Combined output: {COMBINED_DIR}")


if __name__ == "__main__":
    run_all(max_workers=None)
