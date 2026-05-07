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

## Status: Mechanistic loop correct — child survival = 0 (ecology/timing)

Phase 3 adds one child per mother to Phase 2. The mechanistic care loop (forage → navigate →
feed → eat → forage) is confirmed working. Child survival = 0 is an ecological timing issue,
not a code bug. Root cause and next step documented below.

---

## Ecology (percept15 BALANCED — locked from Phase 2)

| Parameter | Value |
|-----------|-------|
| `perception_radius` | 15.0 |
| `hunger_rate` | 1/35 ≈ 0.0286 |
| `move_cost` | 0.01 |
| `eat_gain` | 0.5 |
| `init_food` | 40 |
| `rest_recovery` | 0.005 |

## Phase 3 Additions

| Parameter | Value |
|-----------|-------|
| `children_enabled` | True |
| `care_enabled` | True |
| `infant_starvation_multiplier` | 35/15 ≈ 2.33 — child starves in 15 ticks unfed |
| `care_weight` | 1.0 (fixed genome) |
| `forage_weight` | 1.0 (fixed genome) |
| `self_weight` | 1.0 (fixed genome) |
| `max_ticks` | 400 |
| `init_mothers` | 15 |

---

## Key Files (V3 — Phase 3 Basic)

| File | Role |
|------|------|
| `experiments/phase3_basic/config.py` | Loads percept15 BALANCED from Phase 2 JSON; sets Phase 3 flags |
| `experiments/phase3_basic/run.py` | Diagnostic runner: tick-by-tick trace + multi-seed summary |
| `simulation/simulation.py` | Core sim — all four Phase 3 fixes applied here |

---

## Fixes Applied to simulation.py (2026-05-07)

### Fix A — Clear stale commitment when committed child dies
**Bug**: `has_commitment()` returned True even after committed child died. `domain="care"` was forced
for up to 20 more ticks. Mother held food (held_food=2) but could not eat → starved.

**Fix** (motivation block, before commitment check):
```python
if mother.has_commitment():
    _tgt = self._get_child_by_id(mother.target_child_id)
    if _tgt is None or not _tgt.alive:
        mother.commit_ticks = 0
        mother.target_child_id = None
```

### Fix B — Cap held_food at 1; suppress forage_cue when provisioned
**Bug**: Mother accumulated held_food=2. With forage_cue ≈ 0.667 (perception_radius=15), FORAGE
always beat SELF — food was gathered but never eaten.

**Fix**: Cap held_food at 1 in FORAGE execution block. When `held_food >= 1`, set
`nearest_food = None` → forage_cue = 0 → motivation is SELF (eat) vs CARE (feed child).

### Fix C — Kin-directed care motivation (birth imprinting)
**Bug**: care_child for motivation was the globally most distressed of 15 children (commons trap).
Collective distress always > SELF drive → mothers starved caring for non-own children.

**Biological basis**: Oxytocin bond at parturition. Mother's care motivation is selectively
amplified for own infant (birth imprinting / prolactin analog). Required for Hamilton r to
be meaningful as a predictor at Phase 6+.

**Fix** (motivation block only):
```python
if mother.own_child_id is not None:
    _own = self._get_child_by_id(mother.own_child_id)
    care_child = _own if (_own and _own.alive) else None
else:
    care_child = mother.choose_child(visible_children) if visible_children else None
```

### Fix D — Relatedness-weighted action target (Hamilton r-bias)
**Bug**: `_execute_action` used globally most distressed child as target. Mother navigated to
a stranger's child while own child drifted to dist=12 unattended.

**Biological basis**: Kin-selective care — bias own infant without excluding allomothering.
Biologically: mother can care for others while own child is alive, but prefers own.
For Hamilton's hypothesis: r is embedded directly in the selection function so care-rate vs r
is measurable in Phase 6+ without retrofitting.

**Fix** (`_execute_action` target selection):
```
score = expressed_care_weight × (1 + r) × child.distress
target = max(visible_children, key=score)
```
Own child r=0.5 → 1.5× score. Allomother when stranger's distress > (1/1.5) × own child's.

**Future extension**: Option 3 (proximity-decayed allomother threshold) reserved for when
spatial kin clustering develops in Phase 5+.

---

## Current Diagnostic Results (seeds 42–46, 400 ticks)

| Seed | M_surv | C_surv | Feeds | CARE% | FORAGE% | SELF% |
|------|--------|--------|-------|-------|---------|-------|
| 42 | 0.000 | 0.000 | 34 | 55.4 | 36.1 | 8.5 |
| 43 | 0.000 | 0.000 | 23 | 62.3 | 23.6 | 14.1 |
| 44 | 0.000 | 0.000 | 23 | 49.4 | 39.1 | 11.5 |
| 45 | 0.067 | 0.000 | 16 | 62.8 | 23.3 | 13.9 |
| 46 | 0.067 | 0.000 | 7 | 52.1 | 40.5 | 7.4 |
| **mean** | **0.027** | **0.000** | **21** | **56.4** | **32.5** | **11.1** |

Child death range: ticks 15–30, mean 19.1

**Confirmed working (trace seed=42)**:
- Ticks 0–3: FORAGE, picks food (held_food=1)
- Ticks 4–7: CARE, navigates toward own child (dist 4→0)
- Tick 8: Feeds child at dist=0 (child energy 0.507 → 0.960)
- Tick 9: SELF eats held_food (mother energy 0.640 → 1.0)
- Ticks 10+: FORAGE resumes; second cycle fails (see below)

---

## Remaining Issue — Forage threshold prevents timely second-cycle care

**What happens**: After feeding, child distress drops to ~0. CARE = 0. FORAGE dominates
for ~10 ticks (forage_cue ≈ 0.667 with perception_radius=15). Child drifts to dist=8–12
during this foraging window. CARE only beats FORAGE when distress > 0.667 (≈5 ticks before
child death). By then child is too far to reach in time → child dies on second cycle.

**Root cause**: percept15 BALANCED ecology was calibrated for Phase 2 (mothers only).
`perception_radius=15` keeps forage_cue persistently high. CARE threshold (> 0.667) is
only reached when child is nearly dead — navigation from dist=10 takes longer than 5 ticks.

**This is not a code bug.** The care loop is mechanically correct. The ecology needs
adjustment so that CARE fires earlier in the hunger cycle.

---

## Next Step

Reduce `food_perception_radius` so forage_cue drops and CARE fires at lower child distress.
`food_perception_radius` is already a separate Config parameter — no architecture change needed.
At radius=8: forage_cue ≈ 1 − avg_dist/8. This allows CARE to compete earlier and gives the
mother time to navigate to child before it dies on the second cycle.
