"""
Topology management system for PE-GPT multi-topology converter support.

This module provides the foundation for managing different converter topologies
including DAB, Buck, and PFC converters.
"""

from .topology_manager import TopologyManager
from .base_topology import TopologyModule, TopologyError, UnsupportedTopologyError, TopologyConfigurationError

__all__ = [
    'TopologyManager',
    'TopologyModule', 
    'TopologyError',
    'UnsupportedTopologyError',
    'TopologyConfigurationError'
]