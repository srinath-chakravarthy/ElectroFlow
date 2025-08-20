"""
Core Metrics Calculator - Universal Analytics

Computes core metrics that apply to all electrochemical techniques:
- Capacity (Ah) from current integration
- Energy (Wh) from voltage-current integration  
- Duration and start/end values
"""

import numpy as np
import polars as pl
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CoreMetricsCalculator:
    """
    Calculate universal core metrics for any electrochemical technique segment.
    
    These metrics are technique-agnostic and computed for every segment.
    """
    
    def __init__(self):
        self.logger = logger
    
    def calculate_core_metrics(self, data: pl.DataFrame, 
                             start_row: int, end_row: int) -> Dict[str, Any]:
        """
        Calculate core metrics for a segment.
        
        Args:
            data: Full DataFrame with universal schema
            start_row: Starting row index (inclusive)
            end_row: Ending row index (exclusive)
            
        Returns:
            Dictionary with core metrics and segment boundary values
        """
        try:
            # Extract segment data
            segment_data = data.slice(start_row, end_row - start_row)
            
            if segment_data.height == 0:
                return self._empty_metrics()
            
            # Time values
            time_values = segment_data.get_column('time_s').to_numpy()
            start_time = float(time_values[0])
            end_time = float(time_values[-1])
            duration = end_time - start_time
            
            # Voltage values  
            voltage_values = segment_data.get_column('potential_v').to_numpy()
            start_voltage = float(voltage_values[0]) if not np.isnan(voltage_values[0]) else None
            end_voltage = float(voltage_values[-1]) if not np.isnan(voltage_values[-1]) else None
            
            # Current values
            current_values = segment_data.get_column('current_a').to_numpy()
            start_current = float(current_values[0]) if not np.isnan(current_values[0]) else None
            end_current = float(current_values[-1]) if not np.isnan(current_values[-1]) else None
            
            # Core metric calculations
            capacity_ah = self._calculate_capacity(time_values, current_values)
            energy_wh = self._calculate_energy(time_values, voltage_values, current_values)
            
            return {
                # Segment boundaries
                'start_time_s': start_time,
                'end_time_s': end_time,
                'duration_s': duration,
                'start_potential_v': start_voltage,
                'end_potential_v': end_voltage,
                'start_current_a': start_current,
                'end_current_a': end_current,
                
                # Core metrics
                'capacity_ah': capacity_ah,
                'energy_wh': energy_wh,
                'point_count': segment_data.height
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating core metrics: {e}")
            return self._empty_metrics()
    
    def _calculate_capacity(self, time_values: np.ndarray, 
                          current_values: np.ndarray) -> Optional[float]:
        """
        Calculate capacity using trapezoidal integration: ∫I dt (Ah).
        
        Args:
            time_values: Time points in seconds
            current_values: Current values in amperes
            
        Returns:
            Capacity in amp-hours, or None if calculation fails
        """
        try:
            # Remove NaN values
            valid_mask = ~(np.isnan(time_values) | np.isnan(current_values))
            if not np.any(valid_mask):
                return None
                
            time_clean = time_values[valid_mask]
            current_clean = current_values[valid_mask]
            
            if len(time_clean) < 2:
                return None
            
            # Trapezoidal integration: ∫I dt
            capacity_as = np.trapz(current_clean, time_clean)  # Amp-seconds
            capacity_ah = capacity_as / 3600.0  # Convert to Ah
            
            return float(capacity_ah)
            
        except Exception as e:
            self.logger.debug(f"Capacity calculation failed: {e}")
            return None
    
    def _calculate_energy(self, time_values: np.ndarray, 
                        voltage_values: np.ndarray,
                        current_values: np.ndarray) -> Optional[float]:
        """
        Calculate energy using trapezoidal integration: ∫VI dt (Wh).
        
        Args:
            time_values: Time points in seconds
            voltage_values: Voltage values in volts
            current_values: Current values in amperes
            
        Returns:
            Energy in watt-hours, or None if calculation fails
        """
        try:
            # Calculate instantaneous power
            power_values = voltage_values * current_values
            
            # Remove NaN values
            valid_mask = ~(np.isnan(time_values) | np.isnan(power_values))
            if not np.any(valid_mask):
                return None
                
            time_clean = time_values[valid_mask]
            power_clean = power_values[valid_mask]
            
            if len(time_clean) < 2:
                return None
            
            # Trapezoidal integration: ∫P dt
            energy_ws = np.trapz(power_clean, time_clean)  # Watt-seconds
            energy_wh = energy_ws / 3600.0  # Convert to Wh
            
            return float(energy_wh)
            
        except Exception as e:
            self.logger.debug(f"Energy calculation failed: {e}")
            return None
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure for failed calculations."""
        return {
            'start_time_s': None,
            'end_time_s': None, 
            'duration_s': None,
            'start_potential_v': None,
            'end_potential_v': None,
            'start_current_a': None,
            'end_current_a': None,
            'capacity_ah': None,
            'energy_wh': None,
            'point_count': 0
        }