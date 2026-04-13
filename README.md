# Simulation of the Minimum Ecological Conditions for the Emergence of Kin-Biased Maternal Care via Evolving Neuroendocrine Agents
## FRA361 Open Topics — FIBO 3rd Year, Semester 2

A tick-based, grid-world agent-based simulation studying the **emergence of maternal care** through evolutionary game theory and Hamilton's rule (rB > C). Agents evolve genome weights governing care, foraging, and self-maintenance behaviour without any hard-coded care targets — prosocial behaviour emerges purely from selection pressure.

---

## Project Overview

The simulation models a 2D grid populated by `MotherAgent` and `ChildAgent` instances. At each tick, each mother selects among three behavioural domains — **care**, **forage**, or **self-maintenance** — via an argmax over genome-weighted utility scores. Reproduction is generational (roulette selection by terminal energy), and mutations accumulate across a genome of three (or four, in Phase 4) continuous parameters.

The pipeline proceeds through five experimental phases:

| Phase | Directory | Purpose |
|-------|-----------|---------|
| P1 | `experiments/p1_mechanics_tests/` | Unit tests for mutation, inheritance, reproduction |
| P2 | `experiments/p2_survival_minimal/` | Minimal survival check |
| P3 | `experiments/p3_survival_full/` | Survival gate — confirm baseline viability |
| P3e | `experiments/p3_care_erosion/` | Evolution baseline (care erosion) + zero-shot measurement |
| P4 | `experiments/p4_plasticity_intro/` | Kin-conditional plasticity / Baldwin Effect |
| P5 | `experiments/p5_enhanced_ecology/` | Ecological emergence — natal philopatry + existential infant dependency |
| P6a | `experiments/p6_controls_and_baldwin/p6a_dispersal_ablation/` | Control — high dispersal (scatter=8) |
| P6b | `experiments/p6_controls_and_baldwin/p6b_spatial_control/` | Control — philopatry only (mult=1.0, scatter=2) |
| P6c | `experiments/p6_controls_and_baldwin/p6c_depleted_baseline/` | Depleted-init zero-shot baseline |
| P6d | `experiments/p6_controls_and_baldwin/p6d_baldwin_instinct/` | Baldwin instinct assimilation |

Publication figures: `experiments/make_publication_figures.py`
Cross-phase thesis plots: `experiments/p4_plasticity_intro/make_thesis_plots.py`

---

## Installation & Setup

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
```

`requirements.txt` includes: `matplotlib`, `numpy`, `scipy`, `pandas`, `seaborn`, `pillow`

No additional installation required. All simulation modules are importable from the project root.

---

## Configuration Guide

All flags are passed as keyword arguments to the `SimConfig` dataclass (`config.py`). The table below covers the core flags used across phases.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `children_enabled` | bool | `True` | Spawn ChildAgents at simulation start |
| `care_enabled` | bool | `True` | Allow mother agents to perform care actions |
| `plasticity_enabled` | bool | `False` | Enable `learning_rate` genome parameter (Phase 4 only) |
| `plasticity_kin_conditional` | bool | `False` | Restrict plasticity updates to own-lineage care events |
| `reproduction_enabled` | bool | `True` | Enable generational reproduction and roulette selection |
| `mutation_enabled` | bool | `True` | Allow genome mutation during reproduction |
| `infant_starvation_multiplier` | float | `1.0` | Multiplier on hunger increment for pre-maturity infants. Set to `1.15` in Phase 5 to create existential infant dependency |
| `birth_scatter_radius` | int | `5` | Radius within which newborns are placed near their mother. `2` = natal philopatry (Phase 5a); `8` = high dispersal (Phase 5b) |
| `init_mothers` | int | `30` | Number of mothers at simulation start |
| `init_food` | int | `50` | Number of food items at simulation start |
| `seed` | int | `42` | Random seed for reproducibility |
| `ticks` | int | `5000` | Total simulation duration in ticks |
| `mutation_rate` | float | `0.05` | Per-parameter mutation probability |
| `mutation_sigma` | float | `0.05` | Gaussian mutation standard deviation |

**Phase-by-phase config summary:**

| Flag | baseline_c0 | baseline_r0 | Phase 04 | zero-shot | Phase 4b | Phase 07 |
|------|-------------|-------------|---------|-----------|----------|----------|
| `reproduction_enabled` | True | True | True | **False** | True | True |
| `mutation_enabled` | **False** | **False** | True | **False** | True | True |
| `plasticity_enabled` | False | False | False | False | **True** | False |
| `infant_starvation_multiplier` | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | **1.15** |
| `birth_scatter_radius` | 5 | 5 | 5 | 5 | 5 | **2** |

---

## Execution Instructions

All commands are run from the **project root** directory.

### P1 — Mechanics Tests

```bash
python experiments/p1_mechanics_tests/test_01_mutation.py
python experiments/p1_mechanics_tests/test_02_inheritance.py
python experiments/p1_mechanics_tests/test_03_reproduction.py
python experiments/p1_mechanics_tests/test_04_population_stability.py
```

Or run all four:

```bash
python experiments/p1_mechanics_tests/run.py
```

### P3 — Survival Gate

```bash
python experiments/p3_survival_full/run.py
```

Expects: 12/12 survival, avg energy > 0.85. Results written to `outputs/phase03_survival_full/`.

### P3e — Zero-Shot Baseline Measurement

```bash
python experiments/p3_care_erosion/measure_baseline.py
```

Transfers evolved genomes from P3e evolution (run evolution first). Outputs care window rate for baseline comparison. Results in `outputs/phase05_zeroshot_standard/`.

### P3e — Evolution Baseline (Care Erosion)

Single seed:
```bash
python experiments/p3_care_erosion/run.py
```

Multi-seed (seeds 42–51, 10 runs):
```bash
python experiments/p3_care_erosion/run_multi_seed.py
```

Watch the simulation live (Baseline-C0 config):
```bash
python experiments/p3_care_erosion/watch.py
```

Outputs: per-seed `generation_snapshots.json`, `top_genomes.json`, CI trajectory plot, hitchhiking check.
Combined: `outputs/phase04_care_erosion/multi_seed_evolution/`

### P4 — Kin-Conditional Plasticity / Baldwin Effect

Single seed:
```bash
python experiments/p4_plasticity_intro/run.py
```

Multi-seed:
```bash
python experiments/p4_plasticity_intro/run_multi_seed.py
```

Cross-phase thesis plots (selection gradient, population trough, zero-shot comparison, phase table):
```bash
python experiments/p4_plasticity_intro/make_thesis_plots.py
```

Output: `outputs/phase06_baldwin_effect/` and `outputs/thesis_plots/`

### P5 — Ecological Emergence (Natal Philopatry)

Single seed:
```bash
python experiments/p5_enhanced_ecology/run.py
```

Multi-seed (seeds 42–51):
```bash
python experiments/p5_enhanced_ecology/run_multi_seed.py
```

Output: `outputs/phase07_ecological_emergence/multi_seed_evolution/`

### P6a — Dispersal Ablation Control

```bash
python experiments/p6_controls_and_baldwin/p6a_dispersal_ablation/run.py
```

Uses `birth_scatter_radius=8`. Compares selection gradient vs P5 (scatter=2).

### Generate All Publication Figures

```bash
python experiments/make_publication_figures.py
```

Produces three publication-ready figures in `outputs/publication_figures/` at 300 DPI:
- `figure1_phase04_care_erosion.png` — Phase 3 CI trajectory + selection gradient scatter
- `figure2_phase06_baldwin_effect.png` — Phase 3 vs 4b trajectory + zero-shot bar chart
- `figure3_phase07_ecological_emergence.png` — Phase 5a/5b CI overlay + per-seed gradient bar chart

---

## Output Directory Structure

```
outputs/
  phase03_survival_full/
  phase05_zeroshot_standard/
    run_YYYYMMDD_HHMMSS_seed42/
      plots/
      care_log.csv
      birth_log.csv
      population_history.json
  phase04_care_erosion/
    run_YYYYMMDD_HHMMSS_seed42/     <- canonical evolution run
    multi_seed_evolution/            <- CI plots, summary.json, run_dirs.json
  phase06_baldwin_effect/
    run_YYYYMMDD_HHMMSS_seed42/
    multi_seed_evolution/
  phase07_ecological_emergence/
    run_YYYYMMDD_HHMMSS_seed42/
    multi_seed_evolution/
  publication_figures/               <- figure1/2/3 PNGs (300 DPI)
  thesis_plots/                      <- 4 cross-phase analysis plots
```

---

## Pathfinding

Five algorithms available in `simulation/pathfinding.py`, all with the same interface:

```python
find_step(from_pos, to_pos, is_free, in_bounds) -> tuple[int, int]
```

| Algorithm | Notes |
|-----------|-------|
| `naive_step` | 3-direction greedy — original, can freeze in crowds |
| `greedy_step` | All 8 neighbours, pick closest |
| `bfs_step` | BFS shortest hops |
| `astar_chebyshev` | A* uniform cost |
| `astar_octile` | A* diagonal = √2 — **currently active** |

To swap: change the import in `simulation/world.py`.

---

## Key Results Summary

| Phase | Key Finding | Primary Statistic |
|-------|-------------|-------------------|
| Phase 3 (Evolution) | Care erodes — selection against care | Pearson's r = −0.178 |
| Phase 4b (Baldwin) | learning_rate swept 8/10 seeds; zero-shot assimilation absent at population level | p = 0.815 |
| Phase 5a (Emergence) | Gradient REVERSED — care builds from depleted baseline (mean start 0.25 → 0.35+) | Pearson's r = +0.079, p = 0.0002, Cohen's d = 1.87 |
| Phase 5b (Control) | Dispersal weakens but does not eliminate positive gradient | r = +0.050 vs +0.079 |
