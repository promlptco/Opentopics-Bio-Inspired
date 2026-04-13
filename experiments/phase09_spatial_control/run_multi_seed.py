# experiments/phase09_spatial_control/run_multi_seed.py
"""Phase 09: Spatial-Only Control — multi-seed runner (seeds 42–51).

Runs Phase 09 (mult=1.0, scatter=2, cw~U(0,0.5)) for 10 seeds and reports
the mean Pearson selection gradient across seeds.

Scientific purpose:
  Isolate whether natal philopatry ALONE can reverse the selection gradient.
  Expected: gradient stays ≤ 0 → infant dependency is a necessary condition.

Output: outputs/phase09_spatial_control/multi_seed_evolution/
"""
import sys
import os
import json
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase09_spatial_control.run import run as run_p5d, _compute_selection_gradient

try:
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        'font.size': 10, 'axes.titlesize': 10, 'axes.labelsize': 10,
        'xtick.labelsize': 9, 'ytick.labelsize': 9,
        'legend.fontsize': 9, 'legend.framealpha': 0.93,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': 0.8, 'grid.alpha': 0.22,
        'lines.linewidth': 2.0, 'figure.facecolor': 'white',
    })
except ImportError:
    plt = None

try:
    from scipy import stats as _scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

SEEDS        = list(range(42, 52))
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase09_spatial_control", "multi_seed_evolution")
CHECKPOINT   = os.path.join(COMBINED_DIR, "checkpoint.json")

PHASE3_R   = -0.178
PHASE07_R  = +0.079


# =============================================================================
# Helpers
# =============================================================================

def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _ci95(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean = _mean(values)
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return 1.96 * math.sqrt(variance / n)


def _load_snapshots(run_dir):
    path = os.path.join(run_dir, "generation_snapshots.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


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
# Plot
# =============================================================================

def plot_ci(all_snapshots, seeds, summaries, output_dir):
    if plt is None or not all_snapshots:
        return
    os.makedirs(output_dir, exist_ok=True)

    tick_sets    = [set(s["tick"] for s in snaps) for snaps in all_snapshots if snaps]
    common_ticks = sorted(set.intersection(*tick_sets)) if tick_sets else []

    by_seed = [
        [next((s["avg_care_weight"] for s in snaps if s["tick"] == t), 0.0) for t in common_ticks]
        for snaps in all_snapshots if snaps
    ]
    mean_cw = [_mean([s[i] for s in by_seed]) for i in range(len(common_ticks))]
    ci_cw   = [_ci95([s[i] for s in by_seed]) for i in range(len(common_ticks))]
    lo = [m - c for m, c in zip(mean_cw, ci_cw)]
    hi = [m + c for m, c in zip(mean_cw, ci_cw)]

    valid_grads = [s["grad_r"] for s in summaries if s.get("grad_r") is not None]
    mean_r_str  = f"Mean r = {_mean(valid_grads):+.4f}" if valid_grads else ""

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.suptitle(
        f"Phase 09: Spatial-Only Control (mult=1.0, scatter=2)\n"
        f"{len(seeds)} seeds | depleted init cw ~ U(0, 0.50)",
        fontsize=10,
    )

    for snaps in all_snapshots:
        if not snaps:
            continue
        t_i = [s["tick"]            for s in snaps]
        c_i = [s["avg_care_weight"] for s in snaps]
        ax.plot(t_i, c_i, color="#9467bd", alpha=0.12, linewidth=0.9)

    if common_ticks:
        ax.fill_between(common_ticks, lo, hi, alpha=0.20, color="#9467bd")
        ax.plot(common_ticks, mean_cw, color="#9467bd", linewidth=2.2,
                label=f"Phase 09 — spatial-only (mean ± 95% CI, n={len(seeds)})")

    ax.axhline(0.25,  color="gray",      linestyle="--", linewidth=0.9, alpha=0.65,
               label="Depleted init mean (0.25)")
    ax.axhline(0.420, color="crimson",   linestyle=":",  linewidth=1.0,
               label="Phase 3 final (0.420)")
    ax.axhline(0.290, color="#2ca02c",   linestyle="-.", linewidth=0.9, alpha=0.7,
               label="Phase 5a start ~0.25–0.29")

    ax.set_xlabel("Simulation tick  (≈ 100 ticks per generation)")
    ax.set_ylabel("Mean care_weight")
    ax.set_ylim(0, 0.7)
    ax.legend(loc="upper right", frameon=True)
    ax.grid(True)

    if mean_r_str:
        ax.annotate(
            f"{mean_r_str}  |  Phase 5a: +0.079  |  Phase 3: −0.178",
            xy=(0.97, 0.05), xycoords="axes fraction",
            ha="right", va="bottom", fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow",
                      edgecolor="0.65", linewidth=0.7),
        )

    fig.tight_layout()
    path = os.path.join(output_dir, "multi_seed_care_weight_ci.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =============================================================================
# Main
# =============================================================================

def run_all(seeds=SEEDS):
    os.makedirs(COMBINED_DIR, exist_ok=True)

    cp        = _load_checkpoint()
    done      = set(cp["completed"])
    run_dirs  = dict(cp["run_dirs"])
    summaries = list(cp["summaries"])

    print(f"Phase 09 multi-seed: {len(seeds)} seeds {seeds}")
    if done:
        print(f"  [checkpoint] Completed seeds: {sorted(done)}")
    print()

    for seed in seeds:
        if seed in done:
            print(f"  [checkpoint] seed={seed} already done, skipping.")
            continue

        print(f"--- seed={seed} ---")
        out_dir = run_p5d(seed=seed)
        run_dirs[str(seed)] = out_dir

        snaps = _load_snapshots(out_dir)
        top_path = os.path.join(out_dir, "top_genomes.json")
        grad = _compute_selection_gradient(os.path.join(out_dir, "birth_log.csv"))

        start_cw = snaps[0]["avg_care_weight"]  if snaps else 0.25
        final_cw = snaps[-1]["avg_care_weight"] if snaps else 0.0
        n_surv   = 0
        if os.path.exists(top_path):
            with open(top_path) as f:
                g = json.load(f)
            n_surv   = len(g)
            final_cw = sum(x["care_weight"] for x in g) / n_surv if n_surv else final_cw

        summaries.append({
            "seed":     seed,
            "n_surv":   n_surv,
            "start_cw": start_cw,
            "final_cw": final_cw,
            "grad_r":   grad,
        })

        cp["completed"].append(seed)
        cp["run_dirs"]  = run_dirs
        cp["summaries"] = summaries
        _save_checkpoint(cp)
        print(f"  [checkpoint] seed={seed} saved.\n")

    # ── Save manifests ─────────────────────────────────────────────────────────
    with open(os.path.join(COMBINED_DIR, "run_dirs.json"), "w") as f:
        json.dump({"seeds": seeds, "run_dirs": run_dirs}, f, indent=2)
    with open(os.path.join(COMBINED_DIR, "summary.json"), "w") as f:
        json.dump(summaries, f, indent=2)

    # ── Statistical test ───────────────────────────────────────────────────────
    grads = [s["grad_r"] for s in summaries if s.get("grad_r") is not None]
    stat_result = {}
    if HAS_SCIPY and len(grads) >= 2:
        t_res = _scipy_stats.ttest_1samp(grads, 0.0)
        mean_g = _mean(grads)
        sd_g   = math.sqrt(sum((x - mean_g)**2 for x in grads) / (len(grads) - 1))
        stat_result = {
            "n_seeds":    len(grads),
            "mean_r":     mean_g,
            "ci95":       [mean_g - _ci95(grads), mean_g + _ci95(grads)],
            "phase3_ref": PHASE3_R,
            "phase07_ref": PHASE07_R,
            "ttest_t":    float(t_res.statistic),
            "ttest_p":    float(t_res.pvalue),
            "cohens_d":   mean_g / sd_g if sd_g > 0 else 0.0,
            "positive":   mean_g > 0,
        }
    with open(os.path.join(COMBINED_DIR, "statistical_tests.json"), "w") as f:
        json.dump(stat_result, f, indent=2)

    # ── Plot ───────────────────────────────────────────────────────────────────
    all_snaps = [_load_snapshots(run_dirs[str(s)]) for s in seeds if str(s) in run_dirs]
    plot_ci(all_snaps, seeds, summaries, COMBINED_DIR)

    # ── Summary table ──────────────────────────────────────────────────────────
    print("\n=== Phase 09 Spatial-Only Control — Summary ===")
    print(f"{'Seed':>5}  {'Surv':>5}  {'Start_cw':>8}  {'Final_cw':>8}  {'Grad_r':>8}")
    print("-" * 50)
    for s in summaries:
        grad_str = f"{s['grad_r']:+.4f}" if s.get("grad_r") is not None else "   N/A"
        print(f"{s['seed']:>5}  {s['n_surv']:>5}  {s['start_cw']:>8.4f}  "
              f"{s['final_cw']:>8.4f}  {grad_str:>8}")

    final_cws = [s["final_cw"] for s in summaries]
    n_pos     = sum(1 for s in summaries if (s.get("grad_r") or 0) > 0)
    print("-" * 50)
    print(f"  Mean final care_weight : {_mean(final_cws):.4f} ± {_ci95(final_cws):.4f}")
    if grads:
        print(f"  Mean selection grad r  : {_mean(grads):+.4f}  "
              f"(Phase 5a: +0.079 | Phase 3: -0.178)")
        print(f"  Seeds positive         : {n_pos}/{len(summaries)}")

    if stat_result:
        print(f"\n=== Statistical Test (H0: r == 0) ===")
        print(f"  t={stat_result['ttest_t']:.4f}, p={stat_result['ttest_p']:.4f}")
        print(f"  Cohen's d = {stat_result['cohens_d']:.4f}")
        if stat_result.get("positive"):
            print("  Direction: POSITIVE — spatial structure alone may suffice (unexpected)")
        else:
            print("  Direction: FLAT or NEGATIVE — confirms infant dependency is necessary (expected)")

    print(f"\nOutput: {COMBINED_DIR}")


if __name__ == "__main__":
    run_all()
