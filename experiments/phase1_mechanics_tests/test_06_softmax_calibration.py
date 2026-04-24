"""
Test 06: Softmax Calibration

Verifies that Softmax / Gibbs action selection is correctly implemented:
- softmax_probs() matches the Boltzmann equation
- sampled frequencies match theoretical probabilities
- lower tau sharpens the distribution
- higher tau flattens the distribution
- boundary cases are handled safely
- calibration plot is saved
"""
import sys
import os
import math
import csv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents.mother import softmax_probs, SOFTMAX_TAU

MODULE_NUM = "06"
DEFAULT_SEED = 42
RUN_NUM = 1
TAG = f"test{MODULE_NUM}_{DEFAULT_SEED}_{RUN_NUM}"

_results = []


def _seed(seed: int = DEFAULT_SEED) -> None:
    np.random.seed(seed)


def _log(name: str, detail: str = "") -> None:
    _results.append({"test_name": name, "status": "PASS", "detail": detail})
    print(f"✓ {name} PASSED")


def _assert_valid_probs(probs: dict[str, float], tol: float = 1e-9) -> None:
    """Check probabilities are numerically valid."""
    total = sum(probs.values())

    assert abs(total - 1.0) < tol, f"Probabilities do not sum to 1: {total}"

    for action, p in probs.items():
        assert not math.isnan(p), f"NaN probability for {action}"
        assert not math.isinf(p), f"Inf probability for {action}"
        assert p >= 0.0, f"Negative probability for {action}: {p}"
        assert p <= 1.0, f"Probability above 1 for {action}: {p}"


def _manual_softmax(scores: dict[str, float], tau: float) -> dict[str, float]:
    """Stable manual softmax used as gold-standard reference."""
    max_score = max(scores.values())
    raw = {
        k: math.exp((v - max_score) / tau)
        for k, v in scores.items()
    }
    total = sum(raw.values())
    return {k: raw[k] / total for k in raw}


# ---------------------------------------------------------------------------
# A: Mathematical correctness
# ---------------------------------------------------------------------------

def test_softmax_math_correct():
    """softmax_probs() should match the Boltzmann equation."""
    scores = {"care": 0.7, "forage": 0.4, "self": 0.2}
    tau = SOFTMAX_TAU

    expected = _manual_softmax(scores, tau=tau)
    got = softmax_probs(scores, tau=tau)

    _assert_valid_probs(got)

    for action in scores:
        diff = abs(got[action] - expected[action])
        print(
            f"{action}: expected={expected[action]:.8f}, "
            f"got={got[action]:.8f}, diff={diff:.2e}"
        )
        assert diff < 1e-8, \
            f"{action}: softmax output differs from expected by {diff:.2e}"

    _log(
        "test_softmax_math_correct",
        f"tau={tau};care={got['care']:.6f};"
        f"forage={got['forage']:.6f};self={got['self']:.6f}",
    )


def test_probability_validity():
    """Softmax output should always be valid probabilities."""
    cases = [
        {"care": 0.7, "forage": 0.4, "self": 0.2},
        {"care": 0.0, "forage": 0.0, "self": 0.0},
        {"care": 10.0, "forage": 1.0, "self": -2.0},
        {"care": -1.0, "forage": -2.0, "self": -3.0},
    ]

    for scores in cases:
        probs = softmax_probs(scores, tau=SOFTMAX_TAU)
        _assert_valid_probs(probs)

    _log("test_probability_validity", f"checked_cases={len(cases)}")


# ---------------------------------------------------------------------------
# B: Empirical sampling calibration
# ---------------------------------------------------------------------------

def test_empirical_selection_rate():
    """Sampling should match theoretical softmax probabilities."""
    _seed()

    scores = {"high": 0.9, "low": 0.1}
    tau = SOFTMAX_TAU
    probs = softmax_probs(scores, tau=tau)

    _assert_valid_probs(probs)

    n_samples = 5000
    keys = list(probs.keys())
    weights = [probs[k] for k in keys]

    sampled = np.random.choice(keys, size=n_samples, p=weights)
    p_high_empirical = np.mean(sampled == "high")
    p_high_theory = probs["high"]

    delta = abs(p_high_empirical - p_high_theory)

    print(f"Theoretical P(high): {p_high_theory:.6f}")
    print(f"Empirical  P(high): {p_high_empirical:.6f}")
    print(f"Delta: {delta:.6f}")

    assert p_high_empirical >= 0.99, \
        f"Expected high action to dominate, got {p_high_empirical:.4f}"

    assert delta < 0.01, \
        f"Empirical rate differs from theory too much: delta={delta:.4f}"

    _log(
        "test_empirical_selection_rate",
        f"tau={tau};n_samples={n_samples};"
        f"p_high_theory={p_high_theory:.6f};"
        f"p_high_empirical={p_high_empirical:.6f};delta={delta:.6f}",
    )


def test_moderate_contrast_proportional():
    """Moderate contrast should prefer higher utility without collapsing fully."""
    scores = {"A": 0.6, "B": 0.4}
    tau = 0.5

    probs = softmax_probs(scores, tau=tau)
    expected = _manual_softmax(scores, tau=tau)

    _assert_valid_probs(probs)

    assert probs["A"] > probs["B"], \
        f"Higher utility should have higher probability: {probs}"

    assert probs["B"] > 0.01, \
        f"Lower utility action should still have non-trivial probability: {probs['B']}"

    assert abs(probs["A"] - expected["A"]) < 1e-10, \
        f"P(A) mismatch: expected={expected['A']}, got={probs['A']}"

    _log(
        "test_moderate_contrast_proportional",
        f"tau={tau};p_A={probs['A']:.6f};p_B={probs['B']:.6f}",
    )


# ---------------------------------------------------------------------------
# C: Temperature sensitivity
# ---------------------------------------------------------------------------

def test_temperature_sensitivity():
    """Entropy should increase as tau increases."""
    scores = {"care": 0.8, "forage": 0.5, "self": 0.2}
    taus = [0.05, 0.1, 0.5, 1.0]

    entropies = {}

    for tau in taus:
        probs = softmax_probs(scores, tau=tau)
        _assert_valid_probs(probs)

        entropy = -sum(p * math.log(p) for p in probs.values() if p > 0.0)
        entropies[tau] = entropy

        top_action = max(probs, key=probs.get)
        print(
            f"tau={tau:.2f}: entropy={entropy:.4f}, "
            f"top={top_action}, p_top={probs[top_action]:.4f}"
        )

    sorted_taus = sorted(taus)

    for i in range(len(sorted_taus) - 1):
        t_low = sorted_taus[i]
        t_high = sorted_taus[i + 1]

        assert entropies[t_low] < entropies[t_high], (
            f"Entropy should increase with tau: "
            f"tau={t_low}, H={entropies[t_low]:.4f}; "
            f"tau={t_high}, H={entropies[t_high]:.4f}"
        )

    probs_canonical = softmax_probs(scores, tau=SOFTMAX_TAU)

    assert probs_canonical["care"] > 0.95, \
        f"At tau={SOFTMAX_TAU}, top action should dominate, got {probs_canonical['care']:.4f}"

    detail = ";".join(f"tau={t}:H={entropies[t]:.4f}" for t in sorted_taus)
    _log("test_temperature_sensitivity", detail)


# ---------------------------------------------------------------------------
# D: Boundary robustness
# ---------------------------------------------------------------------------

def test_boundary_equal_scores():
    """Equal scores should produce uniform probabilities."""
    scores = {"care": 0.5, "forage": 0.5, "self": 0.5}
    probs = softmax_probs(scores)

    _assert_valid_probs(probs)

    expected = 1.0 / len(scores)

    for action, p in probs.items():
        assert abs(p - expected) < 1e-10, \
            f"Equal scores should be uniform. {action}: {p} != {expected}"

    _log("test_boundary_equal_scores", f"p_each={expected:.6f}")


def test_boundary_zero_scores():
    """Zero scores should also produce uniform probabilities."""
    scores = {"care": 0.0, "forage": 0.0, "self": 0.0}
    probs = softmax_probs(scores)

    _assert_valid_probs(probs)

    expected = 1.0 / len(scores)

    for action, p in probs.items():
        assert abs(p - expected) < 1e-10, \
            f"Zero scores should be uniform. {action}: {p} != {expected}"

    _log("test_boundary_zero_scores", f"p_each={expected:.6f}")


def test_boundary_single_action():
    """A single action should receive probability 1.0."""
    scores = {"care": 0.7}
    probs = softmax_probs(scores)

    _assert_valid_probs(probs)

    assert abs(probs["care"] - 1.0) < 1e-10, \
        f"Single action should have probability 1.0, got {probs['care']}"

    _log("test_boundary_single_action", f"p_care={probs['care']:.8f}")


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

ACTIONS = ["care", "forage", "self"]

SCENARIOS = [
    {
        "label": "High Contrast",
        "scores": {"care": 0.9, "forage": 0.5, "self": 0.1},
    },
    {
        "label": "Moderate",
        "scores": {"care": 0.7, "forage": 0.4, "self": 0.2},
    },
    {
        "label": "Near Equal",
        "scores": {"care": 0.5, "forage": 0.45, "self": 0.4},
    },
]

TEMP_SCENARIO = {"care": 0.7, "forage": 0.4, "self": 0.2}
TEMP_TAUS = [0.05, 0.1, 0.2, 0.5, 1.0]


def _sample_frequencies(
    scores: dict[str, float],
    tau: float,
    n_samples: int,
    seed: int,
) -> dict[str, float]:
    """Sample actions and return empirical frequencies."""
    np.random.seed(seed)

    probs = softmax_probs(scores, tau=tau)
    keys = list(probs.keys())
    weights = [probs[k] for k in keys]

    chosen = np.random.choice(keys, size=n_samples, p=weights)

    return {
        action: float(np.mean(chosen == action))
        for action in keys
    }


def plot_softmax_calibration(
    out_dir: str,
    n_samples: int = 5000,
    seed: int = DEFAULT_SEED,
) -> str:
    """Save polished softmax calibration plot."""
    tau = SOFTMAX_TAU

    ACTION_COLORS = {
        "care": "#2166AC",
        "forage": "#1A9850",
        "self": "#D6604D",
    }

    plt.style.use("default")

    fig = plt.figure(figsize=(15, 9), facecolor="#FFFFFF")
    fig.patch.set_facecolor("#FFFFFF")

    gs = fig.add_gridspec(
        2,
        3,
        height_ratios=[1.0, 0.9],
        hspace=0.42,
        wspace=0.32,
    )

    axes_top = [fig.add_subplot(gs[0, i]) for i in range(3)]
    ax_bottom = fig.add_subplot(gs[1, :])

    fig.suptitle(
        f"Softmax Calibration — Phase 1 Test 06  |  "
        f"τ={tau}, samples={n_samples:,}, seed={seed}",
        fontsize=14,
        fontweight="bold",
        color="#1A1A1A",
        y=1.02,
    )

    def _style_ax(ax, title: str) -> None:
        ax.set_facecolor("#FAFAFA")
        ax.set_title(
            title,
            fontsize=10,
            fontweight="bold",
            color="#1A1A1A",
            pad=8,
        )
        ax.tick_params(colors="#333333", labelsize=8.5)

        for spine in ax.spines.values():
            spine.set_edgecolor("#CCCCCC")
            spine.set_linewidth(0.85)

        ax.grid(
            axis="y",
            color="#E0E0E0",
            linewidth=0.7,
            linestyle="--",
            alpha=0.9,
        )
        ax.set_axisbelow(True)

    # ------------------------------------------------------------
    # Top row: observed vs theoretical for three scenarios
    # ------------------------------------------------------------
    x = np.arange(len(ACTIONS))
    bar_w = 0.32
    gap = 0.04

    for idx, scenario in enumerate(SCENARIOS):
        ax = axes_top[idx]
        scores = scenario["scores"]

        theory = softmax_probs(scores, tau=tau)
        observed = _sample_frequencies(
            scores=scores,
            tau=tau,
            n_samples=n_samples,
            seed=seed + idx,
        )

        for i, action in enumerate(ACTIONS):
            color = ACTION_COLORS[action]

            obs_pct = observed[action] * 100.0
            theory_pct = theory[action] * 100.0

            ax.bar(
                x[i] - bar_w / 2 - gap / 2,
                obs_pct,
                bar_w,
                color=color,
                alpha=0.75,
                edgecolor="#FFFFFF",
                linewidth=0.7,
                label="Observed" if i == 0 else "",
            )

            ax.bar(
                x[i] + bar_w / 2 + gap / 2,
                theory_pct,
                bar_w,
                color=color,
                alpha=0.28,
                edgecolor=color,
                linewidth=1.2,
                hatch="//",
                label="Theoretical" if i == 0 else "",
            )

            ax.text(
                x[i] - bar_w / 2 - gap / 2,
                obs_pct + 1.0,
                f"{obs_pct:.1f}%",
                ha="center",
                va="bottom",
                fontsize=7.2,
                color="#333333",
            )

            ax.text(
                x[i] + bar_w / 2 + gap / 2,
                theory_pct + 1.0,
                f"{theory_pct:.1f}%",
                ha="center",
                va="bottom",
                fontsize=7.2,
                color="#666666",
            )

        score_text = ", ".join(f"{k}={v}" for k, v in scores.items())

        _style_ax(ax, scenario["label"])
        ax.set_xticks(x)
        ax.set_xticklabels([a.capitalize() for a in ACTIONS])
        ax.set_ylim(0, 110)
        ax.set_xlabel("Action", fontsize=8.5, color="#444444")
        ax.set_ylabel("Frequency (%)", fontsize=8.5, color="#444444")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))

        ax.text(
            0.03,
            0.95,
            score_text,
            transform=ax.transAxes,
            fontsize=7.3,
            verticalalignment="top",
            horizontalalignment="left",
            color="#1A1A1A",
            bbox=dict(
                boxstyle="round,pad=0.35",
                facecolor="#FFFFFF",
                edgecolor="#CCCCCC",
                alpha=0.95,
            ),
        )

        if idx == 0:
            ax.legend(
                fontsize=7.5,
                loc="upper right",
                facecolor="#FFFFFF",
                edgecolor="#CCCCCC",
                labelcolor="#333333",
                framealpha=0.95,
            )

    # ------------------------------------------------------------
    # Bottom row: temperature sensitivity
    # ------------------------------------------------------------
    tau_x = np.arange(len(TEMP_TAUS))
    bar_w_t = 0.20

    for j, action in enumerate(ACTIONS):
        color = ACTION_COLORS[action]

        vals = [
            softmax_probs(TEMP_SCENARIO, tau=t)[action] * 100.0
            for t in TEMP_TAUS
        ]

        offset = (j - 1) * (bar_w_t + 0.035)

        ax_bottom.bar(
            tau_x + offset,
            vals,
            bar_w_t,
            color=color,
            alpha=0.78,
            edgecolor="#FFFFFF",
            linewidth=0.6,
            label=action.capitalize(),
        )

        for xi, val in zip(tau_x + offset, vals):
            ax_bottom.text(
                xi,
                val + 0.8,
                f"{val:.1f}%",
                ha="center",
                va="bottom",
                fontsize=7,
                color="#333333",
            )

    # Highlight canonical tau
    if tau in TEMP_TAUS:
        canonical_idx = TEMP_TAUS.index(tau)
        ax_bottom.axvspan(
            tau_x[canonical_idx] - 0.45,
            tau_x[canonical_idx] + 0.45,
            color="#2166AC",
            alpha=0.07,
            zorder=0,
        )

        ax_bottom.text(
            tau_x[canonical_idx],
            -8,
            "canonical\nτ",
            ha="center",
            va="top",
            fontsize=8,
            color="#2166AC",
            fontweight="bold",
        )

    temp_score_text = ", ".join(f"{k}={v}" for k, v in TEMP_SCENARIO.items())

    _style_ax(
        ax_bottom,
        f"Temperature Sensitivity — Theoretical Softmax ({temp_score_text})",
    )

    ax_bottom.set_xticks(tau_x)
    ax_bottom.set_xticklabels([f"τ = {t}" for t in TEMP_TAUS])
    ax_bottom.set_ylim(0, 115)
    ax_bottom.set_xlabel("Softmax temperature", fontsize=8.5, color="#444444")
    ax_bottom.set_ylabel("Theoretical probability (%)", fontsize=8.5, color="#444444")
    ax_bottom.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))

    ax_bottom.legend(
        fontsize=8.5,
        loc="upper right",
        facecolor="#FFFFFF",
        edgecolor="#CCCCCC",
        labelcolor="#333333",
        framealpha=0.95,
    )

    plt.tight_layout()

    save_path = os.path.join(out_dir, "softmax_calibration.png")
    fig.savefig(
        save_path,
        dpi=150,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)

    return save_path


if __name__ == "__main__":
    test_softmax_math_correct()
    test_probability_validity()

    test_empirical_selection_rate()
    test_moderate_contrast_proportional()

    test_temperature_sensitivity()

    test_boundary_equal_scores()
    test_boundary_zero_scores()
    test_boundary_single_action()

    out_dir = os.path.join(PROJECT_ROOT, "outputs", "phase1_mechanics_tests", TAG)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "logs.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_name", "status", "detail"])
        writer.writeheader()
        writer.writerows(_results)

    plot_path = plot_softmax_calibration(out_dir)

    print(f"Plot saved → {plot_path}")
    print(f"\n=== All Softmax calibration tests PASSED ===")
    print(f"Logs saved → outputs/phase1_mechanics_tests/{TAG}/logs.csv")