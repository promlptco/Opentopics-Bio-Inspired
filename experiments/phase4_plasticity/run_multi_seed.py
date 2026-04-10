# experiments/phase4_plasticity/run_multi_seed.py
"""
Run Phase 4b (kin-conditional Baldwin Effect) across 10 seeds and produce:
  - Per-seed full outputs (generation_snapshots, top_genomes, logs, plots)
  - Per-seed zero-shot transfer (zeroshot_plastic_kin stage)
  - Multi-seed CI plots: care_weight + learning_rate + forage over 5000 ticks
  - Summary table: final care_weight, learning_rate, forage per seed
  - Multi-seed zero-shot bar chart vs Phase 2 baseline

Key questions:
  - Is the care_weight trough + recovery robust (>= 7/10 seeds)?
  - Is the learning_rate late sweep (0.1 -> 0.17) consistent across seeds?
  - Is the +9.5% zero-shot window rate improvement reproducible?
"""
import sys
import os
import json
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase4_plasticity.run import run
from utils.plotting import plot_start_vs_end_multiseed

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

SEEDS = list(range(42, 52))   # seeds 42-51 (10 runs, matches Phase 3)
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase4_plasticity", "multi_seed_evolution")
PHASE2_WINDOW_BASELINE = 0.09069   # Phase 2 zero-shot care-window rate (actual, ticks 0-100)


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


def _ci95(values: list[float]) -> float:
    """95% CI half-width assuming normal distribution."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return 1.96 * math.sqrt(variance / n)


# =============================================================================
# Multi-seed CI plot (3 panels: care_weight, learning_rate, forage)
# =============================================================================

def plot_multi_seed_ci(
    all_snapshots: list[list[dict]],
    seeds: list[int],
    output_dir: str,
) -> None:
    """
    3-panel CI plot:
      Panel 1 — care_weight mean +/- 95% CI (is recovery robust?)
      Panel 2 — learning_rate mean +/- 95% CI (is late sweep consistent?)
      Panel 3 — forage_weight mean (hitchhiking check — should stay flat)
    """
    if plt is None or not all_snapshots:
        return

    os.makedirs(output_dir, exist_ok=True)

    tick_sets = [set(s["tick"] for s in snaps) for snaps in all_snapshots]
    common_ticks = sorted(set.intersection(*tick_sets))
    if not common_ticks:
        print("No common ticks across seeds — skipping CI plot.")
        return

    def get_series(snaps: list[dict], key: str) -> dict:
        return {s["tick"]: s.get(key, 0.0) for s in snaps}

    care_by_seed   = [get_series(s, "avg_care_weight")   for s in all_snapshots]
    lr_by_seed     = [get_series(s, "avg_learning_rate") for s in all_snapshots]
    forage_by_seed = [get_series(s, "avg_forage_weight") for s in all_snapshots]

    care_mean, care_ci = [], []
    lr_mean, lr_ci     = [], []
    forage_mean        = []

    for t in common_ticks:
        c_vals = [d[t] for d in care_by_seed]
        l_vals = [d[t] for d in lr_by_seed]
        f_vals = [d[t] for d in forage_by_seed]
        care_mean.append(sum(c_vals) / len(c_vals));   care_ci.append(_ci95(c_vals))
        lr_mean.append(sum(l_vals) / len(l_vals));     lr_ci.append(_ci95(l_vals))
        forage_mean.append(sum(f_vals) / len(f_vals))

    care_lo = [m - ci for m, ci in zip(care_mean, care_ci)]
    care_hi = [m + ci for m, ci in zip(care_mean, care_ci)]
    lr_lo   = [m - ci for m, ci in zip(lr_mean, lr_ci)]
    lr_hi   = [m + ci for m, ci in zip(lr_mean, lr_ci)]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(
        f"Phase 4b (Kin-Conditional Plasticity) — {len(seeds)} Seeds, Evolution over 5000 Ticks\n"
        "Baldwin Effect: is care_weight recovery + learning_rate sweep robust across seeds?",
        fontsize=10,
    )

    # ── Panel 1: care_weight ──
    for snaps in all_snapshots:
        ticks_i = [s["tick"] for s in snaps if s["tick"] in set(common_ticks)]
        care_i  = [get_series(snaps, "avg_care_weight")[t] for t in ticks_i]
        ax1.plot(ticks_i, care_i, color="seagreen", alpha=0.15, linewidth=1)
    ax1.plot(common_ticks, care_mean, color="seagreen", linewidth=2.5,
             label=f"mean care_weight (n={len(seeds)})")
    ax1.fill_between(common_ticks, care_lo, care_hi, alpha=0.3, color="seagreen",
                     label="95% CI")
    ax1.axhline(0.500, color="gray",    linestyle="--", linewidth=1.0, label="Gen 0 start (0.500)")
    ax1.axhline(0.365, color="crimson", linestyle=":",  linewidth=1.2, label="R0 survivors (0.365)")
    ax1.set_ylabel("care_weight")
    ax1.set_ylim(0, 1)
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(True, alpha=0.25)

    # ── Panel 2: learning_rate ──
    for snaps in all_snapshots:
        ticks_i = [s["tick"] for s in snaps if s["tick"] in set(common_ticks)]
        lr_i    = [get_series(snaps, "avg_learning_rate")[t] for t in ticks_i]
        ax2.plot(ticks_i, lr_i, color="mediumpurple", alpha=0.15, linewidth=1)
    ax2.plot(common_ticks, lr_mean, color="mediumpurple", linewidth=2.5,
             label=f"mean learning_rate (n={len(seeds)})")
    ax2.fill_between(common_ticks, lr_lo, lr_hi, alpha=0.3, color="mediumpurple",
                     label="95% CI")
    ax2.axhline(0.100, color="gray", linestyle="--", linewidth=1.0,
                label="Gen 0 start (0.100)")
    ax2.set_ylabel("learning_rate")
    ax2.set_ylim(0, 0.5)
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, alpha=0.25)

    # ── Panel 3: forage (hitchhiking check) ──
    ax3.plot(common_ticks, forage_mean, color="darkorange", linewidth=2.5,
             label="mean forage_weight")
    ax3.axhline(0.500, color="gray", linestyle="--", linewidth=1.0,
                label="Gen 0 start (0.500)")
    ax3.set_xlabel("Tick  (approx. 1 generation per 100 ticks)")
    ax3.set_ylabel("forage_weight")
    ax3.set_ylim(0, 1)
    ax3.legend(loc="upper left", fontsize=8)
    ax3.grid(True, alpha=0.25)

    plt.tight_layout()
    path = os.path.join(output_dir, "multi_seed_care_weight_ci.png")
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"  Saved: {path}")


# =============================================================================
# Zero-shot multi-seed bar chart
# =============================================================================

def plot_zeroshot_multiseed(
    zs_summaries: list[dict],
    output_dir: str,
) -> None:
    """Per-seed bar chart of zero-shot care-window rate vs Phase 2 baseline."""
    if plt is None or not zs_summaries:
        return

    os.makedirs(os.path.join(output_dir, "plots"), exist_ok=True)

    seeds  = [s["seed"] for s in zs_summaries]
    rates  = [s["window_rate"] for s in zs_summaries]
    colors = ["seagreen" if r >= PHASE2_WINDOW_BASELINE else "coral" for r in rates]
    mean_r = sum(rates) / len(rates)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar([str(s) for s in seeds], rates, color=colors,
                  edgecolor="white", linewidth=1.2)
    ax.axhline(PHASE2_WINDOW_BASELINE, color="steelblue", linestyle="--", linewidth=1.5,
               label=f"Phase 2 baseline ({PHASE2_WINDOW_BASELINE:.5f})")
    ax.axhline(mean_r, color="black", linestyle="-", linewidth=1.2,
               label=f"Phase 4b mean ({mean_r:.5f})")

    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, rate + 0.001,
                f"{rate:.4f}", ha="center", va="bottom", fontsize=8)

    n_above = sum(1 for r in rates if r >= PHASE2_WINDOW_BASELINE)
    ax.set_xlabel("Seed")
    ax.set_ylabel("Care / mother-tick (ticks 0-100)")
    ax.set_title(
        f"Phase 4b Zero-Shot Care-Window Rate vs Phase 2 Baseline — {len(seeds)} Seeds\n"
        f"Green = above baseline ({n_above}/{len(seeds)} seeds improved)",
    )
    ax.legend(fontsize=9)
    ax.set_ylim(0, max(rates) * 1.2)
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "zeroshot_multiseed.png")
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"  Saved: {path}")


# =============================================================================
# Main runner
# =============================================================================

def run_all(seeds: list[int] = SEEDS) -> None:
    os.makedirs(COMBINED_DIR, exist_ok=True)

    evo_run_dirs  = []
    all_snapshots = []
    evo_summaries = []
    zs_run_dirs   = []
    zs_summaries  = []

    print(f"Phase 4b multi-seed: {len(seeds)} seeds {seeds}\n")

    # ── Evolution pass ─────────────────────────────────────────────────────
    for seed in seeds:
        print(f"--- [evolution] seed={seed} ---")
        evo_dir = run(seed=seed, stage="evolution_plastic_kin")
        evo_run_dirs.append(evo_dir)

        snaps = _load_snapshots(evo_dir)
        all_snapshots.append(snaps)

        top_path = os.path.join(evo_dir, "top_genomes.json")
        if os.path.exists(top_path):
            with open(top_path) as f:
                genomes = json.load(f)
            cw   = [g["care_weight"]   for g in genomes]
            fw   = [g["forage_weight"] for g in genomes]
            lr   = [g["learning_rate"] for g in genomes]
            lc   = [g["learning_cost"] for g in genomes]
            gens = [g.get("generation", 0) for g in genomes]
            evo_summaries.append({
                "seed":                    seed,
                "n_survivors":             len(genomes),
                "final_care_mean":         sum(cw) / len(cw)   if cw else 0,
                "final_forage_mean":       sum(fw) / len(fw)   if fw else 0,
                "final_learning_rate_mean":sum(lr) / len(lr)   if lr else 0,
                "final_learning_cost_mean":sum(lc) / len(lc)   if lc else 0,
                "max_generation":          max(gens)            if gens else 0,
            })
        print()

    # ── Zero-shot pass ────────────────────────────────────────────────────
    print("=" * 50)
    print("Starting zero-shot pass...")
    print("=" * 50 + "\n")

    for seed, evo_dir in zip(seeds, evo_run_dirs):
        print(f"--- [zeroshot] seed={seed} ---")
        zs_dir = run(seed=seed, stage="zeroshot_plastic_kin", source_dir=evo_dir)
        zs_run_dirs.append(zs_dir)

        m = _load_zeroshot_metrics(zs_dir)
        window = m.get("care_window", {})
        zs_summaries.append({
            "seed":        seed,
            "window_rate": window.get("care_per_mother_tick_in_window", 0.0),
            "window_care": window.get("care_events_in_window", 0),
            "last_alive":  m.get("last_alive_tick", 0),
        })
        print()

    # ── Save manifests ────────────────────────────────────────────────────
    with open(os.path.join(COMBINED_DIR, "run_dirs.json"), "w") as f:
        json.dump({"seeds": seeds, "evo_run_dirs": evo_run_dirs,
                   "zs_run_dirs": zs_run_dirs}, f, indent=2)
    with open(os.path.join(COMBINED_DIR, "summary.json"), "w") as f:
        json.dump(evo_summaries, f, indent=2)
    with open(os.path.join(COMBINED_DIR, "zeroshot_summary.json"), "w") as f:
        json.dump(zs_summaries, f, indent=2)

    # ── Plots ─────────────────────────────────────────────────────────────
    plot_multi_seed_ci(all_snapshots, seeds, COMBINED_DIR)
    plot_start_vs_end_multiseed(evo_summaries, COMBINED_DIR)
    plot_zeroshot_multiseed(zs_summaries, COMBINED_DIR)

    # ── Summary table ─────────────────────────────────────────────────────
    print("\n=== Phase 4b Multi-Seed Evolution Summary ===")
    print(f"{'Seed':>5}  {'Surv':>5}  {'care_w':>7}  {'forage':>7}  {'lr':>7}  {'max_gen':>7}")
    print("-" * 50)
    for s in evo_summaries:
        print(f"{s['seed']:>5}  {s['n_survivors']:>5}  "
              f"{s['final_care_mean']:>7.4f}  {s['final_forage_mean']:>7.4f}  "
              f"{s['final_learning_rate_mean']:>7.4f}  {s['max_generation']:>7}")

    care_finals = [s["final_care_mean"] for s in evo_summaries]
    lr_finals   = [s["final_learning_rate_mean"] for s in evo_summaries]
    print("-" * 50)
    print(f"  Mean care_weight : {sum(care_finals)/len(care_finals):.4f}"
          f"  +/- {_ci95(care_finals):.4f} (95% CI)")
    print(f"  Mean learn_rate  : {sum(lr_finals)/len(lr_finals):.4f}"
          f"  +/- {_ci95(lr_finals):.4f} (95% CI)")

    print("\n=== Phase 4b Zero-Shot Window Rate ===")
    print(f"{'Seed':>5}  {'window_rate':>12}  {'vs baseline':>12}  {'last_alive':>10}")
    print("-" * 47)
    for s in zs_summaries:
        delta = s["window_rate"] - PHASE2_WINDOW_BASELINE
        pct   = delta / PHASE2_WINDOW_BASELINE * 100
        print(f"{s['seed']:>5}  {s['window_rate']:>12.5f}  "
              f"{pct:>+11.1f}%  {s['last_alive']:>10}")
    wrates = [s["window_rate"] for s in zs_summaries]
    print("-" * 47)
    print(f"  Mean window rate : {sum(wrates)/len(wrates):.5f}"
          f"  +/- {_ci95(wrates):.5f} (95% CI)")
    print(f"  Phase 2 baseline : {PHASE2_WINDOW_BASELINE:.5f}")
    n_above = sum(1 for r in wrates if r >= PHASE2_WINDOW_BASELINE)
    print(f"  Seeds above baseline: {n_above}/{len(wrates)}")
    print(f"\nCombined output: {COMBINED_DIR}")


if __name__ == "__main__":
    run_all()
