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

Last updated: 2026-05-07 (V3 branch)

---

## Status: CONCLUDED — food density alone cannot support child maturation

Phase 3 answers: "Can ecological pressure from food density alone, with unbiased motivation
weights=1.0, produce child maturation through maternal care?"

**Answer: NO.** Sensitivity sweep over 7 init_food values × 10 seeds = 70 runs shows zero
child maturation at all levels. Energy math confirms this is a hard structural limit, not a
bug. Proceeds to Phase 4 (motivation weight sweep).

---

## Ecology (percept8 BALANCED — locked from Phase 2)

| Parameter | Value | Source |
|-----------|-------|--------|
| `perception_radius` | 8.0 | Phase 2 percept8 BALANCED |
| `food_perception_radius` | 8 | explicit (overrides Config default=15) |
| `hunger_rate` | 1/35 ≈ 0.0286 | Phase 2 |
| `move_cost` | 0.005 | Phase 2 |
| `eat_gain` | 0.2 | Phase 2 |
| `init_food` | swept 40–900 | Phase 3 variable |
| `rest_recovery` | 0.005 | Phase 2 |

## Phase 3 Additions (locked)

| Parameter | Value | Note |
|-----------|-------|------|
| `children_enabled` | True | 1 child per mother at init |
| `care_enabled` | True | |
| `infant_starvation_multiplier` | 35/15 ≈ 2.33 | child starves in 15 ticks unfed — biological lock |
| `care_weight` | 1.0 | unbiased, all equal |
| `forage_weight` | 1.0 | |
| `self_weight` | 1.0 | |
| `warmth_factor` | **0.0** | reserved Phase 5+ — locked off for Phase 3/4 |
| `max_ticks` | 400 | |
| `init_mothers` | 15 | |
| `maturity_age` | 200 | default — child must survive 200 ticks to mature |

---

## Key Files

| File | Role |
|------|------|
| `experiments/phase3_basic/config.py` | Loads percept8 BALANCED from Phase 2 JSON |
| `experiments/phase3_basic/run.py` | Diagnostic runner: tick-by-tick trace |
| `experiments/phase3_sweep/config.py` | Sweep config: INIT_FOOD_VALUES, SWEEP_SEEDS |
| `experiments/phase3_sweep/run.py` | Parallel sweep runner (ProcessPoolExecutor) |
| `experiments/phase3_sweep/plot.py` | Three-figure plot suite from CSV + live sims |
| `simulation/simulation.py` | Core sim — all 5 fixes applied |
| `agents/mother.py` | feed_child() — Fix E applied |
| `agents/child.py` | update_distress() — hunger-only distress |

---

## All Fixes (chronological)

### Fix A — Clear stale commitment when committed child dies
**Bug**: `has_commitment()` forced CARE domain for up to 20 ticks after child death.
Mother held food but could never eat → starvation.
**Fix**: Before commitment check, query `_get_child_by_id`; if dead or None, clear commit.

### Fix B — Cap held_food=1; suppress forage_cue when provisioned
**Bug**: Mother accumulated held_food=2. forage_cue always high → food never eaten.
**Fix**: Cap at 1 in FORAGE block. When `held_food >= 1`, set `nearest_food=None` → forage_cue=0.

### Fix C — Kin-directed care motivation (birth imprinting / oxytocin bond)
**Bug**: care_child was globally most distressed child (commons trap) → collective distress
always beat SELF drive → mothers starved caring for strangers' children.
**Biological basis**: Oxytocin bond at parturition; prolactin amplifies own-infant response.
Required for Hamilton r to be meaningful in Phase 6+.
**Fix**: care_child = mother's `own_child_id` target only; allomother only when own child absent.

### Fix D — Relatedness-weighted action target (Hamilton r-bias)
**Bug**: `_execute_action` picked globally most distressed child; mother navigated to
stranger while own child was distant.
**Fix**: `score = expressed_care_weight × (1+r) × child.distress`. Own child r=0.5 → 1.5× boost.
Allomothering possible when stranger's distress > (1/1.5) × own child's.
**Future**: Option 3 (proximity-decayed allomother threshold) reserved for Phase 5+.

### Fix E — feed_child requires held_food; energy conservation (2026-05-07)
**Bug**: `feed_child()` had no `held_food` check. Mother fed child out of thin air
(held_food=0 → success). One food pickup enabled 3+ child feeds (held_food never
decremented). Created phantom energy, inflated feed counts, masked real ecology.
**Fix** (`agents/mother.py`):
```python
if self.held_food <= 0:
    return False, 0.0
self.held_food -= 1
```
**Companion fix** (`simulation/simulation.py`, `_execute_action`): when mother arrives
at child (dist=0) with held_food=0, release commitment so she can immediately forage.

### Fix (distress formula) — Hunger-only infant distress
**Bug**: `distress = (hunger + separation) / 2`. Separation contribution was artificial
(children are immobile infants; separation reflects mother moving to forage, not infant agency).
**Fix** (`agents/child.py`): `distress = hunger = 1 − energy`.

---

## Phase 3 Sensitivity Sweep Results (percept8 BALANCED, warmth=0, all weights=1.0)

70 runs (7 init_food × 10 seeds), max_ticks=400

| init_food | M_surv | C_matr | Feeds | CARE% | FOR% | SELF% | C_death_mu | C_rng |
|-----------|--------|--------|-------|-------|------|-------|------------|-------|
| 40  | 0.000 | 0.000 | 12 | 76.7 | 16.4 | 6.9 | 17.4 | 15–21 |
| 80  | 0.000 | 0.000 | 18 | 73.1 | 21.3 | 5.7 | 18.7 | 15–24 |
| 150 | 0.013 | 0.000 | 21 | 70.0 | 24.6 | 5.4 | 19.2 | 15–24 |
| 250 | 0.153 | 0.000 | 24 | 69.9 | 24.7 | 5.4 | 19.9 | 15–24 |
| 400 | 0.293 | 0.000 | 29 | 69.8 | 25.1 | 5.0 | 20.8 | 18–27 |
| 600 | 0.447 | 0.000 | 30 | 70.8 | 24.7 | 4.5 | 21.0 | 18–30 |
| 900 | 0.567 | 0.000 | 32 | 71.1 | 23.5 | 5.4 | 21.3 | 18–33 |

**Phase 2 BALANCED (no children) reference: M_surv = 62.8%**

Key observations:
- Feeds increase monotonically with food (correct after Fix E) — confirms energy is now conserved
- Even at food=900 (6×), C_death_mu = 21.3 ticks vs maturity_age = 200 — factor of ~9.5× gap
- Mother survival severely degraded vs Phase 2 (57% vs 63%) even with 6× food
- Adding children costs ~6–63% mother survival depending on food density

### Why child maturation is impossible with weights=1.0

Energy budget per child:
```
Energy needed to reach maturity_age=200:  200 × 0.0667 − 1.0 = 12.3 units
Feeds needed:  12.3 / 0.2 = 62 feeds per child
Best observed: 32 total / 15 children = 2.1 feeds per child (food=900)
Gap: 30× shortfall
```
Foraging cycle (forage→navigate→feed→forage): ~8 ticks minimum.
Maximum possible feeds in 200 ticks: 200/8 = 25 per child — still short of 62.
Food density alone cannot close this gap because the bottleneck is cycle time, not food availability.

---

## Plots Generated

Output: `outputs/phase3_sweep/plots/`
- `fig1_sweep_summary.png` — init_food vs feeds / mother survival / child death / action split
- `fig2_timeseries.png` — per-tick population, mother energy, child energy (seed=42, food=900)
- `fig3_phase2_vs_3.png` — mother survival and energy trajectory: Phase 2 vs Phase 3

---

## Phase 3 Conclusion

Food density alone (init_food sweep) with unbiased weights=1.0 and ISM=2.33 cannot produce
child maturation. The care loop is mechanically correct. Phase 4 must introduce motivational
bias (care_weight > forage/self) to close the feeding-cycle gap.

---

## Next: Phase 3b — Ecological Calibration (ISM Sweep)

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

**Answer: care_weight=1.0 is sufficient once the two structural traps are removed.** With fixes applied, C_matr rises from 0.013 (pre-fix maximum) to 0.30–0.75 depending on forage_weight. Child maturation is now mechanically viable.

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

## Next: Phase 5 — Spatial Ecology and Kin Clustering

