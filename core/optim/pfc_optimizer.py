"""
PFC Converter Multi-Objective Optimization

Implements optimization algorithms for Power Factor Correction converters
focusing on power factor, THD (Total Harmonic Distortion), and efficiency.

@reference: Based on PE-GPT optimization framework
@code-author: PE-GPT Multi-Topology Extension
"""

import numpy as np
import pyswarms as ps
import streamlit as st
import torch
from typing import Dict, Tuple, List, Optional

from ..model_zoo.pann_pfc_vars import (
    Vin_rms, Vin_peak, Vout_target, f_line, omega_line,
    power_factor_target, thd_target, efficiency_target
)


class PFCObjectiveFunction:
    """
    Multi-objective function for PFC optimization
    Optimizes power factor, THD, and efficiency simultaneously
    """
    
    def __init__(self, pfc_model, target_power, target_vout=400):
        """
        Initialize PFC objective function
        
        Args:
            pfc_model: PFC PANN model instance
            target_power: Target output power (W)
            target_vout: Target output voltage (V)
        """
        self.pfc_model = pfc_model
        self.target_power = target_power
        self.target_vout = target_vout
        self.vin_rms = Vin_rms
        self.vin_peak = Vin_peak
        
    def calculate_power_factor(self, vin_waveform, iin_waveform):
        """
        Calculate power factor from voltage and current waveforms
        
        Args:
            vin_waveform: Input voltage waveform
            iin_waveform: Input current waveform
        
        Returns:
            power_factor: Calculated power factor
        """
        # Real power (average of instantaneous power)
        p_real = np.mean(vin_waveform * iin_waveform)
        
        # RMS values
        v_rms = np.sqrt(np.mean(vin_waveform ** 2))
        i_rms = np.sqrt(np.mean(iin_waveform ** 2))
        
        # Apparent power
        s_apparent = v_rms * i_rms
        
        # Power factor
        if s_apparent > 1e-6:
            pf = p_real / s_apparent
        else:
            pf = 0.0
        
        return np.clip(pf, 0, 1)
    
    def calculate_thd(self, current_waveform, fundamental_freq=50):
        """
        Calculate Total Harmonic Distortion
        
        Args:
            current_waveform: Input current waveform
            fundamental_freq: Fundamental frequency (Hz)
        
        Returns:
            thd: THD percentage
        """
        # Perform FFT
        fft_result = np.fft.fft(current_waveform)
        fft_magnitude = np.abs(fft_result)
        
        # Get fundamental component (first harmonic)
        fundamental = fft_magnitude[1]
        
        # Calculate harmonics (2nd to 40th typically considered)
        n_harmonics = min(40, len(fft_magnitude) // 2)
        harmonics = fft_magnitude[2:n_harmonics+1]
        
        # THD calculation
        if fundamental > 1e-6:
            thd = 100 * np.sqrt(np.sum(harmonics ** 2)) / fundamental
        else:
            thd = 100.0
        
        # Clip to reasonable range
        return np.clip(thd, 0, 100)
    
    def calculate_efficiency(self, p_in, p_out):
        """
        Calculate converter efficiency
        
        Args:
            p_in: Input power (W)
            p_out: Output power (W)
        
        Returns:
            efficiency: Efficiency (0-1)
        """
        if abs(p_in) > 1e-6:
            eff = abs(p_out) / abs(p_in)
        else:
            eff = 0.0
        
        return np.clip(eff, 0, 1)
    
    def simulate_pfc_cycle(self, control_params):
        """
        Simulate one line cycle of PFC operation
        
        Args:
            control_params: Control parameters [duty_cycle, phase_shift, ...]
        
        Returns:
            metrics: Dictionary with simulation results
        """
        # This is a simplified simulation
        # In practice, this would use the PANN model to simulate the full cycle
        
        duty_cycle = control_params[0]
        
        # Generate input voltage waveform (one line cycle)
        n_points = 1000
        t = np.linspace(0, 1/f_line, n_points)
        vin_waveform = self.vin_peak * np.sin(omega_line * t)
        
        # Simplified current waveform (should be from PANN model)
        # For now, approximate as sinusoidal with duty cycle influence
        iin_waveform = duty_cycle * np.abs(np.sin(omega_line * t))
        
        # Calculate metrics
        pf = self.calculate_power_factor(vin_waveform, iin_waveform)
        thd = self.calculate_thd(iin_waveform)
        
        # Estimate power
        p_in = np.mean(vin_waveform * iin_waveform)
        p_out = self.target_power
        eff = self.calculate_efficiency(p_in, p_out)
        
        # Output voltage regulation error
        vout_error = abs(self.target_vout - 400) / self.target_vout
        
        metrics = {
            'power_factor': pf,
            'thd': thd,
            'efficiency': eff,
            'vout_error': vout_error,
            'p_in': p_in,
            'p_out': p_out
        }
        
        return metrics
    
    def objective_function(self, x, return_all=False):
        """
        Multi-objective function for PSO optimization
        
        Args:
            x: Control parameters array (n_particles, n_dims)
            return_all: If True, return all metrics
        
        Returns:
            cost: Cost value(s) for optimization
        """
        n_particles = x.shape[0]
        costs = np.zeros(n_particles)
        
        all_metrics = []
        
        for i in range(n_particles):
            control_params = x[i]
            
            # Simulate PFC operation
            metrics = self.simulate_pfc_cycle(control_params)
            
            # Multi-objective cost function
            # Minimize: (1 - PF) + THD/100 + (1 - Efficiency) + voltage_error
            
            pf_cost = (1 - metrics['power_factor']) * 10  # Weight: 10
            thd_cost = (metrics['thd'] / 100) * 5  # Weight: 5
            eff_cost = (1 - metrics['efficiency']) * 8  # Weight: 8
            vout_cost = metrics['vout_error'] * 3  # Weight: 3
            
            # Total cost
            costs[i] = pf_cost + thd_cost + eff_cost + vout_cost
            
            if return_all:
                all_metrics.append(metrics)
        
        if return_all:
            return costs, all_metrics
        else:
            return costs


class PFCOptimizer:
    """
    PFC Converter Optimizer using Particle Swarm Optimization
    """
    
    def __init__(self, pfc_model):
        """
        Initialize PFC optimizer
        
        Args:
            pfc_model: PFC PANN model instance
        """
        self.pfc_model = pfc_model
        
    def optimize(self, target_power, target_vout=400, 
                control_mode='CCM', n_iterations=100):
        """
        Optimize PFC control parameters
        
        Args:
            target_power: Target output power (W)
            target_vout: Target output voltage (V)
            control_mode: 'CCM', 'DCM', or 'BCM'
            n_iterations: Number of PSO iterations
        
        Returns:
            results: Dictionary with optimization results
        """
        # Define search boundaries based on control mode
        if control_mode == 'CCM':
            # For CCM: [duty_cycle, current_reference]
            upper_bounds = np.array([0.95, 20.0])
            lower_bounds = np.array([0.1, 0.5])
            n_dims = 2
        elif control_mode == 'DCM':
            # For DCM: [duty_cycle, peak_current]
            upper_bounds = np.array([0.8, 15.0])
            lower_bounds = np.array([0.05, 0.3])
            n_dims = 2
        elif control_mode == 'BCM':
            # For BCM: [on_time, current_threshold]
            upper_bounds = np.array([20e-6, 10.0])
            lower_bounds = np.array([1e-6, 0.2])
            n_dims = 2
        else:
            raise ValueError(f"Unknown control mode: {control_mode}")
        
        # Create objective function
        obj_func = PFCObjectiveFunction(self.pfc_model, target_power, target_vout)
        
        # Configure PSO optimizer
        options = {'c1': 2.05, 'c2': 2.05, 'w': 0.9}
        
        optimizer = ps.single.GlobalBestPSO(
            n_particles=50,
            dimensions=n_dims,
            bounds=(lower_bounds, upper_bounds),
            options=options,
            bh_strategy='periodic',
            vh_strategy='unmodified',
            oh_strategy={"w": "lin_variation"}
        )
        
        # Run optimization
        cost, optimal_params = optimizer.optimize(
            obj_func.objective_function,
            iters=n_iterations
        )
        
        # Evaluate final performance
        final_metrics = obj_func.simulate_pfc_cycle(optimal_params)
        
        results = {
            'optimal_params': optimal_params.tolist(),
            'cost': float(cost),
            'power_factor': final_metrics['power_factor'],
            'thd': final_metrics['thd'],
            'efficiency': final_metrics['efficiency'],
            'vout_error': final_metrics['vout_error'],
            'control_mode': control_mode,
            'target_power': target_power,
            'target_vout': target_vout
        }
        
        return results
    
    def verify_constraints(self, results):
        """
        Verify that optimization results meet design constraints
        
        Args:
            results: Optimization results dictionary
        
        Returns:
            verification: Dictionary with constraint verification
        """
        verification = {
            'power_factor_ok': results['power_factor'] >= power_factor_target,
            'thd_ok': results['thd'] <= thd_target,
            'efficiency_ok': results['efficiency'] >= efficiency_target,
            'all_constraints_met': False
        }
        
        verification['all_constraints_met'] = all([
            verification['power_factor_ok'],
            verification['thd_ok'],
            verification['efficiency_ok']
        ])
        
        return verification


def optimize_pfc_converter(pfc_model, target_power, target_vout=400,
                          control_mode='CCM', n_iterations=100):
    """
    Convenience function to optimize PFC converter
    
    Args:
        pfc_model: PFC PANN model
        target_power: Target output power (W)
        target_vout: Target output voltage (V)
        control_mode: Control mode ('CCM', 'DCM', 'BCM')
        n_iterations: Number of optimization iterations
    
    Returns:
        results: Optimization results
        verification: Constraint verification
    """
    optimizer = PFCOptimizer(pfc_model)
    results = optimizer.optimize(
        target_power,
        target_vout,
        control_mode,
        n_iterations
    )
    verification = optimizer.verify_constraints(results)
    
    return results, verification


def format_pfc_results(results, verification):
    """
    Format PFC optimization results for display
    
    Args:
        results: Optimization results
        verification: Constraint verification
    
    Returns:
        formatted_text: Formatted results string
    """
    text = f"""
### PFC Converter Optimization Results

**Control Mode:** {results['control_mode']}
**Target Power:** {results['target_power']:.1f} W
**Target Output Voltage:** {results['target_vout']:.1f} V

#### Performance Metrics:
- **Power Factor:** {results['power_factor']:.4f} {'✓' if verification['power_factor_ok'] else '✗'}
  (Target: ≥ {power_factor_target})
- **THD:** {results['thd']:.2f}% {'✓' if verification['thd_ok'] else '✗'}
  (Target: ≤ {thd_target}%)
- **Efficiency:** {results['efficiency']*100:.2f}% {'✓' if verification['efficiency_ok'] else '✗'}
  (Target: ≥ {efficiency_target*100}%)
- **Output Voltage Error:** {results['vout_error']*100:.2f}%

#### Optimal Control Parameters:
"""
    
    for i, param in enumerate(results['optimal_params']):
        text += f"- Parameter {i+1}: {param:.4f}\n"
    
    text += f"\n**Overall Status:** {'All constraints met ✓' if verification['all_constraints_met'] else 'Some constraints not met ✗'}"
    
    return text
