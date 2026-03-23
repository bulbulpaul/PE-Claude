"""
PFC Converter PLECS Simulation Interface

Provides interface to PLECS simulation models for PFC converters
with automatic parameter configuration and result visualization.

@reference: Based on PE-GPT PLECS integration framework
@code-author: PE-GPT Multi-Topology Extension
"""

import os
import threading
import xmlrpc.client
import subprocess
import platform
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import io

from func_timeout import func_set_timeout
from ..model_zoo.pann_pfc_vars import (
    Vin_rms, Vout_target, f_line, fs, L, C, R
)


class PFCPlecsThread(threading.Thread):
    """
    Thread for running PLECS simulation of PFC converter
    """
    
    _opts = {
        'ModelVars': {
            'Tstop': 0.1,  # Simulation stop time (s)
            'Vin_rms': Vin_rms,  # RMS input voltage
            'Vout': Vout_target,  # Target output voltage
            'P': 1000,  # Output power (W)
            'fs': fs,  # Switching frequency
            'L': L,  # Inductance
            'C': C,  # Capacitance
            'R': R,  # Load resistance
            'f_line': f_line  # Line frequency
        }
    }
    
    def __init__(self, model_name, file_path, **kwargs):
        """
        Initialize PFC PLECS thread
        
        Args:
            model_name: Name of the PLECS model
            file_path: Path to PLECS model file
            **kwargs: Additional model variables
        """
        super(PFCPlecsThread, self).__init__()
        self.model_name = model_name
        self.model_path = file_path
        self.server = xmlrpc.client.Server('http://localhost:1080/RPC2')
        self.kwargs = kwargs
        
    def update_opts(self):
        """Update simulation options with custom parameters"""
        opts = {
            'ModelVars': {
                'Tstop': self.__class__._opts['ModelVars']['Tstop'],
                'Vin_rms': self.__class__._opts['ModelVars']['Vin_rms'],
                'Vout': self.__class__._opts['ModelVars']['Vout'],
                'f_line': self.__class__._opts['ModelVars']['f_line']
            }
        }
        opts['ModelVars'].update(self.kwargs)
        return opts
    
    def load(self):
        """Load PLECS model"""
        self.server.plecs.load(self.model_path)
    
    def close(self):
        """Close PLECS model"""
        self.server.plecs.close(self.model_name)
    
    @func_set_timeout(30)
    def run_once(self, opts):
        """
        Run simulation once with timeout
        
        Args:
            opts: Simulation options
        """
        self.load()
        self.server.plecs.simulate(self.model_name, opts)
        # self.close()  # Uncomment to close automatically
    
    def run(self):
        """Execute the simulation thread"""
        try:
            opts = self.update_opts()
            self.run_once(opts)
        except Exception as e:
            st.write(f"PLECS simulation error: {e}")


def open_plecs(file_path):
    """
    Open PLECS file in the appropriate application
    
    Args:
        file_path: Path to PLECS file
    """
    system = platform.system()
    if system == 'Windows':
        os.startfile(file_path)
    elif system == 'Darwin':  # macOS
        subprocess.call(["open", file_path])
    elif system == 'Linux':
        subprocess.call(["xdg-open", file_path])


def pfc_plecs_simulation(control_mode, target_power, target_vout, 
                        optimal_params, L_val=None, C_val=None, R_val=None):
    """
    Run PFC PLECS simulation with specified parameters
    
    Args:
        control_mode: 'CCM', 'DCM', or 'BCM'
        target_power: Target output power (W)
        target_vout: Target output voltage (V)
        optimal_params: Optimized control parameters
        L_val: Inductance value (optional, uses default if None)
        C_val: Capacitance value (optional, uses default if None)
        R_val: Load resistance (optional, calculated from power if None)
    """
    # Load the PLECS file
    model_name = "PFC"
    file_path = os.path.abspath(f"core/simulation/{model_name}.plecs")
    
    # Check if file exists, if not, create a placeholder message
    if not os.path.exists(file_path):
        st.warning(f"PLECS model file not found at {file_path}")
        st.info("PFC PLECS model integration is ready. Please add PFC.plecs file to core/simulation/ directory.")
        return
    
    # Open PLECS file
    open_plecs(file_path)
    
    st.write(f"Running PFC simulation in {control_mode} mode...")
    
    # Calculate load resistance if not provided
    if R_val is None:
        R_val = target_vout ** 2 / target_power
    
    # Use default values if not provided
    if L_val is None:
        L_val = L
    if C_val is None:
        C_val = C
    
    # Prepare control parameters based on mode
    if control_mode == 'CCM':
        duty_cycle = optimal_params[0] if len(optimal_params) > 0 else 0.5
        current_ref = optimal_params[1] if len(optimal_params) > 1 else 10.0
        kwargs = {
            "P": target_power,
            "Vout": target_vout,
            "R": R_val,
            "L": L_val,
            "C": C_val,
            "duty_cycle": duty_cycle,
            "current_ref": current_ref,
            "control_mode": 1  # CCM mode indicator
        }
    elif control_mode == 'DCM':
        duty_cycle = optimal_params[0] if len(optimal_params) > 0 else 0.4
        peak_current = optimal_params[1] if len(optimal_params) > 1 else 8.0
        kwargs = {
            "P": target_power,
            "Vout": target_vout,
            "R": R_val,
            "L": L_val,
            "C": C_val,
            "duty_cycle": duty_cycle,
            "peak_current": peak_current,
            "control_mode": 2  # DCM mode indicator
        }
    elif control_mode == 'BCM':
        on_time = optimal_params[0] if len(optimal_params) > 0 else 10e-6
        current_threshold = optimal_params[1] if len(optimal_params) > 1 else 5.0
        kwargs = {
            "P": target_power,
            "Vout": target_vout,
            "R": R_val,
            "L": L_val,
            "C": C_val,
            "on_time": on_time,
            "current_threshold": current_threshold,
            "control_mode": 3  # BCM mode indicator
        }
    else:
        st.error(f"Unknown control mode: {control_mode}")
        return
    
    # Conduct the PLECS simulation
    thread = PFCPlecsThread(model_name, file_path, **kwargs)
    thread.start()
    
    st.success("PLECS simulation started. Check the PLECS window for results.")


def visualize_pfc_waveforms(simulation_data=None):
    """
    Visualize PFC converter waveforms
    
    Args:
        simulation_data: Dictionary with simulation results (optional)
    
    Returns:
        plot_buffer: BytesIO buffer with plot
    """
    if simulation_data is None:
        # Generate example waveforms for demonstration
        t = np.linspace(0, 0.02, 1000)  # 20ms (one line cycle at 50Hz)
        
        # Input voltage (sinusoidal)
        vin = Vin_rms * np.sqrt(2) * np.sin(2 * np.pi * f_line * t)
        
        # Input current (should follow voltage for high PF)
        iin = 5 * np.abs(np.sin(2 * np.pi * f_line * t))
        
        # Output voltage (DC with ripple)
        vout = Vout_target + 10 * np.sin(2 * np.pi * 2 * f_line * t)
        
        # Inductor current (high frequency switching)
        iL = 8 + 2 * np.sin(2 * np.pi * f_line * t) + \
             0.5 * np.sin(2 * np.pi * fs * t)
    else:
        # Use actual simulation data
        t = simulation_data.get('time', np.linspace(0, 0.02, 1000))
        vin = simulation_data.get('vin', np.zeros_like(t))
        iin = simulation_data.get('iin', np.zeros_like(t))
        vout = simulation_data.get('vout', np.zeros_like(t))
        iL = simulation_data.get('iL', np.zeros_like(t))
    
    # Create figure with subplots
    fig, axes = plt.subplots(4, 1, figsize=(12, 10))
    
    # Input voltage
    axes[0].plot(t * 1000, vin, 'b-', linewidth=2)
    axes[0].set_ylabel('Input Voltage (V)', fontsize=10)
    axes[0].set_title('PFC Converter Waveforms', fontsize=12, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim([0, t[-1] * 1000])
    
    # Input current
    axes[1].plot(t * 1000, iin, 'r-', linewidth=2)
    axes[1].set_ylabel('Input Current (A)', fontsize=10)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim([0, t[-1] * 1000])
    
    # Output voltage
    axes[2].plot(t * 1000, vout, 'g-', linewidth=2)
    axes[2].axhline(y=Vout_target, color='k', linestyle='--', 
                   label=f'Target: {Vout_target}V', alpha=0.5)
    axes[2].set_ylabel('Output Voltage (V)', fontsize=10)
    axes[2].legend(loc='upper right')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim([0, t[-1] * 1000])
    
    # Inductor current
    axes[3].plot(t * 1000, iL, 'm-', linewidth=1.5)
    axes[3].set_ylabel('Inductor Current (A)', fontsize=10)
    axes[3].set_xlabel('Time (ms)', fontsize=10)
    axes[3].grid(True, alpha=0.3)
    axes[3].set_xlim([0, t[-1] * 1000])
    
    plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close()
    buf.seek(0)  # Reset to beginning after writing
    
    return buf


def calculate_pfc_metrics_from_waveforms(vin, iin, vout, iL, fs_sample):
    """
    Calculate PFC performance metrics from waveforms
    
    Args:
        vin: Input voltage waveform
        iin: Input current waveform
        vout: Output voltage waveform
        iL: Inductor current waveform
        fs_sample: Sampling frequency
    
    Returns:
        metrics: Dictionary with calculated metrics
    """
    # Power factor
    p_real = np.mean(vin * iin)
    v_rms = np.sqrt(np.mean(vin ** 2))
    i_rms = np.sqrt(np.mean(iin ** 2))
    s_apparent = v_rms * i_rms
    power_factor = p_real / s_apparent if s_apparent > 0 else 0
    
    # THD (simplified)
    fft_iin = np.fft.fft(iin)
    fft_mag = np.abs(fft_iin)
    fundamental = fft_mag[1]
    harmonics = fft_mag[2:41]  # 2nd to 40th harmonic
    thd = 100 * np.sqrt(np.sum(harmonics ** 2)) / fundamental if fundamental > 0 else 100
    
    # Output voltage ripple
    vout_mean = np.mean(vout)
    vout_ripple = np.max(vout) - np.min(vout)
    vout_ripple_percent = 100 * vout_ripple / vout_mean
    
    # Efficiency (estimated)
    p_out = vout_mean ** 2 / R
    efficiency = abs(p_out) / abs(p_real) if abs(p_real) > 1e-6 else 0
    efficiency = np.clip(efficiency, 0, 1)
    
    metrics = {
        'power_factor': power_factor,
        'thd': thd,
        'efficiency': efficiency,
        'vout_mean': vout_mean,
        'vout_ripple': vout_ripple,
        'vout_ripple_percent': vout_ripple_percent,
        'p_in': p_real,
        'p_out': p_out
    }
    
    return metrics


def format_pfc_simulation_results(metrics):
    """
    Format PFC simulation results for display
    
    Args:
        metrics: Dictionary with simulation metrics
    
    Returns:
        formatted_text: Formatted results string
    """
    text = f"""
### PFC Simulation Results

#### Performance Metrics:
- **Power Factor:** {metrics['power_factor']:.4f}
- **THD:** {metrics['thd']:.2f}%
- **Efficiency:** {metrics['efficiency']*100:.2f}%

#### Power:
- **Input Power:** {metrics['p_in']:.2f} W
- **Output Power:** {metrics['p_out']:.2f} W

#### Output Voltage:
- **Mean Output Voltage:** {metrics['vout_mean']:.2f} V
- **Output Voltage Ripple:** {metrics['vout_ripple']:.2f} V ({metrics['vout_ripple_percent']:.2f}%)
"""
    
    return text
