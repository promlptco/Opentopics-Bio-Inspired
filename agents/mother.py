from __future__ import annotations

from typing import TYPE_CHECKING
import random
import numpy as np

from agents.agent import Agent
from evolution.genome import Genome

if TYPE_CHECKING:
    from agents.child import ChildAgent
    from simulation.world import GridWorld


# Global Softmax temperature.
SOFTMAX_TAU: float = 0.1

BASE_FORAGE_CUE: float = 0.10
BASE_SELF_CUE: float = 0.05
BASE_CARE_CUE: float = 0.00


def softmax_probs(scores: dict[str, float], tau: float = SOFTMAX_TAU) -> dict[str, float]:
    """
    Return Gibbs/Softmax probability for each key.

    P(a) = exp(u_a / tau) / sum(exp(u_i / tau))

    Numerically stable:
    subtract max before exp to prevent overflow.
    """
    keys = list(scores.keys())
    vals = np.array([scores[k] for k in keys], dtype=float)

    if tau <= 0:
        best = keys[int(np.argmax(vals))]
        return {k: 1.0 if k == best else 0.0 for k in keys}

    shifted = vals / tau - np.max(vals / tau)
    exp_vals = np.exp(shifted)
    probs = exp_vals / exp_vals.sum()

    return {k: float(p) for k, p in zip(keys, probs)}


class MotherAgent(Agent):
    def __init__(self, x: int, y: int, lineage_id: int, generation: int, genome: Genome):
        super().__init__(x, y, lineage_id, generation)

        self.genome: Genome = genome
        self.expressed_care_weight: float = genome.care_weight
        self.expressed_forage_weight: float = genome.forage_weight
        self.expressed_self_weight: float = genome.self_weight
        self._renormalize_expressed_weights()

        self.stress: float = 0.0
        self.fatigue: float = 0.0
        self.held_food: int = 0

        self.own_child_id: int | None = None
        self.cooldown: int = 0
        self.has_reproduced: bool = False  # one-child-per-lifetime (Change F)

        self.target_child_id: int | None = None
        self.commit_ticks: int = 0

        self.pending_move_cost: float = 0.0
        self.last_pos: tuple[int, int] | None = None
        self.last_motivation: str = "FORAGE"
        self.last_action: str = "NONE"
        self.last_learning_domain: str | None = None
        self.last_learning_delta: float = 0.0
        self.lifetime_learning_cost: float = 0.0
        self.lifetime_update_learning_cost: float = 0.0
        self.lifetime_maintenance_cost: float = 0.0
        self.lifetime_care_learning_cost: float = 0.0
        self.lifetime_forage_learning_cost: float = 0.0
        self.lifetime_self_learning_cost: float = 0.0
        self.total_children: int = 0
        self.matured_children: int = 0

    def _renormalize_expressed_weights(self) -> None:
        total = (
            max(0.0, self.expressed_care_weight)
            + max(0.0, self.expressed_forage_weight)
            + max(0.0, self.expressed_self_weight)
        )
        if total <= 0.0:
            self.expressed_care_weight = 1 / 3
            self.expressed_forage_weight = 1 / 3
            self.expressed_self_weight = 1 / 3
            return
        self.expressed_care_weight = max(0.0, self.expressed_care_weight) / total
        self.expressed_forage_weight = max(0.0, self.expressed_forage_weight) / total
        self.expressed_self_weight = max(0.0, self.expressed_self_weight) / total

    def get_expressed_vector(self) -> tuple[float, float, float]:
        return (
            self.expressed_care_weight,
            self.expressed_forage_weight,
            self.expressed_self_weight,
        )

    def get_genome_vector(self) -> tuple[float, float, float]:
        total = (
            max(0.0, self.genome.care_weight)
            + max(0.0, self.genome.forage_weight)
            + max(0.0, self.genome.self_weight)
        )
        if total <= 0.0:
            return (1 / 3, 1 / 3, 1 / 3)
        return (
            max(0.0, self.genome.care_weight) / total,
            max(0.0, self.genome.forage_weight) / total,
            max(0.0, self.genome.self_weight) / total,
        )

    def genome_behavior_distance(self) -> float:
        """Return total-variation distance between genome and expressed simplex."""
        expressed = self.get_expressed_vector()
        genome = self.get_genome_vector()
        return 0.5 * sum(abs(e - g) for e, g in zip(expressed, genome))

    # ============================================================
    # Tracking Movement Cost
    # ============================================================

    def add_move_cost(self, cost: float) -> None:
        self.pending_move_cost += cost

    def get_total_cost(self, feed_cost: float) -> float:
        total = self.pending_move_cost + feed_cost
        self.pending_move_cost = 0.0
        return total

    # ============================================================
    # Commitment
    # ============================================================

    def set_target(self, child_id: int, duration: int = 2) -> None:
        # Outcome-based commitment: up to 20 ticks (4 days). Cleared early when
        # child.hunger < 0.3 (sated) — see simulation._execute_action (Change D).
        self.target_child_id = child_id
        self.commit_ticks = duration

    def tick_commit(self) -> None:
        if self.commit_ticks > 0:
            self.commit_ticks -= 1
        else:
            self.target_child_id = None

    def has_commitment(self) -> bool:
        return self.commit_ticks > 0 and self.target_child_id is not None

    # ============================================================
    # Legacy genome-only motivation methods
    # ============================================================
    # These are kept for backward compatibility.
    # New Phase 2 / Phase 3 code should prefer compute_motivation_scores().

    def calc_care_score(self, child: ChildAgent) -> float:
        # care_recovery (prolactin analog) boosts care motivation for own infant only —
        # consistent with kin-selective neuroendocrine drive in real mammals.
        effective_weight = self.expressed_care_weight
        if self.own_child_id is not None and child.id == self.own_child_id:
            effective_weight = min(1.0, effective_weight + self.genome.care_recovery)
        return effective_weight * child.distress

    def calc_forage_motivation(self) -> float:
        return self.expressed_forage_weight * (1.0 - self.energy)

    def calc_self_motivation(self) -> float:
        return self.expressed_self_weight * (self.stress + self.fatigue) / 2.0

    def choose_domain(self, visible_children: list[ChildAgent]) -> str:
        """
        Legacy domain selection.

        This uses genome-only internal drives:
          CARE    = care_weight * child.distress
          FORAGE  = forage_weight * (1 - energy)
          SELF    = self_weight * (stress + fatigue) / 2

        Kept for old phases. New survival experiments should use
        choose_motivation(), which combines genome weights with
        environmental cues.
        """
        m_care = 0.0
        if visible_children:
            m_care = max(self.calc_care_score(c) for c in visible_children)

        m_forage = self.calc_forage_motivation()
        m_self = self.calc_self_motivation()

        scores = {"care": m_care, "forage": m_forage, "self": m_self}
        probs = softmax_probs(scores)

        keys = list(probs.keys())
        weights = [probs[k] for k in keys]

        chosen_idx = np.random.choice(len(keys), p=weights)
        return keys[chosen_idx]

    def choose_child(self, visible_children: list[ChildAgent]) -> ChildAgent | None:
        if not visible_children:
            return None
        return max(visible_children, key=lambda c: self.calc_care_score(c))

    # ============================================================
    # New synthesis motivation logic
    # ============================================================

    def compute_forage_cue(
        self,
        perception_radius: float,
        nearest_food: tuple[int, int] | None = None,
        distance_to_food: float | None = None,
    ) -> float:
        """Neutral FORAGE cue bounded [0, 1] (Change B).

        forage_cue = 1 - dist_to_nearest_food / perception_radius
        0 = no food visible; 1 = food at same cell.
        Scale asymmetry removed: genome weights are now the sole differentiator.
        """
        if perception_radius <= 0:
            perception_radius = 1.0
        if nearest_food is None or distance_to_food is None:
            # Empty-handed mothers retain a small exploratory forage drive even when
            # no food is currently visible. Carrying food still suppresses FORAGE.
            return 0.0 if self.held_food >= 1 else BASE_FORAGE_CUE
        return float(max(0.0, min(1.0, 1.0 - distance_to_food / perception_radius)))

    def compute_self_cue(self) -> float:
        """Neutral SELF cue bounded [0, 1] (Change B).

        SELF maps to two different maintenance actions:
          - EAT when the mother is already carrying food
          - REST when she is not

        Hunger should only drive SELF when eating is actually feasible. Otherwise
        SELF should reflect fatigue, since REST only reduces fatigue and does not
        restore energy.
        """
        if self.held_food > 0:
            return float(max(0.0, 1.0 - self.energy))
        return float(max(0.0, min(1.0, self.fatigue)))

    def compute_care_cue(self, child: ChildAgent | None, heard_distress: float | None = None) -> float:
        """Neutral CARE cue = child.distress, bounded [0, 1] (Change B).

        Mother cannot observe child's internal hunger directly — only the composite
        behavioural signal (distress = (hunger + separation) / 2) is observable.
        This removes the magic-constant 60/40 weighting and the direct hunger read.
        """
        if child is None or not child.alive:
            return 0.0
        return heard_distress if heard_distress is not None else float(child.distress)

    def compute_motivation_scores(
        self,
        perception_radius: float,
        child: ChildAgent | None = None,
        nearest_food: tuple[int, int] | None = None,
        distance_to_food: float | None = None,
        care_enabled: bool = True,
        heard_care_distress: float | None = None,
    ) -> dict[str, float]:
        """Unified motivation scoring: normalised_weight × neutral_cue.

        Weights are normalised by their sum before multiplying by cues so that
        each effective weight is a fraction of the motivation budget (sum = 1.0).
        This makes weight values scale-invariant: only ratios matter, genomes
        cannot inflate without changing behaviour, and plots are interpretable.

        effective_FORAGE = (forage_weight / W) × forage_cue   ∈ [0, 1]
        effective_SELF   = (self_weight   / W) × self_cue     ∈ [0, 1]
        effective_CARE   = (care_weight   / W) × child.distress ∈ [0, 1]

        where W = forage_weight + self_weight + care_weight (active domains only).
        """
        forage_cue = self.compute_forage_cue(
            perception_radius=perception_radius,
            nearest_food=nearest_food,
            distance_to_food=distance_to_food,
        )
        self_cue = self.compute_self_cue()

        fw = max(0.0, self.expressed_forage_weight)
        sw = max(0.0, self.expressed_self_weight)
        cw = max(0.0, self.expressed_care_weight) if care_enabled else 0.0

        w_total = fw + sw + cw
        if w_total <= 0.0:
            w_total = 1.0  # degenerate guard: avoid division by zero

        scores = {
            "FORAGE": (fw / w_total) * forage_cue,
            "SELF":   (sw / w_total) * self_cue,
        }

        if care_enabled:
            care_cue = self.compute_care_cue(child=child, heard_distress=heard_care_distress)
            scores["CARE"] = (cw / w_total) * care_cue

        return scores

    def choose_motivation(
        self,
        perception_radius: float,
        tau: float = SOFTMAX_TAU,
        child: ChildAgent | None = None,
        nearest_food: tuple[int, int] | None = None,
        distance_to_food: float | None = None,
        care_enabled: bool = True,
        heard_care_distress: float | None = None,
    ) -> tuple[str, dict[str, float], dict[str, float]]:
        """Choose motivation via softmax over neutral cue scores. Returns (action, scores, probs)."""
        scores = self.compute_motivation_scores(
            perception_radius=perception_radius,
            child=child,
            nearest_food=nearest_food,
            distance_to_food=distance_to_food,
            care_enabled=care_enabled,
            heard_care_distress=heard_care_distress,
        )

        probs = softmax_probs(scores, tau=tau)
        keys = list(probs.keys())
        chosen = np.random.choice(keys, p=[probs[k] for k in keys])
        return str(chosen), scores, probs

    # ============================================================
    # Action helpers
    # ============================================================

    def move_toward(self, target_pos: tuple[int, int], world: GridWorld) -> float:
        new_pos = world.get_step_toward(self.pos, target_pos)
        self.move_to(*new_pos)
        return 0.01

    def pick_food(self, world: GridWorld) -> bool:
        if self.pos in world.food_positions:
            world.remove_food(*self.pos)
            self.held_food += 1
            return True
        return False

    def eat(self, eat_gain: float) -> None:
        if self.held_food > 0:
            self.held_food -= 1
            self.energy = min(1.0, self.energy + eat_gain)

    def feed_child(self, child: ChildAgent, feed_cost: float, world: GridWorld, eat_gain: float = 0.25) -> tuple[bool, float]:
        """Feed child at same cell (dist == 0). Change C: same-cell proximity required.

        Children are non-blocking (placed with blocking=False in world), so the mother
        can move onto the child's cell. feed_child() guards dist > 1 so that any
        residual dist-1 approach step cannot trigger a premature feed.

        eat_gain must equal Config.eat_gain — one food unit delivers the same energy
        to a child as it does to an adult. Callers must pass self.config.eat_gain.
        Requires held_food > 0: one food entity delivers one feed (energy conservation).
        """
        dist = world.get_distance(self.pos, child.pos)
        if dist > 1:
            return False, 0.0
        if self.held_food <= 0:
            return False, 0.0
        self.held_food -= 1
        self.energy -= feed_cost
        hunger_reduced = child.receive_food(eat_gain)
        return True, hunger_reduced

    def rest(self, rest_recovery: float) -> None:
        self.fatigue = max(0.0, self.fatigue - rest_recovery)

    # ============================================================
    # Reproduction
    # ============================================================

    def can_reproduce(self, threshold: float = 0.85) -> bool:
        """Sigmoid reproduction gate (Change E) + one-child-per-lifetime (Change F).

        P(reproduce) = 1 / (1 + exp(-(energy - threshold) / 0.05))
        At threshold=0.85: P=0.50.  At energy=1.0: P≈0.95.  At energy=0.70: P≈0.05.
        Blocking conditions (own_child, cooldown, has_reproduced) are deterministic.
        """
        import math
        if self.own_child_id is not None or self.cooldown > 0 or self.has_reproduced:
            return False
        p = 1.0 / (1.0 + math.exp(-(self.energy - threshold) / 0.05))
        return random.random() < p

    def tick_cooldown(self) -> None:
        if self.cooldown > 0:
            self.cooldown -= 1

    # ============================================================
    # Plasticity
    # ============================================================

    def _record_learning_cost(self, domain: str, cost: float, is_maintenance: bool = False) -> None:
        if cost <= 0.0:
            return
        self.lifetime_learning_cost += cost
        if is_maintenance:
            self.lifetime_maintenance_cost += cost
            return
        self.lifetime_update_learning_cost += cost
        if domain == "CARE":
            self.lifetime_care_learning_cost += cost
        elif domain == "FORAGE":
            self.lifetime_forage_learning_cost += cost
        elif domain == "SELF":
            self.lifetime_self_learning_cost += cost

    def apply_plasticity_maintenance_cost(self, plasticity_beta: float) -> float:
        """Charge the ongoing metabolic burden of remaining plastic."""
        beta = max(0.0, plasticity_beta)
        coefficient = max(0.0, self.genome.plasticity_coefficient)
        cost = beta * coefficient
        if cost <= 0.0:
            return 0.0
        self.energy -= cost
        self._record_learning_cost("MAINTENANCE", cost, is_maintenance=True)
        return cost

    def plastic_update_domain(
        self,
        domain: str,
        reward: float,
        plastic_gain: float,
        energy_cost: float = 0.0,
        noise_sigma: float = 0.0,
        metabolic_alpha: float | None = None,
    ) -> None:
        domain = domain.upper()
        if domain not in {"CARE", "FORAGE", "SELF"}:
            raise ValueError(f"Unknown plasticity domain: {domain}")

        if noise_sigma > 0.0:
            reward = reward * max(0.0, 1.0 + random.gauss(0, noise_sigma))
        sensitivity = max(0.0, self.genome.update_sensitivity)
        coefficient = max(0.0, self.genome.plasticity_coefficient)
        delta = self.genome.learning_rate * coefficient * sensitivity * reward * plastic_gain

        if domain == "CARE":
            self.expressed_care_weight = max(0.0, self.expressed_care_weight + delta)
        elif domain == "FORAGE":
            self.expressed_forage_weight = max(0.0, self.expressed_forage_weight + delta)
        else:
            self.expressed_self_weight = max(0.0, self.expressed_self_weight + delta)
        self._renormalize_expressed_weights()

        alpha = self.genome.learning_cost if metabolic_alpha is None else metabolic_alpha
        cost = alpha * abs(delta) + energy_cost
        self.energy -= cost
        self.last_learning_domain = domain
        self.last_learning_delta = delta
        self._record_learning_cost(domain, cost)

    def plastic_update(
        self,
        reward: float,
        plastic_gain: float,
        energy_cost: float = 0.0,
        noise_sigma: float = 0.0,
        metabolic_alpha: float | None = None,
    ) -> None:
        """Backward-compatible alias for care-domain learning."""
        self.plastic_update_domain(
            domain="CARE",
            reward=reward,
            plastic_gain=plastic_gain,
            energy_cost=energy_cost,
            noise_sigma=noise_sigma,
            metabolic_alpha=metabolic_alpha,
        )

    def compute_modulation_signal(
        self,
        child_nearby: bool = False,
        feed_success: bool = False,
        critical_hunger: bool = False,
        child_matured: bool = False,
        mother_died: bool = False,
    ) -> float:
        """Compute a sparse ecological modulation signal for plasticity updates.

        Only one event fires per tick (priority order: child_matured >
        feed_success > child_nearby > critical_hunger > mother_died).
        Signal is clipped to [-5.0, 5.0].

        Args:
            child_nearby: Child is within perception range this tick.
            feed_success: A successful feed event occurred this tick.
            critical_hunger: Own child has energy < 0.3 this tick.
            child_matured: Own child reached maturity this tick (+5.0).
            mother_died: Mother death signal (handled at simulation level).

        Returns:
            Scalar reward/penalty in [-5.0, 5.0]; 0.0 means no event fired.
        """
        if child_matured:
            return 5.0
        if feed_success:
            return 1.0
        if child_nearby:
            return 0.2
        if critical_hunger:
            return -0.5
        if mother_died:
            return -1.0
        return 0.0

    def compute_plasticity_cost(
        self,
        signal: float,
        plasticity_alpha: float = 0.01,
        plasticity_beta: float = 0.001,
    ) -> float:
        """Compute the energy cost of one plasticity learning step.

        Cost formula: alpha × |Δweights| + beta × plasticity_coefficient.
        Returns 0.0 immediately when signal is zero (no learning occurred).

        Args:
            signal: Modulation signal from compute_modulation_signal().
            plasticity_alpha: Cost coefficient per unit of weight change.
            plasticity_beta: Maintenance cost per unit of plasticity.

        Returns:
            Non-negative energy cost for this tick's learning event.
        """
        if signal == 0.0:
            return 0.0

        cost = (
            plasticity_alpha * abs(self.last_learning_delta)
            + plasticity_beta * max(0.0, self.genome.plasticity_coefficient)
        )
        return float(cost)

    # ============================================================
    # State update
    # ============================================================

    def update_state(self, hunger_rate: float, fatigue_rate: float = 0.0) -> None:
        # Passive per-tick depletion:
        #   hunger_rate = fixed metabolic baseline
        #   fatigue * fatigue_rate = proportional drain from accumulated tiredness
        self.energy = max(0.0, self.energy - hunger_rate - self.fatigue * fatigue_rate)
        self.hunger = 1.0 - self.energy
        self.stress = max(0.0, 1.0 - self.energy)
        self.tick_cooldown()
