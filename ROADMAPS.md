# ROADMAP.md — Experimental Roadmap Aligned with LOGIC.md

**Project:** Simulation of the Minimum Ecological Conditions for the Emergence of Kin-Biased Maternal Care Using Evolving Neuroendocrine Agents  
**Research Question:** Under what minimum ecological conditions can kin-biased maternal care evolve from a depleted baseline, and can it become genetically assimilated as instinct?

---

## Source-of-Truth Rule

This roadmap separates the project into two layers:

1. **Coding / mechanics source of truth:** `LOGIC.md`  
   Use this for the actual simulation mechanics, class behavior, action rules, cue definitions, energy updates, reproduction logic, lineage tracking, logging, and folder/code conventions.

2. **Experimental source of truth:** `EXPERIMENT_DESIGN.md`  
   Use this for the experimental sequence, phase purpose, analysis framework, stopping rules, statistical validity, and reporting requirements.

---

## Core Scientific Philosophy

The goal is not simply to force `care_weight` to increase.  
The goal is to discover the minimum ecological conditions under which maternal care can emerge under natural selection.

A valid experimental phase must satisfy three rules:

1. **Gradient sensitivity**  
   The ecology should respond smoothly to parameter changes. A flat response means the parameter is not useful. A cliff collapse means the system is too brittle.

2. **No magic numbers**  
   Parameters must be justified either biologically or empirically. A value should not be chosen only because it gives the desired result.

3. **Emergence, not confirmation**  
   A null result is still valid. If care does not emerge under a condition, that is an important finding, not a failure.

The expected final endpoint is **maternal instinct**: care behavior becomes genetically encoded in the fixed genome and no longer depends strongly on learned reinforcement.

---

## Locked Simulation Architecture

These parameters must remain consistent across phases unless a phase explicitly tests them.

| Component | Roadmap Value | LOGIC.md Consistency Check |
|---|---:|---|
| Time convention | 5 ticks = 1 day | Keep all durations in both ticks and days. |
| Grid size | 50 × 50 | Required by current logic. |
| Decision architecture | Softmax over motivation utilities | Use `Config.softmax_tau`. |
| Softmax temperature | `tau = 0.1` | Low-temperature stochastic action selection. |
| Food pickup distance | Same cell, `dist = 0` | Mother must stand on food. |
| Child feeding distance | Same cell, `dist = 0` | If not same cell, CARE should move toward child. |
| Warm behavior | Passive, radius ≤ 3 | No separate WARM action. |
| Reproduction gate | Sigmoid probability | Midpoint `energy = 0.85`, scale `0.05`. |
| One child per lifetime | `has_reproduced` flag | Avoids multi-child confound. |
| Mother max age | 400 ticks = 80 days | Forces generational turnover. |
| Child maturity age | 200 ticks = 40 days | Infant dependency period. |
| Mutation rate | `Config.mutation_rate = 0.1` | Per-gene stochastic mutation. |
| Mutation sigma | `Config.mutation_sigma = 0.05` | Gaussian bounded mutation. |
| Commitment rule | Until child.hunger < 0.3 or 20 ticks | Outcome-based care episode. |
| Initial energy | 1.0 | Full energy at birth. |
| Adult hunger rate | `1/35 ≈ 0.0286` per tick | Adult starvation window = 35 ticks = 7 days. |
| Infant starvation multiplier | `35/15 ≈ 2.33` | Infant starvation window ≈ 15 ticks = 3 days when enabled. |
| Food spawn rate | remove food 1 times = add random pos food 1 time | this will makes the direct ecological interpret for food_init |

### Time-scale interpretation

```text
Adult starvation = 35 ticks = 7 days
Infant starvation with multiplier 35/15 = 15 ticks = 3 days
```

---

## Agent and Mechanism Assumptions

### Mother decision model

The mother uses a two-stage motivation system:

```text
Environmental cue × genome weight = motivation utility
```

The active motivation utilities are:

```text
FORAGE = forage_weight × forage_cue
SELF   = self_weight   × self_cue
CARE   = expressed_care_weight × care_cue
```

Where:

- `forage_cue = 1 - distance_to_nearest_food / perception_radius`
- `self_cue = 1 - energy`
- `care_cue = child.distress`
- all cues are clamped to `[0, 1]`

The mother must not read `child.hunger` directly for decision-making.  
She only reads the observable distress signal.

### Energy and rest economy

Energy can only be gained by eating food.  
REST does not directly restore energy. It reduces fatigue, which reduces future fatigue drain.

Per tick:

```text
energy -= hunger_rate
energy -= fatigue × fatigue_rate
```

Movement:

```text
energy  -= move_cost
fatigue += fatigue_rate
```

Self/rest:

```text
fatigue -= rest_recovery
```

This design keeps food density and foraging pressure meaningful.

### Care behavior

CARE should work as:

```text
If child is at same cell:
    feed child
Else:
    move one step toward child
```

A care episode can be committed for up to 20 ticks and ends early when the child becomes sated.

### Plasticity and Baldwin architecture

The fixed genome is inherited.  
The expressed care weight is learned within a lifetime and is not inherited.

```text
genome.care_weight          = genetic care floor
mother.expressed_care_weight = learned phenotype
```

Plasticity update:

```text
delta = learning_rate × reward × plastic_gain
expressed_care_weight += delta
energy -= learning_cost × |delta|
```

Reward should be based on actual `hunger_reduced`, not on merely choosing CARE.

---

# Experimental Pipeline

## Phase 1 — Mechanics Tests

### Purpose

Verify that the simulation operators are correct before running evolutionary experiments.

A bug in this phase invalidates all downstream phases.

### Scope

Phase 1 tests mechanics only. It should not make evolutionary claims.

### Required tests

1. **Mutation boundedness**  
   Mutated genes must remain within `[0, 1]`.

2. **Inheritance fidelity**  
   Offspring genome must be an independent copy of the parent genome.

3. **Sigmoid reproduction gate**  
   Reproduction probability must follow the sigmoid rule, not a hard threshold or roulette-wheel selection.

4. **One-child lifetime rule**  
   A mother must not reproduce again after `has_reproduced = True`.

5. **Population stability sanity check**  
   The simulation should not explode or collapse because of bookkeeping errors.

6. **Stochasticity identity**  
   Same seed must reproduce exactly the same trajectory. Different seeds should produce meaningfully different trajectories.

7. **Softmax calibration**  
   Higher utility actions must be selected more often, consistent with `tau = 0.1`.

8. **Care proximity rule**  
   Feeding should only succeed at `dist = 0`.

9. **Warm behavior rule**  
   Warmth must be passive. It should reduce child hunger-rate near the mother, not create a separate action.

10. **Lineage continuity through maturation**  
    A matured child must preserve lineage and parent links so relatedness remains valid.

### Success criteria

- 100% pass rate.
- Any failure must be fixed before Phase 2.
- Output can be a test log only. Plots are optional.

---

## Phase 2 — Survival Minimal / Ecological Baseline Calibration

### Purpose

Confirm that the mother-only foraging loop is stable and identify ecological conditions that produce meaningful survival gradients.

This phase calibrates the food and energy ecology before adding children, care, reproduction, mutation, or plasticity.

### Mode

Use mother-only survival mode:

| Subsystem | Status |
|---|---|
| Children | OFF |
| Care | OFF |
| Reproduction | OFF |
| Mutation | OFF |
| Plasticity | OFF |
| Active motivations | FORAGE, SELF |
| Active actions | MOVE, PICK, EAT, REST |

### Parameters to sweep

The Phase 2 sweep determines:

- `eat_gain` : [ 0.05,  0.1,  0.2,  0.5, 0.8]
- `init_food`: [   10,   20,   40,   80, 150]
- `move_cost`: [0.005, 0.01, 0.02, 0.05, 0.1]

The following are locked by LOGIC.md and should not be freely tuned:

- `grid = 50 × 50`
- `initial_energy = 1.0`
- `hunger_rate = 1/35`
- `softmax_tau = 0.1`

### Outputs

Phase 2 should produce 3 ecological conditions:

   HARSH:
   - target survival = 10–45%
   - strong survival pressure

   BALANCED:
   - target survival = 50–75%
   - main baseline for Baldwin Effect

   EASY:
   - target survival > 80%
   - low-pressure control

Exact parameter values must be selected from the sweep result, not manually invented.

### Recommended selection logic

Prioritize values for selecting the conditions follow this:
1. Survival rate = current_num_mother / init_mother
2. Population = current_num_mother at the end
3. Mean Energy = sum(energy)/init_mother
4. rest_recovery = use it for ensure the parameters that we have selected is makesense or not. If harsh the rest must be low, if easy the rest action must be more.

if rest = 0% the eco is too harsh, but if rest >= 40% the eco is too easy. must be noted

### Phase2 flows

#### Sub-Phase Prepration
1) Lock mechanics from LOGIC.md
   - grid = 50 × 50
   - initial_energy = 1.0
   - hunger_rate = 1/35
   - softmax_tau = 0.1
   - children/care/reproduction/mutation/plasticity = OFF

        ↓

2) Set provisional baseline
   Temporarily set the value of the parameter that does not yet have an answer.

   Example:
   - init_food = provisional value
   - eat_gain = provisional value
   - move_cost = provisional value
   - rest_recovery = fixed fatigue-recovery value

   This is not yet the final baseline. It's just used as a starting point for the sweep function to have a reference.
 
        ↓

#### Sub-Phase Initial Food Gradient
3) First-pass init_food scan
   Sweep only init_food with wide fine range

   Purpose:
   - Check if the system has a food-density gradient.
   - Find a rough region where neither everyone dies nor everyone survives.
   - Use this as an anchor for the next sweep.

   Example:
   init_food = [10, 20, 40, 80, 150] can be finer

   Output:
   - Select a rough anchor, such as low/medium/high food level.
   - this is not a final HARSH/BALANCED/EASY

        ↓

#### Sub-Phase OVAT Sweeping Method
4) OVAT sweep around anchor
   Sweep each parameter around the anchor.

   4A) init_food sweep
       - Check whether the food density around the anchor is a gradient, flat, or cliff.

   4B) eat_gain sweep
       - Check how much food reward affects survival.

   4C) move_cost sweep
       - Check how much the movement penalty affects survival.

   Important:
   - Change only one at a time.
   - The others are fixed to the provisional anchor.
   - The goal is to look at sensitivity, not to choose a final baseline.

        ↓

5) Build candidate ranges
   From OVAT, select the range of values ​​of interest for all three parameters.

   Example:
   - init_food_values = [low_food, mid_food, high_food]
   - eat_gain_values = [low_gain, mid_gain, high_gain]
   - move_cost_values = [low_cost, mid_cost, high_cost]

        ↓

6) Multi-parameter validation grid
   Overall Run grid:

   Deploit the mother.py in the world
   init_food × eat_gain × move_cost

   Purpose:
   - Look at the interaction between parameters.
   - Because survival doesn't depend on a single parameter.
   - Use this grid as the step to select the final set.

        ↓

7) Select canonical ecological regimes
   Select only from the validation grid.

   HARSH:
   - target survival = 10–45%
   - strong survival pressure

   BALANCED:
   - target survival = 50–75%
   - main baseline for Baldwin Effect

   EASY:
   - target survival > 80%
   - low-pressure control

   Prioritize values for selecting the conditions follow this:
   1. Survival rate = current_num_mother / init_mother
   2. Population = current_num_mother at the end
   3. Mean Energy = sum(energy)/init_mother
   4. rest_recovery = use it for ensure the parameters that we have selected is makesense or not. If harsh the rest must be low, if easy the rest action must be more.

        ↓

8) Final Plot
   each set must have these plot for their own condition: 

- Mean survival rate trajectory over horizon (blue, must have sd, individual line alpha=0.4, legend at bottom left)
- Mean energy trajectory over horizon (green, must have sd, individual line alpha=0.4, legend at bottom left)
- Relate action count for each motivation (3 motivation with the count of actions as barplot)
- Failed-action rate plots. (Barplot of overall action and failed compare for each action lebel the actions and its motivation)
- Food consumption rate. (plot food trajecotory over time)
- Spatial heatmap

---

## Phase 3 — Survival Full / Functioning Care Reference

### Purpose

Add mother-child interaction and find the **MVE (Minimum Viable Ecology)** — the least generous set of environmental parameters (food density, move cost, eat gain) under which mothers can still keep their infant alive to maturity.

This phase does not test evolution yet.  
It defines what functional care looks like in the simulation and establishes the MVE as the ecological baseline for all subsequent phases.

---

## Phase 3a — Motivation Sweep

### Purpose

Find a canonical fixed genome for care behavior.

This genome becomes the behavioral reference for later phases.

### Mode

| Subsystem | Status |
|---|---|
| Children | ON |
| Care | ON |
| Reproduction | OFF |
| Mutation | OFF |
| Plasticity | OFF |
| Genome | Fixed per sweep condition |

### Ecological parameters

Use the Phase 2 selected **BALANCED** ecology.

```text
Load ecological parameters from the selected Phase 2 balanced baseline summary.
Do not hardcode copied values inside Phase 3 scripts.
```

### Motivation grid

Start with the grid from `EXPERIMENT_DESIGN.md`:

```text
care   ∈ {0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0}
forage ∈ {0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0}
self   ∈ {0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0}
```

If this grid is too coarse, refine only around passing regions.

### Seeds and duration

- Use 15–30 independent seeds per combination.
- Single-seed runs are exploratory only.
- Run 400 duration, so we can watch the infants reach mature by mother

### Metrics

Record:

- Mother survival rate.
- Child survival rate.
- Mother energy trajectory.
- Child energy trajectory.
- CARE / FORAGE / SELF selection counts.
- Feed attempts and successful feed events.
- Distance-to-child during care.
- Child distress over time.

### Selection criteria

Select the canonical genome using this order:

1. Child survival rate = number of children who reached maturity_age (converted to MotherAgent) / total children born (including those who died before maturity). Aggregated across all lineages. A child that starves before maturity counts as a failed care event regardless of how long it survived.
2. Mother survival rate. 
3. Child energy does not collapse.
4. CARE events are non-trivial and spatially meaningful.
5. Prefer the lowest `care_weight` that passes.
6. Tie-break by higher mean mother energy.

### Required outputs

- Heatmap/table of child survival by genome.
- Heatmap/table of child final energy by genome.
- Selected canonical genome.
- Short explanation of why this genome is not artificially over-generous.

---

## Phase 3b — Action Visualization

### Purpose

Show what care actually looks like in the simulation.

This is the behavioral reference for later claims that “care is happening.”

### Protocol

Run the selected Phase 3a genome and log actions every tick.

### Required characterization

1. Action frequency:
   - CARE
   - FORAGE
   - SELF
   - MOVE
   - PICK
   - EAT
   - REST
   - FEED_CHILD

2. Temporal pattern:
   - Does care occur early, late, or throughout?
   - Does care cluster when child distress is high?

3. Spatial evidence:
   - Distance between mother and child.
   - Feed events must occur at same-cell proximity.
   - Warmth benefit should occur within warmth radius.

### Required plots

- Stacked area chart of actions over time.
- Single-agent raster plot.
- Child energy over time with care-event markers.
- Distance-to-child overlaid or shown alongside child energy.
- child distress over time with care-event markers.
- Mean survival rate trajectory over horizon (blue, must have sd, individual line alpha=0.4, legend at bottom left)
- Mean energy trajectory over horizon (green, must have sd, individual line alpha=0.4, legend at bottom left)
- Relate action count for each motivation (3 motivation with the count of actions as barplot)
- Failed-action rate plots. (Barplot of overall action and failed compare for each action lebel the actions and its motivation)
- Food consumption rate. (plot food trajecotory over time)
- Spatial heatmap

### Interpretation

A valid care behavior should show that mothers are not merely selecting CARE abstractly. They should physically move toward the child, co-locate, reduce distress, and successfully feed.

---

## Phase 4 — Evolution Baseline

### Purpose

Observe how `care_weight` evolves under standard ecology without special infant dependency and without plasticity.

This is an open empirical question.  
Do not name the phase after the expected result.

### Directory name

Use:

```text
experiments/phase4_evolution_baseline/
outputs/phase4_evolution_baseline/
```

Do not use names such as `care_erosion` until the result is known.

### Precondition

Before Phase 4, test asynchronous evolution mechanics.

Required pass condition:

```text
asynchronous evolution test = 100% pass
```

This should verify that birth, maturation, death, lineage updates, and generation turnover are correct over long runs.

### Protocol

| Parameter | Value |
|---|---|
| `infant_starvation_multiplier` | 1.0 |
| `birth_scatter_radius` | 5 |
| Initial `care_weight` | Uniform(0.0, 1.0) |
| Mutation | ON |
| Plasticity | OFF |
| Duration | 10,000 ticks |
| Seeds | 42–51 |

### Metrics

Track:

- Mean `care_weight`.
- Variance of `care_weight`.
- Mean `forage_weight`.
- Mean `self_weight`.
- Population size.
- Child survival to maturity.
- Birth and death counts.
- Lineage persistence.
- Pearson correlation of `care_weight` over time per seed.

### Required plots

- Per-seed `care_weight` trajectory over the full 10,000 ticks.
- Mean ± SD band for `care_weight`.
- Pearson r distribution across seeds.
- All three motivation weights over time.
- Population and lineage survival over time.

### Interpretation gates

| Result | Interpretation |
|---|---|
| `r < 0` in ≥ 9/10 seeds | Care erodes under standard ecology. |
| `r ≈ 0` | Care is near-neutral. This is a valid null result. |
| `r > 0` | Stop and re-check assumptions before continuing. |

Important:  
Do not treat `r ≈ 0` as weak erosion. It means the ecology is insufficient to create directional pressure on care.

---

## Phase 5 — Ecological Dependency and Philopatry Tests

### Purpose

Test whether maternal care becomes adaptive when infant dependency and/or natal philopatry are introduced.

This phase is implied by the analysis framework in `EXPERIMENT_DESIGN.md`, especially the parameters:

```text
infant_starvation_multiplier
birth_scatter_radius
```

### Why this phase is needed

Phase 4 tests standard ecology.  
Phase 5 tests whether the ecological conditions predicted by the thesis create selection pressure for care.

### Experimental factors

Use a factorial design:

| Factor | Low / Control | High / Treatment |
|---|---|---|
| Infant dependency | `infant_starvation_multiplier = 1.0` | `infant_starvation_multiplier ≈ 2.33` |
| Natal philopatry | Large scatter / weak clustering | Small scatter / strong clustering |

The exact `birth_scatter_radius` values should be chosen after checking the spatial scale of the 50 × 50 grid.  
A reasonable first design is:

```text
birth_scatter_radius ∈ {2, 5, 10}
infant_starvation_multiplier ∈ {1.0, 2.33}
```

### Mode

| Subsystem | Status |
|---|---|
| Children | ON |
| Care | ON |
| Reproduction | ON |
| Mutation | ON |
| Plasticity | OFF initially |
| Warm behavior | ON |
| Lineage tracking | ON |

### Metrics

- Child survival to maturity.
- Care event count.
- `care_weight` trajectory.
- Lineage persistence.
- Mean `rB - C` for care events.
- Own-child vs allomothering care.
- Spatial clustering around birth locations.

### Required analysis

Use Hamilton-style event analysis:

```text
rB - C
```

Where:

- `r` comes from lineage relatedness.
- `B` is hunger reduction.
- `C` is movement + feed cost.

### Interpretation

Care is favored when:

```text
mean(rB - C) > 0
```

and this coincides with improved child survival and directional change in `care_weight`.

---

## Phase 6 — Kin-Biased Care Analysis

### Purpose

Determine whether care is actually kin-biased, not just random helping.

### Protocol

Use the best-performing ecological conditions from Phase 5.

### Required comparisons

Compare care events by relationship:

| Event type | Expected pattern |
|---|---|
| Own child | Highest care probability and highest rB |
| Same lineage but not own child | Moderate care probability if spatial clustering exists |
| Unrelated child | Lower care probability unless distress dominates |

### Metrics

- Care event count by relatedness class.
- Mean `rB - C` by relatedness class.
- Child survival by lineage.
- Distance-to-child before CARE.
- CARE choice probability as a function of distress and relatedness.

### Required plots

- Hamilton scatter: `rB` vs `C`, colored by `is_own_child`.
- Care frequency by relatedness class.
- Child survival by lineage.
- Optional: spatial map of lineages and care events.

### Interpretation

If the model claims kin-biased maternal care, then own-child events should be separable from unrelated-care events either behaviorally, spatially, or in Hamilton-value terms.

---

## Phase 7 — Plasticity-On Baldwin Test

### Purpose

Test whether lifetime learning helps care appear before it becomes genetically encoded.

This phase turns plasticity ON.

### Mode

| Subsystem | Status |
|---|---|
| Children | ON |
| Care | ON |
| Reproduction | ON |
| Mutation | ON |
| Plasticity | ON |
| Plasticity noise | OFF initially |
| Learning-rate evolution | ON unless explicitly controlled |

### Key variables

Track separately:

```text
genome.care_weight
expressed_care_weight
learning_rate
child survival to maturity
```

### Expected Baldwin signature

A successful Baldwin-like trajectory should show:

1. Expressed care rises first.
2. Child survival improves.
3. Genetic `care_weight` rises later.
4. `learning_rate` may decline once genetic care is sufficient.

### Required plot

Baldwin curve:

- X-axis: tick or generation window.
- Left Y-axis: fitness / child survival to maturity.
- Right Y-axis: plasticity / learning rate.
- Show per-seed trajectories and mean ± SD.

### Important control

Do not let plasticity update `forage_weight` or `self_weight`.  
Plasticity must be scoped to care, otherwise the Baldwin signal becomes uninterpretable.

---

## Phase 8 — Genetic Assimilation Under Noisy Plasticity

### Purpose

Test whether unreliable learning creates stronger pressure for genetic assimilation.

This follows the LOGIC.md mechanism:

```text
plasticity_noise_sigma > 0
```

### Experimental factor

Sweep:

```text
plasticity_noise_sigma ∈ {0.0, low, medium, high}
```

Exact values should be calibrated so noise is meaningful but not destructive.

### Optional control

Use:

```text
lock_learning_rate = True
```

when the goal is to stop evolution from solving the task only by becoming a better learner.

### Metrics

- Genetic `care_weight`.
- Expressed `care_weight`.
- `learning_rate`.
- Child survival to maturity.
- Plasticity cost.
- Variance across seeds.

### Interpretation

Evidence for genetic assimilation:

```text
fitness remains high
genome.care_weight rises
learning_rate declines or becomes less necessary
expressed-care gap shrinks
```

Where:

```text
expressed-care gap = expressed_care_weight - genome.care_weight
```

---

# Analysis Framework

## 1. Statistical validity

Any phase making a directional or causal claim must use:

- At least 10 seeds.
- Mean ± SD.
- Per-seed trajectories.
- Number of seeds in predicted direction.
- One-tailed binomial p-value where appropriate.
- No selective reruns.

A result is strong only if at least 9/10 seeds support the direction.

---

## 2. Baldwin Effect Analysis

For each generation window:

```text
fitness_t    = mean over lineages [survived_children / born_children]
plasticity_t = mean over lineages [mean learning_rate of living mothers]

survive_children is child reach mature
```

Use lineage macro-averaging, not naive population averaging.  
Extinct lineages contribute 0 survival.

Required output:

- Fitness and plasticity on the same figure.
- Per-seed thin lines.
- Mean ± SD thick line/band.

---

## 3. Hamilton Rule Analysis

For every care event:

```text
Hamilton value = rB - C
```

Where:

```text
r = relatedness
B = hunger_reduced
C = movement cost + feed cost
```

Required output:

- Mean `rB - C`.
- Own-child vs allomothering comparison.
- Scatter plot: `rB` vs `C`.
- Boundary line: `rB = C`.

---

## 4. Ecological Sensitivity Analysis

For each ecological change, report:

```text
Changing X from A to B caused Y% shift in Z.
The tipping point is at value V.
Above/below this point, behavior emerges in ≥ 9/10 seeds.
```

Parameters of interest:

| Parameter | Role |
|---|---|
| `hunger_rate` | Baseline mortality pressure |
| `init_food` | Food density / harshness |
| `infant_starvation_multiplier` | Infant dependency |
| `birth_scatter_radius` | Natal philopatry |
| `plasticity_noise_sigma` | Learning unreliability |

---

# Output and File Standards

Every phase must produce:

1. `results.csv`
2. `summary.json`
3. Required plots in `plots/`
4. A dated `REPORT.md` entry

Directory structure:

```text
experiments/
  phaseN_<name>/
    config.py
    run.py
    plot.py
    analysis.py

outputs/
  phaseN_<name>/
    <run_id>/
      results.csv
      summary.json
      plots/
        *.png
```

The output directory name must mirror the experiment directory name exactly.

---

# Roadmap Quality Checks

Before starting each phase, check:

- Does this phase test only one major scientific question?
- Are all active subsystems intentional?
- Are all phase-specific parameters declared in the phase config?
- Are global mechanics inherited from root `Config`?
- Are phase-specific values declared explicitly and not copied silently across phases?
- Are seeds predetermined?
- Are outputs defined before running?
- Is the interpretation gate written before seeing results?

After each phase, check:

- Did all required files exist on disk?
- Was `REPORT.md` updated?
- Were results reported across seeds?
- Were unexpected results kept?
- Did the phase result require changing later phases?

---

# Final Deliverable

The final scientific deliverable is not only a claim that maternal care emerged.  
It is a validated parameter map showing:

1. Which ecological conditions are necessary.
2. Which conditions are insufficient.
3. Where the tipping points occur.
4. Whether care is genetically encoded, plastic, or neutral.
5. Whether the result is consistent with Hamilton’s rule and the Baldwin Effect.
