# logging_system/logger.py
from __future__ import annotations
import os
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
    
    def export_choices(self, output_dir: str) -> None:
        """Save choice log to output directory."""
        if not self.choice_records:
            return
        filepath = os.path.join(output_dir, "choice_log.csv")
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
    
    def export_cares(self, output_dir: str) -> None:
        """Save care log to output directory."""
        if not self.care_records:
            return
        filepath = os.path.join(output_dir, "care_log.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["tick", "mother_id", "child_id", "r", "benefit", "cost", "success"])
            for r in self.care_records:
                writer.writerow([
                    r.tick, r.mother_id, r.child_id, r.r, r.benefit, r.cost, r.success
                ])
    
    def save_all(self, output_dir: str) -> None:
        """Save all logs to output directory."""
        self.export_choices(output_dir)
        self.export_cares(output_dir)