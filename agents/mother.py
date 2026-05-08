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
        self.expressed_care_weight: float = genome.care_weight  # phenotypic; genome.care_weight is heritable

        self.stress: float = 0.0
        self.fatigue: float = 0.0
        self.held_food: int = 0

        self.own_child_id: int | None = None
        self.cooldown: int = 0
        self.has_reproduced: bool = False  # one-child-per-lifetime (Change F)

        self.target_child_id: int | None = None
        self.commit_ticks: int = 0

        self.pending_move_cost: float = 0.0
        self.last_motivation: str = "FORAGE"

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

    def set_target(self, child_id: int, duration: int = 20) -> None:
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
        return self.genome.forage_weight * (1.0 - self.energy)

    def calc_self_motivation(self) -> float:
        return self.genome.self_weight * (self.stress + self.fatigue) / 2.0

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
            return 0.0
        return float(max(0.0, min(1.0, 1.0 - distance_to_food / perception_radius)))

    def compute_self_cue(self) -> float:
        """Neutral SELF cue bounded [0, 1] (Change B).

        self_cue = 1 - energy (energy deficit).
        No energy = maximum self-urgency; full energy = no urgency.
        """
        return float(max(0.0, 1.0 - self.energy))

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

        fw = max(0.0, self.genome.forage_weight)
        sw = max(0.0, self.genome.self_weight)
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

    def plastic_update(
        self,
        reward: float,
        plastic_gain: float,
        energy_cost: float = 0.0,
        noise_sigma: float = 0.0,
    ) -> None:
        if noise_sigma > 0.0:
            # Multiplicative noise on the reward signal — learning is unreliable.
            # Mothers with high genetic care_weight are buffered; those relying on
            # plasticity face stochastic errors. This is the Hinton-Nowlan mechanism.
            reward = reward * max(0.0, 1.0 + random.gauss(0, noise_sigma))
        delta = self.genome.learning_rate * reward * plastic_gain
        self.expressed_care_weight = max(0.0, min(1.0, self.expressed_care_weight + delta))
        self.energy -= self.genome.learning_cost * abs(delta) + energy_cost

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