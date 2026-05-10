# EVO_PROPOSAL: Phase 5 Block 2 — Asynchronous Baldwin Evolution

**Status**: Proposal (Awaiting Approval)  
**Date**: 2026-05-10  
**Branch**: V3  
**Deadline**: 2026-05-17

**Prepared by**: GitHub Copilot (Haiku 4.5)  
**For Implementation by**: Any Agent / Collaborator  
**Reference**: ROADMAP.md, CURRENT_STATE.md, Algorithm 1 & 2 (Thesis)

---

## Executive Summary

This proposal defines the implementation of **Phase 5 Block 2** — a continuous asynchronous evolutionary system designed to test whether **maternal-care instinct emerges from genetic selection under metabolic learning constraints**, supporting the Baldwin Effect hypothesis.

**Key Innovation**: CLI-driven parameter configuration allows user to test any combination of evolutionary pressures (mutation ON/OFF × plasticity ON/OFF) without code modification.

---

## 1. Scientific Scope

### Research Question
*Can maternal-care behavior emerge from selfish-lineage selection under asynchronous evolution, without a dedicated altruism gene, through the Baldwin Effect?*

### Theoretical Framework
- **Asynchronous Evolution**: Overlapping generations, continuous time, independent agent lifecycles (not generation-based GA)
- **Implicit Fitness**: Energy balance + reproduction threshold; no external reward function
- **Reward-Modulated Hebbian Learning**: Plasticity adapts behavior locally; metabolic cost creates pressure for genetic assimilation
- **Genetic Assimilation**: Learned behaviors become heritable; offspring partially inherit parent's learned weights

### Success Criteria
1. **Genetic Selection Signal**: `mut_on_plast_off` → care_weight rises above 1/3 neutrality
2. **Baldwin Scaffold**: `mut_on_plast_on` → faster early fitness rise than mutation-only (plasticity accelerates initial adaptation)
3. **Null Control**: `mut_off_plast_off` → care_weight stays ~1/3 (no drift without selection)
4. **Genetic Assimilation Measure**: Population innateness_index increases (plasticity decreases) while fitness maintains
5. **Phenotype-Genome Distance**: Decreases over time (learned behaviors encode into genome)

---

## 2. Core Algorithms

### Algorithm 1: Asynchronous Agent Update with Plasticity Cost (Per Tick)

```
Function UpdateAgent(agent, dt):
    
    /* Age and base metabolism */
    agent.age ← agent.age + dt
    agent.energy ← agent.energy - metabolism_base
    
    /* Perceive and compute brain state */
    agent.FeedInputs()              // sensory inputs: children, food, energy
    agent.TickBrain(dt)             // softmax motivations + choose_action()
    
    /* Reward-modulated Hebbian learning + immediate energy deduction */
    if agent.plasticity_enabled then
        modulation_signal ← agent.compute_modulation_signal()
        cost_p ← agent.compute_plasticity_cost(modulation_signal)
        if cost_p > 0 then
            agent.energy ← agent.energy - cost_p
            agent.lifetime_learning_cost ← agent.lifetime_learning_cost + cost_p
            agent.apply_expression_noise()  // molecular noise during learning
    
    /* Execute action (deduct action-specific cost) */
    action ← agent.choose_action()
    action_cost ← config.get_action_cost(action)
    agent.energy ← agent.energy - action_cost
    agent.ExecuteActions()
    
    /* Natural selection and reproduction handled by Simulation loop */
```

**Key Timing**:
1. Plasticity cost computed **fresh this frame** (not accumulated forward)
2. Deducted **immediately** after computation
3. Expression noise applied **only during learning** (modulation_signal ≠ 0)
4. Action cost deducted **after** learning cost
5. Reproduction checked **by Simulation**, not in UpdateAgent()

---

### Algorithm 2: Value Mutation (Parametric + Epigenetic, No Structural Changes)

```
Function MutateDNA(child_dna, μ):
    
    /* Parametric Mutation: Numerical gene changes */
    for each gene ∈ {care_weight, forage_weight, self_weight, 
                     learning_rate, plasticity_coefficient} do
        if rand() < μ then
            gene ← gene + N(0, mutation_sigma)
    
    /* Clamp to valid ranges */
    learning_rate ← clamp(learning_rate, 0.0, 0.2)
    plasticity_coefficient ← clamp(plasticity_coefficient, 0.0, 1.0)
    
    /* Renormalize motivation weights: sum = 1.0 */
    total ← care_weight + forage_weight + self_weight
    care_weight ← care_weight / total
    forage_weight ← forage_weight / total
    self_weight ← self_weight / total
    
    /* NO Structural Mutation in Block 2 */
    /* (No add/remove nodes, no connection toggles, no topology changes) */
    
    return child_dna
```

**Key Principles**:
- Value mutation only: changes gene values, not network structure
- Parametric mutation: weights, learning rates
- Epigenetic drift: inherited phenotype can mutate separately (see reproduction)
- Renormalization: preserves motivational budget constraint (sum=1)
- No topology changes: focus on value evolution first

---

## 3. Core Definitions

### Modulation Signal (Sparse Ecological Events)

Computed locally by agent from embodied perception. Triggers **only** on significant events:

| Event | Signal | Biological Meaning |
|-------|--------|---|
| Child nearby and alive | +0.2 | Opportunity for care |
| Successful feed | +1.0 | Caregiving effectiveness |
| Child critical hunger (>0.9) | -0.5 | Failure to sustain offspring |
| Child death | -1.0 | Complete failure |
| Child matured | +5.0 | Reproductive success |
| **Range** | [-5, 5] | Clipped to prevent extreme values |

**NOT triggered on**: continuous small penalties, hunger increase, resource scarcity.

---

### Plasticity Cost (Fresh Per Frame)

Energy deducted for learning activity this tick only:

```
cost_p = alpha × |Δweights| + beta × plasticity_coefficient

Where:
  alpha = 0.01   // learning activity cost (per magnitude of weight change)
  beta = 0.001   // maintenance cost of plasticity machinery (baseline)
```

**Only applied if**:
1. `plasticity_enabled = true`
2. `modulation_signal ≠ 0` (active learning event)

**Consequences**:
- Inactive brains are metabolically cheap
- Constantly rewiring brains become expensive
- Evolution discovers that learning is energetically costly
- Pressure to transition from learned → innate behavior (genetic assimilation)

---

### Phenotype Inheritance (Partial Epigenetic)

Offspring inherit **partial** of parent's learned behavior, not full:

```
expressed_value = genome_value + retention × (parent_expressed - genome_value)

retention = 0.15  // 15% of parent's learning is inherited
```

**Example**:
- Parent genome: care=0.3, expressed_care=0.5 (learned +0.2)
- Offspring genome (post-mutation): care=0.32
- Offspring expressed: 0.32 + 0.15×(0.5-0.32) = 0.32 + 0.03 = 0.35

**Biological Interpretation**:
- Not Lamarckian full inheritance (would be retention=1.0)
- Not purely Darwinian (would be retention=0.0)
- Baldwinian: learned behavior provides scaffold for evolution, but not guaranteed to persist

---

### Genetic Assimilation Metrics

Two key measures track assimilation:

1. **Innateness Index**: 
   ```
   innateness = 1 - mean(plasticity_coefficient)
   ```
   Higher = population relies more on innate behavior, less on learning.

2. **Genome-Behavior Distance**:
   ```
   distance = mean( |expressed_care - genome_care| + 
                    |expressed_forage - genome_forage| + 
                    |expressed_self - genome_self| )
   ```
   Decreasing distance = learned behaviors encode into genome.

**Baldwin Signal**: Distance decreases while fitness maintains → learned behavior becomes genetic.

---

## 4. Files to Modify/Create

### **4.1 `evolution/genome.py` (MODIFY)**

**Add to Genome class**:
```python
@dataclass
class Genome:
    # Existing (maintain)
    care_weight: float = 1/3
    forage_weight: float = 1/3
    self_weight: float = 1/3
    
    # NEW: Learning genes (evolvable)
    learning_rate: float = 0.05
    plasticity_coefficient: float = 0.5
    
    def mutate(self, mutation_rate: float, mutation_sigma: float) -> 'Genome':
        """Apply value mutation (parametric) per Algorithm 2.
        
        Returns: Mutated copy of genome.
        """
        # For each gene: mutate with probability mutation_rate
        # Clamp learning_rate ∈ [0.0, 0.2]
        # Clamp plasticity_coefficient ∈ [0.0, 1.0]
        # Renormalize weights (sum = 1.0)
    
    def copy(self) -> 'Genome':
        """Return exact deep copy."""
```

**Mutation Details**:
- `MutateGene(value, sigma)` = `value + N(0, sigma)` (Gaussian mutation)
- `mutation_rate` = 0.05 (5% of genes mutate per reproduction)
- `mutation_sigma` = 0.02 (standard deviation of change)

---

### **4.2 `agents/mother.py` (MODIFY)**

**Add phenotype tracking**:
```python
class MotherAgent:
    def __init__(self, config, genome):
        # ... existing code ...
        self.genome = genome
        
        # Phenotype state (what offspring inherit as starting point)
        self.expressed_care = genome.care_weight
        self.expressed_forage = genome.forage_weight
        self.expressed_self = genome.self_weight
        
        # Cost tracking
        self.lifetime_learning_cost = 0.0
```

**Add method: Modulation Signal**:
```python
def compute_modulation_signal(self) -> float:
    """Compute sparse ecological reward/penalty signal (local, embodied).
    
    Returns: Signal in [-5, 5], clipped.
    Triggers only on significant events.
    """
    # See Section 3 "Modulation Signal"
```

**Add method: Plasticity Cost**:
```python
def compute_plasticity_cost(self, modulation_signal: float) -> float:
    """Compute this frame's learning cost using reward-modulated Hebbian rule.
    
    Cost = alpha × |Δweights| + beta × plasticity_coefficient
    
    Returns: Energy cost (0 if plasticity disabled or signal=0).
    """
    # Pre-activations: sensory inputs (normalized)
    # Post-activations: expressed motivation weights
    # Hebbian delta: η × pre × post × signal
    # See Section 3 "Plasticity Cost"
```

**Modify method: step()**:
```python
def step(self):
    """Per-tick update following Algorithm 1."""
    # 1. self.age += 1
    # 2. self.energy -= metabolism_base
    # 3. perceive_world()
    # 4. choose_motivation() + TickBrain()
    # 5. signal = compute_modulation_signal()
    # 6. cost_p = compute_plasticity_cost(signal)
    #    if cost_p > 0:
    #        energy -= cost_p
    #        lifetime_learning_cost += cost_p
    #        apply_expression_noise()
    # 7. action = choose_action()
    # 8. energy -= action_cost
    # 9. execute_action()
    # (Natural selection + reproduction handled by Simulation)
```

**Add method: Reproduction with Partial Phenotype Inheritance**:
```python
def reproduce(self):
    """Asexual reproduction with mutation and partial epigenetic inheritance.
    
    Offspring genome: copy parent's genome (will be mutated)
    Offspring phenotype: partial inheritance (retention=0.15)
    """
    if self.energy < self.config.repro_threshold:
        return None
    
    # 1. Deduct reproduction cost (equals threshold)
    self.energy -= self.config.repro_threshold
    
    # 2. Clone genome
    offspring_genome = self.genome.copy()
    
    # 3. Partial phenotype inheritance
    retention = self.config.phenotype_retention  # 0.15
    offspring = MotherAgent(config=self.config, genome=offspring_genome)
    offspring.expressed_care = (offspring_genome.care_weight + 
                                retention * (self.expressed_care - offspring_genome.care_weight))
    # ... same for forage, self ...
    
    # 4. Clamp and renormalize expressed values
    offspring.expressed_care = np.clip(offspring.expressed_care, 0.0, 1.0)
    # ... clamp others ...
    # Renormalize sum = 1.0
    
    # 5. Reset cost (offspring starts clean)
    offspring.lifetime_learning_cost = 0
    
    # 6. Apply mutation if enabled
    if self.config.mutation_enabled:
        offspring.genome = offspring.genome.mutate(
            self.config.mutation_rate,
            self.config.mutation_sigma
        )
        # Renormalize genome weights
    
    return offspring
```

**Add method: Expression Noise**:
```python
def _apply_expression_noise(self):
    """Apply small random drift to expressed phenotypes.
    
    Only called when modulation_signal ≠ 0 (during learning).
    Simulates molecular noise in gene regulation.
    """
    # Add N(0, 0.01) to each expressed value
    # Clamp to [0, 1]
    # Renormalize sum = 1.0
```

---

### **4.3 `config.py` (root, MODIFY)**

**Add fields to Config dataclass**:
```python
@dataclass
class Config:
    # ... existing fields ...
    
    # Evolution flags
    mutation_enabled: bool = True
    plasticity_enabled: bool = True
    
    # Genome initialization
    init_learning_rate: float = 0.05
    init_plasticity_coefficient: float = 0.5
    phenotype_retention: float = 0.15
    
    # Mutation parameters
    mutation_rate: float = 0.05
    mutation_sigma: float = 0.02
    
    # Energy costs (separated)
    metabolism_base: float = 0.01    # Per tick base survival
    move_cost: float = 0.005         # Per action
    pick_cost: float = 0.003
    feed_cost: float = 0.001
    
    # Plasticity costs
    plasticity_alpha: float = 0.01   # Per weight change
    plasticity_maintenance_beta: float = 0.001
    
    # Reproduction
    repro_threshold: float = 0.65    # Energy required; cost = threshold
    repro_cooldown: int = 80
    
    # Population
    init_mothers: int = 15
    max_population: int = 100
    maturity_age: int = 200
    
    # Runtime
    max_ticks: int = 40_000
    sample_window: int = 200
```

---

### **4.4 `experiments/phase5_evolution/config.py` (CREATE)**

**Purpose**: Load BEST_ECOLOGICAL from Phase 4b and build Config with CLI parameters.

**Key Function**:
```python
def make_config(
    seed: int = 42,
    mutation_enabled: bool = True,
    plasticity_enabled: bool = True,
    learning_rate: float = 0.05,
    plasticity_coefficient: float = 0.5,
    phenotype_retention: float = 0.15,
    mutation_rate: float = 0.05,
    mutation_sigma: float = 0.02,
    max_ticks: int = 40_000,
    relax_ecology: bool = False,
    ecology_relaxation_factor: float = 1.15,
) -> Config:
    """Build Phase 5 config from CLI parameters.
    
    Loads BEST_ECOLOGICAL from:
      outputs/phase4_weight_sweep/BEST_ECOLOGICAL.json
    
    Or falls back to hardcoded Phase 4b calibrated values.
    """
```

---

### **4.5 `experiments/phase5_evolution/run.py` (CREATE)**

**Entry Point**: `python -m experiments.phase5_evolution.run [CLI_ARGS]`

**Core Functions**:
- `_initial_genomes(learning_rate, plasticity_coefficient)`: Create 15 mother agents with neutral genome (1/3 / 1/3 / 1/3)
- `_sample(sim, tick)`: Capture snapshot every `sample_window` ticks
- `run_one(seed, params)`: Single asynchronous evolution run
- `run_sweep(args)`: Parallel execution over multiple seeds
- `save_results(results, output_dir)`: Save to CSV (snapshots) + JSON (summary)

**CLI Arguments**:
```bash
--mutation-enabled {true|false}
--plasticity-enabled {true|false}
--learning-rate <float>           # default 0.05
--plasticity-coefficient <float>  # default 0.5
--phenotype-retention <float>     # default 0.15
--mutation-rate <float>           # default 0.05
--mutation-sigma <float>          # default 0.02
--max-ticks <int>                 # default 40000
--seeds <int>                     # default 10
--seed-start <int>                # default 42
--workers <int>                   # default 4
--relax-ecology {true|false}      # default false
--ecology-relaxation-factor <float> # default 1.15
--output-dir <str>                # auto-generated timestamp
```

**Output**:
```
outputs/phase5_evolution/
├── snapshots.csv          # Per-tick metrics across all seeds
├── summary.json           # Run metadata + all results
└── trajectories.png       # [From plot.py] Trajectory plots
```

---

### **4.6 `experiments/phase5_evolution/plot.py` (CREATE)**

**Purpose**: Visualize evolutionary trajectories and Baldwin signal.

**Plots**:
1. **Genetic Care Weight** (genome.care_weight) over ticks across seeds
2. **Expressed Care** (phenotype) over ticks
3. **Innateness Index** (1 - plasticity_coefficient) over ticks
4. **Genome-Behavior Distance** (Baldwin assimilation metric) over ticks

**Features**:
- One line per seed (alpha=0.5 transparency)
- Red dashed line at 1/3 (neutral baseline)
- Axes labeled with biological meaning
- Grid, legend, professional styling

---

## 5. Execution Flow (Per Tick)

```
for t in range(cfg.max_ticks):
    
    if t % sample_window == 0:
        snapshots.append(_sample(sim, t))
    
    # All agents update independently (asynchronous)
    for mother in sim.mothers:
        mother.step()  # Age, perceive, learn, act per Algorithm 1
    
    for child in sim.children:
        child.step()   # Age, eat, learn needs, check maturity/death
    
    # Population management
    sim.mothers = [m for m in sim.mothers if m.alive]
    sim.children = [c for c in sim.children if c.alive]
    
    # Reproduction and natural selection
    for mother in sim.mothers:
        if mother.energy > repro_threshold and mother.age > maturity_age:
            offspring = mother.reproduce()  # Mutation + partial phenotype inheritance
            if offspring:
                sim.mothers.append(offspring)
    
    # Population cap
    if len(sim.mothers) > max_population:
        # Remove weakest or random mothers
    
    sim.tick += 1
```

---

## 6. CLI Usage Examples

### Test 1: Pure Genetic Selection (No Plasticity)
```bash
python -m experiments.phase5_evolution.run \
  --mutation-enabled true \
  --plasticity-enabled false \
  --max-ticks 40000 \
  --seeds 10 \
  --output-dir ./outputs/phase5_evolution/mut_only
```

### Test 2: Baldwin Effect (Mutation + Plasticity)
```bash
python -m experiments.phase5_evolution.run \
  --mutation-enabled true \
  --plasticity-enabled true \
  --phenotype-retention 0.15 \
  --max-ticks 40000 \
  --seeds 10 \
  --output-dir ./outputs/phase5_evolution/baldwin
```

### Test 3: Plasticity Only (No Selection)
```bash
python -m experiments.phase5_evolution.run \
  --mutation-enabled false \
  --plasticity-enabled true \
  --max-ticks 40000 \
  --seeds 10 \
  --output-dir ./outputs/phase5_evolution/plasticity_only
```

### Test 4: Control (Neither)
```bash
python -m experiments.phase5_evolution.run \
  --mutation-enabled false \
  --plasticity-enabled false \
  --max-ticks 40000 \
  --seeds 10 \
  --output-dir ./outputs/phase5_evolution/control
```

### Test 5: Pilot Run (Relaxed Ecology, Short)
```bash
python -m experiments.phase5_evolution.run \
  --mutation-enabled true \
  --plasticity-enabled true \
  --max-ticks 5000 \
  --seeds 5 \
  --relax-ecology true \
  --ecology-relaxation-factor 1.2 \
  --output-dir ./outputs/phase5_evolution/pilot
```

---

## 7. Key Design Decisions (Locked)

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **CLI-driven params** | User freedom to test any combination | Requires argparse setup |
| **Partial phenotype inheritance (15%)** | Baldwinian, not Lamarckian | More complex than full inheritance |
| **Sparse modulation signals** | Interpretable, biologically realistic | May converge slower than dense rewards |
| **Expression noise only on learning** | Prevents stagnation efficiently | Adds conditional complexity |
| **Separate energy costs** | Fine-grained cost accounting | More parameters to track |
| **Value mutation only** | Focus on parameter evolution first | Defers topology exploration |
| **Global learning_rate** | Simplicity for Block 2 | Per-synapse learning deferred |
| **No explicit connection toggles** | Simpler; weights mutate to ~0 naturally | Implicit representation harder to debug |
| **Renormalize after plasticity** | Keeps motivational budget stable | Adds extra computation per tick |

---

## 8. Success Criteria & Validation

### Pilot Run (5 seeds, 5k ticks, relaxed ecology)
- [ ] No immediate extinction of all seeds
- [ ] mut_on_plast_off: population persists, some mothers alive at end
- [ ] mut_on_plast_on: shows early fitness boost compared to mut_only
- [ ] mut_off_plast_off: care_weight stays ~1/3 (no drift)
- [ ] Snapshots CSV generated without errors
- [ ] Plots render successfully

### Real Run (10 seeds, 40k ticks, Phase 4b ecology)
- [ ] At least 1 seed completes full run without extinction
- [ ] mean_care_weight rises above 1/3 in mut_on_plast_off (genetic signal)
- [ ] mut_on_plast_on shows faster early rise (Baldwin scaffold)
- [ ] innateness_index increases (genetic assimilation)
- [ ] genome_behavior_distance decreases (learned → innate)
- [ ] child_survival_rate improves over time

---

## 9. Files Checklist

**Create (New)**:
- [ ] `experiments/phase5_evolution/__init__.py` (empty module file)
- [ ] `experiments/phase5_evolution/config.py` (param builder)
- [ ] `experiments/phase5_evolution/run.py` (main runner)
- [ ] `experiments/phase5_evolution/plot.py` (visualizations)

**Modify (Existing)**:
- [ ] `evolution/genome.py` (add learning_rate, plasticity, mutate())
- [ ] `agents/mother.py` (add phenotype, modulation, cost, reproduction)
- [ ] `config.py` root (add evolution flags, energy costs)

**Reference**:
- [ ] Load `outputs/phase4_weight_sweep/BEST_ECOLOGICAL.json` in config.py
- [ ] Or use fallback Phase 4b calibrated values if JSON missing

---

## 10. Known Uncertainties (Clarified)

### Q1: Energy Cost Separation
**Decision**: `metabolism_base = 0.01` per tick (basal survival). Then action-specific costs added on top (move=0.005, pick=0.003, feed=0.001).

### Q2: Offspring Energy at Birth
**Decision**: Offspring born at full energy (1.0).

### Q3: Renormalization Timing
**Decision**: Renormalize expressed_care/forage/self after every plasticity cost deduction (when expression_noise is applied) AND after mutation.

### Q4: Innateness Index Tracking
**Decision**: Population-level averages in snapshots (mean per seed); also track per-individual for analysis.

### Q5: Partial Phenotype Inheritance Math
**Decision**: Confirmed. If parent_expressed=0.4, genome=0.2, retention=0.15:
  - offspring = 0.2 + 0.15×(0.4-0.2) = 0.2 + 0.03 = 0.23 ✓

---

## 11. Implementation Notes

### For Implementer
1. **Start with genome.py**: Add learning_rate, plasticity_coefficient, mutate() method
2. **Then mother.py**: Add phenotype tracking, modulation_signal, compute_plasticity_cost(), reproduction
3. **Then config.py root**: Add evolution flags and energy costs
4. **Then create Phase 5 files**: config builder, run.py, plot.py
5. **Test on pilot run first** (5 seeds, 5k ticks, relaxed ecology)
6. **Debug and refine**, then run real experiment

### Common Pitfalls
- **Forget genome renormalization**: Weights won't sum to 1.0 → softmax breaks
- **Plasticity cost timing**: Must be fresh per frame, not accumulated forward
- **Expression noise scope**: Only apply when learning occurs, not every tick
- **Phenotype inheritance order**: Inherit from parent BEFORE mutation, then mutate offspring
- **Cost deduction order**: Metabolism → plasticity → action (all additive)

### Testing Strategy
```bash
# Quick sanity check (1 seed, 100 ticks)
python -m experiments.phase5_evolution.run \
  --mutation-enabled true --plasticity-enabled false \
  --max-ticks 100 --seeds 1 --workers 1

# Pilot run
python -m experiments.phase5_evolution.run \
  --mutation-enabled true --plasticity-enabled true \
  --max-ticks 5000 --seeds 5 --relax-ecology true

# Real experiment
python -m experiments.phase5_evolution.run \
  --mutation-enabled true --plasticity-enabled true \
  --max-ticks 40000 --seeds 10 --workers 4
```

---

## Approval Status

**Awaiting approval from**: User (original researcher)

**Questions before implementation**:
1. Does EVO_PROPOSAL correctly summarize all decisions?
2. Are there contradictions or oversights?
3. Any adjustments to algorithms, parameters, or file structure?
4. Ready to implement?

---

## References

- **ROADMAP.md**: High-level research plan (Blocks 1-3)
- **CURRENT_STATE.md**: Phase 1-4 status and calibration values
- **PROGRESS.md**: Detailed chronology of findings
- **Thesis Algorithms**: Algorithm 1 (Asynchronous Update), Algorithm 2 (DNA Mutation)

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-10  
**Branch**: V3  
**Status**: Proposal (awaiting approval)