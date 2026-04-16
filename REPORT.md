# Phase 1 — Mechanics Tests Report

**Status:** ✅ COMPLETE — 17/17 tests passed  
**Seed:** 42 (single seed — validation only)

---

## Results

### Test 01 · Mutation (4 tests)

| Test | Key Result |
|---|---|
| Changes values | 100/100 mutations at `mutation_rate=1.0` |
| Stays in bounds | 1,000 iterations from extreme values — all 5 fields in [0,1] |
| Distribution | All 5 fields: mean ~0.50, stdev ~0.05 — consistent with N(0, σ=0.05) |
| Sigma sensitivity | σ=0.01→0.0103, σ=0.05→0.0501, σ=0.10→0.0986 — monotonic, no distortion |

**Bug caught:** implementation used σ=0.1 instead of σ=0.05 specified in design doc. Fixed in `Genome.mutate()`.

### Test 02 · Inheritance (3 tests)

Copy is exact across all 5 fields, independent (no aliasing), and `mutation_rate=0.0` preserves genome exactly.

### Test 03 · Reproduction (4 tests)

All three gates block correctly — energy threshold, child ownership, and cooldown. Cooldown floors at 0 and does not go negative.

### Test 04 · Population Stability (4 tests)

| Test | Result |
|---|---|
| No extinction | 20 alive at tick 100 |
| No explosion | 30 total at tick 100 (threshold=50) |
| Deterministic | Run 1 = Run 2 = 5 survivors (seed=12345) |
| Starvation | 0 alive at tick 200 with food and recovery removed |

---

## Verdict

All genetic operators and simulation mechanics verified correct. One bug found and fixed (σ mismatch). Engine ready for Phase 2.

---

### Phase 2 · Diagnostic Plot Expansion

**Purpose:**  
Extend Phase 2 analysis beyond survival and energy curves by adding behavioral diagnostic plots. These plots help explain *why* a configuration survives or collapses by linking ecological parameters to motivation selection, realized actions, failed decisions, food intake, spatial behavior, and energy expenditure.

This update was added after the baseline calibration and OVAT sensitivity sweep to make the Phase 2 survival-minimal system more interpretable before moving into child-care, plasticity, and evolution phases.

---

#### Code Structure Update

Phase 2 survival-minimal code was reorganized into three main files:

| File | Role |
|---|---|
| `run.py` | Main simulation loop, validation, sweep selection, logging, and plot orchestration |
| `config.py` | Centralized parameters, selection targets, sweep ranges, baseline values, and plot enable/disable switches |
| `plot.py` | All plotting functions, CSV saving, JSON saving, and summary utilities |

This makes the experiment easier to maintain:

- `run.py` focuses on running simulation and validation.
- `config.py` is the main file for changing parameters.
- `plot.py` handles all output visualization and logging.

---

#### Multi-Seed Validation Behavior

All validation and diagnostic plots are generated from the same validation result set.

Current validation protocol:

```text
VALIDATION_SEEDS = [42, 43, 44, 45, 46]
```

Therefore, total runs per plotted condition are:

```text
5 seeds × repeats
```

Example:

```bash
python experiments/phase2_survival_minimal/run.py --mode single --duration 1000 --repeats 10
```

produces:

```text
5 seeds × 10 repeats = 50 runs
```

All diagnostic plots are therefore based on multi-seed, multi-repeat statistics rather than a single stochastic run.

---

#### Motivation and Action Definition

The Phase 2 survival-minimal environment has no child, no care behavior, and no reproduction. Therefore, only two motivation domains are used:

| Level | Variables |
|---|---|
| Motivation | `FORAGE`, `SELF` |
| Action | `MOVE`, `PICK`, `EAT`, `REST` |

Mapping:

```text
FORAGE motivation → MOVE or PICK
SELF motivation   → EAT or REST
```

If a motivation is selected but no valid action is executed, it is counted as a failed realization.

---

#### Added Per-Tick Logs

The simulation now records additional per-tick information:

| Log | Meaning |
|---|---|
| `action_history` | Per-tick counts of `MOVE`, `PICK`, `EAT`, `REST` |
| `motivation_history` | Per-tick counts of `FORAGE`, `SELF` |
| `failed_history` | Per-tick counts of `FAILED_FORAGE`, `FAILED_SELF` |
| `food_history` | Per-tick `PICK`, `EAT`, and available food count |
| `energy_flow_history` | Per-tick hunger loss, movement loss, eating gain, and net energy change |
| `spatial_heatmap` | Mother population visitation heatmap over the grid |

These logs allow the analysis to connect:

```text
parameter setting → motivation → realized action → failed decision → energy/population outcome
```

---

#### Added Diagnostic Plots

The following plots were added to Phase 2. Each plot can be enabled or disabled from `config.py`.

---

##### 1. Action Selection Over Time

**Output:**

```text
action_selection_<name>.png
```

**Purpose:**  
Shows how often each realized action occurs over time.

Actions:

```text
MOVE, PICK, EAT, REST
```

**Interpretation:**  
This plot explains what agents are actually doing during survival. For example, a high `MOVE` rate indicates active foraging, while a high `REST` rate indicates self-maintenance through fatigue recovery.

---

##### 2. Motivation Selection Over Time

**Output:**

```text
motivation_selection_<name>.png
```

**Purpose:**  
Shows the motivation-level decision trend over time.

Motivations:

```text
FORAGE, SELF
```

**Interpretation:**  
This plot reveals whether the population is primarily driven by food-seeking or self-maintenance. In the tested balanced-style configuration, agents initially prioritize `FORAGE`, then gradually shift toward `SELF` as energy and fatigue dynamics stabilize.

---

##### 3. Failed Selection Over Time

**Output:**

```text
failed_selection_<name>.png
```

**Purpose:**  
Shows when motivation selection fails to become a realized action.

Definitions:

```text
FAILED_FORAGE = FORAGE selected but neither MOVE nor PICK occurred
FAILED_SELF   = SELF selected but neither EAT nor REST occurred
```

**Interpretation:**  
This plot explains the gap between motivation and action. For example, if `FORAGE` is high but `MOVE + PICK` is lower, the missing portion is explained by `FAILED_FORAGE`.

Possible causes of `FAILED_FORAGE`:

- food outside perception radius
- no valid target
- movement conflict
- position update failure

Possible causes of `FAILED_SELF`:

- `EAT` selected while no food is held
- self-maintenance selected but no valid self-action executes

---

##### 4. Stacked Action + Failed Selection Chart

**Output:**

```text
stacked_action_failed_<name>.png
```

**Purpose:**  
Combines realized actions and failed selections into one stacked area chart.

Stacked components:

```text
MOVE
PICK
EAT
REST
FAILED_FORAGE
FAILED_SELF
```

**Interpretation:**  
This plot gives a compact overview of how each tick is behaviorally distributed. It shows the proportion of useful actions versus wasted or unrealized decisions.

---

##### 5. FAILED_SELF / FAILED_FORAGE vs Energy Decay Correlation

**Outputs:**

```text
correlation_failed_self_energy_<name>.png
correlation_failed_forage_energy_<name>.png
correlation_summary_<name>.csv
correlation_failed_forage_summary_<name>.csv
```

**Purpose:**  
Tests whether failed decisions are associated with energy decline.

Correlation examples:

```text
FAILED_SELF rate vs energy drop per tick
FAILED_FORAGE rate vs energy drop per tick
```

**Interpretation:**  
A positive correlation suggests that failed decision realization may be related to energy loss. This is useful for diagnosing whether late-run energy decay is caused by poor self-maintenance, failed foraging, or another energy imbalance.

---

##### 6. State Space Plot: Energy vs Action/Motivation

**Output:**

```text
state_space_energy_action_<name>.png
```

**Purpose:**  
Shows how action or motivation probability changes with energy.

Examples:

```text
Energy vs REST
Energy vs EAT
Energy vs SELF
Energy vs FORAGE
```

**Interpretation:**  
This plot helps identify behavioral thresholds. For example, it can reveal whether `SELF` or `REST` begins to dominate when energy drops below a certain level.

---

##### 7. Food Consumption Rate Over Time

**Output:**

```text
food_consumption_rate_<name>.png
```

**Purpose:**  
Tracks food-related behavior over time.

Variables:

```text
PICK rate
EAT rate
available food count
```

**Interpretation:**  
This plot tests whether the population maintains energy because food intake roughly balances energy expenditure. It is useful for identifying break-even behavior between energy gain and energy loss.

---

##### 8. Spatial Heatmap of Mother Population

**Output:**

```text
spatial_heatmap_population_<name>.png
```

**Purpose:**  
Shows where mothers spend most time on the grid.

**Interpretation:**  
This helps determine whether agents spread across the environment, cluster around food-rich zones, or repeatedly occupy specific regions. This is important for later phases involving child care, because spatial clustering may influence mother-child interaction dynamics.

---

##### 9. Energy Expenditure Breakdown

**Output:**

```text
energy_expenditure_breakdown_<name>.png
```

**Purpose:**  
Compares major energy loss and gain terms.

Components:

```text
hunger_loss
move_loss
eat_gain
net_energy_change
```

**Interpretation:**  
This plot shows whether the main survival pressure comes from basal hunger cost or movement cost. It also indicates whether eating compensates for total energy expenditure.

---

#### Plot Enable / Disable System

All additional plots can be turned on or off from `config.py`.

Example:

```python
ENABLE_ACTION_SELECTION_PLOT = True
ENABLE_MOTIVATION_SELECTION_PLOT = True
ENABLE_FAILED_SELECTION_PLOT = True
ENABLE_STACKED_ACTION_FAILED_PLOT = True
ENABLE_FAILED_SELF_ENERGY_CORRELATION_PLOT = True
ENABLE_STATE_SPACE_ENERGY_ACTION_PLOT = True
ENABLE_FOOD_CONSUMPTION_PLOT = True
ENABLE_SPATIAL_HEATMAP_PLOT = True
ENABLE_ENERGY_EXPENDITURE_PLOT = True
```

To disable a specific plot:

```python
ENABLE_SPATIAL_HEATMAP_PLOT = False
ENABLE_FAILED_SELF_ENERGY_CORRELATION_PLOT = False
```

The main validation plot is always generated. The switches only control diagnostic plots.

---

#### Updated Outputs

For `single` mode:

```text
outputs/phase2_survival_minimal/<timestamp>_validation_selected_baselines/
├── validation_single.png
├── action_selection_single.png
├── motivation_selection_single.png
├── failed_selection_single.png
├── stacked_action_failed_single.png
├── correlation_failed_self_energy_single.png
├── correlation_failed_forage_energy_single.png
├── state_space_energy_action_single.png
├── food_consumption_rate_single.png
├── spatial_heatmap_population_single.png
├── energy_expenditure_breakdown_single.png
├── validation_single.csv
├── correlation_summary_single.csv
├── correlation_failed_forage_summary_single.csv
└── auto_baseline_summary.json
```

For `sweep` mode, the same diagnostic outputs are generated separately for:

```text
balanced
easy
harsh
```

Example:

```text
validation_balanced.png
action_selection_balanced.png
motivation_selection_balanced.png
failed_selection_balanced.png
stacked_action_failed_balanced.png
correlation_failed_self_energy_balanced.png
correlation_failed_forage_energy_balanced.png
state_space_energy_action_balanced.png
food_consumption_rate_balanced.png
spatial_heatmap_population_balanced.png
energy_expenditure_breakdown_balanced.png
```

---

#### Current Diagnostic Interpretation

From the current single-condition diagnostic plots:

1. **Motivation-to-action gap exists.**  
   Early in the run, `FORAGE` can be higher than `MOVE + PICK`, meaning some forage motivations fail to become realized actions.

2. **Failed forage should be inspected separately.**  
   `FAILED_FORAGE` explains cases where the agent attempts to forage but cannot move or pick food.

3. **SELF is mainly expressed through REST and EAT.**  
   When `SELF` is higher than `REST + EAT`, the remaining gap is represented by `FAILED_SELF`.

4. **Energy is quasi-stable, not perfectly steady.**  
   The validation plot shows a slight late-run downward slope in energy. This suggests the system is stable over 1,000 ticks but should be tested over longer durations before claiming absolute steady state.

5. **Correlation plots are diagnostic, not causal proof.**  
   Positive correlation between failed selections and energy drop suggests a relationship, but does not alone prove causality.

---

#### Updated Usage

Run full sweep and generate enabled diagnostic plots:

```bash
python experiments/phase2_survival_minimal/run.py --mode sweep --duration 1000 --repeats 3
```

Run one hand-picked configuration with more repeats:

```bash
python experiments/phase2_survival_minimal/run.py --mode single --duration 1000 --repeats 10
```

Run sensitivity sweep:

```bash
python experiments/phase2_survival_minimal/sensitivity_sweep.py --duration 1000 --seeds 5 --repeats 3
```