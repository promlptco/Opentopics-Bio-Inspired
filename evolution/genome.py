from __future__ import annotations
from dataclasses import dataclass
import random

@dataclass
class Genome:
    care_weight: float = 0.5
    forage_weight: float = 0.5
    self_weight: float = 0.5
    learning_rate: float = 0.1
    learning_cost: float = 0.05
    plasticity_coefficient: float = 0.1
    update_sensitivity: float = 1.0
    # Option A — cortisol analog: energy penalty per tick when ignoring own distressed infant.
    # Default 0.0 leaves all prior experiments (Phase 1–6) unaffected.
    distress_sensitivity: float = 0.0
    # Option D — prolactin analog: energy returned per unit hunger reduced in own infant.
    # Default 0.0 leaves all prior experiments unaffected.
    care_recovery: float = 0.0

    def mutate(
        self,
        mutation_rate: float = 0.1,
        sigma: float = 0.05,
        lock_learning_rate: bool = False,
    ) -> Genome:
        def mutate_gene(value: float) -> float:
            if random.random() < mutation_rate:
                delta = random.gauss(0, sigma)
                return max(0.0, min(1.0, value + delta))
            return value

        care   = mutate_gene(self.care_weight)
        forage = mutate_gene(self.forage_weight)
        self_w = mutate_gene(self.self_weight)

        # Normalize so care + forage + self = 1.0 (design decision Block 2).
        # genome.care_weight then equals the effective care share directly,
        # preventing scale drift where all weights inflate without changing behaviour.
        total = care + forage + self_w
        if total > 0:
            care, forage, self_w = care / total, forage / total, self_w / total

        return Genome(
            care_weight=care,
            forage_weight=forage,
            self_weight=self_w,
            learning_rate=self.learning_rate if lock_learning_rate else mutate_gene(self.learning_rate),
            learning_cost=mutate_gene(self.learning_cost),
            plasticity_coefficient=mutate_gene(self.plasticity_coefficient),
            update_sensitivity=mutate_gene(self.update_sensitivity),
            distress_sensitivity=mutate_gene(self.distress_sensitivity),
            care_recovery=mutate_gene(self.care_recovery),
        )

    def copy(self) -> Genome:
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
