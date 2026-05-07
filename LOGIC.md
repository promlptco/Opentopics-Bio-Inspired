# LOGIC.md — Simulation Architecture, Code Logic & Biological Reasoning

This document is the single reference for every non-trivial design decision in the codebase. For each component it answers three questions: **what it does**, **why this design was chosen** (biological or scientific reasoning), and **what is changing** (approved architectural changes not yet coded). Read this before touching any core file.

---

## 1. Entity Hierarchy

```
Entity          ← base spatial unit (id, x, y, alive)
  └── Agent     ← adds lineage_id, generation, age, energy, hunger
        ├── MotherAgent   ← decision engine + genome + plasticity
        └── ChildAgent    ← passive signal emitter
```

### Entity (`agents/entity.py`)

Auto-incrementing `_next_id` class variable ensures every entity has a globally unique ID for the lifetime of a Python process. `move_to()` and `die()` are the only mutating methods. Position is stored as `(x, y)` integers; `pos` is a property returning the tuple.

**Why unique IDs:** The simulation uses ID-keyed dicts (`_mother_by_id`, `_child_by_id`) for O(1) lookup during care and lineage operations. Without globally unique IDs, lineage tracking would break when a dead entity is removed and a new one is created at the same list index.

### Agent (`agents/agent.py`)

Adds `lineage_id` (founding family ID), `generation` (depth from founding ancestor), `age` (ticks alive), and `energy` (0.0–1.0). Death fires when `energy <= 0`. `hunger` field exists but is only actively used by `ChildAgent`.

**Why energy, not hunger, as the death trigger for mothers:** Mothers manage their own energy through foraging and rest. A direct energy model is simpler and more interpretable than accumulating hunger then converting it to energy loss. The conversion was tried and found to be ~100× slower to cause mortality at tick 1 — effectively breaking Phase 2 calibration.

---

## 2. Genome (`evolution/genome.py`)

| Gene | Default | Biological analog |
|---|---|---|
| `care_weight` | 0.5 | Drive to respond to infant distress signals |
| `forage_weight` | 0.5 | Drive to seek and consume food |
| `self_weight` | 0.5 | Drive to self-maintain (rest, recover) |
| `learning_rate` | 0.1 | Rate of phenotypic adjustment per reward signal (plasticity speed) |
| `learning_cost` | 0.05 | Metabolic cost per unit of phenotypic change |
| `distress_sensitivity` | 0.0 | Cortisol analog: energy penalty for ignoring own infant distress |
| `care_recovery` | 0.0 | Prolactin analog: energy reward for successfully feeding own infant |

All genes are bounded `[0, 1]`. Mutation: independent Gaussian noise per gene, bounded clipping.

```python
def mutate_gene(value):
    if random.random() < mutation_rate:
        return clamp(value + gauss(0, sigma), 0.0, 1.0)
    return value
```

**Why Gaussian bounded mutation:** Small-step mutation with bounded clipping is the standard in evolutionary computation (genetic algorithms). Large jumps would cause genetic drift explosion in small populations. Bounded `[0, 1]` keeps all weights interpretable as probabilities/fractions. The `lock_learning_rate` flag (Phase 8) closes the "become a better learner" escape route so selection can only act on the genetic care floor.

**Why distress_sensitivity and care_recovery default to 0.0:** These are optional neuroendocrine analogs for later phases. Setting them to 0 leaves Phase 1–6 experiments entirely unaffected — no behavioral change until explicitly enabled.

**Fixed genome vs expressed genome (Baldwin architecture):**
- `genome.care_weight` = fixed (heritable, never modified by learning). This is the genetic component.
- `mother.expressed_care_weight` = phenotypic (modified by `plastic_update()` during lifetime). This is the learned component.
- Reproduction passes `genome` (the fixed copy). The expressed value is never inherited.
- **This is the Baldwin Effect mechanism:** if expressing high care is beneficial, selection will drive `genome.care_weight` upward over generations until the learned adjustment is no longer needed. The signature is: `expressed_care_weight` rises first (learning), then `genome.care_weight` catches up (genetic assimilation), then `learning_rate` may decline (learning no longer needed).
- Only `care_weight` has an expressed version. `forage_weight` and `self_weight` are used directly from the genome — there is no learning signal for them.

---

## 3. MotherAgent — Decision Engine (`agents/mother.py`)

### 3.1 Cue System

The motivation system is a two-stage computation:

```
Stage 1 — Environmental cues (what the environment is telling the mother):
  forage_cue = how strongly the environment demands foraging
  self_cue   = how strongly the mother's own state demands self-maintenance
  care_cue   = how strongly the environment signals a child in need

Stage 2 — Weighted utility (what the genome weights say to do about it):
  FORAGE score = genome.forage_weight × forage_cue
  SELF score   = genome.self_weight   × self_cue
  CARE score   = expressed_care_weight × care_cue
```

**Why this two-stage structure:** The genome weights are the evolvable traits — they represent the heritable *disposition* toward each behavior. The cues are the environmental signals that *activate* that disposition. Separating them makes the ecology a proper evolutionary lever: if forage_cue is flat (food always available), then forage_weight provides no selection advantage. Only when cues vary does selection on genome weights become visible. This is the "gradient sensitivity" requirement.

**Current cue functions (implemented 2026-05-04 — Changes A–J):**

| Cue | Formula | Biological meaning |
|---|---|---|
| `forage_cue` | `1 - distance_to_nearest_food / perception_radius`, clamped [0,1] | Food proximity: 1 = food at same cell, 0 = no food visible |
| `self_cue` | `1 - energy`, clamped [0,1] | Energy deficit: 1 = fully depleted, 0 = full energy |
| `care_cue` | `child.distress` only | Observable infant signal: composite of hunger + separation |

All cues are bounded [0,1]. Genome weights are the sole differentiator of action selection — no cue can structurally dominate regardless of genome values.

### 3.2 Softmax Action Selection

```python
P(a) = exp(score_a / τ) / Σ exp(score_i / τ)
```

`τ = 0.1` (configurable via `Config.softmax_tau` — Change G).

**Why Softmax, not Argmax:** Argmax produces fully deterministic, brittle agents — they will always do the same thing given the same state. Softmax with low τ approximates Argmax (probability ~0.95 for dominant action at τ=0.1) but retains stochasticity, allowing exploration and modeling naturalistic decision errors. Biologically, animals do not always perform the maximum-utility action — motivation represents a probabilistic drive, not a binary switch.

**Why τ=0.1:** Test 06 confirmed that at τ=0.1, the top action wins ~95% of the time. This matches biological observation that motivated animals strongly prefer the dominant action but occasionally deviate. τ too high = random behavior (no selection signal). τ too low = deterministic (no exploration, fragile to cue scale issues).

### 3.3 Action Execution (`simulation/simulation.py:_execute_action`)

**FORAGE:**
1. If already holding food → do nothing (motivation block suppresses forage_cue when `held_food >= 1`, so this branch should not fire when provisioned).
2. Else if on a food cell → pick up food (remove from world, `held_food += 1`).
3. Else → A* pathfind toward nearest food, move one step (energy -= move_cost, fatigue += fatigue_rate).

**Why pick-carry, not pick-eat:** FORAGE is food procurement only. Eating is deferred to SELF so that energy is consumed when the mother is actually hungry (self_cue = 1−energy is high), not immediately after picking when she may be near full. Immediate eating in FORAGE produced "eat-at-full-energy → gain wasted by cap" behaviour that inflated survival artificially. The carry mechanic also creates a realistic two-trip foraging loop: pick food (FORAGE) → deliver to child (CARE) or eat (SELF).

**SELF:**
1. If holding food (`held_food > 0`) → eat (energy += eat_gain, held_food -= 1). Self-cue fires when energy is low, so food is consumed efficiently when most needed.
2. Otherwise → `rest()` (fatigue -= rest_recovery). No direct energy gain.

Fatigue reduction feeds back into the passive fatigue drain next tick (`energy -= fatigue × fatigue_rate`), providing an indirect energy benefit.

**Why rest, not sleep/shelter:** The simulation models adult-phase behavior where the primary cost is movement fatigue. Resting reduces fatigue but doesn't directly restore energy — energy comes only from food. This preserves the trade-off: mothers can't rest their way to health, they must forage. (Note: SELF eats held food first before resting, matching Phase 2 SurvivalSimulation behaviour.)

**CARE (implemented 2026-05-04 — Change C):**
- Find nearest distressed child in commitment or visible set.
- If distance to child == 0 (same cell): feed child (energy -= feed_cost, child receives energy).
- Else: move one step toward child.

Same-cell requirement is consistent with food picking: direct resource transfer requires physical co-location. Warm behavior (passive heat, Change H) uses radius ≤ 3 and is a separate passive effect.

### 3.4 Commitment System

```python
mother.target_child_id = child_id
mother.commit_ticks    = duration   # outcome-based: up to 20 ticks (Change D)
```

When `has_commitment() is True`, the mother skips motivation sampling and executes CARE for the remaining committed ticks.

**Why commitment:** Uncommitted care means a mother might approach a child for one tick, turn away, and never actually feed. The commitment models the sustained nature of mammalian caregiving episodes (nursing, huddling). Without it, CARE events are statistically isolated ticks rather than behavioral episodes.

**Outcome-based commitment (implemented 2026-05-04 — Change D):** Duration is set to 20 ticks max. Commitment is released early when `child.hunger < 0.3` (infant is sated). This shifts from arbitrary timer to ecological outcome: a meaningful nursing episode ends when the infant is fed, not after a fixed count.

### 3.5 Plasticity — `plastic_update()`

```python
delta = genome.learning_rate × reward × plastic_gain
expressed_care_weight += delta              # bounded [0, 1]
energy -= genome.learning_cost × |delta|   # metabolic cost of learning
```

`reward` = `hunger_reduced` per care event (how much the child's hunger actually dropped). A successful feeding with large hunger reduction produces a large positive reward and a larger plastic update.

**Why hunger_reduced as reward:** This is an outcome-based reinforcement signal — the mother learns from what worked (child was actually fed and hunger dropped), not from the intention to care. If the child is not hungry and feeding does nothing, there is no reward and no plastic update. This prevents the mother from "practicing" care on a well-fed infant.

**Why learning_cost:** Phenotypic plasticity is metabolically expensive in real biology (synaptic restructuring, protein synthesis for memory consolidation). The `learning_cost` makes high-learning_rate mothers pay a per-update energy tax, creating a selection pressure against excessive plasticity once genetic instinct is sufficient. This is the assimilation pressure in the Baldwin Effect.

**Noise option (Phase 8):** `plasticity_noise_sigma > 0` adds multiplicative Gaussian noise to the reward signal. This makes learning unreliable — mothers depending on plasticity face stochastic errors. Mothers with high *genetic* care_weight are buffered (they care regardless). This is the Hinton & Nowlan (1987) mechanism that drives genetic assimilation: noisy learning → selection favors genetic encoding.

---

### 3.6 Agent Mechanism — Energy, Fatigue, and Rest Economy

The three motivations form a closed energy loop. Every action either depletes or restores energy; the balance determines which motivation wins the Softmax next tick.

**Per-tick passive depletion (`update_state()`, every tick):**
```
energy -= hunger_rate                   # fixed metabolic baseline (always)
energy -= fatigue × fatigue_rate        # proportional drain from accumulated tiredness
```
`fatigue` (0–1) is not merely a movement counter — it is an active metabolic cost. An agent that moves repeatedly accumulates fatigue, which then drains energy every subsequent tick even while standing still. This creates sustained ecological pressure toward SELF selection after any burst of movement or care.

**Movement cost (per step, any motivated move):**
```
energy  -= move_cost      # immediate cost of each step
fatigue += fatigue_rate   # tiredness accumulates per step
```
`move_cost` is charged uniformly on every step that results in a position change, regardless of which motivation drove the step:

| Motivation | Move condition | move_cost charged |
|---|---|---|
| FORAGE | no food held, not on food cell → step toward food | Yes |
| CARE | not at same cell as child → step toward child | Yes |
| SELF | rest in place (no movement) | **No** |

SELF never moves. The only path to energy recovery is standing still.

**SELF action — rest (`rest()`):**
```
fatigue -= rest_recovery   # tiredness decreases only — no direct energy change
```
REST reduces fatigue, which in turn reduces the passive fatigue drain next tick (`energy -= fatigue × fatigue_rate`). This is an **indirect** energy benefit — not a direct restoration. Agents cannot rest their way to survival; they must forage to replenish energy. This keeps food density as the primary survival lever.

**Why no direct energy from REST:** If REST restored energy directly at rate R, and `R ≥ hunger_rate`, agents could survive indefinitely without food — making `init_food`, `eat_gain`, and `move_cost` irrelevant. This collapses the entire foraging ecology into a single threshold. Keeping REST as fatigue-management only preserves the gradient sensitivity required for Phase 2.

**Closed-loop summary:**

| Event | fatigue | energy | effect on self_cue |
|---|---|---|---|
| Any move step (FORAGE or CARE) | ↑ +fatigue_rate | ↓ −move_cost | ↑ rises (indirectly) |
| Per tick (passive fatigue drain) | — | ↓ −fatigue×fatigue_rate | ↑ rises |
| Per tick (hunger baseline) | — | ↓ −hunger_rate | ↑ rises |
| SELF (rest) | ↓ −rest_recovery | — (indirect only) | ↓ falls slowly via reduced drain |
| Eat held food (SELF) | — | ↑ +eat_gain | ↓ falls |

**Why this design:** Energy can only be gained by eating. Every other action either drains or manages the drain rate. `rest_recovery` controls how quickly fatigue resets between movement bursts — it is a **mobility recovery** parameter, not an energy parameter. Its evolutionary relevance is speed of recovery between foraging trips, not survival without food.

---

## 4. ChildAgent — Passive Signal Emitter (`agents/child.py`)

```python
child.energy    ∈ [0, 1]   # metabolic reserve; depleted at hunger_rate per tick
child.hunger    = 1 - energy  # derived inverse: 0 = full, 1 = dead (energy = 0)
child.separation ∈ [0, 1]  # normalized distance to mother (tracked but not in distress formula)
child.distress  = hunger    # hunger-only: distress = 1 - energy  [Fixed 2026-05-07]
```

**Death:** `energy <= 0` → starvation. Identical to mother death condition. `hunger` is a derived metric — it is NOT tracked independently.

**Distress is hunger-only (fixed 2026-05-07):** The original formula `distress = (hunger + separation) / 2` included separation — the normalized distance from infant to mother. This was removed because immobile infants cannot signal separation agency; separation reflects the mother moving to forage, not the infant's metabolic state. With the old formula, a well-fed but distant infant had artificially elevated distress (up to 0.5 from separation alone), pulling mothers back toward care even when no feeding was needed. The fix: `distress = hunger = 1 − energy`. `child.separation` is still computed and stored (for logging and potential Phase 5+ warmth extensions) but is no longer part of the distress signal.

**Warm behavior (warmth_factor > 0, Phase 5+ only):** When active, maternal proximity reduces neonatal metabolic cost:
```python
warmth_proximity = max(0.0, 1.0 - dist_to_mother / warmth_radius)
hunger_rate *= (1.0 - warmth_factor * warmth_proximity)
```
With the hunger-only distress formula, warmth now reduces distress through a single path: lower hunger_rate → slower energy depletion → lower hunger → lower distress. `warmth_factor = 0.0` in all Phase 3/4 experiments (locked off).

**Why the mother reads distress, not hunger directly:** Biologically, a mother cannot observe her infant's internal metabolic state. She can only observe behavioral signals: vocalization intensity, postural cues, activity level. `distress` is this observable signal. Reading `child.hunger` directly would mean the mother has metabolic telepathy — it violates the ecological realism requirement.

**Infant starvation multiplier:** `hunger_rate × infant_starvation_multiplier` for infants (`age < maturity_age`). Default: 1.0. Phase 5 setting: ~2.33 (infants hunger ~2.33× faster than adults).

**Why a multiplier, not a separate infant hunger_rate:** The multiplier preserves the same parameter space as the adult ecology so that Phase 2 baseline (hunger_rate=0.0286) transfers cleanly to Phase 5. The multiplier makes the infant's B (benefit of care) existential — without care, the infant starves in 15 days instead of 35 days. This transforms care from marginally helpful to necessary for survival, which is the ecological condition that makes Hamilton's rule favor caregiving.

**Maturation:** At `age >= maturity_age`, the child is converted to a new MotherAgent at the same cell, inheriting the child's genome. The child entity is removed from the world before the mother entity is placed, so the position is free.

---

## 5. Lineage & Relatedness (`evolution/lineage.py`)

```python
r = 2^(-d)    where d = |child_gen - mother_gen|
```

- Same lineage_id, d=1 (parent-child): r = 0.5
- Same lineage_id, d=2 (grandparent-grandchild): r = 0.25
- Different lineage_id: r = 0.0 (unrelated by default)

**Why r = 2^(-d):** This is Hamilton's (1964) relatedness coefficient for diploid sexual organisms where gene sharing probability halves each generation. In this haploid-analog simulation, the same formula gives the expected gene-sharing fraction between a mother and descendants of known depth.

**Why lineage_id tracks founding family, not individual pedigree:** The simulation starts with `init_mothers` founding mothers, each assigned `lineage_id = i`. All their descendants share that lineage_id. Cross-lineage relatedness is assumed 0.0 — different founding families are treated as genetically unrelated. This is an approximation valid early in the simulation; in very long runs (many generations), distant lineages could share genetic material through convergent mutation, but the probability is negligible given sigma=0.05.

**Why pedigree is preserved through maturation:** When a child matures into a new mother, `lineage.parents[new_mother.id] = child.mother_id`. This preserves the pedigree chain so `get_relatedness()` correctly computes the generation distance of the now-adult agent relative to her own offspring. Without this, the maturation event would break the lineage chain and make all subsequent care events appear unrelated (r=0.0).

---

## 6. Simulation Loop (`simulation/simulation.py:step()`)

Order per tick:

1. **Food replenishment:** Burst-spawn food if `food_count < init_food × threshold_ratio`. Optional continuous trickle.
2. **Update children:** hunger += hunger_rate (×multiplier if infant), update separation and distress, tick age, check death.
3. **Shuffle mothers:** randomize order to prevent first-in-list advantage.
4. **Update each mother:** deduct hunger_rate, tick age, enforce mother_max_age, tick commitment. Then: perceive visible children → choose motivation (or continue commitment) → execute action → check death.
5. **Maturation:** convert any child with `age >= maturity_age` to a new MotherAgent.
6. **Reproduction:** any eligible mother spawns a child.
7. **Cleanup:** log deaths, clear stale `own_child_id` references, remove dead entities from lists and ID dicts.

**Why shuffle mothers:** Without shuffling, early-listed mothers would always act before later-listed mothers when food is scarce. This creates a systematic order bias — mothers near index 0 would survive longer purely because they always get first access to food. Shuffling each tick ensures all mothers experience fair, random priority across the simulation.

**Why children update before mothers:** Children's distress is computed before mothers decide. This ensures the distress signal the mother sees is current (updated this tick) rather than lagged by one tick. Biologically: the infant cries, then the mother responds.

**Why cleanup is at the end:** Entity references (e.g., `mother.target_child_id`) may point to a child that died earlier in the same tick. If cleanup happened mid-step, a mother could lose her committed target mid-action. End-of-tick cleanup ensures all actions in the current tick resolve against a consistent world state.

**Distress_sensitivity (Option A — cortisol analog):** If a mother chose FORAGE or SELF while her own child is alive, nearby, and distressed, she pays `distress_sensitivity × child.distress` energy per tick. This makes non-care costly when care is ecologically needed, selecting for both `care_weight` and `distress_sensitivity` rising together. Disabled by default (`distress_sensitivity = 0.0`).

---

## 7. World & Pathfinding (`simulation/world.py`, `simulation/pathfinding.py`)

### GridWorld

- `food_positions: set[(x, y)]` — food does not occupy an agent cell; food and entities can coexist at the same position.
- `occupied: set[(x, y)]` — entity collision set. Two entities cannot share a cell.
- `get_distance()` = **Chebyshev distance**: `max(|dx|, |dy|)`

**Why Chebyshev:** The grid allows 8-directional movement (N, NE, E, SE, S, SW, W, NW). In Chebyshev metric, moving diagonally costs the same as moving cardinally — one step moves you by 1 in the Chebyshev sense regardless of direction. This correctly matches the movement cost model: `move_cost` is charged once per step regardless of direction. Euclidean distance would underestimate true path length for diagonal movement.

### A* with Octile Heuristic

```
h(n) = max(|dx|, |dy|) + (√2 - 1) × min(|dx|, |dy|)
```

This is the admissible heuristic for 8-directional grids where diagonal cost = √2. The octile heuristic never overestimates the true cost, guaranteeing that A* finds the shortest path.

**Why A*, not BFS or greedy:** BFS expands all neighbors equally and is O(V) regardless of goal distance. Greedy best-first is fast but not optimal. A* with octile heuristic is optimal and efficient for the 50×50 grid (~2500 cells), typically expanding far fewer nodes than BFS in open areas.

**Why not Euclidean distance as heuristic:** Euclidean distance on an 8-directional grid is inadmissible — it underestimates cost for paths that must go around obstacles, causing suboptimal paths. Octile is the correct admissible heuristic for this movement model.

---

## 8. Logging System (`logging_system/`)

Four record types logged per simulation:

| Record | When | Key fields |
|---|---|---|
| `ChoiceRecord` | Whenever a distressed child (distress ≥ 0.3) is visible | tick, mother_id, winner_domain, candidate r-values, candidate distress values |
| `CareRecord` | On every feed attempt | r, benefit (hunger_reduced), cost (energy spent), is_own_child |
| `BirthRecord` | Every birth | mother genome snapshot, generation, lineage |
| `DeathRecord` | Every death | cause (starvation/hunger/matured), generation, lineage |

**Why only log when distress ≥ 0.3:** Recording every tick for every mother-child pair produces enormous logs. Distress ≥ 0.3 is a meaningful threshold: a child is moderately hungry or separated. Below this, the care signal is too weak to be analytically interesting. This threshold controls log size without losing the scientifically relevant events.

**Why log r, benefit, and cost in CareRecord:** These are the three variables needed for Hamilton's Rule analysis (`rB − C`). Without logging them at event time, post-hoc analysis would require reconstructing the simulation state from scratch. The logging system makes offline analysis self-contained from the CSV.

---

## 9. Configuration System (`config.py`)

Root `Config` dataclass is the single source of truth for all default parameters. Each phase has its own `config.py` that imports `Config` and overrides only the parameters relevant to that phase. This ensures:
- All other parameters stay at validated defaults.
- CLI overrides work on any phase without modifying source.
- Changing a default in the root Config propagates to all phases automatically.

**Phase-specific config pattern:**
```python
# experiments/phase2/config.py
from config import Config
PHASE2_CONFIG = Config(
    max_ticks=10_000,
    init_mothers=20,
    # ... only what's different for this phase
)
```

**CLI override pattern (via run.py):**
```
python experiments/phase2/run.py --max_ticks 5000 --seed 99
```

**Mode flags (`children_enabled`, `care_enabled`, `plasticity_enabled`, `reproduction_enabled`, `mutation_enabled`):** These gate entire subsystems. Phase 1 mechanics tests disable most flags. Phase 2 disables children and care. Phase 3 enables children and care. This ensures each phase tests only what it claims to test, with no contamination from unused subsystems.

---

## 10. Architectural Changes — Implemented 2026-05-04

All ten changes below were approved and implemented in session 2026-05-04. This section documents what was changed and why. These are now the active defaults in `config.py`, `agents/mother.py`, `simulation/world.py`, and `simulation/simulation.py`.

### A. Grid size: 30×30 → 50×50 ✅ Implemented
`Config.width = 50`, `Config.height = 50`. **Why:** 30×30 = 900 cells for 12+ mothers + children + food tiles. At realistic food densities, crowding artificially concentrates agents and inflates encounter rates. 50×50 = 2500 cells gives proper spatial separation. All phases must use 50×50.

### B. Neutral demand-signal cues ✅ Implemented
All cue functions in `agents/mother.py` replaced with neutral [0,1] signals:
- `forage_cue` = `1 - (distance_to_nearest_food / perception_radius)`, clamped [0,1]
- `self_cue` = `1 - energy`, clamped [0,1]
- `care_cue` = `child.distress` only (never reads `child.hunger` directly)

**Why:** Scale asymmetry biases action selection independent of genome weights. Neutral [0,1] cues make genome weights the *sole* differentiator — the scientific requirement.

### C. Feed requires same-cell proximity (dist == 0) ✅ Implemented
`feed_child()` guard changed from `dist != 1` to `dist > 1` (allows dist 0 or 1; 0 triggers feed). Children placed as non-blocking (`world.place_entity(child, blocking=False)`) so mothers can walk onto a child's cell. **Why:** Direct resource transfer requires physical co-location, consistent with food-pick mechanic.

### D. Outcome-based commitment ✅ Implemented
`commit_ticks = 20` (was `randint(3, 5)`). Released early when `child.hunger < 0.3`. **Why:** Nursing episodes in mammals last until the infant is sated, not for an arbitrary fixed count.

### E. Sigmoid reproduction gate ✅ Implemented
```python
P(reproduce) = 1 / (1 + exp(-(energy - 0.85) / 0.05))
```
Midpoint at energy=0.85. At energy=1.0: P≈0.95. At energy=0.7: P≈0.05. `has_reproduced` flag (Change F) still checked first. **Why:** Reproduction probability-proportional to energy condition — body condition determines fertility.

### F. One child per lifetime ✅ Implemented
`has_reproduced: bool = False` added to `MotherAgent.__init__`. Set `True` after first reproduction. Checked in `can_reproduce()` before sigmoid evaluation. **Why:** Scopes study to dyadic mother-infant bonds. Multi-child dynamics would confound the care analysis.

### G. Softmax tau, mutation_rate, mutation_sigma into Config ✅ Implemented
`Config.softmax_tau = 0.1`, `Config.mutation_rate = 0.1`, `Config.mutation_sigma = 0.05`. Simulation passes these to `choose_motivation(tau=self.config.softmax_tau)` and `genome.mutate(mutation_rate=..., sigma=...)`. **Why:** Evolutionary hyperparameters must be config-file visible and CLI-overridable.

### H. Warm behavior (spatial thermoregulation) ✅ Implemented (locked off Phase 3/4)
`Config.warmth_radius = 3`, `Config.warmth_factor = 0.0` (default in root `config.py`; was 0.3 at initial implementation, updated to 0.0 before Phase 3 to prevent confounding ecology — reserved for Phase 5+ spatial ecology experiments). Applied in child update loop before `update_hunger()`:
```python
warmth_proximity = max(0.0, 1.0 - dist_to_mother / warmth_radius)
hunger_rate *= (1.0 - warmth_factor * warmth_proximity)
```
Passive spatial effect — no separate WARM action. **Why:** Mammalian infants cannot thermoregulate; maternal proximity reduces neonatal metabolic cost, making proximity itself a care benefit (B).

### I. Time convention: 5 ticks = 1 day ✅ Implemented
`Config.maturity_age = 200` (40 days), `Config.mother_max_age = 400` (80 days). **Why:** Small mammal analogs scaled to cover many complete generations within 10,000-tick evolution runs.

### J. Derived ecological parameters ✅ Implemented
```
Config.initial_energy = 1.0
Config.hunger_rate    = 1/35 ≈ 0.0286  (adult starves in 35 ticks without food)
Config.infant_starvation_multiplier = 35/15 ≈ 2.33  (infant starves in ~15 ticks without care)
```
**Why:** The starvation boundary must be fixed before sweeping food parameters. Without a fixed survival window, the energy-parameter sweep has no interpretable anchor. Note: at 5 ticks/day, 35 ticks = 7 days adult survival window; 15 ticks ≈ 3 days infant survival window without any care.

---

## 11. Output & Folder Convention

```
experiments/
  phaseN_<name>/
    config.py      ← phase-specific Config subclass
    run.py         ← CLI entrypoint (--headless/--live/--seed etc.)
    *.py           ← phase-specific scripts

outputs/
  phaseN_<name>/
    <run_id>/      ← timestamps or test IDs, mirrors experiments/ naming
      results.csv
      summary.json
      plots/
        *.png
```

Each run saves all outputs to its timestamped folder. REPORT.md is updated with findings after each phase completes. No phase is considered done until both (a) result files exist on disk and (b) the REPORT.md section for that phase has been written.
