"""
experiments/live_viewer.py

Phase-agnostic live visualizer for simulation runs.

Two modes
---------
Mode A  live    : drives sim.step() tick by tick and reads from a Phase*LiveProvider.
Mode B  replay  : animates a saved result dict via ReplayProvider.

Phase compatibility
-------------------
Any phase run.py can import LiveViewer and its matching provider:

    from experiments.live_viewer import LiveViewer, Phase2LiveProvider

    sim.initialize()
    viewer   = LiveViewer(speed=args.speed, title="Phase 2")
    provider = Phase2LiveProvider(sim, total_ticks=args.duration)
    viewer.run_live(sim, provider)
    result   = sim.collect_result()

For Phase 3+, subclass LiveStateProvider and override get() to include
extra keys (child_history, care_history, …). LiveViewer never imports
phase-specific code.

Replay usage
------------
    provider = ReplayProvider(saved_result_dict)
    viewer   = LiveViewer(speed=2, title="Phase 2 Replay")
    viewer.run_replay(provider)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


# ── helpers ───────────────────────────────────────────────────────────────────

def _style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.grid(True, linestyle="--", linewidth=0.45, alpha=0.30)
    ax.set_facecolor("#fafafa")
    ax.tick_params(labelsize=8)


# ── providers ─────────────────────────────────────────────────────────────────

class LiveStateProvider:
    """
    Abstract base — one subclass per phase.

    get() must return a dict with at minimum:
        energy_history     : list[float]
        population_history : list[int]
        action_history     : list[dict]   keys: MOVE PICK EAT REST alive
        motivation_history : list[dict]   keys: FORAGE SELF alive
        tick               : int          current tick index
        total_ticks        : int          max ticks for this run
    """

    total_ticks: int

    def get(self) -> dict:
        raise NotImplementedError


class Phase2LiveProvider(LiveStateProvider):
    """
    Reads directly from a live SurvivalSimulation (Phase 2).

    Phase 3 run.py can subclass this and extend get() to add
    child_history, care_history, etc. without touching LiveViewer.
    """

    def __init__(self, sim, total_ticks: int):
        self.sim         = sim
        self.total_ticks = total_ticks

    def get(self) -> dict:
        return {
            "energy_history":     list(self.sim.energy_history),
            "population_history": list(self.sim.population_history),
            "action_history":     list(self.sim.action_history),
            "motivation_history": list(self.sim.motivation_history),
            "tick":               self.sim.tick,
            "total_ticks":        self.total_ticks,
        }


class ReplayProvider(LiveStateProvider):
    """
    Animates a saved result dict (e.g. from sim.collect_result()).
    Call advance(n) to move the frame pointer forward, then get().
    """

    def __init__(self, result: dict, total_ticks: int | None = None):
        self.result      = result
        self.total_ticks = total_ticks or len(result["energy_history"])
        self.frame_idx   = 0

    def advance(self, n: int):
        self.frame_idx = min(self.frame_idx + n, self.total_ticks - 1)

    def get(self) -> dict:
        idx = self.frame_idx + 1
        return {
            "energy_history":     self.result["energy_history"][:idx],
            "population_history": self.result["population_history"][:idx],
            "action_history":     self.result.get("action_history",     [])[:idx],
            "motivation_history": self.result.get("motivation_history", [])[:idx],
            "tick":               self.frame_idx,
            "total_ticks":        self.total_ticks,
        }


# ── viewer ────────────────────────────────────────────────────────────────────

class LiveViewer:
    """
    Interactive matplotlib window.

    Parameters
    ----------
    speed : {1, 2, 5}
        Ticks (or replay frames) advanced per display refresh.
    title : str
        Figure title prefix shown in the window.
    """

    _SPEED_MAP = {1: 1, 2: 2, 5: 5}
    _PAUSE     = 0.03   # seconds between redraws  (~30 fps target)

    def __init__(self, speed: int = 1, title: str = "Phase 2"):
        self.tpf   = self._SPEED_MAP.get(speed, 1)
        self.title = title
        self._setup()

    # ── figure ────────────────────────────────────────────────────────────────

    def _setup(self):
        for backend in ("TkAgg", "Qt5Agg", "QtAgg", "WebAgg"):
            try:
                plt.switch_backend(backend)
                break
            except Exception:
                continue
        else:
            print(
                "WARNING: Could not switch to an interactive matplotlib backend. "
                "The live window may not display correctly."
            )

        plt.ion()
        self.fig = plt.figure(figsize=(13, 7), constrained_layout=True)
        self.fig.patch.set_facecolor("white")

        gs = gridspec.GridSpec(2, 2, figure=self.fig)
        self.ax_energy = self.fig.add_subplot(gs[0, 0])
        self.ax_pop    = self.fig.add_subplot(gs[0, 1])
        self.ax_action = self.fig.add_subplot(gs[1, 0])
        self.ax_mot    = self.fig.add_subplot(gs[1, 1])

        for ax in (self.ax_energy, self.ax_pop, self.ax_action, self.ax_mot):
            _style_ax(ax)

        # Static line objects (updated in _update)
        (self.line_energy,) = self.ax_energy.plot([], [], color="tab:blue", linewidth=1.8)
        self.ax_energy.axhline(0.70, color="gray", linestyle=":", linewidth=1.0, alpha=0.55)
        self.ax_energy.set_title("Mean Energy",   fontsize=10)
        self.ax_energy.set_xlabel("Tick",         fontsize=9)
        self.ax_energy.set_ylabel("Energy",       fontsize=9)
        self.ax_energy.set_ylim(-0.05, 1.05)

        (self.line_pop,) = self.ax_pop.step([], [], where="post", color="tab:green", linewidth=1.8)
        self.ax_pop.set_title("Population",   fontsize=10)
        self.ax_pop.set_xlabel("Tick",        fontsize=9)
        self.ax_pop.set_ylabel("Alive",       fontsize=9)
        self.ax_pop.set_ylim(-0.5, 16.5)

        self.ax_action.set_title("Actions (last tick)",     fontsize=10)
        self.ax_mot.set_title("Motivations (last tick)",    fontsize=10)

        plt.show(block=False)

    # ── drawing ───────────────────────────────────────────────────────────────

    def _update(self, state: dict):
        eh    = np.asarray(state["energy_history"],     dtype=float)
        ph    = np.asarray(state["population_history"], dtype=float)
        tick  = int(state["tick"])
        total = int(state["total_ticks"])
        ticks = np.arange(len(eh))
        xlim  = max(total, len(eh))

        self.line_energy.set_data(ticks, eh)
        self.ax_energy.set_xlim(0, xlim)

        self.line_pop.set_data(ticks, ph)
        self.ax_pop.set_xlim(0, xlim)

        # Action bar chart — redrawn each frame (cheap on small N)
        ah = state.get("action_history", [])
        if ah:
            last   = ah[-1]
            alive  = max(last.get("alive", 1), 1)
            keys   = ["MOVE", "PICK", "EAT", "REST"]
            rates  = [last.get(k, 0) / alive for k in keys]
            colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]
            self.ax_action.cla()
            _style_ax(self.ax_action)
            self.ax_action.set_title("Actions (last tick)", fontsize=10)
            self.ax_action.bar(keys, rates, color=colors, alpha=0.82, width=0.6)
            self.ax_action.set_ylim(0, 1.05)

        # Motivation bar chart
        mh = state.get("motivation_history", [])
        if mh:
            last   = mh[-1]
            alive  = max(last.get("alive", 1), 1)
            keys   = ["FORAGE", "SELF"]
            rates  = [last.get(k, 0) / alive for k in keys]
            colors = ["tab:orange", "tab:blue"]
            self.ax_mot.cla()
            _style_ax(self.ax_mot)
            self.ax_mot.set_title("Motivations (last tick)", fontsize=10)
            self.ax_mot.bar(keys, rates, color=colors, alpha=0.82, width=0.4)
            self.ax_mot.set_ylim(0, 1.05)

        pct = 100.0 * tick / max(total, 1)
        self.fig.suptitle(
            f"{self.title} — Live Viewer  |  "
            f"Tick {tick}/{total} ({pct:.0f}%)  |  ×{self.tpf} speed",
            fontsize=12,
            fontweight="bold",
        )

        self.fig.canvas.draw_idle()
        plt.pause(self._PAUSE)

    # ── public entry points ───────────────────────────────────────────────────

    def run_live(self, sim, provider: LiveStateProvider):
        """
        Mode A — drives sim.step() and reads from provider.

        sim must already be initialized (sim.initialize() called before this).
        After this returns, call sim.collect_result() to get the result dict.
        If the user closes the window mid-run the simulation finishes headlessly.
        """
        total = provider.total_ticks
        t     = 0
        alive = True

        while t < total and alive:
            if not plt.fignum_exists(self.fig.number):
                # Window closed: finish the remaining ticks without display.
                while t < total:
                    sim.tick = t
                    sim.step()
                    t += 1
                    if not any(m.alive for m in sim.mothers):
                        break
                break

            for _ in range(self.tpf):
                if t >= total or not alive:
                    break
                sim.tick = t
                sim.step()
                t += 1
                if not any(m.alive for m in sim.mothers):
                    alive = False
                    break

            self._update(provider.get())

        self._close()

    def run_replay(self, provider: ReplayProvider):
        """
        Mode B — animates a pre-loaded result dict.
        """
        while provider.frame_idx < provider.total_ticks - 1:
            if not plt.fignum_exists(self.fig.number):
                return
            provider.advance(self.tpf)
            self._update(provider.get())

        self._close()

    # ── internal ──────────────────────────────────────────────────────────────

    def _close(self):
        plt.ioff()
        if plt.fignum_exists(self.fig.number):
            plt.close(self.fig)
