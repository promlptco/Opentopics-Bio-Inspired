import os
import csv
import json

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from experiments.phase2_survival_minimal.config import (
    INIT_MOTHERS,
    DEFAULT_PERCEPTION_RADIUS,
    TAIL_WINDOW,
)


def pad(x, duration):
    arr = np.full(duration, np.nan)
    x = np.asarray(x, dtype=float)
    arr[: min(duration, len(x))] = x[:duration]
    return arr


def safe(value, nan=0.0):
    return float(np.nan_to_num(value, nan=nan))


def summarize_repeats(repeat_results, duration, tail_window=TAIL_WINDOW):
    final_pops = np.array([r["final_pop"] for r in repeat_results], dtype=float)
    mean_es = np.array([r["mean_energy"] for r in repeat_results], dtype=float)
    final_es = np.array([r["final_energy"] for r in repeat_results], dtype=float)

    tail_means = []
    energy_slopes = []
    pop_slopes = []
    
    for r in repeat_results:
        e = np.nan_to_num(pad(r["energy_history"], duration), nan=0.0)
        p = np.nan_to_num(pad(r["population_history"], duration), nan=0.0)

        tail_means.append(np.mean(e[-tail_window:]))
        energy_slopes.append(tail_slope(r["energy_history"], duration, tail_window))
        pop_slopes.append(tail_slope(r["population_history"], duration, tail_window))

    tail_means = np.array(tail_means, dtype=float)

    return {
        "final_pop": float(np.mean(final_pops)),
        "final_pop_sd": float(np.std(final_pops)),
        "mean_energy": float(np.mean(mean_es)),
        "final_energy": float(np.mean(final_es)),
        "tail_mean_energy": float(np.mean(tail_means)),
        "tail_energy_sd": float(np.std(tail_means)),
        "tail_energy_slope": float(np.mean(energy_slopes)),
        "tail_pop_slope": float(np.mean(pop_slopes)),
    }


def config_title(params):
    return (
        f"perception={params.get('perception_radius', DEFAULT_PERCEPTION_RADIUS)} | "
        f"hunger={params['hunger_rate']} | move={params['move_cost']} | "
        f"eat={params['eat_gain']} | food={params['init_food']} | rest={params['rest_recovery']}"
    )

def tail_slope(series, duration, tail_window=TAIL_WINDOW):
    y = np.nan_to_num(pad(series, duration), nan=0.0)[-tail_window:]
    x = np.arange(len(y), dtype=float)

    if len(y) < 2:
        return 0.0

    return float(np.polyfit(x, y, 1)[0])

def plot_multiseed_condition(name, results, params, run_labels, duration, out_dir):
    ticks = np.arange(duration)

    energy_matrix = np.asarray(
        [np.nan_to_num(pad(r["energy_history"], duration), nan=0.0) for r in results]
    )
    pop_matrix = np.asarray(
        [np.nan_to_num(pad(r["population_history"], duration), nan=0.0) for r in results]
    )

    mean_e = np.mean(energy_matrix, axis=0)
    std_e = np.std(energy_matrix, axis=0)

    mean_p = np.mean(pop_matrix, axis=0)
    std_p = np.std(pop_matrix, axis=0)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    fig.suptitle(
        f"Phase 2 Multi-Seed Validation — {name.upper()}\n"
        f"Runs: {len(results)} total | {config_title(params)}",
        fontsize=14,
        fontweight="bold",
    )

    for i in range(len(results)):
        label = "Individual Runs" if i == 0 else "_nolegend_"
        ax1.plot(ticks, energy_matrix[i], alpha=0.15, linewidth=0.8, color="gray", label=label)
        ax2.step(ticks, pop_matrix[i], where="post", alpha=0.15, linewidth=0.8, color="gray", label=label)

    ax1.fill_between(ticks, mean_e - std_e, mean_e + std_e, color="blue", alpha=0.15, label="Mean ± SD")
    ax1.plot(ticks, mean_e, color="blue", linewidth=2.0, label="Group Mean")

    ax2.fill_between(ticks, mean_p - std_p, mean_p + std_p, color="green", alpha=0.15, label="Mean ± SD")
    ax2.plot(ticks, mean_p, color="green", linewidth=2.0, label="Group Mean")

    ax1.axhline(0.70, color="gray", linestyle=":", label="Target 0.70")
    ax1.axhline(0.75, color="gray", linestyle="--", alpha=0.6, label="Target 0.75")
    ax1.axhline(0.0, color="red", linestyle="--", alpha=0.5, label="Death")

    ax2.axhline(0.0, color="red", linestyle="--", alpha=0.5, label="Extinction")
    ax2.axhline(INIT_MOTHERS, color="gray", linestyle=":", label="Initial count")

    ax1.set_title("Energy Trajectory: Mean ± SD")
    ax1.set_ylabel("Mean energy")
    ax1.set_ylim(-0.05, 1.05)

    ax2.set_title("Alive Population: Mean ± SD")
    ax2.set_ylabel("# alive mothers")
    ax2.set_xlabel("Tick")
    ax2.set_ylim(-0.5, INIT_MOTHERS + 1.5)

    summary = (
        f"final alive mean = {np.mean(pop_matrix[:, -1]):.2f}/15\n"
        f"final energy mean = {mean_e[-1]:.3f}\n"
        f"final energy SD = {std_e[-1]:.3f}"
    )

    ax1.text(
        0.01,
        0.04,
        summary,
        transform=ax1.transAxes,
        fontsize=9,
        bbox=dict(facecolor="white", edgecolor="gray", alpha=0.85),
    )

    for ax in (ax1, ax2):
        ax.grid(True, linestyle="--", alpha=0.25)
        ax.legend(loc="lower right", fontsize=7)

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, f"validation_{name}.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def print_validation_runs(name, results):
    for r in results:
        print(
            f"{name.upper()} seed {r['base_seed']} repeat {r['repeat']}: "
            f"run_seed={r['run_seed']} | "
            f"pop={r['final_pop']}/15 | "
            f"meanE={r['mean_energy']:.3f} | "
            f"finalE={r['final_energy']:.3f}"
        )


def save_summary_json(summary, out_dir):
    path = os.path.join(out_dir, "auto_baseline_summary.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)


def save_validation_csv(name, results, out_dir):
    path = os.path.join(out_dir, f"validation_{name}.csv")

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "seed",
                "repeat",
                "run_seed",
                "final_pop",
                "mean_energy",
                "final_energy",
            ],
        )
        writer.writeheader()

        for r in results:
            writer.writerow(
                {
                    "seed": r["base_seed"],
                    "repeat": r["repeat"],
                    "run_seed": r["run_seed"],
                    "final_pop": r["final_pop"],
                    "mean_energy": r["mean_energy"],
                    "final_energy": r["final_energy"],
                }
            )