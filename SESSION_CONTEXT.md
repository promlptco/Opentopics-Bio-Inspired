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

**YOU ARE HERE: P6c — AWAITING APPROVAL (2026-04-13)**

Strict protocol: execute one step at a time, report results, STOP, wait for explicit **"Approved"** before next step.

---

## Canonical Directory Structure

```
experiments/
  p1_mechanics_tests/
  p2_survival_minimal/
  p3_survival_full/
  p3_care_erosion/          ← evolution (run.py, run_multi_seed.py, watch.py)
                               + zero-shot measurement (measure_baseline.py)
  p4_plasticity_intro/
  p5_enhanced_ecology/
  p6_controls_and_baldwin/
      p6a_dispersal_ablation/
      p6b_spatial_control/
      p6c_depleted_baseline/   ← script not yet written
      p6d_baldwin_instinct/    ← script not yet written

shared/
  constants.py              ← PHASE3_ZS_BASELINE, INFANT_STARVATION_MULT,
                               BIRTH_SCATTER_RADIUS, CONTROL_SCATTER_RADIUS, PHASE07_MEAN_R
```

Output directories (`outputs/`) use the old `phaseXX_` naming — they are NOT renamed.
Existing run outputs remain valid and accessible.

---

## Canonical Plan — P1 through P6

| P# | Label | Status | Statistical status |
|----|-------|--------|--------------------|
| P1 | `mechanics_tests` | DONE | [PASS] single-seed only — unit tests, no multi-seed needed |
| P2 | `survival_minimal` | DONE | [PASS] 6 runs, all seed=42 — survival gate, no multi-seed needed |
| P3 | `survival_full` | DONE | [PASS] single-seed (seed=42) — survival gate, no multi-seed needed |
| P3e | `care_erosion` | DONE | [PASS] multi-seed confirmed: seeds 42–51 verified on disk |
| P4 | `plasticity_intro` | DONE | [PASS] multi-seed confirmed: seeds 42–51 verified on disk |
| P5 | `enhanced_ecology` | DONE | [PASS] multi-seed confirmed: seeds 42–51 verified on disk |
| P6a | `dispersal_ablation` | DONE (evolution) | [UNKNOWN] outputs/phase08_dispersal_control/ not found on disk — zero-shot pending |
| P6b | `spatial_control` | DONE | [PASS] multi-seed confirmed: seeds 42–51 verified on disk |
| P6c | `depleted_baseline` | AWAITING APPROVAL | Not yet run |
| P6d | `baldwin_instinct` | Pending P6c | Not yet run |

---

## Key Findings Per Completed Phase

### P3e — Care Erosion (verified from outputs/phase04_care_erosion/multi_seed_evolution/summary.json)

Seeds 42–51, mean final care_weight ≈ 0.43 (range 0.38–0.57).
Selection gradient: **r = −0.178** (care declines under natural selection).

### P3e Baseline — measure_baseline.py (verified from outputs/phase05_zeroshot_standard/)

Frozen evolved genomes (care_weight ≈ 0.43), 1000 ticks, no plasticity/mutation/reproduction.
**PHASE3_ZS_BASELINE = 0.09069** care events / alive-mother-tick, ticks 0–100.
Note: this baseline uses high-care evolved genomes. Phases P6a/P6b start from depleted init —
P6c will provide the correct matching baseline.

### P4 — Plasticity Intro (verified from outputs/phase06_baldwin_effect/multi_seed_evolution/summary.json)

Seeds 42–51. `is_baldwin=True` in 2/10 seeds (seeds 42, 46). `lr_swept=True` in 8/10 seeds.
Care still erodes under standard ecology (mult=1.0). Baldwin Effect partial — lr sweeps up but
full assimilation absent at population level (p=0.815).

### P5 — Enhanced Ecology (verified from outputs/phase07_ecological_emergence/multi_seed_evolution/statistical_tests.json)

Seeds 42–51, mult=1.15, scatter=2.

| Stat | Value |
|------|-------|
| Mean selection gradient r | **+0.0788** |
| 95% CI | [+0.053, +0.105] — entirely above zero |
| One-sample t vs 0 | t=5.93, **p=0.0002** |
| Cohen's d | **1.87** |
| Seeds positive | **9/10** (seed 43 = −0.026, near-zero outlier) |
| P3e reference | −0.178 — direction REVERSED |

### P6b — Spatial Control (verified from outputs/phase09_spatial_control/multi_seed_evolution/statistical_tests.json)

Seeds 42–51, mult=1.0 (no infant pressure), scatter=2 (philopatry only).

| Stat | Value |
|------|-------|
| Mean selection gradient r | **+0.0656** |
| 95% CI | [+0.023, +0.108] |
| One-sample t | t=3.05, **p=0.0139** |
| Cohen's d | **0.963** |
| Seeds positive | **9/10** (seed 50 = −0.092) |

**UNEXPECTED finding:** Philopatry alone (no infant starvation pressure) still produces a
positive selection gradient. The AND-condition thesis framing must be revised.

**Thesis reframing:**
- OLD: both mult=1.15 AND scatter=2 required (strict AND-condition)
- NEW: natal philopatry is the dominant driver; infant dependency amplifies the effect
  (+0.079 vs +0.0656) but is not strictly necessary
- Mechanism: kin clustering raises effective r, which raises rB above C even with ordinary B
- Compare: P3e (mult=1.0, scatter=8): r=−0.178 — same multiplier with dispersal = strong erosion

---

## P6c — Depleted-Init Baseline Zero-Shot (AWAITING APPROVAL)

**Script to create:** `experiments/p6_controls_and_baldwin/p6c_depleted_baseline/run.py`

**Scientific purpose:**
PHASE3_ZS_BASELINE (0.09069) came from high-care evolved genomes (care_weight ≈ 0.43).
P6a and P6b evolved from depleted init (cw~U(0,0.5), mean≈0.25). A fair zero-shot comparison
requires a baseline from the same depleted init. P6c provides that baseline.

**Config:**
| Parameter | Value |
|-----------|-------|
| `care_weight` init | `~Uniform(0, 0.50)` (depleted — matches P5/P6a/P6b start) |
| `infant_starvation_multiplier` | 1.15 |
| `birth_scatter_radius` | 2 |
| `max_ticks` | 1000 |
| `plasticity_enabled` | False |
| `mutation_enabled` | False |
| `reproduction_enabled` | False |
| `children_enabled` | True |
| `care_enabled` | True |

**Output metric:** `care_window_rate` = successful care events / alive-mother-ticks, ticks 0–100

---

## P6d — Baldwin Instinct Assimilation (Pending P6c)

**Script to create:** `experiments/p6_controls_and_baldwin/p6d_baldwin_instinct/run.py` + `run_multi_seed.py`

**Design:**
- Ecology: mult=1.15, scatter=2 (P5 settings)
- Plasticity: ON, kin-conditional (P4 settings)
- Init: cw~U(0,0.5) (depleted baseline)
- Config addition required: `plasticity_energy_cost` in Config + MotherAgent

**Two stages:**
1. Stage 1 (10000t): evolution + plasticity ON
2. Stage 2 (10000t): plasticity OFF, mutation OFF, reproduction ON — instinct test

**Four instinct criteria (ALL must pass for a seed to count):**
1. `care_weight` drift ≤ 0.02 after plasticity removed
2. Care action rate comparable to plastic phase
3. Child energy / lifetime maintained or improved
4. Infant population stable or growing after plasticity OFF

**Pass criterion:** ≥ 8/10 seeds pass → "maternal care instinct demonstrated"

**Output figure:** Concatenated 0→20000t plot (green=plasticity ON, grey=plasticity OFF)

---

## Hamilton's Rule Framework (rB > C)

| Term | Definition | In This Simulation |
|------|-----------|-------------------|
| **r** | Coefficient of relatedness | `2^(-d)`: own child=0.5, grandchild=0.25. Post-hoc only. |
| **B_individual** | Direct benefit to child | `hunger_reduced` per care event |
| **B_social** | Indirect benefit to lineage | Lineage reproductive success = total descendants at end |
| **C** | Cost to mother | `feed_cost + move_cost` (energy spent) |

- Hamilton's rB > C applies to own-lineage care (r > 0) only
- Foreign-lineage care (r = 0) is a rare proximity by-product — reported as frequency only
- No kin recognition gene — spatial proximity at birth is the sole mechanism

---

## Config Flags

| Flag | baseline_c0 | baseline_r0 | evolution | zeroshot |
|------|-------------|-------------|-----------|----------|
| `children_enabled` | True | True | True | True |
| `care_enabled` | True | True | True | True |
| `plasticity_enabled` | False | False | False* | False |
| `reproduction_enabled` | True | True | True | **False** |
| `mutation_enabled` | **False** | **False** | True | **False** |

*plasticity added in p4_plasticity_intro

---

## Canonical Run Directories (outputs/ — NOT renamed)

| Phase | Canonical output dir |
|-------|---------------------|
| P3e evolution (seed=42) | `outputs/phase04_care_erosion/run_20260409_232012_seed42` |
| P3e multi-seed | `outputs/phase04_care_erosion/multi_seed_evolution` |
| P3e baseline zero-shot | `outputs/phase05_zeroshot_standard/run_20260409_233243_seed42` |
| P4 evolution (seed=42) | `outputs/phase06_baldwin_effect/run_20260410_113356_seed42` |
| P4 multi-seed | `outputs/phase06_baldwin_effect/multi_seed_evolution` |
| P5 evolution (seed=42) | `outputs/phase07_ecological_emergence/run_20260411_233237_seed42` |
| P5 multi-seed | `outputs/phase07_ecological_emergence/multi_seed_evolution` |
| P6b multi-seed | `outputs/phase09_spatial_control/multi_seed_evolution` |
| Publication figures | `outputs/publication_figures/` |

---

## Shared Constants (shared/constants.py)

| Constant | Value | Source |
|----------|-------|--------|
| `PHASE3_ZS_BASELINE` | 0.09069 | P3e zero-shot, seed=42, verified on disk |
| `INFANT_STARVATION_MULT` | 1.15 | P5 calibrated |
| `BIRTH_SCATTER_RADIUS` | 2 | P5 calibrated |
| `CONTROL_SCATTER_RADIUS` | 8 | P6a dispersal control |
| `PHASE07_MEAN_R` | 0.079 | P5 multi-seed, verified from statistical_tests.json |

---

## REPORT.md Status (needs update after P6 complete)

| Section | Status |
|---------|--------|
| Abstract | APPROVED |
| Introduction + Problem Statement | WRITTEN |
| Related Work | WRITTEN |
| Methods | WRITTEN |
| Results (P1–P5) | WRITTEN — needs P6 results added |
| Discussion | WRITTEN — AND-condition framing needs revision (P6b result) |
| Conclusion | WRITTEN — needs revision after P6b |
| References | WRITTEN — check Emlen 1995 and Stacey & Koenig 1990 |

---

## Citations Verified (2026-04-13)

- Hamilton (1964) — *J. Theoretical Biology* 7(1), 1–52
- Hinton & Nowlan (1987) — *Complex Systems* 1(3), 495–502
- Axelrod & Hamilton (1981) — *Science* 211(4489), 1390–1396
- Nowak & May (1992) — *Nature* 359(6398), 826–829
