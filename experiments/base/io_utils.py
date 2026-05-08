# experiments/base/io_utils.py
"""
Shared I/O helpers: CSV, JSON, and timestamp output-dir construction.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def make_output_dir(project_root: str | Path, phase_name: str,
                    tag: str = "") -> Path:
    """
    Build and create outputs/<phase_name>/<tag>_<timestamp>/ in project_root.
    If tag is empty, the directory is outputs/<phase_name>/<timestamp>/.
    """
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{tag}_{ts}" if tag else ts
    path = Path(project_root) / "outputs" / phase_name / stem
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_csv(rows: list[dict], path: str | Path,
              fieldnames: list[str] | None = None) -> None:
    if not rows:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(obj: Any, path: str | Path, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, default=str)


def read_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_csv(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        cast: dict = {}
        for k, v in row.items():
            try:
                cast[k] = int(v)
            except (ValueError, TypeError):
                try:
                    cast[k] = float(v)
                except (ValueError, TypeError):
                    cast[k] = v
        out.append(cast)
    return out


def summarize_numeric(results: list[dict], keys: list[str]) -> dict:
    """Mean and SD for each key across all result dicts."""
    import numpy as np
    out: dict = {}
    for k in keys:
        vals = [r[k] for r in results if k in r and r[k] is not None]
        arr  = [float(v) for v in vals if v == v]   # skip NaN strings
        if arr:
            out[f"{k}_mean"] = float(np.mean(arr))
            out[f"{k}_sd"]   = float(np.std(arr))
        else:
            out[f"{k}_mean"] = float("nan")
            out[f"{k}_sd"]   = float("nan")
    return out
