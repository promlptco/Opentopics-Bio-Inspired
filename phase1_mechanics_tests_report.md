# Phase 1 — Mechanics Tests Report

**Status:** ✅ COMPLETE — 6/6 test files passed, 31/31 sub-tests passed  
**Seed:** 42 for default validation runs  
**Purpose:** Validate the low-level mechanics of the simulation before using it for Phase 2 survival experiments and later Phase 3 full mother-child behavioral experiments.

---

## 1. Purpose of Phase 1

Phase 1 is designed to answer one important question:

> Are the core mechanics of the simulation reliable enough to build higher-level experiments on top of them?

Before analyzing survival, care behavior, reproduction dynamics, learning, or evolution, the simulation must first prove that its basic components work correctly. If mutation, inheritance, reproduction gating, stochastic action selection, or seeding are broken, then later results could look meaningful while actually being caused by hidden implementation errors.

Therefore, Phase 1 does not try to prove that the model is realistic yet. Instead, it verifies that the simulation engine is mechanically stable, internally consistent, and reproducible.

The six tested mechanics are:

1. Mutation
2. Inheritance
3. Reproduction eligibility
4. Population stability
5. Stochasticity control
6. Softmax calibration

Together, these tests check whether genetic operators, agent-level decision mechanics, population-level behavior, and random control are trustworthy enough for the next phase.

---

## 2. Test 01 — Mutation

### Purpose

Test 01 verifies whether genome mutation works correctly.

The main assumption is:

> Mutation should introduce controlled genetic variation without producing invalid genome values.

This is important because later evolutionary experiments depend on mutation as the source of variation. If mutation is too weak, evolution cannot explore. If mutation is too strong, genomes become unstable. If mutation goes outside valid bounds, later behavior may become physically or logically invalid.

### Assumptions Tested

Test 01 checks that:

- Mutation changes genome values when mutation is enabled.
- Mutation does not change values when `mutation_rate = 0.0`.
- Partial mutation rate behaves statistically close to the requested probability.
- Mutation deltas are centered near zero.
- Mutation scale matches the intended sigma.
- Genome values remain inside `[0, 1]`.
- Increasing sigma increases mutation spread.

The latest run shows that all five genome fields mutated correctly at `mutation_rate=1.0`, with `100/100` mutations for each field. The partial mutation-rate test also behaved correctly, with observed mutation rates around `0.49–0.52`, which is consistent with an intended mutation probability of `0.5`.

### Highlighted Code Logic

The strongest parts of Test 01 are the checks on mutation rate, mutation distribution, and sigma sensitivity.

The mutation-rate check verifies that mutation is not simply always-on or always-off. It confirms that the mutation probability is actually being used.

The distribution check measures mutation deltas rather than only final values. This is important because the mutation operator should behave like:

```text
child_value = parent_value + noise
```

So the most meaningful measurement is:

```text
delta = child_value - parent_value
```

The observed delta means were all very close to zero, and the standard deviations were close to `0.05`.

| Field | Delta Mean | Stdev | Normal Test p-value |
|---|---:|---:|---:|
| care_weight | 0.0005 | 0.0516 | 0.769 |
| forage_weight | -0.0001 | 0.0498 | 0.087 |
| self_weight | 0.0011 | 0.0482 | 0.131 |
| learning_rate | 0.0001 | 0.0515 | 0.811 |
| learning_cost | 0.0010 | 0.0498 | 0.842 |

These results support the assumption that mutation noise is centered, stable, and approximately consistent with the intended Gaussian-style mutation model.

The sigma sweep also confirmed that sigma directly controls mutation spread.

| Sigma | Output Stdev |
|---:|---:|
| 0.01 | 0.0103 |
| 0.03 | 0.0300 |
| 0.05 | 0.0493 |
| 0.07 | 0.0705 |
| 0.10 | 0.1016 |

This monotonic relationship is important because it means mutation strength is tunable and predictable.

### Plot Observation

The Test 01 mutation plot shows five field histograms plus a sigma sweep panel.

The field histograms show that all genome parameters are centered around the parent value `0.5`. The fitted normal curves overlap closely with the theoretical `N(0.5, 0.05)` curves. This visually supports the numerical result that the mutation operator produces stable, symmetric variation.

The sigma sweep panel shows that smaller sigma values create narrow distributions, while larger sigma values create wider distributions. This confirms that sigma is not just a parameter in the code, but actually controls the spread of mutation outcomes.

### Result Interpretation

Test 01 confirms that mutation is safe and usable for later phases.

The key conclusion is:

> Mutation can introduce bounded, controlled, statistically reasonable variation into all genome fields.

This means later evolutionary results can be interpreted with more confidence because genetic diversity is being generated correctly.

---

## 3. Test 02 — Inheritance

### Purpose

Test 02 verifies whether genomes are copied and inherited correctly.

The main assumption is:

> A child genome should begin as an exact independent copy of the parent genome before mutation is applied.

This is important because evolution requires trait continuity. If inheritance is broken, then successful traits cannot be passed from parent to child.

### Assumptions Tested

Test 02 checks that:

- `copy()` preserves all genome fields exactly.
- A copied genome is independent from the parent.
- `mutation_rate = 0.0` preserves inherited values exactly.
- `mutation_rate = 1.0` creates variation.

All four inheritance sub-tests passed.

### Highlighted Code Logic

The most important logic is the independence test. Copying a genome must not create an alias to the same object. If the child genome and parent genome pointed to the same object, then changing the child would accidentally change the parent too.

The test correctly modifies the copied child genome and then checks that the parent remains unchanged. This directly tests the assumption that parent and child genomes are separate objects.

The `mutation_rate=0.0` test is also important because it isolates inheritance from mutation. If mutation is disabled, the child should be genetically identical to the parent. This confirms that any later variation comes from mutation, not from accidental copying errors.

### Result Interpretation

Test 02 confirms that inheritance is reliable.

The key conclusion is:

> Parent genomes can be passed to descendants without corruption, aliasing, or unintended changes.

This supports later experiments where genetic traits need to persist across generations.

---

## 4. Test 03 — Reproduction Eligibility

### Purpose

Test 03 verifies the logical gates controlling whether a mother is allowed to reproduce.

The main assumption is:

> A mother should only be eligible to reproduce when the required biological and simulation constraints are satisfied.

This test does not check actual child spawning. Instead, it focuses on reproduction permission logic.

### Assumptions Tested

Test 03 checks that:

- A mother can reproduce above the energy threshold.
- A mother can reproduce exactly at the energy threshold.
- A mother cannot reproduce below the threshold.
- A mother cannot reproduce while already having a child.
- A mother cannot reproduce while on cooldown.
- Cooldown decreases correctly and does not go below zero.

All six reproduction eligibility sub-tests passed.

### Highlighted Code Logic

The most important test is the exact threshold case:

```text
energy == threshold
```

This matters because the intended rule is:

```text
energy >= threshold
```

Without this test, the implementation could accidentally use:

```text
energy > threshold
```

and still pass low-energy and high-energy checks. By testing exact equality, the test confirms the intended boundary behavior.

The cooldown test is also important because it verifies that cooldown behaves like a safe counter:

```text
2 → 1 → 0 → 0
```

This prevents negative cooldown values and ensures that reproduction timing remains controlled.

### Result Interpretation

Test 03 confirms that reproduction eligibility is logically controlled.

The key conclusion is:

> Reproduction cannot occur under invalid conditions such as low energy, active cooldown, or existing child ownership.

This prevents uncontrolled or biologically inconsistent reproduction in later population experiments.

Important limitation:

> Test 03 does not prove that child spawning, energy deduction, world placement, or mother-child linkage are correct. Those are integration-level mechanics and should be interpreted through later tests or separate reproduction-spawn tests.

---

## 5. Test 04 — Population Stability

### Purpose

Test 04 checks whether the full simulation loop behaves stably over a short validation horizon.

The main assumption is:

> When all mechanics run together, the population should not immediately collapse, explode, or behave nondeterministically.

This is the first broader integration test. It does not validate long-term realism yet, but it checks whether the simulation can run without immediate mechanical failure.

### Assumptions Tested

Test 04 checks that:

- The population does not immediately go extinct.
- The population does not immediately explode.
- Same-seed runs produce identical results.
- Starvation causes extinction when food and recovery are removed.

The latest run showed:

| Check | Result |
|---|---:|
| Alive mothers after 100 ticks | 20 |
| Total created population after 100 ticks | 30 |
| Explosion threshold | 50 |
| Deterministic final alive, run 1 | 10 |
| Deterministic final alive, run 2 | 10 |
| Starvation initial alive | 5 |
| Starvation final alive | 0 |

All Test 04 sub-tests passed.

### Highlighted Code Logic

The no-extinction test confirms that the initial configuration is not instantly fatal. This is important because if all agents died immediately, later survival experiments would be meaningless.

The no-explosion test checks total created population rather than only currently alive population. This is stronger because it catches hidden reproduction bursts even if some agents later die.

The deterministic test checks whether repeated runs with the same seed produce the same result. This is essential for reproducible experiments.

The starvation test disables food, rest recovery, children, and reproduction. This isolates the hunger/energy depletion mechanic. Since the final alive count becomes zero, the test confirms that agents actually depend on energy input and cannot survive indefinitely without food or recovery.

### Plot Observation

The population stability plot shows three trajectories:

- Alive mothers
- Alive children
- Total alive population

The plot shows a stable initial period, followed by step-like population changes around later ticks. The total population stays below the explosion threshold, and the system does not collapse immediately.

The flat child count indicates that the child population remains constant in this configuration. Since this behavior is repeatable and the tests pass, it should be documented as part of the current simulation mechanics rather than treated as random noise.

The plot is useful because it reveals dynamics that raw pass/fail tests cannot show. For example, the test can pass while still showing step changes caused by maturation or population accounting behavior. This is exactly why the Test 04 plot is worth keeping.

### Result Interpretation

Test 04 confirms short-horizon population stability.

The key conclusion is:

> The simulation loop can run with all core mechanics active without immediate extinction, uncontrolled explosion, or unreproducible population outcomes.

For Phase 2, this means the simulation is stable enough to begin survival-regime tuning, such as balanced, easy, and harsh environments.

However, this result should not be overclaimed. It does not prove that the population model is realistic. It only proves that the short-horizon engine behavior is mechanically stable.

---

## 6. Test 05 — Stochasticity Control

### Purpose

Test 05 verifies whether random behavior is controlled by seeds.

The main assumption is:

> Stochastic decisions should be reproducible under the same seed and meaningfully different under different seeds.

This is critical for experimental reliability. If random seeds do not control the simulation, then later comparisons between configurations could be invalid.

### Assumptions Tested

Test 05 checks that:

- Same seed produces identical action sequences.
- Different seeds produce divergent action sequences.
- Running a different seed in between does not contaminate a repeated same-seed run.

The latest run showed:

| Check | Result |
|---|---:|
| Same seed 42 | 700/700 identical |
| Different seeds 42 vs 49 | 417/650 divergences |
| Different-seed divergence rate | 64.2% |
| Repeated seed 12345 after seed 99999 | 617/617 identical |

All three stochasticity sub-tests passed.

### Highlighted Code Logic

The strongest part of this test is that it records actual domain choices from the simulation. It does not only compare final population counts. Final counts can accidentally match even when internal actions differ. By comparing full action sequences, the test checks deeper reproducibility.

The repeated-seed-after-different-seed test is also important. It confirms that global random state is reset properly when a new simulation is initialized. This prevents hidden seed contamination across experiments.

### Result Interpretation

Test 05 confirms that stochastic mechanics are seed-controlled.

The key conclusion is:

> Random action selection is reproducible when the seed is fixed, and different seeds produce meaningfully different behavioral trajectories.

This makes later multi-seed experiments valid. It means that when Phase 2 compares survival outcomes across seeds, the seed is acting as a controlled experimental variable rather than uncontrolled noise.

---

## 7. Test 06 — Softmax Calibration

### Purpose

Test 06 verifies whether the softmax action-selection mechanism is mathematically correct and empirically calibrated.

The main assumption is:

> Given a set of action utilities, `softmax_probs()` should convert them into valid probabilities according to the intended Boltzmann/Gibbs equation.

This matters because the simulation’s agent behavior depends heavily on softmax. If the softmax function is wrong, then care, forage, and self-maintenance choices could be biased or unstable.

### Assumptions Tested

Test 06 checks that:

- `softmax_probs()` matches the theoretical equation.
- Probabilities are valid: no NaN, no infinity, no negative values, and sum to 1.
- Empirical sampling matches theoretical probabilities.
- Moderate utility contrast produces proportional, non-collapsed behavior.
- Entropy increases as temperature increases.
- Equal scores produce uniform probabilities.
- Zero scores produce uniform probabilities.
- Single-action input gives probability 1.0.

All Test 06 sub-tests passed.

### Highlighted Code Logic

The mathematical correctness test compares implementation output against a manual softmax calculation. The result matched exactly for the tested case:

| Action | Expected | Got | Difference |
|---|---:|---:|---:|
| care | 0.94649912 | 0.94649912 | 0.00e+00 |
| forage | 0.04712342 | 0.04712342 | 0.00e+00 |
| self | 0.00637746 | 0.00637746 | 0.00e+00 |

This directly verifies that the function implements the intended equation.

The empirical sampling test also passed. The theoretical probability of choosing the high-utility action was `0.999665`, while the empirical frequency over 5,000 samples was `0.999800`, with a very small difference of `0.000135`.

The temperature sensitivity test showed that entropy increases as tau increases:

| Tau | Entropy | Top Action Probability |
|---:|---:|---:|
| 0.05 | 0.0174 | 0.9975 |
| 0.10 | 0.2070 | 0.9503 |
| 0.50 | 0.9885 | 0.5405 |
| 1.00 | 1.0693 | 0.4368 |

This confirms the expected behavior:

```text
Lower tau  → sharper, more deterministic choices
Higher tau → flatter, more exploratory choices
```

### Plot Observation

The Test 06 plot is useful because it compares observed sampling frequencies against theoretical probabilities.

In the high-contrast scenario, the highest-utility action dominates almost completely. This is expected because tau is low and the utility gap is large.

In the moderate scenario, care still dominates, but forage and self retain small probabilities. This confirms that softmax is not simply an argmax selector.

In the near-equal scenario, the action probabilities become more balanced. This is important because when utilities are similar, the agent should remain somewhat exploratory.

The temperature sensitivity panel shows that as tau increases, the distribution becomes flatter. Care starts highly dominant at low tau, then gradually decreases as forage and self probabilities increase. This visually confirms that tau controls the exploitation-exploration balance.

### Result Interpretation

Test 06 confirms that the decision probability mechanism is reliable.

The key conclusion is:

> Softmax action selection is mathematically correct, numerically safe, empirically calibrated, and sensitive to temperature in the intended direction.

This is important for Phase 2 and Phase 3 because action probabilities drive agent behavior. Later behavioral results can be interpreted as consequences of configured utilities and temperature, rather than a broken probability function.

---

## 8. Overall Results Summary

### Test File Summary

| Test File | Focus | Status |
|---|---|---|
| Test 01 | Mutation | ✅ Passed |
| Test 02 | Inheritance | ✅ Passed |
| Test 03 | Reproduction eligibility | ✅ Passed |
| Test 04 | Population stability | ✅ Passed |
| Test 05 | Stochasticity control | ✅ Passed |
| Test 06 | Softmax calibration | ✅ Passed |

The Phase 1 runner reported:

```text
Passed: 6/6
Failed: 0/6
Phase 1: ALL TESTS PASSED
```

### Sub-test Summary

| Test | Number of Sub-tests | Status |
|---|---:|---|
| Test 01 Mutation | 6 | ✅ Passed |
| Test 02 Inheritance | 4 | ✅ Passed |
| Test 03 Reproduction | 6 | ✅ Passed |
| Test 04 Population Stability | 4 | ✅ Passed |
| Test 05 Stochasticity Control | 3 | ✅ Passed |
| Test 06 Softmax Calibration | 8 | ✅ Passed |
| **Total** | **31** | ✅ **31/31 Passed** |

---

## 9. What Phase 1 Proves

After Phase 1, we can reasonably assume that:

1. Mutation creates bounded and controlled variation.
2. Mutation rate and sigma behave as intended.
3. Inheritance preserves parent genome values.
4. Copied genomes are independent objects.
5. Reproduction eligibility gates are logically correct.
6. Cooldown mechanics are stable.
7. The full simulation loop can run without immediate extinction or explosion.
8. Starvation mechanics work when food and recovery are removed.
9. Same seeds reproduce the same stochastic behavior.
10. Different seeds create meaningfully different action trajectories.
11. Softmax probabilities match the intended mathematical model.
12. Softmax sampling matches theoretical probabilities.
13. Tau correctly controls action-selection sharpness.

Together, these results support the statement:

> The low-level simulation mechanics are stable, reproducible, and internally consistent enough to support Phase 2 experiments.

---

## 10. What Phase 1 Does Not Prove

Phase 1 should not be overinterpreted.

It does not prove that:

- The survival environment is already balanced.
- The model is biologically realistic.
- Care behavior is meaningful.
- Evolution improves fitness.
- Long-term population dynamics are stable.
- Phase 3 mother-child interaction dynamics are fully validated.
- Actual child spawning and world placement are fully tested by Test 03 alone.

This distinction is important. Phase 1 validates the foundation, not the final scientific claim.

---

## 11. Implication for Phase 2

Because Phase 1 passed, Phase 2 can now focus on survival-regime validation rather than debugging basic mechanics.

The next phase can safely investigate questions like:

- What parameter settings produce balanced survival?
- What settings produce easy survival?
- What settings produce harsh survival?
- How sensitive are outcomes to food availability, perception radius, energy cost, and rest recovery?
- Does the system reach an edge-of-stability regime?
- Are population and energy trajectories consistent across seeds?

In other words, Phase 1 allows Phase 2 to shift from:

```text
Do the mechanics work?
```

to:

```text
How do these mechanics behave under different environmental conditions?
```

---

## 12. Final Verdict

Phase 1 is complete and successful.

The test suite confirms that the simulation’s core mechanics are reliable enough to support higher-level experiments. Mutation, inheritance, reproduction eligibility, population stability, stochastic control, and softmax calibration all passed their validation checks.

One important bug was already caught and fixed during this phase: the mutation sigma mismatch, where the implementation used a different sigma than the design specification. After correction, the mutation distribution and sigma sensitivity tests confirm that the implementation now matches the intended behavior.

Therefore, the engine is ready for Phase 2 survival experiments.

**Final conclusion:**

> Phase 1 establishes a mechanically valid and reproducible simulation foundation. The system is now ready for Phase 2, where the focus should move from unit-level correctness to survival-regime tuning and multi-seed behavioral validation.
