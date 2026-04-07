from __future__ import annotations
import csv
from logging_system.records import ChoiceRecord, CareRecord

class Logger:
    def __init__(self):
        self.choice_records: list[ChoiceRecord] = []
        self.care_records: list[CareRecord] = []
    
    def log_choice(self, record: ChoiceRecord) -> None:
        self.choice_records.append(record)
    
    def log_care(self, record: CareRecord) -> None:
        self.care_records.append(record)
    
    def export_choices(self, filepath: str) -> None:
        if not self.choice_records:
            return
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "tick", "mother_id", "mother_energy", "winner_domain",
                "chosen_child_id", "chosen_r", "chosen_distress", "chosen_distance"
            ])
            for r in self.choice_records:
                writer.writerow([
                    r.tick, r.mother_id, r.mother_energy, r.winner_domain,
                    r.chosen_child_id, r.chosen_r, r.chosen_distress, r.chosen_distance
                ])
    
    def export_cares(self, filepath: str) -> None:
        if not self.care_records:
            return
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["tick", "mother_id", "child_id", "r", "benefit", "cost", "success"])
            for r in self.care_records:
                writer.writerow([
                    r.tick, r.mother_id, r.child_id, r.r, r.benefit, r.cost, r.success
                ])