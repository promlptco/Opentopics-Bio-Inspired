# Experimental Design & Methodology
**Project:** Simulation of the Minimum Ecological Conditions for the Emergence of Kin-Biased Maternal Care Using Evolving Neuroendocrine Agents
**Research Question:** Under what minimum ecological conditions can kin-biased maternal care evolve from a depleted baseline, and can it become genetically assimilated as instinct?

---

## Core Research Philosophy

> **The primary aim is not to monitor whether `care_weight` rises or falls. The aim is to discover the minimum ecological conditions under which maternal care instinct *emerges* from natural selection — without being pre-programmed, biased in, or assumed.**

A valid phase in this project must satisfy all three of the following requirements:

**1. Gradient sensitivity, not a biased environment.**
The ecology must be responsive: small parameter changes produce measurable, proportional behavioral changes. A flat response means the parameter is not an evolutionary lever. A cliff-edge collapse means the system is too brittle to support natural emergence. The target is a smooth gradient where ecology *shapes* selection pressure — not forces a particular outcome. This is not a claim of finding the global optimum; it is a systematic search for the conditions that are necessary and sufficient.

**2. No magic numbers.**
Every parameter value must be justified by biological reasoning — mammalian physiology, documented survival timescales, ecological precedent — not tuned post-hoc to produce a desired result. Parameters without principled justification are confounds, not controls. If a parameter value cannot be explained to another biologist in one sentence from first principles, it must be rederived.

**3. Emergence, not confirmation.**
This project discovers what ecological conditions are *necessary* for maternal care instinct to arise. A result showing that care does not emerge under a given ecology is a valid and important scientific finding — not a failure to be explained away. No phase is designed to confirm a hypothesis; each is designed to test a necessary lemma in a proof-by-construction argument.

**The evolutionary endpoint** is *maternal instinct*: care behavior that is genetically encoded (high `care_weight` in the fixed genome) and no longer requires learned reinforcement (plasticity declines after assimilation). The proposed mechanism is the **Baldwin Effect**: ecological pressure first selects for plastic (learned) behavior, which is later genetically assimilated as instinct.

---

## 0. Thesis Architecture

The thesis establishes the minimum ecological conditions for the emergence of kin-biased maternal care using evolving neuroendocrine agents.

**Core question (Ecological):** Maternal care evolves under natural selection when specific ecological conditions hold — existential infant dependency and/or natal philopatry. The exact necessity of each condition is an empirical question, not an assumption. The experiment is designed to discover the answer, not confirm a preconceived one.

The pipeline is designed so that each phase either *proves a necessary lemma* or *serves as a control* for the phase that follows. No phase is redundant. Results from each phase propagate forward — if a phase produces a surprising result, the downstream phases must be re-examined before continuing.

---

## 1. Global Simulation Parameters

> See **LOGIC.md** for the complete biological reasoning behind every architectural decision, all approved pending changes, and the precise biological analogs for each parameter.

Unless explicitly overridden by a phase, all runs use the following defaults:

### Locked Architectural Parameters (cannot change between phases)

| Parameter | Value | Rationale |
|---|---|---|
| Time convention | **5 ticks = 1 day** | Ecologically meaningful timescales map to tractable ticks. All durations expressed in both units. |
| Grid size | **50 × 50** | 2500 cells — required for realistic spatial separation at population sizes of 20+ agents. 30×30 was too crowded (inflated food encounter rates). |
| Grid type | 2D discrete grid-world | Spatial proximity is a key evolutionary variable (natal philopatry, warm behavior). |
| Decision architecture | Softmax (Gibbs) Sampling over utility scores {Care, Forage, Self} | Stochastic selection proportional to utility — enables exploration and naturalistic decision errors. |
| Softmax Temperature (τ) | **0.1** (in `Config.softmax_tau`) | At τ=0.1 top action wins ~95% of the time. Low τ ≈ Argmax but retains stochasticity. |
| Reproduction gate | **Sigmoid probability** P = 1/(1+exp(-(energy−0.85)/0.05)) | Fitness-proportional: higher energy → higher P(reproduce). Midpoint at 0.85, near-zero below 0.7. |
| Feed proximity | **Same cell (dist = 0)** | Direct resource transfer requires physical co-location, consistent with food-picking rule. |
| Food proximity | **Same cell (dist = 0)** | Mother must stand on food cell to pick it up. |
| Warm behavior radius | **3 cells** | Mother's body heat reduces infant hunger rate by up to 30% when within 3 cells. Passive spatial benefit. |
| One child per lifetime | **has_reproduced = False flag** | Scopes study to dyadic mother-infant bonds; prevents multi-child care confounds. |
| Mother max age | **400 ticks (80 days)** | One full adult lifetime. Forces generational turnover; prevents immortal founders dominating evolution. |
| Child maturity age | **200 ticks (40 days)** | Infancy period. Infant is dependent for the first 40 days, then matures into a new mother. |
| Mutation rate | **In `Config.mutation_rate` = 0.1** | Stochastic P(mutate) per gene per reproduction event. |
| Mutation magnitude | **In `Config.mutation_sigma` = 0.05** | Gaussian N(0, σ=0.05) per gene, bounded [0,1]. Prevents drift explosion. |
| Commitment rule | **Outcome-based: until child.hunger < 0.3 or 20 ticks** | 20 ticks = 4 days. Commit to a care episode until the infant is sated or time-out. |

### Derived Ecological Parameters (fixed by starvation-constraint analysis)

| Parameter | Value | Derivation |
|---|---|---|
| `initial_energy` | **1.0** | Full energy at birth — every agent starts equal. |
| `hunger_rate` | **1/35 ≈ 0.0286 per tick** | Adult starves in 35 days (175 ticks) without food. |
| `infant_starvation_multiplier` | **35/15 ≈ 2.33** | Infant starves in 15 days without care — makes B existential (alive/dead), not marginal. |

### Phase-Determined Parameters (set by Phase 2 sweep)

`eat_gain`, `init_food`, `move_cost`, `rest_recovery` — values determined by ecological sweep in Phase 2 remake. Not hardcoded here.

### Statistical Validity Requirements

Every phase that makes a *causal or directional claim* must satisfy:

- **Multi-seed:** 10 seeds minimum (42–51). Single-seed results are exploratory only and must be labeled as such.
- **Reporting format:** Mean r ± SD, number of seeds with predicted sign, one-tailed binomial p-value.
- **Sufficiency threshold:** 9/10 or 10/10 seeds in predicted direction (p ≤ 0.05 binomial). 8/10 is marginal and must be flagged.
- **Plots required:** Per-seed trajectory + mean ± SD band. Never report only the mean.
- **Honesty rule:** If results are mixed or unexpected, report them as-is. Do not omit seeds or rerun selectively. Unexpected findings must be discussed, not buried.

---

## 2. Experimental Pipeline

### Phase Structure Overview

```
Phase 1  Mechanics Tests        ──► engine operators are correct
Phase 2  Survival Minimal       ──► foraging loop works
Phase 3  Survival Full          ──► find viable motivation weights; characterize care behavior
  3a     Motivation Sweep       ──► grid search (care × forage × self) → select canonical genome
  3b     Action Visualization   ──► what does care look like in sim? action sequences, frequencies
Phase 4  Evolution Baseline     ──► does care evolve or erode under standard ecology? (open question)
```

---

### Phase 1 · Mechanics Tests

**Purpose:** Verify genetic operators before any evolutionary run. A bug here invalidates everything downstream.

**Protocol:**
- Unit tests for: mutation boundedness (Gaussian, values stay in [0,1]), inheritance fidelity (parent → offspring copy is exact and independent), reproduction gate logic (energy threshold, cooldown, child-present block), population stability (no extinction, no explosion, deterministic across identical seeds).
- Note: roulette wheel normalization was originally listed here but the simulation uses sigmoid-probability reproduction (not a fixed threshold). There is no roulette wheel to normalize. This test was intentionally omitted — see Session Notes.

**Additional tests (amended 2026-04-14):**

- **Test 05 · Stochasticity Identity:** Verify that identical seeds produce 100% identical results (deterministic reproduction), but changing the seed — even slightly — produces meaningfully different action sequences. Confirms stochastic mechanics are seed-controlled, not truly random.
- **Test 06 · Softmax Calibration:** Verify that actions with higher utility are selected more frequently in proportion to the Softmax equation. Given two actions with clearly different utility scores, the higher-utility action must win at a rate consistent with Softmax(τ=0.1). Confirms the selection mechanism is correctly implemented.

**Success criteria:** 100% pass rate. Any failure must be resolved before proceeding.

**Outputs:** Test log only. No plots required.

---

### Phase 2 · Survival Minimal (Baseline Calibration & Sensitivity Analysis)

**Purpose:** Confirm that the core foraging loop and decision-making architecture are stable under stochastic pressure, and identify a canonical "Balanced" baseline parameter set that places the population at the **Edge of Stability** — alive under normal conditions, but susceptible to collapse when any single ecological parameter is worsened.

**Protocol (Pipeline mode — `--mode pipeline`):**
- **Mode:** Foraging only. No reproduction, no care, no mutation.
- **Decision Architecture:** Softmax (τ=0.1) Action Selection.
- **Environmental Noise:** ±20% Foraging Variance (`variance = U(0.8, 1.2)`).
- **Perceptual Noise:** Gaussian N(0, σ=0.1) added to perceived distance-to-food.
- **Grid:** 30×30, 15 mothers, `initial_energy = 0.75`.
- **Duration:** 1,000 ticks. N=50 independent seeds per configuration throughout.

**6-Step Automated Pipeline:**

1. **Synthetic baseline** — uses `BALANCED_BASELINE` from `config.py` as the starting center.
2. **OVAT sweep (N=50 per point)** — all five parameters swept one-at-a-time; each point averaged over 50 seeds.
3. **Dual-metric cliff-edge detection** — for each CLEAR parameter (survival range ≥ 0.20), finds the last stable point where survival ∈ [0.80–0.95] AND energy ∈ [0.65–0.75] with steepest next-step drop. UNCLEAR (flat) parameters become secondary axes in Step 4.
4. **Multi-dimensional validation grid (N=50 per config)** — base params = synthetic baseline; primary axis = `init_food` spanning harsh→easy zone (anchored between detected and synthetic food values, ±4 steps each side); secondary axes = UNCLEAR params × 5 evenly-spaced values.
5. **Penalty scoring selection** — scores all Step 4 configs; hard constraint violations = +1000/unit; soft terms penalize distance from targets: Balanced ≈ 14/15 survival + energy ≈ 0.70 + flat slope; Easy ≈ 15/15 + energy ≥ 0.85; Harsh ≈ 2–5/15 + energy ≤ 0.40.
6. **Diagnostic report generation** — full N=50 validation + complete diagnostic suite for all three selected conditions.

**Three Canonical Conditions** are selected automatically by the pipeline. Exact values depend on the OVAT-detected cliff-edge and are reported in `auto_baseline_summary.json`.


---

#### Phase 2 · OVAT Sensitivity Analysis

**Purpose:** Map the non-linear response of the system to each of the 5 ecological parameters, one at a time (One-Variable-at-a-Time / OVAT), to empirically justify the Balanced baseline and identify the Key Evolutionary Driver for Phase 3 and beyond.

**Protocol:**
- One parameter varied per set; all others fixed at `BALANCED_BASELINE` from `config.py`.
- **50 independent seeds per parameter value** (pipeline mode); N=15 (5 seeds × 3 repeats) in standalone `sensitivity_sweep.py`.
- Metric: tail_mean_energy (last 200 ticks) and survival rate (0.0–1.0).
- Script: `experiments/phase2_survival_minimal/sensitivity_sweep.py` (standalone) or embedded in `--mode pipeline`.

**Results Summary & Tipping Points:**

| Set | Parameter | Baseline Value | Tipping Point | Collapse |
|---|---|---|---|---|
| A | `hunger_rate` | 0.005 | ≈ 0.006 (+0.001) | < 20% survival at 0.008; full extinction at 0.012 |
| B | `move_cost` | 0.001 | ≈ 0.003 (+0.002) | < 50% survival at 0.004; extinction slope continues |
| C | `eat_gain` | 0.07 | ≈ 0.055 (−0.015) | < 20% survival at 0.04; full extinction at 0.03 |
| D | `init_food` | **70** | ≈ 40 (−43%) | < 50% survival at 36; near-extinction at 20 |
| E | `rest_recovery` | **0.005** | None detected | Flat response — nearly irrelevant (0.97–1.00 across all values) |


**Key Findings:**
1. **`hunger_rate` is the Key Evolutionary Driver (Set A):** The steepest collapse slope. A shift of +0.001 from baseline (0.005 → 0.006) drops survival from 99% to 94%. +0.002 drops it to 79%. Full extinction occurs at 0.012. This confirms hunger as the primary selection force.
2. **`move_cost` has moderate leverage (Set B):** Collapse begins around +0.002, but the decline is more gradual than hunger_rate — reflecting that Chebyshev pathfinding limits actual step counts.
3. **`eat_gain` shows a clear nutritional threshold (Set C):** Survival collapses sharply below 0.055. The baseline (0.07) sits safely above the 80% threshold, providing a known margin.
4. **`init_food` shows a non-linear cliff at 40 (Set D):** Above 50, survival is stable. Between 30–40, survival drops sharply. The confirmed baseline (`init_food=70`) sits **30 units above** this cliff, providing a generous safety margin.
5. **`rest_recovery` is negligible (Set E):** Survival remains ≥ 96% across the entire tested range (0.005–0.11). This parameter is not an evolutionary lever. The confirmed baseline (`rest_recovery=0.005`) is the minimum tested value, confirming this is the safest axis to hold fixed.


**Outputs:**
- `outputs/phase2_survival_minimal/sensitivity/<timestamp>/sensitivity_map.png` — 5-panel OVAT map.
- `outputs/phase2_survival_minimal/sensitivity/<timestamp>/set_A_hunger_rate.csv` (and B–E).
- `outputs/phase2_survival_minimal/sensitivity/<timestamp>/sensitivity_summary.json`.


---

### Phase 3 · Survival Full

**Purpose:** Two goals:
1. Find a reliable set of motivation weights (care / forage / self) under which mother + child both survive, with child energy not collapsing.
2. Characterize what care looks like behaviorally — what action sequences does a caring mother execute?

This phase defines the "functioning care" reference state used to interpret all subsequent phases.

---

Before doing Phase 3, use Phase 2 to find the baseline and observe the dynamic of the first generation of mother + child (no reproduction). Care-related code spans these 4 files: run.py, plot.py, sensitivity_sweep.py, config.py.

#### Phase 3a · Motivation Sweep

**Purpose:** Empirically validate the canonical genome via structured sweep. Values cannot be chosen arbitrarily — the selection must be reproducible and justified.

**Protocol:**
- Fixed genomes: `mutation=False`. Drop mother + infant into sim, observe.
- **Mother ecological parameters:** Copied from the Phase 2 pipeline-selected balanced baseline (`auto_baseline_summary.json`): `perception_radius=8`, `hunger_rate=0.005`, `move_cost=0.001`, `eat_gain=0.07`, `init_food=48`, `rest_recovery=0.11`. This isolates the effect of the child — any difference in survival outcome relative to Phase 2 is attributable to caregiving demand, not to a shifted ecological regime.
- Grid search:
  - `care` ∈ {0.3, 0.5, 0.7, 0.9}
  - `forage` ∈ {0.5, 0.7, 0.85, 1.0}
  - `self` ∈ {0.3, 0.5, 0.7}
- **Seeds:** 15–30 independent seeds per combination. Single-seed results are not accepted.
- Per combination, run 1,000 ticks and record:
  - Mother survival rate
  - Child survival rate
  - Mother energy trajectory
  - Child energy trajectory
  - Motivation selected event count (mean ± SD across seeds)

**Selection criteria for canonical genome:**
- Both mother AND infant survive to tick 1,000.
- Child energy stable after initial adjustment.
- Care events non-trivial — care is actively happening.
- Among all passing configs, prefer the *lowest* care weight that still satisfies the above. Avoids an artificially generous baseline.
- **Tie-breaker:** If two or more configurations share the same (lowest) care weight, select the one with the highest mean mother energy averaged across all seeds and all 1,000 ticks. More energetic mothers are more robust to downstream ecological stress.

**Required outputs:**
- Heatmap or table: (care, forage) × child survival rate and child energy at tick 1,000.
- Selected genome explicitly documented and justified with reference to sweep data.

---

#### Phase 3b · Action Visualization

**Purpose:** Establish ground-truth behavioral picture of maternal care in the sim. When later phases claim "care is occurring," this is the reference.

**Protocol:**
- Run selected canonical genome from Phase 3a for 500 ticks.
- Log every action taken by every mother agent at every tick.
- Each motivation maps to a sub-action sequence, e.g.:
  - Care → scan for distressed infant → move toward infant → feed / keep food nearby
  - Forage → search grid → harvest → return
  - Self → eat stored food → rest

**Required characterization:**
1. Action frequency breakdown — % Care / Forage / Self across all ticks and agents. Within Care: which sub-actions dominate?
2. Temporal pattern — does care frequency shift over 500 ticks or stay stable?
3. Spatial co-location — are care actions occurring near infant positions?

**Required plots:**
1. Stacked area chart: action type distribution aggregated per tick window.
2. Single-agent raster: one representative mother, color-coded action per tick.
3. Child energy over time with care event markers **and Distance-to-Child overlaid on the same graph** (secondary y-axis or normalized scale). Co-occurrence of care events with low distance-to-child is spatial evidence that mothers are physically present during caregiving — not just selecting CARE as a motivation while standing far away.

**Output:** A concise behavioral description referenced in the final report. Example: *"Under genome (care=0.7, forage=0.85, self=0.55), mothers spend 38% of ticks on care, predominantly: move-toward-infant → feed. Care clusters in ticks 0–200 when infant energy is lowest."*

---

### Phase 4 · Evolution Baseline

**Purpose:** Observe how care_weight evolves under selection in a standard ecological environment. This is an **open empirical question** — outcome is not known in advance.

**NOTE: Before do this phase we must test the asynchronus evolution --> output: 100% pass or not**

> ⚠️ **Naming rule:** Directory is `phase4_evolution_baseline`. Do NOT rename to "care_erosion" until results confirm the direction. Naming a phase after its expected outcome introduces methodological bias.

**Protocol:**

| Parameter | Value | Rationale |
|---|---|---|
| infant_starvation_multiplier | 1.0 | Standard ecology — no existential infant dependency |
| birth_scatter_radius | 5 | Mixed spatial — weak kin clustering |
| care_weight init | Uniform(0.0, 1.0), Mean = 0.50 | Neutral starting point |
| mutation | ON | Evolution active |
| plasticity | OFF | Isolate evolutionary signal from learning |
| Duration | 10,000 ticks | Extended from 5,000 — stochastic system requires more ticks for selection signal to emerge |
| Seeds | 42–51 (10 seeds) | Statistical validity |

**Additional metric (amended 2026-04-14):** Track intra-population variance of `care_weight` across ticks. Rising variance suggests stochasticity is maintaining genetic diversity; collapsing variance suggests fixation. Report alongside mean trajectory.

**No zero-shot measurement in this phase.** Zero-shot would conflate behavioral measurement with evolutionary results.

**Required plots:**
1. Per-seed care_weight trajectory over 5,000 ticks (individual lines + mean ± SD band).
2. Pearson r distribution across 10 seeds (dot plot or histogram, mean marked).
3. All three motivation weights (care / forage / self) — detect hitchhiking.

**Interpretation gates:**
- **r < 0, ≥ 9/10 seeds negative:** Care erodes.
- **r > 0 (unexpected):** Stop. Re-examine parameters. This undermines the thesis premise. Do not proceed without understanding why.
- **r ≈ 0 (neutral):** Care is genuinely near-neutral — selection pressure is insufficient to move care_weight in either direction at this ecology. Do NOT treat as weak erosion. This is a clean null result and the correct Phase 4 outcome.

---
## 4. File & Code Standards

### Directory Structure

```
experiments/
  phaseN_<name>/
    config.py          ← phase-specific Config (imports root Config, overrides this phase only)
    run.py             ← CLI entrypoint (--headless/--live/--seed/--max_ticks; all Config fields overridable)
    *.py               ← phase-specific analysis scripts

outputs/
  phaseN_<name>/       ← mirrors experiments/ naming exactly
    <run_id>/          ← timestamp (YYYYMMDD_HHMMSS) or test ID
      results.csv      ← per-tick or per-generation data
      summary.json     ← key metrics, config snapshot, seed used
      plots/
        *.png          ← all required plots for this phase

shared/
  constants.py         ← all cross-phase constants (no phase may hardcode a value from another phase)
```

**Naming rule:** experiments/ and outputs/ subdirectory names must match exactly. `experiments/phase2_survival_minimal/` → `outputs/phase2_survival_minimal/<run_id>/`. This makes output provenance unambiguous.

**Phase output requirements:**
Every phase run must produce, at minimum:
1. `results.csv` — machine-readable data (tick, metric columns).
2. `summary.json` — config snapshot + key aggregate metrics.
3. All plots specified in the phase protocol (see §2 and §6).
4. A new dated entry in `REPORT.md` with expert-level analysis of the findings.

A phase is not considered complete until all four items exist on disk and are committed to the repository.

**Per-phase config pattern:**
```python
# experiments/phase2_survival_minimal/config.py
from config import Config

PHASE2_CONFIG = Config(
    max_ticks=10_000,
    init_mothers=20,
    # ... only parameters that differ for this phase
)
```

**CLI override pattern (all Config fields injectable from terminal):**
```bash
python experiments/phase2_survival_minimal/run.py --max_ticks 5000 --seed 99 --init_food 60
```

**Notes on divergence from original design:**
- Phase 3a (motivation sweep) and Phase 3b (action visualization) scripts were not implemented as
  standalone files; the canonical genome was selected manually from early runs.
- Phase 4 source scripts (`p3_care_erosion/`) were not retained. All outputs are preserved in
  `outputs/phase04_care_erosion/`. Results are final — re-running is not required.

### Shared Constants (`shared/constants.py`)

No phase may hardcode a value measured in another phase. All cross-phase constants are imported from `shared/constants.py`. Violation is a reproducibility failure.

---

## 5. Protocol Rules

- **Never fabricate results.** If a file does not exist on disk, say so. Do not infer from memory or prior session notes.
- **Never mark a phase DONE without verifying result files on disk AND REPORT.md has been updated.**
- **Never rerun only failing seeds.** All 10 seeds run together. Selective rerunning biases results.
- **Never name a phase after its expected outcome before running it.**
- **Pause before each phase.** Present the plan. Wait for questions. Proceed only after explicit approval.
- **Pause after each phase.** Do not continue until the user has pushed to origin.
- **If something unexpected happens, stop and report it.** Do not explain it away or proceed around it. Unexpected results must be understood before the pipeline continues.
- **REPORT.md is updated after every phase.** Write the analysis as if writing a research methods section: state what was run, what was found, what it means biologically, and what it implies for the next phase. Do not omit negative or null results.

---

## 6. Analysis Framework

All phases that produce an evolutionary result must be analyzed through three complementary lenses. These are not optional — they constitute the scientific content of the thesis.

---

### 6.1 Baldwin Effect — Genetic Assimilation Plot

**Hypothesis:** A behavior first expressed through lifetime learning (plasticity) will, under sustained selection pressure, become genetically encoded and no longer require learning to maintain its adaptive value.

**Operational definitions for this simulation:**
- **Fitness**: Proportion of children that survive to maturity per generation cohort. This is the inclusive-fitness-relevant quantity — a mother's evolutionary success is measured by surviving offspring, not by her own longevity.
- **Plasticity**: Mean `learning_rate` gene in the living mother population, sampled per generation window (not per tick). `learning_rate` is exclusively a care-plasticity gene — it governs the speed of `expressed_care_weight` adjustment per reward signal and has no effect on foraging or self-maintenance.

**Averaging rule — macro-average by lineage (not naive population mean):**

For each generation window t:
```
fitness_t    = mean over lineages_i [ survived_children_i / born_children_i ]
plasticity_t = mean over lineages_i [ mean(learning_rate of living mothers in lineage_i) ]
```

This weights each lineage equally regardless of size. Prevents a large dominant lineage from collapsing the entire population signal into its own trajectory. Lineages that went extinct contribute 0.0 survival rate — extinction is a valid fitness outcome, not a missing value.

**Required plot — Baldwin Curve (single figure, dual y-axis):**

Both fitness and plasticity are plotted on the **same figure** over the **entire simulation duration** (minimum 10,000 ticks; adjustable via `Config.max_ticks`):

- X-axis: Tick (0 to max_ticks). Generation windows sampled at fixed intervals (e.g., every 200 ticks = 40 days).
- Y-axis (left, blue): Fitness — macro-averaged child survival rate (0.0–1.0).
- Y-axis (right, orange): Plasticity — macro-averaged mean `learning_rate` (0.0–1.0).
- Both curves plotted per-seed (thin lines) + mean ± SD band (thick line + shaded region).

**Interpretation signatures:**
- **Assimilation (target outcome):** Fitness rises → Plasticity initially rises (learning is beneficial) → Plasticity later declines (genetic instinct replaces learned behavior, learning no longer needed).
- **Incomplete assimilation:** Fitness rises but plasticity does not decline — learning remains necessary; the genetic floor has not risen enough.
- **No selection signal:** Plasticity rises without fitness rising — learning is not producing any adaptive advantage; no selection pressure for assimilation exists.
- **Null result:** Both flat — ecology is insufficient to drive care emergence under these parameters. Report as-is.

---

### 6.2 Hamilton's Rule — Kin-Biased Altruism Analysis

**Hypothesis:** Maternal care is evolutionarily stable only when rB > C (Hamilton 1964). The simulation tests whether the ecological structure (natal philopatry + lineage tracking) produces care patterns consistent with this prediction as an *emergent* property — not because the agents compute rB > C.

**Operational definitions:**
- **r**: Genetic relatedness coefficient, computed by `LineageManager.get_relatedness()` as r = 2^(−d), where d = generation distance within the same founding lineage. Own child: r = 0.5.
- **B**: Benefit to recipient = `hunger_reduced` per care event (units: child hunger units, scale [0,1]).
- **C**: Cost to actor = total energy expended per care event (movement cost + feed_cost), scale [0,1].

**Required analysis:**
- Per phase: compute mean (rB − C) across all logged care events. A positive mean indicates care is evolutionarily favored under that ecology.
- Compare own-child events (r = 0.5) vs. allomothering events (r < 0.5): kin-biased care should show systematically higher rB for own-child events.
- **Scatter plot**: rB (y-axis) vs. C (x-axis), colored by `is_own_child` flag. Overlay the Hamilton boundary line (rB = C). Points above the line are evolutionarily stable care events; points below are altruistic losses.

---

### 6.3 Ecological Sensitivity — Parameter-Driven Emergence

**This is the "epigenetics" of the simulation.** Ecological parameters activate or suppress behavioral programs without changing the genome — analogous to how environmental signals alter gene expression in real organisms without altering DNA sequence.

**Analysis method:** For each phase transition introducing a new ecological condition, document:
1. Which parameter changed and by how much.
2. What behavioral shift occurred (action frequency distributions, child survival rate, care rate).
3. Whether the response is gradient (proportional) or threshold (step change at a tipping point).
4. Whether the behavioral shift led to a subsequent genetic change (directional selection on `care_weight`).

**Parameters of interest and their ecological roles:**

| Parameter | Phase Introduced | Ecological Role |
|---|---|---|
| `hunger_rate` | Phase 2 | Primary selection force — sets baseline mortality pressure |
| `init_food` | Phase 2 | Food density — sets ecological harshness gradient |
| `infant_starvation_multiplier` | Phase 5 | Infant dependency — makes care benefit existential, not marginal |
| `birth_scatter_radius` | Phase 5 | Natal philopatry — controls kin spatial clustering |
| `plasticity_noise_sigma` | Phase 8 | Learning unreliability — drives genetic assimilation of instinct |

**Output format for each parameter shift:** *"Changing X from A to B caused a Y% shift in Z. The behavioral tipping point is at [value], above which [behavior] emerges consistently in ≥ 9/10 seeds."*

---

### 6.4 Final Parameter Set — Scientific Deliverable

The output of this project is not only a result — it is a **validated, reasoned parameter set** that another researcher or ALife practitioner can reproduce and extend. Every parameter in the final configuration must be accompanied by:

1. Its biological justification (what in nature does it correspond to?).
2. The phase in which it was empirically validated.
3. Its sensitivity range (the parameter values at which the ecology transitions between regimes).

This deliverable is what distinguishes principled ALife from arbitrary simulation.

---

## Session Notes

*(append only — dated)*

**2026-04-14** — Reproduction mechanism audit (Phase 1 restart):
The global parameters table originally listed "Roulette wheel on accumulated energy" as the reproduction mechanism. Code audit of `simulation/simulation.py:_check_reproduction()` found this to be inaccurate. Actual mechanism: every mother with `energy ≥ reproduction_threshold` (0.95) reproduces each tick — energy-threshold, not probability sampling. The mechanism is still effectively fitness-proportional (higher-energy mothers reproduce sooner/more often) but there is no probability vector to normalize. Roulette wheel normalization test was removed from Phase 1 protocol and the global parameters table was corrected. No code change required.

**2026-04-30** — Design document audit:
Four errors corrected: (1) Sigmoid reproduction gate and perceptual/foraging noise were listed as implemented but were never added to the simulation code — global params table corrected to reflect actual implementation. (2) Phase 4 r≈0 interpretation gate "treat as weak erosion" corrected — r≈0 is the confirmed definitive result, not a marginal case. (3) Evolution duration corrected from 5,000 to 10,000 ticks in global table. (4) Thai character artifact removed from Phase 3 note.

**2026-04-14** — Stochastic mechanics update (Global Parameters amended):
Decision architecture updated from Argmax to Softmax (Gibbs) Sampling with τ=0.1. Reproduction gate updated from hard-threshold to sigmoid probability (midpoint=0.95). Kin recognition noise Gaussian N(0, σ=0.1) added. Foraging variance ±20% added. Mutation rate made stochastic per gene. Implementation notes:
- Replace `reproduction_threshold` hard-check with `sigmoid_prob` (midpoint=0.95) in reproduction logic.
- Use `numpy.random.choice` with Softmax-derived weights for action selection.
- Record τ=0.1 and σ_percept=0.1 in `shared/constants.py`.
- Phase 4 duration extended to 10,000 ticks to account for slower signal emergence under stochastic system.
- Two new Phase 1 tests added: Test 05 (Stochasticity Identity) and Test 06 (Softmax Calibration).

**2026-05-04** — Major architectural overhaul & analysis framework finalization:

All decisions below are **approved and locked** before Phase 2 remake. Full biological reasoning in **LOGIC.md**.

Architectural changes approved:
1. Grid size locked at **50×50** for all phases.
2. **Neutral demand-signal cues**: forage_cue = food proximity [0,1]; self_cue = energy deficit [0,1]; care_cue = child.distress only (mother cannot read child.hunger directly).
3. **Same-cell feeding** (dist = 0) for both food pick-up and child feeding. Warm behavior uses radius ≤ 3 cells (passive heat effect).
4. **Outcome-based commitment**: commit until child.hunger < 0.3 or 20 ticks.
5. **Sigmoid reproduction gate**: P = 1/(1+exp(-(energy−0.85)/0.05)).
6. **One child per lifetime** via `has_reproduced` flag.
7. **softmax_tau, mutation_rate, mutation_sigma** moved into root Config (CLI overridable).
8. **Warm behavior**: within 3 cells, child hunger_rate × (1 − 0.3 × warmth_proximity). Passive spatial effect.
9. **Mother max age = 400 ticks (80 days). Child maturity = 200 ticks (40 days).**
10. **Derived starvation parameters**: initial_energy=1.0, hunger_rate=1/35≈0.0286, infant_starvation_multiplier=35/15≈2.33.

Analysis framework finalized:
- **Baldwin Curve**: fitness AND plasticity on the SAME figure (dual y-axis), over entire simulation (≥10,000 ticks, adjustable via max_ticks). Macro-averaged by lineage: each lineage contributes one mean value per generation window; final metric is mean of lineage means. Never a naive population mean.
- **Hamilton scatter**: rB vs C per care event, colored by is_own_child, Hamilton boundary line rB=C overlaid.
- **Ecological Sensitivity**: per-parameter behavioral tipping points documented.

Output standard finalized:
- Every phase produces: results.csv + summary.json + plots/ + REPORT.md entry.
- outputs/ mirrors experiments/ naming exactly.
- Phase is not done until all four artifacts exist on disk and are committed.