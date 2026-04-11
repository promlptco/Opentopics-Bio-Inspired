# Session Context — Opentopics-Bio-Inspired

> Paste this file path to Claude Code at the start of a new session:
> `Read C:\Users\User\Desktop\FIBO_Study\3Y_2\FRA361_OPENTOPICS\Opentopics-Bio-Inspired\SESSION_CONTEXT.md`

---

## What This Project Is

FRA361 Open Topics (FIBO, 3rd year sem 2).
OOP grid-world simulation studying emergence of maternal care via evolutionary game theory.
Pipeline: survival → maternal → plasticity → Hamilton-like analysis.
**Future thesis continuation** — must be scientifically rigorous.

---

## Hamilton's Rule Framework (rB > C)

| Term | Definition | In This Simulation |
|------|-----------|-------------------|
| **r** | Coefficient of relatedness | `2^(-d)`: own child = 0.5, grandchild = 0.25. Post-hoc only — agents cannot observe r. |
| **B_individual** | Direct benefit to child | `hunger_reduced` per care event |
| **B_social** | Indirect benefit to lineage (inclusive fitness) | Lineage reproductive success = total descendants at end of run |
| **C** | Cost to mother | `feed_cost + move_cost` (energy spent) |

**Key principles:**
- Hamilton's `rB > C` applies to own-lineage care (r > 0) only
- Foreign-lineage care (r = 0) is a rare by-product of proximity-based decisions — reported as frequency only, not Hamilton-analyzed
- No hard-coding of care targets — environment (proximity at birth) naturally creates kin bias
- Mothers pick highest-distress child from ALL visible children — emergence, not programming

---

## All Bugs Fixed

| # | Bug | File |
|---|-----|------|
| 1 | Maturation gave default genome (broke evolution) | simulation.py |
| 2 | Maturation corrupted `occupied` set | simulation.py |
| 3 | `_nearby_pos` fell back to parent's cell | simulation.py |
| 4 | `_log_choice` recomputed domain ignoring commitment | simulation.py |
| 5 | Config flags not enforced | simulation.py |
| 6 | Goal commitment hardcoded to 5 ticks (should be 3–5) | simulation.py |
| 7 | `phase1_survival/run.py` was empty | phase1_survival/run.py |
| 8 | `initialize_with_genomes()` didn't exist | simulation.py |
| 9 | Phase2 loaded genomes from phase1 (wrong) | phase2_zeroshot/run.py |
| 10 | Phase3 never saved `top_genomes.json` | phase3_maternal/run.py |
| 11 | Phase3 had no stage support | phase3_maternal/run.py |
| 12 | `stress` never updated — M_self half-broken | agents/mother.py |
| 13 | `population_history.json` never saved → plots silently skipped | phase3_maternal/run.py |
| 14 | `_log_choice` re-called `choose_child` ignoring commitment → wrong target logged | simulation.py |
| 15 | `init_mothers=30, init_food=25` → 0.83 food/mother → total extinction | phase3_maternal/run.py |
| 16 | `reproduction_enabled=False` on baselines → care only in first 100 ticks | phase3_maternal/run.py |
| 17 | No `mutation_enabled` flag → no way to fix genomes without killing reproduction | config.py, simulation.py |
| 18 | `get_step_toward` only tried 3 directions → agents froze in crowds | simulation/world.py |
| 19 | `own_child_id` never cleared on child death/maturation → mothers could only reproduce once | simulation/simulation.py |
| 20 | `fatigue` never incremented in main sim → `self` domain halved, mothers never rested | simulation/simulation.py, config.py |
| 21 | `mother_lineage_id`, `child_lineage_id`, `is_own_child` missing from CareRecord | logging_system/records.py, simulation/simulation.py, logging_system/logger.py |
| 22 | Candidate arrays in ChoiceRecord never exported to CSV | logging_system/logger.py |
| 23 | No death log → can't compute lifetime reproductive success | logging_system/records.py, logger.py, simulation.py |
| 24 | phase2_zeroshot `init_food=25, init_mothers=30` hardcoded → extinction after maturation | phase2_zeroshot/run.py |
| 25 | phase2_zeroshot no `population_history.json` → energy/population plots silently skipped | phase2_zeroshot/run.py |
| 26 | phase2_zeroshot `init_mothers=30` didn't match evolved genome count (25) | phase2_zeroshot/run.py |
| 27 | phase2_zeroshot missing `mutation_enabled=False` → genomes could drift during test | phase2_zeroshot/run.py |

---

## Config Flags (as of 2026-04-10)

| Flag | baseline_c0 | baseline_r0 | evolution | zeroshot |
|------|-------------|-------------|-----------|----------|
| children_enabled | True | True | True | True |
| care_enabled | True | True | True | True |
| plasticity_enabled | False | False | False* | False |
| reproduction_enabled | True | True | True | **False** |
| mutation_enabled | **False** | **False** | True | **False** |

*plasticity added in phase4

---

## Pathfinding

`simulation/pathfinding.py` — 5 algorithms with identical signature:
```
find_step(from_pos, to_pos, is_free, in_bounds) -> tuple[int, int]
```
1. `naive_step` — 3-direction greedy (original, can freeze)
2. `greedy_step` — all 8 neighbours, pick closest to target
3. `bfs_step` — BFS shortest hops
4. `astar_chebyshev` — A* all moves cost 1
5. `astar_octile` — A* diagonal = √2 ← **active in world.py**

To swap: change the import in `simulation/world.py`.

---

## Current Project State

| Phase | Status |
|-------|--------|
| `step1_survival_check` | VALIDATED — 6 runs, all passed |
| `phase1_survival` | PASSED — 12/12 survive, avg energy 0.910, 2026-04-08 |
| `phase3_maternal` | **Baseline-C0 FROZEN** — 2026-04-08 |
| `phase3_maternal` | **Baseline-R0 COMPLETE** — 2026-04-09 |
| `phase3_maternal` | **Evolution COMPLETE** — 2026-04-09, seeds 42–51 (10 runs) |
| `phase2_zeroshot` | **COMPLETE** — 2026-04-09, seed=42 |
| `phase4_plasticity` | **COMPLETE** — 2026-04-10, evolution + zeroshot, seed=42 |

---

## Baseline-C0 — FROZEN

**Config:** `care=0.7, forage=0.85, self=0.55`, `seed=42`
**Run dir:** `outputs/phase3_maternal/run_20260408_191406_seed42`
**Results:** 24 surviving mothers, 12 children, 1262 care events, 100% success
**Energy:** avg 0.439, stable oscillation 0.25–0.65
**Relatedness:** avg_r=0.056 (~87% foreign care, ~13% own-child)
**Care distance:** flat distribution dist 1–8 (pure distress-driven selection)
**Note:** Run pre-bugfix (#19, #20). Valid for relative comparison with R0, absolute numbers suppressed.

To watch live:
```bash
python experiments/phase3_maternal/watch.py
```

---

## Baseline-R0 — COMPLETE

**Config:** random genomes `uniform(0,1)`, `seed=42`
**Run dir:** `outputs/phase3_maternal/run_20260409_125601_seed42`
**Results:** 24 surviving mothers, 12 children, 829 care events, 100% success
**Energy:** avg 0.447, stable
**Relatedness:** avg_r=0.077 (84% foreign care, 16% own-child)
**Surviving genomes:** care_weight avg=0.365 [0.027–0.500], forage avg=0.500, self avg=0.536
**Hamilton check (own-lineage):** rB=0.034 < C=0.048 — altruistic cost even with random genomes
**Note:** Run pre-bugfix (#19, #20). Valid for relative comparison with C0, absolute numbers suppressed.

---

## Roadmap — Full Thesis Plan

### Part 1 — Core Pipeline (COMPLETE)
1. ~~Phase 1: Survival gate~~ PASSED
2. ~~Baseline-C0~~ FROZEN — fixed genomes (care=0.7, forage=0.85, self=0.55)
3. ~~Baseline-R0~~ COMPLETE — random genomes, seed=42
4. ~~Phase 3: Evolution~~ COMPLETE — seeds 42–51, care declines r=−0.178
5. ~~Phase 4: Kin-conditional Baldwin Effect~~ COMPLETE — lr swept 8/10 seeds, assimilation absent p=0.815
6. ~~Hamilton post-hoc~~ COMPLETE — rB−C≈0, 90% foreign, proximity kin bias confirmed
7. ~~Zero-shot baseline~~ COMPLETE — seed=42, 0.09069/mother-tick

### Part 1 Wrap-Up — DEFERRED (after Phase 5)
- Phase A: Code cleanup
- Phase B: Full pipeline recheck
- Phase C: First draft report
*Conclusion reframing deferred — see Scientific Reframe below. Phase 5 results will determine final conclusion.*

---

### Part 2 — Phase 5: Ecological Emergence (IN PROGRESS — 2026-04-11)
*Motivation: Phase 3–4 showed care is evolutionarily unstable when B is weak and r is diluted. Phase 5 tests whether infant dependency + natal philopatry can REVERSE the selection gradient.*

**Calibration findings (2026-04-11):**
- `infant_starvation_multiplier=3.0` (original design): evolutionary trap — selection works but population crashes during bottleneck (all runs extinct within 400–900 ticks)
- The model's decision model (`choose_domain` = argmax) requires care_weight > ~0.075 for care to ever fire at typical energy levels. True near-zero init (0–0.05) is below the operative threshold
- `mult=1.15` (calibrated): infants die at tick ~108 without care (maturity_age=100), B near-existential. Population survives, selection gradient turns POSITIVE (+24% over 5000 ticks)
- Confirmed via scan: mult=1.0→flat/slight decline, mult=1.10→slight upward, mult=1.15→clear upward (+24%)

**Phase 5 scientific claim (revised):**
- Init: care_weight = uniform(0, 0.50), **mean=0.25** (half of Phase 3 start, below Phase 3 eroded equilibrium 0.42)
- This is "depleted care" not "zero care" — the model cannot support literal zero due to decision mechanics
- KEY FINDING: same ecological setup as Phase 3 but with mult=1.15 **REVERSES** the selection gradient
  - Phase 3 (mult=1.0): care declines 0.500→0.420, r=−0.178
  - Phase 5 (mult=1.15): care BUILDS 0.250→0.355+, r=POSITIVE (target)

**Phase 5a: evolution** — 5000 ticks, seeds 42–51, mult=1.15, scatter=2, plasticity=OFF
**Phase 5b: control** — same but scatter=8 (standard dispersal). Tests natal philopatry contribution.
**Phase 5c: zero-shot** — evolved genomes, no reproduction/mutation, care_window rate vs Phase 3 baseline

**Implementation status (2026-04-11):**
- Config: `infant_starvation_multiplier` + `birth_scatter_radius` added ✓
- Simulation: infant hunger multiplier + birth_pos scatter ✓
- `experiments/phase5_emergence/run.py` ✓ (survival_gate / evolution / control / zeroshot)
- `experiments/phase5_emergence/run_multi_seed.py` ✓
- Survival gate seed=42: PASSED (32 mothers at tick 1000)
- Full single-seed run: IN PROGRESS

**Expected outcomes (updated):**
| Metric | Phase 3 | Phase 4b | Phase 5 (calibrated) |
|--------|---------|----------|----------------------|
| Init care_weight | 0.500 | 0.500 | **0.25 (mean)** |
| Final care_weight | 0.420 | 0.441 | **> 0.350 (RISING)** |
| Selection gradient r | −0.178 | −0.1887 | **> 0 (positive — key result)** |
| Zero-shot assimilation | p=0.815 | p=0.815 | **TBD (pending run)** |

---

### Part 3 — Extended Plasticity (Future Chapter, if needed)
*Revisit only if Phase 5 demonstrates emergence — these become "refinement" experiments, not "fix the broken system" experiments.*
- Epigenetic inheritance (Lamarckian soft transmission)
- Social learning (copy successful mothers)
- Evolvable kin sensitivity genome parameter
- Multi-mechanism combinations

---

**YOU ARE HERE: Phase 5 — Ecological Emergence (care from zero)**

---

## Phase 4: Plasticity / Baldwin Effect — COMPLETE (2026-04-10)

Two versions run. v1 (lineage-blind) was a design flaw caught and corrected. v2 (kin-conditional) is the scientifically valid test. **v2 is canonical.**

### Run directories

| Stage | Dir |
|-------|-----|
| v1 evolution (blind — null result) | `outputs/phase4_plasticity/run_20260410_104824_seed42` |
| v1 zero-shot (blind — confounded) | `outputs/phase4_plasticity/run_20260410_105016_seed42` |
| **v2 evolution (kin-conditional)** | **`outputs/phase4_plasticity/run_20260410_113356_seed42`** |
| **v2 zero-shot (kin-conditional)** | **`outputs/phase4_plasticity/run_20260410_113536_seed42`** |

### v1 lineage-blind — null result (kept as control)

`plastic_update` fired on ALL care events. 90%+ are foreign (r=0) → signal anti-correlated with inclusive fitness.

| Metric | Phase3 (no plast.) | Phase4 v1 (blind) |
|--------|-------------------|-------------------|
| Final care_weight | 0.420 (−0.080) | 0.432 (−0.068) |
| learning_rate Δ | — | +0.041 (non-monotonic, peak 0.160, fell back) |
| forage_weight Δ | — | +0.078 (energy-cost side-effect of frequent updates) |
| Selection r (care vs gen) | −0.178 | **−0.2158 (accelerated — worse)** |
| Hamilton rB-C | — | −0.0052, 31.0% rB>C |

**Diagnosis:** Lineage-blind plasticity accelerated care decline. Null result by design, not by biology.

### v2 kin-conditional — proper Baldwin Effect test

`plastic_update` fires ONLY on `is_own_child=True` (~10% of care events). Signal aligned with inclusive fitness. NOT kin recognition: target selection remains distress-based from all visible children. Only the learning feedback is own-offspring-gated. Config flag: `plasticity_kin_conditional=True`.

**Three-way evolution comparison:**

| Metric | Phase3 (no plast.) | v1 (blind) | **v2 (kin-cond.)** |
|--------|-------------------|-----------|--------------------|
| Final care_weight | 0.420 (−0.080) | 0.432 (−0.068) | **0.436 (−0.065, smallest decline)** |
| care_weight trough | 0.365 (final) | 0.434 | **0.355 @ tick 2300, recovered to 0.436** |
| learning_rate Δ | — | +0.041 noisy | **+0.066 (0.103→0.170, late sustained sweep)** |
| forage_weight Δ | — | +0.078 | **+0.014 (nearly flat)** |
| Selection r | −0.178 | −0.2158 | **−0.1887 (weakest across all conditions)** |
| Care events | 1174 | 1887 | 1147 |
| Hamilton rB-C | — | −0.0052, 31.0% | **−0.0004, 39.7% (nearest break-even)** |

**Care_weight trajectory (v2) — 3-phase:**
1. Ticks 0–1900: slow decline (0.500→~0.450)
2. Ticks 2000–2600: rapid crash to trough (0.355)
3. Ticks 2700–5000: **sustained recovery (0.355→0.436)** — as learning_rate swept upward from 0.087 to 0.170, kin-aligned plastic signal became strong enough to partially reverse genetic erosion of care_weight. This recovery is absent in phase3 and v1 — it is the Baldwin Effect signature.

**Zero-shot comparison (care-window metric, ticks 0–100 = maturity_age):**

| | Phase2 (phase3 genomes, no plast.) | Phase4 v2 (kin-cond.) |
|-|-----------------------------------|-----------------------|
| Window care events | 229 | 239 |
| Window mother-ticks | 2525 | 2406 |
| **Window rate** | **0.09069** | **0.09933** |
| Improvement | — | **+9.5%** |
| Last alive tick | 697 | 575 (dies faster — cares more) |

Phase4 v2 genomes care **9.5% more per mother-tick** in the care window of a new environment. This is Baldwin Effect genetic assimilation: only 8/239 zero-shot events trigger plasticity, so the 9.5% gain comes from the evolved genome itself, shaped by kin-conditional feedback during evolution.

**Note on care-window baseline:** Earlier session computed 0.076 using 25×120 ticks — incorrect. Correct value using actual population data (ticks 0–100): **0.09069**.

### Key findings (Phase 4)

1. **Lineage-blind plasticity is counterproductive** (v1): accelerated care decline (r=−0.2158). 90%+ of updates reward foreign care (r=0) → fitness anti-correlated signal.
2. **Kin-conditional plasticity shows genuine Baldwin Effect** (v2):
   - Smallest care_weight decline (−0.065)
   - care_weight **recovered from trough** as learning_rate swept (ticks 2700–5000) — not seen in phase3 or v1
   - learning_rate late-run sweep: 0.103→0.170 (monotonic from tick 3600) — clean selection, not drift
   - Weakest selection against care (r=−0.1887)
   - Hamilton rB-C nearest zero (−0.0004)
3. **Genetic assimilation confirmed in transfer**: kin-cond. genomes care 9.5% more in zero-shot window (0.09933 vs 0.09069). Effect comes from the genome (only 8/239 zero-shot events trigger plasticity).
4. **Forage stays neutral** (v2 Δ+0.014 vs v1 Δ+0.078): removing energy-wasting foreign plasticity eliminates foraging side-effect.
5. **Mechanistic insight**: kin-aligned plastic feedback provides the correct fitness gradient for Baldwin assimilation. Lineage-blind feedback cannot, regardless of signal magnitude.

### New plots (Phase 4)
- `learning_rate_trajectory.png` — avg_learning_rate over ticks with min/max band (Baldwin signature)

---

## Evolution — COMPLETE

**Run dir (canonical):** `outputs/phase3_maternal/run_20260409_232012_seed42`
**Multi-seed dir:** `outputs/phase3_maternal/multi_seed_evolution` (seeds 42–51)
**Config:** `mutation_enabled=True`, `reproduction_enabled=True`, default Genome (0.5, 0.5, 0.5), `seed=42`
**Results (seed 42):** 25 surviving mothers, care_weight 0.500→0.420 over 50 generations
**Multi-seed:** 9/10 seeds declined (mean −0.059), 1 outlier (seed 48 +0.067 — low forage pressure)
**Hamilton (own-lineage):** r=0.5 correct; mean rB=0.054, mean C=0.050, 44.7% rB>C
**Key finding:** No kin recognition → Hamilton is post-hoc only. Care declines because 89.5% of events are foreign (r=0), pure cost.
**Selection proof:** care_weight vs generation r=−0.178 (birth_log, 648 events). Not drift.
**Survival proof:** care_weight vs post-birth survival r=−0.001. Care does NOT kill mothers. Cost is pre-reproductive.
**Plots:** `evolution_trajectory.png`, `start_vs_end_multiseed.png`, `reproductive_success_by_genotype.png`, `hitchhiking_check.png`
**New logs added:** `birth_log.csv` (BirthRecord: mother genome snapshot at each birth)

---

## Zero-Shot — COMPLETE (2026-04-10)

**Run dir:** `outputs/phase2_zeroshot/run_20260409_233243_seed42`
**Source genomes:** `outputs/phase3_maternal/run_20260409_232012_seed42/top_genomes.json`
**Config:** 25 mothers (from evolution), `init_food=100`, no reproduction, no mutation, 1000 ticks
**Results:** 229 care events (all successful), last alive tick 697
**Care/mother-tick:** 0.0144 (vs phase3 evolution ~0.0094 — higher rate without reproduction pressure)
**Care window:** All 229 events in ticks 0–120 only. After tick ~100 all children matured → no children left to care for.
**Extinction:** Expected — no reproduction → 50 mothers post-maturation with no replacement mechanism.

**Scientific status:** Control baseline for phase4 Baldwin comparison.
- Phase2 window rate (ticks 0–100): **0.09069/mother-tick** (correct — computed from actual population data)
- Phase4 v2 window rate: 0.09933 (+9.5% — genetic assimilation evidence)
- Earlier session note "~0.076" was wrong (used 25×120 ticks denominator instead of actual pop data)

---

## New Logging Added (2026-04-10)

| Log | Record | Key fields | Purpose |
|-----|--------|------------|---------|
| `birth_log.csv` | `BirthRecord` | mother_id, child_id, mother_generation, care_weight, forage_weight, self_weight | Per-mother genome at birth — enables care_weight vs generation correlation (selection proof) |

**Selection proof from birth_log (seed 42):** care_weight vs generation r=−0.178 (n=648 births). Directional. Not drift.
**Survival proof:** care_weight vs ticks-alive-after-first-birth r=−0.001. Care cost is pre-reproductive, not post-reproductive mortality.

---

## New Plots Added (2026-04-10)

| Plot | Location | Answers |
|------|----------|---------|
| `evolution_trajectory.png` | per evolution run `/plots/` | Why care declines (3-phase: growth/crash/erosion), forage independence |
| `start_vs_end_multiseed.png` | `multi_seed_evolution/plots/` | Gen0 vs Gen50 per seed — is decline robust? (9/10 seeds) |
| `reproductive_success_by_genotype.png` | per evolution run `/plots/` | care vs generation (selection), care vs survival (cost mechanism) |

---

## Session Log

| Date | Work done |
|------|-----------|
| 2026-04-08 | phase1 survival, Baseline-C0 |
| 2026-04-09 | Baseline-R0, evolution (seeds 42–51), bugs #19–23 |
| 2026-04-10 | Evolution analysis (3 Qs, hitchhiking, Hamilton caveat), birth_log, reproductive fitness plots, zero-shot fixed + run, clarified zero-shot = baseline for phase4 |
| 2026-04-10 | Phase4 plasticity: rewrote run.py (fixed extinction bug, added zeroshot stage, proper snapshots), added learning_rate_trajectory plot, ran both stages. ALL PIPELINE STEPS COMPLETE. |
| 2026-04-10 | Phase4 v1 (blind) = null result. Phase4 v2 (kin-conditional) = Baldwin Effect confirmed (seed 42). 4 thesis comparison plots. Multi-seed Phase 4b script created, NOT YET RUN. |
| 2026-04-10 | Multi-seed Phase 4b COMPLETE (seeds 42–51). Phase 2 baselines run for all 10 seeds. Paired stats computed. Partial Baldwin Effect: lr sweep 8/10 seeds, care recovery 2/10. Zero-shot not significant (p=0.815). |

---

## Multi-Seed Phase 4b — COMPLETE

**Output dir:** `outputs/phase4_plasticity/multi_seed_evolution/`
**Seeds:** 42–51 (10 seeds)
**Script (hardened):** `experiments/phase4_plasticity/run_multi_seed.py`

### Evolution Results

| Seed | Survivors | care_w | lr | Baldwin? |
|------|-----------|--------|----|----------|
| 42 | 24 | 0.4361 | 0.1695 | YES (care+lr) |
| 43 | 25 | 0.4850 | 0.1026 | no |
| 44 | 25 | 0.4404 | 0.1779 | no (lr only) |
| 45 | 28 | 0.4381 | 0.1716 | no (lr only) |
| 46 | 29 | 0.4168 | 0.1493 | YES (care+lr) |
| 47 | 27 | 0.4542 | 0.1934 | no (lr only) |
| 48 | 27 | 0.4709 | 0.1556 | no (lr only) |
| 49 | 25 | 0.4573 | 0.1638 | no (lr only) |
| 50 | 26 | 0.3997 | 0.1273 | no |
| 51 | 25 | 0.4158 | 0.1368 | no (lr only) |
| **Mean** | **26.1** | **0.4414 ± 0.016** | **0.1548 ± 0.017** | **2/10 full, 8/10 lr** |

- Baldwin (care recovery ≥0.03 AND lr ≥0.03): **2/10 seeds**
- LR sweep only (lr ≥0.03): **8/10 seeds**
- Mean care_weight Phase 4b (0.441) > Phase 3 (0.420) — plasticity buffered care decline by ~10pp

### Paired Zero-Shot Statistical Test (Phase 4b vs Phase 2)

Phase 2 baseline = same Phase 3 genomes tested without plasticity (matched by seed).

| Seed | Phase 4b rate | Phase 2 rate | Diff |
|------|--------------|-------------|------|
| 42 | 0.09933 | 0.09069 | +0.00864 |
| 43 | 0.07050 | 0.07208 | −0.00158 |
| 44 | 0.08062 | 0.07143 | +0.00919 |
| 45 | 0.07921 | 0.06728 | +0.01193 |
| 46 | 0.09036 | 0.10378 | −0.01342 |
| 47 | 0.06862 | 0.07768 | −0.00906 |
| 48 | 0.11164 | 0.09271 | +0.01893 |
| 49 | 0.08475 | 0.06565 | +0.01910 |
| 50 | 0.07426 | 0.09498 | −0.02072 |
| 51 | 0.07848 | 0.09053 | −0.01205 |

**Result: NOT significant**
- Mean diff: +0.00110, 95% CI [−0.00779, +0.00999]
- Paired t-test: t=0.2417, p=0.8145, df=9
- Wilcoxon: W=27.0, p=1.0000
- Cohen's d: 0.076 (negligible)
- 5/10 seeds: Phase 4b > Phase 2; 5/10 seeds: Phase 4b < Phase 2

### Scientific Interpretation

**What evolved:** Learning machinery (lr: 0.10→0.155 mean, 8/10 seeds). Kin-conditional Hebbian feedback selected for plasticity capacity.

**What did NOT evolve:** Genetic assimilation of care behavior (zero-shot improvement not significant). The evolved care advantage depends on within-lifetime learning — removed that learning (zero-shot) and the genome performs no better than Phase 3.

**Partial Baldwin Effect confirmed:**
- Stage 1 (plasticity favored): YES — lr sweep in 8/10 seeds
- Stage 2 (genetic assimilation): ABSENT — zero-shot p=0.815, Cohen's d ≈ 0

**Why seed 42 was special:** Seed 42 showed both stages (care recovery 0.081 AND lr sweep 0.066). The +9.5% zero-shot improvement was real for that seed. Across 10 seeds the effect is not consistent — 5/10 go each direction.

### Output Files
- `summary.json` — per-seed evolution with Baldwin classifications
- `zeroshot_summary.json` — Phase 4b zero-shot window rates
- `phase2_baseline_summary.json` — Phase 2 matched window rates
- `statistical_tests.json` — paired t-test, Wilcoxon, Cohen's d
- `multi_seed_care_weight_ci.png` — 3-panel CI + Phase 3 overlay + Baldwin annotation
- `zeroshot_multiseed.png` — per-seed bar chart Phase 4b vs Phase 2

---

## Thesis Plots — COMPLETE

**Location:** `outputs/thesis_plots/` (4 cross-run comparison plots)
| Plot | Contents |
|------|----------|
| `selection_gradient_comparison.png` | care_weight vs generation scatter, Phase3/4a/4b side-by-side |
| `population_trough.png` | Mothers alive ticks 1800–2800, Phase4b vs Phase3 (trough stability) |
| `zeroshot_comparison.png` | Care-window rate bar: Phase2 / 4a / 4b |
| `phase_comparison_table.png` | All key metrics across Phase3 / 4a / 4b |

**Per-run plots** exist in each run's `plots/` subdirectory (see run dirs above).
**Multi-seed thesis plots** to be added after multi-seed Phase 4b runs.

---

## Scientific Reframe — 2026-04-11

### The Problem with the Original Conclusion

The Phase 0 draft claimed: *"maternal instinct CAN emerge from evolutionary dynamics."*

**This is incorrect framing.** In evolutionary game theory, "emerge from evolutionary dynamics" implies the population started near zero care and selection built it upward. That is not what happened:

1. Random initialization → mean care_weight ≈ 0.500 (given by chance, not selection)
2. Survival gate → passively filtered agents that already had care
3. Evolution (Phase 3 onward) → immediately and consistently **eroded** care (r=−0.178, 9/10 seeds)

Evolution was never the constructive force. It was the destructive one. Calling that "emergence" misrepresents the mechanism.

### What Phases 1–4 Actually Tested

*Given care initialized at moderate levels by random sampling + survival filtering, can natural selection maintain it?*

**Answer: No.** Selection erodes it. Plasticity buffers erosion but cannot reverse it (assimilation absent p=0.815).

Phases 1–4 establish the **maintenance conditions problem** — not emergence. They show:
- Care is evolutionarily unstable without sufficient ecological pressure (Hamilton violated for 89.5% of events)
- Plasticity is a stabilizing force but not sufficient for genetic assimilation
- Kin bias emerges from birth-proximity (confirmed), but effective r too low to satisfy rB > C

### Why Care Won't Emerge from Zero in the Current Design

| Term | Value | Block |
|------|-------|-------|
| r | ~0.1 (90% foreign) | Care benefit diluted across unrelated offspring |
| B | Hunger reduction | Marginal — children survive without care, just hungrier |
| C | Energy cost | Real, paid every event |

A rare care mutant (care_weight = 0.1) in a zero-care population pays real cost but captures near-zero inclusive fitness gain. Selected out before spreading.

### The Fix: Infant Dependency Ecology

**Make infant survival depend on receiving care.** B becomes existential (alive/dead) instead of marginal (less hungry). Even with diluted r, rB >> C when infant_survival_value is large enough.

This is the mammalian analogy: infants are physiologically helpless → without care they die → care genes spread via offspring survival → maternal instinct evolves.

No kin recognition. No hard-coded targets. Mothers still pick highest-distress child from ALL visible. The ecology creates the selection pressure.

### Corrected Research Question (for Phase 5)

**Old question:** Can maternal instinct emerge from evolutionary dynamics?
**Corrected question:** What are the minimum ecological conditions under which maternal care emerges from near-zero and becomes genetically assimilated?

**Phase 5 is the experiment that answers this correctly.**

---

## Phase 5 — Ecological Emergence (IN PROGRESS 2026-04-11)

**Folder:** `experiments/phase5_emergence/`
**Output dir:** `outputs/phase5_emergence/`

### Goal
Demonstrate that infant dependency ecology REVERSES the selection gradient for care: from negative (Phase 3, r=−0.178, eroding) to positive (Phase 5, r>0, building). Show care building upward from a depleted baseline through pure natural selection.

### Mechanism 1 — Infant Starvation (core)

Config param: `infant_starvation_multiplier = 1.15` (calibrated — see note below)
- During `[0, maturity_age]`: child hunger rate *= 1.15
- Without care, infants die at tick ~108 (just after maturity_age=100) → B near-existential
- With care, infants survive → mother's care genes propagate

**Calibration note:** Original design used mult=3.0, but this creates an evolutionary trap: selection works (care builds) but population crashes in the bottleneck before stabilizing. Scanned mult=1.0 through 1.20:
- mult=1.0: flat/slight decline (Phase 3 direction)
- mult=1.10: slight upward
- mult=1.15: **clear upward trend (+24% in 5000 ticks)** ← SELECTED
- mult≥1.25: evolutionary trap, population goes extinct

### Mechanism 2 — Tighter Natal Philopatry (r amplifier)

Config param: `birth_scatter_radius = 2` (Phase 5a), `birth_scatter_radius = 8` (Phase 5b control)
- Infants born within 2 Chebyshev cells of mother → kin stay spatially clustered
- Effective r increases from ~0.1 toward ~0.20 without kin recognition

### Initialization

```python
# Phase 5 init — depleted care baseline
care_weight   = uniform(0.0, 0.50)   # mean=0.25, vs. 0.5 start in Phase 3
forage_weight = uniform(0.0, 1.0)
self_weight   = uniform(0.0, 1.0)
plasticity_enabled          = False   # clean genetic signal
mutation_enabled            = True
reproduction_enabled        = True
infant_starvation_multiplier = 1.15
birth_scatter_radius         = 2
```

### Key Measurements

| Metric | Phase 3 result | Phase 5 prediction |
|--------|---------------|-------------------|
| Init care_weight | 0.500 mean | **0.250 mean (depleted)** |
| Final care_weight | 0.420 (eroded) | **> 0.355 (building)** |
| Selection gradient r | −0.178 (eroding) | **> 0 (positive — KEY)** |
| Trajectory direction | ↓ declining | **↑ rising** |
| Zero-shot assimilation | p=0.815 (none) | **TBD** |

### Phase 5 Stages

1. **5a evolution** — 5000 ticks (50 gens), seeds 42–51, mult=1.15, scatter=2, no plasticity
2. **5b evolution control** — same but scatter=8 — tests natal philopatry contribution
3. **5c zero-shot** — load 5a genomes, no plasticity/reproduction/mutation — assimilation test

### Config Flags

| Flag | Phase 5a | Phase 5b control | Notes |
|------|---------|-----------------|-------|
| `infant_starvation_multiplier` | 1.15 | 1.15 | Calibrated for positive gradient + population survival |
| `birth_scatter_radius` | 2 | 8 | Tight vs dispersed natal philopatry |
| `plasticity_enabled` | False | False | OFF — clean genetic selection signal |
| `mutation_enabled` | True | True | Required for emergence |
| `care_weight_init` | U(0, 0.50) | U(0, 0.50) | Mean=0.25, depleted baseline |

### Survival Gate

Before each 5000-tick run:
- Run 1000 ticks (10 gens) with same config
- Pass: ≥5 mothers at tick 1000
- Seed 42 PASSED: 32 mothers at tick 1000 ✓

---

## Archived: Phase 0 Draft (Superseded)

*Original conclusion draft — kept for reference. Framing was incorrect (see Scientific Reframe above).*

> Maternal care emerged as a phenotypic behavior from random genomes... Conclusion: maternal instinct CAN emerge from evolutionary dynamics, but pure selection erodes it — phenotypic plasticity is necessary (though not sufficient alone) to maintain it across generations.

*This draft will be rewritten after Phase 5 results are in.*

---

## Key Spec Rules (do not violate)

- No kin recognition — agents cannot observe r
- No hard-coded maternal behavior — must emerge from genome
- No hard-coded care targets — mothers pick highest-distress from ALL visible children. Environment (birth proximity) creates kin bias naturally.
- No new folders per stage — phase = folder, stage = config
- Baselines = reference, not optimal solutions
- Do NOT proceed if survival gate fails
- Logging must capture both decision (ChoiceRecord) and outcome (CareRecord)
- Hamilton rB > C applies only to own-lineage care (r > 0). Foreign events = by-product analysis only.
- B_individual = hunger_reduced. B_social = lineage reproductive success (inclusive fitness).