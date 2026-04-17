# Phase 1 — Mechanics Tests Report

**Status:** ✅ COMPLETE — 17/17 tests passed  
**Seed:** 42 (single seed — validation only)

---

## Results

### Test 01 · Mutation (4 tests)

| Test | Key Result |
|---|---|
| Changes values | 100/100 mutations at `mutation_rate=1.0` |
| Stays in bounds | 1,000 iterations from extreme values — all 5 fields in [0,1] |
| Distribution | All 5 fields: mean ~0.50, stdev ~0.05 — consistent with N(0, σ=0.05) |
| Sigma sensitivity | σ=0.01→0.0103, σ=0.05→0.0501, σ=0.10→0.0986 — monotonic, no distortion |

**Bug caught:** implementation used σ=0.1 instead of σ=0.05 specified in design doc. Fixed in `Genome.mutate()`.

### Test 02 · Inheritance (3 tests)

Copy is exact across all 5 fields, independent (no aliasing), and `mutation_rate=0.0` preserves genome exactly.

### Test 03 · Reproduction (4 tests)

All three gates block correctly — energy threshold, child ownership, and cooldown. Cooldown floors at 0 and does not go negative.

### Test 04 · Population Stability (4 tests)

| Test | Result |
|---|---|
| No extinction | 20 alive at tick 100 |
| No explosion | 30 total at tick 100 (threshold=50) |
| Deterministic | Run 1 = Run 2 = 5 survivors (seed=12345) |
| Starvation | 0 alive at tick 200 with food and recovery removed |

---

## Verdict

All genetic operators and simulation mechanics verified correct. One bug found and fixed (σ mismatch). Engine ready for Phase 2.

---

### Phase 2 · Implementation Notes

**Status:** Pipeline implemented. Run with `--mode pipeline --workers N`.

**Code structure:**

| File | Role |
|---|---|
| `run.py` | Simulation loop, pipeline orchestration, selection, diagnostic plot dispatch |
| `config.py` | All parameters: `BALANCED_BASELINE`, `SELECTION_TARGETS`, sweep ranges, plot switches |
| `plot.py` | All plotting functions, CSV/JSON saving, `summarize_repeats` |
| `sensitivity_sweep.py` | Standalone OVAT runner (also called internally by pipeline Step 2) |

**Motivation / action space (Phase 2 — no child, no care):**

| Level | Values |
|---|---|
| Motivation | `FORAGE`, `SELF` |
| Action | `MOVE`, `PICK`, `EAT`, `REST` |
| Failed | `FAILED_FORAGE`, `FAILED_SELF` |

**Diagnostic plots generated per condition** (all toggleable in `config.py`):

| File | What it shows |
|---|---|
| `validation_<cond>.png` | Energy + population trajectory (always generated) |
| `action_selection_<cond>.png` | MOVE / PICK / EAT / REST rates over time |
| `motivation_selection_<cond>.png` | FORAGE / SELF rates over time |
| `stacked_action_failed_<cond>.png` | Realized actions + failed selections stacked |
| `correlation_failed_forage_energy_<cond>.png` | FAILED_FORAGE rate vs energy decay |
| `state_space_energy_action_<cond>.png` | Energy vs action/motivation scatter |
| `food_consumption_rate_<cond>.png` | PICK / EAT rates + food availability |
| `spatial_heatmap_population_<cond>.png` | Mother visitation heatmap |
| `energy_expenditure_breakdown_<cond>.png` | hunger_loss / move_loss / eat_gain / net |
| `homeostatic_balance_<cond>.png` | Energy vs fatigue dynamics |

**Key design decision (pipeline Step 4):** Base params for the validation grid use the synthetic baseline, not the combined cliff-edge values. Combining all individually-detected cliff-edge values simultaneously (high hunger + high move_cost + low eat_gain) creates a super-harsh operating point causing total extinction across the food axis. Cliff-edge detection (Step 3) reports sensitivity results but does not lock the operating point.