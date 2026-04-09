# logging_system/logger.py
from __future__ import annotations
import os
import csv
from logging_system.records import ChoiceRecord, CareRecord, DeathRecord, BirthRecord


class Logger:
    def __init__(self):
        self.choice_records: list[ChoiceRecord] = []
        self.care_records: list[CareRecord] = []
        self.death_records: list[DeathRecord] = []
        self.birth_records: list[BirthRecord] = []

    def log_choice(self, record: ChoiceRecord) -> None:
        self.choice_records.append(record)

    def log_care(self, record: CareRecord) -> None:
        self.care_records.append(record)

    def log_death(self, record: DeathRecord) -> None:
        self.death_records.append(record)

    def log_birth(self, record: BirthRecord) -> None:
        self.birth_records.append(record)

    def export_choices(self, output_dir: str) -> None:
        """Save choice log to output directory. Includes all candidate children."""
        if not self.choice_records:
            return
        filepath = os.path.join(output_dir, "choice_log.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "tick", "mother_id", "mother_energy", "winner_domain",
                "chosen_child_id", "chosen_r", "chosen_distress", "chosen_distance",
                "candidate_child_ids", "candidate_r", "candidate_distress", "candidate_distance",
            ])
            for r in self.choice_records:
                writer.writerow([
                    r.tick, r.mother_id, r.mother_energy, r.winner_domain,
                    r.chosen_child_id, r.chosen_r, r.chosen_distress, r.chosen_distance,
                    ";".join(str(x) for x in r.candidate_child_ids),
                    ";".join(f"{x:.4f}" for x in r.candidate_r),
                    ";".join(f"{x:.4f}" for x in r.candidate_distress),
                    ";".join(str(x) for x in r.candidate_distance),
                ])

    def export_cares(self, output_dir: str) -> None:
        """Save care log to output directory."""
        if not self.care_records:
            return
        filepath = os.path.join(output_dir, "care_log.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "tick", "mother_id", "child_id", "r", "benefit", "cost", "success",
                "mother_lineage_id", "child_lineage_id", "is_own_child",
            ])
            for r in self.care_records:
                writer.writerow([
                    r.tick, r.mother_id, r.child_id, r.r, r.benefit, r.cost, r.success,
                    r.mother_lineage_id, r.child_lineage_id, r.is_own_child,
                ])

    def export_deaths(self, output_dir: str) -> None:
        """Save death log to output directory."""
        if not self.death_records:
            return
        filepath = os.path.join(output_dir, "death_log.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["tick", "agent_id", "agent_type", "lineage_id", "generation", "cause"])
            for d in self.death_records:
                writer.writerow([
                    d.tick, d.agent_id, d.agent_type, d.lineage_id, d.generation, d.cause,
                ])

    def export_births(self, output_dir: str) -> None:
        """Save birth log to output directory."""
        if not self.birth_records:
            return
        filepath = os.path.join(output_dir, "birth_log.csv")
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "tick", "mother_id", "child_id",
                "mother_lineage_id", "mother_generation",
                "mother_care_weight", "mother_forage_weight", "mother_self_weight",
            ])
            for b in self.birth_records:
                writer.writerow([
                    b.tick, b.mother_id, b.child_id,
                    b.mother_lineage_id, b.mother_generation,
                    f"{b.mother_care_weight:.6f}",
                    f"{b.mother_forage_weight:.6f}",
                    f"{b.mother_self_weight:.6f}",
                ])

    def save_all(self, output_dir: str) -> None:
        """Save all logs to output directory."""
        self.export_choices(output_dir)
        self.export_cares(output_dir)
        self.export_deaths(output_dir)
        self.export_births(output_dir)