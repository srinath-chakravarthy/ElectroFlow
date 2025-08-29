"""
Universal Schema Processor - Electrochemical Analysis Suite

Physics-based calculations for universal schema data.
Optimized O(n) operations using scipy.integrate.cumulative_trapezoid.

All instrument parsers share this processor for consistent calculations.
"""

import polars as pl
import numpy as np
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class UniversalProcessor:
    """
    Process universal schema data with optimized physics calculations.
    
    Handles power, impedance, capacity/energy integration, and cumulative tracking
    using efficient Polars operations and O(n) scipy integration.
    """
    
    def __init__(self):
        self.logger = logger
    
    def add_computed_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add computed columns (power, impedance) - basic math operations."""
        try:
            computed_exprs = []
            
            # Power calculation (P = V * I)
            if 'potential_v' in df.columns and 'current_a' in df.columns:
                computed_exprs.append(
                    (pl.col('potential_v') * pl.col('current_a')).alias('power_w')
                )
            
            # Impedance magnitude
            if 'impedance_real_ohm' in df.columns and 'impedance_imag_ohm' in df.columns:
                computed_exprs.append(
                    (pl.col('impedance_real_ohm').pow(2) + pl.col('impedance_imag_ohm').pow(2)).sqrt().alias('impedance_mag_ohm')
                )
                
                # Impedance phase (in degrees)
                computed_exprs.append(
                    (pl.arctan2(pl.col('impedance_imag_ohm'), pl.col('impedance_real_ohm')) * 180 / 3.14159265359).alias('impedance_phase_deg')
                )
            
            # Apply computations
            if computed_exprs:
                df = df.with_columns(computed_exprs)
            
            return df
            
        except Exception as e:
            self.logger.warning(f"Failed to add computed columns: {e}")
            return df
    
    def add_physics_integration(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add physics-based integration using optimized O(n) scipy operations."""
        
        # Check required columns
        if not all(col in df.columns for col in ['time_s', 'current_a', 'segment_number']):
            self.logger.warning("Missing required columns for physics integration")
            return df.with_columns([
                pl.lit(0.0).alias('capacity_ah'),
                pl.lit(0.0).alias('energy_wh')
            ])
        
        try:
            # Get unit conversion factors
            capacity_conversion, energy_conversion = self._get_conversion_factors()
            
            # Process segments with optimized integration
            df = self._integrate_segments_optimized(df, capacity_conversion, energy_conversion)
            
            # Add file-level cumulative tracking
            df = self._add_cumulative_tracking(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Physics integration failed: {e}")
            return df.with_columns([
                pl.lit(0.0).alias('capacity_ah'),
                pl.lit(0.0).alias('energy_wh')
            ])
    
    def _get_conversion_factors(self) -> tuple[float, float]:
        """Get unit conversion factors for capacity and energy."""
        try:
            from ..parsers.configs.universal_schema import get_column_units
            import pint
            ureg = pint.UnitRegistry()
            
            # Get units from schema
            current_units = get_column_units('current_a')
            time_units = get_column_units('time_s')
            capacity_units = get_column_units('capacity_ah')
            power_units = get_column_units('power_w')
            energy_units = get_column_units('energy_wh')
            
            # Calculate conversions
            capacity_conversion = ureg(f"{current_units}*{time_units}").to(capacity_units).magnitude
            energy_conversion = ureg(f"{power_units}*{time_units}").to(energy_units).magnitude
            
            return capacity_conversion, energy_conversion
            
        except (ImportError, ValueError) as e:
            self.logger.warning(f"Using default unit conversions: {e}")
            return 1/3600.0, 1/3600.0  # A*s → Ah, W*s → Wh
    
    def _integrate_segments_optimized(self, df: pl.DataFrame, capacity_conversion: float, energy_conversion: float) -> pl.DataFrame:
        """Optimized O(n) integration using scipy.integrate.cumulative_trapezoid."""
        
        def integrate_segment_capacity_optimized(segment_df):
            """O(n) capacity integration using cumulative_trapezoid."""
            # Sort by time for integration
            segment_df = segment_df.sort('time_s')
            
            # Extract numpy arrays for scipy
            time_vals = segment_df['time_s'].to_numpy()
            current_vals = segment_df['current_a'].to_numpy()
            
            if len(time_vals) < 2:
                return segment_df.with_columns([pl.lit(0.0).alias('capacity_ah')])
            
            # O(n) cumulative integration
            try:
                from scipy.integrate import cumulative_trapezoid
                cumulative_capacity = cumulative_trapezoid(
                    current_vals, time_vals, initial=0.0
                ) * capacity_conversion
            except ImportError:
                # Fallback to deprecated trapz if cumulative_trapezoid unavailable
                from scipy.integrate import trapz
                cumulative_capacity = np.zeros_like(time_vals)
                for i in range(1, len(time_vals)):
                    cumulative_capacity[i] = trapz(current_vals[:i+1], time_vals[:i+1]) * capacity_conversion
            
            # Add capacity column back to Polars DataFrame
            return segment_df.with_columns([
                pl.lit(cumulative_capacity).alias('capacity_ah')
            ])
        
        def integrate_segment_energy_optimized(segment_df):
            """O(n) energy integration using cumulative_trapezoid."""
            if 'power_w' not in segment_df.columns:
                return segment_df.with_columns([pl.lit(0.0).alias('energy_wh')])
            
            # Sort by time for integration  
            segment_df = segment_df.sort('time_s')
            
            # Extract numpy arrays for scipy
            time_vals = segment_df['time_s'].to_numpy()
            power_vals = segment_df['power_w'].to_numpy()
            
            if len(time_vals) < 2:
                return segment_df.with_columns([pl.lit(0.0).alias('energy_wh')])
            
            # O(n) cumulative integration
            try:
                from scipy.integrate import cumulative_trapezoid
                cumulative_energy = cumulative_trapezoid(
                    power_vals, time_vals, initial=0.0
                ) * energy_conversion
            except ImportError:
                # Fallback to deprecated trapz
                from scipy.integrate import trapz
                cumulative_energy = np.zeros_like(time_vals)
                for i in range(1, len(time_vals)):
                    cumulative_energy[i] = trapz(power_vals[:i+1], time_vals[:i+1]) * energy_conversion
            
            # Add energy column back to Polars DataFrame
            return segment_df.with_columns([
                pl.lit(cumulative_energy).alias('energy_wh')
            ])
        
        # Apply optimized integration per segment
        df = df.group_by('segment_number', maintain_order=True).map_groups(integrate_segment_capacity_optimized)
        
        if 'power_w' in df.columns:
            df = df.group_by('segment_number', maintain_order=True).map_groups(integrate_segment_energy_optimized)
        else:
            df = df.with_columns([pl.lit(0.0).alias('energy_wh')])
        
        return df
    
    def _add_cumulative_tracking(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add file-level cumulative capacity and energy tracking."""
        
        # Get final values from each segment for cumulative tracking
        segment_totals = df.group_by('segment_number').agg([
            pl.col('capacity_ah').sort_by('time_s').last().alias('segment_capacity_final'),
            pl.col('energy_wh').sort_by('time_s').last().alias('segment_energy_final')
        ]).sort('segment_number')
        
        # Calculate cumulative values across segments
        segment_totals = segment_totals.with_columns([
            # Net cumulative
            pl.col('segment_capacity_final').cum_sum().alias('capacity_cumulative_segment'),
            pl.col('segment_energy_final').cum_sum().alias('energy_cumulative_segment'),
            
            # Charge cumulative (positive only)
            pl.col('segment_capacity_final').clip(lower_bound=0).cum_sum().alias('charge_cumulative_segment'),
            pl.col('segment_energy_final').clip(lower_bound=0).cum_sum().alias('energy_charge_cumulative_segment'),
            
            # Discharge cumulative (negative only)  
            pl.col('segment_capacity_final').clip(upper_bound=0).cum_sum().alias('discharge_cumulative_segment'),
            pl.col('segment_energy_final').clip(upper_bound=0).cum_sum().alias('energy_discharge_cumulative_segment'),
            
            # Absolute cumulative
            pl.col('segment_capacity_final').abs().cum_sum().alias('capacity_absolute_cumulative_segment'),
            pl.col('segment_energy_final').abs().cum_sum().alias('energy_absolute_cumulative_segment')
        ])
        
        # Join back to main dataframe
        df = df.join(segment_totals, on='segment_number', how='left')
        
        # Convert to point-level cumulative (interpolate within segments)
        df = df.with_columns([
            # File-level cumulative = previous segments + current segment progress
            (pl.col('capacity_cumulative_segment') - pl.col('segment_capacity_final') + pl.col('capacity_ah')).alias('capacity_cumulative_ah'),
            (pl.col('energy_cumulative_segment') - pl.col('segment_energy_final') + pl.col('energy_wh')).alias('energy_cumulative_wh'),
            
            # Charge/discharge tracking
            (pl.col('charge_cumulative_segment') + pl.col('capacity_ah').clip(lower_bound=0)).alias('charge_cumulative_ah'),
            (pl.col('discharge_cumulative_segment') + pl.col('capacity_ah').clip(upper_bound=0)).alias('discharge_cumulative_ah'),
            
            # Energy equivalents
            (pl.col('energy_charge_cumulative_segment') + pl.col('energy_wh').clip(lower_bound=0)).alias('energy_charge_cumulative_wh'),
            (pl.col('energy_discharge_cumulative_segment') + pl.col('energy_wh').clip(upper_bound=0)).alias('energy_discharge_cumulative_wh'),
            
            # Absolute tracking
            (pl.col('capacity_absolute_cumulative_segment') + pl.col('capacity_ah').abs()).alias('capacity_absolute_cumulative_ah'),
            (pl.col('energy_absolute_cumulative_segment') + pl.col('energy_wh').abs()).alias('energy_absolute_cumulative_wh')
        ])
        
        # Clean up temporary columns
        df = df.drop([col for col in df.columns if col.endswith('_segment')])
        
        return df
    
    def add_timestamps(self, df: pl.DataFrame, acquisition_start: datetime) -> pl.DataFrame:
        """Add absolute timestamps to universal schema data."""
        try:
            if 'time_s' in df.columns:
                # Create timestamps from acquisition start + elapsed time
                df = df.with_columns([
                    (pl.lit(acquisition_start) + pl.duration(seconds=pl.col('time_s'))).alias('timestamp')
                ])
            else:
                # No time data available, use acquisition start for all points
                df = df.with_columns([
                    pl.lit(acquisition_start).alias('timestamp')
                ])
            
            return df
            
        except Exception as e:
            self.logger.warning(f"Failed to add timestamps: {e}")
            # Add null timestamp column
            return df.with_columns([
                pl.lit(None).cast(pl.Datetime).alias('timestamp')
            ])