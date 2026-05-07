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

Runs the interactive real-time pygame grid world visualization.

```powershell
# Survival grid world, light theme (default)
python main.py

# Survival grid world, dark theme (neon gradient)
python main.py --theme dark

# Full mother+child simulation
python main.py --mode maternal

# Dark mode + maternal
python main.py --mode maternal --theme dark

# Headless — no pygame window
python main.py --mode survival --no-visual
```

| Flag | Choices | Default | Description |
|---|---|---|---|
| `--mode` | `survival`, `maternal` | `survival` | `survival` = Phase 2 mothers-only; `maternal` = full mother+child simulation |
| `--theme` | `light`, `dark` | `light` | `light` = white background; `dark` = dark background with neon gradient |
| `--no-visual` | — | off | Run headless without opening a pygame window |

**Visual encoding (both themes):**

| Element | Meaning |
|---|---|
| Agent body color | Energy level — gradient from low (red) to high (blue/cyan) |
| Ring around mother | Current motivation: yellow = FORAGE, blue = SELF, green = CARE |
| Mother ring radius | Larger than child ring |
| Food dot | Small circle on the grid |

**To change simulation parameters** → edit `config.py` (bottom of file):

```python
VISUAL_SURVIVAL_CONFIG = Config(
    init_food=120, move_cost=0.01, eat_gain=0.5, max_ticks=400, ...
)
VISUAL_MATERNAL_CONFIG = Config(seed=42)
```

**To change colors or add a new theme** → edit `ui/renderer_config.py`:

```python
DARK_THEME = RendererTheme(
    bg_color=(12, 12, 20),
    ring_forage=(255, 220, 0),   # neon yellow
    ring_self=(0, 140, 255),     # neon blue
    ring_care=(0, 255, 120),     # neon green
    ...
)
THEMES = {"light": LIGHT_THEME, "dark": DARK_THEME}
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

## 🐣 Phase 3 — init_food Sweep (Children Added) ✅ CONCLUDED

Mother + child simulation. Answers: "Can food density alone, with unbiased motivation weights (all = 1.0) and ISM = 2.33, produce child maturation?"

**Result: NO.** C_matr = 0.000 across all 7 init_food values (40–900) × 10 seeds.

```powershell
python -m experiments.phase3_survival_full.phase3_sweep.run --workers 8
python -m experiments.phase3_survival_full.phase3_sweep.plot
```

### Key files

| File | Role |
|------|------|
| `experiments/phase3_sweep/config.py` | Sweep grid (INIT_FOOD_VALUES, SWEEP_SEEDS) |
| `experiments/phase3_sweep/run.py` | Parallel sweep runner |
| `experiments/phase3_sweep/plot.py` | Three-figure evidence suite |

### Output files

All outputs → `outputs/phase3_sweep/`:

| File | Description |
|---|---|
| `sweep_results.csv` | Aggregated metrics per init_food value |
| `plots/fig1_sweep_summary.png` | init_food vs feeds / M_surv / child death / action split |
| `plots/fig2_timeseries.png` | Per-tick population, mother energy, child energy |
| `plots/fig3_phase2_vs_3.png` | Mother survival and energy: Phase 2 vs Phase 3 |

### Phase 3 conclusion

Food density alone cannot produce child maturation. Maximum feeds/child ≈ 2.1 vs 62 needed at ISM=2.33. The bottleneck is the care trap (softmax cycle time), not food availability.

---

## 🔬 Phase 3b — Ecological Calibration ✅ CONCLUDED

3D parameter sweep (ISM × eat_gain × init_food) with unbiased weights. Answers: "Can ecological parameter tuning rescue child maturation at any ISM level?"

**Result: NO.** C_matr = 0.000 across all 64 grid combos × 5 seeds = 320 runs. CHILD_SURVIVAL_POSSIBLE = False.

**Care trap mechanism:** With tau=0.1 and all weights=1.0, CARE only wins softmax when child distress > forage_cue ≈ 0.86 (child at ~14% energy, ~4 ticks from death). Mother arrives empty-handed (no prior FORAGE). Feed fails. Commitment releases. Loop. Child starves.

```powershell
python -m experiments.phase3_survival_full.phase3b_calibration.run --workers 8
python -m experiments.phase3_survival_full.phase3b_calibration.plot
```

### Key files

| File | Role |
|------|------|
| `experiments/phase3b_calibration/config.py` | ISM/eat_gain/init_food sweep grid, PHASE3B_FLAGS |
| `experiments/phase3b_calibration/run.py` | 8-step pipeline (anchor, OVAT, grid, regime selection) |
| `experiments/phase3b_calibration/plot.py` | 5-figure evidence suite |

### Phase 3b CLI reference

| Flag | Default | Description |
|---|---|---|
| `--workers` | `1` | Parallel workers (`0` = auto) |

### Output files

All outputs → `outputs/phase3b_calibration/`:

| File | Description |
|---|---|
| `grid_sweep.csv` | Aggregated metrics — 64 combos × 5 seeds |
| `ovat_set_A_ism.csv` | ISM sensitivity (aggregated) |
| `ovat_set_B_eat_gain.csv` | eat_gain sensitivity |
| `ovat_set_C_init_food.csv` | init_food sensitivity |
| `selected_ecologies.json` | BEST_ECOLOGICAL regime (ISM=1.2, eat_gain=0.70, init_food=600) |
| `plots/ovat_sensitivity.png` | OVAT panels: M_surv + child_death_mu vs each axis |
| `plots/action_rate.png` | Stacked CARE/FORAGE/SELF% across OVAT axes |
| `plots/feasibility_heatmap.png` | ISM × eat_gain heatmap of child_death_mu |
| `plots/mother_energy.png` | BEST_ECOLOGICAL validation: mother energy trajectory |
| `plots/child_energy.png` | BEST_ECOLOGICAL validation: child energy trajectory |
| `plots/mother_population.png` | BEST_ECOLOGICAL validation: mother population trajectory |
| `plots/child_population.png` | BEST_ECOLOGICAL validation: child population trajectory |
| `plots/care_trap_scatter.png` | CARE% vs child_death_mu scatter across all grid combos |

### Phase 3b conclusion

Ecological tuning alone cannot rescue child maturation. Motivational bias (`care_weight > 1.0`) is necessary. Proceeds to Phase 4.

---

## 🧬 Phase 4 — Motivation Weight Sweep 🔲 PLANNED

Find the minimum `care_weight` that enables child maturation at BEST_ECOLOGICAL parameters (ISM=1.2, eat_gain=0.70, init_food=600).

**Scientific rationale:** With care_weight=2.0, CARE wins softmax when distress > 0.43 (child at 57% energy). Mother has held food from prior free-foraging period → delivers → child survives. ~13 feeds in 200 ticks > 8.4 needed.

*Implementation not yet available.*

---

## 🏗️ Project Structure

```
agents/           mother.py, child.py — core agent classes
simulation/       world.py, simulation.py — world dynamics and main loop
evolution/        genome.py, lineage.py — genetic operators and lineage tracking
experiments/
  live_viewer.py                    ← phase-agnostic live visualizer
  phase1_mechanics_tests/           ← mechanics validation (6 tests)          [DONE]
  phase2_survival_minimal/          ← ecological survival calibration          [DONE]
  phase3_survival_full/             ← all Phase 3 experiments                  [DONE]
    phase3_sweep/                     ← init_food sweep (children added)
    phase3b_calibration/              ← ISM × eat_gain × init_food calibration
  archived/
    phase3_basic/                   ← early diagnostic single-run (superseded)
outputs/          auto-generated plots and JSON (mirrors experiments/ structure)
  phase3_survival_full/
    phase3_sweep/
      percept8/                     ← canonical Phase 3 result (perception_radius=8)
      archived/
        percept15/                  ← earlier run with wrong perception radius
    phase3b_calibration/
      plots/                        ← generated evidence figures
```

## 📄 Documentation

- [ROADMAP.md](./ROADMAP.md) — full phase pipeline: done phases with results, planned phases with status
- [LOGIC.md](./LOGIC.md) — simulation architecture, code logic, biological reasoning
- [CURRENT_STATE.md](./CURRENT_STATE.md) — detailed current state per phase (parameters, bugs, results)
