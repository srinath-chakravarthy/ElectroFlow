"""
Core Metrics Extractor - Simplified Database Storage

Extracts final segment metrics from parser-computed data for database storage.
All physics-based integration now happens at parser level.
"""

import polars as pl
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CoreMetricsCalculator:
    """
    Extract segment boundary values and final metrics for database storage.
    
    Physics-based integration is now done at parser level.
    This class only extracts final values and boundaries.
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
            segment_data = data.slice(start_row, end_row - start_row + 1)
            
            if segment_data.height == 0:
                return self._empty_metrics()
            
            # Extract boundary values from first and last rows
            first_row = segment_data.row(0, named=True)
            last_row = segment_data.row(-1, named=True)
            
            # Time boundaries
            start_time = float(first_row.get('time_s') or 0)
            end_time = float(last_row.get('time_s') or 0)
            duration = end_time - start_time
            
            # Voltage boundaries
            start_voltage = first_row.get('potential_v')
            end_voltage = last_row.get('potential_v')
            
            # Current boundaries
            start_current = first_row.get('current_a')
            end_current = last_row.get('current_a')
            
            # Electrode potential boundaries (BioLogic-specific)
            start_we_potential = first_row.get('working_electrode_potential_v')
            end_we_potential = last_row.get('working_electrode_potential_v')
            start_ce_potential = first_row.get('ce_potential_v')
            end_ce_potential = last_row.get('ce_potential_v')
            
            # Final integrated values (computed by parser)
            final_capacity = float(last_row.get('capacity_ah') or 0)
            final_energy = float(last_row.get('energy_wh') or 0)
            
            # Extract timestamp from first row
            start_timestamp = first_row.get('timestamp')
            start_timestamp_str = start_timestamp.isoformat() if start_timestamp else None
            
            # Extract final cumulative values (computed by parser)
            final_capacity_cumulative = float(last_row.get('capacity_cumulative_ah') or 0)
            final_energy_cumulative = float(last_row.get('energy_cumulative_wh') or 0)
            final_charge_cumulative = float(last_row.get('charge_cumulative_ah') or 0)
            final_discharge_cumulative = float(last_row.get('discharge_cumulative_ah') or 0)
            final_energy_charge_cumulative = float(last_row.get('energy_charge_cumulative_wh') or 0)
            final_energy_discharge_cumulative = float(last_row.get('energy_discharge_cumulative_wh') or 0)
            final_capacity_absolute_cumulative = float(last_row.get('capacity_absolute_cumulative_ah') or 0)
            final_energy_absolute_cumulative = float(last_row.get('energy_absolute_cumulative_wh') or 0)
            
            return {
                # Boundary values
                'start_time_s': start_time,
                'end_time_s': end_time,
                'duration_s': duration,
                'start_potential_v': start_voltage,
                'end_potential_v': end_voltage,
                'start_current_a': start_current,
                'end_current_a': end_current,
                'start_we_potential_v': start_we_potential,
                'end_we_potential_v': end_we_potential,
                'start_ce_potential_v': start_ce_potential,
                'end_ce_potential_v': end_ce_potential,
                
                # Final integrated values
                'capacity_ah': final_capacity,
                'energy_wh': final_energy,
                'point_count': segment_data.height,
                
                # Timestamp
                'start_timestamp': start_timestamp_str,
                
                # Final cumulative values
                'capacity_cumulative_ah': final_capacity_cumulative,
                'energy_cumulative_wh': final_energy_cumulative,
                'charge_cumulative_ah': final_charge_cumulative,
                'discharge_cumulative_ah': final_discharge_cumulative,
                'energy_charge_cumulative_wh': final_energy_charge_cumulative,
                'energy_discharge_cumulative_wh': final_energy_discharge_cumulative,
                'capacity_absolute_cumulative_ah': final_capacity_absolute_cumulative,
                'energy_absolute_cumulative_wh': final_energy_absolute_cumulative
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting core metrics: {e}")
            return self._empty_metrics()
    
    
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
            'start_we_potential_v': None,
            'end_we_potential_v': None,
            'start_ce_potential_v': None,
            'end_ce_potential_v': None,
            'capacity_ah': None,
            'energy_wh': None,
            'point_count': 0,
            'start_timestamp': None,
            'capacity_cumulative_ah': None,
            'energy_cumulative_wh': None,
            'charge_cumulative_ah': None,
            'discharge_cumulative_ah': None,
            'energy_charge_cumulative_wh': None,
            'energy_discharge_cumulative_wh': None,
            'capacity_absolute_cumulative_ah': None,
            'energy_absolute_cumulative_wh': None
        }