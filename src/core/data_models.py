"""
Core data models for battery data analyzer.
Fixed version with DataFile/DataFileGroup naming.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import polars as pl
import numpy as np
from enum import Enum
import hashlib
import json


# Universal 31-column schema for all instruments
UNIVERSAL_COLUMNS = [
    # Core Time & Indexing (6 columns)
    'time_s', 'timestamp', 'segment_number', 'point_number', 'loop_number', 'battery_cycle',
    
    # Electrochemical Core (6 columns)
    'potential_v', 'current_a', 'potential_applied_v', 'current_applied_a',
    'potential_avg_v', 'current_avg_a',
    
    # Battery Analytics (4 columns)
    'charge_capacity_ah', 'energy_wh', 'power_w', 'temperature_c',
    
    # EIS (5 columns)
    'frequency_hz', 'impedance_real_ohm', 'impedance_imag_ohm', 
    'impedance_mag_ohm', 'impedance_phase_deg',
    
    # Status & Advanced (8 columns)
    'current_range', 'potential_range', 'mode', 'technique_id', 'status_flags',
    'ce_potential_v', 'cell_potential_v', 'ac_amplitude_v', 'aux_voltage_v',
    
    # Technique Tracking (2 columns)
    'technique_name', 'fundamental_technique'
]

# Universal schema with explicit types
UNIVERSAL_SCHEMA = {
    # Core Time & Indexing
    'time_s': pl.Float64,
    'timestamp': pl.Datetime,
    'segment_number': pl.Int64,
    'point_number': pl.Int64,
    'loop_number': pl.Int64,
    'battery_cycle': pl.Int64,
    
    # Electrochemical Core
    'potential_v': pl.Float64,
    'current_a': pl.Float64,
    'potential_applied_v': pl.Float64,
    'current_applied_a': pl.Float64,
    'potential_avg_v': pl.Float64,
    'current_avg_a': pl.Float64,
    
    # Battery Analytics
    'charge_capacity_ah': pl.Float64,
    'energy_wh': pl.Float64,
    'power_w': pl.Float64,
    'temperature_c': pl.Float64,
    
    # EIS
    'frequency_hz': pl.Float64,
    'impedance_real_ohm': pl.Float64,
    'impedance_imag_ohm': pl.Float64,
    'impedance_mag_ohm': pl.Float64,
    'impedance_phase_deg': pl.Float64,
    
    # Status & Advanced
    'current_range': pl.Int64,
    'potential_range': pl.Int64,
    'mode': pl.Utf8,
    'technique_id': pl.Int64,
    'status_flags': pl.Int64,
    'ce_potential_v': pl.Float64,
    'cell_potential_v': pl.Float64,
    'ac_amplitude_v': pl.Float64,
    'aux_voltage_v': pl.Float64,
    
    # Technique Tracking
    'technique_name': pl.Utf8,
    'fundamental_technique': pl.Utf8
}

# VersaStudio → Universal column mapping
VERSASTUDIO_MAPPING = {
    # Time mappings
    'Elapsed Time(s)': 'time_s',
    'Segment #': 'segment_number',
    'Point #': 'point_number',
    
    # Direct electrochemical mappings
    'E(V)': 'potential_v',
    'I(A)': 'current_a',
    'E Applied(V)': 'potential_applied_v',
    'Frequency(Hz)': 'frequency_hz',
    'Z Real': 'impedance_real_ohm',
    'Z Imag': 'impedance_imag_ohm',
    
    # Status and advanced
    'Current Range': 'current_range',
    'Status': 'status_flags',
    'ActionId': 'technique_id',
    'AC Amplitude': 'ac_amplitude_v',
    'ADC Sync Input(V)': 'aux_voltage_v',
    
    # Computed columns will be added during processing
}

# Technique name mapping to fundamental techniques
TECHNIQUE_MAPPING = {
    'OCV': [
        'Rest', 'Energy Open Circuit', 'Impedance Open Circuit', 'OCV', 
        'Corrosion Open Circuit', 'Voltametry Open Circuit'
    ],
    'CC': [
        'Constant Current', 'CC', 'Voltametry ChronoPotentiometry', 
        'ChronoPotentiometry', 'Energy Constant Current', 'Corrosion Constant Current'
    ],
    'CV': [
        'Constant Voltage', 'CV', 'Voltametry ChronoAmperometry', 
        'ChronoAmperometry', 'Energy Constant Voltage', 'Corrosion Constant Voltage'
    ],
    'GEIS': [
        'Galvanostatic EIS', 'GEIS'
    ],
    'PEIS': [
        'Potentiostatic EIS', 'PEIS'
    ]
}

# Legacy VersaStudio schema for backward compatibility
VERSASTUDIO_COLUMNS = [
    'Segment #', 'Point #', 'E(V)', 'I(A)', 'Elapsed Time(s)',
    'ADC Sync Input(V)', 'Current Range', 'Status', 'E Applied(V)',
    'Frequency(Hz)', 'E Real', 'E Imag', 'I Real', 'I Imag',
    'Z Real', 'Z Imag', 'E2 Status', 'E2(V)', 'E2 Real', 'E2 Imag',
    'Z2 Real', 'Z2 Imag', 'ActionId', 'AC Amplitude'
]

VERSASTUDIO_SCHEMA = {
    'Segment #': pl.Int64,
    'Point #': pl.Int64,
    'E(V)': pl.Float64,
    'I(A)': pl.Float64,
    'Elapsed Time(s)': pl.Float64,
    'ADC Sync Input(V)': pl.Float64,
    'Current Range': pl.Int64,
    'Status': pl.Int64,
    'E Applied(V)': pl.Float64,
    'Frequency(Hz)': pl.Float64,
    'E Real': pl.Float64,
    'E Imag': pl.Float64,
    'I Real': pl.Float64,
    'I Imag': pl.Float64,
    'Z Real': pl.Float64,
    'Z Imag': pl.Float64,
    'E2 Status': pl.Int64,
    'E2(V)': pl.Float64,
    'E2 Real': pl.Float64,
    'E2 Imag': pl.Float64,
    'Z2 Real': pl.Float64,
    'Z2 Imag': pl.Float64,
    'ActionId': pl.Int64,
    'AC Amplitude': pl.Float64
}


class SignalType(Enum):
    """Signal type classification."""
    DC = "DC"
    AC = "AC"
    MIXED = "mixed"


class TechniqueType(Enum):
    """Electrochemical technique types."""
    OCV = "Open Circuit"
    CC = "Constant Current"
    CV = "Cyclic Voltammetry"
    EIS = "Electrochemical Impedance Spectroscopy"
    GITT = "Galvanostatic Intermittent Titration Technique"
    PITT = "Potentiostatic Intermittent Titration Technique"
    CA = "Chronoamperometry"
    CP = "Chronopotentiometry"
    UNKNOWN = "Unknown"


@dataclass
class ActionDefinition:
    """Represents a single action from the .par file."""
    action_id: int
    name: str
    parameters: Dict[str, Any]
    parent_action_id: Optional[int] = None

    def __post_init__(self):
        """Classify action type based on name."""
        name_lower = self.name.lower()
        if "open circuit" in name_lower:
            self.technique = TechniqueType.OCV
        elif "constant current" in name_lower:
            self.technique = TechniqueType.CC
        elif "cyclic voltammetry" in name_lower or "cv" in name_lower:
            self.technique = TechniqueType.CV
        elif "eis" in name_lower or "impedance" in name_lower:
            self.technique = TechniqueType.EIS
        elif "gitt" in name_lower:
            self.technique = TechniqueType.GITT
        elif "pitt" in name_lower:
            self.technique = TechniqueType.PITT
        elif "chronoamperometry" in name_lower:
            self.technique = TechniqueType.CA
        elif "chronopotentiometry" in name_lower:
            self.technique = TechniqueType.CP
        else:
            self.technique = TechniqueType.UNKNOWN


@dataclass
class SegmentData:
    """Represents a data segment from the .par file."""
    segment_id: int
    segment_type: int
    version: int
    column_definition: str
    data: pl.DataFrame

    @property
    def signal_type(self) -> SignalType:
        """Determine signal type based on data content."""
        if self.data.is_empty():
            return SignalType.DC

        # Check if frequency column has non-zero values
        if 'Frequency(Hz)' in self.data.columns:
            freq_col = self.data.get_column('Frequency(Hz)')
            if freq_col.is_not_null().any() and (freq_col > 0).any():
                # Check if we also have DC measurements
                if (freq_col == 0).any() or freq_col.is_null().any():
                    return SignalType.MIXED
                else:
                    return SignalType.AC

        return SignalType.DC

    @property
    def row_count(self) -> int:
        """Number of data points in this segment."""
        return self.data.height


@dataclass
class DataFile:
    """
    Single .par file with universal schema data format.

    This class represents a complete measurement from one .par file,
    including both metadata and universal schema data.
    """
    file_path: Path
    timestamp: datetime
    universal_data: pl.DataFrame  # Universal 31-column schema
    actions: Dict[int, ActionDefinition]
    segments: Dict[int, SegmentData]
    metadata: Dict[str, Any]
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    file_hash: str = field(default="")
    
    def __post_init__(self):
        """Calculate file hash if not provided."""
        if not self.file_hash and self.file_path.exists():
            self.file_hash = calculate_file_hash(self.file_path)

    @property
    def primary_technique(self) -> TechniqueType:
        """Determine the primary technique for this measurement."""
        # Get all techniques from actions
        techniques = [action.technique for action in self.actions.values()
                     if action.technique != TechniqueType.UNKNOWN]

        if not techniques:
            return TechniqueType.UNKNOWN

        # Return most common technique, or first if tie
        from collections import Counter
        technique_counts = Counter(techniques)
        return technique_counts.most_common(1)[0][0]

    @property
    def signal_type(self) -> SignalType:
        """Determine overall signal type for this measurement."""
        segment_types = [segment.signal_type for segment in self.segments.values()]

        if SignalType.AC in segment_types and SignalType.DC in segment_types:
            return SignalType.MIXED
        elif SignalType.AC in segment_types:
            return SignalType.AC
        else:
            return SignalType.DC

    @property
    def duration_seconds(self) -> float:
        """Total measurement duration in seconds."""
        if self.universal_data.is_empty():
            return 0.0
        return self.universal_data.get_column('time_s').max()

    @property
    def point_count(self) -> int:
        """Total number of data points."""
        return self.universal_data.height

    def get_dc_data(self) -> pl.DataFrame:
        """Extract only DC measurements (Frequency = 0 or null)."""
        if 'frequency_hz' not in self.universal_data.columns:
            return self.universal_data
        return self.universal_data.filter(
            (pl.col('frequency_hz').is_null()) |
            (pl.col('frequency_hz') == 0)
        )

    def get_ac_data(self) -> pl.DataFrame:
        """Extract only AC measurements (Frequency > 0)."""
        if 'frequency_hz' not in self.universal_data.columns:
            return pl.DataFrame()
        return self.universal_data.filter(
            pl.col('frequency_hz').is_not_null() &
            (pl.col('frequency_hz') > 0)
        )

    def get_segment_data(self, segment_id: int) -> pl.DataFrame:
        """Get data for a specific segment."""
        if 'segment_number' not in self.universal_data.columns:
            return pl.DataFrame()
        return self.universal_data.filter(pl.col('segment_number') == segment_id)
    
    def get_technique_data(self, fundamental_technique: str) -> pl.DataFrame:
        """Get data for a specific fundamental technique."""
        return self.universal_data.filter(
            pl.col('fundamental_technique') == fundamental_technique
        )
    
    def get_eis_segments(self) -> List[pl.DataFrame]:
        """Get all EIS segments as separate DataFrames."""
        eis_data = self.universal_data.filter(
            (pl.col('fundamental_technique') == 'GEIS') |
            (pl.col('fundamental_technique') == 'PEIS')
        )
        
        if eis_data.is_empty():
            return []
        
        # Group by ActionId (each represents one EIS measurement)
        segments = []
        for action_id in eis_data.get_column('technique_id').unique():
            if action_id is not None:
                segment = eis_data.filter(pl.col('technique_id') == action_id)
                if not segment.is_empty():
                    segments.append(segment)
        
        return segments


@dataclass
class DataFileGroup:
    """
    Collection of related DataFiles (handles fragmented files).

    This class manages multiple .par files that belong to the same
    experimental sequence, providing seamless data access.
    """
    group_id: str
    description: str
    data_files: List[DataFile] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_data_file(self, data_file: DataFile) -> None:
        """Add a data file to this group."""
        self.data_files.append(data_file)
        # Sort by timestamp to maintain chronological order
        self.data_files.sort(key=lambda df: df.timestamp)

    def get_combined_data(self) -> pl.DataFrame:
        """
        Combine all data files with continuous timestamps.

        Returns data with adjusted elapsed times to create seamless
        temporal continuity across fragmented files.
        """
        if not self.data_files:
            return pl.DataFrame(schema=UNIVERSAL_SCHEMA)

        dfs = []
        cumulative_time = 0.0

        for data_file in self.data_files:
            df = data_file.universal_data.clone()

            # Adjust elapsed time for continuity
            if cumulative_time > 0:
                df = df.with_columns([
                    (pl.col('time_s') + cumulative_time).alias('time_s')
                ])

            # Update cumulative time for next file
            if not df.is_empty():
                cumulative_time = df.get_column('time_s').max()

            dfs.append(df)

        # Combine all dataframes
        combined = pl.concat(dfs, how="vertical_relaxed")

        return combined

    @property
    def total_duration(self) -> float:
        """Total duration across all files in seconds."""
        combined = self.get_combined_data()
        if combined.is_empty():
            return 0.0
        return combined.get_column('time_s').max()

    @property
    def total_points(self) -> int:
        """Total number of data points across all files."""
        return sum(df.point_count for df in self.data_files)

    @property
    def file_count(self) -> int:
        """Number of individual files in this group."""
        return len(self.data_files)

    @property
    def primary_technique(self) -> TechniqueType:
        """Determine primary technique across all files."""
        if not self.data_files:
            return TechniqueType.UNKNOWN

        techniques = [df.primary_technique for df in self.data_files]
        from collections import Counter
        technique_counts = Counter(techniques)
        return technique_counts.most_common(1)[0][0]


def prune_empty_columns(df: pl.DataFrame) -> pl.DataFrame:
    """
    Remove columns that contain only null values.

    This creates storage-optimized versions by removing unused columns.
    """
    if df.is_empty():
        return df

    # Find columns that are entirely null
    null_columns = []
    for col in df.columns:
        if df.get_column(col).is_null().all():
            null_columns.append(col)

    # Keep all non-null columns
    keep_columns = [col for col in df.columns if col not in null_columns]

    return df.select(keep_columns)


def map_technique_name(action_name: str) -> str:
    """
    Map VersaStudio action name to fundamental technique.
    
    Args:
        action_name: Original action name from VersaStudio
        
    Returns:
        Fundamental technique type (OCV, CC, CV, GEIS, PEIS, UNKNOWN)
    """
    if not action_name:
        return 'UNKNOWN'
        
    action_lower = action_name.lower()
    
    for fundamental_technique, technique_variants in TECHNIQUE_MAPPING.items():
        for variant in technique_variants:
            if variant.lower() in action_lower:
                return fundamental_technique
                
    return 'UNKNOWN'

def create_universal_dataframe(versastudio_data: pl.DataFrame, 
                             segment_mapping: Dict[int, str],
                             start_timestamp: datetime) -> pl.DataFrame:
    """
    Convert VersaStudio DataFrame to universal schema.
    
    Args:
        versastudio_data: Original VersaStudio DataFrame
        segment_mapping: Segment# -> technique name mapping (hierarchy-based)
        start_timestamp: Experiment start timestamp
        
    Returns:
        DataFrame with universal schema
    """
    # Start with empty universal dataframe
    n_rows = versastudio_data.height
    universal_data = {}
    
    # Initialize all columns with appropriate nulls
    for col, dtype in UNIVERSAL_SCHEMA.items():
        if dtype == pl.Float64:
            universal_data[col] = [None] * n_rows
        elif dtype == pl.Int64:
            universal_data[col] = [None] * n_rows
        elif dtype == pl.Utf8:
            universal_data[col] = [None] * n_rows
        elif dtype == pl.Datetime:
            universal_data[col] = [None] * n_rows
    
    # Map VersaStudio columns to universal columns
    for vs_col, universal_col in VERSASTUDIO_MAPPING.items():
        if vs_col in versastudio_data.columns:
            universal_data[universal_col] = versastudio_data.get_column(vs_col).to_list()
    
    # Create DataFrame with universal schema
    df = pl.DataFrame(universal_data, schema=UNIVERSAL_SCHEMA)
    
    # Add computed columns
    df = df.with_columns([
        # Absolute timestamps
        (pl.lit(start_timestamp) + 
         pl.duration(seconds=pl.col('time_s'))).alias('timestamp'),
        
        # Power calculation
        (pl.col('potential_v') * pl.col('current_a')).alias('power_w'),
        
        # Impedance magnitude and phase
        ((pl.col('impedance_real_ohm')**2 + 
          pl.col('impedance_imag_ohm')**2)**0.5).alias('impedance_mag_ohm'),
        
        (pl.when(pl.col('impedance_real_ohm') != 0)
         .then((pl.col('impedance_imag_ohm') / pl.col('impedance_real_ohm')).arctan() * 180.0 / np.pi)
         .otherwise(90.0 * pl.col('impedance_imag_ohm').sign())).alias('impedance_phase_deg')
    ])
    
    # Add technique names based on SEGMENT mapping (hierarchy-based approach)
    if segment_mapping:
        technique_names = []
        fundamental_techniques = []
        
        for segment_num in df.get_column('segment_number'):
            if segment_num is not None and segment_num in segment_mapping:
                technique_name = segment_mapping[segment_num]
                fundamental_technique = map_technique_name(technique_name)
            else:
                technique_name = 'Unknown'
                fundamental_technique = 'UNKNOWN'
                
            technique_names.append(technique_name)
            fundamental_techniques.append(fundamental_technique)
        
        df = df.with_columns([
            pl.Series('technique_name', technique_names),
            pl.Series('fundamental_technique', fundamental_techniques)
        ])
    
    return df

def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA256 hash of file for integrity checking.
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def create_standardized_dataframe(data: Dict[str, List], available_columns: List[str]) -> pl.DataFrame:
    """
    Legacy function for backward compatibility.
    """
    # Start with available data
    df_data = {}

    for col in VERSASTUDIO_COLUMNS:
        if col in available_columns and col in data:
            df_data[col] = data[col]
        else:
            # Create null column with appropriate type
            data_length = len(next(iter(data.values()))) if data else 0
            df_data[col] = [None] * data_length

    # Create with explicit schema to avoid type inference issues
    return pl.DataFrame(df_data, schema=VERSASTUDIO_SCHEMA)