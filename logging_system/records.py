from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ChoiceRecord:
    tick: int
    mother_id: int
    mother_energy: float
    winner_domain: str
    candidate_child_ids: list[int]
    candidate_r: list[float]
    candidate_distress: list[float]
    candidate_distance: list[int]
    chosen_child_id: int | None
    chosen_r: float | None
    chosen_distress: float | None
    chosen_distance: int | None

@dataclass
class CareRecord:
    tick: int
    mother_id: int
    child_id: int
    r: float
    benefit: float
    cost: float
    success: bool
    mother_lineage_id: int = 0
    child_lineage_id: int = 0
    is_own_child: bool = False


@dataclass
class BirthRecord:
    tick: int
    mother_id: int
    child_id: int
    mother_lineage_id: int
    mother_generation: int
    mother_care_weight: float
    mother_forage_weight: float
    mother_self_weight: float


@dataclass
class DeathRecord:
    tick: int
    agent_id: int
    agent_type: str   # "mother" or "child"
    lineage_id: int
    generation: int
    cause: str        # "starvation" or "hunger"