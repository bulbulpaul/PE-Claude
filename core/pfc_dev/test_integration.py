"""
Integration test for PFC Development System

This module provides basic integration testing for the PFC Development System
to verify that all components work together correctly.

@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin
@github: https://github.com/XinzeLee/PE-GPT
"""

import logging
import numpy as np
from typing import Dict, Any

from .pann_builder import PANNBuilder, PFCPhysicalParameters
from .pann_trainer import PANNTrainer, TrainingConfig
from .pann_evaluator import PANNEvaluator, EvaluationConfig
from .development_manager import DevelopmentManager

logger = logging.getLogger(__name__)


def test_pfc_development_system() -> bool:
    """
    Test the complete PFC Development System integration.
    
    Returns:
        bool: True if all tests pass
    """
    logger.info("Starting PFC Development System integration test")
    
    try:
        # Test 1: PANN Builder
        logger.info("Testing PANN Builder...")
        builder = PANNBuilder()
        
        # Test parameter extraction
        tech_info = """
        PFC Converter Specifications:
        - Inductance: 200 μH
        - Capacitance: 470 μF
        - Switching frequency: 100 kHz
        - Input voltage: 230V RMS
        - Output voltage: 400V DC
        - Power rating: 500W
        - Control mode: CCM
        """
        
        params = builder.extract_physical_parameters(tech_info)
        assert abs(params.inductance - 200e-6) < 1e-9, f"Expected 200e-6, got {params.inductance}"
        assert abs(params.capacitance - 470e-6) < 1e-9, f"Expected 470e-6, got {params.capacitance}"
        logger.info("✅ PANN Builder test passed")
        
        # Test 2: PANN Trainer
        logger.info("Testing PANN Trainer...")
        trainer = PANNTrainer(TrainingConfig(num_epochs=5, batch_size=16))
        
        # Generate test data
        circuit_params = {'L': 200e-6, 'C': 470e-6, 'f_sw': 100e3}
        operating_conditions = [
            {'v_in_rms': 230, 'load_power': 500, 'temperature': 25, 'line_frequency': 50}
        ]
        
        sim_data = trainer.generate_simulation_data(circuit_params, operating_conditions, num_samples=100)
        assert 'power_factor' in sim_data, "Missing power_factor in simulation data"
        assert len(sim_data['power_factor']) == 100, f"Expected 100 samples, got {len(sim_data['power_factor'])}"
        logger.info("✅ PANN Trainer test passed")
        
        # Test 3: PANN Evaluator
        logger.info("Testing PANN Evaluator...")
        evaluator = PANNEvaluator(EvaluationConfig(generate_plots=False))
        
        # Create mock model and test data
        pann_model = builder.build_from_pdf_query("PFC converter parameters")
        test_data = {
            'power_factor': np.random.uniform(0.95, 0.99, 50),
            'thd': np.random.uniform(2.0, 5.0, 50),
            'efficiency': np.random.uniform(0.92, 0.96, 50)
        }
        
        report = evaluator.comprehensive_evaluation(pann_model, test_data)
        assert report.quality_score >= 0.0, f"Invalid quality score: {report.quality_score}"
        assert report.power_factor_metrics.mae >= 0.0, f"Invalid MAE: {report.power_factor_metrics.mae}"
        logger.info("✅ PANN Evaluator test passed")
        
        # Test 4: Development Manager
        logger.info("Testing Development Manager...")
        dev_manager = DevelopmentManager("Test_Project")
        
        # Test status retrieval
        status = dev_manager.get_current_status()
        assert status.current_phase.value == "data_collection", f"Expected data_collection, got {status.current_phase.value}"
        assert status.overall_progress >= 0.0, f"Invalid progress: {status.overall_progress}"
        
        # Test phase prerequisites
        from .development_manager import DevelopmentPhase
        assert dev_manager.check_phase_prerequisites(DevelopmentPhase.DATA_COLLECTION) == True
        assert dev_manager.check_phase_prerequisites(DevelopmentPhase.MODEL_CONSTRUCTION) == False
        logger.info("✅ Development Manager test passed")
        
        logger.info("🎉 All PFC Development System integration tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False


def test_component_interactions() -> bool:
    """
    Test interactions between different components.
    
    Returns:
        bool: True if interaction tests pass
    """
    logger.info("Testing component interactions...")
    
    try:
        # Test Builder -> Trainer interaction
        builder = PANNBuilder()
        trainer = PANNTrainer()
        
        # Build model
        model = builder.build_from_pdf_query("PFC boost converter")
        
        # Generate training data
        sim_data = trainer.generate_simulation_data(
            {'L': 200e-6, 'C': 470e-6}, 
            [{'v_in_rms': 230, 'load_power': 500, 'temperature': 25, 'line_frequency': 50}],
            num_samples=50
        )
        
        # Train model (simplified)
        training_result = trainer.train_with_hybrid_data(model, sim_data)
        assert training_result.final_loss >= 0.0, "Invalid training result"
        
        # Test Trainer -> Evaluator interaction
        evaluator = PANNEvaluator()
        report = evaluator.comprehensive_evaluation(model, sim_data)
        assert report.quality_score >= 0.0, "Invalid evaluation report"
        
        logger.info("✅ Component interaction tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Component interaction test failed: {e}")
        return False


if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run tests
    success = test_pfc_development_system() and test_component_interactions()
    
    if success:
        print("🎉 All tests passed! PFC Development System is working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")