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


# ============================================================
# Basic utilities
# ============================================================

def pad(x, duration):
    arr = np.full(duration, np.nan)
    x = np.asarray(x, dtype=float)
    arr[: min(duration, len(x))] = x[:duration]
    return arr


def safe(value, nan=0.0):
    return float(np.nan_to_num(value, nan=nan))


def tail_slope(series, duration, tail_window=TAIL_WINDOW):
    y = np.nan_to_num(pad(series, duration), nan=0.0)[-tail_window:]
    x = np.arange(len(y), dtype=float)

    if len(y) < 2:
        return 0.0

    return float(np.polyfit(x, y, 1)[0])


def summarize_repeats(repeat_results, duration, tail_window=TAIL_WINDOW):
    final_pops = np.array([r["final_pop"] for r in repeat_results], dtype=float)
    mean_es = np.array([r["mean_energy"] for r in repeat_results], dtype=float)
    final_es = np.array([r["final_energy"] for r in repeat_results], dtype=float)

    tail_means = []
    energy_slopes = []
    pop_slopes = []

    for r in repeat_results:
        e = np.nan_to_num(pad(r["energy_history"], duration), nan=0.0)

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


def smooth_series(y, window=25):
    if window <= 1:
        return y

    kernel = np.ones(window, dtype=float) / window
    return np.convolve(y, kernel, mode="same")


def pad_event_history(history, duration, keys):
    """
    Convert per-tick event history into fixed-length arrays.

    Example row:
      {
        "MOVE": 3,
        "PICK": 1,
        "EAT": 5,
        "REST": 2,
        "alive": 15,
      }
    """
    arrays = {key: np.zeros(duration, dtype=float) for key in keys}
    alive = np.zeros(duration, dtype=float)

    for t, row in enumerate(history[:duration]):
        for key in keys:
            arrays[key][t] = row.get(key, 0)
        alive[t] = row.get("alive", 0)

    return arrays, alive


def event_rate_matrix(results, history_key, event_key, duration, window=25):
    """
    Build a run x tick matrix for an event rate.
    Rate = event count / alive mothers.
    """
    runs = []

    for r in results:
        history = r.get(history_key, [])
        arrays, alive = pad_event_history(history, duration, [event_key])

        y = np.divide(
            arrays[event_key],
            alive,
            out=np.zeros_like(arrays[event_key], dtype=float),
            where=alive > 0,
        )

        runs.append(smooth_series(y, window=window))

    return np.asarray(runs, dtype=float)


def history_value_matrix(results, history_key, value_key, duration, window=25):
    """
    Build run x tick matrix from a scalar value in per-tick history.
    """
    runs = []

    for r in results:
        history = r.get(history_key, [])
        y = np.zeros(duration, dtype=float)

        for t, row in enumerate(history[:duration]):
            y[t] = row.get(value_key, 0.0)

        runs.append(smooth_series(y, window=window))

    return np.asarray(runs, dtype=float)


def style_axes(ax):
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.tick_params(labelsize=9)


def save_figure(fig, out_dir, filename):
    path = os.path.join(out_dir, filename)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved plot → {path}")


# ============================================================
# Main validation plot
# ============================================================

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

    ax1.fill_between(ticks, mean_e - std_e, mean_e + std_e, color="tab:blue", alpha=0.15, label="Mean ± SD")
    ax1.plot(ticks, mean_e, color="tab:blue", linewidth=2.0, label="Group Mean")

    ax2.fill_between(ticks, mean_p - std_p, mean_p + std_p, color="tab:green", alpha=0.15, label="Mean ± SD")
    ax2.plot(ticks, mean_p, color="tab:green", linewidth=2.0, label="Group Mean")

    ax1.axhline(0.70, color="gray", linestyle=":", label="Target 0.70")
    ax1.axhline(0.75, color="gray", linestyle="--", alpha=0.6, label="Target 0.75")
    ax1.axhline(0.0, color="tab:red", linestyle="--", alpha=0.5, label="Death")

    ax2.axhline(0.0, color="tab:red", linestyle="--", alpha=0.5, label="Extinction")
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
        style_axes(ax)
        ax.legend(loc="lower right", fontsize=7, framealpha=0.88)

    plt.tight_layout()
    save_figure(fig, out_dir, f"validation_{name}.png")


# ============================================================
# Saving / printing
# ============================================================

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
                "MOVE",
                "PICK",
                "EAT",
                "REST",
                "FORAGE",
                "SELF",
                "FAILED_FORAGE",
                "FAILED_SELF",
            ],
        )
        writer.writeheader()

        for r in results:
            actions = r.get("actions", {})
            motivations = r.get("motivations", {})
            failed = r.get("failed", {})

            writer.writerow(
                {
                    "seed": r["base_seed"],
                    "repeat": r["repeat"],
                    "run_seed": r["run_seed"],
                    "final_pop": r["final_pop"],
                    "mean_energy": r["mean_energy"],
                    "final_energy": r["final_energy"],
                    "MOVE": actions.get("MOVE", 0),
                    "PICK": actions.get("PICK", 0),
                    "EAT": actions.get("EAT", 0),
                    "REST": actions.get("REST", 0),
                    "FORAGE": motivations.get("FORAGE", 0),
                    "SELF": motivations.get("SELF", 0),
                    "FAILED_FORAGE": failed.get("FAILED_FORAGE", 0),
                    "FAILED_SELF": failed.get("FAILED_SELF", 0),
                }
            )


# ============================================================
# Action / motivation / failed selection plots
# ============================================================

def plot_event_selection_over_time(
    name,
    results,
    duration,
    out_dir,
    history_key,
    event_keys,
    filename_prefix,
    title_prefix,
    window=25,
    as_rate=True,
):
    """
    Validation-style over-time plot:
      - faint gray individual runs
      - bold colored group mean per event
      - shaded mean ± SD per event
    """
    event_colors = {
        "SELF": "tab:blue",
        "FORAGE": "tab:orange",
        "MOVE": "tab:blue",
        "PICK": "tab:orange",
        "EAT": "tab:green",
        "REST": "tab:red",
        "FAILED_FORAGE": "dimgray",
        "FAILED_SELF": "black",
    }

    per_event_runs = {key: [] for key in event_keys}

    for r in results:
        history = r.get(history_key, [])
        arrays, alive = pad_event_history(history, duration, event_keys)

        for key in event_keys:
            y = arrays[key]

            if as_rate:
                y = np.divide(
                    y,
                    alive,
                    out=np.zeros_like(y, dtype=float),
                    where=alive > 0,
                )

            y = smooth_series(y, window=window)
            per_event_runs[key].append(y)

    ticks = np.arange(duration)

    fig, ax = plt.subplots(figsize=(13, 6))

    first_individual_label = True

    for key in event_keys:
        matrix = np.asarray(per_event_runs[key], dtype=float)

        if matrix.size == 0:
            continue

        for i in range(matrix.shape[0]):
            ax.plot(
                ticks,
                matrix[i],
                alpha=0.06,
                linewidth=0.6,
                color="gray",
                label="Individual Runs" if first_individual_label else "_nolegend_",
            )
            first_individual_label = False

    for key in event_keys:
        matrix = np.asarray(per_event_runs[key], dtype=float)

        if matrix.size == 0:
            continue

        mean_y = np.mean(matrix, axis=0)
        std_y = np.std(matrix, axis=0)
        color = event_colors.get(key, None)

        ax.fill_between(
            ticks,
            mean_y - std_y,
            mean_y + std_y,
            alpha=0.12,
            color=color,
            label=f"{key} Mean ± SD",
        )

        ax.plot(
            ticks,
            mean_y,
            linewidth=2.2,
            color=color,
            label=f"{key} Group Mean",
        )

    ylabel = "Selection rate per alive mother" if as_rate else "Selection count per tick"

    fig.suptitle(
        f"{title_prefix} Over Time — {name.upper()}\n"
        f"Runs: {len(results)} total | smoothing window = {window} ticks",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Individual Runs + Group Mean ± SD")
    ax.set_xlabel("Tick")
    ax.set_ylabel(ylabel)

    if as_rate:
        ax.set_ylim(-0.05, 1.05)

    style_axes(ax)
    ax.legend(loc="upper right", fontsize=7, framealpha=0.88)

    plt.tight_layout()
    save_figure(fig, out_dir, f"{filename_prefix}_{name}.png")


def plot_action_selection_over_time(
    name,
    results,
    duration,
    out_dir,
    window=25,
    as_rate=True,
):
    plot_event_selection_over_time(
        name=name,
        results=results,
        duration=duration,
        out_dir=out_dir,
        history_key="action_history",
        event_keys=["MOVE", "PICK", "EAT", "REST"],
        filename_prefix="action_selection",
        title_prefix="Action Selection",
        window=window,
        as_rate=as_rate,
    )


def plot_motivation_selection_over_time(
    name,
    results,
    duration,
    out_dir,
    window=25,
    as_rate=True,
):
    plot_event_selection_over_time(
        name=name,
        results=results,
        duration=duration,
        out_dir=out_dir,
        history_key="motivation_history",
        event_keys=["FORAGE", "SELF"],
        filename_prefix="motivation_selection",
        title_prefix="Motivation Selection",
        window=window,
        as_rate=as_rate,
    )


def plot_failed_selection_over_time(
    name,
    results,
    duration,
    out_dir,
    window=25,
    as_rate=True,
):
    plot_event_selection_over_time(
        name=name,
        results=results,
        duration=duration,
        out_dir=out_dir,
        history_key="failed_history",
        event_keys=["FAILED_FORAGE", "FAILED_SELF"],
        filename_prefix="failed_selection",
        title_prefix="Failed Selection",
        window=window,
        as_rate=as_rate,
    )


# ============================================================
# 1) Stacked action + failed plot
# ============================================================

def plot_stacked_action_failed_over_time(
    name,
    results,
    duration,
    out_dir,
    window=25,
    as_rate=True,
):
    keys = ["MOVE", "PICK", "EAT", "REST", "FAILED_FORAGE", "FAILED_SELF"]

    color_map = {
        "MOVE": "tab:blue",
        "PICK": "tab:orange",
        "EAT": "tab:green",
        "REST": "tab:red",
        "FAILED_FORAGE": "dimgray",
        "FAILED_SELF": "black",
    }

    per_key_mean = {}

    for key in keys:
        if key in ["MOVE", "PICK", "EAT", "REST"]:
            matrix = event_rate_matrix(results, "action_history", key, duration, window=window)
        else:
            matrix = event_rate_matrix(results, "failed_history", key, duration, window=window)

        per_key_mean[key] = np.mean(matrix, axis=0) if matrix.size else np.zeros(duration)

    ticks = np.arange(duration)

    fig, ax = plt.subplots(figsize=(13, 6))

    ax.stackplot(
        ticks,
        [per_key_mean[k] for k in keys],
        labels=keys,
        colors=[color_map[k] for k in keys],
        alpha=0.82,
    )

    fig.suptitle(
        f"Stacked Action and Failed Selection — {name.upper()}\n"
        f"Mean rate across {len(results)} runs | smoothing window = {window} ticks",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Realized Actions + Failed Motivation Realization")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Rate per alive mother" if as_rate else "Count per tick")
    ax.set_ylim(0.0, 1.15)

    style_axes(ax)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.88, ncol=2)

    plt.tight_layout()
    save_figure(fig, out_dir, f"stacked_action_failed_{name}.png")


# ============================================================
# 2) Correlation: FAILED_SELF vs energy decay
# ============================================================

def plot_failed_self_energy_correlation(
    name,
    results,
    duration,
    out_dir,
    window=25,
):
    xs = []
    ys = []

    for r in results:
        failed_self = event_rate_matrix(
            [r],
            "failed_history",
            "FAILED_SELF",
            duration,
            window=window,
        )[0]

        energy = np.nan_to_num(pad(r["energy_history"], duration), nan=0.0)
        energy_delta = np.diff(energy, prepend=energy[0])

        # Positive value means stronger energy drop.
        energy_drop = np.maximum(0.0, -energy_delta)
        energy_drop = smooth_series(energy_drop, window=window)

        xs.extend(failed_self.tolist())
        ys.extend(energy_drop.tolist())

    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)

    if len(xs) > 1 and np.std(xs) > 0 and np.std(ys) > 0:
        corr = float(np.corrcoef(xs, ys)[0, 1])
    else:
        corr = 0.0

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.scatter(xs, ys, alpha=0.08, s=10, color="steelblue", label="Tick samples")

    if len(xs) > 1:
        coef = np.polyfit(xs, ys, 1)
        xfit = np.linspace(float(np.min(xs)), float(np.max(xs)), 100)
        yfit = coef[0] * xfit + coef[1]
        ax.plot(xfit, yfit, color="tab:red", linewidth=2.0, label="Linear fit")

    fig.suptitle(
        f"FAILED_SELF vs Energy Decay — {name.upper()}\n"
        f"Pearson r = {corr:.3f} | Runs: {len(results)}",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Correlation Diagnostic")
    ax.set_xlabel("FAILED_SELF rate per alive mother")
    ax.set_ylabel("Energy drop per tick")
    style_axes(ax)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.88)

    plt.tight_layout()
    save_figure(fig, out_dir, f"correlation_failed_self_energy_{name}.png")

    csv_path = os.path.join(out_dir, f"correlation_summary_{name}.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerow({"metric": "pearson_failed_self_energy_drop", "value": corr})
        
def plot_failed_forage_energy_correlation(
    name,
    results,
    duration,
    out_dir,
    window=25,
):
    xs = []
    ys = []

    for r in results:
        failed_forage = event_rate_matrix(
            [r],
            "failed_history",
            "FAILED_FORAGE",
            duration,
            window=window,
        )[0]

        energy = np.nan_to_num(pad(r["energy_history"], duration), nan=0.0)
        energy_delta = np.diff(energy, prepend=energy[0])

        # Positive value means stronger energy drop.
        energy_drop = np.maximum(0.0, -energy_delta)
        energy_drop = smooth_series(energy_drop, window=window)

        xs.extend(failed_forage.tolist())
        ys.extend(energy_drop.tolist())

    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)

    if len(xs) > 1 and np.std(xs) > 0 and np.std(ys) > 0:
        corr = float(np.corrcoef(xs, ys)[0, 1])
    else:
        corr = 0.0

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.scatter(xs, ys, alpha=0.08, s=10, color="steelblue", label="Tick samples")

    if len(xs) > 1:
        coef = np.polyfit(xs, ys, 1)
        xfit = np.linspace(float(np.min(xs)), float(np.max(xs)), 100)
        yfit = coef[0] * xfit + coef[1]
        ax.plot(xfit, yfit, color="tab:red", linewidth=2.0, label="Linear fit")

    fig.suptitle(
        f"FAILED_FORAGE vs Energy Decay — {name.upper()}\n"
        f"Pearson r = {corr:.3f} | Runs: {len(results)}",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Correlation Diagnostic")
    ax.set_xlabel("FAILED_FORAGE rate per alive mother")
    ax.set_ylabel("Energy drop per tick")
    style_axes(ax)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.88)

    plt.tight_layout()
    save_figure(fig, out_dir, f"correlation_failed_forage_energy_{name}.png")

    csv_path = os.path.join(out_dir, f"correlation_failed_forage_summary_{name}.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerow({"metric": "pearson_failed_forage_energy_drop", "value": corr})


# ============================================================
# 3) State-space scatter: energy vs action/motivation rate
# ============================================================

def plot_state_space_energy_action(
    name,
    results,
    duration,
    out_dir,
    window=25,
):
    plot_items = [
        ("REST", "action_history", "REST", "tab:red"),
        ("EAT", "action_history", "EAT", "tab:green"),
        ("SELF", "motivation_history", "SELF", "tab:blue"),
        ("FORAGE", "motivation_history", "FORAGE", "tab:orange"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharex=True, sharey=True)
    axes_flat = axes.flatten()

    energy_all = np.concatenate(
        [np.nan_to_num(pad(r["energy_history"], duration), nan=0.0) for r in results]
    )

    for ax, (label, history_key, event_key, color) in zip(axes_flat, plot_items):
        rate_matrix = event_rate_matrix(
            results,
            history_key,
            event_key,
            duration,
            window=window,
        )

        rate_all = rate_matrix.reshape(-1)

        ax.scatter(energy_all, rate_all, alpha=0.06, s=8, color=color)

        # Bin energy to show average trend.
        bins = np.linspace(0.0, 1.0, 21)
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        bin_means = []

        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (energy_all >= lo) & (energy_all < hi)
            bin_means.append(float(np.mean(rate_all[mask])) if np.any(mask) else np.nan)

        ax.plot(bin_centers, bin_means, color="black", linewidth=2.0, label="Binned mean")
        ax.set_title(f"Energy vs {label}")
        ax.set_xlabel("Mean energy")
        ax.set_ylabel("Selection rate")
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.05, 1.05)
        style_axes(ax)
        ax.legend(loc="upper right", fontsize=7, framealpha=0.88)

    fig.suptitle(
        f"State Space: Energy vs Action/Motivation — {name.upper()}\n"
        f"Tick samples across {len(results)} runs | smoothing window = {window}",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout()
    save_figure(fig, out_dir, f"state_space_energy_action_{name}.png")


# ============================================================
# 4) Food consumption rate over time
# ============================================================

def plot_food_consumption_over_time(
    name,
    results,
    duration,
    out_dir,
    window=25,
):
    ticks = np.arange(duration)

    pick_matrix = event_rate_matrix(results, "food_history", "PICK", duration, window=window)
    eat_matrix = event_rate_matrix(results, "food_history", "EAT", duration, window=window)

    food_available_matrix = history_value_matrix(
        results,
        "food_history",
        "food_available",
        duration,
        window=window,
    )

    pick_mean, pick_sd = np.mean(pick_matrix, axis=0), np.std(pick_matrix, axis=0)
    eat_mean, eat_sd = np.mean(eat_matrix, axis=0), np.std(eat_matrix, axis=0)
    food_mean, food_sd = np.mean(food_available_matrix, axis=0), np.std(food_available_matrix, axis=0)

    fig, ax1 = plt.subplots(figsize=(13, 6))
    ax2 = ax1.twinx()

    for i in range(eat_matrix.shape[0]):
        ax1.plot(
            ticks,
            eat_matrix[i],
            alpha=0.06,
            linewidth=0.6,
            color="gray",
            label="Individual Runs" if i == 0 else "_nolegend_",
        )

    ax1.fill_between(ticks, eat_mean - eat_sd, eat_mean + eat_sd, color="tab:green", alpha=0.12, label="EAT Mean ± SD")
    ax1.plot(ticks, eat_mean, color="tab:green", linewidth=2.2, label="EAT Group Mean")

    ax1.fill_between(ticks, pick_mean - pick_sd, pick_mean + pick_sd, color="tab:orange", alpha=0.12, label="PICK Mean ± SD")
    ax1.plot(ticks, pick_mean, color="tab:orange", linewidth=2.2, label="PICK Group Mean")

    ax2.fill_between(ticks, food_mean - food_sd, food_mean + food_sd, color="tab:blue", alpha=0.08, label="Food Count Mean ± SD")
    ax2.plot(ticks, food_mean, color="tab:blue", linestyle="--", linewidth=2.0, label="Food Available")

    fig.suptitle(
        f"Food Consumption Rate Over Time — {name.upper()}\n"
        f"Runs: {len(results)} total | smoothing window = {window} ticks",
        fontsize=14,
        fontweight="bold",
    )

    ax1.set_title("PICK/EAT Rates and Available Food")
    ax1.set_xlabel("Tick")
    ax1.set_ylabel("Action rate per alive mother")
    ax2.set_ylabel("Food available count")

    ax1.set_ylim(-0.05, 1.05)

    style_axes(ax1)
    style_axes(ax2)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=7, framealpha=0.88)

    plt.tight_layout()
    save_figure(fig, out_dir, f"food_consumption_rate_{name}.png")


# ============================================================
# 5) Spatial heatmap of population
# ============================================================

def plot_spatial_heatmap_population(
    name,
    results,
    out_dir,
):
    heatmaps = []

    for r in results:
        h = r.get("spatial_heatmap", None)
        if h is not None:
            heatmaps.append(np.asarray(h, dtype=float))

    if not heatmaps:
        return

    mean_heatmap = np.mean(np.asarray(heatmaps, dtype=float), axis=0)

    if np.max(mean_heatmap) > 0:
        normalized_heatmap = mean_heatmap / np.max(mean_heatmap)
    else:
        normalized_heatmap = mean_heatmap

    fig, ax = plt.subplots(figsize=(7, 6))

    im = ax.imshow(
        normalized_heatmap,
        origin="lower",
        interpolation="nearest",
        aspect="equal",
    )

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Normalized visit density", fontsize=9)

    fig.suptitle(
        f"Spatial Heatmap of Mother Population — {name.upper()}\n"
        f"Mean visitation density across {len(results)} runs",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Population Occupancy Heatmap")
    ax.set_xlabel("Grid X")
    ax.set_ylabel("Grid Y")
    style_axes(ax)

    plt.tight_layout()
    save_figure(fig, out_dir, f"spatial_heatmap_population_{name}.png")


# ============================================================
# 6) Energy expenditure breakdown
# ============================================================

def plot_energy_expenditure_breakdown(
    name,
    results,
    out_dir,
):
    rows = []

    for r in results:
        history = r.get("energy_flow_history", [])

        hunger_loss = sum(row.get("hunger_loss", 0.0) for row in history)
        move_loss = sum(row.get("move_loss", 0.0) for row in history)
        eat_gain = sum(row.get("eat_gain", 0.0) for row in history)
        net_energy_change = sum(row.get("net_energy_change", 0.0) for row in history)

        rows.append(
            {
                "hunger_loss": hunger_loss,
                "move_loss": move_loss,
                "eat_gain": eat_gain,
                "net_energy_change": net_energy_change,
            }
        )

    if not rows:
        return

    keys = ["hunger_loss", "move_loss", "eat_gain", "net_energy_change"]
    means = {k: float(np.mean([row[k] for row in rows])) for k in keys}
    sds = {k: float(np.std([row[k] for row in rows])) for k in keys}

    labels = ["Hunger loss", "Move loss", "Eat gain", "Net energy change"]
    values = [
        means["hunger_loss"],
        means["move_loss"],
        means["eat_gain"],
        means["net_energy_change"],
    ]
    errors = [
        sds["hunger_loss"],
        sds["move_loss"],
        sds["eat_gain"],
        sds["net_energy_change"],
    ]

    colors = ["tab:red", "tab:orange", "tab:green", "tab:blue"]

    fig, ax = plt.subplots(figsize=(9, 6))

    x = np.arange(len(labels))
    ax.bar(x, values, yerr=errors, capsize=5, color=colors, alpha=0.82)

    fig.suptitle(
        f"Energy Expenditure Breakdown — {name.upper()}\n"
        f"Mean ± SD across {len(results)} runs",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Episode-Level Energy Flow")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Total energy over episode")
    ax.axhline(0.0, color="black", linewidth=1.0, alpha=0.7)

    style_axes(ax)

    summary = (
        f"hunger = {means['hunger_loss']:.3f}\n"
        f"move = {means['move_loss']:.3f}\n"
        f"eat gain = {means['eat_gain']:.3f}\n"
        f"net = {means['net_energy_change']:.3f}"
    )
    ax.text(
        0.02,
        0.96,
        summary,
        transform=ax.transAxes,
        fontsize=9,
        va="top",
        bbox=dict(facecolor="white", edgecolor="gray", alpha=0.85),
    )

    plt.tight_layout()
    save_figure(fig, out_dir, f"energy_expenditure_breakdown_{name}.png")