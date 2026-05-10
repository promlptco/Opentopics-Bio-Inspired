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

## 🖧 Shared CLI — `experiments/base/`

Phases 2–4 share a common CLI layer built on `experiments/base/cli.py`.
Each phase has an `experiment.py` entry point that accepts the same flags.

### Entry points

```powershell
python -m experiments.phase2_survival_minimal.experiment --mode pipeline --workers 4
python -m experiments.phase3_survival_full.experiment    --mode pipeline --workers 4
python -m experiments.phase4_weight_sweep.experiment     --mode sweep    --workers 4
```

### Full flag reference

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `pipeline` | Phase-specific modes (`pipeline` / `sweep` / `single` / `caretrap`) |
| `--load RESULT.json` | — | Load a prior phase output JSON and auto-set matching Config params |
| `--load-key KEY` | auto | Sub-key inside the loaded JSON (e.g. `OPTIMAL`, `BALANCED`, `BEST_ECOLOGICAL`). Auto-detected when the file contains exactly one nested dict. |
| `--config FILE.json` | — | Hand-written Config override JSON (applied after `--load`) |
| `--duration N` | 400 | Simulation ticks |
| `--seeds N` | 10 | Seeds per config |
| `--workers N` | 4 | Parallel workers (`0` = `os.cpu_count()`) |
| `--output-dir PATH` | auto | Explicit output directory (timestamped if omitted) |
| `--param key=value` | — | Override any `Config` field (repeatable; highest priority) |
| `--caretrap_json PATH` | — | (`caretrap` mode only) Path to `selected_ecologies.json`; uses Phase 3-selected params instead of `BALANCED_BASELINE` |
| `--caretrap_cond` | `balanced` | (`caretrap` mode only) Which ecology to load from `--caretrap_json` (`balanced` / `harsh` / `easy`) |

**Priority (lowest → highest):** `--load` < `--config` < `--param`

### `--load`: phase chaining

`--load` reads a prior phase's output JSON and maps its scalar fields directly onto `Config`.
Use `--load-key` to select which nested sub-dict to load.

```powershell
# Phase 4 — load Phase 3b BEST_ECOLOGICAL ecology
python -m experiments.phase4_weight_sweep.experiment `
    --load outputs/phase3_survival_full/phase3b_calibration/selected_ecologies.json `
    --load-key BEST_ECOLOGICAL `
    --mode sweep --workers 4

# Phase 5 — load Phase 4 OPTIMAL weights as starting genome
python -m experiments.phase5_evolution.experiment `
    --load outputs/phase4_weight_sweep/sweep_.../selected_weights.json `
    --load-key OPTIMAL `
    --mode test --workers 4

# Override one param on top of loaded values
python -m experiments.phase4_weight_sweep.experiment `
    --load outputs/.../selected_ecologies.json --load-key BEST_ECOLOGICAL `
    --param max_ticks=800 --workers 4
```

When `--load-key` is omitted and the JSON has exactly one nested dict, that key is used automatically.
For multi-key files (`OPTIMAL` + `VIABLE_MIN`, or `harsh` + `balanced` + `easy`) the key must be specified explicitly.

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

## 🧬 Phase 4 — Motivation Weight Sweep ✅ CONCLUDED

Find the minimum `care_weight` that enables child maturation at BEST_ECOLOGICAL parameters (ISM=1.2, eat_gain=0.70, init_food=900).

**Result: child maturation becomes viable once two structural traps are removed.**
- Trap 1 — Allomothering pool: all mothers converged on 1–2 most-distressed strangers. Fixed by own-child exclusivity (maternal imprinting via `own_child_id`).
- Trap 2 — Maternal starvation: high care_weight prevented mother from eating. Fixed by `care_energy_floor=0.3` (starvation floor, Approach E).

**VIABLE_MIN (first successful):** `care=0.1, forage=0.5, self=0.5` → c_matr=0.120  
**OPTIMAL regime (selection score = c_matr × m_surv):** `care=0.2, forage=1.0, self=0.1` → c_matr=0.533, m_surv=0.787

```powershell
python -m experiments.phase4_weight_sweep.run --workers 4
python -m experiments.phase4_weight_sweep.run --skip_ovat --skip_grid   # threshold only
python -m experiments.phase4_weight_sweep.run --plot_only               # regenerate plots
```

### Key files

| File | Role |
|------|------|
| `experiments/phase4_weight_sweep/config.py` | Sweep grid, `_load_best_eco()`, `make_config()` |
| `experiments/phase4_weight_sweep/run.py` | 7-step pipeline: threshold → OVAT → grid → self-refinement → selection → validation |
| `experiments/phase4_weight_sweep/plot.py` | 5-figure suite incl. 3-panel heatmap (C_matr, M_surv, selection score) |

### Phase 4 CLI reference

| Flag | Description |
|------|-------------|
| `--workers N` | Parallel workers |
| `--skip_threshold` | Skip Step 1 |
| `--skip_ovat` | Skip Steps 2–4 |
| `--skip_grid` | Skip Step 5 |
| `--skip_self` | Skip Step 5b self-weight refinement |
| `--skip_val` | Skip Step 7 validation |
| `--plot_only` | Regenerate plots from saved CSVs |

### Output files

All outputs → `outputs/phase4_weight_sweep/`:

| File | Description |
|------|-------------|
| `selected_weights.json` | VIABLE_MIN + OPTIMAL regimes → used as Phase 5 starting genome |
| `threshold.csv` | care_weight scan results (forage=self=0.5 fixed) |
| `grid_sweep.csv` | care × forage grid aggregated results |
| `self_refinement.csv` | self_weight sweep at grid OPTIMAL |
| `validation_optimal.csv` | 10-seed validation of OPTIMAL config |
| `fig1_ovat.png` | OVAT panels: care / forage / self sensitivity |
| `fig2_threshold.png` | C_matr + M_surv vs care_weight threshold |
| `fig3_grid_heatmap.png` | 3-panel heatmap: C_matr, M_surv, selection score |
| `fig4_validation_timeseries.png` | Energy + population over time for OPTIMAL |
| `fig2b_self_refinement.png` | self_weight sweep at OPTIMAL (care, forage) |

---

## 🧬 Phase 5 — Baldwin Emergence Evolution ▶ CURRENT

Block 2 of the research pipeline. Asynchronous lineage evolution with a 4-condition control matrix:
mutation ON/OFF × plasticity ON/OFF. Starting genome: `care = forage = self = 1/3` (neutral, no bias).
Answers: "Does ecological pressure alone drive genetic care share above the neutral 1/3 baseline?"

**Starting genome:** care=forage=self=1/3, renormalized after every mutation (no pre-baked bias)
**Ecology:** Phase 4b BEST_CALIBRATED (loaded from `outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json`)
**Success criterion:** `mean_genome_care_weight > 1/3` in `mut_on_plast_off`; stays flat in `mut_off_plast_off`

### Pilot run (5 000 ticks, live visualization)

```powershell
# Live grid visualization — opens a pygame window (single seed, default)
python -m experiments.phase5_evolution.run --seeds 1 --max-ticks 5000 --relax-ecology true

# Render every 5 ticks for faster preview
python -m experiments.phase5_evolution.run --seeds 1 --max-ticks 5000 --relax-ecology true --vis-every 5

# Headless pilot (no visualization)
python -m experiments.phase5_evolution.run --seeds 1 --max-ticks 5000 --relax-ecology true --headless
```

### Control matrix runs (40 000 ticks × 30 seeds each)

```powershell
# Primary result — mutation ON, plasticity OFF
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 30 --max-ticks 40000 --plasticity-enabled false --workers 6 --headless

# Baldwin comparison — mutation ON, plasticity ON
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 30 --max-ticks 40000 --plasticity-enabled true --workers 6 --headless

# Null baseline — mutation OFF, plasticity OFF
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 30 --max-ticks 40000 --mutation-enabled false --plasticity-enabled false --workers 6 --headless
```

### Regenerate plots from saved output

```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.plot --input-dir outputs/phase5_evolution/exp_<timestamp>
```

### Key files

| File | Role |
|------|------|
| `experiments/phase5_evolution/config.py` | `Phase5ConfigFactory` — static factory; loads Phase 4b JSON; builds `Config` |
| `experiments/phase5_evolution/run.py` | `RunParams` dataclass + `EvolutionRunner` class; parallel sweep + snapshot capture |
| `experiments/phase5_evolution/plot.py` | `EvolutionPlotter` — reads CSVs only; 4-panel Baldwin trajectory figure |
| `experiments/phase5_evolution/viewer.py` | `Phase5GridViewer` — live pygame grid window with Phase 5 HUD overlay |

### Phase 5 CLI reference

| Flag | Default | Description |
|------|---------|-------------|
| `--seeds` | `10` | Seeds to run (forced to 1 when `--headless` is not set) |
| `--max-ticks` | `40000` | Simulation ticks per seed |
| `--mutation-enabled` | `true` | Enable genetic mutation during reproduction |
| `--plasticity-enabled` | `true` | Enable phenotypic learning |
| `--mutation-rate` | `0.05` | Per-gene mutation probability |
| `--mutation-sigma` | `0.02` | Gaussian σ for mutation magnitude |
| `--learning-rate` | `0.05` | Initial learning rate for all genomes |
| `--plasticity-coefficient` | `0.5` | Initial plasticity coefficient |
| `--relax-ecology` | `false` | Inflate init_food × 1.15 for pilot runs |
| `--workers` | `4` | Parallel processes (`--headless` only; ignored with visualization) |
| `--seed-start` | `42` | First seed value; subsequent seeds increment by 1 |
| `--headless` | off | Disable live visualization; required for `--seeds > 1` |
| `--vis-every` | `1` | Render one frame every N ticks (use 10+ to preview long runs without slowdown) |
| `--output-dir` | auto | Explicit output path (auto-timestamped if omitted) |

### Live visualization

When `--headless` is **not** set, a pygame window shows the grid world in real time:

| Visual element | Meaning |
| --- | --- |
| Mother body colour | Energy — gradient from red (dying) to blue (healthy) |
| Ring around mother | Last motivation: yellow = FORAGE, blue = SELF, green = CARE |
| Child body colour | Distress — gradient from green (calm) to red (distressed) |
| Yellow line | Mother-child link (own-child bond) |
| HUD line 1 | Tick, alive mothers, alive children, condition label |
| HUD line 2 | `genome_care` vs 1/3 baseline, `c_matr_cum`, mean generation |
| HUD legend | Motivation ring colour key |

Closing the window mid-run does **not** abort the simulation — it finishes headlessly and writes all output files normally.

Use `--vis-every 10` or higher to run long simulations without slowing them down — only 1 in every N ticks is rendered.

### Phase 5 output files

All outputs → `outputs/phase5_evolution/exp_<timestamp>/`:

| File | Description |
| --- | --- |
| `snapshots.csv` | Per-tick metrics for all seeds (seed, tick, mean_genome_care, c_matr_cum, …) |
| `summary.json` | Final-tick summary: params + per-seed final_stats |
| `phase5_evolution_analysis.png` | 4-panel figure: genome care weight / expressed care / innateness index / genome-behavior distance |

---

## 🏗️ Project Structure

```
agents/           mother.py, child.py — core agent classes
simulation/       world.py, simulation.py — world dynamics and main loop
evolution/        genome.py, lineage.py — genetic operators and lineage tracking
experiments/
  base/                             ← shared CLI + base class (all phases)
    experiment.py                     ← BaseExperiment ABC (run_sweep, save_csv, apply_overrides)
    cli.py                            ← build_parser(), load_overrides() with --load/--load-key
    io_utils.py                       ← make_output_dir(), write_csv/json helpers
  live_viewer.py                    ← phase-agnostic live visualizer
  phase1_mechanics_tests/           ← mechanics validation (6 tests)          [DONE]
  phase2_survival_minimal/          ← ecological survival calibration          [DONE]
    experiment.py                     ← CLI entry point (BaseExperiment adapter)
  phase3_survival_full/             ← all Phase 3 experiments                  [DONE]
    experiment.py                     ← CLI entry point
    phase3_sweep/                     ← init_food sweep (children added)
    phase3b_calibration/              ← ISM × eat_gain × init_food calibration
  phase4_weight_sweep/              ← motivation weight sweep                  [DONE]
    experiment.py                     ← CLI entry point
  phase5_evolution/                 ← asynchronous genetic evolution           [CURRENT]
  archived/
    phase3_basic/                   ← early diagnostic single-run (superseded)
outputs/          auto-generated plots and JSON (mirrors experiments/ structure)
  phase3_survival_full/
    phase3_sweep/
    phase3b_calibration/
      selected_ecologies.json       ← BEST_ECOLOGICAL → Phase 5 starting ecology
  phase4_weight_sweep/
    selected_weights.json           ← OPTIMAL weights → Phase 5 starting genome
  phase5_evolution/                 ← generated by Phase 5 runs
```

## 📄 Documentation

| File | Purpose |
|------|---------|
| [PROGRESS.md](./PROGRESS.md) | **Timeline of research findings** — what each phase discovered, why it matters, and how phases connect. Start here to understand the arc of the project. |
| [CURRENT_STATE.md](./CURRENT_STATE.md) | **Technical detail per phase** — exact parameters, locked baselines, bugs fixed, and per-phase status. Referenced by PROGRESS.md for deeper dives. |
| [ROADMAP.md](./ROADMAP.md) | **Research plan** — three-block framework, Block 2 control matrix design, success criteria, progress tracker. |
| [LOGIC.md](./LOGIC.md) | **Simulation architecture** — code logic, agent mechanics, biological reasoning behind design decisions. |
