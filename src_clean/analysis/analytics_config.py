"""
Analytics Configuration Registry
Auto-generated configuration for available analytics methods and interpretability.

This module provides a registry of all available analytics methods and their
metadata for backend systems to dynamically discover analytical capabilities.
"""

from typing import Dict, Any, List, Set
from pathlib import Path
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AnalyticsConfigRegistry:
    """
    Registry system for analytics configuration and interpretability.
    
    Provides dynamic discovery of available analytics methods, segment fields,
    and metadata interpretation for backend systems.
    """
    
    def __init__(self):
        self.logger = logger
        self._config = None
        self._last_generated = None
    
    def generate_config(self) -> Dict[str, Any]:
        """
        Generate complete analytics configuration from current system state.
        
        Returns:
            Complete configuration dictionary
        """
        config = {
            'generated_timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'segment_base_fields': self._get_segment_base_fields(),
            'segment_cumulative_fields': self._get_segment_cumulative_fields(),
            'analysis_result_schemas': self._get_analysis_result_schemas(),
            'available_techniques': self._get_available_techniques(),
            'analytics_methods': self._get_analytics_methods(),
            'group_analytics_methods': self._get_group_analytics_methods()
        }
        
        self._config = config
        self._last_generated = datetime.now()
        return config
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration, generating if needed."""
        if self._config is None:
            return self.generate_config()
        return self._config
    
    def _get_segment_base_fields(self) -> Dict[str, Dict[str, str]]:
        """Define all base segment fields with metadata."""
        return {
            # Core timing and identification
            'segment_id': {'type': 'int', 'unit': '', 'source': 'database', 'description': 'Unique segment identifier'},
            'file_id': {'type': 'str', 'unit': '', 'source': 'database', 'description': 'Associated file identifier'},
            'segment_index': {'type': 'int', 'unit': '', 'source': 'database', 'description': 'Index within file'},
            'technique_id': {'type': 'int', 'unit': '', 'source': 'database', 'description': 'Technique identifier'},
            'fundamental_technique': {'type': 'str', 'unit': '', 'source': 'database', 'description': 'Base technique category'},
            
            # Temporal boundaries
            'start_row': {'type': 'int', 'unit': '', 'source': 'database', 'description': 'Starting row in raw data'},
            'end_row': {'type': 'int', 'unit': '', 'source': 'database', 'description': 'Ending row in raw data'},
            'start_time_s': {'type': 'float', 'unit': 's', 'source': 'database', 'description': 'Segment start time'},
            'end_time_s': {'type': 'float', 'unit': 's', 'source': 'database', 'description': 'Segment end time'},
            'duration_s': {'type': 'float', 'unit': 's', 'source': 'core_metrics', 'description': 'Segment duration'},
            
            # Electrochemical measurements
            'start_potential_v': {'type': 'float', 'unit': 'V', 'source': 'core_metrics', 'description': 'Initial voltage'},
            'end_potential_v': {'type': 'float', 'unit': 'V', 'source': 'core_metrics', 'description': 'Final voltage'},
            'start_current_a': {'type': 'float', 'unit': 'A', 'source': 'core_metrics', 'description': 'Initial current'},
            'end_current_a': {'type': 'float', 'unit': 'A', 'source': 'core_metrics', 'description': 'Final current'},
            'capacity_ah': {'type': 'float', 'unit': 'Ah', 'source': 'core_metrics', 'description': 'Segment capacity (signed)'},
            'energy_wh': {'type': 'float', 'unit': 'Wh', 'source': 'core_metrics', 'description': 'Segment energy (signed)'},
            'point_count': {'type': 'int', 'unit': '', 'source': 'core_metrics', 'description': 'Number of data points'},
            
            # Analysis metadata
            'analysis_status': {'type': 'str', 'unit': '', 'source': 'database', 'description': 'Analysis completion status'},
            'analysis_results': {'type': 'json', 'unit': '', 'source': 'technique_analyzer', 'description': 'Detailed analysis results'},
            'created_at': {'type': 'datetime', 'unit': '', 'source': 'database', 'description': 'Creation timestamp'}
        }
    
    def _get_segment_cumulative_fields(self) -> Dict[str, Dict[str, str]]:
        """Define cumulative fields that require cross-file calculation."""
        return {
            'cumulative_capacity_ah': {'type': 'float', 'unit': 'Ah', 'source': 'group_analytics', 'description': 'Total capacity from cell start'},
            'cumulative_energy_wh': {'type': 'float', 'unit': 'Wh', 'source': 'group_analytics', 'description': 'Total energy from cell start'},
            'cumulative_time_s': {'type': 'float', 'unit': 's', 'source': 'group_analytics', 'description': 'Absolute time from first measurement'},
            'cumulative_duration_s': {'type': 'float', 'unit': 's', 'source': 'group_analytics', 'description': 'Total experiment duration'},
            'cumulative_abs_capacity_ah': {'type': 'float', 'unit': 'Ah', 'source': 'group_analytics', 'description': 'Total capacity throughput'},
            'cumulative_cycle_count': {'type': 'int', 'unit': '', 'source': 'group_analytics', 'description': 'Cumulative cycle number'}
        }
    
    def _get_analysis_result_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Define schemas for analysis_results JSON field contents."""
        return {
            'exponential_fit': {
                'description': 'Exponential decay fitting results: y = y∞ + A·exp(-t/τ)',
                'fields': {
                    'voltage_infinity': {'type': 'float', 'unit': 'V', 'description': 'Equilibrium voltage'},
                    'voltage_amplitude': {'type': 'float', 'unit': 'V', 'description': 'Voltage decay amplitude'},
                    'current_infinity': {'type': 'float', 'unit': 'A', 'description': 'Equilibrium current'},
                    'current_amplitude': {'type': 'float', 'unit': 'A', 'description': 'Current decay amplitude'},
                    'time_constant_s': {'type': 'float', 'unit': 's', 'description': 'Decay time constant'},
                    'r_squared': {'type': 'float', 'unit': '', 'description': 'Goodness of fit (R²)'},
                    'rmse': {'type': 'float', 'unit': 'varies', 'description': 'Root mean square error'}
                }
            },
            'sqrt_fit': {
                'description': 'Square root time fitting results: y = y∞ + A·√t',
                'fields': {
                    'voltage_infinity': {'type': 'float', 'unit': 'V', 'description': 'Equilibrium voltage'},
                    'voltage_sqrt_amplitude': {'type': 'float', 'unit': 'V/s^0.5', 'description': 'Voltage sqrt(t) amplitude'},
                    'current_infinity': {'type': 'float', 'unit': 'A', 'description': 'Equilibrium current'},
                    'current_sqrt_amplitude': {'type': 'float', 'unit': 'A/s^0.5', 'description': 'Current sqrt(t) amplitude'},
                    'r_squared': {'type': 'float', 'unit': '', 'description': 'Goodness of fit (R²)'},
                    'rmse': {'type': 'float', 'unit': 'varies', 'description': 'Root mean square error'}
                }
            },
            'current_pulse': {
                'description': 'Current pulse resistance analysis',
                'fields': {
                    'ir_immediate_ohm': {'type': 'float', 'unit': 'Ω', 'description': 'Immediate resistance'},
                    'ir_10s_ohm': {'type': 'float', 'unit': 'Ω', 'description': 'Resistance at 10 seconds'},
                    'ir_30s_ohm': {'type': 'float', 'unit': 'Ω', 'description': 'Resistance at 30 seconds'},
                    'baseline_voltage_v': {'type': 'float', 'unit': 'V', 'description': 'Baseline voltage'},
                    'average_current_a': {'type': 'float', 'unit': 'A', 'description': 'Average current'},
                    'pulse_duration_s': {'type': 'float', 'unit': 's', 'description': 'Pulse duration'}
                }
            },
            'general_stats': {
                'description': 'General statistical analysis for unspecialized techniques',
                'fields': {
                    'voltage_mean_v': {'type': 'float', 'unit': 'V', 'description': 'Mean voltage'},
                    'voltage_std_v': {'type': 'float', 'unit': 'V', 'description': 'Voltage standard deviation'},
                    'voltage_range_v': {'type': 'float', 'unit': 'V', 'description': 'Voltage range'},
                    'current_mean_a': {'type': 'float', 'unit': 'A', 'description': 'Mean current'},
                    'current_std_a': {'type': 'float', 'unit': 'A', 'description': 'Current standard deviation'},
                    'current_range_a': {'type': 'float', 'unit': 'A', 'description': 'Current range'}
                }
            }
        }
    
    def _get_available_techniques(self) -> List[str]:
        """List of fundamental techniques supported."""
        return ['Rest', 'Galvanostatic', 'Potentiostatic', 'EIS', 'Cyclic_Voltammetry']
    
    def _get_analytics_methods(self) -> Dict[str, Dict[str, Any]]:
        """Define available analytics methods for segments."""
        return {
            'core_metrics_calculation': {
                'description': 'Universal core metrics for all segments',
                'applies_to': 'all_techniques',
                'outputs': ['duration_s', 'start_potential_v', 'end_potential_v', 'start_current_a', 
                          'end_current_a', 'capacity_ah', 'energy_wh', 'point_count'],
                'module': 'src_clean.analysis.core_metrics'
            },
            'rest_phase_analysis': {
                'description': 'Exponential and sqrt(t) fitting for rest phases',
                'applies_to': ['Rest'],
                'outputs': ['analysis_results.exponential_fit', 'analysis_results.sqrt_fit', 'analysis_results.all_fit_coefficients'],
                'module': 'src_clean.analysis.technique_analyzer'
            },
            'current_pulse_analysis': {
                'description': 'Resistance calculations for current pulses',
                'applies_to': ['Galvanostatic', 'Potentiostatic'],
                'outputs': ['analysis_results.current_pulse'],
                'module': 'src_clean.analysis.technique_analyzer'
            },
            'general_technique_analysis': {
                'description': 'Statistical analysis for non-specialized techniques',
                'applies_to': ['EIS', 'Cyclic_Voltammetry'],
                'outputs': ['analysis_results.general_stats'],
                'module': 'src_clean.analysis.technique_analyzer'
            }
        }
    
    def _get_group_analytics_methods(self) -> Dict[str, Dict[str, Any]]:
        """Define available group-level analytics methods."""
        return {
            'group_base_statistics': {
                'description': 'Statistical aggregation of segment base fields across group',
                'inputs': ['group_ids'],
                'outputs': ['mean', 'std', 'min', 'max', 'count'],
                'metrics': ['duration_s', 'start_potential_v', 'end_potential_v', 'start_current_a', 
                          'end_current_a', 'capacity_ah', 'energy_wh', 'point_count'],
                'module': 'src_clean.backend.api'
            },
            'group_temporal_analytics': {
                'description': 'Time-series analysis for group with cumulative calculations',
                'inputs': ['group_ids'],
                'outputs': ['time_series_data', 'cumulative_values'],
                'requires_raw_data': True,
                'module': 'src_clean.backend.api'
            },
            'group_fit_quality_statistics': {
                'description': 'R² and fitting quality statistics across group techniques',
                'inputs': ['group_ids'],
                'outputs': ['r_squared_distribution', 'fit_success_rates'],
                'depends_on': ['analysis_results.exponential_fit.r_squared', 'analysis_results.sqrt_fit.r_squared'],
                'module': 'src_clean.backend.api'
            },
            'group_voltage_correlation': {
                'description': 'Correlation analysis between metrics and start/end voltages',
                'inputs': ['group_ids'],
                'outputs': ['correlation_matrices', 'voltage_dependencies'],
                'module': 'src_clean.backend.api'
            }
        }
    
    def get_cumulative_field_names(self) -> Set[str]:
        """Get set of all field names containing 'cumulative'."""
        cumulative_fields = set(self._get_segment_cumulative_fields().keys())
        
        # Also check for any base fields that might have cumulative in the name
        base_fields = self._get_segment_base_fields()
        for field_name in base_fields.keys():
            if 'cumulative' in field_name.lower():
                cumulative_fields.add(field_name)
        
        return cumulative_fields
    
    def save_config_file(self, config_path: Path = None) -> Path:
        """
        Save configuration to Python file for import.
        
        Args:
            config_path: Path for config file, defaults to auto-generated location
            
        Returns:
            Path to saved config file
        """
        if config_path is None:
            config_path = Path(__file__).parent / 'auto_generated_config.py'
        
        config = self.get_config()
        
        # Generate Python file content
        content = f'''"""
Auto-generated Analytics Configuration
Generated: {config['generated_timestamp']}
Version: {config['version']}

This file is automatically generated by AnalyticsConfigRegistry.
Do not edit manually - regenerate using AnalyticsConfigRegistry.save_config_file()
"""

# Configuration data
ANALYTICS_CONFIG = {json.dumps(config, indent=2)}

# Helper functions
def get_segment_fields():
    """Get all available segment fields with metadata."""
    config = ANALYTICS_CONFIG
    return {{**config['segment_base_fields'], **config['segment_cumulative_fields']}}

def get_cumulative_fields():
    """Get only cumulative fields."""
    return ANALYTICS_CONFIG['segment_cumulative_fields']

def get_analysis_schemas():
    """Get analysis_results JSON schemas."""
    return ANALYTICS_CONFIG['analysis_result_schemas']

def get_available_methods():
    """Get available analytics methods."""
    return ANALYTICS_CONFIG['analytics_methods']

def get_group_methods():
    """Get group-level analytics methods."""
    return ANALYTICS_CONFIG['group_analytics_methods']
'''
        
        # Write to file
        config_path.write_text(content)
        self.logger.info(f"Analytics configuration saved to: {config_path}")
        
        return config_path


# Global instance
_registry = AnalyticsConfigRegistry()

def get_analytics_registry() -> AnalyticsConfigRegistry:
    """Get global analytics configuration registry."""
    return _registry

def generate_config() -> Dict[str, Any]:
    """Generate analytics configuration."""
    return _registry.generate_config()

def get_config() -> Dict[str, Any]:
    """Get current analytics configuration."""
    return _registry.get_config()