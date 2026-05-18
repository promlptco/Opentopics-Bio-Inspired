"""Phase 5 — Configuration factory for asynchronous Baldwin evolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from config import Config


class Phase5ConfigFactory:
    """Factory for Phase 5 evolution Config objects.

    Loads Phase 4b BEST_CALIBRATED ecology and Phase 4c locked mechanism
    settings, then builds a fully configured Config for asynchronous Baldwin
    evolution. All methods are static — no instance state is needed.
    """

    _ECOLOGY_PATH: ClassVar[Path] = Path(
        "outputs/phase4_weight_sweep/phase4b_20260510_111325/selected_ecology.json"
    )
    _MECHANISM_PATH: ClassVar[Path] = Path(
        "outputs/phase4c_mechanism_screen/exp_20260516_010715/best_mechanism_settings.json"
    )
    _FALLBACK: ClassVar[dict] = {
        "init_food": 600,
        "eat_gain": 0.70,
        "move_cost": 0.005,
        "rest_recovery": 0.005,
        "perception_radius": 8,
        "food_perception_radius": 8,
        "infant_starvation_multiplier": 1.0,
    }
    _MECHANISM_FALLBACK: ClassVar[dict] = {
        "cry_decay_radius": 0.0,
        "temperature_sensitivity": 0.0,
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
    def load_mechanism() -> dict:
        """Load Phase 4c locked mechanism settings (cry_decay_radius, temperature_sensitivity).

        Returns:
            Dict with keys 'cry_decay_radius' and 'temperature_sensitivity'.
            Falls back to hardcoded values (cry=0.0, temp=0.0) if JSON missing.
        """
        path = Phase5ConfigFactory._MECHANISM_PATH
        if not path.exists():
            print(f"Warning: {path} not found — using fallback mechanism settings")
            return Phase5ConfigFactory._MECHANISM_FALLBACK.copy()

        try:
            with open(path, "r") as f:
                data = json.load(f)
            return data.get("locked_settings", Phase5ConfigFactory._MECHANISM_FALLBACK.copy())
        except Exception as exc:
            print(f"Warning: Could not load Phase 4c mechanism settings: {exc}")
            return Phase5ConfigFactory._MECHANISM_FALLBACK.copy()

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
        ecology_relaxation_factor: float = 1.2, # 1.15
        circle_world: bool = False,
        infant_starvation_multiplier: float | None = None,
        food_entropy_alpha: float = 0.01,
        maturity_age: int = 80,
        birth_scatter_radius: int = 2,
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
            circle_world: If True, restrict the arena to an inscribed circle.
            infant_starvation_multiplier: Override ISM loaded from ecology JSON.
                None = use the value from the ecology file (default behaviour).

        Returns:
            Fully configured Config ready for Simulation.
        """
        eco = Phase5ConfigFactory.load_ecology()
        mech = Phase5ConfigFactory.load_mechanism()
        fb  = Phase5ConfigFactory._FALLBACK

        init_food = eco.get("init_food", fb["init_food"])
        if relax_ecology:
            init_food = int(init_food * ecology_relaxation_factor)

        ism = (
            infant_starvation_multiplier
            if infant_starvation_multiplier is not None
            else eco.get("infant_starvation_multiplier", fb["infant_starvation_multiplier"])
        )

        return Config(
            # World
            width=50, # 50
            height=50, # 50
            circle_world=circle_world,

            # Population — neutral genome start (care=forage=self=1/3)
            init_mothers=15, # 15
            init_food=init_food,
            max_population=140,

            # Perception — Phase 4b BEST_CALIBRATED value
            perception_radius=int(eco.get("perception_radius", 8)),
            food_perception_radius=int(eco.get("food_perception_radius", 8)),

            # Energy — Phase 4b BEST_CALIBRATED values
            initial_energy=1.0,
            hunger_rate=1 / 35,
            move_cost=eco.get("move_cost", fb["move_cost"]),
            feed_cost=0.01,
            eat_gain=eco.get("eat_gain", fb["eat_gain"]),
            rest_recovery=eco.get("rest_recovery", 0.005),

            # Reproduction — Phase 4b validated thresholds
            reproduction_threshold=0.85, # 0.85
            reproduction_cost=0.20,
            reproduction_cooldown=120,

            # Child
            maturity_age=maturity_age,
            starvation_threshold=1.0,
            infant_starvation_multiplier=ism,

            # Mother lifetime
            mother_max_age=400,

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
            warmth_factor=0.0,  # 0.0 = thermoregulation disabled

            # Ecological mechanisms — Phase 4c locked settings
            food_entropy_alpha=food_entropy_alpha,
            food_entropy_beta=0.01,
            food_entropy_gamma=0.01,
            food_patch_prior=0.12,
            cry_decay_radius=mech.get("cry_decay_radius", 0.0),
            temperature_period=200,
            temperature_sensitivity=mech.get("temperature_sensitivity", 0.0),

            # Phase 5 learning and phenotype inheritance
            init_learning_rate=learning_rate,
            init_plasticity_coefficient=plasticity_coefficient,
            phenotype_retention=phenotype_retention,

            # Birth scatter — tighter radius for kin clustering
            birth_scatter_radius=birth_scatter_radius,
        )
