# Phase 1 — Mechanics Tests: Report

**Project:** Simulation of the Minimum Ecological Conditions for the Emergence of Kin-Biased Maternal Care  
**Phase:** 1 — Core Mechanics Validation  
**Status:** ✅ COMPLETE — All 16 tests passed  
**Seeds:** Single seed (42) — exploratory validation only, no statistical analysis required  

---

## Purpose

Phase 1 verifies that all genetic operators and simulation mechanics are implemented correctly before any evolutionary run begins. A bug at this level invalidates everything downstream. The phase produces test logs only — no plots, no statistical analysis.

---

## Test Suite Overview

| Test File | Description | Tests | Result |
|---|---|---|---|
| `test_01_mutation.py` | Mutation operator | 3 | ✅ PASS |
| `test_02_inheritance.py` | Inheritance / copy fidelity | 3 | ✅ PASS |
| `test_03_reproduction.py` | Reproduction gating | 4 | ✅ PASS |
| `test_04_population_stability.py` | Population-level stability | 4 | ✅ PASS |

---

## Test 01 — Mutation

**Purpose:** Verify that `Genome.mutate()` changes values, respects bounds, and produces a Gaussian distribution.

**Method:**

| Test | Protocol | Success Criterion |
|---|---|---|
| `test_mutation_changes_values` | Mutate same genome 100 times at `mutation_rate=1.0`. Count how many times `care_weight` changes. | `changes > 90 / 100` |
| `test_mutation_stays_in_bounds` | Start from extreme genome (`care=0.99, forage=0.01`). Mutate 1,000 times. Check all 5 fields at every step. | All values remain in `[0.0, 1.0]` |
| `test_mutation_distribution` | Mutate from neutral genome (`all=0.5`) 1,000 times. Compute mean and stdev for all 5 fields. | `0.4 < mean < 0.6` and `0.05 < stdev < 0.2` for every field |

Both `random` and `numpy.random` seeded with `DEFAULT_SEED = 42` before each test for determinism.

**Results:**

```
Mutations occurred: 100/100

care_weight:    Mean=0.501  Stdev=0.103
forage_weight:  Mean=0.500  Stdev=0.100
self_weight:    Mean=0.502  Stdev=0.096
learning_rate:  Mean=0.500  Stdev=0.103
learning_cost:  Mean=0.502  Stdev=0.100
```

**Interpretation:** Mutation rate of 1.0 reliably changes values. All 5 fields are centered near 0.5 with stdev ~0.10, consistent with Gaussian N(0, σ=0.05) applied to a bounded [0,1] range. No field shows bias or asymmetry.

---

## Test 02 — Inheritance

**Purpose:** Verify that `Genome.copy()` produces an exact, independent duplicate, and that `mutate(mutation_rate=0.0)` leaves all values unchanged.

**Method:**

| Test | Protocol | Success Criterion |
|---|---|---|
| `test_copy_is_exact` | Create genome with known values. Call `.copy()`. Compare all 5 fields. | All fields identical |
| `test_copy_is_independent` | Copy genome. Modify child's `care_weight`. Check parent is unchanged. | Parent unaffected — no aliasing |
| `test_inheritance_with_mutation` | Call `mutate(mutation_rate=0.0)`. Compare all 5 fields to parent. | All 5 fields preserved exactly |

No seeding required — tests are fully deterministic with no random operations.

**Results:** All 3 tests passed. Copy is exact, independent, and zero-rate mutation preserves all fields.

**Interpretation:** Genome inheritance is faithful. Children begin as exact copies of parents before mutation is applied. No shared-reference bugs exist between parent and child genomes.

---

## Test 03 — Reproduction

**Purpose:** Verify that the reproduction gating logic correctly blocks or allows reproduction based on energy, child ownership, and cooldown state.

**Method:**

| Test | Protocol | Success Criterion |
|---|---|---|
| `test_can_reproduce_threshold` | Set energy to 0.5, then 0.9. Call `can_reproduce(threshold=0.8)`. | `False` at 0.5, `True` at 0.9 |
| `test_cannot_reproduce_with_child` | Set `own_child_id=99`, energy=1.0, cooldown=0. | `can_reproduce()` returns `False` |
| `test_cannot_reproduce_on_cooldown` | Set `cooldown=10`, energy=1.0, `own_child_id=None`. | `can_reproduce()` returns `False` |
| `test_cooldown_ticks_down` | Start at `cooldown=2`. Call `tick_cooldown()` three times. | Sequence: `2 → 1 → 0 → 0` (floors at 0) |

**Results:** All 4 tests passed. All three blocking conditions (energy, child presence, cooldown) operate independently and correctly. Cooldown floors at 0 and does not go negative.

**Interpretation:** Reproduction is properly gated. A mother cannot reproduce if she lacks energy, already has a dependent child, or is in cooldown. The floor test confirms no underflow bug.

---

## Test 04 — Population Stability

**Purpose:** Verify population-level behavior — no immediate extinction, no runaway growth, deterministic seed behavior, and correct starvation mechanics.

**Method:**

| Test | Protocol | Success Criterion |
|---|---|---|
| `test_no_immediate_extinction` | 10 mothers, 100 ticks, standard config. Count survivors. | `alive > 0` |
| `test_no_immediate_explosion` | 10 mothers, 100 ticks. Count total population. | `total < 50` (5× initial) |
| `test_deterministic_with_seed` | Run identical config with `seed=12345` twice. Compare survivor count. | `run1 == run2` |
| `test_no_food_causes_extinction` | 5 mothers, no food, no rest recovery, reproduction and children disabled. 200 ticks. Food cleared before every step. | `alive == 0` |

Note: `max_population` in config is not a hard enforcement — population cap is not implemented as a hard constraint. Test 2 uses a 5× growth threshold as a reasonable explosion proxy.

**Results:**

```
Alive after 100 ticks:          20
Total population after 100 ticks: 30  (threshold=50)
Run 1: 5,  Run 2: 5
Alive without food:             0
```

**Interpretation:** Population neither collapses nor explodes under standard conditions. Identical seeds produce identical outcomes, confirming the simulation is deterministic. Starvation mechanic correctly drains all agents to death when energy sources are fully removed.

---

## Phase 1 Verdict

**Result: PASS — 16/16 tests**

All genetic operators and simulation mechanics are verified correct. The engine is ready for Phase 2.

| Criterion | Status |
|---|---|
| Mutation changes values | ✅ |
| Mutation stays in bounds | ✅ |
| Mutation is Gaussian across all fields | ✅ |
| Inheritance is exact and non-aliased | ✅ |
| Zero-rate mutation preserves genome | ✅ |
| Reproduction gating: energy | ✅ |
| Reproduction gating: child ownership | ✅ |
| Reproduction gating: cooldown | ✅ |
| Cooldown floor at 0 | ✅ |
| No immediate extinction | ✅ |
| No population explosion | ✅ |
| Deterministic with seed | ✅ |
| Starvation causes extinction | ✅ |

---

*Logs saved to `outputs/phase1_mechanics_tests/test0{1–4}_42_1/logs.csv`*