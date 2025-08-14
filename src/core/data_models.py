"""
Core data models for battery data analyzer.
Fixed version with DataFile/DataFileGroup naming.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import polars as pl
from enum import Enum


# Standardized VersaStudio column schema with explicit types
VERSASTUDIO_COLUMNS = [
    'Segment #', 'Point #', 'E(V)', 'I(A)', 'Elapsed Time(s)',
    'ADC Sync Input(V)', 'Current Range', 'Status', 'E Applied(V)',
    'Frequency(Hz)', 'E Real', 'E Imag', 'I Real', 'I Imag',
    'Z Real', 'Z Imag', 'E2 Status', 'E2(V)', 'E2 Real', 'E2 Imag',
    'Z2 Real', 'Z2 Imag', 'ActionId', 'AC Amplitude'
]

# Explicit schema for Polars (fixes type inference issues)
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
    Single .par file with standardized data format.

    This class represents a complete measurement from one .par file,
    including both metadata and standardized data.
    """
    file_path: Path
    timestamp: datetime
    full_data: pl.DataFrame  # Complete standardized schema
    pruned_data: pl.DataFrame  # Storage-optimized (empty columns removed)
    actions: Dict[int, ActionDefinition]
    segments: Dict[int, SegmentData]
    metadata: Dict[str, Any]

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
        if self.full_data.is_empty():
            return 0.0
        return self.full_data.get_column('Elapsed Time(s)').max()

    @property
    def point_count(self) -> int:
        """Total number of data points."""
        return self.full_data.height

    def get_dc_data(self) -> pl.DataFrame:
        """Extract only DC measurements (Frequency = 0 or null)."""
        if 'Frequency(Hz)' not in self.full_data.columns:
            return self.full_data
        return self.full_data.filter(
            (pl.col('Frequency(Hz)').is_null()) |
            (pl.col('Frequency(Hz)') == 0)
        )

    def get_ac_data(self) -> pl.DataFrame:
        """Extract only AC measurements (Frequency > 0)."""
        if 'Frequency(Hz)' not in self.full_data.columns:
            return pl.DataFrame()
        return self.full_data.filter(
            pl.col('Frequency(Hz)').is_not_null() &
            (pl.col('Frequency(Hz)') > 0)
        )

    def get_segment_data(self, segment_id: int) -> pl.DataFrame:
        """Get data for a specific segment."""
        if 'Segment #' not in self.full_data.columns:
            return pl.DataFrame()
        return self.full_data.filter(pl.col('Segment #') == segment_id)


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
            return pl.DataFrame(schema=VERSASTUDIO_SCHEMA)

        dfs = []
        cumulative_time = 0.0

        for data_file in self.data_files:
            df = data_file.full_data.clone()

            # Adjust elapsed time for continuity
            if cumulative_time > 0:
                df = df.with_columns([
                    (pl.col('Elapsed Time(s)') + cumulative_time).alias('Elapsed Time(s)')
                ])

            # Update cumulative time for next file
            if not df.is_empty():
                cumulative_time = df.get_column('Elapsed Time(s)').max()

            dfs.append(df)

        # Combine all dataframes
        combined = pl.concat(dfs, how="vertical_relaxed")

        # Add absolute timestamps
        start_time = min(df.timestamp for df in self.data_files)
        combined = combined.with_columns([
            (pl.lit(start_time) +
             pl.duration(seconds=pl.col('Elapsed Time(s)'))).alias('absolute_timestamp')
        ])

        return combined

    @property
    def total_duration(self) -> float:
        """Total duration across all files in seconds."""
        combined = self.get_combined_data()
        if combined.is_empty():
            return 0.0
        return combined.get_column('Elapsed Time(s)').max()

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


def create_standardized_dataframe(data: Dict[str, List], available_columns: List[str]) -> pl.DataFrame:
    """
    Create a DataFrame with standardized column schema.

    Args:
        data: Dictionary of column_name -> values
        available_columns: List of columns present in the data

    Returns:
        DataFrame with full VERSASTUDIO_COLUMNS schema (NaN for missing columns)
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