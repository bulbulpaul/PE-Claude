"""
Base topology module and error handling classes.

This module defines the abstract TopologyModule interface that all converter
topologies must implement, along with topology-specific error classes.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TopologyError(Exception):
    """Base exception class for topology-related errors."""
    pass


class UnsupportedTopologyError(TopologyError):
    """Raised when an unsupported topology is requested."""
    pass


class TopologyConfigurationError(TopologyError):
    """Raised when there's an error in topology configuration or loading."""
    pass


class TopologyModule(ABC):
    """
    Abstract base class for all converter topology modules.
    
    This interface defines the common methods that all topology implementations
    must provide according to requirements 1.1 and 1.2.
    """
    
    def __init__(self):
        """Initialize the topology module."""
        self.name: str = self.__class__.__name__
        self.description: str = "Base topology module"
        self.capabilities: List[str] = []
        self._initialized = False
        
    @abstractmethod
    def get_modulation_strategies(self) -> List[str]:
        """
        Get available modulation strategies for this topology.
        
        Returns:
            List[str]: List of available modulation strategy names
        """
        pass
    
    @abstractmethod
    def optimize_parameters(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize converter parameters based on specifications.
        
        Args:
            specs: Dictionary containing design specifications
            
        Returns:
            Dict[str, Any]: Optimized parameters
            
        Raises:
            TopologyError: If optimization fails
        """
        pass
    
    @abstractmethod
    def evaluate_performance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate converter performance with given parameters.
        
        Args:
            params: Dictionary containing converter parameters
            
        Returns:
            Dict[str, Any]: Performance evaluation results
            
        Raises:
            TopologyError: If evaluation fails
        """
        pass
    
    @abstractmethod
    def run_simulation(self, params: Dict[str, Any]) -> str:
        """
        Run circuit simulation with given parameters.
        
        Args:
            params: Dictionary containing simulation parameters
            
        Returns:
            str: Simulation results or path to results file
            
        Raises:
            TopologyError: If simulation fails
        """
        pass
    
    @abstractmethod
    def get_design_stages(self) -> List[str]:
        """
        Get the design stages specific to this topology.
        
        Returns:
            List[str]: List of design stage names
        """
        pass
    
    def validate_specifications(self, specs: Dict[str, Any]) -> bool:
        """
        Validate design specifications for this topology.
        
        Args:
            specs: Dictionary containing design specifications
            
        Returns:
            bool: True if specifications are valid
            
        Raises:
            TopologyError: If specifications are invalid
        """
        # Default implementation - can be overridden by subclasses
        required_fields = self.get_required_specifications()
        
        for field in required_fields:
            if field not in specs:
                raise TopologyError(f"Missing required specification: {field}")
        
        return True
    
    def get_required_specifications(self) -> List[str]:
        """
        Get list of required specification fields for this topology.
        
        Returns:
            List[str]: List of required specification field names
        """
        # Default required specifications - can be overridden by subclasses
        return ["input_voltage", "output_voltage", "power_level"]
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters for this topology.
        
        Returns:
            Dict[str, Any]: Default parameter values
        """
        # Default implementation - should be overridden by subclasses
        return {}
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the topology module with optional configuration.
        
        Args:
            config: Optional configuration dictionary
            
        Raises:
            TopologyConfigurationError: If initialization fails
        """
        try:
            if config:
                self._apply_configuration(config)
            
            self._perform_initialization()
            self._initialized = True
            
            logger.info("Topology module %s initialized successfully", self.name)
            
        except Exception as e:
            logger.error("Failed to initialize topology module %s: %s", self.name, e)
            raise TopologyConfigurationError(f"Initialization failed: {e}")
    
    def is_initialized(self) -> bool:
        """
        Check if the topology module is initialized.
        
        Returns:
            bool: True if initialized
        """
        return self._initialized
    
    def _apply_configuration(self, config: Dict[str, Any]) -> None:
        """
        Apply configuration to the topology module.
        
        Args:
            config: Configuration dictionary
        """
        # Default implementation - can be overridden by subclasses
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def _perform_initialization(self) -> None:
        """
        Perform topology-specific initialization.
        
        This method should be overridden by subclasses to implement
        topology-specific initialization logic.
        """
        # Default implementation - should be overridden by subclasses
        pass
    
    def get_capabilities(self) -> List[str]:
        """
        Get the capabilities of this topology.
        
        Returns:
            List[str]: List of capability descriptions
        """
        return self.capabilities.copy()
    
    def supports_capability(self, capability: str) -> bool:
        """
        Check if this topology supports a specific capability.
        
        Args:
            capability: Capability name to check
            
        Returns:
            bool: True if capability is supported
        """
        return capability in self.capabilities
    
    def get_topology_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about this topology.
        
        Returns:
            Dict[str, Any]: Topology information
        """
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.get_capabilities(),
            "modulation_strategies": self.get_modulation_strategies(),
            "design_stages": self.get_design_stages(),
            "required_specifications": self.get_required_specifications(),
            "initialized": self.is_initialized()
        }


class FallbackTopologyModule(TopologyModule):
    """
    Fallback topology module for error handling.
    
    This module provides basic functionality when a specific topology
    module cannot be loaded or is not available.
    """
    
    def __init__(self, topology_name: str):
        """
        Initialize fallback module.
        
        Args:
            topology_name: Name of the topology this is falling back for
        """
        super().__init__()
        self.topology_name = topology_name
        self.name = f"Fallback_{topology_name}"
        self.description = f"Fallback module for {topology_name} topology"
        self.capabilities = ["basic_error_handling"]
    
    def get_modulation_strategies(self) -> List[str]:
        """Return empty list as fallback."""
        return []
    
    def optimize_parameters(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """Raise error indicating topology not available."""
        raise TopologyError(f"Topology {self.topology_name} is not available for optimization")
    
    def evaluate_performance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Raise error indicating topology not available."""
        raise TopologyError(f"Topology {self.topology_name} is not available for performance evaluation")
    
    def run_simulation(self, params: Dict[str, Any]) -> str:
        """Raise error indicating topology not available."""
        raise TopologyError(f"Topology {self.topology_name} is not available for simulation")
    
    def get_design_stages(self) -> List[str]:
        """Return empty list as fallback."""
        return []