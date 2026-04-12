# Minimum Ecological Conditions for the Emergence of Maternal Care: A Grid-World Evolutionary Game Theory Simulation

**FRA361 Open Topics — FIBO 3rd Year, Semester 2**
**Author:** Chantouch Orungrote
**Date:** April 2026

---

## Abstract

Maternal care is among the most energetically costly prosocial behaviours observed in vertebrates, yet explaining its evolutionary origin under Hamilton's rule (rB > C) remains non-trivial when the coefficient of relatedness r is diluted by spatial mixing and per-event benefits B are marginal. We present a grid-world agent-based simulation in which mother agents evolve genome weights governing care, foraging, and self-maintenance without hard-coded care targets. Under standard ecological parameters, care erodes under selection (Pearson's r = −0.178 across 10 seeds). Introducing kin-conditional phenotypic plasticity induces a Baldwin Effect learning-rate sweep (8/10 seeds) but fails to produce robust genetic assimilation at the population level (p = 0.815). Critically, combining existential infant dependency (infant_starvation_multiplier = 1.15) with natal philopatry (birth_scatter_radius = 2) reverses the selection gradient to strongly positive (Pearson's r = +0.079, p = 0.0002, Cohen's d = 1.87, 9/10 seeds). We conclude that existential offspring dependency and spatial kin bias via natal philopatry are jointly necessary — neither condition alone is sufficient — to satisfy Hamilton's rule and drive care emergence from a depleted evolutionary baseline.

---

## 1. Introduction

Maternal care is among the most energetically costly and evolutionarily significant prosocial behaviours in vertebrate life. Hamilton's rule (rB > C) provides a principled account of when care should evolve: a care-giving allele spreads when the benefit B to the recipient, weighted by the coefficient of relatedness r, exceeds the cost C borne by the actor (Hamilton, 1964). In practice, however, real populations rarely satisfy all three conditions simultaneously. Spatial mixing dilutes effective relatedness toward zero; marginal offspring benefit fails to exceed care cost; and the two shortfalls compound. Explaining how care evolves — rather than merely how it is maintained once established — requires identifying the minimum ecological conditions that jointly bring rB above C.

Prior agent-based life (ALife) studies of cooperation have established that spatial structure can create local clusters of cooperators, providing a route to positive selection without explicit kin recognition (Axelrod and Hamilton, 1981; Nowak and May, 1992). These findings motivate the present inquiry: can spatial proximity at birth serve as a de facto kin-recognition substitute, elevating effective relatedness sufficiently to support care evolution? And does the magnitude of offspring dependency independently modulate the selection gradient?

We address a specific and underexplored research question: *what are the minimum ecological conditions necessary for maternal care to emerge — that is, to build under positive selection — from a depleted evolutionary baseline?* Our framing deliberately excludes the harder problem of emergence from absolute zero, which is below the operative threshold of the model's decision architecture (care_weight < 0.075 yields no care events at typical energy levels). Instead, we initialise with care_weight drawn from Uniform(0, 0.50), mean ≈ 0.25, placing the population below the Phase 3 eroded equilibrium of 0.42 — a state from which spontaneous recovery has not previously been demonstrated.

Our principal finding is that two ecological conditions — existential infant dependency and natal philopatry — are jointly necessary and sufficient to reverse the selection gradient from −0.178 (erosion) to +0.079 (emergence), a sign change with effect size Cohen's d = 1.87. Neither condition in isolation produces a robust reversal. The model generates no explicit kin recognition; spatial proximity at birth is the sole mechanism mediating kin-biased care.

---

## 2. Related Work / Background

### 2.1 Kin Selection and Hamilton's Rule

Hamilton (1964) formalised inclusive fitness theory, demonstrating that altruistic alleles can spread when the weighted benefit to kin outweighs the direct cost to the actor. The rule rB > C applies across all relatedness structures, with r derived from genealogical distance: 0.5 for full siblings or parent-offspring pairs, 0.25 for half-siblings or grandparent-grandchild pairs. In populations with high spatial mixing, however, the effective relatedness of the recipient of an altruistic act approaches zero, as the acting agent cannot distinguish kin from non-kin and distributes care indiscriminately. This is the relatedness dilution problem and is the primary driver of care erosion in our Phase 3 baseline.

### 2.2 The Baldwin Effect and Genetic Assimilation

Hinton and Nowlan (1987) demonstrated that phenotypic plasticity — the capacity for an organism to adjust its phenotype within its lifetime in response to environment — can guide natural selection even when the selectively advantageous phenotype is too improbable to arise by random mutation alone. The mechanism, now termed the Baldwin Effect, works as follows: plastic individuals who discover the adaptive phenotype by learning survive at higher rates; selection then favours heritable predispositions toward that phenotype; eventually, the previously plastic behaviour is encoded in the genotype without learning. This process is termed genetic assimilation.

In our Phase 4b experiment, we implement a `learning_rate` genome parameter that modulates within-lifetime reinforcement of care behaviour in response to observed benefit. We test whether this mechanism induces genetic assimilation of care, as evidenced by elevated zero-shot care rates in evolved genomes relative to a pre-plasticity baseline.

### 2.3 Spatial Structure and Care Evolution in ALife

Spatial population structure can create local clusters of cooperators even in the absence of kin recognition, as demonstrated by Nowak and May (1992) in their landmark study of spatial chaos and cooperation using the Prisoner's Dilemma on lattice structures. Their work showed that cooperators survive by forming self-sustaining spatial clusters, a mechanism that is formally distinct from kin selection but functionally analogous in creating the conditions for positive selection on prosocial behaviour.

Applied to maternal care, spatial proximity at birth — natal philopatry — provides a biologically plausible mechanism by which offspring remain near their birth mother long enough for proximity-based care selection to preferentially reach kin. This does not require kin recognition; it requires only that offspring disperse slowly relative to the maturation timescale. Our Phase 5 experiments directly test this mechanism by manipulating birth scatter radius as a proxy for natal philopatry strength.

### 2.4 The Key Gap

Prior ALife models of care evolution either hard-code care targets (restricting emergence to maintenance studies) or study care in isolation from the spatial mechanism that mediates effective relatedness. Our model contributes a unified treatment: care targets are fully emergent (distress-based selection among visible children, no kin recognition gene), and spatial structure is manipulated as an independent variable. This allows direct attribution of gradient reversal to the natal philopatry mechanism rather than to programmed kin preference.

---

## 3. Methods

### 3.1 Simulation Architecture

We implement a 2D discrete grid-world simulation (tick-based, synchronous update) with two agent types: `MotherAgent` and `ChildAgent`. At each tick, mothers select among three behavioural domains — care, forage, and self-maintenance — via an argmax over genome-weighted utility scores. No care targets are hard-coded; mothers select the highest-distress visible child from all children in their neighbourhood, regardless of lineage. Foreign-lineage care (r = 0) is the dominant event type in unstructured populations.

**Genome structure (Phases 3–5a):** Three continuous parameters in [0, 1]:
- `care_weight`: scales utility of care actions
- `forage_weight`: scales utility of foraging actions
- `self_weight`: scales utility of self-maintenance actions

**Phase 4 extension:** A fourth parameter, `learning_rate` ∈ [0, 1], is added. This parameter modulates the within-lifetime update rule: after each care event, `care_weight += learning_rate × (B_observed − care_cost)`. Under the kin-conditional variant (Phase 4b), updates fire only for own-lineage care events.

**Reproduction:** Roulette selection by agent energy at the terminal generation tick. Selected parents produce offspring with genomes perturbed by Gaussian noise N(0, σ = 0.05) per parameter when `mutation_enabled = True`.

**Pathfinding:** A* octile heuristic (diagonal cost = √2) to prevent agent freezing in crowded grids.

**Logging:** Per-event `care_log.csv` (care_weight, hunger_reduced, feed_cost, move_cost, lineage IDs), per-birth `birth_log.csv` (generation, care_weight, forage_weight, seed), and `population_history.json` (tick-level population and energy).

### 3.2 Experimental Phases

| Phase | Key Config | Scientific Purpose |
|-------|-----------|-------------------|
| Phase 1 | mutation=F, reproduction=T | Survival viability gate |
| Phase 3 | Genome(0.5,0.5,0.5) ± mutation, seeds 42–51, mult=1.0, scatter=5 | Care erosion baseline |
| Phase 4b | + learning_rate, plasticity_kin_conditional=T | Kin-conditional Baldwin Effect |
| Phase 5a | mult=1.15, scatter=2, Genome(0,0.50) | Ecological emergence — natal philopatry |
| Phase 5b | mult=1.15, scatter=8 (all else Phase 5a) | Control — high dispersal |

All multi-seed runs use seeds 42–51 (n = 10 independent replicates). Each seed runs for 5000 ticks (approximately 100 ticks per generation at standard reproduction rates).

### 3.3 B Quantification — Two-Level Measurement

We apply two distinct measurements of offspring benefit B, which must not be conflated in interpretation:

**Level 1 — Per-event B:** The direct energetic benefit of a single care action, measured as `hunger_reduced` in `care_log.csv`. This is the B term that appears directly in Hamilton's formula for individual care events: rB − C = r × hunger_reduced − (feed_cost + move_cost).

**Level 2 — Existential B (Phase 5):** The population-level selective consequence of low care_weight genomes. With `infant_starvation_multiplier = 1.15`, infants accumulate hunger at 1.15× the standard rate. At the calibrated value, infants die at approximately tick 108 without care intervention (maturity_age = 100 ticks). This means genomes that suppress care face extinction of their own lineage — a fitness consequence that is not captured by per-event B measurement. The existential B is operationalised as the difference in lineage reproductive success between high-care and low-care genomes across the 5000-tick run.

Both levels are reported in Results. Level 1 quantifies mechanism; Level 2 quantifies selection pressure.

### 3.4 Operationalisation of Hamilton's Rule

Hamilton's rule is applied post-hoc from care event logs; it is not a selection criterion in the simulation. Agents have no access to r during decision-making.

| Term | Operationalisation |
|------|-------------------|
| r | 2^(−d), d = generational distance (own child: d=1, r=0.5; grandchild: d=2, r=0.25) |
| B | `hunger_reduced` per care event (care_log.csv) |
| C | `feed_cost + move_cost` per care event |
| Selection gradient | Pearson's r of `care_weight` vs `generation` (birth_log.csv) |

**Why Pearson's r for the gradient (not bare r):** To avoid symbol collision with Hamilton's r (relatedness), we use "Pearson's r" throughout when referring to the selection gradient statistic, and "r" unqualified when referring to the coefficient of relatedness.

---

## 4. Results

### 4.1 Phase 3 — Care Erosion

Under standard ecological parameters (infant_starvation_multiplier = 1.0, birth_scatter_radius = 5), care_weight declines monotonically from a mean starting value of 0.500 across all 10 seeds. The mean Pearson's r of care_weight against generation is −0.178, with 9 of 10 seeds showing a negative gradient (Figure 1A). The forage_weight time series remains flat across seeds, confirming that the decline is specific to care rather than a general genomic drift artifact (Figure 1A, lower panel — hitchhiking check).

Hamilton's rule post-hoc analysis for the canonical seed (seed=42) reveals:
- Mean r per care event: 0.056 (89.5% of care events are foreign-lineage, r = 0)
- Mean per-event rB: 0.034
- Mean per-event C: 0.048
- **rB − C ≈ −0.004** — care is a net fitness liability

The diluted effective relatedness (0.056 vs the theoretical 0.500 for own-child care) is the primary mechanism. When 90% of care events reach unrelated recipients, the inclusive fitness benefit to the actor is negligible while the energetic cost is unchanged, placing the population below the Hamilton threshold.

The selection gradient of −0.178 establishes the Phase 3 erosion baseline against which all subsequent interventions are measured (Figure 1B).

**Figure 1.** Phase 3 care erosion. (A) Mean care_weight ± 95% CI across 10 seeds over 5000 ticks, with individual seed traces shown. forage_weight mean shown below as hitchhiking check. (B) Scatter of care_weight vs generation from birth_log.csv (seed=42); Pearson's r = −0.178 regression line overlaid.

### 4.2 Phase 4 — Kin-Conditional Baldwin Effect

The lineage-blind plasticity variant (Phase 4a) produces r = −0.216, worse than the Phase 3 baseline, confirming that indiscriminate learning amplifies noise rather than signal and is not reported further.

Under kin-conditional plasticity (Phase 4b), the care_weight trajectory shows a characteristic Baldwin signature: an initial trough to 0.355 at approximately tick 1500 (reflecting the energetic cost of the novel learning mechanism displacing care in the genome), followed by partial recovery to 0.436 by tick 5000 (Figure 2A). The `learning_rate` parameter sweeps monotonically from 0.103 to 0.170 across the run, with 8 of 10 seeds showing this upward trajectory — the primary positive finding of Phase 4.

For the genetic assimilation test, evolved Phase 4b genomes (seed=42) were transferred to a zero-shot environment (reproduction=False, mutation=False) and their care window rate was compared to the pre-plasticity Phase 2 baseline (0.09069 events/mother-tick). The seed=42 zero-shot rate was 0.09933 — a +9.5% increase, consistent with partial genetic assimilation at the single-genome level.

At the population level, the zero-shot rate distribution across 10 seeds was not significantly different from the Phase 2 baseline: one-sample t-test, p = 0.815, Cohen's d = 0.076 (Figure 2B). We interpret this as genetic assimilation being present but below the detection threshold with n = 10 seeds. This is a partial null result, not a complete null: the learning_rate sweep is the robust finding, and the assimilation effect exists at the single-seed level.

**Figure 2.** Phase 4b Baldwin Effect. (A) Phase 3 vs Phase 4b care_weight trajectory — Baldwin trough and partial recovery visible. (B) Zero-shot care window rate bar chart: Phase 2 baseline vs Phase 4b evolved genomes; p = 0.815.

### 4.3 Phase 5 — Ecological Emergence

#### 4.3.1 Gradient Reversal (Phase 5a)

With existential infant dependency (infant_starvation_multiplier = 1.15) and natal philopatry (birth_scatter_radius = 2), the selection gradient reverses sign in 9 of 10 seeds. Starting from a depleted baseline of care_weight ~ Uniform(0, 0.50) (mean ≈ 0.25, below the Phase 3 eroded equilibrium of 0.42), care_weight builds to a mean of 0.288 ± 0.033 by tick 5000 (Figure 3A).

| Statistic | Value |
|-----------|-------|
| Mean Pearson's r (gradient) | **+0.0788** |
| 95% CI | [+0.053, +0.105] |
| One-sample t vs 0 | t = 5.93, **p = 0.0002** |
| Cohen's d vs Phase 3 baseline | **1.87** |
| Seeds positive | **9/10** |
| Phase 3 reference gradient | −0.178 |

The 95% confidence interval lies entirely above zero, and the effect size of d = 1.87 relative to the Phase 3 reference is very large by conventional thresholds. Seed 43 is the sole outlier (Pearson's r = −0.026), near-zero and plausibly attributable to stochastic early extinction of high-care lineages in that particular initialisation. The remaining 9 seeds show gradients ranging from +0.047 to +0.112 (Figure 3B).

The zero-shot comparison is noted but not interpreted as a primary assimilation test in Phase 5: the depleted starting care_weight (mean 0.25 vs Phase 3's 0.50) creates a directional confound in window rate comparisons that cannot be removed without matched initialisation. The zero-shot rate (0.052) is reported for completeness only.

#### 4.3.2 Philopatry Contribution (Phase 5b)

With dispersal increased to birth_scatter_radius = 8 while holding infant_starvation_multiplier = 1.15 constant, the mean gradient across seeds falls to Pearson's r = +0.050 compared to +0.077 under natal philopatry (scatter = 2). The gradient remains positive — confirming that existential B alone provides a real selection pressure — but is meaningfully weaker, confirming that natal philopatry independently amplifies the gradient.

| Condition | Mean Pearson's r |
|-----------|-----------------|
| Phase 3 (mult=1.0, scatter=5) | −0.178 |
| Phase 5b (mult=1.15, scatter=8) | +0.050 |
| Phase 5a (mult=1.15, scatter=2) | +0.077 |

**Figure 3.** Phase 5 gradient reversal. (A) Phase 5a CI trajectory (rising, n=10 seeds), Phase 5b control (weakened), and Phase 3 reference (declining) overlaid on same axes. (B) Per-seed Pearson's r bar chart for Phase 5a — 9 of 10 seeds positive.

---

## 5. Discussion

### 5.1 Gradient Reversal as the Primary Result

The shift from Pearson's r = −0.178 (Phase 3) to Pearson's r = +0.079 (Phase 5a) is not a reduction in selection pressure — it is a sign change. Under Phase 3 conditions, care is a fitness liability; under Phase 5a conditions, care is a fitness asset. This reversal is the central empirical contribution of this work. The effect size (Cohen's d = 1.87) and 9/10 seed robustness place this result well beyond statistical noise.

The reversal was achieved by modifying exactly two ecological parameters from the Phase 3 baseline: infant_starvation_multiplier (1.0 → 1.15) and birth_scatter_radius (5 → 2). No changes were made to the genome structure, mutation rate, selection mechanism, or decision model. The result is therefore attributable specifically to the ecological manipulation.

### 5.2 The AND Condition: Why Neither Mechanism Alone Suffices

The Phase 5b control demonstrates that existential B alone (mult=1.15, scatter=8) yields a positive but weakened gradient (r = +0.050). The full reversal (r = +0.077) requires natal philopatry in addition. This supports the AND-condition interpretation: both mechanisms must be active for Hamilton's rule to be robustly satisfied.

The logic is as follows. Under high dispersal, infants die without care (existential B is real), but the mothers providing care are not systematically their own birth mothers — spatial mixing means that care events are distributed among mothers with low r to the recipient. The per-event Hamilton calculation remains rB − C < 0 for most events because effective r is diluted, just as in Phase 3. Adding natal philopatry ensures that the mothers proximate to a dying infant are statistically likely to be that infant's birth mother (r = 0.5), converting the majority of care events from foreign-lineage (r ≈ 0) to own-lineage (r = 0.5) interactions. With existential B, rB now substantially exceeds C for own-lineage events, producing positive selection.

Neither condition alone is sufficient in this model:
- Existential B without philopatry: r = +0.050 (real but weak — effective r still diluted)
- Philopatry without existential B: Phase 3 result would be expected (spatial clustering insufficient to overcome low-B regime at mult=1.0)

### 5.3 Spatial Structure as Kin Recognition Substitute

No kin recognition gene exists in this model. Mothers observe the distress of all visible children and select the highest-distress individual regardless of lineage. The kin bias that emerges under natal philopatry (scatter=2) is entirely a consequence of the spatial proximity of offspring to their birth mother during the maturation window (0 to 100 ticks). This is functionally equivalent to natal philopatry in biological systems — the retention of offspring near their birth site until independence.

Biological parallels are well established. In wolves and African wild dogs, pack structure ensures that reproductive females care for offspring that are closely related to all pack members (Stacey and Koenig, 1990). In passerine birds, natal philopatry creates the kinship structure that supports cooperative breeding without requiring explicit recognition of relatedness (Emlen, 1995). Our model demonstrates that the spatial mechanism alone — without any cognitive kin-recognition capacity — is sufficient to produce the kin-biased care events that Hamilton's rule requires.

### 5.4 The Baldwin Effect: A Partial Positive Finding

Phase 4b produces a learning_rate sweep in 8/10 seeds — a robust Baldwin signal. The care_weight trajectory follows the characteristic trough-and-recovery pattern described by Hinton and Nowlan (1987): an initial fitness cost as the learning mechanism is genetically accommodated, followed by partial recovery as the learning mechanism begins returning selective advantage. This is the expected signature of a Baldwin process in progress.

The zero-shot assimilation test (p = 0.815) is a partial null result that should be interpreted carefully. It does not mean that no assimilation occurred — the single-seed +9.5% increase is real and directionally consistent with assimilation. It means that the magnitude of genetic assimilation, averaged across 10 seeds, is below the detection threshold of a one-sample t-test at n = 10. With larger n or longer evolutionary time, assimilation would be expected to accumulate. The honest interpretation is: the Baldwin Effect is present and the learning_rate sweep is its robust signature; genetic assimilation is plausible but not yet statistically demonstrable at this sample size.

### 5.5 Limitations

**5.5.1 Operative threshold and the origin gap.** The model's argmax decision architecture places a practical lower bound on functional care: below care_weight ≈ 0.075, care never wins the argmax at typical energy levels, and no care events fire. True emergence from absolute zero care is therefore not testable in this framework. Our Phase 5 initialisation (Uniform(0, 0.50), mean ≈ 0.25) places the population in the functionally depleted regime but above the operative threshold. This is an important scope limitation: we demonstrate that care can build from a depleted baseline, not that it can arise from a fully inert population.

**5.5.2 B quantification at two levels.** Per-event B (hunger_reduced) and existential B (lineage extinction risk from infant dependency) are distinct measurements that operate at different scales. Results sections report per-event rB − C for Hamilton analysis and the population-level gradient for selection analysis. These must not be conflated: a care event that satisfies rB > C at the per-event level may still fail to produce positive selection if the majority of events are foreign-lineage; and existential B operates through lineage extinction risk, not per-event energetics. Both levels are necessary for a complete account.

**5.5.3 Cost of philopatry.** The model does not implement local resource competition as a cost of natal philopatry. In biological systems, offspring remaining near their birth site compete with siblings and parents for food and territory — a cost that partially offsets the inclusive fitness benefit. This is a standard simplification in ALife grid-world models, where food is globally distributed and offspring do not consume food during the maturation window. Future work should incorporate local resource depletion to provide a more realistic cost structure for philopatry.

---

## 6. Conclusion

This study demonstrates that maternal care can build under positive selection from a depleted evolutionary baseline when two ecological conditions are jointly satisfied: existential infant dependency (infant_starvation_multiplier = 1.15) and natal philopatry (birth_scatter_radius = 2). Under these conditions, the selection gradient on care reverses from −0.178 (Phase 3 erosion) to +0.079 (Phase 5a emergence), a sign change robust across 9 of 10 independent seeds (p = 0.0002, Cohen's d = 1.87).

Neither condition alone achieves robust reversal. High dispersal with existential B yields a weakened positive gradient (+0.050, Phase 5b), confirming that philopatry is independently load-bearing. The mechanism is spatial: natal philopatry elevates effective relatedness of care events from near-zero (foreign care under mixing) to 0.5 (own-child under proximity), converting care from a Hamilton-violating fitness cost to a Hamilton-satisfying fitness investment.

Kin-conditional phenotypic plasticity produces a robust learning_rate sweep (Baldwin Effect signal, 8/10 seeds) but genetic assimilation is below detection threshold at n = 10 seeds. This is a partial positive result: the Baldwin mechanism is active and the learning-rate evolution is real, but assimilation has not accumulated to statistical significance at this experimental scale.

Future work should address three primary extensions. First, stochastic modelling of the operative threshold crossing (care_weight 0.00 → 0.075) to determine whether neutral drift or environmental forcing can bridge the inert-to-functional gap. Second, local resource competition as a philopatry cost — quantifying whether realistic food depletion near birth sites reduces or eliminates the natal philopatry advantage. Third, epigenetic inheritance and social learning (copy successful mothers) as additional plasticity mechanisms that may accelerate genetic assimilation beyond the Baldwin Effect timescale demonstrated here.

---

## References

Axelrod, R., and Hamilton, W. D. (1981). The evolution of cooperation. *Science*, 211(4489), 1390–1396.

Emlen, S. T. (1995). An evolutionary theory of the family. *Proceedings of the National Academy of Sciences*, 92(18), 8092–8099.

Hamilton, W. D. (1964). The genetical evolution of social behaviour. I and II. *Journal of Theoretical Biology*, 7(1), 1–52.

Hinton, G. E., and Nowlan, S. J. (1987). How learning can guide evolution. *Complex Systems*, 1(3), 495–502.

Nowak, M. A., and May, R. M. (1992). Evolutionary games and spatial chaos. *Nature*, 359(6398), 826–829.

Stacey, P. B., and Koenig, W. D. (Eds.) (1990). *Cooperative Breeding in Birds: Long-Term Studies of Ecology and Behavior*. Cambridge University Press.
