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

**YOU ARE HERE: P6 · controls_and_baldwin — STRICT ONE-STEP PROTOCOL (2026-04-13)**

Strict protocol: execute one step at a time, report results, STOP, wait for explicit **"Approved"** before next step.

---

## Canonical Plan — P1 through P6 (Source of Truth)

| P# | Label | Exp Dir(s) | Status | Key result |
|----|-------|------------|--------|------------|
| P1 | `mechanics_tests` | `phase01_mechanics_tests` | ✓ DONE | Unit tests pass |
| P2 | `survival_minimal` | `phase02_survival_minimal` | ✓ DONE | Agents survive (6 runs) |
| P3 | `survival_full` | `phase03_survival_full` + `phase04_care_erosion` | ✓ DONE | Care erodes r=−0.178, 10 seeds |
| P4 | `plasticity_intro` | `phase06_baldwin_effect` | ✓ DONE | Plasticity introduced — care still erodes, p=0.815 |
| P5 | `enhanced_ecology` | `phase07_ecological_emergence` | ✓ DONE | Gradient REVERSED r=+0.079, p=0.0002, d=1.87 |
| P6 | `controls_and_baldwin` | `phase08–11` | IN PROGRESS | See sub-steps below |

### P6 Sub-steps

| Step | Label | Status | Key result |
|------|-------|--------|------------|
| 6a | Dispersal ablation zero-shot (scatter=8) | ✓ DONE | Phase 08 evolution done; zero-shot script ready |
| 6b | Spatial-only control (mult=1.0, scatter=2) | ✓ DONE | Phase 09 mean r=+0.0656, 9/10 positive — UNEXPECTED |
| 6c | Depleted-init baseline zero-shot | **AWAITING APPROVAL** | Phase 10 — not yet run |
| 6d | Baldwin instinct assimilation | After 6c | Phase 11 — not yet run |

---

## P5 Key Results — Phase 07 Ecological Emergence (COMPLETE)

| Seed | Survivors | Start cw | Final cw | Grad r | Emerged? |
|------|-----------|----------|----------|--------|----------|
| 42 | 34 | 0.2741 | 0.3547 | +0.0768 | YES |
| 43 | 45 | 0.2041 | 0.2142 | −0.0260 | no |
| 44 | 44 | 0.1585 | 0.2382 | +0.0909 | YES |
| 45 | 49 | 0.2144 | 0.2930 | +0.0971 | YES |
| 46 | 48 | 0.2225 | 0.2898 | +0.0949 | YES |
| 47 | 39 | 0.1634 | 0.2249 | +0.0732 | YES |
| 48 | 50 | 0.2144 | 0.2608 | +0.1110 | no |
| 49 | 36 | 0.2178 | 0.3028 | +0.0474 | YES |
| 50 | 34 | 0.2488 | 0.3358 | +0.1124 | YES |
| 51 | 43 | 0.2932 | 0.3625 | +0.1104 | YES |
| **Mean** | — | — | 0.2877±0.033 | **+0.0788** | **8/10** |

Primary stats: t=5.93, p=0.0002, d=1.87. CI [+0.053, +0.105] — entirely above zero.

---

## P6b Results — Phase 09 Spatial-Only Control (COMPLETE, UNEXPECTED)

**Config:** mult=1.0 (no infant pressure), scatter=2 (tight philopatry), cw~U(0,0.5), 5000t, seeds 42–51

| Seed | Grad r |
|------|--------|
| 42 | +0.0413 |
| 43 | +0.1241 |
| 44 | +0.0585 |
| 45 | +0.0827 |
| 46 | +0.0226 |
| 47 | +0.0841 |
| 48 | +0.1549 |
| 49 | +0.1131 |
| 50 | −0.0923 |
| 51 | +0.0669 |
| **Mean** | **+0.0656** |

**9/10 positive** — philopatry alone (no infant pressure) still produces a positive gradient.

**Thesis implication — reframing required:**
- OLD: both mult=1.15 AND scatter=2 needed (strict AND-condition)
- NEW: natal philopatry is the dominant driver; infant dependency amplifies (+0.079 vs +0.0656) but is not strictly necessary
- Compare: Phase 04 (mult=1.0, scatter=8): r=−0.178 — same multiplier with dispersal = strong erosion
- Mechanism: kin clustering alone raises effective r sufficiently for rB > C even with ordinary B

---

## P6c Specification — Depleted-Init Baseline Zero-Shot (AWAITING APPROVAL)

**Script to create:** `experiments/phase10_zeroshot_depleted/run.py`

**Scientific purpose:** Phase 05 zero-shot baseline (0.09069) used high-care evolved genomes.
Phases 07/08/09 start from depleted init (cw~U(0,0.5)). Need a baseline from the *same* init
to make zero-shot comparisons fair.

**Config:**
- `care_weight ~ Uniform(0, 0.50)` (depleted — identical to Phase 07/08/09 evolution starts)
- `max_ticks = 1000`
- `plasticity_enabled = False`
- `mutation_enabled = False`
- `reproduction_enabled = False`
- `infant_starvation_multiplier = 1.15`, `birth_scatter_radius = 2` (Phase 07 ecology)

**Output metric:** `care_window_rate` = successful care events / alive-mother-ticks, ticks 0–100

**Provides:** correct baseline for Phase 08 zero-shot + Phase 09 zero-shot comparison

---

## P6d Specification — Baldwin Instinct Assimilation (After P6c)

**Script to create:** `experiments/phase11_instinct_assimilation/run.py` + `run_multi_seed.py`

**Design:**
- Ecology: mult=1.15, scatter=2 (Phase 07 settings)
- Plasticity: ON, kin-conditional (Phase 06 settings)
- Init: cw~U(0,0.5) (depleted baseline)
- Config addition needed: `plasticity_energy_cost` in Config + MotherAgent

**Two stages:**
1. Stage 1 (10000t): evolution + plasticity ON → care_weight and learning_rate should rise
2. Stage 2 (10000t): plasticity OFF, mutation OFF, reproduction ON → instinct test

**Four instinct criteria (ALL must pass for a seed to count):**
1. `care_weight` drift ≤ 0.02 after plasticity removed
2. Care action rate comparable to plastic phase
3. Child energy/lifetime maintained or improved
4. Infant population stable or growing

**Pass criterion:** ≥ 8/10 seeds pass → report can claim "maternal care instinct demonstrated"

**Figure:** Concatenated 0→20000t plot (green=plasticity ON, grey=plasticity OFF)

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

## Config Flags (as of 2026-04-10)

| Flag | baseline_c0 | baseline_r0 | evolution | zeroshot |
|------|-------------|-------------|-----------|----------|
| children_enabled | True | True | True | True |
| care_enabled | True | True | True | True |
| plasticity_enabled | False | False | False* | False |
| reproduction_enabled | True | True | True | **False** |
| mutation_enabled | **False** | **False** | True | **False** |

*plasticity added in phase06

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

## Canonical Run Directories

| Phase | Dir |
|-------|-----|
| Phase 04 C0 baseline | `outputs/phase04_care_erosion/run_20260408_191406_seed42` |
| Phase 04 R0 baseline | `outputs/phase04_care_erosion/run_20260409_125601_seed42` |
| Phase 04 evolution (seed=42) | `outputs/phase04_care_erosion/run_20260409_232012_seed42` |
| Phase 04 multi-seed | `outputs/phase04_care_erosion/multi_seed_evolution` |
| Phase 05 zero-shot | `outputs/phase05_zeroshot_standard/run_20260409_233243_seed42` |
| Phase 06 evolution (seed=42) | `outputs/phase06_baldwin_effect/run_20260410_113356_seed42` |
| Phase 06 multi-seed | `outputs/phase06_baldwin_effect/multi_seed_evolution` |
| Phase 07 evolution (seed=42) | `outputs/phase07_ecological_emergence/run_20260411_233237_seed42` |
| Phase 07 multi-seed | `outputs/phase07_ecological_emergence/multi_seed_evolution` |
| Phase 09 multi-seed | `outputs/phase09_spatial_control/multi_seed_evolution` |
| Publication figures | `outputs/publication_figures/` |

## Frozen Baselines

| Constant | Value | Source |
|----------|-------|--------|
| `PHASE3_ZS_BASELINE` | 0.09069 | Phase 05 zero-shot (standard evolved genomes) |
| `INFANT_STARVATION_MULT` | 1.15 | Phase 07 calibrated |
| `PHILOPATRY_SCATTER` | 2 | Phase 07 calibrated |
| `CONTROL_SCATTER_RADIUS` | 8 | Phase 08 dispersal control |

---

## Phase Naming Map (post-rename 2026-04-12)

| New name | Old name | Content |
|----------|----------|---------|
| phase01_mechanics_tests | phase0_evolution_sanity | Sanity checks |
| phase02_survival_minimal | step1_survival_check | Minimal survival |
| phase03_survival_full | phase1_survival | Full engine survival |
| phase04_care_erosion | phase3_erosion | Baseline evolution |
| phase05_zeroshot_standard | phase2_zeroshot | Standard zero-shot |
| phase06_baldwin_effect | phase4_plasticity | Baldwin/plasticity |
| phase07_ecological_emergence | phase5a_reversal | Ecological emergence |
| phase08_dispersal_control | (thin wrapper, expanded) | Dispersal ablation |
| phase09_spatial_control | phase5d_spatial_control | Spatial-only control |
| phase10_zeroshot_depleted | (NEW) | Depleted-init baseline |
| phase11_instinct_assimilation | (NEW) | Instinct/assimilation |

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
| 7 | `phase03_survival_full/run.py` was empty | phase03_survival_full/run.py |
| 8 | `initialize_with_genomes()` didn't exist | simulation.py |
| 9 | Phase2 loaded genomes from phase1 (wrong) | phase05_zeroshot_standard/run.py |
| 10 | Phase3 never saved `top_genomes.json` | phase04_care_erosion/run.py |
| 11 | Phase3 had no stage support | phase04_care_erosion/run.py |
| 12 | `stress` never updated — M_self half-broken | agents/mother.py |
| 13 | `population_history.json` never saved → plots silently skipped | phase04_care_erosion/run.py |
| 14 | `_log_choice` re-called `choose_child` ignoring commitment → wrong target logged | simulation.py |
| 15 | `init_mothers=30, init_food=25` → 0.83 food/mother → total extinction | phase04_care_erosion/run.py |
| 16 | `reproduction_enabled=False` on baselines → care only in first 100 ticks | phase04_care_erosion/run.py |
| 17 | No `mutation_enabled` flag → no way to fix genomes without killing reproduction | config.py, simulation.py |
| 18 | `get_step_toward` only tried 3 directions → agents froze in crowds | simulation/world.py |
| 19 | `own_child_id` never cleared on child death/maturation → mothers could only reproduce once | simulation/simulation.py |
| 20 | `fatigue` never incremented in main sim → `self` domain halved, mothers never rested | simulation/simulation.py, config.py |
| 21 | `mother_lineage_id`, `child_lineage_id`, `is_own_child` missing from CareRecord | logging_system/records.py, simulation/simulation.py, logging_system/logger.py |
| 22 | Candidate arrays in ChoiceRecord never exported to CSV | logging_system/logger.py |
| 23 | No death log → can't compute lifetime reproductive success | logging_system/records.py, logger.py, simulation.py |
| 24 | phase05_zeroshot_standard `init_food=25, init_mothers=30` hardcoded → extinction after maturation | phase05_zeroshot_standard/run.py |
| 25 | phase05_zeroshot_standard no `population_history.json` → energy/population plots silently skipped | phase05_zeroshot_standard/run.py |
| 26 | phase05_zeroshot_standard `init_mothers=30` didn't match evolved genome count (25) | phase05_zeroshot_standard/run.py |
| 27 | phase05_zeroshot_standard missing `mutation_enabled=False` → genomes could drift during test | phase05_zeroshot_standard/run.py |

---

## Publication Figures

Script: `python experiments/make_publication_figures.py`
Output: `outputs/publication_figures/`

| File | Content |
|------|---------|
| `figure1_phase04_care_erosion.png` | Panel A: 10-seed CI trajectory (erosion); Panel B: birth_log scatter r=−0.178 |
| `figure2_phase06_baldwin_effect.png` | Panel A: Phase 3 vs 4b trajectory; Panel B: zero-shot bar p=0.815 |
| `figure3_phase07_ecological_emergence.png` | Panel A: Phase 5a CI + 5b control + Phase 3 overlay; Panel B: per-seed gradient r |

---

## REPORT.md Status (2026-04-13)

| Section | Status | Notes |
|---------|--------|-------|
| Abstract | APPROVED | 150 words, Pearson's r disambiguation applied |
| Introduction + Problem Statement | WRITTEN | Formal PS blockquote added; "build not emerge" framing |
| Related Work | WRITTEN | Hamilton, Baldwin, ALife precedents, key gap |
| Methods | WRITTEN | Two-level B distinction as §3.3 |
| Results (all phases) | WRITTEN | All plots embedded — **needs update after P6 completion** |
| Discussion | WRITTEN | AND-condition framing — **needs update after Phase 09 result** |
| Conclusion | WRITTEN | **needs update after Phase 09 result** |
| References | WRITTEN | 6 citations — check Emlen 1995 and Stacey & Koenig 1990 are included |

**Outstanding REPORT.md updates (after P6 complete):**
- Reframe Discussion: philopatry dominant, not strict AND-condition
- Add Phase 09 result to §4.6 or new §4.7
- Update Conclusion accordingly
- Add Figure 4 (Phase 11 instinct plot) when ready

---

## Project Title

**"Simulation of the Minimum Ecological Conditions for the Emergence of Kin-Biased Maternal Care via Evolving Neuroendocrine Agents"**

Applied consistently across README.md, EXPERIMENT.md, REPORT.md.

## Citations Verified (2026-04-13)

- Hamilton (1964) — *J. Theoretical Biology* 7(1), 1–52
- Hinton & Nowlan (1987) — *Complex Systems* 1(3), 495–502
- Axelrod & Hamilton (1981) — *Science* 211(4489), 1390–1396
- Nowak & May (1992) — *Nature* 359(6398), 826–829
