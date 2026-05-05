# OpenTopics: Bio-Inspired Maternal Care Simulation

A simulation of the minimum ecological conditions for the emergence of kin-biased maternal care using evolving neuroendocrine agents.

## 🚀 Quick Start

### Installation
1. Ensure you have Python 3.10+ installed.
2. Install dependencies:
   ```powershell
   pip install numpy matplotlib scipy pygame
   ```

### Running Simulations

#### Main Simulation (Visual)
Runs the interactive real-time visualization:
```powershell
python main.py
```

---

## 🧪 Phase 1 — Mechanics Tests

Verifies that all core agent mechanics are correct before any ecological experiment.
Each test is an independent script; `run.py` executes all six in sequence.

```powershell
# Run the full Phase 1 test suite
python experiments/phase1_mechanics_tests/run.py
```

Expected output on success:
```
=== Phase 1: ALL TESTS PASSED ===
```

To run a single test in isolation:
```powershell
python experiments/phase1_mechanics_tests/test_01_mutation.py
python experiments/phase1_mechanics_tests/test_02_inheritance.py
python experiments/phase1_mechanics_tests/test_03_reproduction.py
python experiments/phase1_mechanics_tests/test_04_population_stability.py
python experiments/phase1_mechanics_tests/test_05_stochasticity_identity.py
python experiments/phase1_mechanics_tests/test_06_softmax_calibration.py
```

| Test file | What it checks |
|---|---|
| `test_01_mutation.py` | Mutated genome differs from parent; values stay in `[0, 1]` |
| `test_02_inheritance.py` | Child genome is a copy of parent before mutation |
| `test_03_reproduction.py` | Energy deducted, cooldown applied, child spawns nearby |
| `test_04_population_stability.py` | No immediate extinction or explosion; deterministic with seed |
| `test_05_stochasticity_identity.py` | Same seed → identical action sequences; different seed → different |
| `test_06_softmax_calibration.py` | Softmax output matches Boltzmann equation; sampling proportional at fixed seed |

---

## 🌿 Phase 2 — Survival-Minimal Baseline

Ecological survival calibration. Mother-only, no children, no reproduction.
Finds parameter sets (`balanced`, `easy`, `harsh`) where the population survives stably.

### Pipeline mode — fully automatic (recommended)

Runs the complete 8-step ROADMAPS.md workflow in one command.
No manual baseline selection required.

```powershell
# Sequential
python -m experiments.phase2_survival_minimal.new_run --mode pipeline --duration 1000 --repeats 3

# Parallel (recommended)
python -m experiments.phase2_survival_minimal.new_run --mode pipeline --duration 1000 --repeats 3 --workers 8
```

Pipeline steps (printed during execution):

**Step 1 — Mechanics lock**
Confirms all Phase 2 constraints are active: grid=50×50, energy=1.0, hunger_rate=1/35, tau=0.1, mutation/reproduction/children/plasticity/care all OFF.

**Step 2 — Provisional baseline**
Logs `BALANCED_BASELINE` from `new_config.py` as the starting reference point. No manual calibration required.

**Step 3 — First-pass init_food gradient scan**
Calls `find_food_anchor()`: sweeps `init_food` upward from 10 until mean survival ≥ 50%.
Produces the `anchored_baseline` used in all subsequent steps.

**Step 4 — OVAT sensitivity sweep (N=50 seeds per point)**
Runs all three OVAT sets (A=init_food, B=eat_gain, C=move_cost) around the anchored baseline.
Each sweep point is averaged over **50 independent seeds** to account for softmax stochasticity.
Saves `sensitivity_ovat/sensitivity_map.png` with anchored-baseline reference lines.

**Step 5 — Dual-metric cliff-edge detection**
For each parameter curve, locates the *last stable point* before the tipping-point collapse:
- **CLEAR** (survival span ≥ 0.20): finds the point where the *next adjacent step* shows the steepest drop.
- **UNCLEAR** (flat curve): anchored value retained; parameter becomes a secondary axis in Step 6.

Prints a table: Parameter | Anchored | Detected Cliff-Edge | Status | Justification.

**Step 6 — Multi-parameter validation grid (N=50 per config)**
Builds `init_food × eat_gain × move_cost` grid from cliff-edge detection results.
CLEAR params locked to detected values; UNCLEAR params varied across their sweep range.
Each config run over N=50 seeds.

**Step 7 — Select canonical ecological regimes**
Scores every Step 6 config with a penalty function and selects the best HARSH / BALANCED / EASY configuration.
- **HARSH**: target 25% survival (10–45% bounds)
- **BALANCED**: target 62.5% survival (50–75% bounds)
- **EASY**: target 90% survival (≥80% bound)

Prints the final ecological baseline table (exact genome + environment for all three regimes).

**Step 8 — Final plots + diagnostic report**
Runs full N=50-seed validation for each selected regime and generates the complete diagnostic suite.

Output layout:
```
outputs/phase2_survival_minimal/<timestamp>_validation_selected_baselines/
├── auto_baseline_summary.json        ← includes _pipeline_meta with anchor_food
├── validation_balanced.csv / .png
├── validation_easy.csv / .png
├── validation_harsh.csv / .png
├── <all other diagnostic plots>
└── sensitivity_ovat/
    ├── sensitivity_map.png           ← anchored baseline reference lines
    ├── set_A_init_food.csv
    ├── set_B_eat_gain.csv
    └── set_C_move_cost.csv
```

---

### Sweep mode — auto-calibration

Runs ROADMAPS.md Steps 1-2, 6-8: pre-defined `SWEEP_GRID` (init_food × eat_gain × move_cost),
selects the best three conditions, saves diagnostic plots and summary JSON.
Steps 3-5 (food anchor scan + OVAT + cliff-edge detection) are skipped — use pipeline mode for the full workflow.

```powershell
# Sequential (default)
python -m experiments.phase2_survival_minimal.new_run --mode sweep --duration 1000 --repeats 3

# Parallel — 8 workers (recommended for multi-core machines)
python -m experiments.phase2_survival_minimal.new_run --mode sweep --duration 1000 --repeats 3 --workers 8

# Auto-detect worker count
python -m experiments.phase2_survival_minimal.new_run --mode sweep --workers 0
```

### Single mode — focused validation

Runs ROADMAPS.md Steps 1-2 and Step 8 only: one hand-picked config with all diagnostic plots.
No OVAT, no grid, no regime selection.

```powershell
# Headless, sequential
python -m experiments.phase2_survival_minimal.new_run --mode single --duration 1000

# Headless, parallel (faster)
python -m experiments.phase2_survival_minimal.new_run --mode single --duration 1000 --workers 4

# Live viewer, default speed
python -m experiments.phase2_survival_minimal.new_run --mode single --duration 1000 --live

# Live viewer, 5× speed
python -m experiments.phase2_survival_minimal.new_run --mode single --duration 1000 --live --speed 5
```

### OVAT Sensitivity Sweep (standalone)

One-variable-at-a-time analysis over init_food (Set A), eat_gain (Set B), and move_cost (Set C).
Minimum 10 seeds required for any directional claim.

```powershell
# All three sets, sequential
python -m experiments.phase2_survival_minimal.new_sensitivity --duration 1000 --seeds 10 --repeats 3

# All three sets, parallel
python -m experiments.phase2_survival_minimal.new_sensitivity --duration 1000 --seeds 10 --repeats 3 --workers 8

# Specific sets only (e.g. A and C)
python -m experiments.phase2_survival_minimal.new_sensitivity --sets AC

# Auto-detect worker count
python -m experiments.phase2_survival_minimal.new_sensitivity --workers 0
```

### Phase 2 CLI reference

| Flag | Default | Description |
|---|---|---|
| `--duration` | `1000` | Simulation ticks per run |
| `--repeats` | `3` | Repeats per seed |
| `--tau` | `0.1` | Softmax temperature |
| `--perceptual_noise` | `0.1` | Perceptual noise on food distance |
| `--mode` | `sweep` | `sweep`, `single`, or `pipeline` |
| `--workers` | `1` | Parallel workers (`0` = auto) |
| `--live` | off | Enable live viewer (single mode only) |
| `--speed` | `1` | Live viewer speed: `1`, `2`, or `5` |

### Output files

All outputs are written to `outputs/phase2_survival_minimal/<timestamp>/`:

| File | Description |
|---|---|
| `auto_baseline_summary.json` | Selected configs + validation metrics |
| `validation_<condition>.csv` | Per-run seed/energy/action breakdown |
| `validation_<condition>.png` | Energy + population trajectory |
| `action_selection_<condition>.png` | Action rates over time |
| `motivation_selection_<condition>.png` | Motivation rates over time |
| `rate_sum_check_<condition>.png` | Normalization sanity check |
| `stacked_action_failed_<condition>.png` | Realized + failed action breakdown |
| `correlation_failed_forage_energy_<condition>.png` | FAILED\_FORAGE vs energy decay |
| `state_space_energy_action_<condition>.png` | Energy vs action/motivation scatter |
| `food_consumption_rate_<condition>.png` | PICK/EAT rates + food availability |
| `spatial_heatmap_population_<condition>.png` | Population occupancy heatmap |
| `energy_expenditure_breakdown_<condition>.png` | Episode-level energy flow |
| `homeostatic_balance_<condition>.png` | Energy vs fatigue dynamics |

---

## 🖥️ Live Viewer

Opens an interactive matplotlib window during a single simulation run.
Four panels updated in real-time:

| Panel | Content |
|---|---|
| Top-left | Mean energy trajectory |
| Top-right | Alive population trajectory |
| Bottom-left | Action rates at the current tick (MOVE / PICK / EAT / REST) |
| Bottom-right | Motivation rates at the current tick (FORAGE / SELF) |

### Speed control

| `--speed` | Ticks per frame | Use case |
|---|---|---|
| `1` | 1 | Frame-by-frame, slow observation |
| `2` | 2 | 2× faster |
| `5` | 5 | Fast scan |

Closing the window mid-run does **not** abort the simulation — it finishes headlessly and saves all diagnostic plots normally.

### Replay a saved run (Python API)

```python
from experiments.live_viewer import LiveViewer, ReplayProvider

# `result` is any dict returned by sim.collect_result()
viewer = LiveViewer(speed=2, title="Phase 2 Replay")
viewer.run_replay(ReplayProvider(result))
```

### Phase 3+ integration

`LiveViewer` never imports phase-specific code. To support a new phase, subclass
`Phase2LiveProvider` and extend `get()` with the extra history keys that phase produces:

```python
from experiments.live_viewer import Phase2LiveProvider, LiveViewer

class Phase3LiveProvider(Phase2LiveProvider):
    def get(self) -> dict:
        state = super().get()
        state["child_history"] = list(self.sim.child_history)
        return state

# In phase3 run.py:
sim.initialize()
viewer   = LiveViewer(speed=1, title="Phase 3")
provider = Phase3LiveProvider(sim, total_ticks=args.duration)
viewer.run_live(sim, provider)
result   = sim.collect_result()
```

---

## ⚡ Parallel Execution

All `run_one()` calls are seed-isolated — each run gets its own `set_seed()` and independent random state.
Use `--workers N` to run them in parallel via `ProcessPoolExecutor`.

| `--workers` | Behaviour |
|---|---|
| `1` | Sequential (default, always safe) |
| `N > 1` | N parallel worker processes |
| `0` | Auto: uses `os.cpu_count()` |

**Scripts that support `--workers`:**
- `experiments/phase2_survival_minimal/new_run.py`
- `experiments/phase2_survival_minimal/new_sensitivity.py`

> `--live` and `--workers` are independent.
> The live viewer runs one simulation; `--workers` speeds up the headless validation runs.

---

---

## 🐣 Phase 3 — Mother-Child Caregiving Baseline

Mother + child simulation. Finds the minimum viable ecology (MVE) where mothers can support a dependent child using motivation weights (FORAGE / CARE / SELF).

### Run baseline validation

```powershell
# Sweep mode — grid search over care/forage/self weights
python experiments/phase3_survival_full/run.py --mode sweep --duration 1000 --repeats 3

# Single mode — one hand-picked config
python experiments/phase3_survival_full/run.py --mode single --duration 1000 --repeats 10
```

### Motivation weight grid (48-combination sweep)

```powershell
# Default (15 seeds, 1000 ticks)
python experiments/phase3_survival_full/motivation_sweep.py

# Custom seeds / duration
python experiments/phase3_survival_full/motivation_sweep.py --seeds 30 --duration 1000
```

### Escalation sweep — find the MVE food level

```powershell
# Default sweep food=50→95, step=5, 15 seeds
python experiments/phase3_survival_full/escalation_sweep.py

# Custom range
python experiments/phase3_survival_full/escalation_sweep.py --food_start 50 --food_end 70 --food_step 5 --seeds 15
```

### Action visualization — behavioral characterization

```powershell
python experiments/phase3_survival_full/action_visualization.py
```

### Phase 3 CLI reference

| Flag | Default | Description |
|---|---|---|
| `--duration` | `1000` | Simulation ticks |
| `--repeats` | `3` | Repeats per seed |
| `--seeds` | `15` | Number of seeds (sweep scripts) |
| `--tau` | `0.1` | Softmax temperature |
| `--perceptual_noise` | `0.1` | Perceptual noise on food/child distance |
| `--mode` | `sweep` | `sweep` or `single` |
| `--food_start` | `50` | Start food level (escalation sweep) |
| `--food_end` | `95` | End food level (escalation sweep) |
| `--food_step` | `5` | Step size (escalation sweep) |

### Output files

All outputs → `outputs/phase3_survival_full/<timestamp>/`:

| File | Description |
|---|---|
| `auto_phase3_summary.json` | Selected configs + validation metrics |
| `validation_<name>.png` | Energy + population trajectory |
| `action_selection_<name>.png` | Action rates over time |
| `motivation_selection_<name>.png` | Motivation rates over time |
| `mother_child_diagnostics_<name>.png` | Mother / child energy and feeding |
| `feed_rate_<name>.png` | Feeding event frequency |
| `spatial_heatmap_<name>.png` | Population occupancy heatmap |

---

## 🧬 Phase 4 — Neutral Drift Baseline (Evolution)

Establishes the genetic baseline: does care_weight evolve or drift under standard ecology (no existential infant dependency)?

> **Run scripts 05 and 06 (FIXED) for all scientific conclusions.** Scripts 01–04 contain a known orphan-injection bug and are archived for reference only.

### Definitive scripts (use these)

```powershell
# Script 05 — Ceiling-drop baseline (bug-fixed): care_weight init=0.80, standard cost
python experiments/phase4_neutral_drift_baseline/05_run_ceiling_drop_FIXED.py

# Script 06 — True neutral control (bug-fixed): same as 05 but feed_cost=0 and no infant starvation
python experiments/phase4_neutral_drift_baseline/06_run_true_neutral_FIXED.py
```

### Visualization / analysis scripts

```powershell
# Plot 01 — Artefact mechanism: care crash vs orphan injection rate (stacked)
python experiments/phase4_neutral_drift_baseline/plot_01_artefact_mechanism.py

# Plot 02 — Lineage fitness scatter: buggy vs fixed
python experiments/phase4_neutral_drift_baseline/plot_02_lineage_comparison.py

# Plot 03 — Fixed baselines overlay: Script 05 vs Script 06
python experiments/phase4_neutral_drift_baseline/plot_03_fixed_baselines_overlay.py

# Plot 04 — All-weights stability check (care / forage / self trajectories)
python experiments/phase4_neutral_drift_baseline/plot_04_all_weights_fixed.py

# Turnover analysis
python experiments/phase4_neutral_drift_baseline/05_analyze_turnover.py
```

### Archived scripts (bug-affected — do not use for conclusions)

| Script | Description |
|---|---|
| `01_run_floor_bounce_artefact.py` | Original Phase 4 — floor-bounce artefact from U(0,1) init |
| `02_run_ceiling_drop_erosion.py` | Ceiling-drop recheck — orphan injection bug present |
| `03_run_bounded_drift_validation.py` | Drift validation — orphan injection bug present |
| `04_run_true_neutral_control.py` | Neutral control — orphan injection bug present |

### Output files

All outputs → `outputs/phase4_neutral_drift_baseline/`:

| Directory | Description |
|---|---|
| `05_ceiling_drop_FIXED/` | Script 05 results (care trajectory, r values, checkpoints) |
| `06_true_neutral_FIXED/` | Script 06 results |
| `post_mortem/` | Four visualization plots documenting the bug and fix |

---

## 🏗️ Project Structure

```
agents/           mother.py, child.py — core agent classes
simulation/       world.py, simulation.py — world dynamics and main loop
evolution/        genome.py, lineage.py — genetic operators and lineage tracking
experiments/
  live_viewer.py                    ← phase-agnostic live visualizer
  phase1_mechanics_tests/           ← mechanics validation (6 tests)
  phase2_survival_minimal/          ← ecological survival calibration
  phase3_survival_full/             ← mother-child caregiving baseline
  phase4_neutral_drift_baseline/    ← neutral genetic drift baseline
shared/           constants.py — cross-phase constants
outputs/          auto-generated plots and JSON (organized by phase/timestamp)
```

## 📄 Documentation

- [EXPERIMENT_DESIGN.md](./EXPERIMENT_DESIGN.md) — research question, methodology, phase protocol
- [full_experiment_report.md](./full_experiment_report.md) — full results report (Phases 1–4)
