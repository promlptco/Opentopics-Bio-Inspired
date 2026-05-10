# Research Progress Timeline

> ⚠ **COLLABORATOR NOTE: IF YOU DON'T KNOW, JUST ASK — NO GUESSING.**
> Do not fill in unknown values, infer undocumented behavior, or assume parameter names.
> Read the actual source files before writing anything.

Branch: V3 | Deadline: 2026-05-17

Chronological record of every phase — what was done, what was found, and what it implies.
For technical parameters and code details see [CURRENT_STATE.md](./CURRENT_STATE.md).
For the full research plan see [ROADMAP.md](./ROADMAP.md).

---

## ▶ NEXT SESSION TASK LIST (read this first)

Calibration is now **integrated into Phase 2 and Phase 3 sweeps** — no separate diagnostic runs needed.

### Step 1 — Extend Phase 2 sweep code to 4 parameters

Add `food_entropy_alpha` as Set D to `experiments/phase2_survival_minimal/new_config.py` sweep grid.
Phase 2 now sweeps: `init_food × food_entropy_alpha × move_cost × eat_gain`.

```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase2_survival_minimal.new_run --mode pipeline --workers 4
```

Best result from Phase 2 = provisional ecology baseline (including `food_entropy_alpha` value).

### Step 2 — Extend Phase 3 sweep code to 6 parameters

Add `food_entropy_alpha`, `temperature_sensitivity`, `cry_decay_radius` as Sets D/E/F to `experiments/phase3_survival_full/config.py`.
Phase 3 now sweeps: `init_food × food_entropy_alpha × move_cost × eat_gain × temperature_sensitivity × cry_decay_radius`.

```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase3_survival_full.run --mode pipeline --workers 4
```

Best result from Phase 3 = BEST_ECOLOGICAL (locked for Block 2).

### Step 3 — Re-run Phase 4 with locked BEST_ECOLOGICAL

```powershell
$env:MPLBACKEND='Agg'; python -m experiments.phase4_weight_sweep.run --mode sweep --workers 4
```

### Step 4 — Build Block 2

Write `experiments/phase5_evolution/config.py`, `run.py`, `plot.py` per ROADMAP.md spec.
Starting genome: care = forage = self = 1/3 (normalized sum = 1).
Genome renormalization after every mutation is mandatory (see design decision below).

---

## ⚠️ DESIGN DECISION — Locked 2026-05-08

**Mechanism consistency principle:** All three ecological mechanisms (Shannon entropy food, cry attenuation, temperature cycle) must be active with **the same fixed baseline values across every phase — Block 1 through Block 3**. Only the mechanism parameter values change between experiments (Block 3 eco-pressure analysis). This ensures all blocks are directly comparable and eco-pressure effects are cleanly isolated.

**Consequence: Phase 1–4 must be re-run** with the baseline mechanism values before Block 2 begins.

**Baseline values — TO BE CALIBRATED before re-run:**

| Mechanism | Config param | Baseline value | Notes |
| --- | --- | --- | --- |
| Shannon entropy food | `food_entropy_alpha` | TBD — locked by Phase 2 sweep | Mild spatial heterogeneity |
| Cry attenuation | `cry_decay_radius` | TBD — locked by Phase 3 sweep | Moderate distance decay |
| Temperature cycle | `temperature_sensitivity` | TBD — locked by Phase 3 sweep | Children only; cold/warm asymmetric |

**Block 3 eco-pressure analysis** = vary these three values (one at a time or jointly) on top of the evolved Block 2 genome to measure care behavior response.

**Genome normalization principle (locked):** After every mutation in Block 2/3, genome weights are renormalized by their sum so they always sum to 1.0. `genome.care_weight` IS the effective care share directly.

---

## Block 1 — World Setup 🔁 NEEDS RE-RUN

Goal: validate simulation mechanics, calibrate ecology, identify the structural bottleneck that prevents care from emerging under neutral motivation weights.

**Re-run required:** Block 1 phases were run without the three mechanisms active. Must be re-run once baseline mechanism values are calibrated.

---

### Phase 1 — Mechanics Validation ✅

**When:** pre-V3

**What:** Six deterministic unit tests covering mutation, inheritance, reproduction, population stability, stochasticity identity, and softmax calibration.

**Finding:** 7/7 tests pass. Core engine is correct and reproducible.

**Implication:** All downstream results can be attributed to ecological and motivational dynamics, not simulation bugs.

---

### Phase 2 — Ecological Survival Baseline ✅

**When:** V3 (locked 2026-05-05)

**What:** Mother-only simulation (no children, no care, no reproduction). Swept `init_food × eat_gain × move_cost` to find three ecological regimes.

**Finding:** Three canonical ecologies locked:

| Condition | Survival | move_cost | eat_gain | init_food |
|-----------|----------|-----------|----------|-----------|
| HARSH     | 24.7%    | 0.05      | 0.80     | 80        |
| BALANCED  | 62.4%    | 0.01      | 0.50     | 40        |
| EASY      | 91.6%    | 0.005     | 0.50     | 80        |

**Implication:** HARSH drives survival through movement exhaustion (fatigue cascade). BALANCED drives FAILED_FORAGE events forcing motivational switching. EASY allows near-full survival with stable energy. These three baselines are the ecological entry points for Blocks 2 and 3.

**Technical detail:** [Phase 2 Current State](./CURRENT_STATE.md#phase-2-current-state)

---

### Phase 3 — Children Added, Food Density Sweep ✅ CONCLUDED (null)

**When:** V3

**What:** Added 15 children (ISM=2.33) alongside 15 mothers. Swept `init_food` (40–1500) with all motivation weights equal (1/1/1). Measured child maturation rate C_matr.

**Finding:** C_matr = 0.000 across all init_food values × 10 seeds. Food density alone cannot produce child maturation.

**Implication:** The bottleneck is not food availability — it is the timing of when CARE fires relative to the FORAGE→PICK→DELIVER sequence.

**Technical detail:** [Phase 3 Current State](./CURRENT_STATE.md#phase-3-current-state)

---

### Phase 3b — Ecological Calibration + Care Trap Confirmed ✅ CONCLUDED (null)

**When:** V3

**What:** Full 3D grid sweep: ISM × eat_gain × init_food (64 combos × 5 seeds = 320 runs), all motivation weights equal. Measured C_matr across all combinations.

**Finding:** C_matr = 0.000 across all 320 runs. CHILD_SURVIVAL_POSSIBLE = False under equal weights at any ecological setting.

**The care trap mechanism:**
With tau=0.1 and equal weights, forage_cue ≈ 0.86 at typical food densities. CARE only beats FORAGE in softmax when child distress > 0.86 — meaning the child has ~4 ticks left before starvation. By that point the mother arrives empty-handed (no prior FORAGE), the feed fails, and the loop repeats. Even at the most favourable ecology (ISM=1.2, eat_gain=0.70, init_food=600), observed feeds/child ≈ 1.9 vs 8.4 needed.

**Locked output:** `BEST_ECOLOGICAL` (ISM=1.2, eat_gain=0.70, init_food=600, move_cost=0.005) — the ecology under which child maturation is most feasible, used as the fixed baseline for all later phases.

**Implication:** Ecological tuning is exhausted. The care trap is a structural consequence of softmax + cue dynamics with equal weights. Motivational bias is the necessary change.

**Technical detail:** [Phase 3b Current State](./CURRENT_STATE.md#phase-3b-current-state)

---

### Phase 4 — Motivation Weight Sweep ✅ CONCLUDED (viable)

**When:** V3 (2026-05-07–08)

**What:** Swept care_weight × forage_weight (raw inputs ∈ {0.1, 0.5, 1.0, 1.5, 2.0}, self_weight = 1.0 fixed) over BEST_ECOLOGICAL ecology. 25 combos × 5 seeds = 125 runs. Applied two structural fixes discovered during initial null sweep.

**Two structural fixes required:**

| Fix | Problem | Solution | Biological basis |
| --- | --- | --- | --- |
| Approach A | All 15 mothers converged on 2–3 most-distressed strangers (allomothering pool) | Own-child exclusivity via `own_child_id` | Oxytocin-driven maternal imprinting at birth |
| Approach E | High care_weight caused mothers to starve (delivered all food, never ate) | Starvation floor `care_energy_floor=0.3` | Corticosterone foraging override under extreme hunger |

**Finding:** Child maturation is mechanically viable across a range of weight settings. Canonical output: `outputs/phase4_weight_sweep/sweep_20260508_194211/`.

| Label | care_weight | forage_weight | self_weight | C_matr |
|-------|------------|---------------|-------------|--------|
| VIABLE_MIN | 0.1 | 1.5 | 1.0 | 0.173 |
| OPTIMAL | 0.5 | 2.0 | 1.0 | 0.360 |

**Normalization note:** `compute_motivation_scores()` divides each weight by Σw before multiplying by cue, so only ratios determine behavior. Effective care share at OPTIMAL = 0.5 / (0.5+2.0+1.0) = **14%** of motivation budget.

**Implication:** Neither fix requires evolution or plasticity — they are fixed behavioral rules. Block 2 starts with a simulation that can physically produce child maturation. The Block 2 question is whether ecological pressure causes care share to rise from the neutral 1/3 baseline through genetic selection.

**Technical detail:** [Phase 4 Current State](./CURRENT_STATE.md#phase-4-current-state)

---

### Block 1 Conclusion

The care trap (Phase 3b) and its resolution (Phase 4) together define the research question for Block 2:

> Under what mutation and plasticity conditions does ecological pressure cause `care_share` to rise above the neutral 1/3 baseline, without any pre-baked motivational advantage?

---

## Block 2 — Baldwin Emergence 🔲 TO BUILD

**Starting conditions:**
- Genome: `care = forage = self = 1/3` (normalized to sum = 1.0 at initialization and after every mutation)
- Effective shares at start: care = forage = self = 33.3% — no motivational advantage
- Ecology: Phase 4b BEST_CALIBRATED (`outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json`)
- Evolution: mutation ON, reproduction ON
- Run length: ~40 000 ticks ≈ 100 async generations

**Genome design (canonical):** Each weight stored independently in [0, 1]. After every mutation, weights are renormalized by their sum so they always sum to 1.0. This means:
- Only relative allocation evolves — no softmax temperature confound
- `genome.care_weight` IS the effective care share directly — no conversion needed
- Success criterion is unambiguous: `mean_genome_care_weight > 1/3`

**Four-condition control matrix:**

| Condition | Mutation | Plasticity | Purpose |
|-----------|---------|------------|---------|
| `mut_on_plast_off` | ON | OFF | Genetic selection only — **primary result** |
| `mut_on_plast_on`  | ON | ON  | Baldwin scaffold + genetic evolution |
| `mut_off_plast_on` | OFF | ON  | Phenotypic adjustment only, no selection |
| `mut_off_plast_off`| OFF | OFF | Fixed genome — null baseline |

**Success criterion:** `mean_genome_care_weight` rises above 1/3 in `mut_on_plast_off`. `mut_off_plast_off` stays flat at 1/3 (confirms it's selection, not drift).

**Code location:** `experiments/phase5_evolution/` (not yet written — see [ROADMAP.md](./ROADMAP.md))

---

### Locked Design Decisions (2026-05-10)

**Metabolic cost model — two aspects:**

```
C_total = C_body + C_brain

C_body  = hunger_rate × T_sequence + move_cost × (d_forage + d_deliver) + feed_cost
C_brain = plasticity_alpha × |Δweights| + plasticity_beta × plasticity_coefficient
```

`hunger_rate × T_sequence` dominates C_body (≈82% per feeding event). `feed_cost=0.03` is 7%.
`C_brain` is the Baldwin assimilation driver — innate mothers pay C_body only; learning mothers pay both.

**Architecture decisions:**

| Decision | Choice | Reason |
| -------- | ------ | ------ |
| Config separation | `EvoConfig` composes `Config` (not inherits) | Root `config.py` frozen; Phase 1–4 unaffected |
| Agent separation | `Phase5MotherAgent(MotherAgent)` subclass in `agents/phase5_mother.py` | Phase 1–4 MotherAgent untouched; future phases subclass further |
| Step signature | `step(self, context: StepContext)` typed bundle | Extensible without breaking call sites; `dt=1.0` default for continuous time |
| Population culling | Weakest-by-energy | Deterministic selection; no random noise masking Baldwin signal |
| Unmentioned genes | Fixed at defaults; tracked in snapshots only | Zero confound on selection; full diagnostic visibility |

**Missing Block 1 sweep variables (Block 3 sensitivity targets):**

`feed_cost=0.03`, `reproduction_threshold=0.85`, `reproduction_cost=0.35`, `mother_max_age=400` — never swept. Uncontrolled in Phase 5 but valid Block 3 targets. Not blockers: Phase 4b validated the system at these values.

---

## Block 3 — Eco Pressure Analysis 🔲 TO BUILD

**Starting conditions:** evolved genome from Block 2 `mut_on_plast_off` endpoint + same baseline mechanism values used in Block 1/2.

**What:** Vary the three mechanism parameter values (one at a time, OVAT-style) on top of the evolved genome and measure whether evolved care behavior is maintained, amplified, or suppressed.

| Axis | Low | Baseline | High |
| --- | --- | --- | --- |
| `food_entropy_alpha` | 0.0 (uniform) | TBD — locked by Phase 2 sweep | TBD (high spatial heterogeneity) |
| `cry_decay_radius` | 0.0 (perfect signal) | TBD — locked by Phase 3 sweep | TBD (strong attenuation) |
| `temperature_sensitivity` | 0.0 (no drain) | TBD — locked by Phase 3 sweep | TBD (strong thermal pressure; children only) |

**Code location:** `--mode pressure` flag on Block 2 runner (not yet written)

---

## World Mechanisms ✅ IMPLEMENTED (active from Block 1 onwards)

**When:** 2026-05-08

Three mechanisms implemented in `simulation/simulation.py` and `config.py`. Active in **every** block at the same baseline values — only Block 3 varies them for eco-pressure analysis.

| Mechanism | Config param | Description |
| --- | --- | --- |
| Shannon entropy food | `food_entropy_alpha` | Spatially heterogeneous food patches with depletion and recovery |
| Cry signal attenuation | `cry_decay_radius` | Distance-decayed child distress signal heard by mother |
| Temperature cycle | `temperature_sensitivity` | Asymmetric cold/warm sinusoidal effect — **children only** (renamed from `warm_sensitivity` 2026-05-09) |

**Baseline values:** TBD — must be calibrated before Phase 1 re-run.

**Technical detail:** [World Mechanism Updates](./CURRENT_STATE.md#world-mechanism-updates-block-2-preparation)
