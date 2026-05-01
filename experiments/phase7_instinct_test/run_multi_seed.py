# experiments/phase7_instinct_test/run_multi_seed.py
"""Phase 7 — Multi-seed orchestrator (10 seeds)

Runs Phase 7 zero-shot test for seeds 42-51.
Saves per-seed output dirs and a combined manifest for plotting.

*** UPDATE MLE_MULT in run.py before executing ***
"""
import sys
import os
import json
from concurrent.futures import ProcessPoolExecutor, as_completed

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from experiments.phase7_instinct_test.run import run_phase7, MLE_MULT, INIT_CARE, STAGE1_TICKS


def _run_seed_worker(packed):
    """Top-level picklable worker for ProcessPoolExecutor (Windows spawn-safe)."""
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

    entry_cw  = s1[-1]["avg_care_weight"]  if s1 else None
    final_cw  = s2[-1]["avg_care_weight"]  if s2 else None
    final_pop = s2[-1]["n_mothers"]         if s2 else 0
    final_lr  = s2[-1]["avg_learning_rate"] if s2 else None

    survived           = (final_pop or 0) >= 10
    instinct_confirmed = survived and (final_cw or 0) > INIT_CARE

    return {
        "seed": seed, "run_dir": rd,
        "survived": survived, "final_pop": final_pop,
        "entry_cw": entry_cw, "final_cw": final_cw,
        "final_lr": final_lr, "instinct_confirmed": instinct_confirmed,
    }

SEEDS        = list(range(42, 52))   # 42-51
COMBINED_DIR = os.path.join(PROJECT_ROOT, "outputs", "phase7_instinct_test", "multi_seed")


def _mean(vals):
    return sum(vals) / len(vals) if vals else float("nan")


def main(max_workers=None):
    os.makedirs(COMBINED_DIR, exist_ok=True)

    if max_workers is None:
        max_workers = min(len(SEEDS), os.cpu_count() or 4)

    print(f"\nPhase 7 - Zero-Shot Instinct Test ({len(SEEDS)} seeds)")
    print(f"  MLE ecology : mult={MLE_MULT}")
    print(f"  Stage 1     : ticks 0-{STAGE1_TICKS}  (plasticity ON)")
    print(f"  Stage 2     : ticks {STAGE1_TICKS}-{STAGE1_TICKS*2}  (plasticity OFF)")
    print(f"  Seeds       : {SEEDS}")
    print(f"  Workers     : {max_workers}  ({'parallel' if max_workers > 1 else 'sequential'})\n")

    run_dirs = {}
    results  = []

    if max_workers > 1:
        packed = [(s, PROJECT_ROOT) for s in SEEDS]
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_run_seed_worker, p): p[0] for p in packed}
            for fut in as_completed(futures):
                r = fut.result()
                run_dirs[r["seed"]] = r["run_dir"]
                results.append({k: v for k, v in r.items() if k != "run_dir"})
                print(f"  [done] seed={r['seed']}  survived={r['survived']}  "
                      f"instinct={r['instinct_confirmed']}")
        results.sort(key=lambda r: r["seed"])
    else:
        for seed in SEEDS:
            print(f"--- seed={seed} ---")
            rd = run_phase7(seed=seed)
            run_dirs[seed] = rd

            snap_path = os.path.join(rd, "generation_snapshots.json")
            if os.path.exists(snap_path):
                with open(snap_path) as f:
                    snaps = json.load(f)
                s1_snaps = [s for s in snaps if s["stage"] == 1]
                s2_snaps = [s for s in snaps if s["stage"] == 2]
                entry_cw  = s1_snaps[-1]["avg_care_weight"]  if s1_snaps else None
                final_cw  = s2_snaps[-1]["avg_care_weight"]  if s2_snaps else None
                final_pop = s2_snaps[-1]["n_mothers"]         if s2_snaps else 0
                final_lr  = s2_snaps[-1]["avg_learning_rate"] if s2_snaps else None
            else:
                entry_cw = final_cw = final_pop = final_lr = None

            survived           = (final_pop or 0) >= 10
            instinct_confirmed = survived and (final_cw or 0) > INIT_CARE

            results.append({
                "seed": seed, "survived": survived, "final_pop": final_pop,
                "entry_cw": entry_cw, "final_cw": final_cw,
                "final_lr": final_lr, "instinct_confirmed": instinct_confirmed,
            })
            print(f"  [checkpoint] seed={seed} saved.\n")

    # Save manifest
    manifest = {"seeds": SEEDS, "run_dirs": {str(s): d for s, d in run_dirs.items()}}
    with open(os.path.join(COMBINED_DIR, "run_dirs.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # Summary table
    print("\n=== Phase 7 Multi-Seed Summary ===")
    print(f" {'Seed':>5}  {'Surv':>5}  {'entry_cw':>9}  {'final_cw':>9}  {'final_lr':>9}  {'Instinct':>9}")
    print("-" * 60)
    for r in results:
        surv    = "YES" if r["survived"]           else "NO"
        inst    = "YES" if r["instinct_confirmed"]  else "NO"
        ecw     = f"{r['entry_cw']:.4f}" if r["entry_cw"] is not None else "N/A"
        fcw     = f"{r['final_cw']:.4f}" if r["final_cw"] is not None else "N/A"
        flr     = f"{r['final_lr']:.4f}" if r["final_lr"] is not None else "N/A"
        print(f"  {r['seed']:>4}  {surv:>5}  {ecw:>9}  {fcw:>9}  {flr:>9}  {inst:>9}")

    print("-" * 60)
    n_survived  = sum(1 for r in results if r["survived"])
    n_instinct  = sum(1 for r in results if r["instinct_confirmed"])
    print(f"  Survived         : {n_survived}/{len(SEEDS)} seeds")
    print(f"  Instinct confirmed : {n_instinct}/{len(SEEDS)} seeds")

    cw_vals = [r["final_cw"] for r in results if r["survived"] and r["final_cw"] is not None]
    lr_vals = [r["final_lr"] for r in results if r["survived"] and r["final_lr"] is not None]
    if cw_vals:
        print(f"  Mean final care_w  : {_mean(cw_vals):.4f}  (Phase 3 start: {INIT_CARE})")
    if lr_vals:
        print(f"  Mean final learn_r : {_mean(lr_vals):.4f}  (Genome start: 0.1000)")

    verdict = "BALDWIN EFFECT CONFIRMED" if n_instinct >= len(SEEDS) * 0.7 else "INCONCLUSIVE / FAILED"
    print(f"\n  Verdict: {verdict}")
    print(f"  (Threshold: >=70% seeds instinct_confirmed = care_weight > {INIT_CARE} AND survived Stage 2)\n")


if __name__ == "__main__":
    main(max_workers=None)  # None = auto-detect CPU count
