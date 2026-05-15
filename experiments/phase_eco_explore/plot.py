"""Phase 4c — Viability heatmap plotter.

Reads viability_table.csv produced by run.py and renders two heatmaps:
  Left  — SVR (Seed Viability Rate)
  Centre — G_depth (mean highest generation)
  Right — PSC (Population Stability Coefficient, lower = more stable)

Passing cells are marked with a star (★).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_heatmaps(output_dir: Path) -> None:
    df = pd.read_csv(output_dir / "viability_table.csv")

    relax_factors = sorted(df["relax_factor"].unique())
    # High ISM at top (harder ecology at top of y-axis)
    ism_values = sorted(df["ism"].unique(), reverse=True)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    fig.suptitle("Phase 4c: Ecological Viability Screen", fontsize=13, fontweight="bold")

    panels = [
        ("svr",     "SVR\n(≥ 0.60 to pass)",           0.0, 1.0,  "Greens"),
        ("g_depth", "G_depth\n(≥ 10 to pass)",          0.0, None, "Blues"),
        ("psc",     "PSC\n(< 0.50 to pass, lower=better)", 0.0, 2.0,  "Reds_r"),
    ]

    for ax, (col, title, vmin, vmax, cmap) in zip(axes, panels):
        grid = np.full((len(ism_values), len(relax_factors)), np.nan)
        for _, row in df.iterrows():
            ri = relax_factors.index(row["relax_factor"])
            ii = ism_values.index(row["ism"])
            grid[ii, ri] = row[col]

        if vmax is None:
            vmax = float(np.nanmax(grid)) if not np.all(np.isnan(grid)) else 1.0

        im = ax.imshow(grid, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        ax.set_xticks(range(len(relax_factors)))
        ax.set_xticklabels([str(r) for r in relax_factors])
        ax.set_yticks(range(len(ism_values)))
        ax.set_yticklabels([str(i) for i in ism_values])
        ax.set_xlabel("Relax factor (food multiplier)", fontsize=9)
        ax.set_ylabel("ISM (infant starvation multiplier)", fontsize=9)
        ax.set_title(title, fontsize=10)

        for ii in range(len(ism_values)):
            for ri in range(len(relax_factors)):
                val = grid[ii, ri]
                if not np.isnan(val):
                    ax.text(ri, ii, f"{val:.2f}", ha="center", va="center",
                            fontsize=9, color="black")

        # Mark passing cells
        for _, row in df[df["passes"]].iterrows():
            ri = relax_factors.index(row["relax_factor"])
            ii = ism_values.index(row["ism"])
            ax.text(ri, ii + 0.38, "★", ha="center", va="center",
                    fontsize=13, color="gold")

    plt.tight_layout()
    out_path = output_dir / "eco_viability_heatmap.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4c: Plot viability heatmaps")
    parser.add_argument("--input-dir", type=str, required=True,
                        help="Directory containing viability_table.csv")
    args = parser.parse_args()
    plot_heatmaps(Path(args.input_dir))


if __name__ == "__main__":
    main()
