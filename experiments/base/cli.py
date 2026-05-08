# experiments/base/cli.py
"""
Shared CLI builder for phase experiments.

Every phase entry point calls build_parser() and may add phase-specific
arguments on top.  The --param flag accepts any Config field override as
--param key=value pairs (repeatable).

Usage pattern in a phase experiment.py:
    from experiments.base.cli import build_parser, load_overrides
    parser = build_parser(description="Phase N ...")
    parser.add_argument("--my-flag", ...)
    args = parser.parse_args()
    overrides = load_overrides(args)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def build_parser(
    description: str = "Bio-Inspired simulation experiment",
    modes: list[str] | None = None,
    default_mode: str = "pipeline",
    default_duration: int = 400,
    default_seeds: int = 10,
    default_workers: int = 4,
) -> argparse.ArgumentParser:
    """
    Return an ArgumentParser pre-loaded with the standard shared flags.

    Standard flags
    --------------
    --mode       : pipeline / sweep / single (or phase-specific list)
    --load       : path to a prior phase output JSON; auto-sets matching Config params
    --load-key   : sub-key to drill into the loaded JSON (e.g. OPTIMAL, BALANCED)
    --config     : path to JSON file of Config overrides (applied after --load)
    --duration   : simulation length in ticks
    --seeds      : number of random seeds
    --workers    : parallel workers (0 = auto)
    --output-dir : explicit output directory (default = outputs/<phase>/<ts>)
    --param      : key=value pairs to override individual Config fields (highest priority)

    Priority (lowest -> highest): --load < --config < --param
    """
    if modes is None:
        modes = ["pipeline", "sweep", "single"]

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode", type=str, choices=modes, default=default_mode,
        help="Experiment mode",
    )
    parser.add_argument(
        "--load", type=str, default=None, metavar="RESULT.json",
        help="Prior phase output JSON; matching Config params are auto-set "
             "(e.g. outputs/phase4_weight_sweep/.../selected_weights.json)",
    )
    parser.add_argument(
        "--load-key", dest="load_key", type=str, default=None, metavar="KEY",
        help="Sub-key inside the loaded JSON (e.g. OPTIMAL, BALANCED, BEST_ECOLOGICAL). "
             "Auto-detected when the JSON has exactly one nested-dict entry.",
    )
    parser.add_argument(
        "--config", type=str, default=None, metavar="FILE.json",
        help="JSON file of Config field overrides (applied after --load, before --param)",
    )
    parser.add_argument(
        "--duration", type=int, default=default_duration,
        help="Simulation length in ticks",
    )
    parser.add_argument(
        "--seeds", type=int, default=default_seeds,
        help="Number of random seeds per config",
    )
    parser.add_argument(
        "--workers", type=int, default=default_workers,
        help="Parallel workers (0 = auto-detect)",
    )
    parser.add_argument(
        "--output-dir", dest="output_dir", type=str, default=None,
        help="Explicit output directory (auto-generated if omitted)",
    )
    parser.add_argument(
        "--param", action="append", default=[], metavar="key=value",
        help="Override a Config field, e.g. --param move_cost=0.01 (repeatable)",
    )
    return parser


def load_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """
    Merge overrides in priority order: --load < --config < --param.

    --load   : reads a prior phase output JSON and pulls flat scalar fields
    --config : reads a hand-written Config override JSON
    --param  : individual key=value pairs (highest priority)

    Values are coerced by BaseExperiment.apply_overrides().
    """
    overrides: dict[str, Any] = {}

    # ── 1. --load (lowest priority) ───────────────────────────────────────────
    load_path = getattr(args, "load", None)
    if load_path:
        path = Path(load_path)
        if not path.exists():
            print(f"[cli] --load file not found: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            loaded: dict = json.load(f)

        load_key: str | None = getattr(args, "load_key", None)

        # Auto-detect: if exactly one top-level value is a dict, use that key
        if load_key is None:
            nested = [k for k, v in loaded.items() if isinstance(v, dict)]
            if len(nested) == 1:
                load_key = nested[0]

        if load_key is not None:
            if load_key not in loaded:
                print(
                    f"[cli] --load-key '{load_key}' not found in {path.name}. "
                    f"Available keys: {list(loaded.keys())}",
                    file=sys.stderr,
                )
                sys.exit(1)
            data = loaded[load_key]
        else:
            data = loaded

        # Only scalar values — skip nested dicts / lists
        flat = {k: v for k, v in data.items()
                if not isinstance(v, (dict, list))}
        overrides.update(flat)

        label   = f"{path.name}:{load_key}" if load_key else path.name
        summary = ", ".join(f"{k}={v}" for k, v in flat.items())
        print(f"[load] {label} -> {summary}")

    # ── 2. --config (overrides --load) ────────────────────────────────────────
    if args.config:
        path = Path(args.config)
        if not path.exists():
            print(f"[cli] --config file not found: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            overrides.update(json.load(f))

    # ── 3. --param (highest priority) ─────────────────────────────────────────
    for kv in (args.param or []):
        if "=" not in kv:
            print(f"[cli] --param must be key=value, got: {kv!r}", file=sys.stderr)
            sys.exit(1)
        k, _, v = kv.partition("=")
        overrides[k.strip()] = _coerce(v.strip())

    return overrides


def _coerce(v: str) -> Any:
    """Parse a CLI string value into int / float / bool / str."""
    if v.lower() in ("true",  "yes"): return True
    if v.lower() in ("false", "no"):  return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def n_workers(w: int) -> int:
    """Resolve worker count: 0 → cpu_count, else clamp to >= 1."""
    import os
    return (os.cpu_count() or 1) if w == 0 else max(1, w)
