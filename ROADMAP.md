# ROADMAP: A-Life Maternal-Care Emergence

> ⚠ **COLLABORATOR NOTE: IF YOU DON'T KNOW, JUST ASK — NO GUESSING.**
> Do not fill in unknown values, infer undocumented behavior, or assume parameter names.
> Read the actual source files before writing anything.

Last updated: 2026-05-11
Branch: V3
Deadline: 2026-05-17

---

## Research Question (Locked)

Can kin-directed maternal caregiving emerge from selfish-lineage persistence under
asynchronous evolution, without a dedicated altruism gene or hardcoded altruistic policy?

**Scope statement (locked):**
This project does **not** search for the "best mother." It builds a highly stochastic
world with **no explicit caregiving bias** and asks whether caregiving emerges cleanly
under ecological pressure. Selection pressure primarily favors selfish lineage
persistence. If a stable caregiving strategy appears, we interpret it as a
**world-specific local optimum**, not a universal optimum.

**Implicit fitness (locked):**
No explicit reward function is optimized. Ecological pressure is the only selector.
Within-lifetime plasticity is driven by **endogenous homeostatic signals**
(drive reduction / local state improvement), not an externally authored reward.
Primary Phase 5 interpretation will use **cohort-level lineage viability**:

- child survival / maturation viability
- mother persistence
- cohort fitness (matured offspring per mother cohort)
- plasticity dependence over generations

The current tick-snapshot `c_matr_cum` in `snapshots.csv` is exploratory only and is
not the final inferential fitness statistic.

**Baldwin decomposition (locked):**

- **Global search** = inherited genome mutation + selection across generations
- **Local search** = within-life adjustment of the expressed motivation vector
  (`care`, `forage`, `self`)
- **Plasticity signal** = endogenous homeostatic / drive-reduction signal
  (own hunger relief, fatigue relief, own-child distress reduction)
- **Learning cost** = energetic burden of plastic updates plus plasticity maintenance
- **Not in scope** = local search over all genes, or direct inheritance of learned phenotype
- `phenotype_retention` remains reserved / inactive for the current non-Lamarckian interpretation

---

## Framework: Three Blocks

```
┌─────────────────────────────────────────────────────┐
│  BLOCK 1 — World Setup    (✅ COMPLETE)             │
│  Validate mechanics. Sweep eco space.               │
│  Lock BEST_ECOLOGICAL (Phase 4b).                   │
│  Phases 1 / 2 / 3 / 3b / 4                         │
│  Mechanisms remain disabled (0.0).                  │
└────────────────────┬────────────────────────────────┘
                     │  Phase 4b BEST_CALIBRATED locked
                     ▼
┌─────────────────────────────────────────────────────┐
│  BLOCK 2 — Emergence Under Eco Pressure (🔨 TO BUILD)│
│  Init genome: care=forage=self=1/3 (sum=1).         │
│  Renormalize genome after every mutation.           │
│  Ecology: Phase 4b BEST_CALIBRATED.                 │
│  Keep world stochastic / minimally hardcoded.       │
│  Run ~100 generations, multi-seed.                  │
│  Compare plasticity ON vs OFF.                      │
└────────────────────┬────────────────────────────────┘
                     │  evolved genome weights
                     ▼
┌─────────────────────────────────────────────────────┐
│  BLOCK 3 — Eco Pressure Analysis  (TO BUILD)        │
│  Take evolved genome. Optionally vary mechanisms    │
│  (food_entropy_alpha / cry_decay_radius /           │
│   temperature_sensitivity) one at a time — OVAT.    │
│  Measure care behavior response.                    │
└─────────────────────────────────────────────────────┘
```

---

**Status note (2026-05-11):** the block schematic is historical. In code, Block 2
software is now implemented; the remaining work is experiment execution and
interpretation.

## Software Architecture (Scalability Contract)

All three blocks run on the **same core engine**. No phase-specific logic lives in `simulation.py`.

| Layer | File | Role |
| --- | --- | --- |
| Config (Phase 1–4) | `config.py` | **FROZEN** — `Config` dataclass, all Phase 1–4 parameters |
| Config (Phase 5+) | `experiments/phase5_evolution/config.py` | `Phase5ConfigFactory` — static factory; loads Phase 4b JSON, builds `Config` |
| Runner (Phase 5+) | `experiments/phase5_evolution/run.py` | `RunParams` dataclass + `EvolutionRunner` class; parallel sweep + snapshot capture |
| Plotter (Phase 5+) | `experiments/phase5_evolution/plot.py` | Exploratory snapshot dashboard + lifecycle/cohort plotter |
| Engine | `simulation/simulation.py` | Generic `Simulation(config)` — used by all phases/blocks |
| Agents | `agents/mother.py`, `agents/child.py` | OOP agents; phenotype-vector plasticity wiring in `mother.py` |
| Evolution | `evolution/genome.py` | `Genome` dataclass + `_mutate_gene()` + `_renormalize()` private statics |

**Key contracts:**

- `config.py` (root) is **frozen**. Phase 5+ config logic lives in `Phase5ConfigFactory`, not in root `config.py`.
- `EvolutionRunner._run_worker` is a `@staticmethod` — only `RunParams` (plain dataclass) crosses the process boundary.
- `EvolutionRunner._sample()` is the single definition of all tracked metrics — adding a metric edits this only.
- Plots read from CSV only — decoupled from simulation; always re-runnable with `--output-file`.

---

## Block 1 — World Setup (✅ COMPLETE)

| Phase | Goal | Result | Status |
| --- | --- | --- | --- |
| Phase 1 | Mechanics: mutation, inheritance, reproduction, softmax, stochasticity | 7/7 tests pass | ✅ Complete |
| Phase 2 | Mother-only eco baselines; sweeps `init_food × move_cost × eat_gain` | Three canonical ecologies locked (HARSH / BALANCED / EASY) | ✅ Complete |
| Phase 3 | Children + ISM sweep; identified care trap mechanism | C_matr = 0.000 across all conditions | ✅ Complete (null result) |
| Phase 3b | Subsumed into Phase 3 (ISM locked at 2.33) | BEST_ECOLOGICAL locked (ISM=1.2, eat_gain=0.70, init_food=600, move_cost=0.005) | ⛔ Deprecated |
| Phase 4 | Motivation weight sweep to identify viable care weights | Weight combinations identified | ✅ Complete |

**Mechanism configuration:** Ecological mechanisms (food_entropy_alpha, cry_decay_radius, temperature_sensitivity) remain **disabled (0.0)** to avoid re-run delays. Block 2 and 3 use this same baseline.

**Engine capabilities (permanent, carry into Block 2/3):**

- Own-child exclusivity — `own_child_id` in `simulation.py`
- Starvation floor — `care_energy_floor = 0.3`
- Genome normalization — after every mutation: `w /= w.sum()` so genome always sums to 1.0
- Shannon entropy food — `food_entropy_alpha` in `config.py` (disabled for Block 2)
- Temperature cycle — `temperature_sensitivity` in `config.py` (disabled for Block 2)

**Locked output for Block 2:**
`outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json` → `BEST_CALIBRATED` (Phase 4b result)

---

## Block 2 — Baldwin Emergence

### Design

| Parameter | Value |
| --- | --- |
| Starting genome | `care = forage = self = 1/3` — normalized sum = 1, neutral, no pre-baked bias |
| Genome mutation | After every mutation: renormalize by sum → weights always sum to 1.0 |
| Ecology | Phase 4b BEST_CALIBRATED (`outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json`) |
| Mechanisms | Same baseline values as Block 1; avoid extra hardcoded prosocial rules |
| Evolution | mutation ON, reproduction ON |
| Plasticity (primary) | OFF |
| Plasticity (control) | ON — for Baldwin comparison |
| Run length | 40 000 ticks ≈ 100 generations |
| Control seeds | 30 |
| Sweep seeds | 3 |

**Why 1/3 each?** Genome is normalized to sum=1, so 1/3 each = equal budget shares = perfectly neutral start. This keeps the world-builder claim clean: no pre-baked caregiving bias is injected into the starting population.

**Current local-search implementation:**

- Mothers carry an expressed motivation simplex:
  - `expressed_care_weight`
  - `expressed_forage_weight`
  - `expressed_self_weight`
- Action selection uses that expressed simplex directly.
- Local updates are domain-aware:
  - CARE learns from caregiving outcomes
  - FORAGE learns from resource-acquisition outcomes
  - SELF learns from self-maintenance outcomes
- The expressed simplex renormalizes after each update.
- The inherited genome remains the baseline and mutation substrate.

### Interpretive stance

- We are **not** hand-constructing an optimal caregiver.
- We are **not** hardcoding altruism into the action policy.
- The mother is implicitly selfish at the lineage level: preserve her genes as long as possible.
- Under ecological pressure, that selfish lineage logic may still produce **kin-directed altruistic-looking behavior** toward her own child.
- Future work may study environmental sensitivity and epigenetic-like modulation, but that is **outside the scope of this project**.

### Control Matrix (4 conditions)

| Condition | mutation | plasticity | Purpose |
| --- | --- | --- | --- |
| `mut_on_plast_off` | ON | OFF | Genetic selection only — **primary result** |
| `mut_on_plast_on` | ON | ON | Baldwin scaffold + genetic evolution |
| `mut_off_plast_on` | OFF | ON | Phenotypic adjustment only, no selection |
| `mut_off_plast_off` | OFF | OFF | Fixed genome — null baseline |

### Hyperparameter Sweep Grid

| Parameter | Values |
| --- | --- |
| `mutation_rate` | 0.05, 0.10, 0.20 |
| `sigma` | 0.02, 0.05, 0.10 |
| `tau` | 0.05, 0.10 |
| `learning_rate` | sweep if control matrix confirms signal |

### Success Criteria

**Primary Block 2 criterion:**

1. A caregiving-capable lineage remains viable over a shared multi-seed generation window without heavy hardcoding.
2. Cohort reproductive success stabilizes at a non-zero level:
   `reproductive_success(seed s, generation g) = matured offspring of cohort g / mothers in cohort g`.
3. Offspring maturation fraction remains viable:
   `maturation_fraction(seed s, generation g) = matured offspring of cohort g / total children born to cohort g`.
4. In plasticity-ON conditions, learning reliance and/or learning cost drop while reproductive success remains stable.
5. Own-lineage child outcomes remain viable (child survival / maturation does not collapse to extinction).

**Supporting mechanism criteria:**

6. Any heritable shift (including but not limited to `genome.care_weight`) is evidence about the substrate carrying the behavior.
7. If `mean genome care share` rises above the neutral baseline, that is a useful supporting signal — but it is **not the sole definition of success**.

### Metrics

#### A. Exploratory snapshot metrics (tick-based, survivor-biased; dashboard only)

| Metric | Description |
| --- | --- |
| `mean_genome_care_weight` | Mean genome care among currently alive mothers |
| `mean_expressed_care_weight` | Mean expressed care among currently alive mothers |
| `innateness_index` | `1 - mean(plasticity_coefficient)` among currently alive mothers |
| `genome_behavior_distance` | mean total-variation distance between expressed and genome motivation vectors among currently alive mothers |
| `c_matr_cum` | Current cumulative child maturation proxy from living mothers only |
| `n_alive_mothers`, `n_alive_children` | Population state |
| `mean_mother_energy`, `mean_child_energy` | Tick-level energy state |
| `mean_generation`, `highest_generation` | Async generation clock |

#### B. Inferential lifecycle / cohort metrics (Phase 5 statistical analysis)

These are the metrics to use for statistical claims. Seed is the replicate; generation is the cohort index.

| Metric | Definition |
| --- | --- |
| `reproductive_success_s,g` | matured offspring of cohort `g` in seed `s` / mothers in cohort `g` |
| `maturation_fraction_s,g` | matured offspring of cohort `g` in seed `s` / total children born to cohort `g` |
| `plasticity_drift_s,g` | mean total-variation distance between the final expressed motivation vector and the genome motivation vector for mothers in cohort `g` |
| `learning_cost_s,g` | mean lifetime plasticity cost for mothers in cohort `g` = update cost + maintenance cost |
| `child_nRMST_s,g` | normalized restricted mean survival time for children in cohort `g`, horizon = `maturity_age` |
| `mother_nRMST_s,g` | normalized restricted mean survival time for mothers in cohort `g`, horizon = verified mother lifespan horizon |
| `genome_care_s,g` | optional supporting metric: mean `genome.care_weight` of mothers in cohort `g` |

### Planned outputs

**Primary statistical plot families (66 plots total):**

- Reproductive success over generation
- Offspring maturation fraction over generation
- Plasticity reliance / drift over generation
- Learning cost over generation
- Mean child time to death / nRMST over generation
- Mean mother time to death / nRMST over generation

For each family:
- 10 individual seed plots
- 1 overall plot with mean ± 95% CI across seeds

**Optional supporting family (adds 11 more plots, total = 77):**

- Mean genome care share over generation

This supporting family is recommended because it directly visualizes which inherited substrate is changing, but it is not the only success criterion.

### Data requirement for inferential plots

`snapshots.csv` is insufficient for the cohort plot framework. Phase 5 statistical analysis requires lifecycle tables:

- `mother_lifecycle.csv` — one row per mother end-state
- `child_lifecycle.csv` — one row per child death or maturation

Minimum fields:

`seed, agent_id, agent_type, generation, birth_tick, event_tick, event_type, cause, final_genome_care, final_genome_forage, final_genome_self, final_expressed_care, final_expressed_forage, final_expressed_self`

Mother rows also need:

`matured_children, total_children, lifetime_learning_cost, lifetime_update_learning_cost, lifetime_maintenance_cost`

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

### Future-work note

Block 3 is the natural home for world sensitivity analysis and later epigenetic-like extensions:

- how different worlds pull behavior toward different local optima
- whether environmental structure changes the inherited substrate carrying caregiving
- whether stochastic environmental pressures improve or degrade the emergent strategy

These questions are **future work**, not part of the current Block 2 claim.

### Figures

| Figure | Content |
|---|---|
| `fig4_pressure_comparison.png` | Action % and C_matr across eco presets |
| `fig5_pressure_sweep.png` | C_matr vs ISM at fixed evolved genome |

---

## File Organization

```text
agents/
    mother.py                  (shared — Phase 1–5; Phase 5 methods added in-place)
    child.py                   (shared — all phases)

evolution/
    genome.py                  Genome dataclass; _mutate_gene + _renormalize @staticmethods

experiments/
    phase1_mechanics_tests/    (existing)
    phase2_survival_minimal/   (existing)
    phase3_survival_full/      (existing)
    phase5_evolution/          (Block 2 — implemented)
        __init__.py            empty module marker
        config.py              Phase5ConfigFactory — static factory class
        run.py                 RunParams dataclass + EvolutionRunner class
        plot.py                EvolutionPlotter class — CSV-only, no sim dependency

outputs/
    phase4_weight_sweep/
        phase4b_20260510_111325/
            selected_ecology.json   (BEST_CALIBRATED — loaded by Phase5ConfigFactory)
    phase5_evolution/               (auto-created by EvolutionRunner.run_sweep())
        exp_<timestamp>/
            snapshots.csv
            summary.json
            phase5_evolution_analysis.png
            mother_lifecycle.csv
            child_lifecycle.csv
            cohort_plots/
```

Phase 4b JSON is the only cross-phase input to Block 2. No other Phase 4 outputs are loaded.

---

## Commands

**Pilot run — 5 seeds, 5k ticks, relaxed ecology:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 5 --max-ticks 5000 --relax-ecology true --workers 4
```

**Full control run — mut ON / plast OFF (primary result):**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 30 --max-ticks 40000 --plasticity-enabled false --workers 6
```

**Full control run — mut ON / plast ON (Baldwin comparison):**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 30 --max-ticks 40000 --plasticity-enabled true --workers 6
```

**Null baseline — mut OFF / plast OFF:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 30 --max-ticks 40000 --mutation-enabled false --plasticity-enabled false --workers 6
```

**Exploratory plots only (from existing output dir):**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.plot --input-dir outputs/phase5_evolution/exp_<timestamp>
```

---

## Progress Tracker

### Status: Block 1 — World Setup ✅ COMPLETE (mechanisms disabled by decision)

- [x] Phase 1 mechanics validated
- [x] Phase 2 ecological baselines — HARSH / BALANCED / EASY locked
- [x] Phase 3 null result — C_matr = 0 (care trap confirmed)
- [x] Phase 3b — care trap mechanism explained, BEST_ECOLOGICAL locked
- [x] Phase 4 weight sweep — OPTIMAL weights locked (care=0.5, forage=2.0)
- [x] Phase 4b — BEST_CALIBRATED ecology locked (init_food=600, eat_gain=0.70, ISM=1.0)

### Status: Block 2 — Baldwin Emergence

- [x] `experiments/phase5_evolution/__init__.py` — module marker
- [x] `experiments/phase5_evolution/config.py` — `Phase5ConfigFactory` (static class, loads Phase 4b JSON)
- [x] `experiments/phase5_evolution/run.py` — `RunParams` + `EvolutionRunner` (OOP, parallel sweep)
- [x] `experiments/phase5_evolution/plot.py` — exploratory `snapshots.csv` dashboard
- [x] `evolution/genome.py` — OOP refactor: `_mutate_gene`, `_renormalize` static helpers; `lock_learning_rate`
- [x] `agents/mother.py` — guard clauses + docstrings in Phase 5 methods
- [ ] Smoke test (1 seed, 500 ticks): no crash, `snapshots.csv` generated
- [ ] Pilot run (5 seeds, 5k ticks, `--relax-ecology true`): no extinction, plots render
- [ ] Control matrix 4-condition × 30-seed run (40k ticks each)
- [x] Lifecycle log export (`mother_lifecycle.csv`, `child_lifecycle.csv`)
- [x] Cohort statistical plotter (44 primary plots; optional +11 support plots)
- [ ] Emergence / assimilation criterion confirmed or refuted:
  viable cohort fitness + reduced plasticity dependence under ecological pressure
- [ ] Supporting mechanism check: identify which inherited substrate, if any, carries the stabilized behavior

### Status: Block 3 — Eco Pressure

- [ ] Eco pressure OVAT runner (vary food_entropy_alpha / cry_decay_radius / temperature_sensitivity)
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
