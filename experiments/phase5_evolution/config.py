"""Phase 5 — Configuration factory for asynchronous Baldwin evolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from config import Config


class Phase5ConfigFactory:
    """Factory for Phase 5 evolution Config objects.

    Loads Phase 4b BEST_CALIBRATED ecology and builds a fully configured
    Config for asynchronous Baldwin evolution. All methods are static —
    no instance state is needed.
    """

    _ECOLOGY_PATH: ClassVar[Path] = Path(
        "outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json"
    )
    _FALLBACK: ClassVar[dict] = {
        "init_food": 600,
        "eat_gain": 0.70,
        "move_cost": 0.005,
        "infant_starvation_multiplier": 1.0,
    }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @staticmethod
    def load_ecology() -> dict:
        """Load Phase 4b BEST_CALIBRATED ecology parameters.

        Returns:
            Dict of ecology parameters keyed by Config field names.
            Falls back to hardcoded values if the JSON is missing or malformed.
        """
        path = Phase5ConfigFactory._ECOLOGY_PATH
        if not path.exists():
            print(f"Warning: {path} not found — using fallback ecology")
            return Phase5ConfigFactory._FALLBACK.copy()

        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data.get("BEST_CALIBRATED", data)
        except Exception as exc:
            print(f"Warning: Could not load Phase 4b ecology: {exc}")
            return Phase5ConfigFactory._FALLBACK.copy()

    @staticmethod
    def make(
        seed: int = 42,
        mutation_enabled: bool = True,
        plasticity_enabled: bool = True,
        learning_rate: float = 1.0, # 0.1
        plasticity_coefficient: float = 1.0, # 0.5 
        phenotype_retention: float = 0.15,
        mutation_rate: float = 0.5, # 0.05
        mutation_sigma: float = 0.02,
        max_ticks: int = 40_000,
        relax_ecology: bool = False,
        ecology_relaxation_factor: float = 5.0, # 1.15
    ) -> Config:
        """Build a Phase 5 Config with Phase 4b ecology and run parameters.

        Args:
            seed: Random seed for reproducibility.
            mutation_enabled: Enable genetic mutation during reproduction.
            plasticity_enabled: Enable phenotypic learning (plasticity).
            learning_rate: Initial learning_rate for all starting genomes.
            plasticity_coefficient: Initial plasticity_coefficient for genomes.
            phenotype_retention: Fraction of parent expressed value inherited
                by offspring — 0.15 is Baldwinian (not Lamarckian).
            mutation_rate: Per-gene probability of applying a perturbation.
            mutation_sigma: Gaussian noise std-dev for mutations.
            max_ticks: Total simulation duration in ticks.
            relax_ecology: If True, inflate init_food for pilot runs.
            ecology_relaxation_factor: Multiplier on init_food when relax=True.

        Returns:
            Fully configured Config ready for Simulation.
        """
        eco = Phase5ConfigFactory.load_ecology()
        fb  = Phase5ConfigFactory._FALLBACK

        init_food = eco.get("init_food", fb["init_food"])
        if relax_ecology:
            init_food = int(init_food * ecology_relaxation_factor)

        return Config(
            # World
            width=50, # 50
            height=50, # 50

            # Population — neutral genome start (care=forage=self=1/3)
            init_mothers=15, # 15
            init_food=init_food,
            max_population=300,

            # Perception
            perception_radius=15,
            food_perception_radius=15,

            # Energy — Phase 4b BEST_CALIBRATED values
            initial_energy=1.0,
            hunger_rate=1 / 35,
            move_cost=eco.get("move_cost", fb["move_cost"]),
            feed_cost=0.01,
            eat_gain=eco.get("eat_gain", fb["eat_gain"]),
            rest_recovery=0.5,

            # Reproduction — Phase 4b validated thresholds
            reproduction_threshold=0.70, # 0.85
            reproduction_cost=0.25,
            reproduction_cooldown=80,

            # Child
            maturity_age=80, # 200
            starvation_threshold=1.0,
            infant_starvation_multiplier=eco.get(
                "infant_starvation_multiplier",
                fb["infant_starvation_multiplier"],
            ),

            # Mother lifetime
            mother_max_age=200, # 400

            # Fatigue
            fatigue_rate=0.01,

            # Plasticity
            plastic_gain=0.1,
            plasticity_metabolic_alpha=0.01,
            plasticity_maintenance_beta=0.001,
            plasticity_kin_conditional=True,

            # Simulation
            max_ticks=max_ticks,
            seed=seed,

            # Mode flags — all active for Block 2 evolution
            children_enabled=True,
            care_enabled=True,
            allow_allomothering=False, # On
            plasticity_enabled=plasticity_enabled,
            reproduction_enabled=True,
            mutation_enabled=mutation_enabled,

            # Softmax and mutation
            softmax_tau=0.1, # 0.1
            mutation_rate=mutation_rate,
            mutation_sigma=mutation_sigma,
            min_mutation_rate=0.01,

            # Thermoregulation — disabled
            warmth_radius=3,
            warmth_factor=1.0, # must be 0.0 to disable thermoregulation

            # Ecological mechanisms — disabled for Block 2
            food_entropy_alpha=0.01,
            food_entropy_beta=0.01,
            food_entropy_gamma=0.01,
            food_patch_prior=0.2,
            cry_decay_radius=10.0, # 0.0 disables cry-based patch learning
            temperature_period=200,
            temperature_sensitivity=0.0,

            # Phase 5 learning and phenotype inheritance
            init_learning_rate=learning_rate,
            init_plasticity_coefficient=plasticity_coefficient,
            phenotype_retention=phenotype_retention,

            # Birth scatter — tighter radius for kin clustering
            birth_scatter_radius=2,
        )
