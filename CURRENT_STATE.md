# Phase 2 Current State

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

| Set | Key | Values |
|-----|-----|--------|
| A | `init_food` | 10, 20, 40, 80, 150 |
| B | `eat_gain` | 0.05, 0.10, 0.20, 0.50, 0.80 |
| C | `move_cost` | 0.005, 0.01, 0.02, 0.05, 0.10 |

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

## OVAT Sweep Axes (same as Phase 2, extended init_food range)

| Set | Key | Values |
|-----|-----|--------|
| A | `init_food` | 40, 100, 200, 400, 700, 1000, 1500 |
| B | `eat_gain` | 0.10, 0.20, 0.30, 0.50, 0.70 |
| C | `move_cost` | 0.005, 0.01, 0.02, 0.05, 0.10 |

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

Last updated: 2026-05-07 (V3 branch)

---

## Status: CONCLUDED — child maturation achieved after two structural fixes

Phase 4 answers: "What is the minimum care_weight bias that enables child maturation, given the BEST_ECOLOGICAL baseline from Phase 3b?"

**Answer: child maturation is mechanically viable once the two structural traps are removed.**  
In the recorded Phase 4 output (`outputs/phase4_weight_sweep/selected_weights.json`):  
- **VIABLE_MIN** = `care=0.1, forage=0.5, self=0.5` (`C_matr=0.120`)  
- **OPTIMAL** = `care=0.2, forage=1.0, self=0.1` (`C_matr=0.533`, `M_surv=0.787`)  
This confirms viability without requiring `care_weight=1.0`.

---

## Ecological Baseline (locked from Phase 3b BEST_ECOLOGICAL)

| Parameter | Value |
|-----------|-------|
| `infant_starvation_multiplier` | 1.2 |
| `eat_gain` | 0.70 |
| `init_food` | 600 |
| `move_cost` | 0.005 |
| `rest_recovery` | 0.005 |
| `hunger_rate` | 1/35 |
| `food_perception_radius` | 8 |
| `maturity_age` | 200 |
| `max_ticks` | 400 |
| `init_mothers` | 15 |
| `feeds_needed` | 8.4 (formula: (200 × 1/35 × 1.2 − 1.0) / 0.70) |

---

## Phase 4 Initial Sweep (before fixes) — null result confirmed

Full 2D grid (care_weight × forage_weight, 30 combos × 5 seeds = 150 runs):

- Maximum C_matr across all combos: **0.013** (1 child per 75 total)
- feeds/child: 1.5–2.0 across all weight combinations (needed: 8.4)
- Root cause: two structural traps prevented effective care delivery

---

## The Two Structural Traps

### Trap 1 — Allomothering pool (dominant failure mode)

`_execute_action` selected child via `max(all_children, key=Hamilton_score)`.
With 15 children visible, all 15 mothers converged on the 1–2 most-distressed strangers.
A mother abandons her own child whenever any stranger's distress exceeds `1.5 × own_child.distress`.
Own-child feeds were diluted to ~1.9/child (average); distribution was heavily skewed (2–3 children received all care, 12–13 received none and starved at tick 29).

### Trap 2 — Maternal starvation (high care_weight)

When `held_food=1` and `care_weight ≥ 2.5`, CARE always beat SELF even at critical hunger.
Mother delivered all food to children, never ate herself, starved at tick 30–45.
Fewer total feeds delivered per run as care_weight increased — the opposite of the intended effect.

---

## Fixes Applied

### Fix — Approach A: Own-child exclusivity (`simulation/simulation.py: _execute_action`)

```python
# Commit to own infant first; allomother only when own child is absent or dead.
if mother.own_child_id is not None:
    _own = self._get_child_by_id(mother.own_child_id)
    if _own and _own.alive:
        target = _own   # skip Hamilton max-scan entirely
# Fall back to distress-responsive selection only when childless.
if target is None and visible_children:
    target = max(visible_children, key=lambda c: ... * c.distress)
```

**Biological basis**: Oxytocin-driven maternal imprinting at parturition. The mother bonds to the specific infant she birthed (`own_child_id`). She responds to her own infant's cry preferentially regardless of who is crying loudest — the mechanism that makes kin selection produce inclusive fitness gains without requiring explicit r-computation.

### Fix — Approach E: Starvation floor (`simulation/simulation.py: step()`, `config.py`)

```python
# Survival override: mother cannot commit to CARE when critically hungry.
if domain == "care" and mother.energy < config.care_energy_floor:
    domain = "self"    # eat carried food if available
    # or "forage" + break commitment if empty-handed
```

`care_energy_floor = 0.3` in Phase 4. Default = 0.0 in `Config` (disabled — all prior phases unaffected).

**Biological basis**: Corticosterone-driven foraging override. In real mammals, extreme hunger suppresses maternal behaviour — a mother cannot provision offspring she cannot survive to care for.

---

## Results After Fixes (10 seeds each)

| Weights | C_matr before | C_matr after | feeds/child | M_surv |
|---------|--------------|--------------|-------------|--------|
| care=1.0, forage=1.0 | 0.000 | **0.307** | 11.0 | 0.427 |
| care=1.0, forage=2.0 | 0.013 | **0.747** | 13.4 | 1.433* |
| care=1.5, forage=2.0 | 0.013 | **0.700** | 14.0 | 1.360* |
| care=1.5, forage=1.0 | 0.000 | **0.113** | 10.4 | 0.300 |

*M_surv > 1.0 is correct: matured children become new mothers (reproduction_enabled=False but `_check_maturation()` still runs), so the final mother count can exceed INIT_MOTHERS=15.

feeds/child > 8.4 needed in all cases — the feeding bottleneck is resolved.

---

## On Hamilton r and Allomothering — Correct Framing

**Phase 4 does NOT implement Hamilton r-selection.** The two-stage behavioral rule is:

1. **Imprinting-based own-child care** — mother recognises own infant via `own_child_id` (set at birth). This is the biological mechanism that evolution selects under Hamilton's rule, but the agent computes no r.
2. **Post-bereavement maternal responsiveness** — when own child is dead/absent, residual maternal drive responds to the most distressed visible infant. All strangers have r=0, so the Hamilton `(1+r)` term equals 1.0 for everyone → the fallback reduces to plain `argmax(distress)`. No kin-selection is occurring.

Hamilton r becomes structurally meaningful only in Phase 5+, when spatial kin clustering (natal philopatry, `birth_scatter_radius`) creates non-zero r between neighbouring agents. In Phase 4 the r-weighting formula is forward-compatible scaffolding; it does not change behaviour.

**How to describe allomothering in Phase 4 write-ups**: "When own child has died, the mother's residual maternal motivation responds to any distressed infant within range (post-bereavement responsiveness). This is not kin selection — it is a behavioural artefact of persistent maternal drive without a target."

---

## Key Files

| File | Role |
|------|------|
| `experiments/phase4_weight_sweep/config.py` | Sweep grid, PHASE4_FLAGS, `care_energy_floor=0.3` |
| `experiments/phase4_weight_sweep/run.py` | 7-step pipeline: threshold → OVAT → grid → selection → validation |
| `experiments/phase4_weight_sweep/plot.py` | 5-figure suite; grid_heatmap vmax fixed to data-scaled |
| `simulation/simulation.py` | Approach A (own-child exclusivity) + Approach E (starvation floor) |
| `config.py` | `care_energy_floor: float = 0.0` added (default disabled) |
| `outputs/phase4_weight_sweep/` | CSVs + plots from pre-fix run (reflect null result) |

---

## Phase 4 Conclusion

Two behavioral fixes — own-child exclusivity (maternal imprinting) and a starvation floor (self-preservation override) — are necessary and sufficient to enable child maturation under the BEST_ECOLOGICAL parameters. Neither fix requires genetic evolution or plasticity: they are fixed behavioral rules that remove the two structural traps blocking care delivery.

The Phase 4 sweep establishes that:
1. `care_weight=1.0` with `forage_weight=2.0` achieves the highest C_matr (~0.75), because high forage_weight ensures mothers are always provisioned before committing to CARE.
2. The minimum viable combination is `care_weight=1.0, forage_weight=1.0` (C_matr=0.31) — demonstrating that the weight value itself matters less than removing the structural traps.
3. The starvation floor prevents high care_weight from being counterproductive.

---

## Next: Phase 5 — Asynchronous Genetic Evolution

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

**Mechanism**: `thermal_drain(t) = warm_sensitivity × |sin(2π × t / temperature_period)|`

| New Config param | Default | Description |
|---|---|---|
| `temperature_period` | 200 | Ticks per full hot/cold cycle |
| `warm_sensitivity` | 0.0 | Amplitude of thermal drain — 0 = disabled |

**Behavior when `warm_sensitivity > 0`**:
- `abs(sin(...))` model: both summer peak and winter peak drain energy (thermoneutral zone at sin=0)
- Applied to both mothers (energy drain) and children (additive hunger rate)
- Computed once per tick as `_thermal_drain`, applied to all agents
- Block 1–2: set to very low value (e.g., 0.005); Block 3: sweep to observe evolved response

Note: separate from `warmth_factor`/`warmth_radius` (maternal proximity warmth — unchanged).

**Files changed**: `config.py`, `simulation/simulation.py` (`_thermal_drain` in `step()`)

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
