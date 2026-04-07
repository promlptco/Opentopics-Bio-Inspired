from __future__ import annotations

class LineageManager:
    def __init__(self):
        self.parents: dict[int, int] = {}      # child_id -> mother_id
        self.generations: dict[int, int] = {}  # agent_id -> generation
        self.lineages: dict[int, int] = {}     # agent_id -> lineage_id
    
    def register_birth(self, child_id: int, mother_id: int, lineage_id: int, generation: int) -> None:
        self.parents[child_id] = mother_id
        self.generations[child_id] = generation
        self.lineages[child_id] = lineage_id
    
    def register_mother(self, mother_id: int, lineage_id: int, generation: int) -> None:
        self.generations[mother_id] = generation
        self.lineages[mother_id] = lineage_id
    
    def get_relatedness(self, mother_id: int, child_id: int) -> float:
        """r = 2^(-d) where d = generation distance"""
        if mother_id not in self.lineages or child_id not in self.lineages:
            return 0.0
        
        # Different lineage = unrelated
        if self.lineages[mother_id] != self.lineages[child_id]:
            return 0.0
        
        # Same lineage: compute generation distance
        mother_gen = self.generations.get(mother_id, 0)
        child_gen = self.generations.get(child_id, 0)
        d = abs(child_gen - mother_gen)
        
        if d == 0:
            return 0.0  # same generation, not parent-child
        
        return 2.0 ** (-d)