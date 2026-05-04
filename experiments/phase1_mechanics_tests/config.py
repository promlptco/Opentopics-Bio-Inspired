from itertools import product
import numpy as np

initial_energy = 1.0
hunger_rate = 1.0 / 35.0 
infant_starvation_multiplier = 35.0 / 15.0

INIT_ENERGIES = [0.75, 0.80, 0.85, 0.90, 0.95, 1.0]