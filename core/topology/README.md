# Topology Management System

This module provides the foundation for PE-GPT's multi-topology converter support, implementing a centralized management system for different converter topologies including DAB, Buck, and PFC converters.

## Architecture

The topology management system consists of three main components:

### 1. TopologyManager (`topology_manager.py`)
Central management system that handles:
- Topology selection and switching
- Available topology management  
- Topology recommendation based on requirements
- Lazy loading of topology modules

### 2. TopologyModule (`base_topology.py`)
Abstract base class that defines the common interface all topology implementations must provide:
- `get_modulation_strategies()` - Available modulation strategies
- `optimize_parameters()` - Parameter optimization
- `evaluate_performance()` - Performance evaluation
- `run_simulation()` - Circuit simulation
- `get_design_stages()` - Design workflow stages

### 3. DABTopology (`dab_topology.py`)
DAB (Dual Active Bridge) converter implementation that wraps existing DAB functionality while maintaining complete backward compatibility.

## Usage

### Basic Usage

```python
from core.topology import TopologyManager

# Initialize the topology manager
manager = TopologyManager()

# Get available topologies
topologies = manager.get_available_topologies()
print(topologies)  # ['DAB', 'Buck', 'PFC']

# Select a topology
dab_module = manager.select_topology("DAB")

# Get topology information
info = manager.get_topology_info("DAB")
print(info)
```

### Topology Recommendation

```python
# Define design requirements
requirements = {
    "input_voltage": 200,
    "output_voltage": 100, 
    "power_level": 1000,
    "bidirectional": True,
    "isolation": True
}

# Get topology recommendation
recommended = manager.recommend_topology(requirements)
print(recommended)  # "DAB"
```

### Working with DAB Topology

```python
# Select DAB topology
dab = manager.select_topology("DAB")

# Define specifications
specs = {
    "input_voltage": 200,
    "output_voltage": 200,
    "power_level": 800,
    "modulation": "TPS"
}

# Optimize parameters
optimized = dab.optimize_parameters(specs)
print(optimized["modulation_strategy"])
print(optimized["current_stress"])

# Evaluate performance
performance = dab.evaluate_performance(specs)
print(performance["efficiency_estimate"])

# Run simulation
result = dab.run_simulation(specs)
print(result)
```

## Backward Compatibility

The DAB topology module maintains complete backward compatibility with existing PE-GPT functionality:

- All existing DAB functions continue to work unchanged
- Session state variables are properly managed
- PANN models and optimizers are preserved
- PLECS integration remains functional

## Error Handling

The system includes comprehensive error handling:

- `TopologyError` - Base exception for topology-related errors
- `UnsupportedTopologyError` - Raised for unsupported topologies
- `TopologyConfigurationError` - Raised for configuration/loading errors

## Extension Points

To add new topologies:

1. Create a new class inheriting from `TopologyModule`
2. Implement all abstract methods
3. Register with `TopologyManager.register_topology_module()`
4. Add to the available topologies list

## Integration with PE-GPT

The topology management system integrates seamlessly with the existing PE-GPT design workflow:

- Task-based design stages are preserved
- LLM agents can work with any topology
- GUI components remain compatible
- Optimization and simulation workflows are maintained

## Requirements Satisfied

This implementation satisfies the following requirements:

- **1.1**: AI agent automatic topology judgment and flow initiation
- **1.2**: Topology selection and switching functionality  
- **1.3**: Topology characteristics and application range explanation
- **4.1-4.4**: Complete backward compatibility with existing DAB functionality

## Future Development

The system is designed to support future topology additions:
- Buck Converter (LLM-based design support)
- PFC Converter (PANN development system)
- Additional converter topologies as needed