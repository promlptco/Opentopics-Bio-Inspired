# Experimental Setup

## Research Question

Under what ecological conditions does care behavior emerge from agents with no pre-programmed drive to care, and does that ecology sustain care as fitness-positive across population, individual, and behavioral/genomic scales?

## Main Hypotheses

### H0: Null Hypothesis

Maternal care does not emerge from ecological pressure. Changes in food distribution, plasticity, or mutation do not significantly improve child maturation, lineage survival, or genome care weight.

### H1: Ecological Emergence Hypothesis

Patchy food distribution makes care fitness-positive. When food becomes spatially uncertain, mother-child pairs benefit more from care than from solitary foraging, increasing child maturation.

### H2: Baldwin Effect Hypothesis

If care improves fitness under ecological pressure, phenotypic plasticity should first improve survival, and over generations mutation plus selection should begin shifting genome care weight upward.

## Core Variables

| Variable Type | Variables | Purpose |
|---|---|---|
| Independent variables | Food mechanism, food entropy alpha, birth scatter radius, genome weights, mutation ON/OFF, plasticity ON/OFF | Experimental conditions being changed |
| Dependent variables | Final population, extinction tick, child maturation rate, care action rate, genome care weight, expressed care weight, generation depth | Measured outcomes |
| Control variables | World size, initial mothers, initial energy, hunger rate, perception radius, rest recovery, fatigue rate, mutation sigma, maturity age, max ticks, random seed protocol | Held fixed to make comparisons fair |

## Phase 1: Mechanism Unit Test

### Objective

Verify that the simulation mechanics work correctly before ecological experiments are trusted.

### Independent Variables

None. This phase validates mechanisms directly.

### Dependent Variables

| Output | Meaning |
|---|---|
| Mutation test result | Confirms mutation changes genome values correctly |
| Inheritance test result | Confirms offspring genome copying works |
| Reproduction test result | Confirms reproduction threshold and child creation work |
| Population stability test result | Confirms agents survive with food and die without food |

### Control Variables

| Control | Value / Rule |
|---|---|
| Seed control | Deterministic test seeds |
| Food availability | Present for stability tests, absent for extinction test |
| Agent mechanics | Same movement, energy, and reproduction rules as later phases |

### Expected Result

All core mechanisms pass before running Phase 2-5 experiments.

## Phase 2: Self-Survival Baseline

### Objective

Find an ecological baseline where agents can survive alone under real but non-catastrophic resource pressure.

### Hypothesis

Ecological parameters such as food amount, movement cost, and eat gain determine whether self-only agents can survive.

### Independent Variables

| Variable | Tested Values / Conditions |
|---|---|
| `init_food` | Swept across candidate food amounts |
| `move_cost` | Swept across movement-cost levels |
| `eat_gain` | Swept across food-energy gains |
| food entropy `alpha` | Uniform / entropy food settings |

### Dependent Variables

| Variable | Measurement |
|---|---|
| Final population | Number of agents alive at tick 1,000 |
| Mean energy | Average agent energy, especially tail-window mean |
| Failed forage rate | Fraction of forage attempts where no food is visible |
| REST action rate | Sanity check for fatigue and recovery pressure |

### Control Variables

| Control | Value |
|---|---|
| Agent system | Mothers only |
| Children / care | OFF |
| Reproduction | OFF |
| Mutation | OFF |
| Plasticity | OFF |
| World size | 50 x 50 grid |
| Initial mothers | 15 |
| Initial energy | 1.0 |
| Hunger rate | 1/35 per tick |
| Perception radius | 8 cells |
| Rest recovery | 0.005 energy per REST action |
| Fatigue rate | 0.01 |
| Baseline genome | care = 0.0, forage = 1.0, self = 1.0 |
| Run length | 1,000 ticks |
| Seeds | 10 seeds x 3 repeats |

### Selection Criteria

Let:

```text
S = N_alive / 15
E_tail = mean energy over final 200 ticks
sigma_E = tail-energy standard deviation
R_rest = REST action rate
```

The selected baseline should have moderate survival, moderate energy, and non-zero ecological pressure.

| Ecology | Survival Gate | Energy Gate / Target |
|---|---|---|
| Harsh | 0.10 <= S <= 0.45 | E_tail target about 0.20 |
| Balanced | 0.50 <= S <= 0.75 | E_tail target about 0.35 |
| Easy | S >= 0.80 | E_tail target about 0.50 |

### Selected Result

The Balanced ecology was selected as the working baseline because it preserved survival while maintaining real resource pressure.

## Phase 3: Food Mechanism Search

### Objective

Test which food distribution makes maternal care valuable for mother-child pairs.

### Hypothesis

Patchy Shannon entropy food increases the fitness value of care by making solitary juvenile survival harder and maternal provisioning more useful.

### Independent Variables

| Condition | Food Mechanism | Alpha |
|---|---|---:|
| F0 | Uniform 1:1 respawn | 0.00 |
| F1 | Shannon entropy | 0.01 |
| F2 | Shannon entropy | 0.05 |
| F3 | Shannon entropy | 0.10 |

### Dependent Variables

| Variable | Measurement |
|---|---|
| Phase 2 self-only population | Tail population without care |
| Phase 3 population | Tail population with mother-child pairs |
| Care action rate | Fraction of actions assigned to care |
| Child maturation rate | Fraction of children reaching maturity |
| Mean agent energy | Energy available under each food condition |

### Control Variables

| Control | Value |
|---|---|
| World size | 50 x 50 grid |
| Initial mothers | 15 |
| Genome weights | care = forage = self = 1.0 |
| Children / care | ON |
| Perception radius | 8 cells |
| Birth scatter radius | 2 |
| Hunger rate | 1/35 per tick |
| Initial energy | 1.0 |
| Seeds | 10 seeds per condition |

### Selected Result

Shannon entropy food at alpha = 0.01 was selected as the Phase 5 baseline because it creates real care pressure without preventing population establishment. Higher alpha values produced much higher child maturation, but were not used as the main evolutionary baseline.

## Birth Scatter Radius Test

### Objective

Test how far children can be born from mothers before care fails.

### Independent Variable

| Variable | Tested Values |
|---|---|
| `birth_scatter_radius` | 2, 3, 5 |

### Dependent Variables

| Variable | Measurement |
|---|---|
| Extinction tick | Time until all agents die |
| Child maturation rate | Fraction of children reaching maturity |

### Control Variables

Same ecology and genome settings as the Phase 3 selected baseline.

### Selected Result

`birth_scatter_radius = 2` was selected. Radius 3 or higher caused rapid extinction because children were born outside effective provisioning range.

## Phase 4: Genome Weight Sweep

### Objective

Find the best starting motivational genome for the evolutionary experiment.

### Hypothesis

Care must be non-zero for children to survive, but foraging must remain dominant so mothers can maintain enough energy to provide care.

### Independent Variables

| Variable | Description |
|---|---|
| `g_c` | Genome care weight |
| `g_f` | Genome forage weight |
| `g_s` | Genome self-preservation weight |

### Dependent Variables

| Variable | Measurement |
|---|---|
| Child maturation rate | Fraction of children reaching maturity |
| Mother survival | Survival relative to initial mother population |

### Control Variables

| Control | Value |
|---|---|
| Food mechanism | Shannon entropy |
| Food entropy alpha | 0.01 |
| Birth scatter radius | 2 |
| World size | 50 x 50 grid |
| Initial mothers | 15 |
| Children / care | ON |
| Mutation | OFF |
| Evolutionary plasticity | OFF for weight calibration |

### Selected Result

| Configuration | care `g_c` | forage `g_f` | self `g_s` | Child Maturation | Mother Survival |
|---|---:|---:|---:|---:|---:|
| Viable minimum | 0.1 | 1.5 | 1.0 | 17.3% | 77.3% |
| Optimal | 0.5 | 2.0 | 1.0 | 36.0% | 122.7% |

The selected starting genome for Phase 5 was:

```text
care : forage : self = 0.5 : 2.0 : 1.0
```

This ratio means foraging dominates, self-preservation remains active, and care is present but not energetically overwhelming.

## Phase 5: Baldwin Effect Experiment

### Objective

Test whether mutation and plasticity allow care to improve survival and begin shifting into the genome.

### Hypotheses

| Hypothesis | Prediction |
|---|---|
| H0 | Mutation and plasticity do not improve survival or genome care drift |
| H1 | Plasticity improves lineage survival under ecological pressure |
| H2 | Mutation plus selection produces upward drift in genome care weight |
| H3 | Mutation and plasticity together produce the strongest Baldwin Effect signal |

### Independent Variables

| Factor | Levels |
|---|---|
| Mutation | OFF, ON |
| Plasticity | OFF, ON |

### Experimental Conditions

| Condition | Mutation | Plasticity |
|---|---|---|
| mut_OFF, plast_OFF | OFF | OFF |
| mut_ON, plast_OFF | ON | OFF |
| mut_OFF, plast_ON | OFF | ON |
| mut_ON, plast_ON | ON | ON |

### Dependent Variables

| Variable | Measurement |
|---|---|
| Extinction tick | Population-level lineage survival |
| Child maturation rate | Individual-level reproductive success proxy |
| Genome care weight | Genomic drift toward care |
| Expressed care weight | Phenotypic care expression |
| Genome-behavior distance | Plasticity gap |
| Innateness index | Progress toward genetic assimilation |
| Maximum generation reached | Evolutionary depth |

### Control Variables

| Control | Value |
|---|---|
| Food mechanism | Shannon entropy |
| Food entropy alpha | 0.01 |
| Birth scatter radius | 2 |
| Starting genome | care:forage:self = 0.5:2.0:1.0 |
| Initial mothers | 15 |
| World size | 50 x 50 grid |
| Maximum population | 140 |
| Initial energy | 1.0 |
| Hunger rate | 1/35 per tick |
| Mutation sigma | 0.02 |
| Phenotype retention | 0.15 |
| Max ticks | 40,000 |
| Seeds | 10 seeds per condition |

### Expected Result

Plasticity should increase short-term survival. Mutation should create heritable variation. Mutation plus plasticity should show the clearest early Baldwin Effect signal through longer survival and upward genome care drift.

## Robustness Strategy

| Robustness Method | Purpose |
|---|---|
| Multiple seeds | Prevent conclusions from depending on one random run |
| Repeated runs | Measure variation within each condition |
| OVAT sensitivity sweeps | Identify which parameters control survival |
| Food mechanism comparison | Test whether results depend on food distribution |
| Birth radius sensitivity | Test spatial robustness of mother-child care |
| 2 x 2 factorial design | Separate mutation effects from plasticity effects |
| Statistical tests | Validate whether condition differences are meaningful |

## Overall Experimental Logic

```text
Phase 1 verifies mechanics
Phase 2 calibrates self-survival ecology
Phase 3 finds food conditions where care pays off
Phase 4 finds viable starting genome weights
Phase 5 tests Baldwin Effect evolution under calibrated ecology
```
