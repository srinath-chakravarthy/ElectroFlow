"""
Universal Schema Configuration

Defines the 29-column universal schema with explicit units for instrument-agnostic 
electrochemical data processing. This schema serves as the single source of truth
for column types, units, and descriptions across all parsers.

Key Features:
- Explicit units for each column (eliminates ambiguity)
- Type definitions for Polars DataFrame validation  
- Integration-safe (physics calculations read units from schema)
- Self-documenting with detailed descriptions
"""

import polars as pl
from typing import Dict, Any

# =============================================================================
# UNIVERSAL SCHEMA - Single source of truth with units
# =============================================================================

UNIVERSAL_SCHEMA = {
    # Core Time & Indexing (6 columns)
    'time_s': {
        'type': pl.Float64,
        'units': 's',
        'description': 'Relative time from experiment start'
    },
    'timestamp': {
        'type': pl.Datetime,
        'units': 'ISO8601',
        'description': 'Absolute timestamp (ISO format)'
    },
    'segment_number': {
        'type': pl.Int64,
        'units': 'dimensionless',
        'description': 'Experimental segment index'
    },
    'point_number': {
        'type': pl.Int64,
        'units': 'dimensionless',
        'description': 'Point within segment'
    },
    'loop_number': {
        'type': pl.Int64,
        'units': 'dimensionless',
        'description': 'Loop iteration'
    },
    'battery_cycle': {
        'type': pl.Int64,
        'units': 'dimensionless',
        'description': 'Battery cycle number'
    },
    
    # Electrochemical Core (6 columns)
    'potential_v': {
        'type': pl.Float64,
        'units': 'V',
        'description': 'Working electrode potential'
    },
    'current_a': {
        'type': pl.Float64,
        'units': 'A',
        'description': 'Current'
    },
    'potential_applied_v': {
        'type': pl.Float64,
        'units': 'V',
        'description': 'Applied potential'
    },
    'current_applied_a': {
        'type': pl.Float64,
        'units': 'A',
        'description': 'Applied current'
    },
    'potential_avg_v': {
        'type': pl.Float64,
        'units': 'V',
        'description': 'Average potential'
    },
    'current_avg_a': {
        'type': pl.Float64,
        'units': 'A',
        'description': 'Average current'
    },
    
    # Battery Analytics (4 columns)
    'capacity_ah': {
        'type': pl.Float64,
        'units': 'Ah',
        'description': 'Segment capacity integration'
    },
    'energy_wh': {
        'type': pl.Float64,
        'units': 'Wh',
        'description': 'Segment energy integration'
    },
    'power_w': {
        'type': pl.Float64,
        'units': 'W',
        'description': 'Instantaneous power'
    },
    'temperature_c': {
        'type': pl.Float64,
        'units': 'degC',
        'description': 'Temperature'
    },
    
    # Experimental Context - Cumulative Tracking (8 columns)
    'capacity_cumulative_ah': {
        'type': pl.Float64,
        'units': 'Ah',
        'description': 'File-level cumulative capacity'
    },
    'energy_cumulative_wh': {
        'type': pl.Float64,
        'units': 'Wh',
        'description': 'File-level cumulative energy'
    },
    'charge_cumulative_ah': {
        'type': pl.Float64,
        'units': 'Ah',
        'description': 'Positive capacity cumulative'
    },
    'discharge_cumulative_ah': {
        'type': pl.Float64,
        'units': 'Ah',
        'description': 'Negative capacity cumulative'
    },
    'energy_charge_cumulative_wh': {
        'type': pl.Float64,
        'units': 'Wh',
        'description': 'Positive energy cumulative'
    },
    'energy_discharge_cumulative_wh': {
        'type': pl.Float64,
        'units': 'Wh',
        'description': 'Negative energy cumulative'
    },
    'capacity_absolute_cumulative_ah': {
        'type': pl.Float64,
        'units': 'Ah',
        'description': 'Absolute capacity cumulative activity'
    },
    'energy_absolute_cumulative_wh': {
        'type': pl.Float64,
        'units': 'Wh',
        'description': 'Absolute energy cumulative activity'
    },
    
    # EIS (5 columns)
    'frequency_hz': {
        'type': pl.Float64,
        'units': 'Hz',
        'description': 'Frequency'
    },
    'impedance_real_ohm': {
        'type': pl.Float64,
        'units': 'Ω',
        'description': 'Real impedance'
    },
    'impedance_imag_ohm': {
        'type': pl.Float64,
        'units': 'Ω',
        'description': 'Imaginary impedance'
    },
    'impedance_mag_ohm': {
        'type': pl.Float64,
        'units': 'Ω',
        'description': 'Magnitude impedance'
    },
    'impedance_phase_deg': {
        'type': pl.Float64,
        'units': 'deg',
        'description': 'Phase'
    },
    
    # Status & Advanced (8 columns)
    'current_range': {
        'type': pl.Utf8,
        'units': 'categorical',
        'description': 'Current range setting'
    },
    'potential_range': {
        'type': pl.Utf8,
        'units': 'categorical',
        'description': 'Potential range setting'
    },
    'mode': {
        'type': pl.Utf8,
        'units': 'categorical',
        'description': 'Measurement mode'
    },
    'technique_id': {
        'type': pl.Int64,
        'units': 'dimensionless',
        'description': 'ActionID/Technique identifier'
    },
    'status_flags': {
        'type': pl.Utf8,
        'units': 'categorical',
        'description': 'Status flags'
    },
    'ce_potential_v': {
        'type': pl.Float64,
        'units': 'V',
        'description': 'Counter electrode potential'
    },
    'cell_potential_v': {
        'type': pl.Float64,
        'units': 'V',
        'description': 'Cell potential'
    },
    'ac_amplitude_v': {
        'type': pl.Float64,
        'units': 'V',
        'description': 'AC amplitude'
    },
    'aux_voltage_v': {
        'type': pl.Float64,
        'units': 'V',
        'description': 'Auxiliary voltage'
    }
}

# Schema metadata
SCHEMA_VERSION = "2.0.0"
TOTAL_COLUMNS = len(UNIVERSAL_SCHEMA)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_polars_schema() -> Dict[str, pl.DataType]:
    """Extract just the Polars schema for DataFrame validation."""
    return {col: config['type'] for col, config in UNIVERSAL_SCHEMA.items()}

def get_column_units(column_name: str) -> str:
    """Get units for a specific column."""
    if column_name not in UNIVERSAL_SCHEMA:
        raise ValueError(f"Column '{column_name}' not found in universal schema")
    return UNIVERSAL_SCHEMA[column_name]['units']

def get_columns_by_units(units: str) -> list:
    """Get all columns that use specific units."""
    return [col for col, config in UNIVERSAL_SCHEMA.items() if config['units'] == units]

def validate_column_exists(column_name: str) -> bool:
    """Check if column exists in universal schema."""
    return column_name in UNIVERSAL_SCHEMA

# Schema summary for debugging
def get_schema_summary() -> Dict[str, Any]:
    """Get summary information about the schema."""
    units_count = {}
    for col, config in UNIVERSAL_SCHEMA.items():
        unit = config['units']
        units_count[unit] = units_count.get(unit, 0) + 1
    
    return {
        'version': SCHEMA_VERSION,
        'total_columns': TOTAL_COLUMNS,
        'units_distribution': units_count,
        'column_names': list(UNIVERSAL_SCHEMA.keys())
    }