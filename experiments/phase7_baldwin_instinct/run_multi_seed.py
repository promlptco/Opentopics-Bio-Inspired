# experiments/p6_controls_and_baldwin/p6d_baldwin_instinct/run_multi_seed.py
"""Phase 11: Baldwin Effect — Instinct Assimilation — multi-seed runner (seeds 42–51).

Runs both Stage 1 (evolution) and Stage 2 (instinct) for 10 seeds and reports:
  - Per-seed instinct pass/fail across all four criteria
  - Overall pass rate (≥ 8/10 → "maternal care instinct demonstrated")
  - Concatenated 0 → 20 000 t care_weight trajectory (green=plasticity ON, grey=OFF)

Output: outputs/phase11_instinct_assimilation/multi_seed_evolution/
"""
import sys
import os
import json
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase7_baldwin_instinct.run import (
    run_evolution,
    run_instinct,
    PHASE_NAME,
)

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
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

SEEDS        = list(range(42, 52))
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", PHASE_NAME, "multi_seed_evolution")
CHECKPOINT   = os.path.join(COMBINED_DIR, "checkpoint.json")

PASS_THRESHOLD = 8   # seeds that must pass instinct criteria


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
    var  = sum((x - mean) ** 2 for x in values) / (n - 1)
    return 1.96 * math.sqrt(var / n)


def _load_snapshots(run_dir: str) -> list:
    path = os.path.join(run_dir, "generation_snapshots.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _load_instinct_metrics(run_dir: str) -> dict:
    path = os.path.join(run_dir, "instinct_metrics.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def _load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {
        "completed_evo":      [],
        "completed_instinct": [],
        "evo_dirs":           {},
        "instinct_dirs":      {},
        "summaries":          [],
    }


def _save_checkpoint(cp: dict) -> None:
    os.makedirs(COMBINED_DIR, exist_ok=True)
    with open(CHECKPOINT, "w") as f:
        json.dump(cp, f, indent=2)


# =============================================================================
# Plot
# =============================================================================

def plot_concatenated(all_evo_snaps, all_inst_snaps, seeds, summaries, output_dir: str):
    """Concatenated 0–20 000 t plot: green=plasticity ON, grey=instinct."""
    if not HAS_MPL:
        return
    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 5))
    n_pass = sum(1 for s in summaries if s.get("instinct_passed"))
    fig.suptitle(
        f"Phase 11: Baldwin Effect — Instinct Assimilation ({len(seeds)} seeds)\n"
        f"Instinct passed: {n_pass}/{len(summaries)} seeds  "
        f"({'DEMONSTRATED' if n_pass >= PASS_THRESHOLD else 'NOT demonstrated'}, "
        f"threshold={PASS_THRESHOLD})",
        fontsize=10,
    )

    # Individual seed traces — Stage 1 (green) and Stage 2 (grey)
    for snaps_evo, snaps_inst in zip(all_evo_snaps, all_inst_snaps):
        if snaps_evo:
            t_e = [s["tick"] for s in snaps_evo]
            c_e = [s["avg_care_weight"] for s in snaps_evo]
            ax.plot(t_e, c_e, color="#2ca02c", alpha=0.12, linewidth=0.9)
        if snaps_inst:
            t_i = [s["tick"] for s in snaps_inst]
            c_i = [s["avg_care_weight"] for s in snaps_inst]
            ax.plot(t_i, c_i, color="#7f7f7f", alpha=0.12, linewidth=0.9)

    # Mean ± CI for Stage 1
    def _mean_ci_traces(all_snaps):
        all_ticks  = sorted({s["tick"] for snaps in all_snaps for s in snaps})
        by_seed    = [[next((s["avg_care_weight"] for s in snaps if s["tick"] == t), None)
                       for t in all_ticks] for snaps in all_snaps]
        mean_vals  = []
        ci_vals    = []
        valid_t    = []
        for i, t in enumerate(all_ticks):
            vals = [bs[i] for bs in by_seed if bs[i] is not None]
            if vals:
                mean_vals.append(_mean(vals))
                ci_vals.append(_ci95(vals))
                valid_t.append(t)
        return valid_t, mean_vals, ci_vals

    valid_evo  = [s for s in all_evo_snaps  if s]
    valid_inst = [s for s in all_inst_snaps if s]

    if valid_evo:
        t_e, m_e, ci_e = _mean_ci_traces(valid_evo)
        lo_e = [m - c for m, c in zip(m_e, ci_e)]
        hi_e = [m + c for m, c in zip(m_e, ci_e)]
        ax.fill_between(t_e, lo_e, hi_e, alpha=0.18, color="#2ca02c")
        ax.plot(t_e, m_e, color="#2ca02c", linewidth=2.2,
                label=f"Stage 1 — plasticity ON (mean ± 95% CI, n={len(valid_evo)})")

    if valid_inst:
        t_i, m_i, ci_i = _mean_ci_traces(valid_inst)
        lo_i = [m - c for m, c in zip(m_i, ci_i)]
        hi_i = [m + c for m, c in zip(m_i, ci_i)]
        ax.fill_between(t_i, lo_i, hi_i, alpha=0.18, color="#7f7f7f")
        ax.plot(t_i, m_i, color="#7f7f7f", linewidth=2.2,
                label=f"Stage 2 — instinct test plast=OFF (mean ± 95% CI, n={len(valid_inst)})")

    ax.axvline(10_000, color="black", linestyle="--", linewidth=0.9, alpha=0.7,
               label="Plasticity removed (t=10 000)")
    ax.axhline(0.25,   color="gray",  linestyle=":",  linewidth=0.8, alpha=0.6,
               label="Depleted init mean (0.25)")

    ax.set_xlabel("Simulation tick  (0–10 000 = plasticity ON,  10 001–20 000 = instinct test)")
    ax.set_ylabel("Mean care_weight")
    ax.set_ylim(0, 0.85)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True)

    fig.tight_layout()
    path = os.path.join(output_dir, "multi_seed_instinct_assimilation.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =============================================================================
# Main
# =============================================================================

def run_all(seeds=SEEDS):
    os.makedirs(COMBINED_DIR, exist_ok=True)

    cp          = _load_checkpoint()
    done_evo    = set(cp["completed_evo"])
    done_inst   = set(cp["completed_instinct"])
    evo_dirs    = dict(cp["evo_dirs"])
    inst_dirs   = dict(cp["instinct_dirs"])
    summaries   = list(cp["summaries"])

    print(f"Phase 11 multi-seed: {len(seeds)} seeds {seeds}")
    if done_evo:
        print(f"  [checkpoint] Evolution done: {sorted(done_evo)}")
    if done_inst:
        print(f"  [checkpoint] Instinct done: {sorted(done_inst)}")
    print()

    # ── Stage 1: evolution ────────────────────────────────────────────────────
    for seed in seeds:
        if seed in done_evo:
            print(f"  [checkpoint] seed={seed} evolution already done, skipping.")
            continue
        print(f"--- seed={seed} Stage 1 (evolution) ---")
        evo_dir = run_evolution(seed=seed)
        evo_dirs[str(seed)] = evo_dir
        cp["completed_evo"].append(seed)
        cp["evo_dirs"] = evo_dirs
        _save_checkpoint(cp)
        print(f"  [checkpoint] seed={seed} evolution saved.\n")

    # ── Stage 2: instinct ─────────────────────────────────────────────────────
    for seed in seeds:
        if seed in done_inst:
            print(f"  [checkpoint] seed={seed} instinct already done, skipping.")
            continue
        if str(seed) not in evo_dirs:
            print(f"  [WARN] seed={seed}: no evolution dir found — skipping instinct.")
            continue
        print(f"--- seed={seed} Stage 2 (instinct) ---")
        inst_dir = run_instinct(seed=seed, source_dir=evo_dirs[str(seed)])
        inst_dirs[str(seed)] = inst_dir
        cp["completed_instinct"].append(seed)
        cp["instinct_dirs"] = inst_dirs
        _save_checkpoint(cp)
        print(f"  [checkpoint] seed={seed} instinct saved.\n")

    # ── Aggregate summaries ───────────────────────────────────────────────────
    summaries = []
    for seed in seeds:
        row = {"seed": seed}
        evo_snaps = _load_snapshots(evo_dirs.get(str(seed), ""))
        row["evo_final_cw"] = evo_snaps[-1]["avg_care_weight"] if evo_snaps else None
        inst_m = _load_instinct_metrics(inst_dirs.get(str(seed), ""))
        row["instinct_passed"] = inst_m.get("instinct_passed")
        row["cw_start"] = inst_m.get("cw_start")
        row["cw_end"]   = inst_m.get("cw_end")
        crit = inst_m.get("criteria", {})
        row["c1_drift"]    = crit.get("c1_cw_drift_ok")
        row["c2_care"]     = crit.get("c2_care_rate_ok")
        row["c3_child"]    = crit.get("c3_child_energy_ok")
        row["c4_infant"]   = crit.get("c4_infant_pop_stable")
        summaries.append(row)

    with open(os.path.join(COMBINED_DIR, "summary.json"), "w") as f:
        json.dump(summaries, f, indent=2)

    # ── Summary table ─────────────────────────────────────────────────────────
    n_pass = sum(1 for s in summaries if s.get("instinct_passed") is True)
    print("\n=== Phase 11 Instinct Assimilation — Summary ===")
    print(f"{'Seed':>5}  {'EvoCW':>6}  {'CW_s':>6}  {'CW_e':>6}  "
          f"{'C1':>3}  {'C2':>3}  {'C3':>3}  {'C4':>3}  {'PASS':>5}")
    print("-" * 60)
    for s in summaries:
        def _b(v): return "Y" if v is True else ("N" if v is False else "?")
        print(f"{s['seed']:>5}  "
              f"{(s['evo_final_cw'] or 0):>6.3f}  "
              f"{(s['cw_start'] or 0):>6.3f}  "
              f"{(s['cw_end'] or 0):>6.3f}  "
              f"{_b(s['c1_drift']):>3}  {_b(s['c2_care']):>3}  "
              f"{_b(s['c3_child']):>3}  {_b(s['c4_infant']):>3}  "
              f"{'PASS' if s.get('instinct_passed') else 'FAIL':>5}")
    print("-" * 60)
    print(f"  Seeds passed: {n_pass}/{len(summaries)}  "
          f"(threshold={PASS_THRESHOLD}/10)")
    if n_pass >= PASS_THRESHOLD:
        print("  → RESULT: Maternal care instinct DEMONSTRATED (Baldwin assimilation)")
    else:
        print("  → RESULT: Instinct NOT demonstrated (plasticity removed → care collapses)")
    print(f"\nOutput: {COMBINED_DIR}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    all_evo_snaps  = [_load_snapshots(evo_dirs.get(str(s), ""))  for s in seeds]
    all_inst_snaps = [_load_snapshots(inst_dirs.get(str(s), "")) for s in seeds]
    plot_concatenated(all_evo_snaps, all_inst_snaps, seeds, summaries, COMBINED_DIR)


if __name__ == "__main__":
    run_all()
