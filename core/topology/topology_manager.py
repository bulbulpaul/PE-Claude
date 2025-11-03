"""
TopologyManager - Central management system for converter topologies.

This module implements the central topology management system that handles
topology selection, switching, and management of available topologies.
"""

from typing import Dict, List, Optional, Any
import logging
from .base_topology import TopologyModule, UnsupportedTopologyError, TopologyConfigurationError

logger = logging.getLogger(__name__)


class TopologyManager:
    """
    Central management system for converter topologies.
    
    Handles topology selection, switching, and management of available topologies
    according to requirements 1.1 and 1.2.
    """
    
    def __init__(self):
        """Initialize the topology manager with available topologies."""
        self.available_topologies = ["DAB", "Buck", "PFC"]
        self.current_topology: Optional[str] = None
        self.topology_modules: Dict[str, TopologyModule] = {}
        self._loaded_modules: Dict[str, TopologyModule] = {}
        
        logger.info("TopologyManager initialized with topologies: %s", self.available_topologies)
    
    def select_topology(self, topology_name: str) -> TopologyModule:
        """
        Select and return the specified topology module.
        
        Args:
            topology_name: Name of the topology to select ("DAB", "Buck", "PFC")
            
        Returns:
            TopologyModule: The selected topology module instance
            
        Raises:
            UnsupportedTopologyError: If the topology is not supported
            TopologyConfigurationError: If the topology cannot be loaded
        """
        if topology_name not in self.available_topologies:
            raise UnsupportedTopologyError(f"Topology '{topology_name}' is not supported. "
                                         f"Available topologies: {self.available_topologies}")
        
        try:
            # Use lazy loading to get the module
            module = self._get_module(topology_name)
            self.current_topology = topology_name
            
            logger.info("Selected topology: %s", topology_name)
            return module
            
        except Exception as e:
            logger.error("Failed to select topology %s: %s", topology_name, e)
            raise TopologyConfigurationError(f"Failed to load topology '{topology_name}': {e}")
    
    def get_available_topologies(self) -> List[str]:
        """
        Get list of available topology names.
        
        Returns:
            List[str]: List of available topology names
        """
        return self.available_topologies.copy()
    
    def get_current_topology(self) -> Optional[str]:
        """
        Get the currently selected topology name.
        
        Returns:
            Optional[str]: Current topology name or None if none selected
        """
        return self.current_topology
    
    def recommend_topology(self, requirements: Dict[str, Any]) -> str:
        """
        Recommend the most suitable topology based on requirements.
        
        Args:
            requirements: Dictionary containing design requirements
            
        Returns:
            str: Recommended topology name
        """
        # Basic recommendation logic based on common requirements
        # This can be enhanced with more sophisticated algorithms
        
        # Check for bidirectional power requirement (DAB)
        if requirements.get("bidirectional", False):
            return "DAB"
        
        # Check for AC input (PFC)
        if requirements.get("input_type") == "AC":
            return "PFC"
        
        # Check for power factor requirements (PFC)
        if "power_factor" in requirements or "thd" in requirements:
            return "PFC"
        
        # Check for voltage step-down (Buck)
        input_voltage = requirements.get("input_voltage", 0)
        output_voltage = requirements.get("output_voltage", 0)
        if input_voltage > 0 and output_voltage > 0 and output_voltage < input_voltage:
            return "Buck"
        
        # Check for isolation requirement (DAB)
        if requirements.get("isolation", False):
            return "DAB"
        
        # Default recommendation
        logger.info("Using default topology recommendation: DAB")
        return "DAB"
    
    def register_topology_module(self, topology_name: str, module: TopologyModule):
        """
        Register a topology module with the manager.
        
        Args:
            topology_name: Name of the topology
            module: TopologyModule instance to register
        """
        if topology_name not in self.available_topologies:
            self.available_topologies.append(topology_name)
        
        self.topology_modules[topology_name] = module
        logger.info("Registered topology module: %s", topology_name)
    
    def _get_module(self, topology_name: str) -> TopologyModule:
        """
        Get topology module using lazy loading.
        
        Args:
            topology_name: Name of the topology
            
        Returns:
            TopologyModule: The topology module instance
        """
        if topology_name not in self._loaded_modules:
            # Try to get from registered modules first
            if topology_name in self.topology_modules:
                self._loaded_modules[topology_name] = self.topology_modules[topology_name]
            else:
                # Lazy load the module
                self._loaded_modules[topology_name] = self._load_module(topology_name)
        
        return self._loaded_modules[topology_name]
    
    def _load_module(self, topology_name: str) -> TopologyModule:
        """
        Load topology module dynamically.
        
        Args:
            topology_name: Name of the topology to load
            
        Returns:
            TopologyModule: Loaded topology module
            
        Raises:
            TopologyConfigurationError: If module cannot be loaded
        """
        try:
            if topology_name == "DAB":
                from .dab_topology import DABTopology
                return DABTopology()
            elif topology_name == "Buck":
                # Buck topology will be implemented in future tasks
                raise TopologyConfigurationError(f"Buck topology module not yet implemented")
            elif topology_name == "PFC":
                # PFC topology will be implemented in future tasks
                raise TopologyConfigurationError(f"PFC topology module not yet implemented")
            else:
                raise UnsupportedTopologyError(f"Unknown topology: {topology_name}")
                
        except ImportError as e:
            logger.error("Failed to import topology module %s: %s", topology_name, e)
            raise TopologyConfigurationError(f"Failed to import {topology_name} module: {e}")
    
    def get_topology_info(self, topology_name: str) -> Dict[str, Any]:
        """
        Get information about a specific topology.
        
        Args:
            topology_name: Name of the topology
            
        Returns:
            Dict[str, Any]: Topology information including capabilities and features
        """
        if topology_name not in self.available_topologies:
            raise UnsupportedTopologyError(f"Topology '{topology_name}' is not supported")
        
        try:
            module = self._get_module(topology_name)
            return {
                "name": topology_name,
                "modulation_strategies": module.get_modulation_strategies(),
                "description": getattr(module, 'description', f"{topology_name} converter topology"),
                "capabilities": getattr(module, 'capabilities', []),
                "supported": True
            }
        except Exception as e:
            logger.warning("Could not get full info for topology %s: %s", topology_name, e)
            return {
                "name": topology_name,
                "description": f"{topology_name} converter topology",
                "supported": False,
                "error": str(e)
            }