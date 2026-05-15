# ROADMAP: A-Life Maternal-Care Emergence

> ⚠ **COLLABORATOR NOTE: IF YOU DON'T KNOW, JUST ASK — NO GUESSING.**
> Do not fill in unknown values, infer undocumented behavior, or assume parameter names.
> Read the actual source files before writing anything.

Last updated: 2026-05-15
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

## Scientific Narrative

This project is an incremental ecological exploration. Each phase asks one question,
produces a locked output, and hands that output to the next phase. No phase is run
speculatively — each requires the previous phase's answer.

### The Arc

| Phase | Question | Method | Locked Output |
| --- | --- | --- | --- |
| **Phase 1** | Does the engine work deterministically? | Unit tests | `tau`, `sigma`, base `mutation_rate` |
| **Phase 2** | What do mothers do in isolation? | Eco param sweep | HARSH / BALANCED / EASY regimes |
| **Phase 3** | What happens when children appear? | ISM sweep + care analysis | Care trap mechanism; ISM locked |
| **Phase 4** | What weights make care viable? | Motivation weight OVAT | BEST_CALIBRATED ecology |
| **Phase 4c** | How do ecological mechanisms shape behavior? | Mechanism OVAT: food / cry / temperature | BEST_MECHANISM_SETTINGS |
| **Block 2** | Does care emerge through evolution? | 4-condition control matrix, 30 seeds | Baldwin signal (or null result) |
| **Block 3** | What pressures sustain the evolved strategy? | Optional OVAT on evolved genome | Eco-sensitivity interpretation |

### Why this order?

**Phase 1 first:** Simulation results are meaningless if the engine has bugs. We lock
three calibration constants (`tau`, `sigma`, base `mutation_rate`) at values that produce
deterministic unit-test behavior. In evolution phases these constants can be varied to
study sensitivity — but all unit tests must pass at the locked values first.

**Phase 2 before children:** To understand what mothers contribute to child survival,
we must first know what mothers do when children are absent. Sweeping food abundance,
movement cost, and energy gain produces three reference ecological regimes (HARSH /
BALANCED / EASY) and tells us where "the interesting zone" is — enough pressure to
select, but enough slack to survive.

**Phase 3 as a reality check:** Adding children to the BALANCED ecology tests whether
care appears spontaneously. It does not — `C_matr = 0` across all ISM conditions. This
null result is important: ecological pressure alone does not produce care. A specific
combination of strategy conditions is needed before the question is even askable.

**Phase 4 to unlock the strategy space:** Sweeping motivation weights (care × forage ×
self) identifies combinations where care becomes feasible without causing extinction.
The locked BEST_CALIBRATED weights are not a global optimum; they are a point in
strategy space where the caregiving question can be asked scientifically.

**Phase 4c to understand the world:** Before running expensive multi-seed evolution
(Block 2), we probe how three ecological mechanisms — food distribution structure,
cry-signal propagation, and temperature cycles — modulate population behavior. This
is one-variable-at-a-time (OVAT) with fixed genomes so mechanism effects are isolated
from strategy effects. The locked BEST_MECHANISM_SETTINGS define the ecological world
that Block 2 evolution operates in.

**Block 2 as the core claim:** With a calibrated, well-understood world, we run
multi-seed evolution under four conditions (mutation × plasticity factorial). The
Baldwin effect predicts that within-lifetime plasticity scaffolds genetic assimilation
of care strategies. We test that prediction across 30 seeds.

---

## Framework: Three Blocks

```
┌─────────────────────────────────────────────────────┐
│  BLOCK 1 — World Setup    (✅ Ph1–4 COMPLETE)        │
│  Phase 1: Validate engine. Lock calibration params. │
│  Phase 2: Mother-only eco sweep. Lock 3 regimes.    │
│  Phase 3: Add children. Discover care trap.         │
│  Phase 4: Motivation weight sweep. Lock BEST_CAL.   │
│  Phase 4c: Mechanism OVAT. Lock BEST_MECH.          │
└────────────────────┬────────────────────────────────┘
                     │  BEST_CALIBRATED + BEST_MECHANISM_SETTINGS
                     ▼
┌─────────────────────────────────────────────────────┐
│  BLOCK 2 — Emergence Under Eco Pressure (🔨 ACTIVE)  │
│  Init genome: care=forage=self=1/3 (neutral start). │
│  Renormalize genome after every mutation (simplex). │
│  World: Phase 4b ecology + Phase 4c mechanisms.     │
│  4-condition control matrix × 30 seeds × 40k ticks. │
│  Primary test: does care emerge? Baldwin signal?    │
└────────────────────┬────────────────────────────────┘
                     │  evolved genome weights
                     ▼
┌─────────────────────────────────────────────────────┐
│  BLOCK 3 — Eco Pressure Analysis  (OPTIONAL)        │
│  Take evolved genome from Block 2.                  │
│  Vary eco pressure axes around BEST_MECHANISM.      │
│  Ask: what pressures break or sustain care?         │
└─────────────────────────────────────────────────────┘
```

---

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

## Block 1 — World Setup

| Phase | Question | Result | Status |
| --- | --- | --- | --- |
| Phase 1 | Does the engine work deterministically? | 7/7 tests pass; `tau=0.1`, `sigma=0.02`, `mutation_rate=0.05` locked | ✅ Complete |
| Phase 2 | What do mothers do in isolation? | HARSH / BALANCED / EASY ecologies locked | ✅ Complete |
| Phase 3 | What happens when children appear? | `C_matr=0` (care trap confirmed); ISM locked | ✅ Complete |
| Phase 3b | [subsumed into Phase 3] | BEST_ECOLOGICAL locked (ISM=1.2, eat_gain=0.70, init_food=600, move_cost=0.005) | ⛔ Deprecated |
| Phase 4 | What weights make care viable? | BEST_CALIBRATED locked (care=0.5, forage=2.0) | ✅ Complete |
| Phase 4c | How do mechanisms shape behavior? | BEST_MECHANISM_SETTINGS locked | ⬜ Pending |

**Mechanism configuration through Phase 4:**
Ecological mechanisms (`food_entropy_alpha`, `cry_decay_radius`, `temperature_sensitivity`)
are disabled (0.0) in Phases 1–4 so their effects are not confounded with ecology/weight effects.
Phase 4c is the dedicated experiment to understand and lock mechanism settings.

**Locked output for Block 2:**
`outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json` → `BEST_CALIBRATED`

---

## Phase 1 — Engine Calibration

**Question:** Does the simulation engine behave correctly and deterministically?

**Method:** Unit tests covering all core mechanics. Tests use the locked calibration constants.

| Constant | Locked value | Role |
| --- | --- | --- |
| `softmax_tau` | 0.1 | Action selection sharpness — deterministic enough for unit tests |
| `mutation_sigma` | 0.02 | Per-gene Gaussian noise — small enough for stable unit tests |
| `mutation_rate` | 0.05 | Per-gene perturbation probability — baseline for Block 1 tests |

**Note:** These values serve as calibration anchors for all non-evolutionary phases.
In Block 2 evolution, `mutation_rate` and `mutation_sigma` are swept (see Block 2 Hyperparameter Grid).
`tau` may also be varied in Block 2 to study behavioral sharpness.

**Result:** 7/7 tests pass. Engine validated.

---

## Phase 2 — Mother-Only Ecological Baselines

**Question:** What ecological conditions allow mothers to survive in isolation (no children)?

**Method:** Sweep `init_food × move_cost × eat_gain` with mothers only (`children_enabled=False`).
Identify the range of viable ecologies and characterize three qualitatively distinct regimes.

| Regime | Characteristic | Use |
| --- | --- | --- |
| HARSH | Frequent extinction; high selection pressure | Upper bound on pressure |
| BALANCED | Stable population; meaningful selection | Primary Block 2 ecology zone |
| EASY | Trivial survival; little selection | Lower bound reference |

**Result:** Three canonical ecologies locked. BALANCED identified as the target zone.

---

## Phase 3 — Children + Care Trap Discovery

**Question:** What happens when children are added to the BALANCED ecology?

**Method:** Add children (`children_enabled=True`). Sweep `infant_starvation_multiplier (ISM)`.
Track `C_matr` (child maturation rate) across all conditions.

**Result:** `C_matr = 0.000` across all ISM conditions. Care trap confirmed:
mothers cannot afford to allocate energy to offspring under standard ecological pressure.
The care trap tells us that **ecological pressure alone is not sufficient** to produce care —
we need to first find a strategy space where care is energetically viable.

**ISM locked:** Intermediate ISM value retained as BEST_ECOLOGICAL baseline for Phase 4.

---

## Phase 4 — Motivation Weight Sweep

**Question:** What motivation weight combination (care / forage / self) allows both maternal
survival and non-zero child maturation?

**Method:** OVAT — vary one weight axis at a time from neutral (1/3 each), holding others fixed.
Run at BEST_ECOLOGICAL ecology. Measure survival rate and `C_matr`.

**Result:** Unequal weights — heavy foraging, moderate care, minimal self — allow mothers
to support offspring without starving. BEST_CALIBRATED ecology locked.

**BEST_CALIBRATED output:** `outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json`

Fields loaded by `Phase5ConfigFactory`:
`init_food`, `eat_gain`, `move_cost`, `rest_recovery`, `perception_radius`,
`food_perception_radius`, `infant_starvation_multiplier`

---

## Phase 4c — Ecological Mechanism Screen

**Question:** How do food distribution structure, cry-signal propagation, and temperature
cycles each affect population behavior and care investment?

### Motivation

Phase 4b BEST_CALIBRATED uses uniform food (`food_entropy_alpha=0`), no cry signals,
and no temperature variation. These mechanisms exist in the engine but have never been
tested systematically. Before running expensive Block 2 evolution, we need to know:

1. Does patchy food (Shannon entropy distribution) force different foraging/care trade-offs?
2. Do cry signals enable mothers to locate and respond to distressed infants more effectively?
3. Does a temperature cycle compete with care for the energy budget?

Phase 4c answers these questions with fixed genomes (no mutation) so mechanism effects are
isolated from strategy learning or evolutionary adaptation.

### Design

**Baseline:** Phase 4b BEST_CALIBRATED ecology, all three mechanisms disabled (0.0).

**Fixed genome:** Phase 4b optimal weights (care=0.5, forage=2.0, self=1/3 normalized).
`mutation_enabled=False`. Genome does not change — we are characterizing the world, not evolving.

**Runs per level:** 5 seeds × 10,000 ticks.
(`mother_max_age=400` → one generation ≤ 400 ticks → ~25 generations per run.)

**Approach:** One variable at a time (OVAT). Each mechanism axis is swept independently.
When sweeping mechanism X, mechanisms Y and Z stay at their baseline (disabled) values.

#### Food Distribution Axis (cry=C0, temperature=T0)

| Level | `food_entropy_alpha` | Description |
| --- | --- | --- |
| F0 | 0.00 | Uniform distribution — Phase 4b baseline |
| F1 | 0.01 | Mild Shannon entropy — slight patchiness |
| F2 | 0.05 | Medium Shannon entropy — moderate patchiness |
| F3 | 0.10 | High Shannon entropy — strong patchiness |

#### Cry Signal Axis (food=F0, temperature=T0)

| Level | `cry_decay_radius` | Description |
| --- | --- | --- |
| C0 | 0.0 | Disabled — no cry-based patch learning |
| C1 | 3.0 | Short range cry |
| C2 | 6.0 | Medium range cry |
| C3 | 10.0 | Long range cry |

#### Temperature Axis (food=F0, cry=C0)

| Level | `temperature_sensitivity` | Description |
| --- | --- | --- |
| T0 | 0.0 | Disabled — no temperature effect |
| T1 | 0.1 | Mild temperature sensitivity |
| T2 | 0.3 | Moderate temperature sensitivity |
| T3 | 0.5 | Strong temperature sensitivity |

**Total runs:** 3 axes × 4 levels × 5 seeds = 60 seed runs (≈ 1–2 hours at 6 workers).

### Metrics (per level per axis)

| Metric | Formula | Purpose |
| --- | --- | --- |
| **SVR** — Seed Viability Rate | fraction of seeds with `n_mothers > 3` at T_end | Filter: must be ≥ 0.60 to be considered |
| **CMR** — Child Maturation Rate | mean `matured_children / total_children` across seeds | Primary: higher = more care |
| **PSC** — Population Stability Coefficient | `std(n_mothers, ticks 2000–T_end) / mean` | Stability: must be < 0.50 |
| **mean_care_freq** | mean fraction of time-steps in CARE action | Supporting signal |

### Lock Rule

For each axis independently, select the level with the highest CMR and mean_care_freq
among levels where SVR ≥ 0.60 and PSC < 0.50.

If all viable levels produce CMR ≈ 0 on an axis, the mechanism is neutral — keep it disabled (Level 0).

**Locked output:** `outputs/phase4c_mechanism_screen/<exp>/best_mechanism_settings.json`

```json
{
  "food_entropy_alpha": <F-level value>,
  "cry_decay_radius": <C-level value>,
  "temperature_sensitivity": <T-level value>
}
```

These three values define the **BEST_MECHANISM_SETTINGS** used by `Phase5ConfigFactory` in Block 2.

### Heatmap

One summary figure per axis: SVR / CMR / PSC across levels, passing levels marked ★.
Output: `outputs/phase4c_mechanism_screen/<exp>/mechanism_screen.png`

---

## Block 2 — Baldwin Emergence

### Design

| Parameter | Value |
| --- | --- |
| Starting genome | `care = forage = self = 1/3` — normalized sum = 1, neutral, no pre-baked bias |
| Genome mutation | After every mutation: renormalize by sum → weights always sum to 1.0 |
| Ecology | Phase 4b BEST_CALIBRATED (`selected_ecology.json`) |
| Mechanisms | Phase 4c BEST_MECHANISM_SETTINGS (loaded from `best_mechanism_settings.json`) |
| Evolution | mutation ON, reproduction ON |
| Plasticity (primary) | OFF |
| Plasticity (control) | ON — for Baldwin comparison |
| Run length | 40 000 ticks ≈ 100 generations |
| Control seeds | 30 |
| Sweep seeds | 3 |

**Why 1/3 each?** Genome is normalized to sum=1, so 1/3 each = equal budget shares = perfectly neutral start.
This keeps the world-builder claim clean: no pre-baked caregiving bias is injected into the starting population.

**Why Phase 4c mechanisms?** Phases 1–4 used disabled mechanisms to isolate ecological and strategy effects.
Phase 4c identifies which mechanisms matter. Block 2 runs in the most ecologically realistic world we
can justify — the world where Phase 4c showed mechanisms produce viable, care-inducing populations.

### Interpretive stance

- We are **not** hand-constructing an optimal caregiver.
- We are **not** hardcoding altruism into the action policy.
- The mother is implicitly selfish at the lineage level: preserve her genes as long as possible.
- Under ecological pressure, that selfish lineage logic may still produce **kin-directed altruistic-looking behavior** toward her own child.

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

1. Any heritable shift (including but not limited to `genome.care_weight`) is evidence about the substrate carrying the behavior.
2. If `mean genome care share` rises above the neutral baseline, that is a useful supporting signal — but it is **not the sole definition of success**.

### Metrics

#### A. Exploratory snapshot metrics (tick-based, survivor-biased; dashboard only)

| Metric | Description |
| --- | --- |
| `mean_genome_care_weight` | Mean genome care among currently alive mothers |
| `mean_expressed_care_weight` | Mean expressed care among currently alive mothers |
| `innateness_index` | `1 - mean(plasticity_coefficient)` among currently alive mothers |
| `genome_behavior_distance` | mean total-variation distance between expressed and genome motivation vectors |
| `c_matr_cum` | Current cumulative child maturation proxy from living mothers only |
| `n_alive_mothers`, `n_alive_children` | Population state |
| `mean_mother_energy`, `mean_child_energy` | Tick-level energy state |
| `mean_generation`, `highest_generation` | Async generation clock |

#### B. Inferential lifecycle / cohort metrics (Phase 5 statistical analysis)

| Metric | Definition |
| --- | --- |
| `reproductive_success_s,g` | matured offspring of cohort `g` in seed `s` / mothers in cohort `g` |
| `maturation_fraction_s,g` | matured offspring of cohort `g` in seed `s` / total children born to cohort `g` |
| `plasticity_drift_s,g` | mean total-variation distance between final expressed and genome motivation vectors for cohort `g` mothers |
| `learning_cost_s,g` | mean lifetime plasticity cost for cohort `g` mothers (update cost + maintenance cost) |
| `child_nRMST_s,g` | normalized restricted mean survival time for children in cohort `g`, horizon = `maturity_age` |
| `mother_nRMST_s,g` | normalized restricted mean survival time for mothers in cohort `g` |
| `genome_care_s,g` | optional supporting metric: mean `genome.care_weight` of mothers in cohort `g` |

---

## Block 3 — Eco Pressure Analysis (Optional)

Phase 4c already performs mechanism OVAT with fixed genomes before evolution. Block 3
asks whether the same mechanism axes have a different effect on an *evolved* genome —
i.e., does the evolved strategy show ecological specialization?

This block is **optional**. Run it only if Block 2 produces a clear evolved genome signal.

### Block 3 Design

| Parameter | Value |
| --- | --- |
| Starting genome | Best-emerged weights from Block 2 `mut_on_plast_off` endpoint |
| Mode | Fixed genome — `mutation_enabled=False` |
| Run length | 5 000–10 000 ticks |
| Seeds | 5 per condition |

**Eco pressure axes (OVAT from BEST_MECHANISM_SETTINGS baseline):**

| Mechanism | Config param | Baseline | Low | High |
| --- | --- | --- | --- | --- |
| Shannon food | `food_entropy_alpha` | Phase 4c locked value | F0 (0.00) | F3 (0.10) |
| Cry signal | `cry_decay_radius` | Phase 4c locked value | C0 (0.0) | C3 (10.0) |
| Temperature | `temperature_sensitivity` | Phase 4c locked value | T0 (0.0) | T3 (0.5) |

**Interpretation question:** Does the evolved genome perform better under the same
mechanisms it was selected in? Does it break under different mechanisms?

---

## Statistical Validation Metrics

Nine metrics total — one test per metric, no hierarchical models.

### Block 1 (ecological calibration)

| # | Metric | Formula | Test | Pass condition |
| --- | --- | --- | --- | --- |
| B1.1 | **EVR** — Ecology Viability Rate | fraction of seeds with `n_mothers > 0` at T_end | Bootstrap 95% CI per condition | CI excludes 0 for BALANCED and EASY |
| B1.2 | **CMR** — Child Maturation Rate | `Σ matured_children / Σ total_children` per seed, then mean | Bootstrap 95% CI | CMR > 0 (CI excludes 0) |
| B1.3 | **Condition ordering** | mean extinction tick per seed | Kruskal-Wallis; pairwise Mann-Whitney U | Ordered: HARSH < BALANCED < EASY |

### Phase 4c (mechanism screen, per axis per level)

| Metric | Formula | Threshold |
| --- | --- | --- |
| **SVR** | fraction of seeds with `n_mothers > 3` at T_end | ≥ 0.60 (gate condition) |
| **CMR** | mean `matured_children / total_children` across seeds | Maximize (primary selection criterion) |
| **PSC** | `std(n_mothers, ticks 2000–T_end) / mean` | < 0.50 (stability gate) |

Lock rule: highest CMR among levels where SVR ≥ 0.60 and PSC < 0.50.

### Block 2 (Baldwin emergence — inferential)

| # | Metric | Formula | Test | H₀ | Expected |
| --- | --- | --- | --- | --- | --- |
| B2.1 | **Baldwin Signal** | mean `genome_care_weight` at final cohort generation, per seed | One-sample Wilcoxon signed-rank vs 1/3 | median = 1/3 | Reject in `mut_on_plast_off`; **fail** to reject in `mut_off_plast_off` (null control) |
| B2.2 | **Scaffold Effect** | mean `maturation_fraction` over first 20 generations, per seed | Mann-Whitney U: `plast_on` vs `plast_off` | Equal AUC | `plast_on` > `plast_off` |
| B2.3 | **Assimilation** | Spearman ρ between `genome_behavior_distance` and generation, per seed | One-sample t-test on 30 ρ values vs 0 | mean ρ = 0 | mean ρ < 0 (distance decreasing) |

---

## File Organization

```text
agents/
    mother.py                  (shared — Phase 1–5; Phase 5 methods added in-place)
    child.py                   (shared — all phases)

evolution/
    genome.py                  Genome dataclass; _mutate_gene + _renormalize @staticmethods

experiments/
    phase1_mechanics_tests/    Phase 1 unit tests
    phase2_survival_minimal/   Phase 2 mother-only eco baselines
    phase3_survival_full/      Phase 3 children + care trap
    phase4c_mechanism_screen/  Phase 4c mechanism OVAT (to be implemented)
        __init__.py
        run.py                 MechanismScreenRunner — OVAT across food/cry/temperature
        plot.py                Heatmap per axis (SVR, CMR, PSC)
    phase5_evolution/          Block 2 — implemented
        __init__.py
        config.py              Phase5ConfigFactory — loads Phase 4b JSON + Phase 4c JSON
        run.py                 RunParams + EvolutionRunner
        plot.py                EvolutionPlotter — CSV-only

outputs/
    phase4_weight_sweep/
        phase4b_20260510_111325/
            selected_ecology.json   (BEST_CALIBRATED — loaded by Phase5ConfigFactory)
    phase4c_mechanism_screen/
        <exp>/
            mechanism_screen.csv    (per-level per-axis metrics)
            mechanism_screen.png    (3-axis heatmap)
            best_mechanism_settings.json   (BEST_MECHANISM_SETTINGS — loaded by Phase5ConfigFactory)
    phase5_evolution/
        exp_<timestamp>/
            snapshots.csv
            summary.json
            mother_lifecycle.csv
            child_lifecycle.csv
            cohort_plots/
```

---

## Commands

**Phase 4c — Food mechanism OVAT (5 seeds × 10k ticks, 4 food levels):**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase4c_mechanism_screen.run --axis food --workers 6
```

**Phase 4c — Cry mechanism OVAT:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase4c_mechanism_screen.run --axis cry --workers 6
```

**Phase 4c — Temperature mechanism OVAT:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase4c_mechanism_screen.run --axis temperature --workers 6
```

**Phase 4c — All axes (sequential, auto-lock best settings):**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase4c_mechanism_screen.run --axis all --workers 6
```

**Phase 4c — Plot heatmaps from existing output:**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase4c_mechanism_screen.plot --input-dir outputs/phase4c_mechanism_screen/exp_<timestamp>
```

**Block 2 pilot (1 seed, 1k ticks, smoke test):**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 1 --max-ticks 1000 --workers 1
```

**Block 2 full — mut ON / plast OFF (primary result):**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 30 --max-ticks 40000 --plasticity-enabled false --workers 6
```

**Block 2 full — mut ON / plast ON (Baldwin comparison):**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 30 --max-ticks 40000 --plasticity-enabled true --workers 6
```

**Block 2 full — mut OFF / plast OFF (null baseline):**
```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.run --seeds 30 --max-ticks 40000 --mutation-enabled false --plasticity-enabled false --workers 6
```

**Block 2 exploratory plots (from existing output):**

```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase5_evolution.plot --input-dir outputs/phase5_evolution/exp_<timestamp>
```

---

## Progress Tracker

### Status: Block 1 — World Setup

- [x] Phase 1 mechanics validated — tau, sigma, base mutation_rate locked
- [x] Phase 2 ecological baselines — HARSH / BALANCED / EASY locked
- [x] Phase 3 null result — C_matr = 0 (care trap confirmed)
- [x] Phase 3b deprecated — care trap mechanism explained, BEST_ECOLOGICAL locked
- [x] Phase 4 weight sweep — BEST_CALIBRATED locked (init_food=600, eat_gain=0.70, ISM=1.0)
- [ ] Phase 4c — BEST_MECHANISM_SETTINGS locked (food / cry / temperature OVAT)

### Status: Block 2 — Baldwin Emergence

- [x] `experiments/phase5_evolution/__init__.py` — module marker
- [x] `experiments/phase5_evolution/config.py` — `Phase5ConfigFactory` (loads Phase 4b JSON)
- [x] `experiments/phase5_evolution/run.py` — `RunParams` + `EvolutionRunner` (OOP, parallel)
- [x] `experiments/phase5_evolution/plot.py` — exploratory snapshot dashboard
- [x] `evolution/genome.py` — `_mutate_gene`, `_renormalize`; `lock_learning_rate`
- [x] `agents/mother.py` — guard clauses + Phase 5 methods
- [x] Lifecycle log export (`mother_lifecycle.csv`, `child_lifecycle.csv`)
- [x] Cohort statistical plotter (44 primary plots; +11 optional support plots)
- [ ] `Phase5ConfigFactory` updated to load `best_mechanism_settings.json`
- [ ] Smoke test (1 seed, 500 ticks): no crash, `snapshots.csv` generated
- [ ] Pilot run (5 seeds, 5k ticks): no extinction, plots render
- [ ] Control matrix 4-condition × 30-seed run (40k ticks each)
- [ ] Emergence / assimilation criterion confirmed or refuted

### Status: Block 3 — Eco Pressure (Optional, post-Block 2)

- [ ] Block 2 produces clear evolved genome (prerequisite)
- [ ] OVAT on evolved genome across Phase 4c mechanism axes
- [ ] Pressure interpretation written

### Paper

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
| `outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json` | BEST_CALIBRATED — loaded by Phase5ConfigFactory |
| `outputs/phase4c_mechanism_screen/<exp>/best_mechanism_settings.json` | BEST_MECHANISM_SETTINGS — loaded by Phase5ConfigFactory after Phase 4c |
