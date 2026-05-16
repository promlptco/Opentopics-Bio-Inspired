# Food Experiment Summary
**Project**: Opentopics-Bio-Inspired (FRA361)  
**Date**: 2026-05-16  
**Branch**: V3

---

## What We Were Testing

The food model controls how food is distributed across the 50x50 grid. Two mechanisms are interleaved:

1. **Burst replenishment** (Shannon OFF): When a mother eats food, a new food unit spawns randomly elsewhere (1:1 replacement). Food count stays near `init_food`.

2. **Shannon entropy food** (Shannon ON, alpha > 0): Each grid cell has a spawn probability `p`. Each tick, empty cells spawn food with rate `rate = -alpha * p * log(p)`. This peaks at `p = 1/e ~= 0.37` (entropy maximum). When food is eaten, `p` decreases (depletion, beta=0.01). Each tick, all cells pull back toward `food_patch_prior` (recovery, gamma=0.01).

The Shannon mechanism creates **spatial food structure**: heavily-eaten patches recover slowly, pushing food to undervisited areas (dispersal signal).

---

## Phase 2 — Mothers Only, No Children

### What we tested
- Shannon alpha = [0.00, 0.01, 0.05, 0.10] with locked prior=0.12 (old)
- Then: 2D sweep alpha x prior — [0.0,0.05,0.10,0.20,0.50] x [0.12,0.24,0.37,0.50,0.75]
- Finally: diagnostic plots with best prior=0.37

### Key findings
- **All Phase 2 conditions survive 100%** (no children = no care cost drain)
- Shannon alpha has minor effect on final population (~9-13 mothers)
- Higher prior = more food = slightly lower final_pop (density-dependent limits) 
- Prior confounds alpha: old sweep locked prior=0.12 (low density), inflating apparent alpha effect
- **Best config**: prior=0.37 (entropy max), alpha=0.05 (mild spatial structure)

### Conclusion
Phase 2 ecology is robust. Food quantity (prior) matters more than spatial structure (alpha) for pure survival. Shannon adds texture but doesn't change survival at these scales.

---

## Phase 3 — Mothers + Children (Reproduction OFF)

### What we tested
- Shannon alpha = [0.00, 0.01, 0.05, 0.10] with locked prior=0.12 (old)
- 2D sweep alpha x prior (same grid as Phase 2)
- Diagnostic plots with best prior=0.37
- Perception sweep: percept=[8, 15, 25, 50] at alpha=0.10, prior=0.37
- High-alpha sweep: alpha=[0.10, 0.20, 0.50, 1.00] at percept=8, prior=0.37

### Key findings: Alpha x Prior sweep
| alpha | prior | CMR     | Notes |
|-------|-------|---------|-------|
| 0.00  | 0.12  | 0.253   | food-starved, spatial effect absent |
| 0.00  | 0.37  | 0.600   | food quantity effect only |
| 0.05  | 0.12  | 0.960   | alpha kicks in even at low density |
| 0.05  | 0.37  | 0.920   | similar — Shannon structure is primary driver |
| 0.50  | 0.37  | 1.000   | full maturation rate |

**True Shannon structural advantage**: ~0.35 CMR units (not 0.70 as old locked-prior experiment suggested — prior confound inflated the effect size).

### Why Shannon helps CMR
The food dispersal mechanism pushes food regeneration toward under-visited patches. Mothers must move to reach food -> they occasionally move near infants -> care events happen opportunistically -> infants receive more feeding -> CMR rises. The mechanism is indirect: food dispersal -> mother movement -> opportunistic care.

### Spatial clustering problem
- Phase 3 spatial heatmaps show population concentrated in specific corners (especially seed 42-46)
- Root cause: CARE mechanism anchors mother-child pairs to their initial location (warmth + proximity)
- Shannon dispersal (beta=0.01, gamma=0.01, recovery ~10 ticks) is too weak to break this anchor
- All Phase 3 mothers die (final_pop=0) — care cost drain over 2000 ticks is lethal

### Perception sweep results (alpha=0.10, prior=0.37)
| percept | F0 CMR | F3 CMR | Notes |
|---------|--------|--------|-------|
| 8       | 0.600  | 0.973  | baseline |
| 15      | 0.747  | 0.973  | improved null condition |
| 25      | (see plots) | (see plots) | |
| 50      | (see plots) | (see plots) | wider search = better foraging |

**Larger perception = better foraging efficiency** (agents find food faster).
The Shannon advantage (F3-F0 gap) narrows at large perception because even the null condition performs well when agents see far.

### High-alpha sweep results (percept=8, prior=0.37)
| alpha | CMR (mean) | Notes |
|-------|-----------|-------|
| 0.10  | ~0.973    | baseline |
| 0.20  | ~0.980+   | slightly better |
| 0.50  | ~1.000    | strong dispersal |
| 1.00  | ~1.000    | near-perfect but may destabilize low-density patches |

Higher alpha improves CMR but spatial clustering does not change significantly — the CARE anchor is stronger than food dispersal at these beta/gamma values.

---

## The Prior Confound (Critical Methodological Issue)

### What happened
Old experiments locked `food_patch_prior = init_food / (W*H) = 300/2500 = 0.12`.
This is well below the entropy maximum (0.37). When sweeping alpha:
- alpha=0 with prior=0.12: food density target = 0.12 (300 food) 
- alpha=0.10 with prior=0.12: food density target ALSO = 0.12 BUT Shannon adds spatial structure

The experiment was measuring both "spatial structure effect" AND "food quantity was already low, higher alpha helped because it moved food toward agents". Not a clean alpha test.

### The fix
Use `init_food = int(prior * W * H)` so initial food density equals the prior. This way:
- Varying alpha changes spatial structure only (food quantity stays constant)
- prior controls food quantity independently

With this fix:
- **Alpha effect is real but smaller** than old experiments suggested (~0.35 CMR, not ~0.70)
- **Prior effect is also real**: prior=0.37 vs 0.12 gives CMR 0.600 vs 0.253 at alpha=0 (food quantity matters)

---

## Phase 5 Food Settings

### Configuration used in Phase 5 Block 2
```
food_entropy_alpha = 0.01   (mild Shannon, F1 level)
food_entropy_beta  = 0.01   (slow depletion)
food_entropy_gamma = 0.01   (slow recovery)
food_patch_prior   = 0.45   (slightly above entropy max)
```

### Problem identified
Phase 5 init_food=300 (from Phase 4b ecology) but equilibrium target is `0.45 * 2500 = 1125`.
Shannon food takes hundreds of ticks to equilibrate. During this low-food startup period, neutral-care mothers (1/3 each) starve before selection can act.

### Fix applied
`ecology_relaxation_factor = 3.75` => `init_food = 300 * 3.75 = 1125 = food_patch_prior * W * H`
This starts food already at equilibrium density, preventing startup starvation.

### Recommendation for future runs
When using Shannon food mode, always initialize with:
```
init_food = int(food_patch_prior * W * H)
```
This ensures food starts at the Shannon equilibrium density.

---

## Output Locations

| Experiment | Output Directory |
|-----------|-----------------|
| Phase 2 alpha x prior sweep | `outputs/phase2_alpha_prior_sweep/exp_20260516_033400/` |
| Phase 3 alpha x prior sweep | `outputs/phase3_alpha_prior_sweep/exp_20260516_033959/` |
| Phase 2 diagnostic (prior=0.37) | `outputs/phase2_food_shannon_diagnostic/exp_20260516_035024/` |
| Phase 3 diagnostic (prior=0.37) | `outputs/phase3_food_shannon_diagnostic/exp_20260516_035129/` |
| Phase 3 perception sweep | `outputs/phase3_percept_sweep/percept08/, percept15/, percept25/, percept50/` |
| Phase 3 high-alpha sweep | `outputs/phase3_alpha_high_sweep/exp_*/` |

---

## Summary Table

| Question | Answer |
|----------|--------|
| Does Shannon alpha improve CMR? | YES, threshold effect at alpha>=0.05. CMR saturates ~1.0 |
| Is alpha the main driver? | NO — prior (food quantity) also matters significantly |
| What is the true Shannon advantage? | ~0.35 CMR units (alpha=0 prior=0.37 gives 0.60, alpha=0.10 gives 0.97) |
| Does higher perception break clustering? | Partially — better foraging, but CARE anchor persists |
| Does higher alpha break clustering? | No — Shannon dispersal too weak (beta/gamma = 0.01) vs CARE anchor |
| Best config for Phase 3? | alpha=0.10, prior=0.37, perception=8-15 |
| Best config for Phase 5? | alpha=0.01-0.10, food_patch_prior=0.45, init_food=1125 (at equilibrium) |
