"""
VersaStudio Configuration

VersaStudio-specific schema definitions and column mappings for Princeton Applied Research
electrochemical instruments. Contains CSV schema validation and column mapping to universal schema.

Key Features:
- Enhanced column mapping with explicit units
- CSV schema for .par.csv file validation
- Units-aware mapping for automatic conversion
- Support for alternative column names across VersaStudio versions
"""

import polars as pl

# =============================================================================
# VERSASTUDIO CSV SCHEMA - For .par.csv file validation
# =============================================================================

VERSASTUDIO_CSV_SCHEMA = {
    'Potential (V)': pl.Float64,
    'Current (A)': pl.Float64,
    'Elapsed Time (s)': pl.Float64,
    'Charge (C)': pl.Float64,
    'Applied Potential (V)': pl.Float64,
    'Frequency (Hz)': pl.Float64,
    '|Z| (ohms)': pl.Float64,
    'Zre (ohms)': pl.Float64,
    'Zim (ohms)': pl.Float64,
    'Phase of Z (deg)': pl.Float64,
    'Segment': pl.Int64,
    'Point': pl.Int64,
    'ActionId': pl.Int64,
    # Alternative column names that might exist
    'Segment #': pl.Int64,
    'Point #': pl.Int64,
    'Frequency(Hz)': pl.Float64,
    'Current Range': pl.Utf8,
    'Status': pl.Utf8,
    'AC Amplitude': pl.Float64,
    'ADC Sync Input(V)': pl.Float64
}

# =============================================================================
# VERSASTUDIO COLUMN MAPPING - Enhanced with units
# =============================================================================

VERSASTUDIO_CSV_MAPPING = {
    # Direct mappings with units
    'Potential (V)': {
        'universal': 'potential_v',
        'units': 'V'
    },
    'Current (A)': {
        'universal': 'current_a',
        'units': 'A'
    },
    'Elapsed Time (s)': {
        'universal': 'time_s',
        'units': 's'
    },
    'Applied Potential (V)': {
        'universal': 'potential_applied_v',
        'units': 'V'
    },
    'ActionId': {
        'universal': 'technique_id',
        'units': 'dimensionless'
    },
    'Segment': {
        'universal': 'segment_number',
        'units': 'dimensionless'
    },
    'Segment #': {  # Alternative column name
        'universal': 'segment_number',
        'units': 'dimensionless'
    },
    'Point': {
        'universal': 'point_number',
        'units': 'dimensionless'
    },
    'Point #': {  # Alternative column name
        'universal': 'point_number',
        'units': 'dimensionless'
    },
    'Frequency (Hz)': {
        'universal': 'frequency_hz',
        'units': 'Hz'
    },
    'Frequency(Hz)': {  # Alternative column name
        'universal': 'frequency_hz',
        'units': 'Hz'
    },
    'Zre (ohms)': {
        'universal': 'impedance_real_ohm',
        'units': 'Ω'
    },
    'Zim (ohms)': {
        'universal': 'impedance_imag_ohm',
        'units': 'Ω'
    },
    '|Z| (ohms)': {
        'universal': 'impedance_mag_ohm',
        'units': 'Ω'
    },
    'Phase of Z (deg)': {
        'universal': 'impedance_phase_deg',
        'units': 'deg'
    },
    'Current Range': {
        'universal': 'current_range',
        'units': 'categorical'
    },
    'Status': {
        'universal': 'status_flags',
        'units': 'categorical'
    },
    'AC Amplitude': {
        'universal': 'ac_amplitude_v',
        'units': 'V'
    },
    'ADC Sync Input(V)': {
        'universal': 'aux_voltage_v',
        'units': 'V'
    }
}

# =============================================================================
# VERSASTUDIO METADATA
# =============================================================================

VERSASTUDIO_INFO = {
    'manufacturer': 'Princeton Applied Research',
    'file_extensions': ['.par', '.par.csv'],
    'file_type': 'dual',
    'description': 'VersaStudio potentiostat data files'
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_mapping_summary():
    """Get summary of VersaStudio mapping configuration."""
    units_count = {}
    for vs_col, config in VERSASTUDIO_CSV_MAPPING.items():
        if isinstance(config, dict) and 'units' in config:
            unit = config['units']
            units_count[unit] = units_count.get(unit, 0) + 1
    
    return {
        'total_mappings': len(VERSASTUDIO_CSV_MAPPING),
        'units_distribution': units_count,
        'mapped_universal_columns': list(set(
            config['universal'] for config in VERSASTUDIO_CSV_MAPPING.values() 
            if isinstance(config, dict) and 'universal' in config
        ))
    }