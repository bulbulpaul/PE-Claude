"""
Integration tests for PFC Converter implementation

Tests the complete PFC converter system including:
- PANN model creation
- Optimization algorithms
- PLECS simulation interface
- GUI task integration
"""

import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_pfc_pann_model_creation():
    """Test PFC PANN model can be created"""
    from core.model_zoo.pann_pfc import create_pfc_pann_model
    
    # Test CCM mode
    model_ccm = create_pfc_pann_model(control_mode='CCM')
    assert model_ccm is not None
    assert model_ccm.control_mode == 'CCM'
    
    # Test DCM mode
    model_dcm = create_pfc_pann_model(control_mode='DCM')
    assert model_dcm is not None
    assert model_dcm.control_mode == 'DCM'
    
    # Test BCM mode
    model_bcm = create_pfc_pann_model(control_mode='BCM')
    assert model_bcm is not None
    assert model_bcm.control_mode == 'BCM'
    
    print("✓ PFC PANN model creation test passed")


def test_pfc_optimizer():
    """Test PFC optimizer functionality"""
    from core.model_zoo.pann_pfc import create_pfc_pann_model
    from core.optim.pfc_optimizer import PFCOptimizer
    
    # Create model
    pfc_model = create_pfc_pann_model(control_mode='CCM')
    
    # Create optimizer
    optimizer = PFCOptimizer(pfc_model)
    assert optimizer is not None
    
    # Run optimization with small iteration count for testing
    results = optimizer.optimize(
        target_power=1000,
        target_vout=400,
        control_mode='CCM',
        n_iterations=10  # Small number for fast testing
    )
    
    # Verify results structure
    assert 'optimal_params' in results
    assert 'power_factor' in results
    assert 'thd' in results
    assert 'efficiency' in results
    assert 'control_mode' in results
    
    # Verify reasonable values
    assert 0 <= results['power_factor'] <= 1
    assert 0 <= results['thd'] <= 100
    assert 0 <= results['efficiency'] <= 1
    
    print("✓ PFC optimizer test passed")
    print(f"  Power Factor: {results['power_factor']:.4f}")
    print(f"  THD: {results['thd']:.2f}%")
    print(f"  Efficiency: {results['efficiency']*100:.2f}%")


def test_pfc_objective_function():
    """Test PFC objective function calculations"""
    from core.model_zoo.pann_pfc import create_pfc_pann_model
    from core.optim.pfc_optimizer import PFCObjectiveFunction
    
    pfc_model = create_pfc_pann_model()
    obj_func = PFCObjectiveFunction(pfc_model, target_power=1000)
    
    # Test with sample control parameters
    test_params = np.array([[0.5, 10.0]])
    
    # Test objective function
    cost = obj_func.objective_function(test_params)
    assert cost is not None
    assert len(cost) == 1
    assert cost[0] >= 0  # Cost should be non-negative
    
    # Test with return_all
    costs, metrics = obj_func.objective_function(test_params, return_all=True)
    assert len(metrics) == 1
    assert 'power_factor' in metrics[0]
    assert 'thd' in metrics[0]
    assert 'efficiency' in metrics[0]
    
    print("✓ PFC objective function test passed")


def test_pfc_waveform_visualization():
    """Test PFC waveform visualization"""
    from core.simulation.pfc_plecs import visualize_pfc_waveforms
    
    # Test with default (example) data
    plot_buffer = visualize_pfc_waveforms()
    assert plot_buffer is not None
    
    # Read the buffer to check it has content
    content = plot_buffer.read()
    assert len(content) > 0  # Buffer should have content
    
    print("✓ PFC waveform visualization test passed")


def test_pfc_metrics_calculation():
    """Test PFC metrics calculation from waveforms"""
    from core.simulation.pfc_plecs import calculate_pfc_metrics_from_waveforms
    
    # Generate sample waveforms
    t = np.linspace(0, 0.02, 1000)
    vin = 311 * np.sin(2 * np.pi * 50 * t)
    iin = 5 * np.abs(np.sin(2 * np.pi * 50 * t))
    vout = 400 + 10 * np.sin(2 * np.pi * 100 * t)
    iL = 8 + 2 * np.sin(2 * np.pi * 50 * t)
    
    # Calculate metrics
    metrics = calculate_pfc_metrics_from_waveforms(vin, iin, vout, iL, 50000)
    
    # Verify metrics structure
    assert 'power_factor' in metrics
    assert 'thd' in metrics
    assert 'efficiency' in metrics
    assert 'vout_mean' in metrics
    assert 'vout_ripple' in metrics
    
    # Verify reasonable values
    assert 0 <= metrics['power_factor'] <= 1
    assert metrics['thd'] >= 0
    assert 0 <= metrics['efficiency'] <= 1
    assert metrics['vout_mean'] > 0
    
    print("✓ PFC metrics calculation test passed")
    print(f"  Power Factor: {metrics['power_factor']:.4f}")
    print(f"  THD: {metrics['thd']:.2f}%")


def test_pfc_variables():
    """Test PFC variables are properly defined"""
    from core.model_zoo import pann_pfc_vars
    
    # Check critical variables exist
    assert hasattr(pann_pfc_vars, 'L')
    assert hasattr(pann_pfc_vars, 'C')
    assert hasattr(pann_pfc_vars, 'R')
    assert hasattr(pann_pfc_vars, 'Vin_rms')
    assert hasattr(pann_pfc_vars, 'Vout_target')
    assert hasattr(pann_pfc_vars, 'fs')
    assert hasattr(pann_pfc_vars, 'f_line')
    
    # Check reasonable values
    assert pann_pfc_vars.L > 0
    assert pann_pfc_vars.C > 0
    assert pann_pfc_vars.R > 0
    assert pann_pfc_vars.Vin_rms > 0
    assert pann_pfc_vars.Vout_target > 0
    
    print("✓ PFC variables test passed")


def test_pfc_format_results():
    """Test PFC results formatting"""
    from core.optim.pfc_optimizer import format_pfc_results
    
    # Sample results
    results = {
        'control_mode': 'CCM',
        'target_power': 1000,
        'target_vout': 400,
        'power_factor': 0.99,
        'thd': 4.5,
        'efficiency': 0.95,
        'vout_error': 0.01,
        'optimal_params': [0.5, 10.0]
    }
    
    verification = {
        'power_factor_ok': True,
        'thd_ok': True,
        'efficiency_ok': True,
        'all_constraints_met': True
    }
    
    # Format results
    formatted = format_pfc_results(results, verification)
    
    assert formatted is not None
    assert isinstance(formatted, str)
    assert 'CCM' in formatted
    assert '0.99' in formatted or '0.9900' in formatted
    
    print("✓ PFC format results test passed")


def run_all_tests():
    """Run all PFC integration tests"""
    print("\n" + "="*60)
    print("Running PFC Integration Tests")
    print("="*60 + "\n")
    
    tests = [
        ("PFC PANN Model Creation", test_pfc_pann_model_creation),
        ("PFC Variables", test_pfc_variables),
        ("PFC Objective Function", test_pfc_objective_function),
        ("PFC Optimizer", test_pfc_optimizer),
        ("PFC Waveform Visualization", test_pfc_waveform_visualization),
        ("PFC Metrics Calculation", test_pfc_metrics_calculation),
        ("PFC Format Results", test_pfc_format_results),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}")
            print("-" * 60)
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_name} FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
