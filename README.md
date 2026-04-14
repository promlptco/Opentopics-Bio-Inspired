# OpenTopics: Bio-Inspired Maternal Care Simulation

A simulation of the minimum ecological conditions for the emergence of kin-biased maternal care using evolving neuroendocrine agents.

## 🚀 Quick Start

### Installation
1. Ensure you have Python 3.10+ installed.
2. Install dependencies:
   ```powershell
   pip install numpy matplotlib scipy pygame
   ```

### Running Simulations

#### Mode 1: Main Simulation (Visual)
Runs the interactive real-time visualization:
```powershell
python main.py
```

#### Mode 2: Phase 2 Stochastic Stress Test
Runs the auto-calibration sweep or single validation with high statistical repeats (no visualization):
```powershell
# Auto-calibration (Grid sweep of 243 configs)
python experiments/phase2_survival_minimal/run.py --mode sweep

# Single validation (5 seeds x 3 repeats) - Highly Optimized
python experiments/phase2_survival_minimal/run.py --mode single
```

## 🏗️ Project Structure
- `agents/`: Core agent classes (`mother.py`, `infant.py`).
- `simulation/`: World dynamics (`world.py`) and main loop (`simulation.py`).
- `evolution/`: Genetic operators and population management.
- `experiments/`: Targeted validation phases and calibration scripts.
- `outputs/`: Automatically generated plots and JSON data (organized by date/time).

## 📄 Documentation
For detailed information on the research question, experimental methodology, and success criteria, see:
- [EXPERIMENT_DESIGN.md](./EXPERIMENT_DESIGN.md)
- [DESIGN_BASELINE.md](./DESIGN_BASELINE.md)
