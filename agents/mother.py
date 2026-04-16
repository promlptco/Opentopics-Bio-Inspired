from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np

from agents.agent import Agent
from evolution.genome import Genome

if TYPE_CHECKING:
    from agents.child import ChildAgent
    from simulation.world import GridWorld


# Global Softmax temperature.
SOFTMAX_TAU: float = 0.1


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

        self.stress: float = 0.0
        self.fatigue: float = 0.0
        self.held_food: int = 0

        self.own_child_id: int | None = None
        self.cooldown: int = 0

        self.target_child_id: int | None = None
        self.commit_ticks: int = 0

        self.pending_move_cost: float = 0.0

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

    def set_target(self, child_id: int, duration: int = 5) -> None:
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
        return self.genome.care_weight * child.distress

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
        world: GridWorld,
        perception_radius: float,
        nearest_food: tuple[int, int] | None = None,
        distance_to_food: float | None = None,
    ) -> float:
        """
        Environmental FORAGE cue.

        This imports the useful Phase 2 logic:
          - food nearby increases forage cue
          - standing on food gives strong forage cue
          - already holding food suppresses further foraging

        This cue is not genetic by itself.
        The final FORAGE score is:
          genome.forage_weight * forage_cue
        """
        if perception_radius <= 0:
            perception_radius = 1.0

        if self.pos in world.food_positions:
            forage_cue = 1.5

        elif nearest_food is not None and distance_to_food is not None:
            forage_cue = max(0.0, 1.0 - (distance_to_food / perception_radius))

        else:
            forage_cue = 0.0

        # If mother already holds food, reduce urge to gather more.
        if self.held_food > 0:
            forage_cue *= 0.25

        return float(max(0.0, forage_cue))

    def compute_self_cue(self) -> float:
        """
        Environmental SELF cue.

        SELF is based on the need to maintain the mother's own state:
          - low energy
          - fatigue

        This does not decide EAT vs REST yet.
        It only decides whether SELF maintenance should dominate.
        """
        energy_deficit = max(0.0, 1.0 - self.energy)
        fatigue_pressure = max(0.0, self.fatigue)

        self_cue = 0.65 * energy_deficit + 0.35 * fatigue_pressure

        # If holding food and energy is low, self-maintenance is more actionable.
        if self.held_food > 0:
            self_cue += 0.25 * energy_deficit

        return float(max(0.0, self_cue))

    def compute_care_cue(
        self,
        child: ChildAgent | None,
        world: GridWorld,
        perception_radius: float,
    ) -> float:
        """
        Environmental CARE cue.

        CARE is based on:
          - child distress
          - child hunger
          - separation between mother and child
          - whether mother is carrying food

        This cue is only active when a living child exists.
        """
        if child is None or not child.alive:
            return 0.0

        if perception_radius <= 0:
            perception_radius = 1.0

        child_dist = world.get_distance(self.pos, child.pos)
        distance_pressure = min(1.0, child_dist / perception_radius)

        distress_pressure = max(0.0, child.distress)
        hunger_pressure = max(0.0, child.hunger)

        care_cue = (
            0.55 * distress_pressure
            + 0.25 * hunger_pressure
            + 0.20 * distance_pressure
        )

        # If mother has food and the child is hungry, care becomes more actionable.
        if self.held_food > 0:
            care_cue += 0.35 * hunger_pressure

        return float(max(0.0, care_cue))

    def compute_motivation_scores(
        self,
        world: GridWorld,
        perception_radius: float,
        child: ChildAgent | None = None,
        nearest_food: tuple[int, int] | None = None,
        distance_to_food: float | None = None,
        care_enabled: bool = True,
    ) -> dict[str, float]:
        """
        New unified motivation scoring.

        This is the key synthesis:

          final_FORAGE = genome.forage_weight * environmental_forage_cue
          final_SELF   = genome.self_weight   * environmental_self_cue
          final_CARE   = genome.care_weight   * environmental_care_cue

        Phase 2 can run with:
          care_enabled = False
          care_weight = 0.0
          forage_weight = 1.0
          self_weight = 1.0

        Phase 3 can run with:
          care_enabled = True
          care_weight > 0
        """
        forage_cue = self.compute_forage_cue(
            world=world,
            perception_radius=perception_radius,
            nearest_food=nearest_food,
            distance_to_food=distance_to_food,
        )

        self_cue = self.compute_self_cue()

        scores = {
            "FORAGE": max(0.0, self.genome.forage_weight * forage_cue),
            "SELF": max(0.0, self.genome.self_weight * self_cue),
        }

        if care_enabled:
            care_cue = self.compute_care_cue(
                child=child,
                world=world,
                perception_radius=perception_radius,
            )
            scores["CARE"] = max(0.0, self.genome.care_weight * care_cue)

        return scores

    def choose_motivation(
        self,
        world: GridWorld,
        perception_radius: float,
        tau: float = SOFTMAX_TAU,
        child: ChildAgent | None = None,
        nearest_food: tuple[int, int] | None = None,
        distance_to_food: float | None = None,
        care_enabled: bool = True,
    ) -> tuple[str, dict[str, float], dict[str, float]]:
        """
        Choose motivation using synthesis logic.

        Returns:
          motivation, scores, probabilities

        motivation:
          FORAGE / SELF / CARE

        scores:
          weighted utilities before softmax

        probabilities:
          softmax probabilities
        """
        scores = self.compute_motivation_scores(
            world=world,
            perception_radius=perception_radius,
            child=child,
            nearest_food=nearest_food,
            distance_to_food=distance_to_food,
            care_enabled=care_enabled,
        )

        probs = softmax_probs(scores, tau=tau)

        keys = list(probs.keys())
        weights = [probs[k] for k in keys]

        chosen = np.random.choice(keys, p=weights)

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

    def feed_child(self, child: ChildAgent, feed_cost: float, world: GridWorld) -> tuple[bool, float]:
        """
        Feed child if adjacent.

        Return:
          success, actual hunger reduction
        """
        dist = world.get_distance(self.pos, child.pos)

        if dist != 1:
            return False, 0.0

        self.energy -= feed_cost
        hunger_reduced = child.receive_food(0.2)

        return True, hunger_reduced

    def rest(self, rest_recovery: float) -> None:
        self.fatigue = max(0.0, self.fatigue - rest_recovery)

    # ============================================================
    # Reproduction
    # ============================================================

    def can_reproduce(self, threshold: float) -> bool:
        return (
            self.energy >= threshold
            and self.own_child_id is None
            and self.cooldown == 0
        )

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
    ) -> None:
        delta = self.genome.learning_rate * reward * plastic_gain
        self.genome.care_weight = max(0.0, min(1.0, self.genome.care_weight + delta))
        self.energy -= self.genome.learning_cost * abs(delta) + energy_cost

    # ============================================================
    # State update
    # ============================================================

    def update_state(self, hunger_rate: float) -> None:
        self.hunger = min(1.0, self.hunger + hunger_rate)
        self.energy = max(0.0, self.energy - self.hunger * 0.01)
        self.stress = max(0.0, 1.0 - self.energy)
        self.tick_cooldown()