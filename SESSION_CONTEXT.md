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
| `phase4_plasticity` | Implemented, not yet run — **NEXT** |

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

## Roadmap — Current Position: Step 5

1. ~~Run phase1 survival gate~~ PASSED
2. ~~Baseline-C0~~ FROZEN — balanced `(care=0.7, forage=0.85, self=0.55)`
3. ~~Baseline-R0~~ COMPLETE — random genomes, seed=42
4. ~~Evolution~~ COMPLETE — `phase3_maternal`, seeds 42–51, 10 runs
5. **YOU ARE HERE: Plasticity / Baldwin effect** (`phase4_plasticity`)
6. ~~Hamilton analysis~~ COMPLETE (embedded in generate_all_plots — split own/foreign, rB vs C, lineage fitness)
7. ~~Zero-shot~~ COMPLETE — `phase2_zeroshot`, seed=42, 229 care events, 0.0144/mother-tick

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

**Scientific status — IMPORTANT:**
Zero-shot without plasticity is minimally meaningful. Fixed genome weights always produce the same behavior regardless of environment — there is no real "transfer" occurring, just the same static policy on a new random seed. This run serves as the **control baseline** for phase4. The meaningful comparison is:
- Phase3 genome (no plasticity) in zero-shot = this run (baseline)
- Phase4 genome (with plasticity) in same zero-shot = the actual experiment
- Does plasticity improve within-lifetime adaptation to the new env? That is the Baldwin effect test.

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
