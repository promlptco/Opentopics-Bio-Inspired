# Current State

Last updated: 2026-05-11 (V3 branch)

> ⚠ **COLLABORATOR NOTE: IF YOU DON'T KNOW, JUST ASK — NO GUESSING.**
> Do not fill in unknown values, infer undocumented behavior, or assume parameter names.
> Read the actual source files before writing anything.

---

## ✅ STATUS — Phase 5 core implementation active

**Decision:** Phase 1–4 re-runs remain skipped due to time constraints. The current
work focus is Phase 5 asynchronous evolution under the locked Phase 4b ecology.

**Ecology baseline:** Phase 4b BEST_CALIBRATED
(`outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json`).

**Mechanism configuration:** Ecological mechanisms remain available in the engine,
but the default Phase 5 configuration still keeps the Block 1/2 baseline stance of
no explicit caregiving bias.

**Current implementation milestone (2026-05-11):** the Baldwin mechanism is now a
**motivation-vector local search**, not a care-only scalar update.

---

## Phase 5 Current State (active)

### What is implemented now

1. **Global search remains genetic and intergenerational**
   - Inherited genes still mutate in [`evolution/genome.py`](./evolution/genome.py):
     `care_weight`, `forage_weight`, `self_weight`, `learning_rate`,
     `plasticity_coefficient`.
   - Genome weights are renormalized after mutation so the motivation genome remains
     a simplex.

2. **Local search is now phenotype-vector based**
   - [`MotherAgent`](./agents/mother.py) now carries:
     - `expressed_care_weight`
     - `expressed_forage_weight`
     - `expressed_self_weight`
   - These are renormalized to sum to 1.0 after every local update.
   - Action selection in `compute_motivation_scores()` now uses the **expressed**
     vector for CARE / FORAGE / SELF, instead of only care being phenotypic.

3. **Domain-aware plasticity is active**
   - Local updates are now domain-specific:
     - CARE updates when caregiving succeeds or clearly fails
     - FORAGE updates on food acquisition / weak failure penalties
     - SELF updates on eating/rest success
   - The local learner therefore adapts the current behavioral allocation, not just
     caregiving intensity.

4. **Plasticity cost now has two live components**
   - **Update cost:** charged when a plasticity update occurs.
   - **Maintenance cost:** charged every tick as
     `plasticity_maintenance_beta * plasticity_coefficient` when plasticity is enabled.
   - `lifetime_learning_cost` now reflects the total metabolic burden of being plastic
     across the mother's life.

5. **Lifecycle export and cohort plotting are active**
   - Phase 5 runs now write:
     - `snapshots.csv`
     - `mother_lifecycle.csv`
     - `child_lifecycle.csv`
     - `summary.json`
   - The cohort plotter now supports the Baldwin-aligned families:
     - reproductive success
     - offspring maturation fraction
     - plasticity reliance / vector drift
     - learning cost
     - child nRMST / TTD
     - mother nRMST / TTD
     - optional genome-care support

### What changed conceptually

The local search is no longer “care-only learning.” It is now:

- **global search** in genotype space
- **local search** in expressed motivation space

This is a stronger Baldwin interpretation because the phenotype can now redistribute
behavioral effort across care, forage, and self within a lifetime.

### What is still intentionally *not* implemented

1. **No local search over all genes**
   - Only the expressed motivation phenotype is locally updated.
   - Deep genotype parameters are still global-search only.

2. **No Lamarckian inheritance of learned phenotype**
   - `phenotype_retention` remains present in configuration / runner plumbing, but it is
     still not used to directly seed offspring phenotype from parental learned state.
   - This is intentional for the current Baldwin interpretation.

3. **No explicit time-cost variable for learning**
   - Time cost remains indirect through TTD / nRMST and cohort viability.
   - The live explicit cost is metabolic / energetic.

### Active analysis semantics

- `genome_behavior_distance` in snapshots is now the **total-variation distance**
  between the genome motivation simplex and the expressed motivation simplex.
- `plasticity_drift` in cohort plots now uses the same vector notion whenever the full
  lifecycle columns are present.
- `c_matr_cum` / `child_survival_rate` in `snapshots.csv` remain exploratory-only and
  survivor-biased.

### Verification completed after the update

- `python -m py_compile agents\\mother.py simulation\\simulation.py experiments\\phase5_evolution\\run.py experiments\\phase5_evolution\\plot.py experiments\\phase1_mechanics_tests\\test_07_engine_fixes.py`
  passed.
- `python experiments\\phase1_mechanics_tests\\test_07_engine_fixes.py`
  passed with added vector-plasticity and maintenance-cost checks.
- Smoke outputs created successfully:
  - `outputs/phase5_evolution/exp_20260511_211342/`
  - `outputs/phase5_evolution/exp_20260511_211418/`

### Historical sections below

The remainder of this file preserves the earlier Phase 2–4 record. Those sections are
historical context; the status above is the current Phase 5 truth.

---

## Phase 2 Current State (PENDING RE-RUN)

Last updated: 2026-05-05 (V3 branch)

---

## What Phase 2 Is

Mother-only ecological survival baseline. No children, no care, no reproduction, no mutation, no plasticity.

Goal: find three canonical ecological parameter sets (HARSH / BALANCED / EASY) that produce distinct survival pressures. These become the starting conditions for Phase 3 evolution.

Motivations active: FORAGE, SELF  
Actions active: MOVE, PICK, EAT, REST

---

## Key Files (V3)

| File | Role |
|------|------|
| `experiments/phase2_survival_minimal/new_run.py` | Main entry point; 8-step pipeline, sweep, and single modes |
| `experiments/phase2_survival_minimal/new_config.py` | Sweep grid, selection targets, BALANCED_BASELINE, SENSITIVITY_SWEEPS |
| `experiments/phase2_survival_minimal/new_plot.py` | All plot functions — academic style, distinct colour palette |
| `experiments/phase2_survival_minimal/new_sensitivity.py` | OVAT standalone runner + find_food_anchor (user-owned) |
| `agents/mother.py` | MotherAgent with `choose_motivation()` |
| `config.py` (root) | Global defaults |

---

## Fixed Parameters (new_config.py — BALANCED_BASELINE)

| Parameter | Value | Reason |
|-----------|-------|--------|
| `hunger_rate` | 1/35 ≈ 0.0286 | Adult starves in 35 ticks = 7 days |
| `perception_radius` | 15.0 | 30% of 50×50 map |
| `move_cost` | 0.005 | OVAT Set C lever (0.01 produced poor BALANCED/EASY separation) |
| `eat_gain` | 0.20 | OVAT Set B lever |
| `rest_recovery` | 0.005 | OVAT Set E lever |
| `fatigue_rate` | 0.01 | Root config default |
| `init_food` | 80 | OVAT Set A anchor |
| `init_mothers` | 15 | Matches all phases |
| `initial_energy` | 1.0 | Full energy at birth |
| Grid | 50×50 | Standard Phase 2+ |

---

## BALANCED_BASELINE ecology

With `move_cost=0.005, eat_gain=0.20`. Baseline `move_cost` was lowered from 0.01 after empirical tests showed 0.01 produced poor BALANCED/EASY ecological separation in survival curves.

---

## SENSITIVITY_SWEEPS (new_config.py)

⚠ Set D added 2026-05-09 — sweep code extension pending.

| Set | Key | Values |
|-----|-----|--------|
| A | `init_food` | 10, 20, 40, 80, 150 |
| B | `eat_gain` | 0.05, 0.10, 0.20, 0.50, 0.80 |
| C | `move_cost` | 0.005, 0.01, 0.02, 0.05, 0.10 |
| D | `food_entropy_alpha` | TBD — calibrate via sweep (0.0 = disabled baseline) |

---

## SELECTION_TARGETS (new_config.py)

| Condition | Survival range |
|-----------|---------------|
| HARSH | 10% – 45% |
| BALANCED | 50% – 75% |
| EASY | > 80% |

---

## 8-Step Pipeline (ROADMAPS.md)

```
python -m experiments.phase2_survival_minimal.new_run --mode pipeline --duration 1000 --workers 4
```

| Step | Description | Status |
|------|-------------|--------|
| 1 | Mechanics lock (1:1 food replacement, pop-weighted energy) | Done |
| 2 | Provisional baseline (BALANCED_BASELINE synthetic config) | Done |
| 3 | Food anchor scan (find_food_anchor) | User-owned fix in progress |
| 4 | OVAT sweep (Sets A / B / C, 5 values each) | Done |
| 5 | Zone classification (DEAD / HARSH / BALANCED / EASY per param) | Fixed (Bug 2) |
| 6 | Full init_food × eat_gain × move_cost grid (5×5×5 = 125 configs) | Fixed (Bug 3) |
| 7 | Regime selection (HARSH / BALANCED / EASY candidate pick) | Pending Step 3 fix |
| 8 | Final diagnostic plots | Ready (see Plot Refinements below) |

---

## Bugs Fixed This Session (V3)

### Bug 2 — `_detect_cliff_edge_from_ovat` dead threshold logic
- **Was**: `surv_lo=0.80, surv_hi=0.95` — unreachable given max survival ≈ 31%; logic always fell back to max-gradient
- **Fix**: Replaced with ROADMAPS.md zone classification (DEAD / HARSH / BALANCED / EASY); picks value closest to BALANCED target

### Bug 3 — `_pipeline_multidim_configs` not building 3-parameter grid
- **Was**: Only varied `init_food`; all CLEAR params → single-axis sweep
- **Fix**: Replaced with full Cartesian product of SENSITIVITY_SWEEPS A × B × C = 5×5×5 = 125 configs per ROADMAPS.md Step 6

### Bug 1 — `find_food_anchor` wrong fallback (user-owned)
- **Was**: Returns `food_max` (595) on fallback; should return `argmax` (~food=190)
- **Status**: User is fixing this independently; do not touch `new_sensitivity.py`

---

## Plot Refinements (new_plot.py) — Completed 2026-05-05

### Mandatory Fix
- `config_title()`: `hunger_rate` now formatted as `:.4f` → displays `0.0286` in all validation plot subtitles

### Global Academic Style
- `matplotlib.rcParams` block applied at import time: sans-serif font, tick direction `"in"`, consistent size hierarchy (title 12 pt, axis label 11 pt, tick 9 pt), white figure background
- `style_axes()`: white axes face, inward ticks, font sizes 11/12

### Distinct Colour Palette

| Element | Colour | Hex |
|---------|--------|-----|
| MOVE | Steel blue | `#1f77b4` |
| PICK | Golden orange | `#e6902a` |
| EAT | Forest green | `#2a9a3c` |
| REST | Brick red | `#c7443a` |
| FORAGE | Burnt orange | `#d45b13` |
| SELF | Purple | `#7b4ea0` |
| FAILED_FORAGE | Mid grey | `#888888` |
| FAILED_SELF | Dark grey | `#333333` |
| Energy (validation) | Steel blue | `#1f77b4` |
| Population (validation) | Muted blue | `#1f77b4` |
| Energy trajectory | Forest green | `#2ca02c` |

### Label Improvements
- All suptitles use `|` separator on a single line; `"n = X runs"` notation
- All axis labels include context or units (`"Simulation tick"`, `"Population-weighted mean energy"`, etc.)
- Subplot titles describe shading meaning (e.g., `"green = group mean ± 1 SD"`)
- Validation plot: long config_title rendered as monospace subtitle via `fig.text()` separate from main suptitle

---

## Commands

```bash
# Full 8-step pipeline
python -m experiments.phase2_survival_minimal.new_run --mode pipeline --duration 1000 --workers 4

# OVAT sweep only (Steps 1-2, 6-8)
python -m experiments.phase2_survival_minimal.new_run --mode sweep --duration 1000 --workers 4

# Single config validation (Steps 1-2, 8)
python -m experiments.phase2_survival_minimal.new_run --mode single --duration 1000
```

---

## Phase 3 Ecological Baselines (LOCKED)

Source: `outputs/phase2_survival_minimal/pin_auto_400_percept15_repeat3_validation_selected_baselines/selected_ecologies.json`  
Validation seeds: 42–51 (N=10), duration=1000 ticks, perception_radius=15, tau=0.1

### Shared fixed parameters (all three conditions)

| Parameter | Value |
|-----------|-------|
| `perception_radius` | 15.0 |
| `hunger_rate` | 1/35 ≈ 0.02857 |
| `rest_recovery` | 0.005 |
| `care_weight` | 0.0 |
| `forage_weight` | 1.0 |
| `self_weight` | 1.0 |

### Selected ecological regimes

| Condition | `move_cost` | `eat_gain` | `init_food` | Survival rate | Final pop (mean) | Tail energy (mean) |
|-----------|-------------|------------|-------------|---------------|------------------|--------------------|
| **HARSH** | 0.05 | 0.8 | 80 | **24.7%** (3.7 / 15) | 3.7 ± 1.84 | 0.215 ± 0.076 |
| **BALANCED** | 0.01 | 0.5 | 40 | **62.4%** (9.36 / 15) | 9.36 ± 1.83 | 0.379 ± 0.070 |
| **EASY** | 0.005 | 0.5 | 80 | **91.6%** (13.74 / 15) | 13.74 ± 1.31 | 0.507 ± 0.039 |

### Ecological gradient validation

- Monotonic survival: HARSH < BALANCED < EASY ✓
- Monotonic tail energy: HARSH < BALANCED < EASY ✓
- All within SELECTION_TARGETS bounds ✓
- Population SD decreases from HARSH → EASY (EASY is most stable) ✓

### HARSH regime notes

`move_cost=0.05` is the primary driver (movement is expensive enough to trigger fatigue cascade).  
`eat_gain=0.8` is high, so surviving agents eat well — death comes from movement exhaustion, not starvation.  
REST rate is lowest of all three (2.3%) confirming the fatigue cascade mechanism.

### BALANCED regime notes

`init_food=40` (food-scarce) forces FAILED_FORAGE events, driving occasional SELF switching.  
REST rate is highest (7.1%) — agents manage fatigue more actively in this regime.

### EASY regime notes

`move_cost=0.005` (cheap movement) and `init_food=80` allow near-full population survival.  
Near-zero tail energy slope (−0.00012) confirms stable steady state.

---

## Branch / Git

Branch: `V3`

---

---

# Phase 3 Current State

Last updated: 2026-05-08 (V3 branch)

---

## Status: RESTRUCTURED — awaiting Block 1 confirmation run

Phase 3 was restructured to match Phase 2's OVAT 8-step pipeline exactly.
New files created in `experiments/phase3_survival_full/` (top-level, not sub-folders).
Phase 3 has NOT been re-run yet with the new pipeline — pending Block 1 confirmation run.

### Research Question
"What ecological conditions (init_food × eat_gain × move_cost) allow mother-child pairs
to coexist, given unbiased motivation weights (1/1/1)?"

---

## What Changed (vs old phase3_sweep / phase3b_calibration)

| Old | New |
|-----|-----|
| Only swept `init_food` (1D) | Sweeps `init_food × eat_gain × move_cost` (3D, same axes as Phase 2) |
| Swept `ISM` — a biological constant | ISM **locked at 35/15 ≈ 2.33** (not swept) |
| No HARSH/BALANCED/EASY selection | Same regime selection criteria as Phase 2 + Option C child gate |
| Different plot style | Same academic plot style as Phase 2 + 4-row OVAT map |
| Different pipeline structure | Identical 8-step pipeline to Phase 2 |

Old sub-folders (`phase3_sweep/`, `phase3b_calibration/`) kept as archives, not entry points.

---

## Key Files (new — entry points)

| File | Role |
|------|------|
| `experiments/phase3_survival_full/config.py` | ISM=2.33 locked, unbiased weights 1/1/1, OVAT axes, Option C child targets, Phase 2 anchor loader |
| `experiments/phase3_survival_full/run.py` | `Phase3Simulation` wrapper + full 8-step pipeline; 3 modes: pipeline/sweep/single |
| `experiments/phase3_survival_full/plot.py` | 4-panel condition overview, motivation split bar, 4-row × 3-col OVAT sensitivity map |

---

## Fixed Parameters

| Parameter | Value | Note |
|-----------|-------|------|
| `ISM` (infant_starvation_multiplier) | 35/15 ≈ 2.33 | biological constant — locked, NOT swept |
| `maturity_age` | 200 | ticks to reach maturity (5 ticks/day × 40 days) |
| `max_ticks` | 400 | 5 ticks/day × 80 days |
| `init_mothers` | 15 | same as Phase 2 |
| `care_weight` | 1.0 | unbiased — all motivations equal |
| `forage_weight` | 1.0 | |
| `self_weight` | 1.0 | |
| `children_enabled` | True | 15 mother-child pairs at t=0 |
| `care_enabled` | True | |
| `reproduction_enabled` | False | ecology calibration only |
| `perception_radius` | 8 | matches Phase 2 anchor |

---

## OVAT Sweep Axes (same as Phase 2, extended init_food range + 3 new axes)

⚠ Sets D/E/F added 2026-05-09 — sweep code extension pending.
Phase 3 uses Phase 2 best result as provisional baseline (Step 1), then re-sweeps all 6 axes.

| Set | Key | Values |
|-----|-----|--------|
| A | `init_food` | 40, 100, 200, 400, 700, 1000, 1500 |
| B | `eat_gain` | 0.10, 0.20, 0.30, 0.50, 0.70 |
| C | `move_cost` | 0.005, 0.01, 0.02, 0.05, 0.10 |
| D | `food_entropy_alpha` | TBD — same values locked in Phase 2 (0.0 = disabled baseline) |
| E | `temperature_sensitivity` | TBD — calibrate via sweep (0.0 = disabled baseline; children only) |
| F | `cry_decay_radius` | TBD — calibrate via sweep (0.0 = global cry baseline) |

Note: `init_food` range extended vs Phase 2 because 15 children add indirect resource pressure on mothers.

---

## Selection Criteria

### Mother criteria (identical to Phase 2)

| Condition | Survival range |
|-----------|---------------|
| HARSH | 10% – 45% |
| BALANCED | 50% – 75% |
| EASY | > 80% |

### Child criteria — Option C (dual metric, user-approved 2026-05-08)

| Condition | C_matr | child_death_mu |
|-----------|--------|----------------|
| HARSH | no constraint | no constraint |
| BALANCED | > 0.0 (any maturation counts) | ≥ 50 ticks |
| EASY | ≥ 0.10 | ≥ 120 ticks |

---

## Phase 2 Anchor (auto-loaded)

Loads BALANCED ecology from `outputs/phase2_survival_minimal/auto_400_percept8/selected_ecologies.json`.
Falls back to `{move_cost:0.01, eat_gain:0.20, init_food:40, rest_recovery:0.005}` if absent.

---

## Run Command

```bash
python -m experiments.phase3_survival_full.run --mode pipeline --workers 4
```

---

## Validation

- Syntax: 3/3 files pass `py_compile.compile()` ✓
- Import: all modules import cleanly ✓
- Functional (100-tick smoke test): Phase3Simulation ran; final_pop=1, C_matr=0.0, child_death_mu=18.8, care_pct=60%, child_population_history populated ✓

---

## Next: Run Phase 1–3 for Block 1 confirmation

---

---

# Phase 3b Current State

Last updated: 2026-05-07 (V3 branch)

---

## Status: CONCLUDED — CHILD_SURVIVAL_POSSIBLE = False

Phase 3b answers: "Can ecologically plausible parameters, with unbiased motivation weights (all = 1.0), produce child maturation (reach tick 200)?"

**Answer: NO.** Full 3D grid sweep (ISM × eat_gain × init_food, 64 combos × 5 seeds = 320 runs) produced C_matr = 0.0 across all combinations. This is not a bug — it is the mechanistic care trap, derived directly from the unbiased softmax dynamics.

---

## Parameters Swept

| Axis | Values | Justification |
|------|--------|---------------|
| `infant_starvation_multiplier` (ISM) | [1.2, 1.5, 2.0, 2.33] | Key child vulnerability parameter — never swept in Phase 3 |
| `eat_gain` | [0.20, 0.30, 0.50, 0.70] | Energy per feed |
| `init_food` | [100, 300, 600, 900] | Food density → forage cycle speed |

**Fixed (all Phase 3b runs):**
`care_weight = forage_weight = self_weight = 1.0` (unbiased), `warmth_factor = 0.0`, `move_cost = 0.005`, `rest_recovery = 0.005`, `hunger_rate = 1/35`, `maturity_age = 200`, `max_ticks = 400`, `init_mothers = 15`

---

## BEST_ECOLOGICAL Regime (highest child_death_mu — children lived longest)

| Parameter | Value |
|-----------|-------|
| `infant_starvation_multiplier` | 1.2 |
| `eat_gain` | 0.70 |
| `init_food` | 600 |
| `c_matr` | 0.000 |
| `m_surv` | 0.133 |
| `child_death_mu` | 48.3 ticks |

Saved to: `outputs/phase3b_calibration/selected_ecologies.json`

---

## OVAT Sensitivity Results (5 seeds each)

### Set A — ISM sweep (eat_gain=0.30, init_food=400)

| ISM | M_surv | C_matr | child_death_mu |
|-----|--------|--------|----------------|
| 1.0 | 0.053 | 0.000 | 47.7 |
| 1.5 | 0.173 | 0.000 | 34.2 |
| 2.0 | 0.240 | 0.000 | 26.2 |
| 2.33 | 0.413 | 0.000 | 21.5 |
| 2.5 | 0.427 | 0.000 | 20.1 |

ISM paradox: higher ISM kills children faster, ending the care trap sooner → mothers survive better. Lower ISM lets children live longer in the care trap → mothers starve.

### ISM Comparison — Confound Warning (Approach C)

The Phase 3b OVAT table above used **fixed ecology** (eat_gain=0.30, init_food=400, move_cost=0.005) across all ISM values. That is a controlled ISM comparison.

The earlier Phase 3 full-ecology sweeps (outputs/phase3_survival_full/auto_400_percept8_ism1/ and auto_400_percept8_ism2.33/) swept ecology parameters **independently per ISM**. The selected "easy" ecologies from those runs have very different energy acquisition:

| ISM | eat_gain | init_food | move_cost |
| --- | --- | --- | --- |
| 1.0 (Phase 3 easy) | 0.20 | 1500 | 0.005 |
| 2.33 (Phase 3 easy) | 0.70 | 1500 | 0.010 |

The optimizer compensated for higher ISM difficulty by selecting richer ecology (3.5× higher eat_gain). Any validation plot comparison between those two ISM runs reflects ISM + ecology combined, not ISM alone.

**Write-up framing:** Treat each Phase 3 ISM × ecology run as an independent **existence proof** that the care trap emerges under those combined conditions. Do not present them as a direct ISM comparison. For controlled ISM effects, cite Phase 3b OVAT (above) or Phase 4 ISM sweeps (both control ecology).

---

## Why Child Maturation Is Impossible with Weights = 1.0 — The Care Trap

With `tau = 0.1` (near-deterministic softmax) and all weights = 1.0:

```
forage_cue = 1 - dist_to_food / perception_radius
```

At init_food=600 (24% grid coverage), forage_cue ≈ 0.86 dominates SELF and CARE.

CARE only wins softmax when `child.distress > forage_cue ≈ 0.86`, meaning the child has ~14% energy remaining — approximately 4 ticks before starvation.

By that point:
1. Mother commits to CARE and navigates to child.
2. She arrives with held_food = 0 (has not foraged recently — FORAGE only fires when distress < 0.86).
3. `feed_child()` fails (held_food ≤ 0 guard). Commitment releases.
4. Next tick: child distress > 0.86 again → CARE wins → mother navigates again → loop.
5. Child starves. Mother resumes normal foraging.

**Feeds needed formula:**
```
feeds_needed = (200 × hunger_rate × ISM - 1.0) / eat_gain
             = (5.714 × ISM - 1.0) / eat_gain
```

| ISM | eat_gain | feeds_needed | Best observed feeds/child |
|-----|----------|-------------|--------------------------|
| 1.2 | 0.70 | 8.4 | ~1.9 (from grid data) |
| 1.5 | 0.30 | 25.2 | ~1.8 |
| 2.33 | 0.20 | 61.6 | — (mathematically impossible) |

Even at the best ecological combo (ISM=1.2, eat_gain=0.70), observed feeds/child ≈ 1.9 vs 8.4 needed. Gap remains ~4.4×.

**Root cause**: FORAGE must precede CARE (mother must pick food before she can deliver it). With unbiased weights, FORAGE and CARE compete as equals. CARE fires too late (child at 14% energy) and mother arrives empty. The sequential dependency (FORAGE → CARE) is broken by simultaneous competition.

---

## Key Files

| File | Role |
|------|------|
| `experiments/phase3b_calibration/config.py` | ISM/eat_gain/init_food sweep grid, PHASE3B_FLAGS, feeds_needed formula |
| `experiments/phase3b_calibration/run.py` | 8-step pipeline: anchor, OVAT, grid, regime selection |
| `experiments/phase3b_calibration/plot.py` | 5-figure evidence suite (OVAT sensitivity, action dist, heatmap, validation, care trap) |

---

## Phase 3b Conclusion

Ecological parameter tuning alone (ISM, eat_gain, init_food) cannot rescue child maturation when motivation weights are unbiased. The care trap is a structural consequence of the softmax + cue system with equal weights, not an artefact of any single parameter. This confirms:

1. The simulation mechanics are correct.
2. Motivational bias is the necessary and sufficient change to enable child maturation.
3. Phase 4 must sweep `care_weight` to establish the minimum bias needed.

---

## Next: Phase 4 — Motivation Weight Sweep (care_weight bias)

---

---

# Phase 4 Current State

Last updated: 2026-05-10 (V3 branch)

---

## Status: CONCLUDED — ISM sweep complete; Block 2 baseline locked

Phase 4 answers: "What is the minimum care_weight bias that enables child maturation, and how does the Infant Starvation Multiplier (ISM) gate feasibility?"

**Three ISM sweeps run** (25 weight combos × 10 seeds × 3 repeats = 750 runs each):

| Sweep folder | ISM | Best C_matr | Best weights | Mean C_matr (all combos) |
| --- | --- | --- | --- | --- |
| `sweep_ism1` | **1.0** | **0.360** | care=0.5, forage=2.0 | 0.067 |
| `sweep_ism1p2` | 1.2 | 0.327 | care=0.5, forage=2.0 | 0.060 |
| `sweep_ism2p33` | 2.33 | 0.009 | care=0.5, forage=2.0 | 0.001 |

ISM=2.33: child maturation effectively impossible across all 25 weight combos (original care trap null result).  
ISM=1.0 and 1.2: maturation viable — same OPTIMAL weight combo wins both.

---

## ISM vs Child Survival Analysis

Plot: `outputs/phase4_weight_sweep/ism_vs_child_survival.png`  
Script: `experiments/phase4_weight_sweep/plot_ism_vs_child_survival.py`

Two-panel figure:

- **(A)** Line plot — max and mean C_matr vs ISM. Clear monotonic collapse: ISM acts as ecological gatekeeper.
- **(B)** Box plot — full distribution of C_matr across all 25 weight combos per ISM. ISM=2.33 compressed at zero; ISM=1.0 and 1.2 have viable tails above the 0.10 viability threshold.

**Key finding:** ISM is the primary feasibility gate. Above ISM≈1.5, no weight combination can rescue child maturation. ISM=1.0 selected for Block 2 as the most permissive ecology.

---

## Ecological Baseline Used in Phase 4 Sweeps

Phase 4 used the **hardcoded Phase 3b BEST_ECOLOGICAL** fallback (no Phase 3b JSON found):

| Parameter | Value |
| --- | --- |
| `infant_starvation_multiplier` | varies per sweep (1.0 / 1.2 / 2.33) |
| `eat_gain` | 0.70 |
| `init_food` | 600 |
| `move_cost` | 0.005 |
| `rest_recovery` | 0.005 |
| `hunger_rate` | 1/35 ≈ 0.02857 |
| `food_perception_radius` | 8 |
| `perception_radius` | 8 |
| `maturity_age` | 200 |
| `max_ticks` | 400 |
| `init_mothers` | 15 |

---

## The Two Structural Traps (fixed before any sweep)

### Trap 1 — Allomothering pool (dominant failure mode)

`_execute_action` selected child via `max(all_children, key=Hamilton_score)`.
With 15 children visible, all 15 mothers converged on the 1–2 most-distressed strangers.
Own-child feeds were diluted to ~1.9/child; distribution heavily skewed (2–3 children received all care, 12–13 starved at tick 29).

### Trap 2 — Maternal starvation (high care_weight)

When `held_food=1` and `care_weight ≥ 2.5`, CARE beat SELF even at critical hunger.
Mother delivered all food to children, starved at tick 30–45. Counterproductive at high care_weight.

---

## Fixes Applied (both carried into all ISM sweeps)

### Fix A — Own-child exclusivity (`simulation/simulation.py: _execute_action`)

Mother commits to `own_child_id` first; allomother fallback only when own child is absent/dead.  
**Biological basis**: oxytocin-driven maternal imprinting at parturition.

### Fix E — Starvation floor (`config.py: care_energy_floor = 0.3`)

Mother overrides CARE → SELF when `energy < care_energy_floor`.  
**Biological basis**: corticosterone foraging override under extreme hunger.

---

## On Hamilton r — Correct Framing

Phase 4 does NOT implement Hamilton r-selection. The own-child bond is imprinting-based (`own_child_id`), not r-computed. Post-bereavement fallback reduces to `argmax(distress)` (all strangers r=0). Hamilton r becomes structurally meaningful in Phase 5+ via spatial kin clustering.

---

## Phase 4 Key Files

| File | Role |
| --- | --- |
| `experiments/phase4_weight_sweep/config.py` | Sweep grid, PHASE4_FLAGS, `care_energy_floor=0.3` |
| `experiments/phase4_weight_sweep/run.py` | Sweep runner + weight selection logic |
| `experiments/phase4_weight_sweep/plot.py` | Heatmap, mother survival, 3D surface figures |
| `experiments/phase4_weight_sweep/plot_ism_vs_child_survival.py` | ISM vs C_matr two-panel figure |
| `outputs/phase4_weight_sweep/sweep_ism1/` | ISM=1.0 sweep results (OPTIMAL used for Block 2) |
| `outputs/phase4_weight_sweep/sweep_ism1p2/` | ISM=1.2 sweep results |
| `outputs/phase4_weight_sweep/sweep_ism2p33/` | ISM=2.33 sweep results (care trap confirmed) |
| `outputs/phase4_weight_sweep/ism_vs_child_survival.png` | ISM gating figure |

---

## Phase 4 Conclusion

ISM is the ecological feasibility gate for child maturation. At ISM=2.33 (original Phase 3 locked value), no motivational bias rescues child survival. At ISM=1.0, the OPTIMAL weight combo (care=0.5, forage=2.0, self=1.0) achieves C_matr=0.36 — selected as the Block 2 starting condition.

---

## Block 2 Baseline — LOCKED (2026-05-10, updated 2026-05-10 after Phase 4b)

### Ecology — Phase 4b BEST_CALIBRATED

Source: `outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json` → `"BEST_CALIBRATED"`

**Why Phase 4b, not Phase 2 easy:** Phase 2 easy (eat_gain=0.50, init_food=150, move_cost=0.02) was calibrated for 15 mothers with no children. Phase 4b confirmed that no combination with init_food ≤ 300 or eat_gain ≤ 0.50 passes the EASY gate (M_surv ≥ 80% AND C_matr ≥ 0.05) under OPTIMAL weights with 30 agents present. Phase 2 easy is structurally too sparse for mother-child pairs. Phase 4b swept init_food × eat_gain (7 × 4 = 28 combos, 840 runs total) and found exactly one qualifying ecology.

| Parameter | Value |
| --- | --- |
| `infant_starvation_multiplier` | **1.0** |
| `eat_gain` | **0.70** |
| `init_food` | **600** |
| `move_cost` | **0.005** |
| `rest_recovery` | 0.005 |
| `hunger_rate` | 1/35 ≈ 0.02857 |
| `perception_radius` | 8 |
| `food_perception_radius` | 8 |

Phase 4b result: C_matr=0.509, M_surv_metric=1.233 (metric > 1 because maturing children become new mothers; original 15 mothers plus ~7 new from maturation).

### Motivation Weights — Phase 4 sweep_ism1 OPTIMAL (unchanged)

Source: `outputs/phase4_weight_sweep/sweep_ism1/selected_weights.json` → `"OPTIMAL"`

| Parameter | Value |
| --- | --- |
| `care_weight` | **0.5** |
| `forage_weight` | **2.0** |
| `self_weight` | **1.0** |

**Validation note resolved:** The previous concern that OPTIMAL weights might not hold under Phase 2 easy ecology is now closed. Phase 4b confirmed the weights produce C_matr=0.509 under the BEST_CALIBRATED ecology, which IS the ecology Phase 5 will use.

---

## Block 1 → Block 2 Parameter Handoff

Complete parameter set entering Phase 5. All values locked from Block 1 sweeps.

### Ecology (Phase 4b BEST_CALIBRATED)

| Parameter | Block 1 phases that set it | Block 2 value |
| --- | --- | --- |
| `init_food` | Phase 4b sweep (7 × 4 grid) | **600** |
| `eat_gain` | Phase 4b sweep | **0.70** |
| `move_cost` | Phase 4 / Phase 4b diagnostic | **0.005** |
| `rest_recovery` | Phase 3b locked | 0.005 |
| `hunger_rate` | Phase 3b locked | 1/35 ≈ 0.02857 |
| `perception_radius` | Phase 4 config | 8 |
| `food_perception_radius` | Phase 4 config | 8 |
| `infant_starvation_multiplier` | Phase 4 ISM sweep | **1.0** |
| `maturity_age` | Phase 3 locked | 200 |
| `max_ticks` | Phase 3 locked | 400 |
| `init_mothers` | All phases | 15 |
| `initial_energy` | All phases | 1.0 |

### Motivation weights (Phase 4 OPTIMAL, sweep_ism1)

| Parameter | Phase 2 / Phase 3 | Block 2 value |
| --- | --- | --- |
| `care_weight` | 0.0 (Ph2) / 1.0 (Ph3 unbiased) | **0.5** |
| `forage_weight` | 1.0 | **2.0** |
| `self_weight` | 1.0 | **1.0** |

### Mechanism flags

| Flag | Block 1 | Block 2 |
| --- | --- | --- |
| `children_enabled` | False (Ph2) / True (Ph3+) | True |
| `care_enabled` | False (Ph2) / True (Ph3+) | True |
| `care_energy_floor` | 0.0 (Ph2/3) / 0.3 (Ph4) | **0.3** |
| `reproduction_enabled` | False | **True** (Phase 5) |
| `mutation_enabled` | False | **True** (Phase 5) |
| `plasticity_enabled` | False | TBD |
| `food_entropy_alpha` | 0.0 | TBD (Block 3 sweep) |
| `cry_decay_radius` | 0.0 | TBD (Block 3 sweep) |
| `temperature_sensitivity` | 0.0 | TBD (Block 3 sweep) |

### Genome starting values (Block 2 explicit defaults)

| Gene | Block 1 default | Block 2 baseline |
| --- | --- | --- |
| `distress_sensitivity` | 0.0 | **0.5** |
| `care_recovery` | 0.0 | **0.5** |

---

## Next: Phase 5 — Asynchronous Genetic Evolution (Block 2)

---

---

## Phase 4b Current State

Last updated: 2026-05-10 (V3 branch)

---

## Status: CONCLUDED — BEST_CALIBRATED locked

Phase 4b answers: "Given OPTIMAL motivation weights (care=0.5, forage=2.0, self=1.0) and ISM=1.0, which init_food × eat_gain ecology produces a stable mother population AND feasible child maturation?"

**Result:** Exactly one combo in the 7 × 4 = 28-combo grid passes both EASY gates (M_surv ≥ 80% AND C_matr ≥ 0.05).

---

## Sweep Design

| Axis | Values | Fixed |
| --- | --- | --- |
| `init_food` | 50, 100, 150, 200, 300, 400, 600 | — |
| `eat_gain` | 0.20, 0.30, 0.50, 0.70 | — |
| `move_cost` | — | **0.005** (matches Phase 4 working ecology) |
| `ISM` | — | **1.0** |
| Weights | — | care=0.5, forage=2.0, self=1.0 |

Seeds: 10 × 3 repeats = 30 runs per combo. Total: 840 runs.

**Why move_cost=0.005, not 0.02 (Phase 2 easy):** Single-seed diagnostic showed M_surv=0.067 with move_cost=0.02 and food=300. With 30 agents moving to forage and care, 0.02/step is too expensive — mothers starve before food density can compensate. Phase 4's working ecology used 0.005.

---

## Full Grid Results

| init_food | eat_gain | C_matr | M_surv | child_mu | care% | Gate |
| --- | --- | --- | --- | --- | --- | --- |
| 50 | 0.20 | 0.000 | 0.000 | 39.8 | 25.5% | ✗ |
| 50 | 0.30 | 0.000 | 0.002 | 43.4 | 29.3% | ✗ |
| 50 | 0.50 | 0.000 | 0.007 | 51.7 | 37.5% | ✗ |
| 50 | 0.70 | 0.000 | 0.007 | 56.8 | 39.0% | ✗ |
| 100 | 0.20 | 0.000 | 0.004 | 42.9 | 25.3% | ✗ |
| 100 | 0.30 | 0.000 | 0.067 | 48.9 | 30.4% | ✗ |
| 100 | 0.50 | 0.000 | 0.076 | 63.5 | 38.8% | ✗ |
| 100 | 0.70 | 0.004 | 0.058 | 77.0 | 41.2% | ✗ |
| 150 | 0.20 | 0.000 | 0.049 | 45.0 | 26.0% | ✗ |
| 150 | 0.30 | 0.000 | 0.213 | 53.9 | 33.1% | ✗ |
| 150 | 0.50 | 0.000 | 0.104 | 76.2 | 39.9% | ✗ |
| 150 | 0.70 | 0.036 | 0.107 | 98.0 | 40.6% | ✗ |
| 200 | 0.20 | 0.000 | 0.167 | 46.6 | 26.7% | ✗ |
| 200 | 0.30 | 0.000 | 0.404 | 56.9 | 34.1% | ✗ |
| 200 | 0.50 | 0.002 | 0.229 | 86.4 | 40.7% | ✗ |
| 200 | 0.70 | 0.067 | 0.202 | 104.7 | 41.0% | ✗ |
| 300 | 0.20 | 0.000 | 0.391 | 49.8 | 27.5% | ✗ |
| 300 | 0.30 | 0.000 | 0.584 | 63.7 | 35.6% | ✗ |
| 300 | 0.50 | 0.033 | 0.262 | 106.4 | 40.9% | ✗ |
| 300 | 0.70 | 0.196 | 0.467 | 123.4 | 40.3% | ✗ |
| 400 | 0.20 | 0.000 | 0.569 | 52.1 | 28.4% | ✗ |
| 400 | 0.30 | 0.000 | 0.653 | 70.8 | 36.4% | ✗ |
| 400 | 0.50 | 0.100 | 0.529 | 117.5 | 40.9% | ✗ M_surv |
| 400 | 0.70 | 0.316 | 0.798 | 132.4 | 38.9% | ✗ M_surv |
| 600 | 0.20 | 0.000 | 0.773 | 55.0 | 29.5% | ✗ C_matr |
| 600 | 0.30 | 0.000 | 0.733 | 78.9 | 37.4% | ✗ C_matr |
| 600 | 0.50 | 0.207 | 0.784 | 132.7 | 39.5% | ✗ M_surv |
| **600** | **0.70** | **0.509** | **1.233** | **135.8** | **38.0%** | **✓** |

M_surv > 1 is expected: maturing children become new mothers, growing the population past the initial 15. M_surv=1.233 means ~18.5 total alive mothers at the end (15 original + ~7.6 from maturation, minus some deaths).

---

## BEST_CALIBRATED Regime

| Parameter | Value |
| --- | --- |
| `infant_starvation_multiplier` | 1.0 |
| `eat_gain` | **0.70** |
| `init_food` | **600** |
| `move_cost` | **0.005** |
| `rest_recovery` | 0.005 |
| `hunger_rate` | 1/35 |
| `perception_radius` | 8 |
| `care_weight` | 0.5 |
| `forage_weight` | 2.0 |
| `self_weight` | 1.0 |
| C_matr (mean, 30 runs) | **0.509** |
| M_surv metric (mean, 30 runs) | 1.233 |
| child_death_mu (mean) | 135.8 ticks |

Saved to: `outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json`

---

## Key Finding

Phase 4b confirms that the Phase 3b/Phase 4 hardcoded ecology (eat_gain=0.70, init_food=600, move_cost=0.005) is not arbitrary — it is the minimum viable ecology for mother-child coexistence under OPTIMAL weights. No sparser ecology achieves both EASY mother survival and non-trivial child maturation simultaneously.

Specifically:

- **eat_gain is the binding constraint**: at eat_gain=0.50, even init_food=600 gives M_surv=0.784 (below gate). Mothers survive but barely — the forage_weight=2.0 bias keeps them foraging constantly, but energy per food item must be 0.70 to close the budget.
- **init_food is the secondary constraint**: at eat_gain=0.70, init_food=400 gives M_surv=0.798 (just below gate). Food density must be high enough for forage_weight=2.0 to find food quickly between care trips.

---

## Phase 4b Key Files

| File | Role |
| --- | --- |
| `experiments/phase4_weight_sweep/phase4b_config.py` | Locked params, sweep grid, `make_config()` |
| `experiments/phase4_weight_sweep/phase4b_run.py` | `run_one()`, sweep, selection, output |
| `experiments/phase4_weight_sweep/phase4b_plot.py` | C_matr heatmap, M_surv heatmap, scatter |

---

---

# World Mechanism Updates (Block 2 preparation)

Last updated: 2026-05-08 (V3 branch)

---

## Status: IMPLEMENTED — all mechanisms backward-compatible; Block 1 runs unaffected

All new features default to 0.0 / disabled. Block 1 experiments reproduce identically unless the new Config params are explicitly set.

---

## 1. Shannon Entropy Food Model

**Mechanism**: `spawn_rate(p) = −α × p × log(p)` per cell per tick.

| New Config param | Default | Description |
|---|---|---|
| `food_entropy_alpha` | 0.0 | Scale factor α — 0 = disabled (old food_replace_on_pick) |
| `food_entropy_beta` | 0.1 | Probability depletion on pick |
| `food_entropy_gamma` | 0.01 | Mean-reversion recovery rate per tick |
| `food_patch_prior` | 0.5 | Equilibrium probability p₀ per cell |

**Behavior when `food_entropy_alpha > 0`**:
- `world.init_patch_probs(p0)` called at initialize — all cells start at `p0`
- Per tick: each empty cell spawns food with probability `−α × p × log(p)` (peaks at p = 1/e ≈ 0.37)
- On pick: `p -= beta` at the picked cell (local depletion)
- Per tick: `p += gamma × (p0 − p)` mean reversion (global recovery)
- `food_replace_on_pick` is bypassed when entropy is active

**Files changed**: `config.py`, `simulation/world.py` (new `init_patch_probs`, `deplete_patch`, `recover_patches`), `simulation/simulation.py` (new `_spawn_food_entropy`, section 1c in `step()`)

---

## 2. Cry Signal Distance Attenuation

**Mechanism**: `distress_heard = distress × exp(−d / cry_decay_radius)`

| New Config param | Default | Description |
|---|---|---|
| `cry_decay_radius` | 0.0 | Decay length in cells — 0 = global cry (Block 1 behavior) |

**Behavior when `cry_decay_radius > 0`**:
- CARE motivation cue uses distance-attenuated distress, not raw `child.distress`
- `distress_sensitivity` cortisol penalty also uses attenuated signal
- At d=0: full distress; at d=cry_decay_radius: ~37% distress; at d=3×radius: ~5%

**Files changed**: `agents/mother.py` (`compute_care_cue`, `compute_motivation_scores`, `choose_motivation` — added `heard_distress`/`heard_care_distress` params), `simulation/simulation.py` (compute `_heard_care_distress` and `_heard_ds` before motivation call)

---

## 3. World Temperature Cycle

**Mechanism** (updated 2026-05-09): raw sinusoid with asymmetric cold/warm effects — children only.

```text
T(t) = sin(2π × t / temperature_period)   →  +1 = peak warm,  -1 = peak cold
warm phase (T > 0): child.energy -= temperature_sensitivity × T   (heat stress — direct drain)
cold phase (T < 0): hunger_rate += temperature_sensitivity × |T|  (thermoregulation cost)
```

| New Config param | Default | Description |
| --- | --- | --- |
| `temperature_period` | 200 | Ticks per full hot/cold cycle |
| `temperature_sensitivity` | 0.0 | Amplitude of thermal effect — 0 = disabled |

**Behavior when `temperature_sensitivity > 0`**:

- Warm phase (sin > 0): direct energy drain on child (`child.energy -=`); hunger synced immediately after (`child.hunger = 1 - child.energy`) before `update_distress()` is called.
- Cold phase (sin < 0): extra metabolic cost added to `hunger_rate` before `child.update_hunger()`.
- **Children only** — mothers are not affected. Old mother thermal drain code is commented out (not deleted) in `simulation/simulation.py`.
- Separate from `warmth_factor`/`warmth_radius` (maternal proximity warmth — unchanged, locked 0.0).

**Files changed**: `config.py` (rename + updated comment), `simulation/simulation.py` (`_warm_stress`/`_cold_stress` replacing old `_thermal_drain`)

---

## 4. Genome Defaults — distress_sensitivity and care_recovery

Not changed in `evolution/genome.py` (default stays 0.0 for Block 1 backward compatibility).

Block 2 config (`experiments/phase5_evolution/config.py`) will explicitly set:
- `distress_sensitivity = 0.5` (cortisol analog — moderate baseline)
- `care_recovery = 0.5` (prolactin analog — moderate baseline)

These genes will also be tested in Block 3 eco-pressure analysis (sensitivity parameter).

---

## Maturation Removal — No Bug Confirmed

`_check_maturation()` removal chain is clean:
1. `birth_mother.own_child_id = None` cleared immediately → mother can reproduce again
2. Child popped from `_child_by_id` and removed from `world.entities`
3. Child remains in `self.children` as `alive=False` until step-7 filter — excluded by all `c.alive` checks
4. New mother placed at `child.pos` with correct genome and lineage chain

Edge case noted: if a mother is standing on the child's cell at maturation tick, two mothers temporarily share the same world position (very rare, not a crash).

---

---

# Approved Next Steps (session 2026-05-08)

Last updated: 2026-05-08 (V3 branch)

---

## Status: COMPLETED (session 2026-05-08)

All three workstreams implemented and smoke-tested.

---

## Workstream 1 — Care Trap Diagnostic Plots (Route A)

Use **existing Phase 3 run data** (`outputs/phase3_survival_full/auto_400_20260508_183813/`).
No new simulation run needed. Add new plot functions to `experiments/phase3_survival_full/plot.py`.

### Scientific narrative

Phase 3 (ISM=2.33, all weights=1/1/1) already shows C_matr≈0. These plots explain *why* mechanistically.
Each figure is a **separate standalone PNG** — not multi-panel in the same figure.
Teacher audience: keep each plot simple and self-contained. No zooming into specific care trap moments.

### 5 individual plots

| Figure | Name | What it shows |
|--------|------|---------------|
| `caretrap_motivation_scores.png` | Motivation scores over time | 3 smooth lines (FORAGE, CARE, SELF scores) over ticks for 1 representative run (seed=42). FORAGE flatly dominates. X=tick, Y=score 0–1. |
| `caretrap_action_strip.png` | Action sequence strip | Categorical color strip: one colored cell per tick, color = action chosen (FORAGE/PICK/CARE_MOVE/FEED/EAT/REST). X=tick, Y=one row per mother (15 rows). Shows FORAGE-dominated pattern. |
| `caretrap_held_food.png` | held_food state | Step function (0 or 1) for 1 representative mother over ticks. Red ✗ markers at ticks where CARE motivation was chosen but held_food=0 (failed delivery). |
| `caretrap_child_energy.png` | Child energy decline | Per-child energy lines (15 children) declining to 0. Vertical dashed lines at ticks where CARE fired. Red dot at each child's death tick. |
| `caretrap_failed_care_bar.png` | % failed CARE attempts | Bar chart across all 15 mothers: % of CARE-selection ticks where held_food=0 at that moment. Population-level evidence. One sentence takeaway: "X% of CARE attempts fail because mother has no food to deliver." |

### Implementation note

To produce these plots, `Phase3Simulation.run()` must log per-tick:
- motivation chosen per mother
- action taken per mother
- `held_food` value per mother
- child energy per child
- whether CARE was chosen AND held_food=0 (failed delivery flag)

Check whether this data is already in the trajectory CSV from the existing run before adding new logging.

---

## Workstream 2 — Phase 4 Weight Sweep (Route B)

**New experiment**: `experiments/phase4_weight_sweep/` (re-implement from scratch — old files were deleted).

### Scientific narrative

Shows that increasing care_weight relative to forage_weight rescues child maturation.
Unbiased (1/1/1) is the leftmost column of the heatmap — C_matr≈0, connecting to Workstream 1.

### Sweep design

| Axis | Values | Note |
|------|--------|------|
| `care_weight` | 0.1, 0.5, 1.0, 1.5, 2.0 | primary axis |
| `forage_weight` | 0.1, 0.5, 1.0, 1.5, 2.0 | secondary axis |
| `self_weight` | 1.0 (fixed) | not swept — SELF drives EAT/REST, not the CARE→FEED chain |

Seeds per combo: 5. Total runs: 25 combos × 5 seeds = 125 runs.
Ecology: Phase 3b BEST_ECOLOGICAL (ISM=1.2, eat_gain=0.70, init_food=600, move_cost=0.005).
Carry forward Phase 4 fixes: own-child exclusivity (Approach A) + starvation floor `care_energy_floor=0.3` (Approach E).

### 3 figures

| Figure | Name | Type | Content |
|--------|------|------|---------|
| `sweep_3d_surface.png` | 3D motivation sweep | 3D surface (matplotlib `plot_surface`) | X=care_weight, Y=forage_weight, Z=mean C_matr. Viridis colormap. 2D heatmap projected below as shadow. `self_weight=1.0` noted in title. |
| `sweep_heatmap.png` | 2D weight heatmap | Annotated heatmap | care × forage grid, cell colour = mean C_matr, cell text = value. Contour line at C_matr=0.10 (VIABLE_MIN). ★ at OPTIMAL point. |
| `sweep_mother_survival.png` | Mother survival heatmap | Annotated heatmap | Same grid, cell colour = mean M_surv. Overlay: same VIABLE_MIN contour from C_matr figure. |

### Key outputs

- `selected_weights.json` — VIABLE_MIN (lowest care_weight with C_matr≥0.10) and OPTIMAL (highest C_matr combo)
- `sweep_results_raw.csv` — one row per (care, forage, seed)
- `sweep_summary.csv` — one row per (care, forage), mean ± SD across seeds

---

## Workstream 3 — OOP Restructure + CLI Config (Phase 1–3)

**Goal**: make all phases runnable cleanly on a Linux terminal/server for long Phase 5+ evolution runs.
Implement after Workstreams 1 and 2 are confirmed working.

### Problems with current code

- Each phase has its own flat `config.py / run.py / plot.py` with hardcoded defaults
- No CLI to override individual params without editing source files
- No `--config path/to/file.json` support for batch server jobs
- No shared base class — common logic (seed loops, CSV writing, progress logging) duplicated across phases

### Target structure

```
experiments/
  base/
    __init__.py
    experiment.py     ← BaseExperiment class
    cli.py            ← shared argparse builder
    io_utils.py       ← shared CSV / JSON write helpers
  phase2_survival_minimal/
    experiment.py     ← Phase2Experiment(BaseExperiment)
    config.py         ← parameter dataclass + defaults (no hardcoding)
    plot.py           ← unchanged style
  phase3_survival_full/
    experiment.py     ← Phase3Experiment(BaseExperiment)
    config.py
    plot.py
  phase4_weight_sweep/
    experiment.py     ← Phase4Experiment(BaseExperiment)
    config.py
    plot.py
```

### BaseExperiment contract

```python
class BaseExperiment:
    def __init__(self, cfg: Config, out_dir: Path): ...
    def run_one(self, seed: int) -> dict: ...          # override per phase
    def run_sweep(self, grid: list[dict]) -> pd.DataFrame: ...
    def save_results(self, df: pd.DataFrame) -> None: ...
    def make_plots(self, df: pd.DataFrame) -> None: ...  # override per phase
```

### CLI requirements (every phase entry point)

```bash
python -m experiments.phase3_survival_full.experiment \
    --mode pipeline \
    --config configs/phase3_balanced.json \
    --duration 1000 \
    --seeds 10 \
    --workers 8 \
    --output-dir outputs/phase3_run1
```

All `Config` fields overridable via `--param value` flags (generated from dataclass fields).
`--config` loads a JSON file first; CLI flags override on top.
Progress logged to stdout with timestamps (for nohup/screen sessions on Linux).

### Backward compatibility

- Old `new_run.py` / `run.py` entry points kept as thin shims that call the new classes
- Existing output directories and JSON formats unchanged
- All prior phase outputs remain valid inputs for downstream phases

---

## Completion Summary

| Workstream | Status | Key files |
|-----------|--------|-----------|
| WS1 — Care Trap Diagnostics | Done | `experiments/phase3_survival_full/plot.py` (+5 caretrap functions), `run.py` (`run_diagnostic`, `caretrap` CLI mode) |
| WS2 — Phase 4 Weight Sweep | Done | `experiments/phase4_weight_sweep/{config,run,plot,experiment}.py` |
| WS3 — OOP Restructure + CLI | Done | `experiments/base/{experiment,cli,io_utils}.py`, phase adapters for 2/3/4 |

---

## Shared CLI — `experiments/base/cli.py`

Every phase entry point is `experiments/<phase>/experiment.py`.
All phases share the same flags via `build_parser()`.

### Full flag reference

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `pipeline` | Phase-specific modes (pipeline / sweep / single / caretrap) |
| `--load RESULT.json` | — | Load a prior phase output JSON; auto-sets matching Config params |
| `--load-key KEY` | auto | Sub-key inside the loaded JSON (e.g. `OPTIMAL`, `BALANCED`, `BEST_ECOLOGICAL`). Auto-detected when the JSON has exactly one nested-dict entry. |
| `--config FILE.json` | — | Hand-written Config override JSON (applied after `--load`) |
| `--duration N` | 400 | Simulation ticks |
| `--seeds N` | 10 | Seeds per config |
| `--workers N` | 4 | Parallel workers (`0` = auto `os.cpu_count()`) |
| `--output-dir PATH` | auto | Explicit output dir (timestamped auto-path if omitted) |
| `--param key=value` | — | Override any Config field (repeatable; highest priority) |

### Priority order (lowest → highest)

```
--load  <  --config  <  --param
```

### Phase-chaining examples

```bash
# Phase 4: load Phase 3b BEST_ECOLOGICAL ecology
python -m experiments.phase4_weight_sweep.experiment \
    --load outputs/phase3_survival_full/phase3b_calibration/selected_ecologies.json \
    --load-key BEST_ECOLOGICAL \
    --mode sweep --workers 4

# Phase 5: load Phase 4 OPTIMAL weights as starting genome
python -m experiments.phase5_evolution.experiment \
    --load outputs/phase4_weight_sweep/sweep_20260508_194211/selected_weights.json \
    --load-key OPTIMAL \
    --mode test --workers 4

# Override one param on top of loaded values
python -m experiments.phase4_weight_sweep.experiment \
    --load outputs/.../selected_ecologies.json --load-key BEST_ECOLOGICAL \
    --param max_ticks=800 --workers 4
```

### Entry points

| Phase | Entry point |
|-------|-------------|
| Phase 2 | `python -m experiments.phase2_survival_minimal.experiment` |
| Phase 3 | `python -m experiments.phase3_survival_full.experiment` |
| Phase 4 | `python -m experiments.phase4_weight_sweep.experiment` |

---

---

## Phase 5 Block 2 — Pre-Implementation Decisions

Last updated: 2026-05-10 (V3 branch)

---

## Status: APPROVED — Ready to implement

All design decisions locked in review session 2026-05-10.

---

## Ecology Source (corrected from EVO_PROPOSAL)

EVO_PROPOSAL referenced `BEST_ECOLOGICAL.json` — file does not exist.
Actual source:

```
outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json → "BEST_CALIBRATED"
```

Phase 5 inherits Phase 4b values exactly. No re-calibration. Energy regime is unchanged.

---

## Full Metabolic Cost Model (Two Aspects)

### 1. Body Metabolism (caregiving)

```
C_body = hunger_rate × T_sequence
       + move_cost × (d_forage + d_deliver)
       + feed_cost
```

Typical breakdown per feeding event:

| Component | Formula | Approx value |
| --- | --- | --- |
| Base metabolism (time cost) | `(1/35) × ~12 ticks` | **≈ 0.343** (82%) |
| Movement cost | `0.005 × ~10 steps` | ≈ 0.050 (12%) |
| Feed act | `feed_cost = 0.03` | ≈ 0.030 (7%) |
| **Total C_body** | | **≈ 0.423** |

`feed_cost` was never swept in Block 1 — it is 7% of C_body. The dominant cost is `hunger_rate × T_sequence` (time spent in the care sequence). This was validated empirically in Phase 4b (C_matr=0.509 at these values).

### 2. Brain Metabolism (plasticity)

```
C_brain = alpha × |Δweights| + beta × plasticity_coefficient

Where:
  alpha = plasticity_alpha  = 0.01   (per magnitude of weight change)
  beta  = plasticity_beta   = 0.001  (maintenance cost baseline)
```

Only paid when `plasticity_enabled=True` AND `modulation_signal ≠ 0`.

### Total

```
C_total = C_body + C_brain
```

**Baldwin selection mechanism**: a mother with innate care (high `genome.care_weight`, low `plasticity_coefficient`) pays `C_body` only. A mother who learns to care pays `C_body + C_brain` every event. Evolution selects toward the cheaper strategy → genetic assimilation.

---

## Architecture Decisions (Implemented 2026-05-10)

### 1. Config layer — `Phase5ConfigFactory` (static factory class)

Root `config.py` is **FROZEN** — Phase 5 adds no fields there. All Phase 5 config logic lives in:

```
experiments/phase5_evolution/config.py  ← Phase5ConfigFactory class
```

`Phase5ConfigFactory` is a pure-static class (no instances). It owns:

- `_ECOLOGY_PATH` — path to Phase 4b JSON (class constant)
- `_FALLBACK` — hardcoded fallback dict (class constant)
- `load_ecology() -> dict` — loads and unwraps `"BEST_CALIBRATED"` from JSON
- `make(...) -> Config` — builds fully configured `Config` from ecology + CLI params

### 2. Run layer — `EvolutionRunner` + `RunParams`

```text
experiments/phase5_evolution/run.py  ← RunParams dataclass + EvolutionRunner class
```

`RunParams` is a plain dataclass holding all hyperparameters. Acts as the single source of truth for what a run looks like — also the only object that crosses the process boundary in multiprocessing.

`EvolutionRunner` encapsulates all runtime logic:

- `run_sweep(output_dir) -> list[dict]` — parallel orchestration via `ProcessPoolExecutor`
- `save(results, output_dir)` — CSV + JSON persistence
- `_run_worker(seed, params)` — `@staticmethod` for picklable multiprocessing
- `_execute_single(seed)` — one seed end-to-end
- `_initial_genomes(n)` — neutral genome population (care=forage=self=1/3)
- `_sample(sim, tick)` — all ROADMAP metrics per snapshot
- `_write_snapshots_csv(results, path)` — `@staticmethod` persistence helper
- `_write_summary_json(results, path)` — `@staticmethod` persistence helper

### 3. Plot layer — `EvolutionPlotter`

```text
experiments/phase5_evolution/plot.py  ← EvolutionPlotter class
```

`EvolutionPlotter` reads `snapshots.csv` only — fully decoupled from simulation:

- `plot(output_file=None)` — public entry point, 4-panel figure
- `_plot_genome_care(ax, df, seeds, colors)` — private per-subplot
- `_plot_expressed_care(ax, df, seeds, colors)` — private per-subplot
- `_plot_innateness(ax, df, seeds, colors)` — private per-subplot
- `_plot_genome_behavior_distance(ax, df, seeds, colors)` — private per-subplot
- `_draw_seed_lines(ax, df, seeds, colors, col)` — private DRY helper (used by all 4 subplots)
- `_style_axes(ax)` — `@staticmethod` academic styling

### 4. Genome layer — `Genome` (dataclass, minimal OOP refactor)

```text
evolution/genome.py  ← Genome dataclass
```

- `_mutate_gene(value, mutation_rate, sigma)` — `@staticmethod` private helper (replaces inline function)
- `_renormalize(care, forage, self_w)` — `@staticmethod` private helper (weight sum = 1.0)
- `mutate(mutation_rate, sigma, lock_learning_rate)` — now uses both private statics
- Google-style docstrings on all public methods

### 5. Agent layer — `MotherAgent` (minimal cleanup only)

Phase 5 methods (`compute_modulation_signal`, `compute_plasticity_cost`) remain in `mother.py`:

- Guard clauses replace nested if-chains in `compute_modulation_signal()`
- `hasattr` defensive check removed from `compute_plasticity_cost()` (unnecessary since `__init__` always sets `last_learning_delta`)
- Google-style docstrings added to both methods

---

## Missing Block 1 Sweep Variables (Block 3 Sensitivity Targets)

These were never swept in Block 1. They are uncontrolled in Phase 5 but are valid Block 3 sensitivity targets:

| Variable | Current value | Why it matters for Baldwin |
| --- | --- | --- |
| `feed_cost` | 0.03 (never swept) | 7% of C_body — caregiving act cost |
| `reproduction_threshold` | 0.85 (never swept) | Controls generation turnover speed |
| `reproduction_cost` | 0.35 (never swept) | Energy per birth — fitness tradeoff |
| `mother_max_age` | 400 (never swept) | Generation length and overlap |

Phase 4b validated the system (C_matr=0.509) with all four fixed. Not blockers for Phase 5.
Speed of Baldwin assimilation observed in Phase 5 is partly a function of these values.

---

## Implementation Status

| File | Class / Change | Status |
| --- | --- | --- |
| `evolution/genome.py` | `Genome` — `_mutate_gene`, `_renormalize` static helpers; `lock_learning_rate` param | ✅ Done |
| `agents/mother.py` | Guard clauses + docstrings in `compute_modulation_signal`, `compute_plasticity_cost` | ✅ Done |
| `experiments/phase5_evolution/__init__.py` | Empty module marker | ✅ Done |
| `experiments/phase5_evolution/config.py` | `Phase5ConfigFactory` static class | ✅ Done |
| `experiments/phase5_evolution/run.py` | `RunParams` dataclass + `EvolutionRunner` class | ✅ Done |
| `experiments/phase5_evolution/plot.py` | `EvolutionPlotter` class | ✅ Done |
