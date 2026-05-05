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

## Branch / Git

Branch: `V3`
