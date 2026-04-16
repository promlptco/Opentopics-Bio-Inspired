import os
import csv
import json

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from experiments.phase3_survival_full.config import (
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


def smooth_series(y, window=25):
    if window <= 1:
        return y

    kernel = np.ones(window, dtype=float) / window
    return np.convolve(y, kernel, mode="same")


def style_axes(ax):
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.tick_params(labelsize=9)


def save_figure(fig, out_dir, filename):
    path = os.path.join(out_dir, filename)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved plot → {path}")


def config_title(params):
    return (
        f"perception={params.get('perception_radius', DEFAULT_PERCEPTION_RADIUS)} | "
        f"hunger={params['hunger_rate']} | move={params['move_cost']} | "
        f"eat={params['eat_gain']} | food={params['init_food']} | "
        f"child_hunger={params['child_hunger_rate']} | "
        f"feed_amount={params['feed_amount']} | feed_cost={params['feed_cost']}"
    )


def pad_event_history(history, duration, keys):
    arrays = {key: np.zeros(duration, dtype=float) for key in keys}
    alive = np.zeros(duration, dtype=float)

    for t, row in enumerate(history[:duration]):
        for key in keys:
            arrays[key][t] = row.get(key, 0)
        alive[t] = row.get("alive", 0)

    return arrays, alive


def event_rate_matrix(results, history_key, event_key, duration, window=25):
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
    runs = []

    for r in results:
        history = r.get(history_key, [])
        y = np.zeros(duration, dtype=float)

        for t, row in enumerate(history[:duration]):
            y[t] = row.get(value_key, 0.0)

        runs.append(smooth_series(y, window=window))

    return np.asarray(runs, dtype=float)


# ============================================================
# Summary
# ============================================================

def summarize_repeats(repeat_results, duration, tail_window=TAIL_WINDOW):
    final_mothers = np.array([r["final_mothers"] for r in repeat_results], dtype=float)
    final_children = np.array([r["final_children"] for r in repeat_results], dtype=float)

    mean_mother_energy = np.array([r["mean_mother_energy"] for r in repeat_results], dtype=float)
    final_mother_energy = np.array([r["final_mother_energy"] for r in repeat_results], dtype=float)

    mean_child_hunger = np.array([r["mean_child_hunger"] for r in repeat_results], dtype=float)
    final_child_hunger = np.array([r["final_child_hunger"] for r in repeat_results], dtype=float)

    mean_child_distress = np.array([r["mean_child_distress"] for r in repeat_results], dtype=float)
    final_child_distress = np.array([r["final_child_distress"] for r in repeat_results], dtype=float)

    tail_mother_energy = []
    tail_child_hunger = []
    tail_child_distress = []
    tail_distance = []

    mother_energy_slopes = []
    child_hunger_slopes = []
    child_distress_slopes = []

    for r in repeat_results:
        mother_energy = np.nan_to_num(pad(r["mother_energy_history"], duration), nan=0.0)
        child_hunger = np.nan_to_num(pad(r["child_hunger_history"], duration), nan=0.0)
        child_distress = np.nan_to_num(pad(r["child_distress_history"], duration), nan=0.0)
        distance = np.nan_to_num(pad(r["mother_child_distance_history"], duration), nan=0.0)

        tail_mother_energy.append(np.mean(mother_energy[-tail_window:]))
        tail_child_hunger.append(np.mean(child_hunger[-tail_window:]))
        tail_child_distress.append(np.mean(child_distress[-tail_window:]))
        tail_distance.append(np.mean(distance[-tail_window:]))

        mother_energy_slopes.append(tail_slope(r["mother_energy_history"], duration, tail_window))
        child_hunger_slopes.append(tail_slope(r["child_hunger_history"], duration, tail_window))
        child_distress_slopes.append(tail_slope(r["child_distress_history"], duration, tail_window))

    return {
        "final_mothers": float(np.mean(final_mothers)),
        "final_mothers_sd": float(np.std(final_mothers)),
        "final_children": float(np.mean(final_children)),
        "final_children_sd": float(np.std(final_children)),

        "mother_survival_rate": float(np.mean(final_mothers) / INIT_MOTHERS),
        "child_survival_rate": float(np.mean(final_children) / INIT_MOTHERS),

        "mean_mother_energy": float(np.mean(mean_mother_energy)),
        "final_mother_energy": float(np.mean(final_mother_energy)),
        "mean_child_hunger": float(np.mean(mean_child_hunger)),
        "final_child_hunger": float(np.mean(final_child_hunger)),
        "mean_child_distress": float(np.mean(mean_child_distress)),
        "final_child_distress": float(np.mean(final_child_distress)),

        "tail_mother_energy": float(np.mean(tail_mother_energy)),
        "tail_mother_energy_sd": float(np.std(tail_mother_energy)),
        "tail_child_hunger": float(np.mean(tail_child_hunger)),
        "tail_child_hunger_sd": float(np.std(tail_child_hunger)),
        "tail_child_distress": float(np.mean(tail_child_distress)),
        "tail_child_distress_sd": float(np.std(tail_child_distress)),
        "tail_mother_child_distance": float(np.mean(tail_distance)),
        "tail_mother_child_distance_sd": float(np.std(tail_distance)),

        "tail_mother_energy_slope": float(np.mean(mother_energy_slopes)),
        "tail_child_hunger_slope": float(np.mean(child_hunger_slopes)),
        "tail_child_distress_slope": float(np.mean(child_distress_slopes)),
    }


# ============================================================
# Save / print
# ============================================================

def print_validation_runs(name, results):
    for r in results:
        print(
            f"{name.upper()} seed {r['base_seed']} repeat {r['repeat']}: "
            f"run_seed={r['run_seed']} | "
            f"mothers={r['final_mothers']}/15 | "
            f"children={r['final_children']}/15 | "
            f"motherE={r['final_mother_energy']:.3f} | "
            f"childH={r['final_child_hunger']:.3f} | "
            f"childD={r['final_child_distress']:.3f}"
        )


def save_summary_json(summary, out_dir):
    path = os.path.join(out_dir, "auto_phase3_summary.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)


def save_validation_csv(name, results, out_dir):
    path = os.path.join(out_dir, f"validation_{name}.csv")

    fieldnames = [
        "seed",
        "repeat",
        "run_seed",
        "final_mothers",
        "final_children",
        "mean_mother_energy",
        "final_mother_energy",
        "mean_child_hunger",
        "final_child_hunger",
        "mean_child_distress",
        "final_child_distress",
        "MOVE_FOOD",
        "PICK",
        "EAT",
        "MOVE_CHILD",
        "FEED",
        "REST",
        "FORAGE",
        "CARE",
        "SELF",
        "FAILED_FORAGE",
        "FAILED_CARE",
        "FAILED_SELF",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
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
                    "final_mothers": r["final_mothers"],
                    "final_children": r["final_children"],
                    "mean_mother_energy": r["mean_mother_energy"],
                    "final_mother_energy": r["final_mother_energy"],
                    "mean_child_hunger": r["mean_child_hunger"],
                    "final_child_hunger": r["final_child_hunger"],
                    "mean_child_distress": r["mean_child_distress"],
                    "final_child_distress": r["final_child_distress"],
                    "MOVE_FOOD": actions.get("MOVE_FOOD", 0),
                    "PICK": actions.get("PICK", 0),
                    "EAT": actions.get("EAT", 0),
                    "MOVE_CHILD": actions.get("MOVE_CHILD", 0),
                    "FEED": actions.get("FEED", 0),
                    "REST": actions.get("REST", 0),
                    "FORAGE": motivations.get("FORAGE", 0),
                    "CARE": motivations.get("CARE", 0),
                    "SELF": motivations.get("SELF", 0),
                    "FAILED_FORAGE": failed.get("FAILED_FORAGE", 0),
                    "FAILED_CARE": failed.get("FAILED_CARE", 0),
                    "FAILED_SELF": failed.get("FAILED_SELF", 0),
                }
            )


# ============================================================
# Main validation plot
# ============================================================

def plot_multiseed_condition(name, results, params, run_labels, duration, out_dir):
    ticks = np.arange(duration)

    mother_energy_matrix = np.asarray(
        [np.nan_to_num(pad(r["mother_energy_history"], duration), nan=0.0) for r in results]
    )
    mother_pop_matrix = np.asarray(
        [np.nan_to_num(pad(r["mother_population_history"], duration), nan=0.0) for r in results]
    )
    child_pop_matrix = np.asarray(
        [np.nan_to_num(pad(r["child_population_history"], duration), nan=0.0) for r in results]
    )
    child_hunger_matrix = np.asarray(
        [np.nan_to_num(pad(r["child_hunger_history"], duration), nan=0.0) for r in results]
    )
    child_distress_matrix = np.asarray(
        [np.nan_to_num(pad(r["child_distress_history"], duration), nan=0.0) for r in results]
    )

    mean_energy = np.mean(mother_energy_matrix, axis=0)
    std_energy = np.std(mother_energy_matrix, axis=0)

    mean_mother_pop = np.mean(mother_pop_matrix, axis=0)
    std_mother_pop = np.std(mother_pop_matrix, axis=0)

    mean_child_pop = np.mean(child_pop_matrix, axis=0)
    std_child_pop = np.std(child_pop_matrix, axis=0)

    mean_child_hunger = np.mean(child_hunger_matrix, axis=0)
    std_child_hunger = np.std(child_hunger_matrix, axis=0)

    mean_child_distress = np.mean(child_distress_matrix, axis=0)
    std_child_distress = np.std(child_distress_matrix, axis=0)

    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
    ax1, ax2, ax3 = axes

    fig.suptitle(
        f"Phase 3 Mother-Child Validation — {name.upper()}\n"
        f"Runs: {len(results)} total | {config_title(params)}",
        fontsize=14,
        fontweight="bold",
    )

    for i in range(len(results)):
        label = "Individual Runs" if i == 0 else "_nolegend_"
        ax1.plot(ticks, mother_energy_matrix[i], alpha=0.12, linewidth=0.8, color="gray", label=label)
        ax2.step(ticks, mother_pop_matrix[i], where="post", alpha=0.10, linewidth=0.8, color="gray", label=label)
        ax2.step(ticks, child_pop_matrix[i], where="post", alpha=0.10, linewidth=0.8, color="gray")
        ax3.plot(ticks, child_hunger_matrix[i], alpha=0.10, linewidth=0.8, color="gray", label=label)

    ax1.fill_between(ticks, mean_energy - std_energy, mean_energy + std_energy, color="tab:blue", alpha=0.15, label="Mother Energy Mean ± SD")
    ax1.plot(ticks, mean_energy, color="tab:blue", linewidth=2.0, label="Mother Energy Mean")

    ax2.fill_between(ticks, mean_mother_pop - std_mother_pop, mean_mother_pop + std_mother_pop, color="tab:green", alpha=0.12, label="Mother Pop Mean ± SD")
    ax2.plot(ticks, mean_mother_pop, color="tab:green", linewidth=2.0, label="Mother Pop Mean")

    ax2.fill_between(ticks, mean_child_pop - std_child_pop, mean_child_pop + std_child_pop, color="tab:orange", alpha=0.12, label="Child Pop Mean ± SD")
    ax2.plot(ticks, mean_child_pop, color="tab:orange", linewidth=2.0, label="Child Pop Mean")

    ax3.fill_between(ticks, mean_child_hunger - std_child_hunger, mean_child_hunger + std_child_hunger, color="tab:red", alpha=0.12, label="Child Hunger Mean ± SD")
    ax3.plot(ticks, mean_child_hunger, color="tab:red", linewidth=2.0, label="Child Hunger Mean")

    ax3.fill_between(ticks, mean_child_distress - std_child_distress, mean_child_distress + std_child_distress, color="tab:purple", alpha=0.10, label="Child Distress Mean ± SD")
    ax3.plot(ticks, mean_child_distress, color="tab:purple", linewidth=2.0, label="Child Distress Mean")

    ax1.axhline(0.70, color="gray", linestyle=":", alpha=0.7, label="Energy target 0.70")
    ax1.axhline(0.0, color="tab:red", linestyle="--", alpha=0.5)

    ax2.axhline(INIT_MOTHERS, color="gray", linestyle=":", alpha=0.7, label="Initial count")
    ax2.axhline(0.0, color="tab:red", linestyle="--", alpha=0.5)

    ax3.axhline(1.0, color="tab:red", linestyle="--", alpha=0.5, label="Starvation threshold")
    ax3.axhline(0.35, color="gray", linestyle=":", alpha=0.7, label="Target hunger ≤ 0.35")

    ax1.set_title("Mother Energy")
    ax1.set_ylabel("Mean energy")
    ax1.set_ylim(-0.05, 1.05)

    ax2.set_title("Mother and Child Survival")
    ax2.set_ylabel("# alive")
    ax2.set_ylim(-0.5, INIT_MOTHERS + 1.5)

    ax3.set_title("Child Hunger and Distress")
    ax3.set_ylabel("Mean state")
    ax3.set_xlabel("Tick")
    ax3.set_ylim(-0.05, 1.05)

    summary = (
        f"final mothers = {np.mean(mother_pop_matrix[:, -1]):.2f}/15\n"
        f"final children = {np.mean(child_pop_matrix[:, -1]):.2f}/15\n"
        f"final mother E = {mean_energy[-1]:.3f}\n"
        f"final child H = {mean_child_hunger[-1]:.3f}"
    )

    ax1.text(
        0.01,
        0.04,
        summary,
        transform=ax1.transAxes,
        fontsize=9,
        bbox=dict(facecolor="white", edgecolor="gray", alpha=0.85),
    )

    for ax in axes:
        style_axes(ax)
        ax.legend(loc="upper right", fontsize=7, framealpha=0.88)

    plt.tight_layout()
    save_figure(fig, out_dir, f"validation_{name}.png")


# ============================================================
# Event selection plots
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
    event_colors = {
        "FORAGE": "tab:orange",
        "CARE": "tab:purple",
        "SELF": "tab:blue",
        "MOVE_FOOD": "tab:blue",
        "PICK": "tab:orange",
        "EAT": "tab:green",
        "MOVE_CHILD": "tab:purple",
        "FEED": "tab:pink",
        "REST": "tab:red",
        "FAILED_FORAGE": "dimgray",
        "FAILED_CARE": "slategray",
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

            per_event_runs[key].append(smooth_series(y, window=window))

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
                alpha=0.05,
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
    ax.legend(loc="upper right", fontsize=7, framealpha=0.88, ncol=2)

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
        event_keys=["MOVE_FOOD", "PICK", "EAT", "MOVE_CHILD", "FEED", "REST"],
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
        event_keys=["FORAGE", "CARE", "SELF"],
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
        event_keys=["FAILED_FORAGE", "FAILED_CARE", "FAILED_SELF"],
        filename_prefix="failed_selection",
        title_prefix="Failed Selection",
        window=window,
        as_rate=as_rate,
    )


# ============================================================
# Mother-child specific diagnostics
# ============================================================

def plot_mother_child_diagnostics(
    name,
    results,
    duration,
    out_dir,
    window=25,
):
    ticks = np.arange(duration)

    hunger_matrix = np.asarray(
        [smooth_series(np.nan_to_num(pad(r["child_hunger_history"], duration), nan=0.0), window) for r in results]
    )
    distress_matrix = np.asarray(
        [smooth_series(np.nan_to_num(pad(r["child_distress_history"], duration), nan=0.0), window) for r in results]
    )
    distance_matrix = np.asarray(
        [smooth_series(np.nan_to_num(pad(r["mother_child_distance_history"], duration), nan=0.0), window) for r in results]
    )
    child_pop_matrix = np.asarray(
        [np.nan_to_num(pad(r["child_population_history"], duration), nan=0.0) for r in results]
    )

    fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True)
    ax1, ax2, ax3 = axes

    for i in range(len(results)):
        label = "Individual Runs" if i == 0 else "_nolegend_"
        ax1.plot(ticks, hunger_matrix[i], color="gray", alpha=0.08, linewidth=0.7, label=label)
        ax2.plot(ticks, distress_matrix[i], color="gray", alpha=0.08, linewidth=0.7, label=label)
        ax3.plot(ticks, distance_matrix[i], color="gray", alpha=0.08, linewidth=0.7, label=label)

    for ax, matrix, color, label, ylabel in [
        (ax1, hunger_matrix, "tab:red", "Child Hunger", "Hunger"),
        (ax2, distress_matrix, "tab:purple", "Child Distress", "Distress"),
        (ax3, distance_matrix, "tab:blue", "Mother-Child Distance", "Distance"),
    ]:
        mean_y = np.mean(matrix, axis=0)
        std_y = np.std(matrix, axis=0)

        ax.fill_between(ticks, mean_y - std_y, mean_y + std_y, color=color, alpha=0.12, label=f"{label} Mean ± SD")
        ax.plot(ticks, mean_y, color=color, linewidth=2.2, label=f"{label} Group Mean")
        ax.set_ylabel(ylabel)
        style_axes(ax)
        ax.legend(loc="upper right", fontsize=7, framealpha=0.88)

    ax1.axhline(1.0, color="tab:red", linestyle="--", alpha=0.5, label="Death threshold")
    ax1.axhline(0.35, color="gray", linestyle=":", alpha=0.7, label="Target hunger")
    ax2.axhline(0.40, color="gray", linestyle=":", alpha=0.7, label="Target distress")

    ax3.set_xlabel("Tick")

    fig.suptitle(
        f"Mother-Child Diagnostics — {name.upper()}\n"
        f"Child state and spatial coupling across {len(results)} runs",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout()
    save_figure(fig, out_dir, f"mother_child_diagnostics_{name}.png")


def plot_feed_rate_over_time(
    name,
    results,
    duration,
    out_dir,
    window=25,
):
    ticks = np.arange(duration)

    feed_matrix = event_rate_matrix(results, "feed_history", "FEED", duration, window=window)
    success_matrix = event_rate_matrix(results, "feed_history", "feed_success", duration, window=window)
    hunger_reduced_matrix = history_value_matrix(results, "feed_history", "hunger_reduced", duration, window=window)

    fig, ax1 = plt.subplots(figsize=(13, 6))
    ax2 = ax1.twinx()

    for i in range(feed_matrix.shape[0]):
        ax1.plot(
            ticks,
            feed_matrix[i],
            alpha=0.06,
            linewidth=0.6,
            color="gray",
            label="Individual Runs" if i == 0 else "_nolegend_",
        )

    feed_mean, feed_sd = np.mean(feed_matrix, axis=0), np.std(feed_matrix, axis=0)
    success_mean, success_sd = np.mean(success_matrix, axis=0), np.std(success_matrix, axis=0)
    reduced_mean, reduced_sd = np.mean(hunger_reduced_matrix, axis=0), np.std(hunger_reduced_matrix, axis=0)

    ax1.fill_between(ticks, feed_mean - feed_sd, feed_mean + feed_sd, color="tab:pink", alpha=0.12, label="FEED Mean ± SD")
    ax1.plot(ticks, feed_mean, color="tab:pink", linewidth=2.2, label="FEED Group Mean")

    ax1.fill_between(ticks, success_mean - success_sd, success_mean + success_sd, color="tab:purple", alpha=0.10, label="Feed Success Mean ± SD")
    ax1.plot(ticks, success_mean, color="tab:purple", linewidth=2.0, label="Feed Success")

    ax2.fill_between(ticks, reduced_mean - reduced_sd, reduced_mean + reduced_sd, color="tab:green", alpha=0.08, label="Hunger Reduced Mean ± SD")
    ax2.plot(ticks, reduced_mean, color="tab:green", linestyle="--", linewidth=2.0, label="Hunger Reduced")

    fig.suptitle(
        f"Feed Rate Over Time — {name.upper()}\n"
        f"Care action and child hunger reduction across {len(results)} runs",
        fontsize=14,
        fontweight="bold",
    )

    ax1.set_title("Feeding Behavior and Hunger Reduction")
    ax1.set_xlabel("Tick")
    ax1.set_ylabel("Feed rate per alive mother")
    ax2.set_ylabel("Child hunger reduced per tick")

    ax1.set_ylim(-0.05, 1.05)

    style_axes(ax1)
    style_axes(ax2)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=7, framealpha=0.88)

    plt.tight_layout()
    save_figure(fig, out_dir, f"feed_rate_{name}.png")


def plot_spatial_heatmap(
    name,
    results,
    out_dir,
):
    mother_heatmaps = []
    child_heatmaps = []

    for r in results:
        mh = r.get("spatial_heatmap_mother", None)
        ch = r.get("spatial_heatmap_child", None)

        if mh is not None:
            mother_heatmaps.append(np.asarray(mh, dtype=float))
        if ch is not None:
            child_heatmaps.append(np.asarray(ch, dtype=float))

    if not mother_heatmaps and not child_heatmaps:
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, heatmaps, title in [
        (axes[0], mother_heatmaps, "Mother Occupancy"),
        (axes[1], child_heatmaps, "Child Occupancy"),
    ]:
        if heatmaps:
            mean_heatmap = np.mean(np.asarray(heatmaps, dtype=float), axis=0)
            if np.max(mean_heatmap) > 0:
                mean_heatmap = mean_heatmap / np.max(mean_heatmap)
        else:
            mean_heatmap = np.zeros_like(np.asarray(mother_heatmaps[0], dtype=float))

        im = ax.imshow(mean_heatmap, origin="lower", interpolation="nearest", aspect="equal")
        ax.set_title(title)
        ax.set_xlabel("Grid X")
        ax.set_ylabel("Grid Y")
        style_axes(ax)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle(
        f"Spatial Heatmap — {name.upper()}\n"
        f"Mean normalized visitation density across {len(results)} runs",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout()
    save_figure(fig, out_dir, f"spatial_heatmap_{name}.png")