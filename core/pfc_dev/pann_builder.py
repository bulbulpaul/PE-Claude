"""
PANN Builder for PFC Converters

This module provides PANN (Physics-in-Architecture Neural Network) construction
capabilities for PFC converters using Amazon Bedrock Knowledge Base PDF technical
information integration.

@reference: PE-GPT: a New Paradigm for Power Electronics Design, by Fanfan Lin, Xinze Li, et al.
@code-author: Xinze Li, Fanfan Lin
@github: https://github.com/XinzeLee/PE-GPT
"""

import re
import json
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from core.llm.bedrock_kb_retriever import BedrockKnowledgeBaseRetriever
from core.knowledge.kb_config import KnowledgeBaseConfig

logger = logging.getLogger(__name__)


@dataclass
class PFCPhysicalParameters:
    """Physical parameters extracted from PDF technical information"""
    inductance: float  # H
    capacitance: float  # F
    resistance: float  # Ohm
    switching_frequency: float  # Hz
    input_voltage_rms: float  # V
    output_voltage: float  # V
    power_rating: float  # W
    control_mode: str  # CCM, DCM, BCM
    additional_params: Dict[str, float]


@dataclass
class PFCDifferentialEquation:
    """PFC circuit differential equation representation"""
    inductor_equation: str
    capacitor_equation: str
    power_balance_equation: str
    control_equation: str
    state_variables: List[str]
    input_variables: List[str]
    parameters: Dict[str, float]


class PANNBuilder:
    """
    PANN Builder for PFC converters using Bedrock Knowledge Base integration.
    
    This class constructs PANN models by:
    1. Retrieving PDF technical information from Bedrock Knowledge Base
    2. Extracting physical parameters automatically
    3. Building PFC circuit differential equations
    4. Creating PANN architecture based on physics
    """
    
    def __init__(self, config: Optional[KnowledgeBaseConfig] = None):
        """
        Initialize PANN Builder.
        
        Args:
            config: Knowledge Base configuration for PDF retrieval
        """
        self.config = config
        self.kb_retriever = None
        
        if config and config.is_bedrock_enabled():
            try:
                self.kb_retriever = BedrockKnowledgeBaseRetriever(config)
                logger.info("✅ Bedrock Knowledge Base retriever initialized for PANN Builder")
            except Exception as e:
                logger.error(f"Failed to initialize KB retriever: {e}")
                if not config.enable_fallback:
                    raise
        
        # PFC-specific parameter patterns for extraction
        self.parameter_patterns = {
            'inductance': [
                r'L\s*=\s*([0-9.]+)\s*([μu]?H)',
                r'inductor\s*[:\s]*([0-9.]+)\s*([μu]?H)',
                r'inductance\s*[:\s]*([0-9.]+)\s*([μu]?H)'
            ],
            'capacitance': [
                r'C\s*=\s*([0-9.]+)\s*([μu]?F)',
                r'capacitor\s*[:\s]*([0-9.]+)\s*([μu]?F)',
                r'capacitance\s*[:\s]*([0-9.]+)\s*([μu]?F)'
            ],
            'switching_frequency': [
                r'f[s_]?\s*=\s*([0-9.]+)\s*(kHz|MHz|Hz)',
                r'switching\s+frequency\s*[:\s]*([0-9.]+)\s*(kHz|MHz|Hz)',
                r'fsw\s*=\s*([0-9.]+)\s*(kHz|MHz|Hz)'
            ],
            'input_voltage': [
                r'V[i_]?n\s*=\s*([0-9.]+)\s*V',
                r'input\s+voltage\s*[:\s]*([0-9.]+)\s*V',
                r'Vin\s*=\s*([0-9.]+)\s*V'
            ],
            'output_voltage': [
                r'V[o_]?ut\s*=\s*([0-9.]+)\s*V',
                r'output\s+voltage\s*[:\s]*([0-9.]+)\s*V',
                r'Vout\s*=\s*([0-9.]+)\s*V'
            ],
            'power_rating': [
                r'P\s*=\s*([0-9.]+)\s*(W|kW)',
                r'power\s*[:\s]*([0-9.]+)\s*(W|kW)',
                r'rated\s+power\s*[:\s]*([0-9.]+)\s*(W|kW)'
            ]
        }
    
    def build_from_pdf_query(self, pdf_query: str) -> 'PFCPANNModel':
        """
        Build PFC PANN model from PDF technical information query.
        
        Args:
            pdf_query: Query to search for PFC technical information in PDFs
            
        Returns:
            PFCPANNModel: Constructed PANN model
        """
        logger.info(f"Building PFC PANN from PDF query: {pdf_query}")
        
        # Retrieve technical information from Bedrock Knowledge Base
        tech_info = self._retrieve_technical_info(pdf_query)
        
        # Extract physical parameters from technical information
        physical_params = self.extract_physical_parameters(tech_info)
        
        # Build differential equations based on extracted parameters
        diff_equations = self.build_differential_equations(physical_params)
        
        # Create PANN architecture
        pann_model = self.create_pann_architecture(diff_equations, physical_params)
        
        logger.info("✅ PFC PANN model construction completed")
        return pann_model
    
    def _retrieve_technical_info(self, query: str) -> str:
        """
        Retrieve technical information from Bedrock Knowledge Base.
        
        Args:
            query: Search query for PFC technical information
            
        Returns:
            str: Retrieved technical information text
        """
        if not self.kb_retriever:
            logger.warning("Knowledge Base retriever not available, using fallback")
            return self._get_fallback_tech_info()
        
        try:
            # Enhance query for PFC-specific information
            enhanced_query = f"PFC power factor correction {query} circuit parameters inductance capacitance switching frequency"
            
            nodes = self.kb_retriever.retrieve(enhanced_query)
            
            if not nodes:
                logger.warning("No technical information retrieved from Knowledge Base")
                return self._get_fallback_tech_info()
            
            # Combine retrieved information
            tech_info = ""
            for node_with_score in nodes:
                tech_info += node_with_score.node.text + "\n\n"
            
            logger.info(f"Retrieved {len(nodes)} documents from Knowledge Base")
            return tech_info
            
        except Exception as e:
            logger.error(f"Error retrieving technical information: {e}")
            if self.config and self.config.enable_fallback:
                return self._get_fallback_tech_info()
            raise
    
    def _get_fallback_tech_info(self) -> str:
        """
        Get fallback technical information when Knowledge Base is not available.
        
        Returns:
            str: Default PFC technical information
        """
        return """
        PFC (Power Factor Correction) Circuit Parameters:
        
        Typical boost PFC converter specifications:
        - Input voltage: 85-265V AC RMS
        - Output voltage: 400V DC
        - Switching frequency: 100 kHz
        - Inductance: 200 μH
        - Output capacitance: 470 μF
        - Power rating: 500W
        - Control mode: CCM (Continuous Conduction Mode)
        
        Circuit equations:
        - Inductor current: L * di_L/dt = v_in - v_out * D
        - Capacitor voltage: C * dv_c/dt = i_L * D - i_load
        - Power factor: PF = P_real / P_apparent
        - THD target: < 5%
        """
    
    def extract_physical_parameters(self, tech_info: str) -> PFCPhysicalParameters:
        """
        Extract physical parameters from technical information text.
        
        Args:
            tech_info: Technical information text from PDFs
            
        Returns:
            PFCPhysicalParameters: Extracted physical parameters
        """
        logger.info("Extracting physical parameters from technical information")
        
        extracted_params = {}
        
        # Extract parameters using regex patterns
        for param_name, patterns in self.parameter_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, tech_info, re.IGNORECASE)
                for match in matches:
                    try:
                        value = float(match.group(1))
                        unit = match.group(2) if len(match.groups()) > 1 else ""
                        
                        # Convert to base units
                        converted_value = self._convert_to_base_units(value, unit, param_name)
                        extracted_params[param_name] = converted_value
                        logger.debug(f"Extracted {param_name}: {value} {unit} -> {converted_value}")
                        break
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Failed to extract {param_name} from match: {e}")
                        continue
                
                if param_name in extracted_params:
                    break
        
        # Determine control mode
        control_mode = self._determine_control_mode(tech_info)
        
        # Use defaults for missing parameters
        defaults = self._get_default_parameters()
        for param, default_value in defaults.items():
            if param not in extracted_params:
                extracted_params[param] = default_value
                logger.info(f"Using default value for {param}: {default_value}")
        
        # Create PFCPhysicalParameters object
        physical_params = PFCPhysicalParameters(
            inductance=extracted_params.get('inductance', defaults['inductance']),
            capacitance=extracted_params.get('capacitance', defaults['capacitance']),
            resistance=extracted_params.get('resistance', defaults['resistance']),
            switching_frequency=extracted_params.get('switching_frequency', defaults['switching_frequency']),
            input_voltage_rms=extracted_params.get('input_voltage', defaults['input_voltage']),
            output_voltage=extracted_params.get('output_voltage', defaults['output_voltage']),
            power_rating=extracted_params.get('power_rating', defaults['power_rating']),
            control_mode=control_mode,
            additional_params={}
        )
        
        logger.info(f"✅ Physical parameters extracted: L={physical_params.inductance*1e6:.1f}μH, "
                   f"C={physical_params.capacitance*1e6:.1f}μF, f_sw={physical_params.switching_frequency/1000:.1f}kHz")
        
        return physical_params
    
    def _convert_to_base_units(self, value: float, unit: str, param_type: str) -> float:
        """
        Convert parameter values to base SI units.
        
        Args:
            value: Parameter value
            unit: Unit string
            param_type: Parameter type for context
            
        Returns:
            float: Value in base SI units
        """
        unit_lower = unit.lower()
        
        # Inductance conversions (to Henries)
        if param_type == 'inductance':
            if unit_lower in ['μh', 'uh']:
                return value * 1e-6
            elif unit_lower == 'mh':
                return value * 1e-3
            elif unit_lower == 'h':
                return value
        
        # Capacitance conversions (to Farads)
        elif param_type == 'capacitance':
            if unit_lower in ['μf', 'uf']:
                return value * 1e-6
            elif unit_lower == 'nf':
                return value * 1e-9
            elif unit_lower == 'pf':
                return value * 1e-12
            elif unit_lower == 'f':
                return value
        
        # Frequency conversions (to Hz)
        elif param_type == 'switching_frequency':
            if unit_lower == 'khz':
                return value * 1000
            elif unit_lower == 'mhz':
                return value * 1000000
            elif unit_lower == 'hz':
                return value
        
        # Power conversions (to Watts)
        elif param_type == 'power_rating':
            if unit_lower == 'kw':
                return value * 1000
            elif unit_lower == 'w':
                return value
        
        return value
    
    def _determine_control_mode(self, tech_info: str) -> str:
        """
        Determine PFC control mode from technical information.
        
        Args:
            tech_info: Technical information text
            
        Returns:
            str: Control mode (CCM, DCM, or BCM)
        """
        text_lower = tech_info.lower()
        
        if 'continuous conduction mode' in text_lower or 'ccm' in text_lower:
            return 'CCM'
        elif 'discontinuous conduction mode' in text_lower or 'dcm' in text_lower:
            return 'DCM'
        elif 'boundary conduction mode' in text_lower or 'bcm' in text_lower or 'critical conduction mode' in text_lower:
            return 'BCM'
        else:
            # Default to CCM for high power applications
            return 'CCM'
    
    def _get_default_parameters(self) -> Dict[str, float]:
        """
        Get default PFC parameters for fallback.
        
        Returns:
            Dict[str, float]: Default parameter values in SI units
        """
        return {
            'inductance': 200e-6,  # 200 μH
            'capacitance': 470e-6,  # 470 μF
            'resistance': 0.1,  # 0.1 Ohm (ESR)
            'switching_frequency': 100e3,  # 100 kHz
            'input_voltage': 230.0,  # 230V RMS
            'output_voltage': 400.0,  # 400V DC
            'power_rating': 500.0  # 500W
        }
    
    def build_differential_equations(self, params: PFCPhysicalParameters) -> PFCDifferentialEquation:
        """
        Build PFC circuit differential equations based on physical parameters.
        
        Args:
            params: Physical parameters of the PFC circuit
            
        Returns:
            PFCDifferentialEquation: Differential equation representation
        """
        logger.info(f"Building differential equations for {params.control_mode} PFC converter")
        
        # State variables: [i_L, v_C]
        state_variables = ['i_L', 'v_C']
        
        # Input variables: [v_in, D, i_load]
        input_variables = ['v_in', 'D', 'i_load']
        
        # Build equations based on control mode
        if params.control_mode == 'CCM':
            # Continuous Conduction Mode equations
            inductor_eq = f"L * di_L/dt = v_in - v_C * D"
            capacitor_eq = f"C * dv_C/dt = i_L * D - i_load"
        elif params.control_mode == 'DCM':
            # Discontinuous Conduction Mode equations (simplified)
            inductor_eq = f"L * di_L/dt = v_in - v_C * D * (i_L > 0)"
            capacitor_eq = f"C * dv_C/dt = i_L * D * (i_L > 0) - i_load"
        else:  # BCM
            # Boundary Conduction Mode equations
            inductor_eq = f"L * di_L/dt = v_in - v_C * D"
            capacitor_eq = f"C * dv_C/dt = i_L * D - i_load"
        
        # Power balance equation
        power_balance_eq = f"P_in = v_in * i_L * PF, P_out = v_C * i_load"
        
        # Control equation (duty cycle calculation)
        control_eq = f"D = f(v_in, v_C, i_ref)"
        
        # Parameter dictionary
        param_dict = {
            'L': params.inductance,
            'C': params.capacitance,
            'R': params.resistance,
            'f_sw': params.switching_frequency,
            'V_in_rms': params.input_voltage_rms,
            'V_out': params.output_voltage,
            'P_rated': params.power_rating
        }
        
        diff_equations = PFCDifferentialEquation(
            inductor_equation=inductor_eq,
            capacitor_equation=capacitor_eq,
            power_balance_equation=power_balance_eq,
            control_equation=control_eq,
            state_variables=state_variables,
            input_variables=input_variables,
            parameters=param_dict
        )
        
        logger.info("✅ Differential equations constructed")
        return diff_equations
    
    def create_pann_architecture(self, diff_eq: PFCDifferentialEquation, 
                                params: PFCPhysicalParameters) -> 'PFCPANNModel':
        """
        Create PANN architecture based on differential equations and parameters.
        
        Args:
            diff_eq: PFC differential equations
            params: Physical parameters
            
        Returns:
            PFCPANNModel: PANN model architecture
        """
        logger.info("Creating PANN architecture for PFC converter")
        
        # Define PANN architecture parameters
        architecture_config = {
            'input_size': len(diff_eq.input_variables),
            'state_size': len(diff_eq.state_variables),
            'hidden_size': 64,
            'num_layers': 3,
            'physics_constraints': {
                'inductance_range': (params.inductance * 0.5, params.inductance * 2.0),
                'capacitance_range': (params.capacitance * 0.5, params.capacitance * 2.0),
                'frequency_range': (params.switching_frequency * 0.8, params.switching_frequency * 1.2)
            },
            'control_mode': params.control_mode,
            'differential_equations': diff_eq
        }
        
        # Create PFC PANN model (placeholder - actual implementation would use PyTorch)
        pann_model = PFCPANNModel(architecture_config)
        
        logger.info(f"✅ PANN architecture created: {params.control_mode} mode, "
                   f"{architecture_config['input_size']} inputs, {architecture_config['state_size']} states")
        
        return pann_model


class PFCPANNModel:
    """
    PFC PANN Model representation.
    
    This is a placeholder class that would be implemented with actual
    PyTorch neural network components in a full implementation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PFC PANN model.
        
        Args:
            config: Architecture configuration dictionary
        """
        self.config = config
        self.is_trained = False
        self.training_history = []
        
        logger.info(f"PFC PANN model initialized with config: {config['control_mode']} mode")
    
    def get_architecture_info(self) -> Dict[str, Any]:
        """
        Get architecture information.
        
        Returns:
            Dict[str, Any]: Architecture information
        """
        return {
            'control_mode': self.config['control_mode'],
            'input_size': self.config['input_size'],
            'state_size': self.config['state_size'],
            'hidden_size': self.config['hidden_size'],
            'num_layers': self.config['num_layers'],
            'is_trained': self.is_trained
        }
    
    def predict_power_factor(self, inputs: np.ndarray) -> np.ndarray:
        """
        Predict power factor (placeholder implementation).
        
        Args:
            inputs: Input array
            
        Returns:
            np.ndarray: Predicted power factor values
        """
        # Placeholder implementation
        return np.random.uniform(0.95, 0.99, size=inputs.shape[0])
    
    def predict_thd(self, inputs: np.ndarray) -> np.ndarray:
        """
        Predict THD (placeholder implementation).
        
        Args:
            inputs: Input array
            
        Returns:
            np.ndarray: Predicted THD values
        """
        # Placeholder implementation
        return np.random.uniform(2.0, 5.0, size=inputs.shape[0])
    
    def predict_efficiency(self, inputs: np.ndarray) -> np.ndarray:
        """
        Predict efficiency (placeholder implementation).
        
        Args:
            inputs: Input array
            
        Returns:
            np.ndarray: Predicted efficiency values
        """
        # Placeholder implementation
        return np.random.uniform(0.92, 0.96, size=inputs.shape[0])