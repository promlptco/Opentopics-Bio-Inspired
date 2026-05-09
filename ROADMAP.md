# ROADMAP: A-Life Maternal-Care Emergence

> ⚠ **COLLABORATOR NOTE: IF YOU DON'T KNOW, JUST ASK — NO GUESSING.**
> Do not fill in unknown values, infer undocumented behavior, or assume parameter names.
> Read the actual source files before writing anything.

Last updated: 2026-05-09
Branch: V3
Deadline: 2026-05-17

---

## Research Question (Locked)

Can maternal-care instinct emerge from selfish-lineage selection under asynchronous evolution,
without a dedicated altruism gene?

**Implicit fitness (locked):**
`C_matr` — cumulative child maturation rate (matured / (matured + hunger_dead)).
No explicit fitness function. Ecological pressure is the only selector.

---

## Framework: Three Blocks

```
┌─────────────────────────────────────────────────────┐
│  BLOCK 1 — World Setup    (NEEDS RE-RUN)            │
│  Validate mechanics. Sweep eco space.               │
│  Select and lock BEST_ECOLOGICAL values.            │
│  Phases 1 / 2 / 3 / 3b / 4                         │
│  ⚠ Must re-run with mechanism baseline values ON   │
└────────────────────┬────────────────────────────────┘
                     │  BEST_ECOLOGICAL + mechanism baseline locked
                     ▼
┌─────────────────────────────────────────────────────┐
│  BLOCK 2 — Baldwin Emergence    (TO BUILD)          │
│  Init genome: care=forage=self=1/3 (sum=1).         │
│  Renormalize genome after every mutation.           │
│  Same mechanism baseline as Block 1.                │
│  Run ~100 generations, multi-seed.                  │
│  Baldwin test: plasticity ON vs OFF.                │
└────────────────────┬────────────────────────────────┘
                     │  evolved genome weights
                     ▼
┌─────────────────────────────────────────────────────┐
│  BLOCK 3 — Eco Pressure Analysis  (TO BUILD)        │
│  Take evolved genome. Vary mechanism values         │
│  (food_entropy_alpha / cry_decay_radius /           │
│   temperature_sensitivity) one at a time — OVAT.           │
│  Measure care behavior response.                    │
└─────────────────────────────────────────────────────┘
```

---

## Software Architecture (Scalability Contract)

All three blocks run on the **same core engine**. No phase-specific logic lives in `simulation.py`.

| Layer | File | Role |
|---|---|---|
| Config | `config.py` | Single `Config` dataclass — every parameter in one place |
| Engine | `simulation/simulation.py` | Generic `Simulation(config)` — used by all phases/blocks |
| Agents | `agents/mother.py`, `agents/child.py` | OOP agents; plasticity wiring in `mother.py` |
| Evolution | `evolution/genome.py` | `Genome` dataclass + `mutate()` + `copy()` |
| Experiment | `experiments/*/config.py` | Sets flags, loads locked JSON, defines sweep grid |
| Experiment | `experiments/*/run.py` | Generic parallel sweep runner + snapshot capture |
| Experiment | `experiments/*/plot.py` | Figures from CSVs — no simulation dependency |

**Key contracts:**
- `Simulation.initialize(genomes=None)` — pass explicit genomes or it reads `Config` weights.
  Block 2 passes `genomes=None` with `Config(care_weight=0.5, forage_weight=0.5, self_weight=0.5)`.
- `run_parallel(tasks, worker_fn, workers)` — one reusable function in `run.py`;
  `tasks` is any list of parameter dicts. No phase-specific sweep functions.
- `capture_snapshot(sim)` — one function returns a dict of all tracked metrics per tick.
  Adding a new metric means editing this function only.
- Plots read from CSV only — decoupled from simulation; always re-runnable with `--plot_only`.

---

## Block 1 — World Setup (⚠ NEEDS RE-RUN)

| Phase | Goal | Previous result | Re-run status |
| --- | --- | --- | --- |
| Phase 1 | Mechanics: mutation, inheritance, reproduction, softmax, stochasticity | 7/7 tests pass | ✅ Unaffected by mechanisms — no re-run needed |
| Phase 2 | Mother-only eco baselines; now sweeps `init_food × food_entropy_alpha × move_cost × eat_gain` (4 params) | Old results invalid | 🔁 Re-run — sweep code extension pending |
| Phase 3 | Children + full 6-param sweep: `init_food × food_entropy_alpha × move_cost × eat_gain × temperature_sensitivity × cry_decay_radius` | Old results invalid | 🔁 Re-run — sweep code extension pending |
| Phase 3b | Subsumed into Phase 3 (ISM locked at 2.33, not swept) | Old results superseded | ⛔ Deprecated as standalone phase |
| Phase 4 | Motivation weight sweep with BEST_ECOLOGICAL from Phase 3 | Old results invalid | 🔁 Re-run after Phase 3 locks BEST_ECOLOGICAL |

**⚠ Why re-run:** Three ecological mechanisms (Shannon entropy food, cry attenuation, temperature cycle) must be active at fixed baseline values in ALL blocks. Previous runs used 0.0 for all three. Calibration is now integrated into Phase 2 and Phase 3 sweeps — no separate calibration step needed. See PROGRESS.md `▶ NEXT SESSION TASK LIST`.

**Engine capabilities (permanent, carry into Block 2/3):**

- Own-child exclusivity — `own_child_id` in `simulation.py`
- Starvation floor — `care_energy_floor = 0.3`
- Genome normalization — after every mutation: `w /= w.sum()` so genome always sums to 1.0
- Shannon entropy food — `food_entropy_alpha` in `config.py`; burst replenishment disabled when active
- Temperature cycle — `temperature_sensitivity` in `config.py`; asymmetric cold/warm, children only

**Locked output for Block 2:**
`outputs/phase3_survival_full/selected_ecologies.json` → `BEST_ECOLOGICAL` (produced by Phase 3 re-run)

---

## Block 2 — Baldwin Emergence

### Design

| Parameter | Value |
|---|---|
| Starting genome | `care = forage = self = 1/3` — normalized sum = 1, neutral, no pre-baked bias |
| Genome mutation | After every mutation: renormalize by sum → weights always sum to 1.0 |
| Ecology | BEST_ECOLOGICAL (loaded from Phase 3b JSON; frozen) |
| Mechanisms | Same baseline values as Block 1 (food_entropy_alpha, cry_decay_radius, temperature_sensitivity) |
| Evolution | mutation ON, reproduction ON |
| Plasticity (primary) | OFF |
| Plasticity (control) | ON — for Baldwin comparison |
| Run length | 40 000 ticks ≈ 100 generations |
| Control seeds | 30 |
| Sweep seeds | 3 |

**Why 1/3 each?** Genome is normalized to sum=1, so 1/3 each = equal budget shares = perfectly neutral start. Any rise in `mean_genome_care_weight` above 1/3 is pure ecological selection. `genome.care_weight` IS the effective care share directly — no conversion needed.

### Control Matrix (4 conditions)

| Condition | mutation | plasticity | Purpose |
|---|---|---|---|
| `mut_on_plast_off` | ON | OFF | Genetic selection only — **primary result** |
| `mut_on_plast_on` | ON | ON | Baldwin scaffold + genetic evolution |
| `mut_off_plast_on` | OFF | ON | Phenotypic adjustment only, no selection |
| `mut_off_plast_off` | OFF | OFF | Fixed genome — null baseline |

### Hyperparameter Sweep Grid

| Parameter | Values |
|---|---|
| `mutation_rate` | 0.05, 0.10, 0.20 |
| `sigma` | 0.02, 0.05, 0.10 |
| `tau` | 0.05, 0.10 |
| `learning_rate` | sweep if control matrix confirms signal |

### Success Criteria

1. `mut_on_plast_off`: `mean_genome_care_weight` rises above 1/3 over ~100 generations.
2. `mut_off_plast_off`: care_weight stays flat at 1/3 (no drift, no selection).
3. `C_matr` improves over generations in mutation-ON only.
4. Baldwin signal: `mut_on_plast_on` shows faster early C_matr rise, converges to same endpoint as `mut_on_plast_off`.

### Tracked Metrics (per snapshot tick)

| Metric | Description |
|---|---|
| `mean_genome_care_weight` | Genetic drift / selection signal |
| `mean_expressed_care_weight` | Phenotypic signal (plasticity-ON runs only) |
| `c_matr_cum` | Cumulative child maturation rate |
| `n_alive_mothers` | Population health |
| `mean_mother_energy` | Mother energy dynamics |
| `mean_child_energy` | Child energy dynamics |
| `mean_generation` | Async generation clock |

### Figures

| Figure | Content |
|---|---|
| `fig1_baldwin_template.png` | 4-panel: genome care_weight / plasticity drift / C_matr / mean energy vs generation |
| `fig2_control_endpoints.png` | Endpoint box plots across 4 conditions |
| `fig3_sweep_heatmap.png` | C_matr endpoint across mutation_rate × sigma grid |

---

## Block 3 — Eco Pressure Analysis

### Design

| Parameter | Value |
|---|---|
| Starting genome | Best-emerged weights from Block 2 `mut_on_plast_off` endpoint |
| Mode | `--mode pressure` on same `run.py` |
| Run length | 1 000–5 000 ticks (quick, interactive) |
| Seeds | 1–3 (qualitative interpretation) |

**Eco pressure axes (OVAT — vary one at a time from baseline):**

| Mechanism | Config param | Baseline | Low | High |
|-----------|-------------|---------|-----|------|
| Shannon entropy food | `food_entropy_alpha` | TBD | 0.0 (uniform) | TBD |
| Cry attenuation | `cry_decay_radius` | TBD | 0.0 (perfect) | TBD |
| Temperature cycle | `temperature_sensitivity` | TBD | 0.0 (none) | TBD |

### Eco Presets (via `--eco-preset` or manual CLI flags)

| Preset | Description |
|---|---|
| `BEST_ECO` | Phase 3b baseline — same ecology Block 2 trained on |
| `HARSH` | High starvation pressure (Phase 2 HARSH) |
| `BALANCED` | Moderate pressure (Phase 2 BALANCED) |
| `EASY` | Low pressure (Phase 2 EASY) |
| `CUSTOM` | `--food-alpha`, `--cry-radius`, `--warm-sens` flags |

### Interpretation Questions

- Higher `food_entropy_alpha`: does patchy food force more foraging, suppressing care?
- Higher `cry_decay_radius`: does weaker cry signal reduce care responsiveness?
- Higher `temperature_sensitivity`: does thermal pressure compete with care for energy budget?
- What combination of pressures breaks the evolved care behavior?

### Figures

| Figure | Content |
|---|---|
| `fig4_pressure_comparison.png` | Action % and C_matr across eco presets |
| `fig5_pressure_sweep.png` | C_matr vs ISM at fixed evolved genome |

---

## File Organization (Minimal New Files)

```
experiments/
    phase1_mechanics_tests/    ← existing ✓
    phase2_survival_minimal/   ← existing ✓
    phase3_survival_full/      ← existing ✓
    phase5_evolution/          ← NEW (3 files only)
        config.py              loads BEST_ECO JSON; defines sweep grid; no simulation logic
        run.py                 generic parallel runner; 3 modes: test / control / sweep + pressure
        plot.py                reads CSVs; all figures; --plot_only always works

outputs/
    phase3_survival_full/      ← provides BEST_ECOLOGICAL ✓
    phase5_evolution/          ← auto-created by run.py
        test/    data/  plots/
        control/ data/  plots/
        sweep/   data/  plots/
        pressure/<preset>/ data/ plots/
```

No `phase4_weight_sweep` in the Block 2 pipeline. Phase 4 outputs are not loaded.

---

## Commands

**Smoke test — 5 seeds, verify plot output:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --mode test --seeds 5 --workers 4
```

**Full control matrix — 30 seeds, primary result:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --mode control --seeds 30 --workers 6
```

**Hyperparameter sweep:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --mode sweep --workers 4
```

**Eco pressure — Block 3:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --mode pressure --eco-preset HARSH
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --mode pressure --ism 1.8 --eat-gain 0.5
```

**Plots only:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --mode control --plot_only
```

---

## Progress Tracker

**Block 1 — World Setup (⚠ NEEDS RE-RUN)**
- [x] Phase 1 mechanics validated (without mechanisms)
- [x] Phase 2 ecological baselines (without mechanisms)
- [x] Phase 3 null result — C_matr = 0 (without mechanisms)
- [x] Phase 3b null result — care trap + BEST_ECOLOGICAL locked (without mechanisms)
- [x] Phase 4 weight sweep — viable weight regimes found (without mechanisms)
- [ ] **Mechanism baseline values calibrated** ← START HERE
- [ ] Phase 1–4 re-run with mechanism baseline values ON

**Block 2 — Baldwin Emergence**
- [ ] `experiments/phase5_evolution/` code written (config + run + plot)
- [ ] Genome normalization (sum=1 after mutation) implemented
- [ ] Smoke test: generation x-axis, energy panels, genome drift visible
- [ ] Control matrix 30-seed run complete
- [ ] Baldwin signal confirmed or refuted
- [ ] Hyperparameter sweep complete
- [ ] Stats: Mann-Whitney endpoint test + rank-biserial effect size

**Block 3 — Eco Pressure**
- [ ] `--mode pressure` with mechanism OVAT wired in run.py
- [ ] food_entropy_alpha sweep complete
- [ ] cry_decay_radius sweep complete
- [ ] temperature_sensitivity sweep complete
- [ ] Pressure interpretation written

**Paper**
- [ ] ≤ 6 figures locked
- [ ] Introduction, Methods, Results drafted

---

## Core Files (Do Not Change Without Reason)

| File | Role |
|---|---|
| `simulation/simulation.py` | Universal engine — used by all blocks |
| `agents/mother.py` | Mother OOP agent; plasticity in `plastic_update()` |
| `agents/child.py` | Child OOP agent; maturation logic |
| `evolution/genome.py` | `Genome` dataclass; `mutate()`, `copy()` |
| `config.py` | Single `Config` dataclass — all parameters |
| `outputs/phase3_survival_full/phase3b_calibration/selected_ecologies.json` | BEST_ECOLOGICAL — loaded by Block 2/3 |
