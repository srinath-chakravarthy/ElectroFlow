"""
BioLogic Parser - Integration Layer

Integrates MPRReader with electrochemical data analysis platform.
Handles technique interpretation and universal schema conversion.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import hashlib
import polars as pl

from .mpr_reader import MPRReader

# Import from existing infrastructure
try:
    from ..base import SingleFileParser
    from ..configs.universal_schema import add_missing_universal_columns
    from ...core.data_models import DataFile, FileMetadata
    from ...core.exceptions import DataParsingError, MetadataExtractionError

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

            # Convert to universal schema
            universal_df = self._map_to_universal_schema(raw_df)

            # Add missing universal columns
            if INTEGRATED_MODE:
                universal_df = add_missing_universal_columns(universal_df)
                
                # BioLogic enhancement: populate electrode-specific columns from available data
                universal_df = self._enhance_biologic_electrode_columns(universal_df)

            # Extract metadata (needed for timestamps)
            metadata = self.parse_metadata(file_path)
            
            # Note: Absolute timestamps already added in MPRReader if available

            if INTEGRATED_MODE:
                return DataFile(
                    universal_data=universal_df,
                    metadata=metadata
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
            
            for biologic_col, universal_col in BIOLOGIC_TO_UNIVERSAL_MAPPING.items():
                if biologic_col in df.columns:
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
                # Select only mapped columns
                mapped_cols = list(BIOLOGIC_TO_UNIVERSAL_MAPPING.values()) + ["potential_v"]
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
        
        BioLogic may provide electrode-specific impedance data. For now:
        - Map cell impedance to WE impedance columns (same data)
        - CE impedance columns remain null (until separate CE data identified)
        """
        expressions = []
        
        # Columns 2-5: Map cell impedance to WE impedance (same data for now)
        we_impedance_mappings = {
            'impedance_real_ohm': 'we_impedance_real_ohm',
            'impedance_imag_ohm': 'we_impedance_imag_ohm',
            'impedance_mag_ohm': 'we_impedance_mag_ohm',
            'impedance_phase_deg': 'we_impedance_phase_deg'
        }
        
        for source_col, target_col in we_impedance_mappings.items():
            if source_col in df.columns:
                expressions.append(
                    pl.col(source_col).alias(target_col)
                )
        
        # Apply enhancements
        if expressions:
            df = df.with_columns(expressions)
        
        # CE impedance columns remain null (already handled by add_missing_universal_columns)
        # TODO: Investigate if BioLogic provides separate CE impedance data
        return df

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def get_parser_info(self) -> Dict[str, Any]:
        """Get parser information."""
        return {
            'instrument_name': self.get_instrument_name(),
            'supported_extensions': self.get_supported_extensions(),
            'parser_version': self.PARSER_VERSION,
            'integration_mode': 'integrated' if INTEGRATED_MODE else 'standalone'
        }