"""
BioLogic Parser - Integration Layer

Integrates MPRReader with electrochemical data analysis platform.
Handles technique interpretation and universal schema conversion.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import hashlib
import polars as pl

from .mpr_reader import MPRReader

# Import from existing infrastructure
try:
    from .base import SingleFileParser
    from ..core.data_models import DataFile, FileMetadata, add_missing_universal_columns
    from ..core.exceptions import DataParsingError, MetadataExtractionError

    INTEGRATED_MODE = True
except ImportError:
    # Standalone mode - create minimal implementations
    INTEGRATED_MODE = False
    print("Running in standalone mode - using minimal implementations")


class BiologicParser(SingleFileParser if INTEGRATED_MODE else object):
    """BioLogic parser integrating with parser infrastructure."""

    PARSER_VERSION = "1.0.0"

    def __init__(self):
        if INTEGRATED_MODE:
            super().__init__()
        self.mpr_reader = MPRReader(debug=False)

    def get_instrument_name(self) -> str:
        """Return instrument name."""
        return "BioLogic"

    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return ['.mpr', '.mps', '.mpt']

    def validate_file(self, file_path: Path) -> bool:
        """Validate if file can be parsed by this parser."""
        try:
            if not file_path.exists():
                return False

            # Check file extension
            if not any(str(file_path).lower().endswith(ext) for ext in self.get_supported_extensions()):
                return False

            # Check file magic for MPR files
            if str(file_path).lower().endswith('.mpr'):
                with open(file_path, 'rb') as f:
                    magic = f.read(23)  # Length of "BIO-LOGIC MODULAR FILE"
                    return magic.startswith(b"BIO-LOGIC MODULAR FILE")

            # TODO: Add validation for .mps and .mpt files
            return True

        except Exception:
            return False

    def parse_metadata(self, file_path: Path) -> 'FileMetadata':
        """Extract metadata from MPR file with timestamp extraction."""
        try:
            # Basic file metadata
            file_size = file_path.stat().st_size
            file_hash = self._calculate_file_hash(file_path)

            # Extract acquisition timestamp from log metadata if available
            acquisition_start = datetime.now()  # Default fallback
            software_version = 'Unknown'
            
            if hasattr(self.mpr_reader, 'last_log_metadata') and self.mpr_reader.last_log_metadata:
                log_data = self.mpr_reader.last_log_metadata
                
                # Extract OLE timestamp if available
                if 'ole_timestamp' in log_data:
                    ole_timestamp = log_data['ole_timestamp']
                    if ole_timestamp and ole_timestamp > 0:
                        acquisition_start = self.mpr_reader._convert_ole_timestamp(ole_timestamp)
                
                # Extract software version if available
                if 'ec_lab_version' in log_data:
                    software_version = log_data.get('ec_lab_version', 'Unknown')

            metadata = {
                'original_filename': file_path.name,
                'file_hash': file_hash,
                'file_size_bytes': file_size,
                'parser_version': self.PARSER_VERSION,
                'acquisition_start': acquisition_start,  # Now extracted from file
                'acquisition_duration_s': 0.0,  # TODO: Calculate from data
                'instrument_model': 'BioLogic',
                'software_version': software_version,  # Now extracted from log
                'total_points': 0,  # TODO: Extract from data
                'technique_count': 1,  # TODO: Extract from settings
                'actionid_mappings': {},  # TODO: Extract technique mappings
                'notes': '',
                'user_metadata': {}
            }

            if INTEGRATED_MODE:
                return FileMetadata(**metadata)
            else:
                return metadata

        except Exception as e:
            if INTEGRATED_MODE:
                raise MetadataExtractionError(str(file_path), ["basic_metadata"])
            else:
                raise ValueError(f"Failed to extract metadata: {e}")

    def parse_data(self, file_path: Path) -> 'DataFile':
        """Parse MPR data file and return universal schema DataFile."""
        try:
            # Parse raw binary data
            raw_df = self.mpr_reader.parse_mpr_file(file_path)

            # Generate segment numbers from raw BioLogic Ns data BEFORE universal schema conversion
            raw_df = self._add_segment_numbers_to_raw_data(raw_df)

            # Convert to universal schema (segment_number will be included)
            universal_df = self._map_to_universal_schema(raw_df)

            # Add missing universal columns
            if INTEGRATED_MODE:
                universal_df = add_missing_universal_columns(universal_df)
                
                # BioLogic enhancement: populate electrode-specific columns from available data
                universal_df = self._enhance_biologic_electrode_columns(universal_df)
                
                # Add technique information to universal schema
                if hasattr(self.mpr_reader, 'last_technique_parameters'):
                    ftech_name = self.mpr_reader.last_technique_parameters.get('_ftech_name', 'unknown')
                    technique_id = self._get_technique_id_from_ftech(ftech_name)
                    
                    universal_df = universal_df.with_columns([
                        pl.lit(technique_id).alias('technique_id')  # Use existing universal column
                    ])
                

            # Extract metadata (needed for timestamps)
            metadata = self.parse_metadata(file_path)
            
            # Add absolute timestamps using extracted OLE timestamp from MPRReader
            if hasattr(self.mpr_reader, 'last_log_metadata') and self.mpr_reader.last_log_metadata:
                ole_timestamp = self.mpr_reader.last_log_metadata.get('ole_timestamp')
                if ole_timestamp and ole_timestamp > 1000 and ole_timestamp < 100000:  # Reasonable OLE timestamp range
                    try:
                        acquisition_start = self._convert_ole_timestamp(ole_timestamp)
                        universal_df = self._add_absolute_timestamps(universal_df, acquisition_start)
                    except Exception as e:
                        pass  # Continue without timestamps if conversion fails

            if INTEGRATED_MODE:
                return DataFile(
                    universal_data=universal_df,
                    metadata=metadata,
                    processing_timestamp=datetime.now()
                )
            else:
                return {
                    'universal_data': universal_df,
                    'metadata': metadata
                }

        except Exception as e:
            if INTEGRATED_MODE:
                raise DataParsingError(str(file_path), "MPR parsing", str(e))
            else:
                raise ValueError(f"Failed to parse data: {e}")

    def _map_to_universal_schema(self, df: pl.DataFrame) -> pl.DataFrame:
        """Map BioLogic raw data to universal schema with enhanced electrode-specific support."""
        try:
            from .configs.biologic_mappings import BIOLOGIC_TO_UNIVERSAL_MAPPING, BIOLOGIC_UNIT_CONVERSIONS
            
            expressions = []
            
            # Handle current_a with priority: control_I preferred over I
            if "control_I" in df.columns:
                # Use control_I (preferred)
                conversion_factor = BIOLOGIC_UNIT_CONVERSIONS.get("control_I", 1)
                expressions.append(
                    (pl.col("control_I") * conversion_factor).alias("current_a")
                )
            elif "I" in df.columns:
                # Use I as fallback
                conversion_factor = BIOLOGIC_UNIT_CONVERSIONS.get("I", 1)
                expressions.append(
                    (pl.col("I") * conversion_factor).alias("current_a")
                )
            
            # Handle all other mappings (excluding current_a conflicts)
            for biologic_col, universal_col in BIOLOGIC_TO_UNIVERSAL_MAPPING.items():
                if universal_col != "current_a" and biologic_col in df.columns:
                    # Apply unit conversion if needed
                    if biologic_col in BIOLOGIC_UNIT_CONVERSIONS:
                        conversion_factor = BIOLOGIC_UNIT_CONVERSIONS[biologic_col]
                        expressions.append(
                            (pl.col(biologic_col) * conversion_factor).alias(universal_col)
                        )
                    else:
                        expressions.append(
                            pl.col(biologic_col).alias(universal_col)
                        )
            
            # Calculate cell voltage: potential_v = Ewe - Ece (if both available)
            if "Ewe" in df.columns and "Ece" in df.columns:
                expressions.append(
                    (pl.col("Ewe") - pl.col("Ece")).alias("potential_v")
                )
            elif "Ewe" in df.columns:
                # For 2-electrode: cell voltage = WE voltage
                expressions.append(
                    pl.col("Ewe").alias("potential_v")
                )
            
            if expressions:
                universal_df = df.with_columns(expressions)
                
                # Get all possible mapped columns
                mapped_cols = [col for col in BIOLOGIC_TO_UNIVERSAL_MAPPING.values() if col != "current_a"]
                mapped_cols.append("current_a")  # Add current_a explicitly
                mapped_cols.append("potential_v")  # Add potential_v
                
                # Only select columns that actually exist
                available_cols = [col for col in mapped_cols if col in universal_df.columns]
                
                return universal_df.select(available_cols)
            else:
                return df
                
        except ImportError:
            # Fallback to legacy mapping for standalone mode
            column_mapping = {
                "time": "time_s",
                "Ewe": "potential_v",
                "I": "current_a",
                "(Q-Qo)": "capacity_ah",
                "dQ": "capacity_delta_ah",
                "|Energy|": "energy_wh",
                "Energy ce charge": "energy_charge_wh",
                "Energy ce discharge": "energy_discharge_wh",
                "Temperature": "temperature_c",
                "cycle number": "cycle_number",
            }

            # Apply legacy mapping for available columns
            rename_dict = {}
            for biologic_col, universal_col in column_mapping.items():
                if biologic_col in df.columns:
                    rename_dict[biologic_col] = universal_col

            if rename_dict:
                df = df.rename(rename_dict)

            # Select only mapped columns
            available_universal_cols = [col for col in column_mapping.values() if col in df.columns]
            if available_universal_cols:
                df = df.select(available_universal_cols)

            return df
    
    def _enhance_biologic_electrode_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Enhance BioLogic data with electrode-specific impedance columns.
        
        With updated mappings, electrode-specific impedance data is directly mapped
        from BioLogic columns (Zwe-ce, Zce) to universal schema. No additional 
        processing needed - all electrode impedance handled in main mapping.
        """
        # No additional processing needed - electrode impedance columns 
        # now directly mapped in BIOLOGIC_TO_UNIVERSAL_MAPPING
        return df

    def _get_technique_id_from_ftech(self, ftech_name: str) -> int:
        """Map fundamental technique to existing technique_id system."""
        ftech_to_id_mapping = {
            'rest': 23,    # OCV/Rest ActionID from VersaStudio
            'cv': 1,       # CV ActionID  
            'cc': 8,       # Galvanostatic ActionID
            'cp': 7,       # Potentiostatic ActionID
            'eis': 20,     # EIS ActionID
            'pulse': 9,    # Pulse ActionID
            'unknown': 0   # Unknown
        }
        return ftech_to_id_mapping.get(ftech_name, 0)

    def _add_segment_numbers_to_raw_data(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Add segment numbers to raw BioLogic data based on Ns (sequence) changes.
        
        This processes the raw data BEFORE universal schema conversion.
        BioLogic uses Ns column to indicate technique sequence changes.
        Each unique Ns value represents a separate segment.
        """
        # Check if we have the raw Ns column from BioLogic
        if 'Ns' in df.columns:
            # Create segment numbers based on Ns changes
            # Use Polars shift() to detect where Ns changes from previous row
            df_with_segments = df.with_columns([
                # Mark Ns changes: True where Ns differs from previous row
                (pl.col('Ns') != pl.col('Ns').shift(1)).alias('ns_change')
            ]).with_columns([
                # Cumulative sum of Ns changes gives us segment numbers
                # Add 1 to start segment numbering from 1 instead of 0
                (pl.col('ns_change').cast(pl.Int32).cum_sum() + 1).alias('segment_number')
            ]).drop('ns_change')  # Clean up helper column
            
            return df_with_segments
        else:
            # No Ns data available - single segment
            return df.with_columns(pl.lit(1).alias('segment_number'))

    def _generate_segment_numbers_from_ns(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Generate proper segment numbers based on BioLogic Ns (sequence) changes.
        
        BioLogic uses Ns column to indicate technique sequence changes.
        Each unique Ns value represents a separate segment.
        Map Ns values to sequential segment numbers for universal schema.
        """
        # Check if we have the raw Ns column from BioLogic
        if 'Ns' in df.columns:
            # Create segment numbers based on Ns changes
            # Use Polars shift() to detect where Ns changes from previous row
            df_with_segments = df.with_columns([
                # Mark Ns changes: True where Ns differs from previous row
                (pl.col('Ns') != pl.col('Ns').shift(1)).alias('ns_change')
            ]).with_columns([
                # Cumulative sum of Ns changes gives us segment numbers
                # Add 1 to start segment numbering from 1 instead of 0
                (pl.col('ns_change').cast(pl.Int32).cum_sum() + 1).alias('segment_number')
            ]).drop('ns_change')  # Clean up helper column
            
            return df_with_segments
        else:
            # No Ns data available - single segment
            return df.with_columns(pl.lit(1).alias('segment_number'))

    def _generate_segment_numbers(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Generate proper segment numbers based on technique_id changes.
        
        Each change in technique_id represents a new segment (technique transition).
        Map each technique block to sequential segment numbers for universal schema.
        """
        if 'technique_id' not in df.columns:
            # No technique_id data - single segment
            return df.with_columns(pl.lit(1).alias('segment_number'))
        
        # Create segment numbers based on technique_id changes
        # Use Polars shift() to detect where technique_id changes from previous row
        df_with_segments = df.with_columns([
            # Mark technique changes: True where technique_id differs from previous row
            (pl.col('technique_id') != pl.col('technique_id').shift(1)).alias('technique_change')
        ]).with_columns([
            # Cumulative sum of technique changes gives us segment numbers
            # Add 1 to start segment numbering from 1 instead of 0
            (pl.col('technique_change').cast(pl.Int32).cum_sum() + 1).alias('segment_number')
        ]).drop('technique_change')  # Clean up helper column
        
        return df_with_segments

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _convert_ole_timestamp(self, ole_float: float) -> datetime:
        """
        Convert Microsoft OLE timestamp to Python datetime.
        
        OLE timestamp format:
        - Float64 representing days since 1900-01-01 00:00:00
        - Integer part = days, fractional part = time of day
        
        Args:
            ole_float: OLE timestamp value
            
        Returns:
            Python datetime object
        """
        try:
            # OLE epoch: January 1, 1900 (but treat as January 2, 1900 due to Excel bug)
            # This matches the YADG implementation
            ole_epoch = datetime(1899, 12, 30)  # Adjusted for Excel/OLE bug
            
            # Extract days and fractional day
            days = int(ole_float)
            fraction = ole_float - days
            
            # Calculate total seconds from fractional day
            seconds_in_day = fraction * 24 * 60 * 60
            
            # Create datetime
            acquisition_datetime = ole_epoch + timedelta(days=days, seconds=seconds_in_day)
                
            return acquisition_datetime
            
        except Exception as e:
            # Return epoch time as fallback
            return datetime(1970, 1, 1)

    def _add_absolute_timestamps(self, df: pl.DataFrame, acquisition_start: datetime) -> pl.DataFrame:
        """
        Add absolute timestamp column to DataFrame.
        
        Calculates: timestamp = acquisition_start + time_s for each data point
        
        Args:
            df: DataFrame with time_s column
            acquisition_start: Experiment start datetime
            
        Returns:
            DataFrame with added timestamp column
        """
        if 'time_s' not in df.columns:
            return df
        
        try:
            # Convert acquisition_start to Polars datetime literal
            start_lit = pl.lit(acquisition_start)
            
            # Calculate absolute timestamps: acquisition_start + time_s
            df = df.with_columns([
                (start_lit + pl.duration(seconds=pl.col('time_s'))).alias('timestamp')
            ])
                
        except Exception as e:
            pass
        
        return df

    def get_parser_info(self) -> Dict[str, Any]:
        """Get parser information."""
        return {
            'instrument_name': self.get_instrument_name(),
            'supported_extensions': self.get_supported_extensions(),
            'parser_version': self.PARSER_VERSION,
            'integration_mode': 'integrated' if INTEGRATED_MODE else 'standalone'
        }