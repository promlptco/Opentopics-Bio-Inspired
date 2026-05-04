# ROADMAP.md — Maternal Care Instinct Emergence Experiment

## 1. Project Goal

The goal of this project is to find the minimum ecological parameters that can make maternal care instinct emerge in an agent-based mother-child simulation within 10,000 ticks.

The final system must not only show that care behavior can happen. It must show that care can become genetically stable enough that evolved agents continue to care in a new world without lifetime learning.

---

## 2. Final Scientific Target

The final claim is:

> Under a minimal set of ecological conditions, maternal care can emerge through evolution and become expressed as a zero-shot inherited behavior.

The final test is a Baldwin-style zero-shot deployment test.

Final evolved genomes must be deployed into a new world with:

- plasticity OFF
- learning_rate = 0
- mutation OFF
- reproduction ON
- children_enabled ON

The zero-shot test passes only if:

1. Mothers still perform realized care behavior.
2. FEED_CHILD events occur.
3. Children survive.
4. The population does not go extinct.
5. Descendants continue across generations.
6. Care behavior persists without lifetime learning.
7. The result is robust across multiple seeds.

---

## 3. Definitions

### 3.1 Maternal Care

Maternal care is not just selecting the CARE motivation.

Maternal care counts only when the mother performs real child-support behavior, such as:

- moving toward the child when the child is hungry,
- reaching spatial proximity to the child,
- feeding the child,
- reducing child hunger,
- improving child survival or descendant success.

Important distinction:

```text
CARE motivation selected != care behavior proven
```

A valid care metric must include realized actions, especially:

- FEED_CHILD rate
- mother-child distance
- child hunger reduction
- child survival
- descendant survival

---

### 3.2 Instinct

In this project, instinct means:

> A heritable behavior that is expressed immediately by the agent without lifetime learning.

A behavior can be called instinct-like only if:

- it is encoded in inherited genome parameters,
- descendants express it without plasticity,
- it works in a new deployment world,
- it supports survival or reproduction,
- it is robust across seeds.

---

### 3.3 Baldwin Effect

The Baldwin Effect means:

> Lifetime plasticity helps early generations survive, and later evolution assimilates the behavior into inherited parameters.

Evidence for Baldwin Effect requires:

1. Plasticity ON performs better than Plasticity OFF early in evolution.
2. Plasticity improves survival, reproduction, or descendant success.
3. Final inherited care behavior remains after plasticity is disabled.
4. Reliance on lifetime learning decreases or becomes unnecessary.
5. Zero-shot descendants still care.

Do not claim Baldwin Effect from plasticity alone.

---

### 3.4 Genetic Assimilation

Genetic assimilation means:

> A behavior that originally needed lifetime plasticity becomes expressed through inherited parameters alone.

Evidence requires:

- evolved inherited care_weight or care tendency,
- reduced need for learning,
- zero-shot care behavior with learning_rate = 0,
- successful reproduction and descendant continuation.

---

## 4. Scientific Success Criteria

The project supports maternal care instinct emergence only if all of the following are true:

1. No-care control fails or performs much worse.
2. Care rescue succeeds.
3. Care has a cost to the mother.
4. Care improves child survival or descendant success.
5. Care-related traits are heritable.
6. Population survives across generations.
7. Final evolved genomes still care in zero-shot deployment.
8. Results are robust across multiple seeds.
9. Results are not explained by hardcoding, drift, biased initialization, or logging artifacts.

---

## 5. Scientific Failure Criteria

The claim fails or must be weakened if:

1. Children survive or mature without care.
2. CARE motivation is selected but no FEED_CHILD behavior occurs.
3. Care is not costly.
4. Care does not improve child survival or descendant success.
5. Care behavior disappears when plasticity is disabled.
6. Population goes extinct during zero-shot deployment.
7. Results depend on one seed only.
8. Weight changes are explained by mutation drift or regression to the mean.
9. The implementation contains unresolved inheritance, reproduction, maturation, or logging bugs.

---

## 6. Core Methodology Rules

### 6.1 No Phase Can Be Claimed Complete Without Outputs

Every completed phase must save:

- raw CSV logs,
- config JSON,
- summary JSON,
- plots PNG,
- Report.md interpretation.

If these outputs are missing, the phase is exploratory only.

---

### 6.2 Use Multi-Seed Validation

Default minimum:

- 30 seeds for short validation phases,
- 10 seeds minimum for 10,000-tick evolution phases,
- 30 seeds preferred if runtime allows.

Single-seed results are only debugging results.

---

### 6.3 Never Report Only Mean Curves

Always report:

- per-seed trajectories,
- mean ± SD,
- number of seeds supporting the direction,
- failure seeds,
- interpretation of variance.

---

### 6.4 Log Actions and Motivations Separately

The simulation must distinguish:

- selected motivation,
- attempted action,
- realized successful action,
- failed action.

This is required because CARE motivation does not automatically prove real caregiving.

---

### 6.5 No Selective Reruns

Do not rerun only failed seeds and mix them with old results.

If a run is repeated, repeat the full seed set.

---

### 6.6 No Silent Overwriting

All experiment outputs must use timestamped folders.

Old outputs must not be overwritten.

Invalid old outputs should be marked as archived, not deleted.

---

### 6.7 Stop After Each Phase

After each implemented phase:

1. Save outputs.
2. Append results to Report.md.
3. Update README.md commands if needed.
4. Stop.
5. Wait for user approval before continuing.

---

## 7. Required Logging Schema

At minimum, experiment logs should include the following fields when relevant:

```text
tick
seed
run_id
mother_id
child_id
generation
lineage_id
motivation
action
action_success
mother_energy
mother_alive
child_hunger
child_alive
child_matured
mother_child_distance
care_weight
forage_weight
self_weight
learning_rate
plasticity_enabled
mutation_enabled
feed_events
births
deaths
final_population
max_generation
descendant_count
```

For evolution phases, also log:

```text
birth_tick
parent_id
offspring_id
parent_generation
offspring_generation
parent_lineage_id
offspring_lineage_id
parent_care_weight
offspring_care_weight
parent_forage_weight
offspring_forage_weight
parent_self_weight
offspring_self_weight
mutation_delta_care
mutation_delta_forage
mutation_delta_self
```

For plasticity phases, also log:

```text
plasticity_event
pre_care_weight
post_care_weight
delta_care_weight
child_hunger_before
child_hunger_after
hunger_reduction
plasticity_cost
lifetime_plasticity_cost
```

---

## 8. Required Plot Types

The full project should generate these plots where relevant:

1. Population over time.
2. Mother survival over time.
3. Child survival over time.
4. Child hunger over time.
5. Mother energy over time.
6. CARE / FORAGE / SELF motivation rates.
7. Realized action rates.
8. Failed action rates.
9. FEED_CHILD rate over time.
10. Mother-child distance over time.
11. Care / forage / self genome weights over time.
12. Lineage descendant count vs care_weight.
13. Plasticity ON vs OFF comparison.
14. Learning rate over generations.
15. Lifetime plasticity cost over generations.
16. Zero-shot comparison between evolved and control genomes.

---

## 9. Repository Audit Requirements

Before implementing new experiments, audit the old repository.

The audit must check:

### 9.1 Repository Structure

Identify:

- existing experiment folders,
- existing scripts,
- config files,
- shared constants,
- report files,
- old output folders,
- archived outputs.

### 9.2 Existing Phase Reliability

Classify each old phase as:

- reliable,
- partially reliable,
- unreliable,
- archived / invalid.

Explain why.

### 9.3 Code Risks

Audit for bugs in:

- inheritance,
- mutation,
- reproduction,
- child maturation,
- mother-child linkage,
- child death cleanup,
- occupied-cell consistency,
- food spawning,
- pathfinding,
- action logging,
- motivation logging,
- failed action accounting,
- seed control,
- parallel-run reproducibility.

### 9.4 Methodology Risks

Check whether old experiments suffer from:

- child can survive without care,
- care not costly,
- care not beneficial,
- care not heritable,
- plasticity confounded with evolution,
- mutation drift mistaken for selection,
- regression-to-mean artifact,
- founder effect,
- floor-bounce artifact,
- only motivation logs but no realized action logs,
- single-seed or weak multi-seed evidence,
- undocumented parameter changes.

---

## 10. Special Known Concern: Phase 3 Child Dependency

Old Phase 3 may be unreliable if:

```text
child_hunger_rate == mother_hunger_rate
```

If the child hunger rate is too low, a child may mature before starvation even without care.

Example:

```text
child_hunger_rate = 0.005
maturity_age = 100
death_hunger = 1.0
hunger_at_maturity = 0.005 * 100 = 0.5
```

In this case, the child can reach maturity without care.

This means old Phase 3 may show:

```text
care is helpful
```

but not:

```text
care is necessary
```

Therefore, before using Phase 3 as a foundation, the project must run a child dependency control.

---

# 11. Corrected Experiment Pipeline

## Phase 1 — Mechanics and Repository Audit

### Purpose

Confirm that the old codebase and previous results are reliable enough to support new experiments.

### Hypothesis

If mechanics are correct, then inheritance, mutation, reproduction, maturation, logging, and seed control should behave as documented.

### Tasks

- Map repository.
- Classify old phases.
- Audit code risks.
- Audit methodology risks.
- Identify invalid or archived results.
- Identify first blocking bug.

### Required Outputs

- Audit section in Report.md.
- List of valid old results.
- List of invalid old results.
- List of blocking bugs.
- Recommended next command.

### Success Criteria

- No critical unresolved bug blocks child dependency experiments.
- Old results are clearly classified.
- Next phase is scientifically justified.

### Failure Criteria

- Inheritance, maturation, occupied-cell logic, or logging is unreliable.
- Existing results cannot be interpreted.

### Command Template

```bash
python experiments/phase1_mechanics_tests/run.py
```

---

## Phase 2 — Mother-Only Ecological Baseline

### Purpose

Find a stable but pressured ecology where mothers can survive without children.

This baseline is needed before adding child dependency.

### Hypothesis

There exists a food/energy regime where mothers mostly survive but are not fully saturated.

### Parameters

Candidate sweep:

```text
init_food
hunger_rate
move_cost
eat_gain
rest_recovery
perception_radius
```

### Default Duration

```text
1000 ticks
```

### Seeds

```text
30 seeds preferred
```

### Controls

- mother-only,
- children OFF,
- reproduction OFF,
- mutation OFF,
- plasticity OFF.

### Metrics

- mother survival rate,
- final population,
- mean mother energy,
- final mother energy,
- food consumption rate,
- failed forage rate.

### Required CSV Logs

- per-tick mother energy,
- actions,
- food events,
- deaths.

### Required JSON Outputs

- config.json,
- summary.json.

### Required Plots

- population over time,
- mother energy over time,
- action rates,
- food availability,
- failed forage rate.

### Success Criteria

A valid balanced baseline should show:

- mother survival around 80–95%,
- non-trivial energy pressure,
- no immediate extinction,
- no full saturation at max energy.

### Failure Criteria

- all mothers die,
- all mothers survive trivially with saturated energy,
- strong seed instability.

### Command Template

```bash
python experiments/phase2_survival_minimal/run.py --mode pipeline --duration 1000 --repeats 3 --workers 0
```

---

## Phase 3 — Child Dependency Control

### Purpose

Test whether children actually need maternal care to survive.

This phase directly fixes the Phase 3 reliability concern.

### Hypothesis

At a valid child dependency setting, children should not survive or mature reliably without care.

### Settings

```text
care_weight = 0.0
forage_weight = 1.0
self_weight = baseline value
mutation OFF
plasticity OFF
reproduction OFF
duration = 1000 ticks
```

### Sweep

```text
child_hunger_rate = [0.005, 0.008, 0.010, 0.012, 0.015, 0.020]
```

or equivalent:

```text
infant_starvation_multiplier = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
```

### Seeds

```text
30 seeds minimum
```

### Controls

- no-care child condition,
- mother-only baseline reference.

### Metrics

- child survival rate,
- child matured rate,
- mean child hunger,
- time to child death,
- mother survival rate,
- mother energy,
- FEED_CHILD events,
- realized CARE action rate.

### Required CSV Logs

- per-tick child hunger,
- child alive/dead,
- child matured,
- mother energy,
- actions and motivations.

### Required JSON Outputs

- config.json,
- dependency_summary.json.

### Required Plots

1. child survival rate vs child_hunger_rate,
2. child matured rate vs child_hunger_rate,
3. mean child hunger over time,
4. time-to-child-death distribution,
5. mother survival over time.

### Success Criteria

Select the weakest child dependency setting where:

```text
no-care child survival < 0.20
```

If too strict:

```text
no-care child survival < 0.50
```

### Failure Criteria

- children survive without care,
- children mature before starvation without care,
- mothers die before dependency can be tested,
- FEED_CHILD happens even when care_weight = 0.0 due to a bug.

### Command Template

```bash
python experiments/phase3_survival_full/child_dependency_sweep.py --duration 1000 --seeds 30
```

---

## Phase 4 — Care Rescue and Minimum Care Threshold

### Purpose

Test whether maternal care rescues child survival under the selected child dependency setting.

### Hypothesis

If care is functional, then care_weight > 0 should improve child survival compared with no-care control.

### Settings

Use selected child_hunger_rate from Phase 2.

```text
mutation OFF
plasticity OFF
reproduction OFF
duration = 1000 ticks
```

### Sweep

```text
care_weight = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7]
forage_weight = [0.7, 0.85, 1.0]
self_weight = [0.3, 0.5, 0.7]
```

### Seeds

```text
30 seeds minimum
```

### Controls

- no-care control,
- high-care condition,
- forage-dominant condition,
- self-dominant condition if relevant.

### Metrics

- mother survival rate,
- child survival rate,
- child matured rate,
- mean child hunger,
- mother energy,
- FEED_CHILD rate,
- CARE motivation rate,
- realized CARE action rate,
- mother-child distance,
- failed CARE rate,
- failed FORAGE rate.

### Required CSV Logs

- per-tick action log,
- motivation log,
- mother-child distance,
- child hunger,
- mother energy,
- feed events.

### Required JSON Outputs

- config.json,
- rescue_summary.json,
- selected_canonical_genome.json.

### Required Plots

1. heatmap: child survival by care_weight and forage_weight,
2. heatmap: mother survival by care_weight and forage_weight,
3. action frequency breakdown,
4. FEED_CHILD rate over time,
5. child hunger over time,
6. mother-child distance over time,
7. care trap plot: care_weight vs mother energy.

### Success Criteria

Care rescue succeeds if:

- no-care child survival is low,
- at least one care_weight > 0 gives high child survival,
- mother survival remains high,
- FEED_CHILD events occur,
- mother-child distance confirms spatially meaningful care.

Preferred threshold:

```text
mother_survival_rate >= 0.80
child_survival_rate >= 0.80
```

### Failure Criteria

- no-care survives,
- care does not improve child survival,
- mother dies because care is too costly,
- only CARE motivation increases but FEED_CHILD does not.

### Command Template

```bash
python experiments/phase3_survival_full/care_rescue_sweep.py --duration 1000 --seeds 30 --child_hunger_rate SELECTED_VALUE
```

---

## Phase 5 — Minimum Ecological Pressure Sweep

### Purpose

Find the minimum ecological parameters that make care genetically useful.

### Hypothesis

Care becomes genetically useful only under specific ecological pressure, such as stronger infant dependency or stronger natal philopatry.

### Candidate Parameters

```text
child_hunger_rate / infant_starvation_multiplier
birth_scatter_radius / natal philopatry
feed_cost
init_food
hunger_rate
move_cost
```

### Recommended Small Grid

Keep the grid small and interpretable.

Example:

```text
infant_starvation_multiplier = [1.0, 1.5, 2.0, 2.5]
birth_scatter_radius = [0, 1, 3, 5]
feed_cost = [0.00, 0.01, 0.03]
```

### Duration

```text
1000–3000 ticks for sweep
```

Use 10,000 ticks only for final evolution phases.

### Seeds

```text
10–30 seeds depending on runtime
```

### Controls

1. standard ecology baseline,
2. no-care control,
3. care-capable fixed genome,
4. infant dependency only,
5. natal philopatry only,
6. dependency + philopatry.

### Metrics

- mother survival rate,
- child survival rate,
- final population,
- max generation if reproduction is enabled,
- descendant count,
- realized FEED_CHILD rate,
- child hunger,
- mother energy.

### Required CSV Logs

- per-condition survival logs,
- action logs,
- child hunger logs,
- reproduction logs if enabled.

### Required JSON Outputs

- config.json,
- ecological_pressure_summary.json,
- selected_minimum_ecology.json.

### Required Plots

1. survival zone heatmap,
2. child survival vs ecological pressure,
3. mother survival vs ecological pressure,
4. FEED_CHILD rate vs ecological pressure,
5. descendant success vs condition if reproduction is enabled.

### Success Criteria

Select the weakest ecological condition where:

- no-care performs poorly,
- care-capable genome performs better,
- care improves child survival or descendant success,
- mother survival remains viable,
- effect appears across seeds.

### Failure Criteria

- care gives no advantage,
- ecology kills mothers regardless of care,
- only high-resource ecology works,
- result depends on one seed.

### Command Template

```bash
python experiments/phase4_ecological_pressure_sweep/run.py --duration 3000 --seeds 10
```

---

## Phase 6 — Evolution Without Plasticity

### Purpose

Test whether the selected minimum ecology creates genetic selection for maternal care without lifetime learning.

### Hypothesis

If ecology is sufficient, care-related inherited traits should increase or stabilize because caring lineages leave more descendants.

### Settings

Use selected minimum ecology from Phase 4.

```text
duration = 10000 ticks
mutation ON
plasticity OFF
reproduction ON
learning_rate = 0
children_enabled ON
```

### Seeds

```text
10 seeds minimum
30 preferred if runtime allows
```

### Initialization

Avoid known artifacts.

Do not rely only on U(0,1) if it creates floor-bounce.

Recommended include at least two initializations:

1. varied broad init,
2. controlled high-care or mid-care init,
3. neutral drift control if possible.

### Controls

- mutation drift control,
- no-child or no-care-benefit control if possible,
- standard ecology baseline.

### Metrics

- care_weight over time,
- forage_weight over time,
- self_weight over time,
- realized FEED_CHILD rate,
- child survival rate,
- mother survival rate,
- population over time,
- max generation,
- descendant count per lineage,
- lineage care_weight vs descendant count,
- mutation statistics.

### Required CSV Logs

- per-tick population log,
- birth_log.csv,
- lineage_log.csv,
- action_log.csv,
- genome_snapshot_log.csv.

### Required JSON Outputs

- config.json,
- evolution_summary.json,
- selection_gradient_summary.json.

### Required Plots

1. population over time,
2. care / forage / self weights over time,
3. realized FEED_CHILD rate over time,
4. child survival over time,
5. lineage descendant count vs care_weight,
6. per-seed selection gradient distribution.

### Success Criteria

This phase supports genetic care emergence if:

- care_weight or realized care behavior increases across generations,
- child survival or descendant success improves,
- care lineage success is positive,
- result is robust across seeds,
- not explained by mutation drift or regression to mean.

### Failure Criteria

- care decreases,
- care is neutral,
- population extinct,
- weight movement matches bounded mutation drift,
- no realized FEED_CHILD increase.

### Command Template

```bash
python experiments/phase5_evolution_no_plasticity/run.py --duration 10000 --seeds 10
```

---

## Phase 7 — Evolution With Care-Specific Plasticity

### Purpose

Test whether lifetime plasticity helps maternal care survive and become genetically assimilated.

### Hypothesis

Plasticity helps early generations discover or maintain care. Later evolution should reduce reliance on plasticity by increasing inherited care tendency.

### Settings

Use the same selected minimum ecology from Phase 4.

```text
duration = 10000 ticks
mutation ON
reproduction ON
children_enabled ON
```

### Treatments

```text
plasticity OFF
plasticity ON
```

### Plasticity Rule

Only care_weight may be updated by plasticity.

Do not update:

```text
forage_weight
self_weight
```

from care outcomes.

Plasticity should trigger only from successful child feeding or actual child hunger reduction.

Do not update care_weight from failed care actions.

### Seeds

```text
10 seeds minimum
30 preferred if runtime allows
```

### Controls

- plasticity OFF treatment,
- plasticity ON treatment,
- cost-of-plasticity condition if implemented,
- no-care or no-child-benefit control if possible.

### Metrics

- inherited care_weight over generations,
- effective lifetime care_weight,
- learning_rate over generations,
- lifetime plasticity cost,
- realized FEED_CHILD rate,
- child survival rate,
- mother survival rate,
- population over time,
- descendant count,
- max generation,
- plasticity ON vs OFF comparison.

### Required CSV Logs

- raw tick logs,
- birth_log.csv,
- lineage_log.csv,
- plasticity_log.csv,
- genome_snapshot_log.csv.

### Required JSON Outputs

- config.json,
- plasticity_evolution_summary.json,
- treatment_comparison_summary.json.

### Required Plots

1. plasticity ON vs OFF population,
2. inherited care_weight over time,
3. effective lifetime care_weight over time,
4. learning_rate over time,
5. lifetime plasticity cost over time,
6. FEED_CHILD rate over time,
7. child survival over time,
8. lineage descendant count comparison.

### Success Criteria

This phase supports Baldwin-style scaffolding if:

- plasticity ON improves early survival or reproduction,
- final inherited care_weight increases or stabilizes,
- reliance on plasticity decreases or does not remain the only reason for survival,
- zero-shot testing later confirms care without learning,
- result is robust across seeds.

### Failure Criteria

- plasticity ON does not improve survival or reproduction,
- plasticity is the only reason agents survive,
- learned care disappears when plasticity is disabled,
- plasticity updates forage/self and confounds interpretation,
- high learning_rate is selected forever without assimilation.

### Command Template

```bash
python experiments/phase6_evolution_plasticity/run.py --duration 10000 --seeds 10 --plasticity off
python experiments/phase6_evolution_plasticity/run.py --duration 10000 --seeds 10 --plasticity on
python experiments/phase6_evolution_plasticity/compare.py
```

---

## Phase 8 — Baldwin Zero-Shot Deployment

### Purpose

Test whether maternal care has become genetically assimilated into the final evolved genomes.

This is the final test.

### Hypothesis

If genetic assimilation occurred, final evolved genomes should still express care in a new world without plasticity, learning, or mutation.

### Input

Use final evolved genomes from Phase 6.

Include controls from:

1. plasticity ON evolved genomes,
2. plasticity OFF evolved genomes,
3. naive random genomes,
4. hand-designed care-capable baseline if available.

### Deployment Settings

```text
new world
new random seeds
plasticity OFF
learning_rate = 0
mutation OFF
reproduction ON
children_enabled ON
duration = 10000 ticks
```

### Seeds

```text
10 seeds minimum
30 preferred if runtime allows
```

### Metrics

- mother survival rate,
- child survival rate,
- final population,
- max generation,
- descendant count,
- realized FEED_CHILD rate,
- CARE motivation rate,
- mother-child distance,
- child hunger,
- care_weight stability,
- extinction rate across seeds.

### Required CSV Logs

- zero_shot_tick_log.csv,
- birth_log.csv,
- lineage_log.csv,
- action_log.csv,
- genome_source_log.csv.

### Required JSON Outputs

- config.json,
- zero_shot_summary.json,
- final_claim_summary.json.

### Required Plots

1. zero-shot population over time,
2. child survival over time,
3. FEED_CHILD rate over time,
4. mother-child distance over time,
5. descendant count by genome source,
6. plasticity-evolved vs non-plastic-evolved vs naive comparison.

### Success Criteria

Zero-shot passes if:

- mothers perform realized care behavior,
- FEED_CHILD events occur,
- children survive,
- population does not go extinct,
- descendants continue across generations,
- care persists without plasticity,
- results are robust across seeds.

### Failure Criteria

- no realized care,
- child survival collapses,
- population extinct,
- behavior only works with plasticity ON,
- evolved genomes do not outperform naive controls.

### Command Template

```bash
python experiments/phase7_baldwin_zero_shot/export_final_genomes.py
python experiments/phase7_baldwin_zero_shot/run_zero_shot.py --duration 10000 --seeds 10 --plasticity off --learning_rate 0 --mutation off --reproduction on
python experiments/phase7_baldwin_zero_shot/analyze_zero_shot.py
```

---

## 12. Report.md Format

After each phase, append this structure to Report.md:

```md
## Phase X — Title

### Purpose
Explain what this phase tests.

### Protocol
List parameters, seeds, duration, and command used.

### Outputs
List generated CSV, JSON, PNG files.

### Results
Report main numbers with mean ± SD.

### Interpretation
Explain what the result means scientifically.

### Failure / Limitation
State what is weak, invalid, or unresolved.

### Decision
State whether to proceed, revise, or stop.
```

---

## 13. README.md Update Rule

Whenever a new phase script is added, update README.md with:

- purpose of the phase,
- command to run,
- expected output folder,
- key generated files.

Keep README commands short and runnable.

---

## 14. Implementation Style

Use simple implementation.

Preferred tools:

```text
Python standard library
numpy
pandas
matplotlib
scipy if already used
```

Avoid heavy frameworks unless the repository already depends on them.

Code rules:

- Use seed-controlled runs.
- Use clear function names.
- Use dataclasses where helpful.
- Keep scripts runnable from command line.
- Add comments only to important scientific or logic lines.
- Do not over-engineer.
- Do not modify unrelated phases.
- Do not delete old results.

---

## 15. Recommended Workflow With AI Coding Agent

Use this ROADMAP.md as the project constitution.

Recommended prompt flow:

1. Ask the AI coding agent to audit the repository against ROADMAP.md.
2. Ask it to write the audit result to Report.md.
3. Review the audit manually.
4. Approve only one phase at a time.
5. Ask the AI coding agent to implement only the approved phase.
6. After each phase, inspect Report.md and outputs before continuing.

Example prompt:

```text
Read ROADMAP.md.
Audit the repository against the roadmap.
Do not implement anything yet.
Write the audit result to Report.md.
Then stop and wait for approval.
```

Example implementation prompt:

```text
Read ROADMAP.md and Report.md.
Implement only Phase 2 — Child Dependency Control.
Follow all logging, plotting, and reporting rules.
Append results to Report.md.
Update README.md commands if needed.
Then stop and wait for approval.
```

---

## 16. Immediate Next Step

The safest first action is:

```bash
python experiments/phase1_mechanics_tests/run.py
```

Then audit whether the current mechanics are reliable enough to proceed to Phase 2 Child Dependency Control.

Do not proceed to new evolution experiments until child dependency is proven.
