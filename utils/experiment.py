# utils/experiment.py
"""Experiment infrastructure utilities."""
import os
import json
import random
from datetime import datetime
from dataclasses import asdict
from typing import Any


def get_timestamp() -> str:
    """Return timestamp string: YYYYMMDD_HHMMSS"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_run_dir(phase_name: str, seed: int) -> str:
    """Create and return output directory path."""
    timestamp = get_timestamp()
    run_name = f"run_{timestamp}_seed{seed}"
    path = os.path.join("outputs", phase_name, run_name)
    os.makedirs(path, exist_ok=True)
    return path


def set_seed(seed: int) -> None:
    """Set all random seeds for reproducibility."""
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass


def save_config(config: Any, output_dir: str) -> None:
    """Save config as JSON."""
    path = os.path.join(output_dir, "config.json")
    if hasattr(config, "__dataclass_fields__"):
        data = asdict(config)
    elif hasattr(config, "__dict__"):
        data = vars(config)
    else:
        data = dict(config)
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def save_metadata(output_dir: str, phase: str, seed: int, **kwargs) -> None:
    """Save run metadata."""
    metadata = {
        "phase": phase,
        "timestamp": get_timestamp(),
        "seed": seed,
        **kwargs
    }
    path = os.path.join(output_dir, "metadata.json")
    with open(path, "w") as f:
        json.dump(metadata, f, indent=2)