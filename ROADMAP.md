# ROADMAP — Opentopics Bio-Inspired Simulation

Research question: "What are the minimum ecological and motivational conditions for the emergence of kin-biased maternal care in a population of evolving neuroendocrine agents?"

Last updated: 2026-05-07 (V3 branch)

---

## Scientific Narrative — Why we ran each phase in this order

The experiment is built as a progressive elimination argument. Each phase tests one candidate explanation for why child survival fails, rules it out with data, and hands off a tighter question to the next phase.

**Phase 3 — "Maybe food density is the problem."**
We added children to the Phase 2 ecology and swept `init_food` across 7 levels (40→900) with everything else fixed — including ISM=2.33 (infants hunger 2.33× faster than adults) and all motivation weights = 1.0 (unbiased). Result: C_matr = 0 at every food level. Even at 6× the baseline food, children died in ~21 ticks on average, against a maturity target of 200. Food availability is not the bottleneck.

**Phase 3b — "Maybe ISM=2.33 is too harsh. What if we relax all ecological parameters at once?"**
We ran a full 3D sweep: ISM × eat_gain × init_food (64 combos × 5 seeds = 320 runs), still with weights = 1.0. Result: C_matr = 0 across all 64 combos. The best we achieved was child_death_mu = 48 ticks (ISM=1.2, eat_gain=0.70, init_food=600) — still 4× short of maturity. Ecology alone cannot close the gap.

**Analysis — Why both failed: the care trap.**
With tau=0.1 and equal weights (1.0), CARE only wins the softmax when child distress > forage_cue ≈ 0.86. That means the child is at ~14% energy, roughly 4 ticks from starvation. By that point, the mother has no food in hand — she has not foraged recently because FORAGE and CARE competed as equals and FORAGE was winning while the child was less urgent. The mother arrives, finds she cannot feed (held_food = 0), releases commitment, and the cycle repeats. The child starves. The core problem is that FORAGE must *precede* CARE (pick food first, then deliver), but equal weights make them compete simultaneously rather than sequence them.

**Phase 4 — The only remaining lever: motivational bias.**
Ecological parameters cannot fix a sequencing problem caused by the motivational system. The minimum necessary intervention is `care_weight > 1.0`. A higher care_weight shifts the softmax threshold earlier — CARE fires when the child still has energy to spare, the mother has food from prior foraging, and the feed succeeds. Phase 4 sweeps care_weight to find the minimum bias at which child maturation becomes possible.

---

## Phase 1 — Mechanics Tests ✅ DONE

**Goal:** Verify all core agent mechanics before any ecological experiment.

**Experiments:** `experiments/phase1_mechanics_tests/`

**Tests:**
| Test | What it checks | Result |
|------|----------------|--------|
| `test_01_mutation.py` | Genome mutation — values stay in [0,1] | PASS |
| `test_02_inheritance.py` | Child genome is copy of parent before mutation | PASS |
| `test_03_reproduction.py` | Energy deducted, cooldown applied, child spawns nearby | PASS |
| `test_04_population_stability.py` | No immediate extinction or explosion | PASS |
| `test_05_stochasticity_identity.py` | Same seed → identical action sequences | PASS |
| `test_06_softmax_calibration.py` | Softmax matches Boltzmann equation | PASS |

**Result:** All 6 tests passed. Core mechanics confirmed correct.

---

## Phase 2 — Survival-Minimal Ecological Baseline ✅ DONE

**Goal:** Find three canonical ecological parameter sets (HARSH / BALANCED / EASY) for mother-only survival (no children, no care). These become the locked starting conditions for all subsequent phases.

**Experiments:** `experiments/phase2_survival_minimal/`

**Method:** OVAT sweep (init_food, eat_gain, move_cost) + full 3D grid selection, N=10 seeds, 1000 ticks.

**Result — Locked ecological regimes:**

| Condition | move_cost | eat_gain | init_food | M_surv | perception_radius |
|-----------|-----------|----------|-----------|--------|-------------------|
| HARSH | 0.05 | 0.80 | 80 | 24.7% | 15 |
| BALANCED | 0.01 | 0.50 | 40 | 62.4% | 15 |
| EASY | 0.005 | 0.50 | 80 | 91.6% | 15 |

Source: `outputs/phase2_survival_minimal/pin_auto_400_percept15_repeat3_validation_selected_baselines/selected_ecologies.json`

**Conclusion:** Monotonic survival gradient confirmed (HARSH < BALANCED < EASY). Phase 2 BALANCED locked as the child phase starting point.

---

## Phase 3 — init_food Sweep (Children Added) ✅ DONE

**Goal:** "Can food density alone, with unbiased motivation weights (all = 1.0) and ISM = 2.33, produce child maturation?"

**Experiments:** `experiments/phase3_sweep/`

**Method:** 7 init_food values × 10 seeds = 70 runs. Used percept8 BALANCED ecology from Phase 2 (perception_radius=8 override). ISM fixed at 35/15 ≈ 2.33.

**Result:**

| init_food | M_surv | C_matr | child_death_mu |
|-----------|--------|--------|----------------|
| 40–900 (all) | 0–57% | **0.000** | 17–21 ticks |

**Conclusion:** No — food density alone cannot produce child maturation. Maximum observed feeds/child ≈ 2.1 vs 62 needed at ISM=2.33. The bottleneck is cycle time, not food availability.

**Fixes applied this phase:**
- Fix A: Clear stale commitment when committed child dies
- Fix B: Cap held_food=1; suppress forage_cue when provisioned
- Fix C: Kin-directed care (own child priority — Hamilton r-bias foundation)
- Fix D: Outcome-based commitment (release when child.hunger < 0.3)
- Fix E: feed_child() requires held_food > 0 (energy conservation)
- Fix (distress): hunger-only infant distress (removed separation component)

---

## Phase 3b — Ecological Calibration (ISM × eat_gain × init_food Sweep) ✅ DONE

**Goal:** "Can ecologically plausible parameters, sweeping ISM, produce child maturation with unbiased weights?"

**Experiments:** `experiments/phase3b_calibration/`

**Method:** Full 3D grid (ISM [1.2, 1.5, 2.0, 2.33] × eat_gain [0.20, 0.30, 0.50, 0.70] × init_food [100, 300, 600, 900]) × 5 seeds = 320 runs. Plus OVAT sets A/B/C (5 seeds each).

**Result:**

| | C_matr | child_death_mu range | CHILD_SURVIVAL_POSSIBLE |
|--|--------|---------------------|------------------------|
| All 64 combos | **0.000** | 18–48 ticks | **False** |

BEST_ECOLOGICAL (highest child_death_mu): ISM=1.2, eat_gain=0.70, init_food=600 → child_death_mu=48.3, M_surv=0.133

Source: `outputs/phase3b_calibration/selected_ecologies.json`

**ISM paradox discovered:** Higher ISM kills children faster → ends care trap sooner → mothers survive better. Lower ISM traps mothers longer in the care loop → mothers starve.

**Care trap mechanism:** With tau=0.1 and all weights=1.0, forage_cue ≈ 0.86 at init_food=600. CARE only wins softmax when distress > 0.86 (child at ~14% energy, ~4 ticks from starvation). At that point, mother has no held_food (FORAGE was suppressed by CARE winning). Arrives empty → commitment releases → loop. Child starves in <50 ticks. No combo allows the sequential FORAGE→CARE chain needed for feeding.

**Conclusion:** Ecology alone cannot rescue child maturation. Motivational bias (`care_weight > 1.0`) is necessary and sufficient.

---

## Phase 4 — Motivation Weight Sweep (care_weight bias) 🔲 PLANNED

**Goal:** Find the minimum `care_weight` that enables child maturation at BEST_ECOLOGICAL params (ISM=1.2, eat_gain=0.70, init_food=600).

**Scientific rationale:** With care_weight=2.0, CARE wins softmax when distress > 0.43 (child at 57% energy, ~15 ticks into life). Mother has been foraging freely for 15 ticks → has held_food=1. Delivers food → child resets → cycle repeats ~13 times in 200 ticks. feeds_needed at ISM=1.2, eat_gain=0.70 ≈ 8.4. 13 > 8.4 → child survives.

**Planned sweep:** `care_weight` ∈ [1.0, 1.2, 1.5, 2.0, 2.5, 3.0] × OVAT over forage_weight and self_weight.

**Primary metric:** C_matr (child maturation rate). **Secondary:** M_surv, feeds/child, CARE%.

*Note: Phase 4 design is planned but not yet implemented. Implementation correctness not yet verified.*

---

## Phase 5 — Spatial Thermoregulation (warmth_factor) 🔲 PLANNED

**Goal:** Enable `warmth_factor > 0`. Test whether passive maternal proximity reduces child hunger_rate enough to supplement motivational bias from Phase 4.

**Dependency:** Phase 4 VIABLE regime required as baseline.

*Note: Not yet implemented. Implementation correctness not yet verified.*

---

## Phase 6 — Evolution (Reproduction + Mutation, Fixed Weights) 🔲 PLANNED

**Goal:** Enable `reproduction_enabled = True`, `mutation_enabled = True`. Run multi-generation evolution with weights fixed at Phase 4 VIABLE values. Establish population genetic baseline before plasticity.

**Scientific focus:** Does care_weight remain stable under selection? Does the VIABLE threshold evolve higher than the Phase 4 minimum?

*Note: Not yet implemented. Implementation correctness not yet verified.*

---

## Phase 7 — Baldwin Effect (Plasticity Enabled) 🔲 PLANNED

**Goal:** Enable `plasticity_enabled = True`. Mother's `expressed_care_weight` can shift via `plastic_update()` within a lifetime. Track genetic assimilation: `expressed_care_weight` rises first (learning), `genome.care_weight` catches up (genetic), `learning_rate` may decline.

**Signatures to measure:**
- `expressed_care_weight` trajectory vs `genome.care_weight` trajectory
- `learning_rate` evolution under assimilation pressure
- Generation at which `expressed_care_weight ≈ genome.care_weight` (assimilation point)

*Note: Not yet implemented. Implementation correctness not yet verified.*

---

## Phase 8 — Plasticity Noise & Genetic Lock 🔲 PLANNED

**Goal:** Enable `plasticity_noise_sigma > 0` and `lock_learning_rate` flag. Noisy learning degrades phenotypic plasticity reliability → selection favors genetic encoding over learned adjustment. This is the Hinton & Nowlan (1987) mechanism.

*Note: Not yet implemented. Implementation correctness not yet verified.*

---

## Summary Table

| Phase | Name | Status | Key Result |
|-------|------|--------|------------|
| 1 | Mechanics Tests | ✅ DONE | All 6 tests pass |
| 2 | Survival-Minimal Baseline | ✅ DONE | HARSH/BALANCED/EASY locked |
| 3 | init_food Sweep | ✅ DONE | C_matr = 0 at all food levels |
| 3b | Ecological Calibration | ✅ DONE | C_matr = 0, BEST_ECOLOGICAL: ISM=1.2, eat_gain=0.70, init_food=600 |
| 4 | Motivation Weight Sweep | 🔲 PLANNED | Minimum care_weight for child survival |
| 5 | Spatial Thermoregulation | 🔲 PLANNED | warmth_factor as supplementary care |
| 6 | Evolution (Fixed Weights) | 🔲 PLANNED | Genetic baseline before plasticity |
| 7 | Baldwin Effect | 🔲 PLANNED | Phenotypic → genetic assimilation |
| 8 | Plasticity Noise | 🔲 PLANNED | Hinton-Nowlan genetic lock mechanism |
