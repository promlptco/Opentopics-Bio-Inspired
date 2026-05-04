# CURRENT_STATE.md — Project Checkpoint

## Approved Roadmap

`ROADMAP.md` is the project constitution. All phases follow its methodology rules.

`PHASE_TEMPLATE.md` contains the reusable workflow rules, output format, scientific rules, required outputs, and report section format that apply to every future phase. Reference it when writing new phase prompts.

---

## Completed

### Phase 1 — Mechanics Tests
- 7/7 tests pass (including `test_07_engine_fixes.py`)
- Command: `python experiments/phase1_mechanics_tests/run.py`

### Phase 0 — Blocking Engine Fixes
Four bugs fixed (R01/R02/R04/R05). Full details in `REPORT.md → Phase 0`.

### Phase 3 — Child Dependency Control
**Status: COMPLETE — PASS**

- Command: `python experiments/phase3_survival_full/child_dependency_sweep.py --duration 1000 --seeds 30`
- Output: `outputs/phase3_survival_full/20260503_003412/`
- Result: sharp cliff at multiplier=1.25 (theoretical); ×1.0 = 100% child survival (problem), ×1.5 = 0% child survival (selected)
- Selected: `infant_starvation_multiplier = 1.5` (effective child hunger rate = 0.0120/tick)
- Care events: 0 (valid no-care control)
- Full results in `REPORT.md → Phase 3`

---

### Phase 4 — Care Rescue and Minimum Care Threshold

**Status: COMPLETE — FAIL (dual threshold not met; care rescue confirmed)**

- Command: `python experiments/phase3_survival_full/care_rescue_sweep.py --duration 1000 --seeds 30 --child_hunger_rate 0.0120`
- Output: `outputs/phase4_care_rescue/20260503_095550/`
- Result: 0/54 conditions passed both thresholds. Child rescue confirmed (0%→98.3%). Mother survival collapsed in all conditions (max 34.2%) due to food-economy depletion at 1000 ticks without reproduction.
- Minimum care_weight for child ≥ 80%: **cw=0.3** (fw=0.7, sw=0.3 → child=86.4%, mother=34.2%)
- Root cause of FAIL: food grid cannot sustain 12 mothers × 1000 ticks without reproduction, not a failure of the care mechanism.
- Full results in `REPORT.md → Phase 4`

---

### Phase 4b — Care Rescue Short-Horizon Validation (300 ticks)

**Status: COMPLETE — FAIL on dual threshold / PASS on scientific question**

- Command: `python experiments/phase3_survival_full/care_rescue_sweep.py --duration 300 --seeds 30 --child_hunger_rate 0.0120 --out_label phase4b_care_rescue`
- Output: `outputs/phase4b_care_rescue/20260503_110656/`
- Result: 0/54 conditions passed both thresholds. Maximum mother survival = 65% (cw=0.5, fw=0.85, sw=0.3) — improvement from Phase 4's 34%, but 80% threshold structurally unreachable without reproduction.
- Protocol artifact confirmed: no-care mothers survive 15–25% at 300 ticks vs 0% at 1000 ticks.
- Care rescue confirmed: child survival 0% (cw=0) → 98.3% (cw=0.7), identical to Phase 4.
- **Canonical genome (minimum cw for child ≥ 80%):** `care_weight=0.3, forage_weight=0.70, self_weight=0.30` → child=86.4%, mother=61.4%, feed=0.164/tick
- Full results in `REPORT.md → Phase 4b`

---

### Phase 5a — Reproduction-Enabled Ecology Check

**Status: COMPLETE — FAIL on extinction criterion / PASS on scientific question**

- Command: `python experiments/phase5a_ecology_check/run.py --duration 3000 --seeds 30`
- Output: `outputs/phase5a_ecology_check/20260503_142126/`
- Result: All 3 conditions extinct by tick 3000. Care dramatically improves ecology vs no-care.
- Key numbers:
  - no_care: child_surv=0%, births=9.5, max_gen=1, gen2+=0/30
  - canonical (cw=0.3): child_surv=82.2%, births=69.6, max_gen=8.8, gen2+=30/30, feed=0.083/tick
  - high_care (cw=0.5): child_surv=92.8%, births=79.0, max_gen=10.0, gen2+=30/30, feed=0.116/tick
- Root cause of FAIL: food economy bottleneck (init_food=45, slow replenishment) cannot sustain population growth under reproduction=ON, mutation=OFF. Same structural limitation as Phase 4/4b.
- Care mechanism confirmed viable: 82-93% child survival, 8-10 mean generations, realized FEED_CHILD events, 30/30 seeds reach gen2 in both care conditions.
- Full results in `REPORT.md → Phase 5a`

---

### Phase 5b — Food Ecology Calibration

**Status: COMPLETE — FAIL on viability criterion / PASS on scientific question**

- Command: `python experiments/phase5b_food_ecology/run.py --duration 3000 --seeds 30`
- Output: `outputs/phase5b_food_ecology/20260503_152343/`
- Sweep: init_food=[45,60,80,100] × replenish=[5,10,15] × 3 conditions × 30 seeds = 1080 runs
- Result: ALL 12 ecologies result in canonical extinction_rate ≥ 0.97 by tick 3000.
- Best ecology (fallback selection): `init_food=45, replenish=10` (canonical ext=0.967, max_gen=10.1, gen2+=30/30)
- Care contrast confirmed: no_care ext=1.0 gen=1.0 vs canonical ext=0.97 gen=10.1 (care benefit unambiguous)
- Root cause: burst-replenishment mechanism (add R units when food < init_food×0.5) cannot offset consumption from populations of 30–100 agents; boom-bust Malthusian trap
- Larger init_food (80, 100) does not help — enables larger population peaks that collapse harder
- New config parameters added: `food_replenish_amount` (default 5) and `food_replenish_threshold_ratio` (default 0.5) — prior phase behavior unchanged
- Full results in `REPORT.md → Phase 5b`

---

### Phase 5c — Extended Food Replenishment Sweep

**Status: COMPLETE — FAIL on viability criterion / PASS on scientific question**

- Command: `python experiments/phase5c_food_ecology/run.py --duration 3000 --seeds 30`
- Output: `outputs/phase5c_food_ecology/20260503_190312/`
- Sweep: init_food=[45,60,80] × replenish=[20,30,50] × 3 conditions × 30 seeds = 810 runs
- Result: ALL 9 ecologies: canonical extinction_rate ≥ 0.93 by tick 3000 (none viable)
- Best ecology (fallback selection): `init_food=45, replenish_amount=20` (canonical ext=0.93, max_gen=10.2, gen2+=30/30, crash_tick=940)
- Care contrast confirmed: no_care ext=1.00/gen=1.0/child_surv=0.000 vs canonical ext=0.93/gen=10.2/child_surv=0.831
- Root cause: burst-replenishment is structurally inadequate at any tested R; larger R is non-monotonic and larger init_food is counterproductive (larger peaks → harder crashes)
- Combined Phase 5b+5c: 21 ecologies (R=5–50, F=45–100) all fail — food ecology mechanism must change
- Full results in `REPORT.md → Phase 5c`

---

### Phase 5d — Hybrid Food Replenishment Calibration

**Status: COMPLETE — FAIL on viability criterion / PASS on scientific question**

- Command: `python experiments/phase5d_hybrid_food/run.py --duration 3000 --seeds 30`
- Output: `outputs/phase5d_hybrid_food/20260503_213435/` *(corrected rerun — see correction note below)*
- Sweep: continuous_food_rate=[0.1, 0.2, 0.5, 1.0, 2.0] × 3 conditions × 30 seeds = 450 runs
- Result: ALL 5 ecologies: canonical extinction_rate = 1.00 (none viable)
- Selected (fallback): `cfr_0.10` (canonical ext=1.00, max_gen=7.6, crash_tick=847, boom_crash_rate=0.77)
- Care contrast confirmed: no_care crash_tick=331/gen=1.0 vs canonical crash_tick=847/gen=7.6 vs high_care crash_tick=980/gen=9.3
- Root cause: at peak pop 40–60 agents, consumption (~25 food/tick) overwhelms trickle (0.1–2.0/tick) + burst combined; higher rates produce larger booms then harder crashes (non-monotonic above rate=1.0)
- Food saturation: 0.000–0.191 (all below 0.5 cap — food IS being consumed as fast as produced)
- Combined Phases 5b+5c+5d: 26 ecologies tested across all food-ecology approaches; none viable
- **Code correction:** `run.py` fixed (zero_row food_count=0→NaN, NaN-safe food aggregation, final-pop y-axis fix, 4 sanity assertions per run + aggregate checks). All sanity checks pass. Metrics unchanged.
- Full results in `REPORT.md → Phase 5d` and `REPORT.md → Phase 5d Correction`

---

---

### Phase 5e — Crash Mechanism Diagnosis

**Status: COMPLETE (diagnostic — no pass/fail criterion)**

- Command: `python experiments/phase5e_crash_diagnosis/run.py --duration 3000 --seeds 30`
- Output: `outputs/phase5e_crash_diagnosis/20260504_042835/`
- Runs: 3 conditions × 30 seeds = 90 runs, fixed ecology (cfr_0.10)
- **Dominant mechanism: CHRONIC_ENERGY_DEPLETION**
- **Key finding: food NEVER hits zero in any seed (food_depl_tick = -1 for all 90 runs)** — burst replenishment always maintains food > 0; acute food collapse is NOT the cause
- canonical: peak_pop=48.2 at tick 240; gradual 597-tick decline to extinction at tick 837
- Crash sequence: birth_peak (tick 120) → death_peak (tick 133) → peak_pop (tick 240) → chronic decline → extinction (tick 837)
- Root cause: reproduction_cost=0.35 drains mothers faster than food income can restore energy; at peak_pop of 48 agents competing for ~22.5 food units, energy budget is chronically marginally negative
- Care slows decline: high_care peak_pop=42.7 (lower than canonical 48.2) → less food competition → slower depletion → crash_tick=979 vs 837 (+17% longer). Care acts as density regulator in boom-bust ecology.
- Spatial crowding ruled out: peak occupied_density ≈ 5.3% (48/900 cells) — far below movement-failure threshold
- Full results in `REPORT.md → Phase 5e`

---

### Phase 5f — Reproduction Cost Calibration

**Status: COMPLETE — FAIL on viability / PASS on scientific question**

- Command: `python experiments/phase5f_repro_cost/run.py --duration 3000 --seeds 30`
- Output: `outputs/phase5f_repro_cost/20260504_045028/`
- Sweep: reproduction_cost=[0.35, 0.25, 0.20, 0.15, 0.10] × 3 conditions × 30 seeds = 450 runs
- Result: ALL 5 rc values — canonical extinction_rate = 1.000 (none viable). Fallback selected: `rc=0.10`.
- Key numbers at rc=0.10: no_care crash_t=339, canonical crash_t=977, high_care crash_t=1192; child_surv=0.833/0.919; food_depl_tick=-1 (food never hits 0)
- Root cause: reducing per-birth cost does not relieve peak-population food competition; crash driver is chronic energy depletion at ~50 agents vs ~22 food/tick
- Care contrast robust: no_care crash 339 vs canonical 977 vs high_care 1192 (+188%/+252% over no_care); identical across all rc values
- Combined 5b+5c+5d+5f: 31 parameter conditions (food-ecology + birth-cost tuning) all fail
- Full results in `REPORT.md → Phase 5f`

---

## Next Phase

All food-ecology and birth-cost tuning exhausted (Phases 5b–5f: 31 conditions tested, all fail). Decision: **Accept boom-bust ecology** and proceed to Phase 6. Care contrast is strong (crash x2.9 for canonical, x3.5 for high_care vs no_care). Evolution can act on this difference.

**Phase 6 ecology settings (frozen):** `reproduction_cost=0.10, init_food=45, replenish_amount=20, threshold_ratio=0.5, continuous_food_rate=0.10, continuous_food_max=200, infant_starvation_multiplier=1.5`

---

## Baldwin Effect Analysis (additional requirement — added 2026-05-03)

Script: `experiments/baldwin_analysis/plot_baldwin_effect.py`

This script must be run after Phase 7 (Evolution With Plasticity) completes. It generates:
1. Fitness over time (proxy: rolling child survival rate, window=500 ticks)
2. Phenotypic plasticity over time (proxy: mean expressed_care_weight − genome.care_weight)
3. Combined comparison figure for qualitative Baldwin-effect inspection

**Phase 6/7 logging requirement:** the per-tick log must include these columns:
```
tick, seed, treatment, n_alive_mothers, n_alive_children,
mean_genome_care_weight, mean_expressed_care_weight,
n_births_this_tick, n_child_deaths_hunger_this_tick
```
Save this file as `evolution_tick_log.csv` in the phase output directory.

**Rules:**
- Use real data only. Do not shape results to match the reference pattern.
- Report honestly if the Baldwin pattern is absent or ambiguous.
- Run command: `python experiments/baldwin_analysis/plot_baldwin_effect.py --data <output>/evolution_tick_log.csv --out outputs/baldwin_analysis/`

---

## Standing Rules

1. Implement one phase at a time.
2. Append full results to `REPORT.md` after each phase.
3. Update `CURRENT_STATE.md` after each phase.
4. Stop and wait for approval after each phase.
5. Do not paste long reports in chat — write to `REPORT.md`.
6. Phase 6/7 must produce `evolution_tick_log.csv` (see Baldwin section above).
