from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Genome:
    """Heritable gene set for one mother agent.

    The three motivation weights (care, forage, self) are always kept normalized
    so their sum equals 1.0 after every mutation. This means genome.care_weight
    is the effective care share directly — no conversion needed.

    Attributes:
        care_weight: Fraction of motivation budget allocated to caregiving.
        forage_weight: Fraction allocated to food procurement.
        self_weight: Fraction allocated to self-maintenance.
        learning_rate: Rate at which expressed phenotype tracks reward signal.
        learning_cost: Energy coefficient per unit of phenotypic change.
        plasticity_coefficient: Current degree of phenotypic flexibility [0, 1].
        update_sensitivity: Scales how strongly reward drives plastic change.
        distress_sensitivity: Cortisol analog — energy penalty for ignoring
            own distressed infant. Default 0.0 keeps Phase 1–4 unaffected.
        care_recovery: Prolactin analog — energy returned per unit hunger
            reduced in own infant. Default 0.0 keeps Phase 1–4 unaffected.
    """

    care_weight: float = 1.0
    forage_weight: float = 0.5
    self_weight: float = 0.8

    learning_rate: float = 0.1
    learning_cost: float = 0.005
    plasticity_coefficient: float = 0.1
    update_sensitivity: float = 1.0

    distress_sensitivity: float = 0.0
    care_recovery: float = 0.0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def mutate(
        self,
        mutation_rate: float = 0.05,
        sigma: float = 0.02,
        lock_learning_rate: bool = False,
    ) -> Genome:
        """Return a mutated child genome.

        Mutates five core genes: care_weight, forage_weight, self_weight,
        learning_rate, and plasticity_coefficient. All other genes are
        inherited unchanged. After mutating the three motivation weights,
        renormalizes them so care + forage + self = 1.0.

        Args:
            mutation_rate: Per-gene probability of applying a perturbation.
            sigma: Std-dev of the Gaussian perturbation.
            lock_learning_rate: If True, learning_rate is not mutated.

        Returns:
            New Genome with mutated values; caller's genome is unchanged.
        """
        care   = self._mutate_gene(self.care_weight,   mutation_rate, sigma)
        forage = self._mutate_gene(self.forage_weight, mutation_rate, sigma)
        self_w = self._mutate_gene(self.self_weight,   mutation_rate, sigma)

        care, forage, self_w = self._renormalize(care, forage, self_w)

        new_lr = (
            self.learning_rate
            if lock_learning_rate
            else self._mutate_gene(self.learning_rate, mutation_rate, sigma)
        )

        return Genome(
            care_weight=care,
            forage_weight=forage,
            self_weight=self_w,
            learning_rate=new_lr,
            learning_cost=self.learning_cost,
            plasticity_coefficient=self._mutate_gene(
                self.plasticity_coefficient, mutation_rate, sigma
            ),
            update_sensitivity=self.update_sensitivity,
            distress_sensitivity=self.distress_sensitivity,
            care_recovery=self.care_recovery,
        )

    def copy(self) -> Genome:
        """Return an exact copy of this genome.

        Returns:
            New Genome with identical field values.
        """
        return Genome(
            care_weight=self.care_weight,
            forage_weight=self.forage_weight,
            self_weight=self.self_weight,
            learning_rate=self.learning_rate,
            learning_cost=self.learning_cost,
            plasticity_coefficient=self.plasticity_coefficient,
            update_sensitivity=self.update_sensitivity,
            distress_sensitivity=self.distress_sensitivity,
            care_recovery=self.care_recovery,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mutate_gene(value: float, mutation_rate: float, sigma: float) -> float:
        """Apply Gaussian mutation to one gene with probability mutation_rate.

        Args:
            value: Current gene value.
            mutation_rate: Probability of applying a perturbation.
            sigma: Std-dev of the Gaussian perturbation.

        Returns:
            Mutated gene clamped to [0.0, 1.0], or original value unchanged.
        """
        if random.random() >= mutation_rate:
            return value
        return max(0.0, min(1.0, value + random.gauss(0, sigma)))

    @staticmethod
    def _renormalize(
        care: float, forage: float, self_w: float
    ) -> tuple[float, float, float]:
        """Normalize three motivation weights so they sum to 1.0.

        If all three are zero (degenerate case), returns equal thirds.

        Args:
            care: Raw care motivation weight.
            forage: Raw forage motivation weight.
            self_w: Raw self motivation weight.

        Returns:
            Tuple (care, forage, self_w) summing to 1.0.
        """
        total = care + forage + self_w
        if total <= 0.0:
            return 1 / 3, 1 / 3, 1 / 3
        return care / total, forage / total, self_w / total
