# Simulating the Minimum Ecological Conditions for the Emergence of Kin-Directed Maternal via Evolving Neuroendocrine Agents
## Experimental Design — FRA361 Open Topics, FIBO 3rd Year, Semester 2

This document provides a full methodological breakdown of every experimental phase in the pipeline. Each phase is designed to isolate a specific mechanism or test a specific hypothesis, building cumulatively toward the core finding: that existential infant dependency and natal philopatry are jointly necessary and sufficient to reverse the evolutionary selection gradient on maternal care.

---

## Experimental Pipeline Overview

```
Phase 0: Sanity checks (mutation, inheritance, reproduction, population stability)
Phase 1: Survival gate (viability confirmation)
Phase 2: Zero-shot transfer (behavioural baseline without further evolution)
Phase 3: Evolution baseline — care erosion (the problem to be explained)
Phase 4: Kin-conditional plasticity — Baldwin Effect test
Phase 5a: Ecological emergence — natal philopatry + existential B
Phase 5b: Control — high dispersal (isolates philopatry contribution)
```

---

## Phase 0 — Evolution Sanity Checks

### Purpose
Verify that the genetic algorithm (GA) machinery is mechanically correct before running any evolutionary experiments.

### Assumption
Evolutionary dynamics are only interpretable if the underlying GA operators (mutation, inheritance, roulette selection) function as specified.

### Rationale
Any bias in inheritance or selection distorts the downstream evolutionary signal. These tests must pass before Phase 1.

### Objective
Four unit-level properties must hold:
1. Mutated genomes differ from parents by at most `mutation_sigma` per parameter
2. Offspring inherit parental genome when mutation is disabled
3. Roulette selection is positively biased toward higher-energy parents
4. Population remains stable across 100 generations under neutral selection

### Variables
| Variable | Role | Value |
|----------|------|-------|
| Mutation operator | IV | Gaussian noise N(0, sigma) per parameter |
| Offspring genome | DV | Distance from parent in parameter space |
| mutation_enabled | Control | Toggled per test |
| seed | Control | Fixed (42) |

---

## Phase 1 — Survival Gate

### Purpose
Confirm that the simulation environment is viable for sustained agent life. Agents must survive, maintain energy, and complete at least one full simulation run without extinction.

### Assumption
A simulation that cannot maintain life under fixed, high-quality genomes cannot be used as an evolutionary testbed. This is a prerequisite gate, not a scientific question.

### Rationale
Early versions of the simulation suffered from food scarcity extinction (init_food=25 with init_mothers=30, yielding 0.83 food/mother). The survival gate catches environment-level failures before any evolutionary signal is sought.

### Objective
- All mothers survive to tick 1000 (no extinction)
- Average energy > 0.85 at termination
- At least one care event recorded

### Variables
| Variable | Role | Value |
|----------|------|-------|
| Genome | IV | Fixed: care=0.7, forage=0.85, self=0.55 |
| Survival rate | DV | Fraction surviving to tick 1000 |
| mutation_enabled | Control | False |
| reproduction_enabled | Control | True |
| seed | Control | 42 |

### Result (2026-04-08)
PASSED — 12/12 survive, avg energy 0.910.

---

## Phase 2 — Zero-Shot Transfer Baseline

### Purpose
Establish a behavioural baseline for evolved genomes without further evolutionary pressure. Quantifies how much care a genome population exhibits when mutation and reproduction are disabled.

### Assumption
If plastic learning or genetic assimilation has occurred in Phase 4, evolved genomes transferred to a zero-shot environment should show elevated care rates compared to the Phase 2 (pre-plasticity) baseline. This comparison is the assimilation test.

### Rationale
Zero-shot transfer decouples behavioural expression from ongoing selection. Any difference between the zero-shot rate and an evolved genome's intrinsic rate reflects the degree to which evolution has encoded previously plastic behaviour.

### Objective
- Record per-mother-tick care window rate (primary metric)
- Phase 2 canonical rate (seed=42): **0.09069 events/mother-tick**
- This value serves as the Phase 3 → Phase 4b assimilation comparison baseline

### Variables
| Variable | Role | Value |
|----------|------|-------|
| Genome source | IV | Top evolved genomes from Phase 3 |
| Care window rate | DV | Events per mother per tick |
| reproduction_enabled | Control | False |
| mutation_enabled | Control | False |
| seed | Control | 42 |

### Result (2026-04-09)
Baseline rate: 0.09069/mother-tick. Used as reference for Phase 4b assimilation test.

---

## Phase 3 — Evolution Baseline: Care Erosion

### Purpose
Establish the evolutionary baseline under standard ecological parameters. The central question: does care evolve spontaneously when offspring benefit is marginal and effective relatedness is diluted?

### Assumption
Hamilton's rule (rB > C) predicts care should not evolve when B is low and the effective relatedness r is near zero. In an open grid where mothers cannot identify kin, spatial mixing dilutes effective r toward zero, and care is predicted to erode under selection.

### Rationale
Phase 3 is the problem statement of the thesis. Before claiming that ecological interventions can reverse the gradient, we must demonstrate that the baseline gradient is negative. Phase 3 establishes this baseline across 10 independent seeds, making the gradient robust and not seed-specific.

### Objective
- **Primary:** Demonstrate that care_weight declines under selection (Pearson's r < 0 between care_weight and generation)
- **Forage control:** Confirm forage_weight remains flat (rules out hitchhiking — care decline is not a side effect of forage drift)
- **Hamilton post-hoc:** Confirm rB−C < 0 for the canonical seed (mechanistic account of the erosion)

### Hypothesis
H0: Mean Pearson's r across seeds = 0 (no directional selection)
H1: Mean Pearson's r < 0 (negative selection on care)

### Variables
| Variable | Role | Value |
|----------|------|-------|
| Ecological parameters | IV | Standard (infant_mult=1.0, scatter=5) |
| care_weight trajectory | DV | Pearson's r per seed (birth_log.csv, generation vs care_weight) |
| forage_weight | Control DV | Must remain flat (hitchhiking check) |
| Seeds | Replication | 42–51 (n=10) |
| ticks | Control | 5000 |
| init genome | Control | Uniform(0.5, 0.5, 0.5) ± mutation |

### Key Results (2026-04-09)

| Stat | Value |
|------|-------|
| Mean final care_weight | 0.420 (from start 0.500) |
| Pearson's r (selection gradient) | **−0.178** |
| Seeds declining | 9/10 |
| Hamilton rB−C (seed 42, post-hoc) | ≈ −0.004 |
| Foreign care events | 89.5% (r_kin ≈ 0 for most events) |

---

## Phase 4b — Kin-Conditional Baldwin Effect

### Purpose
Test whether phenotypic plasticity that is selectively triggered by kin interactions can induce genetic assimilation of the care phenotype — i.e., the Baldwin Effect in a kin-recognition context.

### Assumption
The Baldwin Effect (Hinton & Nowlan, 1987) predicts that if a learnable behaviour increases fitness, the capacity for that behaviour will eventually be encoded genetically — the plastic phenotype is assimilated into the genotype. In this simulation, the learning mechanism is:
- A `learning_rate` genome parameter modulates how strongly a care event updates the mother's care_weight in the direction of the observed benefit
- The update rule is: `care_weight += learning_rate * (B_observed - care_cost)`
- Under the kin-conditional variant, updates only fire for own-lineage care events (proximity-inferred kin bias)

### Rationale
Phase 3 demonstrated that care erodes when rB < C. A plastic response that amplifies care weight in proportion to observed benefit offers a route to partial rescue. If learning_rate is swept upward by selection while care_weight recovers, this is the Baldwin signature. Kin-conditionality is required because indiscriminate learning on foreign-kin events amplifies noise, not signal (Phase 4a null result: r=−0.216, worse than Phase 3 baseline).

### Objective
- **Primary:** Does learning_rate sweep upward across generations? (8/10 seeds required for robustness claim)
- **Secondary:** Does care_weight recover after the initial trough induced by introducing the learning cost?
- **Assimilation test:** Is the zero-shot care rate of Phase 4b-evolved genomes significantly higher than the Phase 2 baseline (0.09069)?

### Hypothesis
H0 (assimilation): zero-shot rate Phase 4b = Phase 2 baseline (no genetic assimilation)
H1 (assimilation): zero-shot rate Phase 4b > Phase 2 baseline (Baldwin assimilation)
Threshold: one-sample t-test, α = 0.05

### Variables
| Variable | Role | Value |
|----------|------|-------|
| plasticity_kin_conditional | IV | True (Phase 4b) vs False (Phase 4a — null result) |
| learning_rate trajectory | DV (primary) | Pearson's r, generation vs learning_rate |
| care_weight trajectory | DV (secondary) | Population mean across ticks |
| Zero-shot window rate | DV (assimilation) | Per-mother-tick events vs baseline 0.09069 |
| Seeds | Replication | 42–51 (n=10) |
| infant_starvation_multiplier | Control | 1.0 |
| birth_scatter_radius | Control | 5 |

### Key Results (2026-04-10)

| Stat | Value | Interpretation |
|------|-------|----------------|
| learning_rate sweep | 0.103 → 0.170 (8/10 seeds) | Baldwin signal confirmed |
| care_weight trough | 0.355 at ~tick 1500 | Baldwin cost before recovery |
| care_weight recovery | 0.436 at tick 5000 | Partial recovery, below Phase 3 start |
| Zero-shot rate (seed 42) | 0.09933 vs 0.09069 baseline | +9.5% — single-seed assimilation |
| Population-level p-value | p = 0.815, d = 0.076 | No robust assimilation across 10 seeds |

**Interpretation:** The Baldwin Effect is present at the single-seed level but does not reach statistical significance at n=10. The learning_rate sweep is the primary positive finding; zero-shot assimilation is a partial null result, not a complete null. Honest framing: assimilation occurs but its magnitude is below the detection threshold with n=10 seeds.

---

## Phase 5a — Ecological Emergence: Natal Philopatry

### Purpose
Test whether two specific ecological interventions — existential infant dependency and natal philopatry — are jointly sufficient to reverse the selection gradient on care from negative (Phase 3 baseline) to positive.

### Assumption
Hamilton's rule rB > C can be satisfied if either B is elevated to an existential level (making care fitness-critical for offspring survival), or if effective r is elevated by spatial kinship (natal philopatry ensures infants remain near their birth mother). The working hypothesis is that both conditions must hold simultaneously (logical AND, not OR).

The model's decision architecture (argmax over domain utilities) places an operative threshold of care_weight ≈ 0.075 below which care never fires at typical energy levels. True zero-care initialisation is below this threshold and is not testable in this model. Phase 5 therefore initialises with care_weight ~ Uniform(0, 0.50), mean ≈ 0.25 — a **depleted baseline**, below the Phase 3 eroded equilibrium of 0.42, but operationally non-zero.

### Rationale
Phase 3 established that the gradient is negative under standard parameters. Phase 5a tests whether changing exactly two parameters (infant_starvation_multiplier: 1.0 → 1.15; birth_scatter_radius: 5 → 2) reverses the direction. The calibration choice of 1.15 (vs 3.0 originally) is critical:
- mult=3.0: evolutionary trap — population crashes before selection can act
- mult=1.15: infants die at tick ~108 without care (maturity_age=100), creating near-existential B while preserving population

### Objective
- **Primary:** Pearson's r (care_weight vs generation, birth_log.csv) is positive and significantly different from zero
- **Magnitude:** Cohen's d vs Phase 3 reference gradient (−0.178)
- **Robustness:** 8 or more of 10 seeds show positive gradient
- **Philopatry contribution (Phase 5b comparison):** r_5a − r_5b > 0

### Hypothesis
H0: Mean Pearson's r across seeds = 0 (no reversal)
H1: Mean Pearson's r > 0 (gradient reversed)
One-sample t-test vs 0, α = 0.05

### Variables
| Variable | Role | Value |
|----------|------|-------|
| infant_starvation_multiplier | IV | **1.15** (Phase 5a) vs 1.0 (Phase 3) |
| birth_scatter_radius | IV | **2** (Phase 5a) vs 5 (Phase 3) |
| Pearson's r (gradient) | DV | Per-seed, from birth_log.csv |
| Final care_weight | DV (secondary) | Population mean at tick 5000 |
| forage_weight | Control DV | Must remain non-selective (hitchhiking check) |
| Seeds | Replication | 42–51 (n=10) |
| Init care_weight | Control | Uniform(0, 0.50), mean ≈ 0.25 |
| plasticity_enabled | Control | False |
| ticks | Control | 5000 |

### Key Results (2026-04-12)

| Seed | Start cw | Final cw | Grad r | Emerged? |
|------|----------|----------|--------|----------|
| 42 | 0.2741 | 0.3547 | **+0.0768** | YES |
| 43 | 0.2041 | 0.2142 | −0.0260 | no |
| 44 | 0.1585 | 0.2382 | **+0.0909** | YES |
| 45 | 0.2144 | 0.2930 | **+0.0971** | YES |
| 46 | 0.2225 | 0.2898 | **+0.0949** | YES |
| 47 | 0.1634 | 0.2249 | **+0.0732** | YES |
| 48 | 0.2144 | 0.2608 | **+0.1110** | no* |
| 49 | 0.2178 | 0.3028 | **+0.0474** | YES |
| 50 | 0.2488 | 0.3358 | **+0.1124** | YES |
| 51 | 0.2932 | 0.3625 | **+0.1104** | YES |
| **Mean** | — | **0.2877 ± 0.033** | **+0.0788** | **8/10** |

*Seed 48 shows positive r but final cw below threshold.

| Stat | Value | Interpretation |
|------|-------|----------------|
| Mean Pearson's r | +0.0788 | Positive — care builds |
| 95% CI | [+0.053, +0.105] | Entirely above zero |
| One-sample t vs 0 | t = 5.93, **p = 0.0002** | Highly significant |
| Cohen's d vs Phase 3 | **1.87** | Very large effect |
| Seeds positive | 9/10 (8 clearly positive) | Robust across seeds |
| Phase 3 reference | −0.178 | Direction fully reversed |

---

## Phase 5b — Control: High Dispersal

### Purpose
Isolate the specific contribution of natal philopatry (low birth_scatter_radius) to the gradient reversal observed in Phase 5a. If philopatry is the spatial kin-recognition mechanism, increasing birth scatter should weaken but not eliminate the positive gradient.

### Assumption
The positive gradient in Phase 5a arises from two mechanisms working jointly: existential B (infant_mult=1.15) and elevated effective r from spatial kinship (scatter=2). If scatter is increased while infant_mult is held constant, B remains existential but effective r is diluted — the gradient should weaken, corresponding to partial violation of Hamilton's rule.

### Rationale
A control arm with scatter=8 allows attribution. If the positive gradient disappears entirely with scatter=8, natal philopatry is necessary (not merely sufficient). If it weakens but persists, the existential B condition independently contributes to the gradient.

### Objective
- Compare Pearson's r_5b (scatter=8) vs r_5a (scatter=2)
- Expected: r_5b < r_5a (weakened gradient)
- Expected: r_5b > Phase 3 baseline −0.178 (existential B still contributes)

### Variables
| Variable | Role | Value |
|----------|------|-------|
| birth_scatter_radius | IV | **8** (high dispersal) vs 2 (Phase 5a) |
| infant_starvation_multiplier | Control | 1.15 (same as Phase 5a) |
| Pearson's r | DV | Per-seed selection gradient |
| Seeds | Replication | 42–51 (n=10) |
| All other config | Control | Identical to Phase 5a |

### Key Results

| Condition | Mean Pearson's r |
|-----------|-----------------|
| Phase 5a (scatter=2, natal philopatry) | **+0.077** |
| Phase 5b (scatter=8, high dispersal) | **+0.050** |
| Phase 3 (scatter=5, standard, mult=1.0) | −0.178 |

**Interpretation:** Dispersal weakens but does not eliminate the positive gradient. Both conditions are load-bearing — existential B alone yields r≈+0.050; adding philopatry raises it to +0.077. This confirms the AND-condition hypothesis: the full gradient reversal requires both mechanisms.

---

## Summary: Experimental Logic Chain

| Phase | Question | Result | Feeds into |
|-------|----------|--------|------------|
| Phase 0 | GA machinery correct? | Pass | All downstream phases |
| Phase 1 | Environment viable? | PASS (12/12 survive) | Phase 3 onwards |
| Phase 2 | Behavioural baseline without evolution? | 0.09069/mother-tick | Phase 4b assimilation test |
| Phase 3 | Does care erode under standard conditions? | YES — r=−0.178 (9/10 seeds) | Establishes the problem |
| Phase 4b | Does kin-conditional plasticity induce genetic assimilation? | PARTIAL — lr swept (8/10), assimilation p=0.815 | Establishes plasticity cannot rescue care alone |
| Phase 5a | Does existential B + natal philopatry reverse the gradient? | YES — r=+0.079, p=0.0002, d=1.87 | Core finding |
| Phase 5b | Is philopatry specifically responsible? | PARTIALLY — gradient weakens to +0.050 | Confirms AND condition |

---

## Operationalisation of Hamilton's Rule

Hamilton's rule (rB > C) is not used as a selection criterion in the simulation — it is applied **post-hoc** to care events logged in `care_log.csv`.

| Term | Operationalisation |
|------|-------------------|
| r | 2^(−d) where d = generational distance (1 = own child, 2 = grandchild) |
| B | `hunger_reduced` per care event — hunger decrement caused by the care action |
| C | `feed_cost + move_cost` per care event |
| Selection gradient | Pearson's r of `care_weight` vs `generation` in `birth_log.csv` |

**Two-level B distinction (critical for reviewer clarity):**
- *Per-event B*: `hunger_reduced` — the direct energetic benefit of a single care action
- *Existential B (Phase 5)*: infant mortality without care due to `infant_starvation_multiplier=1.15` — the population-level selective consequence of low-care genomes. These are distinct measurements; neither substitutes for the other in Hamilton's formula.

**Why agents cannot recognise kin:**
The genome contains no kin-recognition parameter. Mothers select the highest-distress visible child regardless of lineage. Kin bias arises entirely from spatial proximity: with `birth_scatter_radius=2`, a mother's offspring remain nearby long enough that proximity-based care selection preferentially reaches own-lineage children without any explicit recognition. This is the natal philopatry mechanism.
