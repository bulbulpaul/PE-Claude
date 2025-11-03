"""
PFC Converter PANN Model Variables and Parameters

Defines global variables and circuit parameters for PFC PANN models
"""

import numpy as np

# Simulation parameters
Tslen = 500  # Time steps per switching period
fs = 50e3  # Switching frequency (50 kHz typical for PFC)
Ts = 1/fs
dt = Ts/Tslen  # Time step for Euler integration
Tsim = Ts * 20  # Simulate 20 switching periods

# Sequence length for ONNX deployment
seqlen_onnx = 1

# Line frequency parameters
f_line = 50  # Line frequency (Hz) - 50Hz for EU, 60Hz for US
omega_line = 2 * np.pi * f_line
T_line = 1 / f_line  # Line period

# Input voltage parameters
Vin_rms = 220  # RMS input voltage (V)
Vin_peak = Vin_rms * np.sqrt(2)  # Peak input voltage

# Circuit parameters for PFC converter
# These are initial values that can be learned by the PANN
L = 1e-3  # Inductance (1 mH)
C = 470e-6  # Output capacitance (470 uF)
R = 100  # Load resistance (100 Ohm)

# Output voltage target
Vout_target = 400  # Target output voltage (V)

# Control mode
# 'CCM' - Continuous Conduction Mode
# 'DCM' - Discontinuous Conduction Mode  
# 'BCM' - Boundary Conduction Mode (Critical Conduction Mode)
control_mode = 'CCM'

# Performance targets
power_factor_target = 0.99  # Target power factor (>0.99)
thd_target = 5.0  # Target THD (< 5%)
efficiency_target = 0.95  # Target efficiency (> 95%)

# Physical constraints for parameter learning
L_min, L_max = 100e-6, 10e-3  # Inductance range (100uH to 10mH)
C_min, C_max = 100e-6, 2000e-6  # Capacitance range (100uF to 2000uF)
R_min, R_max = 10, 500  # Load resistance range (10 to 500 Ohm)

# Training parameters
train_epochs = 50
batch_size = 10
learning_rate_params = 1e-5  # Learning rate for circuit parameters
learning_rate_nn = 1e-3  # Learning rate for neural network weights

# Data split ratios
train_ratio = 0.1
test_ratio = 0.45
val_ratio = 0.45  # Remaining data for validation

# Evaluation thresholds (from requirements)
power_factor_accuracy = 0.01  # ±0.01 accuracy requirement
thd_accuracy = 1.0  # ±1% accuracy requirement
efficiency_accuracy = 2.0  # ±2% accuracy requirement
waveform_correlation_threshold = 0.95  # Minimum correlation coefficient
