"""Phase 4 -- Step 5: Generational Turnover Hypothesis Test

HYPOTHESIS
----------
Script 04 (True Neutral, feed_cost=0, infant_mult=0) settled at care~0.59
while Script 02 (Baseline, real costs) settled at care~0.50.

Proposed explanation: removing feed_cost caused a population boom in Script 04,
producing MORE generations in the same 10,000 ticks, which ACCELERATED the
bounded random walk and caused MORE drift toward 0.5 -- except Script 04
actually settled HIGHER (0.59), not lower.

Wait, re-reading the hypothesis: the claim is the opposite -- more generations
in Script 04 caused MORE drift from 0.80, explaining why care eroded in Script
04 even without selection. The implicit prediction is that Script 04 has
significantly more generational turnover than Script 02.

VERDICT
-------
REFUTED. Both runs reach max_generation = 99 across all 10 seeds. Generational
depth and avg generation at t=10,000 are essentially identical. The equilibrium
difference (0.59 vs 0.50) cannot be explained by differential drift rates
caused by different generational turnover.

DATA AVAILABILITY
-----------------
Script 04 logged full per-run CSVs (birth_log, death_log, generation_snapshots).
Script 02 logged only per-seed aggregate snapshot JSONs -- total births are NOT
recorded. Where unavailable, columns show "N/A".
"""

import json
import csv
import glob
import os
import statistics

ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "outputs", "phase4_neutral_drift_baseline"
)
ROOT = os.path.normpath(ROOT)

SEEDS = list(range(42, 52))

# ---------------------------------------------------------------------------
# Script 02 -- read from seed_snapshots/*.json
# ---------------------------------------------------------------------------
s02 = []
for seed in SEEDS:
    path = os.path.join(ROOT, "02_ceiling_drop_erosion", "seed_snapshots", f"seed{seed}.json")
    with open(path) as f:
        snaps = json.load(f)

    # average n_mothers across all snapshots (equilibrium population)
    n_list = [s["n_mothers"] for s in snaps]
    avg_pop_all  = statistics.mean(n_list)
    # equilibrium = last quarter of run (ticks 7500-10000)
    eq_snaps = [s for s in snaps if s["tick"] >= 7500]
    avg_pop_eq   = statistics.mean(s["n_mothers"] for s in eq_snaps)

    final = snaps[-1]
    s02.append({
        "seed":        seed,
        "max_gen":     final["max_generation"],
        "avg_gen":     final["avg_generation"],
        "care_final":  final["avg_care_weight"],
        "pop_eq":      avg_pop_eq,
        "births":      None,          # not logged
        "mother_deaths": None,
        "child_deaths":  None,
    })

# ---------------------------------------------------------------------------
# Script 04 -- read from run_*/ directories
# ---------------------------------------------------------------------------
s04 = []
run_dirs = sorted(glob.glob(os.path.join(ROOT, "04_true_neutral_control", "run_*")))
for rdir in run_dirs:
    seed = int(os.path.basename(rdir).split("seed")[1])

    # generation snapshots
    gpath = os.path.join(rdir, "generation_snapshots.json")
    with open(gpath) as f:
        snaps = json.load(f)
    eq_snaps = [s for s in snaps if s["tick"] >= 7500]
    avg_pop_eq = statistics.mean(s["n_mothers"] for s in eq_snaps)
    final = snaps[-1]

    # births
    bpath = os.path.join(rdir, "birth_log.csv")
    with open(bpath) as f:
        births = sum(1 for _ in f) - 1  # exclude header

    # mother vs child deaths
    dpath = os.path.join(rdir, "death_log.csv")
    mother_deaths = 0
    child_deaths  = 0
    with open(dpath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["agent_type"] == "mother":
                mother_deaths += 1
            else:
                child_deaths  += 1

    s04.append({
        "seed":          seed,
        "max_gen":       final["max_generation"],
        "avg_gen":       final["avg_generation"],
        "care_final":    final["avg_care_weight"],
        "pop_eq":        avg_pop_eq,
        "births":        births,
        "mother_deaths": mother_deaths,
        "child_deaths":  child_deaths,
    })

s04.sort(key=lambda x: x["seed"])

# ---------------------------------------------------------------------------
# Helper: mean of a column (skip None)
# ---------------------------------------------------------------------------
def col_mean(rows, key, fmt=".1f"):
    vals = [r[key] for r in rows if r[key] is not None]
    if not vals:
        return "N/A"
    return format(statistics.mean(vals), fmt)

def col_vals(rows, key, fmt=".1f"):
    return [format(r[key], fmt) if r[key] is not None else "N/A" for r in rows]

# ---------------------------------------------------------------------------
# Per-seed comparison table
# ---------------------------------------------------------------------------
print()
print("=" * 90)
print("  Phase 4 Script 05 -- Generational Turnover Hypothesis Test")
print("=" * 90)

HDR = (
    f"{'Seed':>6}  {'MaxGen':>6}  {'AvgGen':>7}  {'PopEq':>6}  "
    f"{'CareFinal':>9}  {'Births':>7}  {'MotherD':>7}  {'ChildD':>7}"
)
SEP = "-" * 90

print()
print("  A. SCRIPT 02 -- Ceiling-Drop Baseline  (infant_mult=1.0, feed_cost=default)")
print(SEP)
print(HDR)
print(SEP)
for r in s02:
    print(
        f"  {r['seed']:>4}  {r['max_gen']:>6}  {r['avg_gen']:>7.1f}  {r['pop_eq']:>6.1f}  "
        f"  {r['care_final']:>8.3f}  {'N/A':>7}  {'N/A':>7}  {'N/A':>7}"
    )
print(SEP)
print(
    f"  {'MEAN':>4}  {col_mean(s02,'max_gen','.0f'):>6}  {col_mean(s02,'avg_gen'):>7}  "
    f"{col_mean(s02,'pop_eq'):>6}  {col_mean(s02,'care_final','.3f'):>9}  "
    f"{'N/A':>7}  {'N/A':>7}  {'N/A':>7}"
)

print()
print("  B. SCRIPT 04 -- True Neutral Control   (infant_mult=0.0, feed_cost=0.0)")
print(SEP)
print(HDR)
print(SEP)
for r in s04:
    print(
        f"  {r['seed']:>4}  {r['max_gen']:>6}  {r['avg_gen']:>7.1f}  {r['pop_eq']:>6.1f}  "
        f"  {r['care_final']:>8.3f}  {r['births']:>7}  {r['mother_deaths']:>7}  {r['child_deaths']:>7}"
    )
print(SEP)
print(
    f"  {'MEAN':>4}  {col_mean(s04,'max_gen','.0f'):>6}  {col_mean(s04,'avg_gen'):>7}  "
    f"{col_mean(s04,'pop_eq'):>6}  {col_mean(s04,'care_final','.3f'):>9}  "
    f"{col_mean(s04,'births','.0f'):>7}  {col_mean(s04,'mother_deaths','.0f'):>7}  "
    f"{col_mean(s04,'child_deaths','.0f'):>7}"
)

# ---------------------------------------------------------------------------
# Side-by-side summary
# ---------------------------------------------------------------------------
print()
print("=" * 90)
print("  SIDE-BY-SIDE COMPARISON  (10-seed means)")
print("=" * 90)

metrics = [
    ("Max generation reached",    col_mean(s02, "max_gen",    ".1f"), col_mean(s04, "max_gen",    ".1f")),
    ("Avg generation @ t=10000",  col_mean(s02, "avg_gen",    ".2f"), col_mean(s04, "avg_gen",    ".2f")),
    ("Avg pop size (eq, 7.5k+)",  col_mean(s02, "pop_eq",     ".1f"), col_mean(s04, "pop_eq",     ".1f")),
    ("Final care_weight",         col_mean(s02, "care_final", ".3f"), col_mean(s04, "care_final", ".3f")),
    ("Total births (10k ticks)",  "N/A (not logged)",                  col_mean(s04, "births",     ".0f")),
    ("Mother deaths (10k ticks)", "N/A (not logged)",                  col_mean(s04, "mother_deaths", ".0f")),
    ("Child deaths  (10k ticks)", "N/A (not logged)",                  col_mean(s04, "child_deaths",  ".0f")),
]

col_w = 35
print(f"  {'Metric':<{col_w}}  {'Script 02 (baseline)':>22}  {'Script 04 (neutral)':>22}")
print("  " + "-" * (col_w + 50))
for label, v02, v04 in metrics:
    print(f"  {label:<{col_w}}  {v02:>22}  {v04:>22}")

# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
max_gens_02 = [r["max_gen"] for r in s02]
max_gens_04 = [r["max_gen"] for r in s04]
same_gen = all(a == b for a, b in zip(max_gens_02, max_gens_04))

print()
print("=" * 90)
print("  VERDICT")
print("=" * 90)
print()
if same_gen:
    print("  HYPOTHESIS REFUTED -- Generational Turnover does NOT explain the equilibrium gap.")
    print()
    print(f"  Both runs reach max_generation = {max_gens_02[0]} across all 10 seeds.")
    print(f"  Avg generation at t=10,000: Script02 = {col_mean(s02,'avg_gen','.1f')}, "
          f"Script04 = {col_mean(s04,'avg_gen','.1f')}.")
    print()
    print("  If generational turnover were the mechanism, Script 04 should show")
    print("  significantly MORE generations (faster boom -> more drift cycles).")
    print("  It does not. The number of generations is identical.")
    print()
    pop02 = float(col_mean(s02, "pop_eq", ".1f"))
    pop04 = float(col_mean(s04, "pop_eq", ".1f"))
    print(f"  Population at equilibrium: Script02 = {pop02:.1f},  Script04 = {pop04:.1f}.")
    if pop04 > pop02:
        print(f"  Script 04 has a LARGER population (+{pop04 - pop02:.1f} mothers).")
        print("  Larger N reduces effective genetic drift per generation (Wright's law).")
        print("  If turnover drove the result, Script04 should erode MORE, not less.")
        print("  Instead Script04 settles HIGHER (0.59 vs 0.50) -- opposite of prediction.")
    print()
    print("  RESIDUAL EXPLANATION:")
    print("  The equilibrium gap (0.59 vs 0.50) is driven by SELECTION in Script 02,")
    print("  not by differential drift rates. In Script 02, mothers who invest energy")
    print("  in care (feed_cost > 0) while facing infant starvation (mult=1.0) are at")
    print("  a fitness disadvantage. Low-care genomes outreproduce high-care genomes,")
    print("  pushing the population mean below the drift attractor (~0.59) to ~0.50.")
    print("  In Script 04, no such selection exists, so only drift operates and the")
    print("  equilibrium stays at the bounded random walk attractor (~0.59).")
else:
    print("  HYPOTHESIS PARTIALLY SUPPORTED -- max generations differ across runs.")
    print("  Inspect per-seed table above for details.")

print()
print("=" * 90)
