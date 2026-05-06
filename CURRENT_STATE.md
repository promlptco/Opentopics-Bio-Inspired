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

Last updated: 2026-05-06 (V3 branch)

---

## Phase 3a Status: BLOCKED — awaiting food calibration

Phase 3a (Motivation Sweep) cannot run until `init_food` is re-calibrated for Phase 3a's mechanics.

---

## Phase 3a Bugs Fixed (2026-05-06)

### Bug 1 — `mother_max_age=400` kills all survivors at tick 399
- **Cause**: Config default `mother_max_age=400` equals `max_ticks=400`. Phase 3's `Simulation.step()` calls `mother.die()` when `age >= 400`, which fires on every survivor at the very last tick.
- **Effect**: `mother_survival_rate = 0.0` for all 216 genomes. Phase 2's `SurvivalSimulation` has no age cap — the BALANCED ecology was calibrated without it.
- **Fix**: `mother_max_age=None` added to Phase 3a config (`experiments/phase3a_motivation_sweep/config.py`).

### Bug 2 — FORAGE domain eats food at full energy (wasted gain)
- **Cause**: Phase 3's FORAGE domain ate held food immediately after picking (energy ~0.95 → gain = `min(1.0, 0.95+0.5)−0.95 = 0.05`, not 0.5). Phase 2's SELF domain ate only when energy was low (~0.4), getting the full 0.5 gain each time. 70–90% of each food's energy was wasted in Phase 3.
- **Effect**: Phase 3 survival with BALANCED ecology = ~1/15 vs Phase 2's 6–13/15 with identical parameters.
- **Fix** (`simulation/simulation.py`): FORAGE domain = pick or navigate only (no eating). SELF domain = eat held food if available, else rest. This matches Phase 2's `SurvivalSimulation` behavior.

### Also fixed in this session
- `food_replace_on_pick: bool = True` added to `Config` as the universal 1:1 replacement default. `food_replenish_threshold_ratio` defaulted to `0.0` (burst disabled). Phase 3a config cleaned up of the workaround values.

---

## Remaining Issue — Ecological pressure from Phase 2 calibration

After both bug fixes, Phase 3a best result is:
- `mother_survival = 0.41` (below MOTHER_SURVIVAL_MIN = 0.5)
- `child_survival = 0.00` (no children mature)

**This is ecological pressure, not a code bug.** The BALANCED ecology (`init_food=40`) was designed for Phase 2 (mothers only). Phase 3a adds:
- 15 children each needing a feed every ~7 ticks to survive 200 ticks to maturity
- Feed cost: 0.03 energy per feed from mother
- Care commitment: 20-tick blocks where mothers cannot forage

The Phase 2 BALANCED ecology has no food surplus for child-rearing. Decision: increase `init_food` for Phase 3a (Option A).

---

## NEXT STEP — Phase 3 Food Calibration Sweep

**Goal**: Find minimum `init_food` where Phase 3a ecology is viable: `mother_survival >= 0.5` AND at least some children mature.

**Approach**: Extend Phase 2's `new_run.py` with `--mode phase3_food`. No new directory — reuse existing sweep infrastructure for code efficiency and scalability.

### new_config.py additions (bottom of file)

```python
# Phase 3 Food Calibration — init_food sweep with Phase 3a mechanics
PHASE3_FOOD_SWEEP_VALUES = [40, 50, 60, 70, 80, 100, 120, 150]

# Fixed conservative genome (low care, strong forage — stress-tests child survival)
PHASE3_FOOD_CAL_GENOME = {"care_w": 0.2, "forage_w": 1.0, "self_w": 1.0}

# Phase 3a mode flags — same as phase3a_motivation_sweep/config.py
PHASE3_FOOD_CAL_FLAGS = {
    "children_enabled": True, "care_enabled": True,
    "reproduction_enabled": False, "mutation_enabled": False,
    "plasticity_enabled": False, "mother_max_age": None,
    "infant_starvation_multiplier": 1.0, "init_mothers": 15,
}

# Pass thresholds (same as Phase 3a)
PHASE3_MOTHER_SURVIVAL_MIN = 0.5
PHASE3_MOTHER_ENERGY_MIN   = 0.1
PHASE3_CHILD_SURVIVAL_MIN  = 0.0   # any child matured counts
PHASE3_CARE_CHOICE_MIN     = 0.05
```

### new_run.py additions (3 new functions after `_run_task`, mode handler in `run_experiment`)

```python
def make_phase3_config(params, duration):
    cfg = make_config(params, duration)          # reuse Phase 2 config builder
    for k, v in PHASE3_FOOD_CAL_FLAGS.items():
        setattr(cfg, k, v)
    cfg.care_weight   = PHASE3_FOOD_CAL_GENOME["care_w"]
    cfg.forage_weight = PHASE3_FOOD_CAL_GENOME["forage_w"]
    cfg.self_weight   = PHASE3_FOOD_CAL_GENOME["self_w"]
    return cfg

def run_one_phase3(params, seed, duration):
    from simulation.simulation import Simulation
    cfg = dataclasses.replace(make_phase3_config(params, duration), seed=seed)
    sim = Simulation(cfg); sim.run()
    alive_m = [m for m in sim.mothers if m.alive]
    matured = sum(1 for r in sim.logger.death_records
                  if r.agent_type == "child" and r.cause == "matured")
    tc = len(sim.logger.choice_records)
    cc = sum(1 for r in sim.logger.choice_records if r.winner_domain == "care")
    return {
        "init_food":            params["init_food"],
        "seed":                 seed,
        "mother_survival_rate": round(len(alive_m) / cfg.init_mothers, 4),
        "child_survival_rate":  round(matured / cfg.init_mothers, 4),
        "mean_mother_energy":   round(sum(m.energy for m in alive_m)/len(alive_m) if alive_m else 0.0, 4),
        "care_choice_rate":     round(cc / tc if tc else 0.0, 4),
    }

def _run_task_phase3(task):
    params, seed, duration = task
    return run_one_phase3(params, seed, duration)
```

Mode handler in `run_experiment` (alongside `"sweep"`, `"pipeline"`, `"single"`):
- Builds task list: `[({init_food: v}, seed, duration) for v in PHASE3_FOOD_SWEEP_VALUES for seed in seeds]`
- Runs via ProcessPoolExecutor with `_run_task_phase3`
- Aggregates raw rows → per-`init_food` mean ± SD
- Saves `food_sweep_raw.csv`, `food_sweep_agg.csv`, `selected_init_food.json`, `survival_vs_food.png`
- Picks minimum `init_food` where `mother_survival_rate >= PHASE3_MOTHER_SURVIVAL_MIN`

CLI:
```
python -m experiments.phase2_survival_minimal.new_run --mode phase3_food --duration 400 --repeats 15 --workers 8
```

### Output directory
```
outputs/phase3_food_calibration/{timestamp}_food_sweep/
├── food_sweep_raw.csv
├── food_sweep_agg.csv
├── selected_init_food.json    # {"recommended_init_food": N}
└── survival_vs_food.png
```

### After calibration — return to Phase 3a
Update `experiments/phase3a_motivation_sweep/config.py`:
- Keep loading ecology params from Phase 2 BALANCED JSON
- Override `init_food` from `selected_init_food.json`
- Re-run Phase 3a sweep: `python -m experiments.phase3a_motivation_sweep.run --seeds 15 --workers 8`

---

## Phase 3a Files (current state)

| File | Status |
|------|--------|
| `experiments/phase3a_motivation_sweep/config.py` | Bug 1+2 fixed; awaiting food calibration |
| `experiments/phase3a_motivation_sweep/run.py` | Ready |
| `experiments/phase3a_motivation_sweep/plot.py` | Ready |
| `simulation/simulation.py` | Bug 2 fixed (eat moved to SELF domain) |
| `config.py` | `food_replace_on_pick=True` added |
