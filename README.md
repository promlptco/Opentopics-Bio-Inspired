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

Runs the complete workflow in one command: wide sweep → auto-select balanced/easy/harsh → OVAT around the balanced baseline.
No manual baseline selection step required.

```powershell
# Sequential
python experiments/phase2_survival_minimal/run.py --mode pipeline --duration 1000 --repeats 3

# Parallel (recommended)
python experiments/phase2_survival_minimal/run.py --mode pipeline --duration 1000 --repeats 3 --workers 8
```

Pipeline steps (printed during execution):

**Step 1 — Synthetic starting baseline**
Uses `BALANCED_BASELINE` from `config.py` as the absolute center point.
No manual calibration required. Logs starting parameters.

**Step 2 — OVAT sensitivity sweep (N=50 seeds per point)**
Runs all five OVAT sets (A–E) around the synthetic center.
Each sweep point is averaged over **50 independent seeds** to account for Softmax stochasticity.
Saves `sensitivity_ovat/sensitivity_map.png` with vertical synthetic-center lines visible.

**Step 3 — Dual-metric cliff-edge detection**
For each parameter curve, locates the *last stable point* before the tipping-point collapse:
- **CLEAR** (survival span ≥ 0.20): finds the point satisfying survival ∈ [0.80–0.95] **AND** energy ∈ [0.65–0.75] where the *next adjacent step* shows the steepest drop.
- **UNCLEAR** (flat curve): synthetic value retained; parameter becomes a secondary axis in Step 4.

Prints a table: Parameter | Synthetic | Detected Cliff-Edge | Status | Justification.

**Step 4 — Multi-dimensional validation grid (N=50 per config)**
- **Primary axis**: `init_food` ±4 steps around the cliff-edge center.
- **Secondary axes**: one axis per UNCLEAR parameter (5 evenly-spaced values from its sweep range).
- **CLEAR params**: locked to their cliff-edge values.
- Total configs = food_steps × UNCLEAR_param_combinations; each run N=50 seeds.

**Step 5 — Automated penalty scoring selection**
Scores every Step 4 config with a penalty function combining hard constraints and soft distance-to-target terms:
- **Balanced**: target ≈ 14/15 survival, energy ≈ 0.70, flat slope (slope heavily penalised).
- **Easy**: target ≈ 15/15 survival, energy ≥ 0.85.
- **Harsh**: target ≈ 2–5/15 survival, energy ≤ 0.40.

Prints the final ecological baseline table (exact genome + environment for all three states).

**Step 6 — Diagnostic report generation**
Runs full N=50-seed validation for each selected condition and generates the complete diagnostic suite.

Output layout:
```
outputs/phase2_survival_minimal/<timestamp>_validation_selected_baselines/
├── auto_baseline_summary.json        ← includes _pipeline_meta key
├── validation_balanced.csv / .png
├── validation_easy.csv / .png
├── validation_harsh.csv / .png
├── <all other diagnostic plots>
└── sensitivity_ovat/
    ├── sensitivity_map.png           ← baseline lines mark synthetic center
    ├── set_A_hunger_rate.csv
    ├── set_B_move_cost.csv
    ├── set_C_eat_gain.csv
    ├── set_D_init_food.csv
    └── set_E_rest_recovery.csv
```

---

### Sweep mode — auto-calibration

Runs a grid of candidate configs, selects the best three conditions by validation-first rule,
then saves diagnostic plots and a summary JSON.

```powershell
# Sequential (default)
python experiments/phase2_survival_minimal/run.py --mode sweep --duration 1000 --repeats 3

# Parallel — 8 workers (recommended for multi-core machines)
python experiments/phase2_survival_minimal/run.py --mode sweep --duration 1000 --repeats 3 --workers 8

# Auto-detect worker count
python experiments/phase2_survival_minimal/run.py --mode sweep --workers 0
```

### Single mode — focused validation

Runs one hand-picked config across all validation seeds.

```powershell
# Headless, sequential
python experiments/phase2_survival_minimal/run.py --mode single --duration 1000

# Headless, parallel (faster)
python experiments/phase2_survival_minimal/run.py --mode single --duration 1000 --workers 4

# Live viewer, default speed
python experiments/phase2_survival_minimal/run.py --mode single --duration 1000 --live

# Live viewer, 5× speed
python experiments/phase2_survival_minimal/run.py --mode single --duration 1000 --live --speed 5
```

### OVAT Sensitivity Sweep

One-variable-at-a-time analysis over hunger rate, move cost, eat gain, food count, and rest recovery.

```powershell
# All five sets, sequential
python experiments/phase2_survival_minimal/sensitivity_sweep.py --duration 1000 --seeds 5 --repeats 3

# All five sets, parallel
python experiments/phase2_survival_minimal/sensitivity_sweep.py --duration 1000 --seeds 5 --repeats 3 --workers 8

# Specific sets only (e.g. A and C)
python experiments/phase2_survival_minimal/sensitivity_sweep.py --sets AC

# Auto-detect worker count
python experiments/phase2_survival_minimal/sensitivity_sweep.py --workers 0
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
- `experiments/phase2_survival_minimal/run.py`
- `experiments/phase2_survival_minimal/sensitivity_sweep.py`

> `--live` and `--workers` are independent.
> The live viewer runs one simulation; `--workers` speeds up the headless validation runs.

---

## 🏗️ Project Structure
- `agents/`: Core agent classes (`mother.py`, `infant.py`).
- `simulation/`: World dynamics (`world.py`) and main loop (`simulation.py`).
- `evolution/`: Genetic operators and population management.
- `experiments/`: Targeted validation phases and calibration scripts.
  - `live_viewer.py`: Phase-agnostic live visualizer (shared across all phases).
  - `phase2_survival_minimal/`: Phase 2 ecological survival baseline.
- `outputs/`: Automatically generated plots and JSON data (organized by date/time).

## 📄 Documentation
For detailed information on the research question, experimental methodology, and success criteria, see:
- [EXPERIMENT_DESIGN.md](./EXPERIMENT_DESIGN.md)
- [DESIGN_BASELINE.md](./DESIGN_BASELINE.md)
