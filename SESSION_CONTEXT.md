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

---

## Current Project State

| Phase | Status |
|-------|--------|
| `step1_survival_check` | VALIDATED — 6 runs, all passed |
| `phase1_survival` | PASSED — 12/12 survive, avg energy 0.910, 2026-04-08 |
| `phase3_maternal` | Ready — supports `stage=`: `baseline_c0`, `baseline_r0`, `evolution` |
| `phase2_zeroshot` | Ready — loads from phase3 `top_genomes.json` |
| `phase4_plasticity` | Implemented, not yet run |

---

## Roadmap — Current Position: Step 2

1. ~~Run phase1 survival gate~~ PASSED
2. **YOU ARE HERE: Baseline-C0** (`phase3_maternal`, `stage="baseline_c0"`):
   - balanced: `(care=0.7, forage=0.85, self=0.55)`
   - care-leaning: `(care=0.85, forage=0.75, self=0.5)`
   - forage-leaning: `(care=0.5, forage=0.9, self=0.65)`
   - Pick stable, non-trivial config → freeze as Baseline-C0
3. Baseline-R0 (`phase3_maternal`, `stage="baseline_r0"`)
4. Evolution (`phase3_maternal`, `stage="evolution"`)
5. Plasticity / Baldwin effect (`phase4_plasticity`)
6. Hamilton analysis (split):
   - 6a. Own-lineage (r>0): per-event `rB_individual > C`, regression `chosen ~ r + distance + distress`
   - 6b. Foreign-lineage (r=0): frequency count only (by-product of proximity, not Hamilton)
   - 6c. Lineage fitness: total descendants per founding lineage = B_social measure
   - 6d. Evolution trajectory: does mean care_weight increase over generations?
7. Zero-shot (`phase2_zeroshot`, pass `phase3_run_dir=` from step 4 output)

### Implementation needed before step 6:
- Extend CareRecord: add `mother_lineage_id`, `child_lineage_id`, `is_own_child`
- Extend CSV export with new columns
- Add `get_surviving_lineages()` to Simulation
- Add `analyze_hamilton_split()` to utils/plotting.py
- Add lineage fitness metric (descendants count per lineage)

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
