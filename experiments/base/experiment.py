# experiments/base/experiment.py
"""
BaseExperiment — abstract base class for all phase experiments.

Provides:
  run_sweep()    — parallel seed loops with progress logging
  save_results() — CSV + JSON write helpers
  make_plots()   — override per phase
  run_one()      — override per phase

Subclasses override run_one() and make_plots().  All other bookkeeping
(seed loops, CSV writing, progress stdout) is shared here.
"""

from __future__ import annotations

import csv
import json
import os
import time
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

import numpy as np


class BaseExperiment(ABC):
    """
    Abstract base experiment.

    Parameters
    ----------
    cfg    : Config dataclass instance with simulation parameters
    out_dir: output directory (created automatically)
    """

    def __init__(self, cfg, out_dir: Path) -> None:
        self.cfg     = cfg
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    # ── interface ─────────────────────────────────────────────────────────────

    @abstractmethod
    def run_one(self, seed: int) -> dict:
        """
        Run one replicate for the given seed.  Returns a flat result dict
        suitable for CSV serialisation.
        """

    def make_plots(self, results: list[dict]) -> None:
        """Override to produce figures.  Default: no-op."""

    # ── seed sweep ────────────────────────────────────────────────────────────

    def run_sweep(
        self,
        seeds: list[int],
        *,
        workers: int = 1,
        label: str = "",
    ) -> list[dict]:
        """
        Run run_one() for every seed, in parallel when workers > 1.

        Parameters
        ----------
        seeds   : list of integer seeds
        workers : parallel processes (1 = sequential)
        label   : progress prefix printed to stdout

        Returns a list of result dicts, one per seed.
        """
        total   = len(seeds)
        results = []
        prefix  = f"[{label}] " if label else ""

        t0 = time.monotonic()
        print(f"{prefix}Running {total} seeds  (workers={workers})")

        if workers <= 1:
            for i, seed in enumerate(seeds, 1):
                r = self.run_one(seed)
                results.append(r)
                if i % max(1, total // 10) == 0 or i == total:
                    elapsed = time.monotonic() - t0
                    print(f"  {prefix}{i}/{total}  elapsed={elapsed:.1f}s")
        else:
            futures = {}
            with ProcessPoolExecutor(max_workers=workers) as pool:
                for seed in seeds:
                    fut = pool.submit(self._run_one_static, seed)
                    futures[fut] = seed
                done = 0
                for fut in as_completed(futures):
                    results.append(fut.result())
                    done += 1
                    if done % max(1, total // 10) == 0 or done == total:
                        elapsed = time.monotonic() - t0
                        print(f"  {prefix}{done}/{total}  elapsed={elapsed:.1f}s")

        elapsed = time.monotonic() - t0
        print(f"{prefix}Done  {total} seeds  total={elapsed:.1f}s")
        return results

    def _run_one_static(self, seed: int) -> dict:
        """Picklable wrapper for ProcessPoolExecutor."""
        return self.run_one(seed)

    # ── I/O ──────────────────────────────────────────────────────────────────

    def save_csv(self, rows: list[dict], filename: str,
                 fieldnames: list[str] | None = None) -> Path:
        """Write rows to a CSV in out_dir.  Returns the full path."""
        path = self.out_dir / filename
        if not rows:
            return path
        if fieldnames is None:
            fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames,
                                    extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"  Saved: {filename}")
        return path

    def save_json(self, obj: Any, filename: str) -> Path:
        """Write obj as pretty-printed JSON in out_dir.  Returns path."""
        path = self.out_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, default=str)
        print(f"  Saved: {filename}")
        return path

    def save_results(self, results: list[dict],
                     filename: str = "results_raw.csv") -> Path:
        return self.save_csv(results, filename)

    # ── Config override ───────────────────────────────────────────────────────

    @staticmethod
    def apply_overrides(cfg, overrides: dict) -> None:
        """
        Apply a flat key→value dict of Config field overrides.
        Performs type coercion: matches the original field type.
        """
        for key, raw_val in overrides.items():
            if not hasattr(cfg, key):
                continue
            orig = getattr(cfg, key)
            if orig is None:
                setattr(cfg, key, raw_val)
            else:
                try:
                    setattr(cfg, key, type(orig)(raw_val))
                except (TypeError, ValueError):
                    setattr(cfg, key, raw_val)

    # ── Summary helpers ───────────────────────────────────────────────────────

    @staticmethod
    def aggregate(results: list[dict], keys: list[str]) -> dict:
        """Return mean ± SD for each numeric key across all result dicts."""
        out = {}
        for k in keys:
            vals = [r[k] for r in results if k in r and r[k] is not None]
            arr  = np.array(vals, dtype=float)
            out[f"{k}_mean"] = float(np.nanmean(arr)) if len(arr) else float("nan")
            out[f"{k}_sd"]   = float(np.nanstd(arr))  if len(arr) else float("nan")
        return out
