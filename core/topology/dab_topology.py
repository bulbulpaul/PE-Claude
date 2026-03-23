"""
DAB (Dual Active Bridge) topology module implementation.

This module wraps existing DAB functionality to conform to the TopologyModule interface
while maintaining complete backward compatibility.
"""

from typing import Dict, List, Any, Optional
import logging
import streamlit as st
from .base_topology import TopologyModule, TopologyError

logger = logging.getLogger(__name__)


class DABTopology(TopologyModule):
    """
    DAB (Dual Active Bridge) converter topology implementation.
    
    This class wraps existing DAB functionality to conform to the TopologyModule
    interface while maintaining complete backward compatibility according to
    requirements 4.1, 4.2, 4.3, and 4.4.
    """
    
    def __init__(self):
        """Initialize DAB topology module."""
        super().__init__()
        self.name = "DAB"
        self.description = "Dual Active Bridge converter topology"
        self.capabilities = [
            "bidirectional_power_flow",
            "galvanic_isolation", 
            "soft_switching",
            "multiple_modulation_strategies",
            "pann_modeling",
            "plecs_simulation"
        ]
        
        # Initialize DAB-specific components
        self._model_pann = None
        self._optimizer_pann = None
        self._clamper = None
        self._n = None  # transformer turns ratio
        
        logger.info("DAB topology module initialized")
    
    def get_modulation_strategies(self) -> List[str]:
        """
        Get available modulation strategies for DAB converter.
        
        Returns:
            List[str]: Available modulation strategies
        """
        return ["SPS", "DPS", "EPS", "TPS", "5DOF"]
    
    def get_required_specifications(self) -> List[str]:
        """
        Get required specifications for DAB converter.
        
        Returns:
            List[str]: Required specification fields
        """
        return ["input_voltage", "output_voltage", "power_level"]
    
    def get_design_stages(self) -> List[str]:
        """
        Get design stages for DAB converter.
        
        Returns:
            List[str]: Design stage names
        """
        return [
            "init_design",
            "recommend_modulation", 
            "evaluate_dab",
            "simulation_verification",
            "train_pann"
        ]
    
    def optimize_parameters(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize DAB converter parameters based on specifications.
        
        Args:
            specs: Design specifications containing input_voltage, output_voltage, 
                  power_level, and optional modulation strategy
                  
        Returns:
            Dict[str, Any]: Optimized parameters including modulation parameters,
                          performance metrics, and recommended strategy
                          
        Raises:
            TopologyError: If optimization fails
        """
        try:
            # Validate specifications
            self.validate_specifications(specs)
            
            # Extract specifications
            input_voltage = specs["input_voltage"]
            output_voltage = specs["output_voltage"] 
            power_level = specs["power_level"]
            modulation = specs.get("modulation", self._recommend_modulation_strategy(specs))
            
            # Import DAB optimization functionality
            from ..optim.optimizers import optimize_mod_dab
            
            # Perform optimization using existing DAB optimization
            ipp, zvs, zcs, power, pos, plot, updated_modulation = optimize_mod_dab(
                input_voltage, output_voltage, power_level, modulation
            )
            
            # Return optimized parameters
            return {
                "modulation_strategy": updated_modulation,
                "modulation_parameters": pos,
                "current_stress": ipp,
                "zvs_achievement": zvs,
                "zcs_achievement": zcs,
                "power_level": power,
                "input_voltage": input_voltage,
                "output_voltage": output_voltage,
                "optimization_plot": plot
            }
            
        except Exception as e:
            logger.error("DAB parameter optimization failed: %s", e)
            raise TopologyError(f"DAB optimization failed: {e}")
    
    def evaluate_performance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate DAB converter performance with given parameters.
        
        Args:
            params: Parameters including operating conditions and modulation settings
            
        Returns:
            Dict[str, Any]: Performance evaluation results
            
        Raises:
            TopologyError: If evaluation fails
        """
        try:
            # If optimization parameters are provided, use them directly
            if "modulation_parameters" in params:
                return {
                    "current_stress": params.get("current_stress"),
                    "zvs_achievement": params.get("zvs_achievement"),
                    "zcs_achievement": params.get("zcs_achievement"),
                    "power_level": params.get("power_level"),
                    "modulation_strategy": params.get("modulation_strategy"),
                    "efficiency_estimate": self._estimate_efficiency(params)
                }
            
            # Otherwise, perform optimization to get performance
            specs = {
                "input_voltage": params["input_voltage"],
                "output_voltage": params["output_voltage"],
                "power_level": params["power_level"],
                "modulation": params.get("modulation", "TPS")
            }
            
            optimized = self.optimize_parameters(specs)
            
            return {
                "current_stress": optimized["current_stress"],
                "zvs_achievement": optimized["zvs_achievement"], 
                "zcs_achievement": optimized["zcs_achievement"],
                "power_level": optimized["power_level"],
                "modulation_strategy": optimized["modulation_strategy"],
                "efficiency_estimate": self._estimate_efficiency(optimized)
            }
            
        except Exception as e:
            logger.error("DAB performance evaluation failed: %s", e)
            raise TopologyError(f"DAB performance evaluation failed: {e}")
    
    def run_simulation(self, params: Dict[str, Any]) -> str:
        """
        Run PLECS simulation for DAB converter.
        
        Args:
            params: Simulation parameters including operating conditions and modulation
            
        Returns:
            str: Simulation status message
            
        Raises:
            TopologyError: If simulation fails
        """
        try:
            # Import DAB PLECS functionality
            from ..simulation.load_plecs import dab_plecs
            
            # Extract parameters
            modulation = params.get("modulation_strategy", params.get("modulation", "TPS"))
            input_voltage = params["input_voltage"]
            output_voltage = params["output_voltage"]
            power_level = params["power_level"]
            mod_params = params.get("modulation_parameters", [])
            
            # Run PLECS simulation using existing functionality
            dab_plecs(modulation, input_voltage, output_voltage, power_level, *mod_params)
            
            return "PLECS simulation completed successfully. Check PLECS interface for results."
            
        except Exception as e:
            logger.error("DAB PLECS simulation failed: %s", e)
            raise TopologyError(f"DAB simulation failed: {e}")
    
    def train_pann_model(self) -> Dict[str, Any]:
        """
        Train or retrain the DAB PANN model.
        
        Returns:
            Dict[str, Any]: Training results including losses and model info
            
        Raises:
            TopologyError: If training fails
        """
        try:
            # Import DAB PANN training functionality
            from ..model_zoo.pann_dab import train_dab
            
            # Perform training using existing functionality
            plot, test_loss, val_loss = train_dab()
            
            return {
                "test_loss": test_loss,
                "validation_loss": val_loss,
                "training_plot": plot,
                "status": "Training completed successfully"
            }
            
        except Exception as e:
            logger.error("DAB PANN training failed: %s", e)
            raise TopologyError(f"DAB PANN training failed: {e}")
    
    def _recommend_modulation_strategy(self, specs: Dict[str, Any]) -> str:
        """
        Recommend modulation strategy based on specifications.
        
        Args:
            specs: Design specifications
            
        Returns:
            str: Recommended modulation strategy
        """
        # Use existing modulation recommendation logic
        # This is a simplified version - the actual recommendation logic
        # is handled by the LLM agents in the existing system
        
        power_level = specs.get("power_level", 0)
        
        if power_level > 5000:  # High power
            return "5DOF"
        elif power_level > 2000:  # Medium-high power
            return "TPS"
        elif power_level > 500:   # Medium power
            return "DPS"
        else:  # Low power
            return "SPS"
    
    def _estimate_efficiency(self, params: Dict[str, Any]) -> float:
        """
        Estimate efficiency based on parameters.
        
        Args:
            params: Converter parameters
            
        Returns:
            float: Estimated efficiency (0-1)
        """
        # Simplified efficiency estimation
        # In practice, this would use the PANN model or detailed calculations
        
        zvs = params.get("zvs_achievement", 0)
        zcs = params.get("zcs_achievement", 0)
        current_stress = params.get("current_stress", 1)
        
        # Basic efficiency estimation based on soft switching achievement
        base_efficiency = 0.85
        zvs_bonus = zvs * 0.05  # Up to 5% bonus for ZVS
        zcs_bonus = zcs * 0.03  # Up to 3% bonus for ZCS
        current_penalty = min(current_stress / 10, 0.1)  # Penalty for high current stress
        
        efficiency = base_efficiency + zvs_bonus + zcs_bonus - current_penalty
        return min(max(efficiency, 0.7), 0.98)  # Clamp between 70% and 98%
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters for DAB converter.
        
        Returns:
            Dict[str, Any]: Default parameter values
        """
        return {
            "input_voltage": 200.0,
            "output_voltage": 200.0, 
            "power_level": 800.0,
            "modulation": "TPS",
            "switching_frequency": 50000.0,  # 50 kHz
            "transformer_turns_ratio": 1.0,
            "leakage_inductance": 50e-6,  # 50 µH
            "dead_time": 200e-9  # 200 ns
        }
    
    def _perform_initialization(self) -> None:
        """
        Perform DAB-specific initialization.
        """
        try:
            # Initialize DAB PANN model and related components
            from ..model_zoo.pann_dab import model_pann, optimizer_pann, clamper
            from ..model_zoo.pann_dab_vars import n
            
            self._model_pann = model_pann
            self._optimizer_pann = optimizer_pann
            self._clamper = clamper
            self._n = n
            
            # Ensure session state variables are initialized
            if "model_pann" not in st.session_state:
                st.session_state["model_pann"] = model_pann
            if "optimizer_pann" not in st.session_state:
                st.session_state["optimizer_pann"] = optimizer_pann
            if "clamper" not in st.session_state:
                st.session_state["clamper"] = clamper
            
            logger.info("DAB-specific initialization completed")
            
        except Exception as e:
            logger.warning("DAB initialization had issues: %s", e)
            # Don't raise error to maintain compatibility
    
    def get_pann_model(self):
        """
        Get the DAB PANN model.
        
        Returns:
            PANN model instance
        """
        if not self._initialized:
            self.initialize()
        return self._model_pann
    
    def supports_capability(self, capability: str) -> bool:
        """
        Check if DAB supports a specific capability.
        
        Args:
            capability: Capability to check
            
        Returns:
            bool: True if supported
        """
        return capability in self.capabilities