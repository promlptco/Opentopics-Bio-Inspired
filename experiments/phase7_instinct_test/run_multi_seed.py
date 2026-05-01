# experiments/phase7_instinct_test/run_multi_seed.py
"""Phase 7 — Multi-seed runner (10 seeds, zero-shot instinct test).

Produces the key Baldwin Effect graph:
  - Fitness (n_mothers)          — solid line, stable through both stages
  - Phenotypic Plasticity        — dashed line, peaks in Stage 1, drops in Stage 2
  - Genetic care_weight          — dotted line, holds or rises through both stages
  Vertical dashed line marks Stage 1 -> Stage 2 boundary (tick 5000).

Verdict: Baldwin Effect confirmed if >=70% seeds survive Stage 2 with
         genetic care_weight >= Phase 6d starting value (0.325).
"""
import sys
import os
import json
import math
from concurrent.futures import ProcessPoolExecutor, as_completed

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase7_instinct_test.run import (
    run_phase7, MLE_MULT, INIT_CARE, INIT_DS, INIT_CR, INIT_LR,
    STAGE1_TICKS, TOTAL_TICKS,
)

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 11, "axes.labelsize": 11,
        "xtick.labelsize": 10, "ytick.labelsize": 10,
        "legend.fontsize": 10, "legend.framealpha": 0.93, "legend.edgecolor": "0.6",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.8, "grid.alpha": 0.22, "grid.linewidth": 0.5,
        "lines.linewidth": 2.2, "figure.facecolor": "white", "axes.facecolor": "white",
    })
    HAS_PLT = True
except ImportError:
    HAS_PLT = False

SEEDS        = list(range(42, 52))
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase7_instinct_test", "multi_seed")


def _mean(vals):
    return sum(vals) / len(vals) if vals else float("nan")


def _ci95(vals):
    n = len(vals)
    if n < 2:
        return 0.0
    m = _mean(vals)
    var = sum((x - m) ** 2 for x in vals) / (n - 1)
    return 1.96 * math.sqrt(var / n)


def _run_seed_worker(packed):
    seed, project_root = packed
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import json as _json
    from experiments.phase7_instinct_test.run import run_phase7, INIT_CARE

    rd        = run_phase7(seed=seed)
    snap_path = os.path.join(rd, "generation_snapshots.json")
    snaps     = _json.load(open(snap_path)) if os.path.exists(snap_path) else []

    s1 = [s for s in snaps if s["stage"] == 1]
    s2 = [s for s in snaps if s["stage"] == 2]

    entry_cw  = s1[-1]["avg_care_weight"]           if s1 else None
    entry_ecw = s1[-1]["avg_expressed_care_weight"]  if s1 else None
    final_cw  = s2[-1]["avg_care_weight"]            if s2 else None
    final_pop = s2[-1]["n_mothers"]                  if s2 else 0
    final_lr  = s2[-1]["avg_learning_rate"]          if s2 else None

    survived           = (final_pop or 0) >= 10
    instinct_confirmed = survived and (final_cw or 0) >= INIT_CARE

    return {
        "seed": seed, "run_dir": rd,
        "survived": survived, "final_pop": final_pop,
        "entry_cw": entry_cw, "entry_ecw": entry_ecw,
        "final_cw": final_cw, "final_lr": final_lr,
        "instinct_confirmed": instinct_confirmed,
    }


def _load_snapshots(run_dir):
    path = os.path.join(run_dir, "generation_snapshots.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _plot_baldwin_graph(all_snaps, seeds, results, output_dir):
    """
    The key Baldwin Effect graph — mirrors the textbook diagram:
      Panel 1: Fitness (n_mothers) — solid, stable across both stages
      Panel 2: Phenotypic Plasticity (avg_expressed_care_weight) — dashed,
               peaks in Stage 1, then drops in Stage 2 as instinct takes over
               Genetic care_weight (avg_care_weight) — dotted,
               holds steady or rises, showing assimilation floor
    """
    if not HAS_PLT or not all_snaps:
        return

    # Use all ticks present in any snapshot across all seeds
    all_ticks = sorted(set(s["tick"] for snaps in all_snaps for s in snaps))
    if not all_ticks:
        return

    def get(snaps, t, key, default=None):
        for s in snaps:
            if s["tick"] == t:
                return s.get(key, default)
        return default

    # Build per-seed time series, padding missing ticks with None
    pop_series   = [[get(snaps, t, "n_mothers")                 for t in all_ticks] for snaps in all_snaps]
    ecw_series   = [[get(snaps, t, "avg_expressed_care_weight")  for t in all_ticks] for snaps in all_snaps]
    cw_series    = [[get(snaps, t, "avg_care_weight")            for t in all_ticks] for snaps in all_snaps]

    def safe_mean(series, i):
        vals = [s[i] for s in series if s[i] is not None]
        return _mean(vals) if vals else float("nan")

    def safe_ci(series, i):
        vals = [s[i] for s in series if s[i] is not None]
        return _ci95(vals) if len(vals) >= 2 else 0.0

    pop_mean  = [safe_mean(pop_series,  i) for i in range(len(all_ticks))]
    ecw_mean  = [safe_mean(ecw_series,  i) for i in range(len(all_ticks))]
    cw_mean   = [safe_mean(cw_series,   i) for i in range(len(all_ticks))]
    pop_ci    = [safe_ci(pop_series,    i) for i in range(len(all_ticks))]
    ecw_ci    = [safe_ci(ecw_series,    i) for i in range(len(all_ticks))]
    cw_ci     = [safe_ci(cw_series,     i) for i in range(len(all_ticks))]

    n_survived = sum(1 for r in results if r["survived"])
    n_instinct = sum(1 for r in results if r["instinct_confirmed"])

    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    fig.suptitle(
        f"Phase 7 — Baldwin Effect: Phenotypic Plasticity → Genetic Instinct\n"
        f"MLE={MLE_MULT} | care_init={INIT_CARE} | DS={INIT_DS} | CR={INIT_CR} | {len(seeds)} seeds\n"
        f"Stage 2 survived: {n_survived}/{len(seeds)}  |  Instinct confirmed: {n_instinct}/{len(seeds)}",
        fontsize=11,
    )

    # ── Panel 1: Fitness (n_mothers) ──────────────────────────────────────────
    ax = axes[0]
    for snaps in all_snaps:
        ticks = [s["tick"] for s in snaps]
        vals  = [s["n_mothers"] for s in snaps]
        ax.plot(ticks, vals, color="#2ca02c", alpha=0.10, linewidth=0.8)

    lo_pop = [m - c for m, c in zip(pop_mean, pop_ci)]
    hi_pop = [m + c for m, c in zip(pop_mean, pop_ci)]
    ax.fill_between(all_ticks, lo_pop, hi_pop, alpha=0.20, color="#2ca02c")
    ax.plot(all_ticks, pop_mean, color="#2ca02c", linewidth=2.5,
            label="Fitness (population size)  mean +/- 95% CI")
    ax.axvline(STAGE1_TICKS, color="black", linestyle="--", linewidth=1.4, alpha=0.7)
    ax.set_ylabel("Number of mothers")
    ax.set_ylim(0, 60)
    ax.text(STAGE1_TICKS - 200, ax.get_ylim()[1] * 0.92, "first step",
            ha="right", fontsize=9, color="black", alpha=0.7)
    ax.text(STAGE1_TICKS + 200, ax.get_ylim()[1] * 0.92, "second step",
            ha="left", fontsize=9, color="black", alpha=0.7)
    ax.legend(loc="lower right", frameon=True)
    ax.grid(True)

    # ── Panel 2: Phenotypic Plasticity + Genetic floor ───────────────────────
    ax = axes[1]

    # Individual seed traces (faint)
    for snaps in all_snaps:
        ticks = [s["tick"] for s in snaps]
        ecw   = [s["avg_expressed_care_weight"] for s in snaps]
        cw    = [s["avg_care_weight"] for s in snaps]
        ax.plot(ticks, ecw, color="#d62728", alpha=0.10, linewidth=0.8)
        ax.plot(ticks, cw,  color="steelblue", alpha=0.08, linewidth=0.8)

    # Expressed care (phenotypic plasticity) — dashed red
    lo_ecw = [m - c for m, c in zip(ecw_mean, ecw_ci)]
    hi_ecw = [m + c for m, c in zip(ecw_mean, ecw_ci)]
    ax.fill_between(all_ticks, lo_ecw, hi_ecw, alpha=0.18, color="#d62728")
    ax.plot(all_ticks, ecw_mean, color="#d62728", linewidth=2.5, linestyle="--",
            label="Phenotypic Plasticity (expressed care_weight)  mean +/- 95% CI")

    # Genetic care_weight — solid blue (the instinct floor)
    lo_cw = [m - c for m, c in zip(cw_mean, cw_ci)]
    hi_cw = [m + c for m, c in zip(cw_mean, cw_ci)]
    ax.fill_between(all_ticks, lo_cw, hi_cw, alpha=0.18, color="steelblue")
    ax.plot(all_ticks, cw_mean, color="steelblue", linewidth=2.5,
            label="Fitness / Genetic care_weight (instinct floor)  mean +/- 95% CI")

    ax.axhline(INIT_CARE, color="gray", linestyle=":", linewidth=1.2,
               label=f"Phase 6d genome start ({INIT_CARE})")
    ax.axvline(STAGE1_TICKS, color="black", linestyle="--", linewidth=1.4, alpha=0.7)
    ax.set_xlabel("Simulation tick  (Stage 1: plasticity ON  |  Stage 2: plasticity OFF)")
    ax.set_ylabel("care_weight")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", frameon=True)
    ax.grid(True)

    fig.tight_layout()
    path = os.path.join(output_dir, "phase7_baldwin_effect.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def main(max_workers=None):
    os.makedirs(COMBINED_DIR, exist_ok=True)

    if max_workers is None:
        max_workers = min(len(SEEDS), os.cpu_count() or 4)

    print(f"\nPhase 7 — Zero-Shot Instinct Test ({len(SEEDS)} seeds)")
    print(f"  MLE ecology     : mult={MLE_MULT}")
    print(f"  Genome init     : care={INIT_CARE}, DS={INIT_DS}, CR={INIT_CR}, LR={INIT_LR}")
    print(f"  Stage 1         : ticks 0-{STAGE1_TICKS}  (plasticity ON)")
    print(f"  Stage 2         : ticks {STAGE1_TICKS}-{TOTAL_TICKS}  (plasticity OFF)")
    print(f"  Seeds           : {SEEDS}")
    print(f"  Workers         : {max_workers}\n")

    run_dirs = {}
    results  = []

    packed = [(s, PROJECT_ROOT) for s in SEEDS]
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_seed_worker, p): p[0] for p in packed}
        for fut in as_completed(futures):
            r = fut.result()
            run_dirs[r["seed"]] = r["run_dir"]
            results.append({k: v for k, v in r.items() if k != "run_dir"})
            print(f"  [done] seed={r['seed']}  survived={r['survived']}  "
                  f"instinct={r['instinct_confirmed']}  pop={r['final_pop']}")

    results.sort(key=lambda r: r["seed"])

    manifest = {"seeds": SEEDS, "run_dirs": {str(s): d for s, d in run_dirs.items()}}
    with open(os.path.join(COMBINED_DIR, "run_dirs.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    with open(os.path.join(COMBINED_DIR, "summary.json"), "w") as f:
        json.dump(results, f, indent=2)

    all_snaps = [_load_snapshots(run_dirs[s]) for s in SEEDS if s in run_dirs]
    _plot_baldwin_graph([s for s in all_snaps if s], SEEDS, results, COMBINED_DIR)

    print("\n=== Phase 7 Multi-Seed Summary ===")
    print(f"  {'Seed':>5}  {'Surv':>5}  {'Pop':>4}  {'entry_cw':>9}  {'entry_ecw':>10}  {'final_cw':>9}  {'Instinct':>9}")
    print("-" * 68)
    for r in results:
        surv = "YES" if r["survived"]           else "NO"
        inst = "YES" if r["instinct_confirmed"]  else "NO"
        ecw  = f"{r['entry_ecw']:.4f}" if r["entry_ecw"] is not None else "   N/A"
        ecw  = f"{r['entry_cw']:.4f}"  if r["entry_cw"]  is not None else "   N/A"
        fcw  = f"{r['final_cw']:.4f}"  if r["final_cw"]  is not None else "   N/A"
        pop  = r["final_pop"] or 0
        ecwv = f"{r['entry_ecw']:.4f}" if r["entry_ecw"] is not None else "   N/A"
        print(f"  {r['seed']:>5}  {surv:>5}  {pop:>4}  {ecw:>9}  {ecwv:>10}  {fcw:>9}  {inst:>9}")

    print("-" * 68)
    n_survived = sum(1 for r in results if r["survived"])
    n_instinct = sum(1 for r in results if r["instinct_confirmed"])
    print(f"  Survived (Stage 2)   : {n_survived}/{len(SEEDS)} seeds")
    print(f"  Instinct confirmed   : {n_instinct}/{len(SEEDS)} seeds")

    cw_vals  = [r["final_cw"]  for r in results if r["survived"] and r["final_cw"]  is not None]
    lr_vals  = [r["final_lr"]  for r in results if r["survived"] and r["final_lr"]  is not None]
    if cw_vals:
        print(f"  Mean final care_w    : {_mean(cw_vals):.4f}  (Phase 6d start: {INIT_CARE})")
    if lr_vals:
        print(f"  Mean final learn_r   : {_mean(lr_vals):.4f}  (Phase 6d start: {INIT_LR:.4f})")

    threshold = 0.7
    verdict = (
        "BALDWIN EFFECT CONFIRMED"
        if n_instinct >= len(SEEDS) * threshold
        else "INCONCLUSIVE / FAILED"
    )
    print(f"\n  Verdict : {verdict}")
    print(f"  (Threshold: >={int(threshold*100)}% seeds survive Stage 2 with care_weight >= {INIT_CARE})")
    print(f"\n  Output  : {COMBINED_DIR}")


if __name__ == "__main__":
    main(max_workers=None)
