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
        f"eat={params['eat_gain']} | food={params['init_food']} | rest={params['rest_recovery']} | "
        f"Fw={params.get('forage_weight', 1.0)} | Sw={params.get('self_weight', 1.0)} | "
        f"Cw={params.get('care_weight', 0.0)}"
    )


def smooth_series(y, window=25):
    if window <= 1:
        return y

    kernel = np.ones(window, dtype=float) / window
    return np.convolve(y, kernel, mode="same")


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


_ANNOT_BOX = dict(
    boxstyle="round,pad=0.4",
    facecolor="white",
    edgecolor="#cccccc",
    alpha=0.90,
)

_LEGEND_KW = dict(fontsize=8, framealpha=0.92, edgecolor="#cccccc", fancybox=True)


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.35, color="#888888")
    ax.grid(True, which="minor", linestyle=":", linewidth=0.35, alpha=0.2, color="#aaaaaa")
    ax.minorticks_on()
    ax.tick_params(which="major", labelsize=9, length=4, width=0.8)
    ax.tick_params(which="minor", labelsize=0, length=2, width=0.5)
    ax.set_facecolor("#fafafa")
    ax.xaxis.label.set_size(10)
    ax.yaxis.label.set_size(10)
    ax.title.set_size(11)


def save_figure(fig, out_dir, filename):
    fig.patch.set_facecolor("white")
    path = os.path.join(out_dir, filename)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
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
        f"MotherAgent | Runs: {len(results)} total | {config_title(params)}",
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
        bbox=_ANNOT_BOX,
    )

    for ax in (ax1, ax2):
        style_axes(ax)
        ax.legend(loc="lower right", **_LEGEND_KW)

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
                "mean_fatigue",
                "final_fatigue",
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

            fatigue_history = r.get("fatigue_history", [])
            mean_fatigue = float(np.mean(fatigue_history)) if fatigue_history else 0.0
            final_fatigue = float(fatigue_history[-1]) if fatigue_history else 0.0

            writer.writerow(
                {
                    "seed": r["base_seed"],
                    "repeat": r["repeat"],
                    "run_seed": r["run_seed"],
                    "final_pop": r["final_pop"],
                    "mean_energy": r["mean_energy"],
                    "final_energy": r["final_energy"],
                    "mean_fatigue": mean_fatigue,
                    "final_fatigue": final_fatigue,
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
        f"MotherAgent | Runs: {len(results)} total | smoothing window = {window} ticks",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Individual Runs + Group Mean ± SD")
    ax.set_xlabel("Tick")
    ax.set_ylabel(ylabel)

    if as_rate:
        ax.set_ylim(-0.05, 1.05)

    style_axes(ax)
    ax.legend(loc="upper right", **_LEGEND_KW)

    plt.tight_layout()
    save_figure(fig, out_dir, f"{filename_prefix}_{name}.png")


def plot_action_selection_over_time(name, results, duration, out_dir, window=25, as_rate=True):
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


def plot_motivation_selection_over_time(name, results, duration, out_dir, window=25, as_rate=True):
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


def plot_failed_selection_over_time(name, results, duration, out_dir, window=25, as_rate=True):
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

def plot_stacked_action_failed_over_time(name, results, duration, out_dir, window=25, as_rate=True):
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
        f"MotherAgent | Mean rate across {len(results)} runs | window = {window}",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Realized Actions + Failed Motivation Realization")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Rate per alive mother" if as_rate else "Count per tick")
    ax.set_ylim(0.0, 1.15)

    style_axes(ax)
    ax.legend(loc="upper right", ncol=2, **_LEGEND_KW)

    plt.tight_layout()
    save_figure(fig, out_dir, f"stacked_action_failed_{name}.png")


# ============================================================
# 2) Correlation plots
# ============================================================

def _plot_failed_energy_correlation(name, results, duration, out_dir, failed_key, filename, metric_name, window=25):
    xs = []
    ys = []

    for r in results:
        failed_rate = event_rate_matrix(
            [r],
            "failed_history",
            failed_key,
            duration,
            window=window,
        )[0]

        energy = np.nan_to_num(pad(r["energy_history"], duration), nan=0.0)
        energy_delta = np.diff(energy, prepend=energy[0])

        # Positive value means stronger energy drop.
        energy_drop = np.maximum(0.0, -energy_delta)
        energy_drop = smooth_series(energy_drop, window=window)

        xs.extend(failed_rate.tolist())
        ys.extend(energy_drop.tolist())

    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)

    # Remove invalid samples before correlation and linear fit.
    valid_mask = np.isfinite(xs) & np.isfinite(ys)
    xs = xs[valid_mask]
    ys = ys[valid_mask]

    # Default values if the data is degenerate.
    corr = 0.0
    can_fit = (
        len(xs) >= 3
        and np.std(xs) > 1e-12
        and np.std(ys) > 1e-12
        and np.all(np.isfinite(xs))
        and np.all(np.isfinite(ys))
    )

    if can_fit:
        corr = float(np.corrcoef(xs, ys)[0, 1])

    fig, ax = plt.subplots(figsize=(8, 6))

    if len(xs) > 0:
        ax.scatter(xs, ys, alpha=0.08, s=10, color="steelblue", label="Tick samples")

    # Linear fit only when data is numerically valid.
    if can_fit:
        try:
            coef = np.polyfit(xs, ys, 1)
            xfit = np.linspace(float(np.min(xs)), float(np.max(xs)), 100)
            yfit = coef[0] * xfit + coef[1]

            ax.plot(
                xfit,
                yfit,
                color="tab:red",
                linewidth=2.0,
                label="Linear fit",
            )
        except np.linalg.LinAlgError:
            ax.text(
                0.02,
                0.95,
                "Linear fit skipped: SVD did not converge",
                transform=ax.transAxes,
                fontsize=9,
                va="top",
                bbox=_ANNOT_BOX,
            )
    else:
        ax.text(
            0.02,
            0.95,
            "Linear fit skipped: insufficient variance or invalid samples",
            transform=ax.transAxes,
            fontsize=9,
            va="top",
            bbox=_ANNOT_BOX,
        )

    fig.suptitle(
        f"{failed_key} vs Energy Decay — {name.upper()}\n"
        f"Pearson r = {corr:.3f} | Runs: {len(results)}",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Correlation Diagnostic")
    ax.set_xlabel(f"{failed_key} rate per alive mother")
    ax.set_ylabel("Energy drop per tick")

    style_axes(ax)
    ax.legend(loc="upper right", **_LEGEND_KW)

    plt.tight_layout()
    save_figure(fig, out_dir, filename)

    csv_path = os.path.join(out_dir, f"{metric_name}_{name}.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "metric",
                "value",
                "num_valid_samples",
                "x_std",
                "y_std",
                "linear_fit_used",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "metric": metric_name,
                "value": corr,
                "num_valid_samples": len(xs),
                "x_std": float(np.std(xs)) if len(xs) > 0 else 0.0,
                "y_std": float(np.std(ys)) if len(ys) > 0 else 0.0,
                "linear_fit_used": bool(can_fit),
            }
        )


def plot_failed_self_energy_correlation(name, results, duration, out_dir, window=25):
    _plot_failed_energy_correlation(
        name=name,
        results=results,
        duration=duration,
        out_dir=out_dir,
        failed_key="FAILED_SELF",
        filename=f"correlation_failed_self_energy_{name}.png",
        metric_name="pearson_failed_self_energy_drop",
        window=window,
    )


def plot_failed_forage_energy_correlation(name, results, duration, out_dir, window=25):
    _plot_failed_energy_correlation(
        name=name,
        results=results,
        duration=duration,
        out_dir=out_dir,
        failed_key="FAILED_FORAGE",
        filename=f"correlation_failed_forage_energy_{name}.png",
        metric_name="pearson_failed_forage_energy_drop",
        window=window,
    )


# ============================================================
# 3) State-space scatter
# ============================================================

def plot_state_space_energy_action(name, results, duration, out_dir, window=25):
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
        ax.legend(loc="upper right", **_LEGEND_KW)

    fig.suptitle(
        f"State Space: Energy vs Action/Motivation — {name.upper()}\n"
        f"MotherAgent | Tick samples across {len(results)} runs | window = {window}",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout()
    save_figure(fig, out_dir, f"state_space_energy_action_{name}.png")


# ============================================================
# 4) Food consumption rate over time
# ============================================================

def plot_food_consumption_over_time(name, results, duration, out_dir, window=25):
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
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", **_LEGEND_KW)

    plt.tight_layout()
    save_figure(fig, out_dir, f"food_consumption_rate_{name}.png")


# ============================================================
# 5) Spatial heatmap
# ============================================================

def plot_spatial_heatmap_population(name, results, out_dir):
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

def plot_energy_expenditure_breakdown(name, results, out_dir):
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
        bbox=_ANNOT_BOX,
    )

    plt.tight_layout()
    save_figure(fig, out_dir, f"energy_expenditure_breakdown_{name}.png")


# ============================================================
# 7) Homeostatic balance
# ============================================================

def plot_homeostatic_balance(name, results, duration, out_dir, window=25):
    ticks = np.arange(duration)

    energy_matrix = np.asarray(
        [
            smooth_series(
                np.nan_to_num(pad(r["energy_history"], duration), nan=0.0),
                window=window,
            )
            for r in results
        ],
        dtype=float,
    )

    fatigue_matrix = np.asarray(
        [
            smooth_series(
                np.nan_to_num(pad(r.get("fatigue_history", []), duration), nan=0.0),
                window=window,
            )
            for r in results
        ],
        dtype=float,
    )

    mean_energy = np.mean(energy_matrix, axis=0)
    std_energy = np.std(energy_matrix, axis=0)

    mean_fatigue = np.mean(fatigue_matrix, axis=0)
    std_fatigue = np.std(fatigue_matrix, axis=0)

    fig, ax_energy = plt.subplots(figsize=(13, 6))
    ax_fatigue = ax_energy.twinx()

    for i in range(len(results)):
        label = "Individual Runs" if i == 0 else "_nolegend_"

        ax_energy.plot(
            ticks,
            energy_matrix[i],
            color="gray",
            alpha=0.08,
            linewidth=0.7,
            label=label,
        )

        ax_fatigue.plot(
            ticks,
            fatigue_matrix[i],
            color="gray",
            alpha=0.05,
            linewidth=0.7,
        )

    ax_energy.fill_between(
        ticks,
        mean_energy - std_energy,
        mean_energy + std_energy,
        color="tab:blue",
        alpha=0.14,
        label="Energy Mean ± SD",
    )

    ax_energy.plot(
        ticks,
        mean_energy,
        color="tab:blue",
        linewidth=2.3,
        label="Mean Energy",
    )

    ax_fatigue.fill_between(
        ticks,
        mean_fatigue - std_fatigue,
        mean_fatigue + std_fatigue,
        color="tab:red",
        alpha=0.10,
        label="Fatigue Mean ± SD",
    )

    ax_fatigue.plot(
        ticks,
        mean_fatigue,
        color="tab:red",
        linestyle="--",
        linewidth=2.3,
        label="Mean Fatigue",
    )

    fig.suptitle(
        f"Homeostatic Balance: Energy vs Fatigue — {name.upper()}\n"
        f"MotherAgent | Runs: {len(results)} total | smoothing window = {window} ticks",
        fontsize=14,
        fontweight="bold",
    )

    ax_energy.set_title("Energy–Fatigue Homeostatic Dynamics")
    ax_energy.set_xlabel("Tick")
    ax_energy.set_ylabel("Mean Energy", color="tab:blue")
    ax_fatigue.set_ylabel("Mean Fatigue", color="tab:red")

    ax_energy.tick_params(axis="y", labelcolor="tab:blue")
    ax_fatigue.tick_params(axis="y", labelcolor="tab:red")

    ax_energy.set_ylim(-0.05, 1.05)
    ax_fatigue.set_ylim(-0.05, 1.05)

    ax_energy.axhline(
        0.70,
        color="tab:blue",
        linestyle=":",
        alpha=0.55,
        linewidth=1.1,
        label="Energy target 0.70",
    )

    ax_fatigue.axhline(
        0.0,
        color="tab:red",
        linestyle=":",
        alpha=0.35,
        linewidth=1.0,
        label="Fatigue baseline",
    )

    style_axes(ax_energy)
    style_axes(ax_fatigue)

    lines_energy, labels_energy = ax_energy.get_legend_handles_labels()
    lines_fatigue, labels_fatigue = ax_fatigue.get_legend_handles_labels()

    ax_energy.legend(
        lines_energy + lines_fatigue,
        labels_energy + labels_fatigue,
        loc="upper right",
        **_LEGEND_KW,
    )

    plt.tight_layout()
    save_figure(fig, out_dir, f"homeostatic_balance_{name}.png")
    
def plot_rate_sum_check(
    name,
    results,
    duration,
    out_dir,
):
    """
    Check whether event rates are normalized correctly.

    Denominator is reconstructed from motivation counts:
        processed_count = FORAGE + SELF

    Ticks where processed == 0 (run already ended) are set to NaN so they
    do not pull down the mean.  nanmean / nanstd are used across runs.
    Smoothing is disabled (window=1) to avoid edge artifacts.
    """
    ticks = np.arange(duration)

    action_keys = ["MOVE", "PICK", "EAT", "REST"]
    failed_keys = ["FAILED_FORAGE", "FAILED_SELF"]
    motivation_keys = ["FORAGE", "SELF"]

    action_sum_runs = []
    failed_sum_runs = []
    action_failed_sum_runs = []
    motivation_sum_runs = []

    for r in results:
        action_history = r.get("action_history", [])
        failed_history = r.get("failed_history", [])
        motivation_history = r.get("motivation_history", [])

        action_arrays, _ = pad_event_history(action_history, duration, action_keys)
        failed_arrays, _ = pad_event_history(failed_history, duration, failed_keys)
        motivation_arrays, _ = pad_event_history(motivation_history, duration, motivation_keys)

        action_count = np.zeros(duration, dtype=float)
        failed_count = np.zeros(duration, dtype=float)
        motivation_count = np.zeros(duration, dtype=float)

        for key in action_keys:
            action_count += action_arrays[key]

        for key in failed_keys:
            failed_count += failed_arrays[key]

        for key in motivation_keys:
            motivation_count += motivation_arrays[key]

        # Use motivation count as the true processed denominator.
        # Every processed mother generates exactly one motivation.
        # Ticks where processed == 0 become NaN (run ended) so they
        # are excluded from nanmean/nanstd instead of pulling rates to 0.
        processed = motivation_count.copy()
        active = processed > 0

        def _nan_rate(numerator):
            out = np.full(duration, np.nan)
            out[active] = numerator[active] / processed[active]
            return out

        action_sum_runs.append(_nan_rate(action_count))
        failed_sum_runs.append(_nan_rate(failed_count))
        action_failed_sum_runs.append(_nan_rate(action_count + failed_count))
        motivation_sum_runs.append(_nan_rate(motivation_count))

    action_sum_runs = np.asarray(action_sum_runs, dtype=float)
    failed_sum_runs = np.asarray(failed_sum_runs, dtype=float)
    action_failed_sum_runs = np.asarray(action_failed_sum_runs, dtype=float)
    motivation_sum_runs = np.asarray(motivation_sum_runs, dtype=float)

    fig, ax = plt.subplots(figsize=(13, 6))

    curves = [
        ("Action only", action_sum_runs, "tab:blue", "-"),
        ("Failed only", failed_sum_runs, "tab:red", "--"),
        ("Action + Failed", action_failed_sum_runs, "tab:green", "-"),
        ("Motivation", motivation_sum_runs, "tab:orange", ":"),
    ]

    for label, matrix, color, linestyle in curves:
        mean_y = np.nanmean(matrix, axis=0)
        std_y = np.nanstd(matrix, axis=0)

        ax.fill_between(
            ticks,
            mean_y - std_y,
            mean_y + std_y,
            color=color,
            alpha=0.10,
            label=f"{label} Mean ± SD",
        )

        ax.plot(
            ticks,
            mean_y,
            color=color,
            linestyle=linestyle,
            linewidth=2.2,
            label=f"{label} Group Mean",
        )

    ax.axhline(
        1.0,
        color="black",
        linestyle="--",
        linewidth=1.2,
        alpha=0.75,
        label="Expected normalized total = 1.0",
    )

    fig.suptitle(
        f"Rate Sum Check — {name.upper()}\n"
        f"MotherAgent | Runs: {len(results)} total | no smoothing (NaN-padded ends)",
        fontsize=14,
        fontweight="bold",
    )

    ax.set_title("Check event-rate completeness using processed mothers as denominator")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Rate sum per processed mother")
    ax.set_ylim(-0.05, 1.25)

    style_axes(ax)
    ax.legend(loc="upper right", ncol=2, **_LEGEND_KW)

    plt.tight_layout()
    save_figure(fig, out_dir, f"rate_sum_check_{name}.png")