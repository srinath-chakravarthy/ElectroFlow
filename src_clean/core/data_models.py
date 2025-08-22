"""
Clean Data Models - Electrochemical Analysis Suite

Universal schema definitions and data structures for instrument-agnostic
electrochemical data processing.

Key Principles:
- Single universal schema for all instruments (29 columns)
- Clean VersaStudio mapping (remove legacy schemas)
- DataFile class for universal data representation
- Explicit column types for reliable processing
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import polars as pl

# Import schema from config
from ..parsers.configs.universal_schema import UNIVERSAL_SCHEMA, get_polars_schema


# Note: VersaStudio schemas moved to src_clean/parsers/configs/versastudio_mappings.py


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FileMetadata:
    """Metadata extracted from instrument files."""
    
    # File information
    original_filename: str
    file_hash: str
    file_size_bytes: int
    parser_version: str
    
    # Acquisition metadata
    acquisition_start: datetime
    acquisition_duration_s: float
    instrument_model: str
    software_version: str
    
    # Experimental metadata
    total_points: int
    technique_count: int
    actionid_mappings: Dict[int, str]
    
    # Optional metadata
    notes: str = ""
    temperature_c: Optional[float] = None
    user_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.user_metadata is None:
            self.user_metadata = {}


@dataclass
class DataFile:
    """Universal data file representation."""
    
    # Universal schema data
    universal_data: pl.DataFrame
    
    # File metadata
    metadata: FileMetadata
    
    # Processing information
    processing_timestamp: datetime
    file_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate universal schema compliance."""
        self._validate_universal_schema()
    
    def _validate_universal_schema(self):
        """Ensure DataFrame matches universal schema."""
        expected_columns = set(UNIVERSAL_SCHEMA.keys())
        actual_columns = set(self.universal_data.columns)
        
        # Check for missing required columns
        missing_columns = expected_columns - actual_columns
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Check column types (allow extra columns for flexibility)
        for col_name, col_info in UNIVERSAL_SCHEMA.items():
            expected_type = col_info['type']  # Extract type from dict
            if col_name in actual_columns:
                actual_type = self.universal_data.schema[col_name]
                if actual_type != expected_type:
                    # Allow compatible types (e.g., Int32 vs Int64)
                    if not self._types_compatible(actual_type, expected_type):
                        raise ValueError(f"Column '{col_name}' has type {actual_type}, expected {expected_type}")
    
    def _types_compatible(self, actual_type, expected_type) -> bool:
        """Check if data types are compatible."""
        # Allow integer type variations
        if expected_type == pl.Int64 and actual_type in [pl.Int32, pl.Int64]:
            return True
        
        # Allow float type variations
        if expected_type == pl.Float64 and actual_type in [pl.Float32, pl.Float64]:
            return True
        
        return actual_type == expected_type
    
    @property
    def start_time(self) -> datetime:
        """Get experiment start timestamp."""
        return self.metadata.acquisition_start
    
    @property
    def duration_s(self) -> float:
        """Get experiment duration in seconds."""
        if 'time_s' in self.universal_data.columns:
            return float(self.universal_data['time_s'].max())
        return self.metadata.acquisition_duration_s
    
    @property
    def technique_ids(self) -> List[int]:
        """Get unique technique IDs in the data."""
        if 'technique_id' in self.universal_data.columns:
            return self.universal_data['technique_id'].unique().drop_nulls().to_list()
        return []
    
    @property
    def point_count(self) -> int:
        """Get total number of data points."""
        return self.universal_data.height
    
    def get_segment_boundaries(self) -> List[Dict[str, Any]]:
        """Get segment boundaries based on segment_number values from original instrument."""
        if 'segment_number' not in self.universal_data.columns:
            return [{
                'segment_number': 0,
                'technique_id': self.universal_data['technique_id'][0] if 'technique_id' in self.universal_data.columns else None,
                'start_row': 0,
                'end_row': self.point_count - 1,
                'start_time_s': 0.0,
                'end_time_s': self.duration_s,
                'point_count': self.point_count
            }]
        
        segments = []
        df = self.universal_data
        
        # Group by segment_number to find boundaries (respects original instrument segmentation)
        segment_groups = df.with_row_count().group_by('segment_number', maintain_order=True)
        
        for segment_number, group_df in segment_groups:
            if segment_number[0] is not None:  # segment_number is a tuple from group_by
                start_row = int(group_df['row_nr'].min())
                end_row = int(group_df['row_nr'].max())
                start_time = float(group_df['time_s'].min()) if 'time_s' in group_df.columns else 0.0
                end_time = float(group_df['time_s'].max()) if 'time_s' in group_df.columns else 0.0
                
                # Get the technique_id for this segment (should be consistent within segment)
                technique_id = group_df['technique_id'][0] if 'technique_id' in group_df.columns else None
                
                segments.append({
                    'segment_number': segment_number[0],
                    'technique_id': technique_id,
                    'start_row': start_row,
                    'end_row': end_row,
                    'start_time_s': start_time,
                    'end_time_s': end_time,
                    'point_count': group_df.height
                })
        
        return sorted(segments, key=lambda x: x['start_row'])


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_universal_schema(df: pl.DataFrame) -> bool:
    """Validate that DataFrame conforms to universal schema."""
    try:
        # Check required columns exist
        required_columns = set(UNIVERSAL_SCHEMA.keys())
        actual_columns = set(df.columns)
        
        missing_columns = required_columns - actual_columns
        if missing_columns:
            return False
        
        # Check column types
        for col_name, col_info in UNIVERSAL_SCHEMA.items():
            expected_type = col_info['type']  # Extract type from dict
            if col_name in df.columns:
                actual_type = df.schema[col_name]
                if actual_type != expected_type:
                    # Allow compatible integer/float types
                    if not _types_compatible(actual_type, expected_type):
                        return False
        
        return True
        
    except Exception:
        return False


def _types_compatible(actual_type, expected_type) -> bool:
    """Check if data types are compatible."""
    # Allow integer type variations
    if expected_type == pl.Int64 and actual_type in [pl.Int32, pl.Int64]:
        return True
    
    # Allow float type variations  
    if expected_type == pl.Float64 and actual_type in [pl.Float32, pl.Float64]:
        return True
    
    return actual_type == expected_type


def create_empty_universal_dataframe() -> pl.DataFrame:
    """Create an empty DataFrame with universal schema."""
    return pl.DataFrame(schema=get_polars_schema())


def add_missing_universal_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Add missing universal schema columns with null values."""
    existing_columns = set(df.columns)
    missing_columns = set(UNIVERSAL_SCHEMA.keys()) - existing_columns
    
    for col_name in missing_columns:
        col_type = UNIVERSAL_SCHEMA[col_name]['type']  # Extract type from dict
        # Add column with appropriate null values
        if col_type == pl.Utf8:
            df = df.with_columns(pl.lit(None).cast(col_type).alias(col_name))
        else:
            df = df.with_columns(pl.lit(None).cast(col_type).alias(col_name))
    
    return df


# =============================================================================
# CONSTANTS AND UTILITIES
# =============================================================================

# Fundamental technique classifications
FUNDAMENTAL_TECHNIQUES = {
    'rest': 'Rest/Open Circuit',
    'cv': 'Cyclic Voltammetry', 
    'cc': 'Constant Current',
    'cp': 'Constant Potential',
    'pulse': 'Pulse Technique',
    'eis': 'Electrochemical Impedance Spectroscopy',
    'unknown': 'Unknown/Unclassified'
}

# Default ActionID mappings for common VersaStudio techniques
DEFAULT_ACTIONID_MAPPINGS = {
    1: ('Rest', 'rest'),
    2: ('Potentiostatic', 'cp'),
    3: ('Galvanostatic', 'cc'),
    4: ('Linear Sweep', 'cv'),
    5: ('Cyclic Voltammetry', 'cv'),
    10: ('EIS', 'eis'),
    15: ('Current Interrupt', 'pulse'),
    20: ('GITT', 'pulse')
}


# Schema version for compatibility tracking
SCHEMA_VERSION = "2.0.0"
PARSER_VERSION = "2.0.0"