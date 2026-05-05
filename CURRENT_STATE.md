# Phase 2 Current State

Last updated: 2026-05-05

---

## What Phase 2 Is

Mother-only ecological survival baseline. No children, no care, no reproduction, no mutation, no plasticity.

Goal: find three canonical ecological parameter sets (HARSH / BALANCED / EASY) that produce distinct survival pressures. These become the starting conditions for Phase 3 evolution.

Motivations active: FORAGE, SELF  
Actions active: MOVE, PICK, EAT, REST

---

## Mechanics Fixes Applied (this session)

| Issue | Fix |
|-------|-----|
| Batch food replenishment caused tragedy-of-commons — all conditions converged to same energy | Replaced with **1:1 food replacement**: every PICK spawns one new food at a random position. `init_food` is now the permanent food density on the map. |
| Survivor bias in energy metric — HARSH survivors (elite) appeared healthier than EASY agents | Changed denominator from `len(alive_now)` to `init_mothers` (12). Energy is now **population-weighted**: dead agents count as 0. |
| `max_abs_pop_slope=0.005` constraint excluded all food values except food=100 | Removed slope constraints from BALANCED selection. With 1:1 replacement, slow population decline (slope -0.005 to -0.015) is inherent — not a failure mode. |

---

## Food Ecology — 1:1 Replacement

With 1:1 replacement, the survival curve is **humped** (not monotonic):

| init_food | Survival (sweep seeds) | Pop-weighted tail energy | Zone |
|-----------|----------------------|--------------------------|------|
| 50 | 25% (3.0/12) | 0.110 | HARSH |
| 60 | 44% (5.3/12) | 0.212 | transition |
| 78 | 58% (7.0/12) | 0.279 | BALANCED |
| 100 | **81% (9.67/12)** | **0.331** | **EASY (peak)** |
| 134 | 64% (7.67/12) | 0.262 | declining |
| 182 | 67% (8.0/12) | 0.263 | declining |

Above food=100, survival **drops** because FORAGE motivation dominates with high food density — agents constantly pick food but rarely switch to SELF to eat, so they slowly starve while holding food.

**Canonical baselines:**
- HARSH = food=50 (25% survival)
- BALANCED = food=78 (58% survival)
- EASY = food=100 (81% survival, ecological peak)

---

## Fixed Parameters

| Parameter | Value | Reason |
|-----------|-------|--------|
| `hunger_rate` | 1/35 = 0.0286 | Locked: adult starves in 35 ticks = 7 days |
| `perception_radius` | 15.0 | 30% of 50x50 map |
| `move_cost` | 0.001 | OVAT Set B: flat lever |
| `rest_recovery` | 0.005 | OVAT Set E: flat lever |
| `eat_gain` | 0.25 | Swept default; 1 food = 8.7 ticks of energy |
| `fatigue_rate` | 0.01 | Root Config default |
| `init_mothers` | 12 | Matches all phases |
| `initial_energy` | 1.0 | Full energy at birth |
| Grid | 50x50 | Standard Phase 2+ |

**Energy equilibrium note:** Agents' per-survivor energy equilibrates at ~0.35-0.45 regardless of condition — determined by eat_gain=0.25 and hunger_rate=1/35. The **ecological gradient shows primarily in survival rate, not per-survivor energy**. This is ecologically realistic: stress manifests as mortality, not as lower metabolic state of survivors. Population-weighted energy (divides by 12) does show a clear gradient: HARSH=0.11, BALANCED=0.24, EASY=0.30.

---

## Energy Metric

```python
# run.py line 354 — population-weighted energy
avg_energy = sum(m.energy for m in alive_now) / self.config.init_mothers
```

Dead agents contribute 0. This avoids survivor bias (where HARSH survivors appeared healthier than EASY agents because the weakest had already died). The metric represents "expected energy of a randomly chosen starting agent."

---

## Selection Targets (current)

| Condition | Survival hard bounds | Energy hard bounds | Sort preference |
|-----------|---------------------|--------------------|-----------------|
| HARSH | 1.2 <= pop <= 4.0 | [0.02, 0.20] | closest to target_pop=3.0 |
| BALANCED | pop >= 5.5 | [0.18, 0.38] | **lowest init_food** (food=78 over food=100) |
| EASY | pop >= 7.5 | >= 0.22 | highest tail_energy (food=100 over food=78) |

Slope constraints removed from BALANCED. Energy bounds overlap by design — survival rate is the primary separator; energy is a secondary sanity check.

---

## Step 1 — OVAT Sweep

Run previously with batch replenishment. Results are now superseded by the 1:1 replacement ecology. The sweep grid in `candidate_configs("sweep")` has been manually calibrated based on the measured humped curve:

```python
"init_food": [50, 60, 78, 100, 134, 182]
```

Do NOT re-run `sensitivity_sweep.py` before completing Step 2 — it would auto-overwrite this calibrated grid.

---

## Step 2 — Validate and Select Canonical Baselines (PENDING — running now)

**Command:**
```
python -m experiments.phase2_survival_minimal.new_run --mode pipeline --duration 1000 --workers 4
```

**Expected selection:**
- HARSH: food=50 (strict pass predicted)
- BALANCED: food=78 (first in pool by init_food; strict pass predicted)
- EASY: food=100 (first in pool by highest energy; strict pass predicted)

**Expected gradient:**
| Condition | Survival | Pop-weighted tail energy |
|-----------|----------|--------------------------|
| HARSH | ~25% | ~0.11 |
| BALANCED | ~55-65% | ~0.22-0.28 |
| EASY | ~70-80% | ~0.28-0.33 |

**Risk:** If food=78 validation (15 seeds) gives pop < 5.5/12, BALANCED falls back to food=100 and both BALANCED and EASY would be the same config. Check `selection_status` in `auto_baseline_summary.json` — should be `validated_pass` for all three.

---

## Step 3 — Diagnostic Plots (auto-generated inside Step 2)

12 plots per condition saved alongside the JSON:
- `validation_<name>.png` — population-weighted energy + population trajectories
- `action_selection_<name>.png` — MOVE/PICK/EAT/REST rates over time
- `motivation_selection_<name>.png` — FORAGE/SELF rates over time
- `failed_selection_<name>.png` — failed action rates
- `stacked_action_failed_<name>.png` — stacked area chart
- `rate_sum_check_<name>.png` — rate normalization check
- `correlation_failed_forage_energy_<name>.png`
- `state_space_energy_action_<name>.png`
- `food_consumption_rate_<name>.png`
- `spatial_heatmap_population_<name>.png`
- `energy_expenditure_breakdown_<name>.png`
- `homeostatic_balance_<name>.png`

---

## Key Files

| File | Role |
|------|------|
| `experiments/phase2_survival_minimal/new_run.py` | Main entry point; 8-step pipeline, sweep, and single modes |
| `experiments/phase2_survival_minimal/new_config.py` | Sweep grid, selection targets, BALANCED_BASELINE, SENSITIVITY_SWEEPS |
| `experiments/phase2_survival_minimal/new_plot.py` | All plot functions |
| `experiments/phase2_survival_minimal/new_sensitivity.py` | OVAT standalone runner + find_food_anchor |
| `agents/mother.py` | MotherAgent with `choose_motivation()` |
| `config.py` (root) | Global defaults |

---

## Branch / Git

Branch: `V3`
