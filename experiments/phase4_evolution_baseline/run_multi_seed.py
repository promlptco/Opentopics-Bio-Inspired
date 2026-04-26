"""Phase 4: Evolution Baseline -- multi-seed runner (seeds 42-51).

Produces:
  - Per-seed generation_snapshots.json + birth_log.csv from run.py
  - Plot 1: care_weight trajectory  (per-seed lines + mean +/- SD band)
  - Plot 2: Pearson r distribution  (dot plot, mean marked, zero line)
  - Plot 3: Motivation weight trajectories  (care / forage / self -- hitchhiking check)
  - Plot 4: Intra-population variance of care_weight over time
  - Summary table: mean r, SD, n_negative_seeds, binomial p-value

Statistical reporting (per EXPERIMENT_DESIGN.md):
  Mean r +/- SD | n seeds with predicted sign (r < 0) | one-tailed binomial p
  Sufficiency threshold: 9/10 or 10/10 in predicted direction (p <= 0.05).
  8/10 is marginal -- flagged but not conclusive.

Output: outputs/phase4_evolution_baseline/multi_seed/
"""
import sys
import os
import json
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase4_evolution_baseline.run import (
    run as run_single,
    compute_selection_gradient,
    PHASE_NAME,
)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 10, "axes.titlesize": 10, "axes.labelsize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "legend.fontsize": 9, "legend.framealpha": 0.93, "legend.edgecolor": "0.6",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.8, "grid.alpha": 0.22, "grid.linewidth": 0.5,
        "lines.linewidth": 1.8, "figure.facecolor": "white", "axes.facecolor": "white",
    })
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("Warning: matplotlib not available -- plots will be skipped.")

SEEDS        = list(range(42, 52))
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", PHASE_NAME, "multi_seed")
CHECKPOINT   = os.path.join(COMBINED_DIR, "checkpoint.json")


# =============================================================================
# Helpers
# =============================================================================

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _sd(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (n - 1))


def _ci95(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    return 1.96 * _sd(values) / math.sqrt(n)


def _binom_p_k_or_more(n: int, k: int, p: float = 0.5) -> float:
    """One-tailed binomial P(X >= k | n, p)."""
    from math import comb
    return sum(comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


def _load_snapshots(run_dir: str) -> list[dict]:
    path = os.path.join(run_dir, "generation_snapshots.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {"completed": [], "run_dirs": {}, "gradients": {}, "summaries": []}


def _save_checkpoint(cp: dict) -> None:
    os.makedirs(COMBINED_DIR, exist_ok=True)
    with open(CHECKPOINT, "w") as f:
        json.dump(cp, f, indent=2)


# =============================================================================
# Plots
# =============================================================================

def _plot_care_weight_trajectory(
    all_snapshots: list[list[dict]],
    seeds: list[int],
    output_dir: str,
) -> None:
    if not HAS_MPL or not all_snapshots:
        return

    tick_sets    = [set(s["tick"] for s in snaps) for snaps in all_snapshots if snaps]
    common_ticks = sorted(set.intersection(*tick_sets)) if tick_sets else []
    if not common_ticks:
        return

    by_seed = [
        [next(s["avg_care_weight"] for s in snaps if s["tick"] == t) for t in common_ticks]
        for snaps in all_snapshots if snaps
    ]
    mean_cw = [_mean([s[i] for s in by_seed]) for i in range(len(common_ticks))]
    sd_cw   = [_sd([s[i] for s in by_seed])   for i in range(len(common_ticks))]
    lo_cw   = [m - sd for m, sd in zip(mean_cw, sd_cw)]
    hi_cw   = [m + sd for m, sd in zip(mean_cw, sd_cw)]

    by_seed_var = [
        [next((s.get("var_care_weight", 0.0) for s in snaps if s["tick"] == t), 0.0) for t in common_ticks]
        for snaps in all_snapshots if snaps
    ]
    mean_var = [_mean([s[i] for s in by_seed_var]) for i in range(len(common_ticks))]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.suptitle(
        f"Phase 4 Evolution Baseline -- care_weight trajectory\n"
        f"{len(seeds)} seeds | mult=1.0 | scatter=5 | init U(0,1) mean=0.50",
        fontsize=10,
    )

    # Individual seed traces (faint)
    for snaps in all_snapshots:
        if not snaps:
            continue
        t_i = [s["tick"]            for s in snaps]
        c_i = [s["avg_care_weight"] for s in snaps]
        ax1.plot(t_i, c_i, color="#1f77b4", alpha=0.12, linewidth=0.9)

    ax1.fill_between(common_ticks, lo_cw, hi_cw, alpha=0.20, color="#1f77b4")
    ax1.plot(common_ticks, mean_cw, color="#1f77b4", linewidth=2.2,
             label=f"Mean care_weight +/- SD  (n={len(seeds)} seeds)")
    ax1.axhline(0.5, color="gray", linestyle="--", linewidth=0.9, alpha=0.65,
                label="Init mean (0.50)")
    ax1.set_ylabel("Mean care_weight (genome)")
    ax1.set_ylim(0, 1)
    ax1.legend(loc="upper right", frameon=True)
    ax1.grid(True)

    ax2.plot(common_ticks, mean_var, color="#d62728", linewidth=2.0,
             label="Intra-population variance of care_weight (mean across seeds)")
    ax2.set_ylabel("Variance of care_weight")
    ax2.set_xlabel("Simulation tick")
    ax2.legend(loc="upper right", frameon=True)
    ax2.grid(True)

    fig.tight_layout()
    path = os.path.join(output_dir, "phase4_care_weight_trajectory.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def _plot_pearson_r_distribution(
    gradients: dict[str, float | None],
    seeds: list[int],
    output_dir: str,
) -> None:
    if not HAS_MPL:
        return

    valid = [(s, gradients.get(str(s))) for s in seeds if gradients.get(str(s)) is not None]
    if not valid:
        return

    sorted_seeds = [s for s, _ in sorted(valid, key=lambda x: x[0])]
    r_vals       = [r for _, r in sorted(valid, key=lambda x: x[0])]
    mean_r       = _mean(r_vals)

    colors = ["#d62728" if r >= 0 else "#2ca02c" for r in r_vals]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title(
        f"Phase 4 -- Pearson r distribution across {len(sorted_seeds)} seeds\n"
        f"Predicted direction: r < 0 (care erodes)  |  Mean r = {mean_r:+.4f}",
        fontsize=10,
    )
    ax.scatter(r_vals, list(range(len(sorted_seeds))),
               color=colors, s=80, zorder=5)
    ax.set_yticks(list(range(len(sorted_seeds))))
    ax.set_yticklabels([f"seed {s}" for s in sorted_seeds], fontsize=8)
    ax.axvline(0,      color="black", linewidth=1.0, linestyle="-",  alpha=0.5, label="r = 0")
    ax.axvline(mean_r, color="#1f77b4", linewidth=1.5, linestyle="--",
               label=f"Mean r = {mean_r:+.4f}")
    ax.set_xlabel("Pearson r  (care_weight vs generation)")
    ax.legend(loc="lower right", frameon=True)
    ax.grid(True, axis="x", alpha=0.3)
    # Annotate: green=negative (expected), red=positive (unexpected)
    ax.text(0.02, 0.97, "Green = r < 0 (expected erosion)\nRed = r > 0 (unexpected)",
            transform=ax.transAxes, fontsize=8, va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow",
                      edgecolor="0.65", linewidth=0.7))
    fig.tight_layout()
    path = os.path.join(output_dir, "phase4_pearson_r_distribution.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def _plot_motivation_weights(
    all_snapshots: list[list[dict]],
    seeds: list[int],
    output_dir: str,
) -> None:
    if not HAS_MPL or not all_snapshots:
        return

    tick_sets    = [set(s["tick"] for s in snaps) for snaps in all_snapshots if snaps]
    common_ticks = sorted(set.intersection(*tick_sets)) if tick_sets else []
    if not common_ticks:
        return

    def _extract(key: str) -> tuple[list, list]:
        by_seed = [
            [next(s.get(key, 0.5) for s in snaps if s["tick"] == t) for t in common_ticks]
            for snaps in all_snapshots if snaps
        ]
        return (
            [_mean([s[i] for s in by_seed]) for i in range(len(common_ticks))],
            [_sd([s[i] for s in by_seed])   for i in range(len(common_ticks))],
        )

    care_m,   care_sd   = _extract("avg_care_weight")
    forage_m, forage_sd = _extract("avg_forage_weight")
    self_m,   self_sd   = _extract("avg_self_weight")

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    fig.suptitle(
        "Phase 4 -- All motivation weights over time (hitchhiking check)\n"
        f"{len(seeds)} seeds | expected: care erodes, forage/self stable",
        fontsize=10,
    )

    for ax, mean_w, sd_w, label, color in [
        (axes[0], care_m,   care_sd,   "care_weight",   "#1f77b4"),
        (axes[1], forage_m, forage_sd, "forage_weight", "#d95f02"),
        (axes[2], self_m,   self_sd,   "self_weight",   "#2ca02c"),
    ]:
        lo = [m - s for m, s in zip(mean_w, sd_w)]
        hi = [m + s for m, s in zip(mean_w, sd_w)]
        ax.fill_between(common_ticks, lo, hi, alpha=0.20, color=color)
        ax.plot(common_ticks, mean_w, color=color, linewidth=2.0,
                label=f"{label} mean +/- SD")
        ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6,
                   label="Init mean (0.50)")
        ax.set_ylabel(label)
        ax.set_ylim(0, 1)
        ax.legend(loc="upper right", frameon=True, fontsize=8)
        ax.grid(True)

    axes[2].set_xlabel("Simulation tick")
    fig.tight_layout()
    path = os.path.join(output_dir, "phase4_motivation_weights.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =============================================================================
# Main
# =============================================================================

def run_all(seeds: list[int] = SEEDS) -> None:
    os.makedirs(COMBINED_DIR, exist_ok=True)

    cp         = _load_checkpoint()
    done       = set(cp["completed"])
    run_dirs   = dict(cp["run_dirs"])
    gradients  = dict(cp["gradients"])
    summaries  = list(cp["summaries"])

    print(f"Phase 4 multi-seed: {len(seeds)} seeds {seeds}")
    if done:
        print(f"  [checkpoint] Already done: {sorted(done)}")
    print()

    for seed in seeds:
        if seed in done:
            print(f"  [checkpoint] seed={seed} already done, skipping.")
            continue

        print(f"--- seed={seed} ---")
        run_dir  = run_single(seed=seed)
        grad     = compute_selection_gradient(os.path.join(run_dir, "birth_log.csv"))

        snaps    = _load_snapshots(run_dir)
        start_cw = snaps[0]["avg_care_weight"] if snaps else 0.5
        final_cw = snaps[-1]["avg_care_weight"] if snaps else 0.0
        max_gen  = snaps[-1].get("max_generation", 0) if snaps else 0

        run_dirs[str(seed)]  = run_dir
        gradients[str(seed)] = grad
        summaries.append({
            "seed":           seed,
            "run_dir":        run_dir,
            "start_cw":       start_cw,
            "final_cw":       final_cw,
            "max_generation": max_gen,
            "gradient_r":     grad,
        })
        cp["completed"]  = list(done | {seed})
        cp["run_dirs"]   = run_dirs
        cp["gradients"]  = gradients
        cp["summaries"]  = summaries
        done.add(seed)
        _save_checkpoint(cp)
        grad_str = f"{grad:+.4f}" if grad is not None else "N/A"
        print(f"  [checkpoint] seed={seed} saved.  gradient_r={grad_str}\n")

    # ── Statistical analysis ───────────────────────────────────────────────────
    valid_grads = [v for v in gradients.values() if v is not None]
    n           = len(valid_grads)
    n_negative  = sum(1 for r in valid_grads if r < 0)
    n_positive  = sum(1 for r in valid_grads if r > 0)
    mean_r      = _mean(valid_grads)
    sd_r        = _sd(valid_grads)

    # One-tailed binomial: P(X >= n_negative | n, 0.5)  [predicted direction = negative]
    binom_p_neg = _binom_p_k_or_more(n, n_negative) if n > 0 else 1.0
    # Also report positive for transparency
    binom_p_pos = _binom_p_k_or_more(n, n_positive) if n > 0 else 1.0

    stat_results = {
        "n_seeds":          n,
        "mean_r":           round(mean_r, 6),
        "sd_r":             round(sd_r, 6),
        "n_negative_seeds": n_negative,
        "n_positive_seeds": n_positive,
        "binom_p_negative": round(binom_p_neg, 6),
        "binom_p_positive": round(binom_p_pos, 6),
        "predicted_direction": "r < 0 (care erodes)",
        "interpretation": (
            "EROSION CONFIRMED (p<=0.05)"   if binom_p_neg <= 0.05 and mean_r < 0 else
            "MARGINAL EROSION (flag 8/10)"  if n_negative == 8 else
            "NEUTRAL (r~0)"                 if abs(mean_r) < 0.02 else
            "UNEXPECTED POSITIVE (STOP)"    if mean_r > 0 else
            "MIXED -- inspect per-seed"
        ),
    }

    # ── Save outputs ──────────────────────────────────────────────────────────
    with open(os.path.join(COMBINED_DIR, "run_dirs.json"), "w") as f:
        json.dump({"seeds": seeds, "run_dirs": run_dirs}, f, indent=2)
    with open(os.path.join(COMBINED_DIR, "summary.json"), "w") as f:
        json.dump(summaries, f, indent=2)
    with open(os.path.join(COMBINED_DIR, "statistical_results.json"), "w") as f:
        json.dump(stat_results, f, indent=2)

    # ── Plots ─────────────────────────────────────────────────────────────────
    valid_seeds = [s for s in seeds if str(s) in run_dirs]
    all_snaps   = [_load_snapshots(run_dirs[str(s)]) for s in valid_seeds]

    _plot_care_weight_trajectory(all_snaps, valid_seeds, COMBINED_DIR)
    _plot_pearson_r_distribution(gradients, valid_seeds, COMBINED_DIR)
    _plot_motivation_weights(all_snaps, valid_seeds, COMBINED_DIR)

    # ── Console summary ───────────────────────────────────────────────────────
    print("\n=== Phase 4 Evolution Baseline -- Multi-Seed Summary ===")
    print(f"  {'Seed':>5}  {'Start_cw':>9}  {'Final_cw':>9}  {'Max_gen':>8}  {'r':>8}")
    print("  " + "-" * 50)
    for s in summaries:
        g = s.get("gradient_r")
        g_str = f"{g:+.4f}" if g is not None else "   N/A"
        print(f"  {s['seed']:>5}  {s['start_cw']:>9.4f}  {s['final_cw']:>9.4f}  "
              f"{s['max_generation']:>8}  {g_str:>8}")
    print("  " + "-" * 50)
    print(f"  Mean r         : {mean_r:+.4f}  (SD={sd_r:.4f})")
    print(f"  Seeds r < 0    : {n_negative}/{n}")
    print(f"  Seeds r > 0    : {n_positive}/{n}")
    print(f"  Binomial p (r<0): {binom_p_neg:.4f}")
    print(f"  Binomial p (r>0): {binom_p_pos:.4f}")
    print(f"\n  Interpretation : {stat_results['interpretation']}")

    print("\n=== Interpretation Gates (EXPERIMENT_DESIGN.md, Phase 4) ===")
    if mean_r < -0.02 and n_negative >= 9:
        print("  => r < 0, >=9/10 seeds negative: CARE ERODES. Proceed to Phase 5.")
    elif mean_r > 0.02:
        print("  => r > 0 (UNEXPECTED): STOP. Re-examine parameters before proceeding.")
        print("     Do not proceed to Phase 5 without understanding this result.")
    else:
        print("  => r ~= 0 (neutral): selectively invisible. Treat as weak erosion. Note and proceed.")

    print(f"\nCombined output: {COMBINED_DIR}")


if __name__ == "__main__":
    run_all()
