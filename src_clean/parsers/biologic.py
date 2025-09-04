"""
MPR Binary Reader - Pure binary parsing utility

Handles MPR binary format parsing using YADG logic.
No inheritance - pure utility class.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import polars as pl

from .configs.biologic_mappings import (
    data_columns,
    conflict_columns,
    flag_columns,
    technique_dependent_ids,
    module_header_dtypes,
    log_dtypes
)


class MPRReader:
    """Pure binary parsing utility for MPR files."""

    def __init__(self, debug: bool = False):
        self.debug = debug

    def parse_mpr_file(self, file_path: Path) -> pl.DataFrame:
        """
        Parse MPR file and return raw Polars DataFrame.

        Args:
            file_path: Path to .mpr file

        Returns:
            Polars DataFrame with biologic column names
        """
        if self.debug:
            print(f"Parsing MPR file: {file_path}")

        with open(file_path, "rb") as f:
            mpr_bytes = f.read()

        # Validate file magic
        file_magic = b"BIO-LOGIC MODULAR FILE\x1a"
        if not mpr_bytes.startswith(file_magic):
            raise ValueError("Invalid MPR file format")

        # Process modules
        data_df, log_metadata = self._process_modules(mpr_bytes)
        
        # Store log metadata for timestamp processing
        self.last_log_metadata = log_metadata
        return data_df

    def _process_modules(self, content: bytes) -> tuple[pl.DataFrame, dict]:
        """Process all modules and extract data with log metadata."""
        modules = content.split(b"MODULE")[1:]
        data_df = None
        log_metadata = {}
        technique = ""

        if self.debug:
            print(f"Found {len(modules)} modules")

        for i, module in enumerate(modules):
            if len(module) == 0:
                continue

            header = self._read_module_header(module)
            if header is None:
                continue

            name = header["short_name"]
            version = header.get("newver", 0) + header["oldver"]
            module_data = module[self._get_header_size(module):]

            if self.debug:
                print(f"Module {i}: '{name}' version: {version}")

            if name == "VMP Set":
                technique = self._extract_technique(module_data)
            elif name == "VMP data":
                data_df = self._process_data_module(module_data, version, technique)
            elif name == "VMP LOG":
                log_metadata = self._process_log_module(module_data)

        if data_df is None:
            raise ValueError("No data module found in MPR file")

        return data_df, log_metadata

    def _process_log_module(self, module_data: bytes) -> dict:
        """
        Process BioLogic log module to extract acquisition timestamp and metadata.
        
        Log module contains:
        - OLE timestamp (0x0249) - Microsoft OLE date format
        - Device info, software versions, channel data
        """
        log_metadata = {}
        
        if self.debug:
            print(f"Processing log module, size: {len(module_data)}")
        
        # Extract log fields using YADG mappings
        for offset, (dtype_str, field_name) in log_dtypes.items():
            try:
                if offset + self._get_dtype_size(dtype_str) <= len(module_data):
                    if dtype_str == "pascal":
                        value = self._read_pascal_string(module_data, offset)
                    else:
                        dtype = np.dtype(dtype_str)
                        value = np.frombuffer(module_data, offset=offset, dtype=dtype, count=1)[0]
                        
                        # Convert numpy types to Python types
                        if hasattr(value, 'item'):
                            value = value.item()
                    
                    log_metadata[field_name] = value
                    
                    if self.debug and field_name == "ole_timestamp":
                        print(f"Extracted OLE timestamp: {value}")
                        
            except Exception as e:
                if self.debug:
                    print(f"Could not extract {field_name} at offset 0x{offset:04x}: {e}")
                continue
        
        return log_metadata
    
    def _get_dtype_size(self, dtype_str: str) -> int:
        """Get size in bytes for a numpy dtype string."""
        if dtype_str == "pascal":
            return 256  # Conservative estimate for pascal strings
        else:
            return np.dtype(dtype_str).itemsize
    
    def _read_pascal_string(self, data: bytes, offset: int) -> str:
        """Read a Pascal string (length-prefixed) from binary data."""
        try:
            if offset >= len(data):
                return ""
            
            length = data[offset]
            if offset + 1 + length > len(data):
                return ""
            
            string_bytes = data[offset + 1:offset + 1 + length]
            return string_bytes.decode('ascii', errors='ignore').strip()
        except Exception:
            return ""

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
            acquisition_datetime = ole_epoch + \
                                 timedelta(days=days, seconds=seconds_in_day)
            
            if self.debug:
                print(f"Converted OLE {ole_float} → {acquisition_datetime}")
                
            return acquisition_datetime
            
        except Exception as e:
            if self.debug:
                print(f"OLE timestamp conversion failed: {e}")
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
            if self.debug:
                print("Warning: No time_s column found, cannot calculate absolute timestamps")
            return df
        
        try:
            # Convert acquisition_start to Polars datetime literal
            start_lit = pl.lit(acquisition_start)
            
            # Calculate absolute timestamps: acquisition_start + time_s
            df = df.with_columns([
                (start_lit + pl.duration(seconds=pl.col('time_s'))).alias('timestamp')
            ])
            
            if self.debug:
                print(f"Added absolute timestamps starting from {acquisition_start}")
                
        except Exception as e:
            if self.debug:
                print(f"Failed to add absolute timestamps: {e}")
        
        return df

    def _read_module_header(self, module: bytes) -> Optional[Dict]:
        """Read module header using YADG logic."""
        for dtype in module_header_dtypes:
            try:
                if len(module) < dtype.itemsize:
                    continue

                value = np.frombuffer(module, offset=0, dtype=dtype, count=1)[0]

                header = {}
                for field_name in dtype.names:
                    field_value = value[field_name]
                    if hasattr(field_value, 'decode'):
                        header[field_name] = field_value.decode('ascii', errors='ignore').strip()
                    else:
                        header[field_name] = field_value

                # Fix invalid length
                if header["length"] == 0xFFFFFFFF:
                    header["length"] = len(module) - dtype.itemsize

                # Validate length
                if len(module) >= dtype.itemsize + header["length"]:
                    return header

            except Exception:
                continue

        return None

    def _get_header_size(self, module: bytes) -> int:
        """Get header size for module."""
        for dtype in module_header_dtypes:
            if len(module) >= dtype.itemsize:
                return dtype.itemsize
        return 0

    def _extract_technique(self, data: bytes) -> str:
        """Extract technique from settings module."""
        # TODO: Implement technique extraction from settings
        return "Unknown"

    def _process_data_module(self, data: bytes, version: int, technique: str) -> pl.DataFrame:
        """Process data module using YADG logic."""
        if len(data) < 5:
            raise ValueError("Data module too small")

        # Read data header
        n_datapoints = np.frombuffer(data, offset=0x0000, dtype="<u4", count=1)[0]
        n_columns = np.frombuffer(data, offset=0x0004, dtype="|u1", count=1)[0]

        if self.debug:
            print(f"Data points: {n_datapoints}, Columns: {n_columns}")

        if n_datapoints == 0 or n_columns == 0:
            raise ValueError("No data points or columns")

        # Version-specific column ID parsing
        if version in {10, 11}:
            column_ids = np.frombuffer(data, offset=0x005, dtype=">u2", count=n_columns)
        elif version in {2, 3}:
            column_ids = np.frombuffer(data, offset=0x005, dtype="<u2", count=n_columns)
        else:
            column_ids = np.frombuffer(data, offset=0x005, dtype="<u2", count=n_columns)

        if self.debug:
            print(f"Column IDs: {list(column_ids)}")

        # Parse columns
        names, dtypes, units, flags = self._parse_columns(list(column_ids), technique)

        # Create numpy dtype for structured array
        data_dtype = np.dtype(list(zip(names, dtypes)))

        # Version-specific data offset
        if version in {10, 11}:
            offset = 0x3EF
        elif version == 2:
            offset = 0x195
        elif version == 3:
            offset = 0x196
        else:
            offset = 0x195

        if self.debug:
            print(f"Using data offset: 0x{offset:X}")

        # Parse binary data
        try:
            values = np.frombuffer(data, offset=offset, dtype=data_dtype, count=n_datapoints)

            # Convert to dictionary
            data_dict = {}
            for name in names:
                data_dict[name] = values[name]

            # Create Polars DataFrame
            df = pl.DataFrame(data_dict)

            if self.debug:
                print(f"Created DataFrame: {df.shape}")

            return df

        except Exception as e:
            raise ValueError(f"Failed to parse data: {e}")

    def _parse_columns(self, column_ids: List[int], technique: str = "") -> Tuple[List, List, List, Dict]:
        """Parse column IDs using YADG logic."""
        names = []
        dtypes = []
        units = []
        flags = {}

        for col_id in column_ids:
            idd = col_id % 256

            # Check flag columns first
            if col_id in flag_columns:
                bitmask, name = flag_columns[col_id]
                flags[name] = bitmask
                if "flags" not in names:
                    names.append("flags")
                    dtypes.append("|u1")
                    units.append(None)

            # Check regular data columns
            elif idd in data_columns:
                dtype, name, unit = data_columns[idd]

                # Handle technique-dependent naming
                if idd in technique_dependent_ids:
                    name = technique_dependent_ids[idd].get(technique, name)

                # Handle duplicates
                if name in names:
                    name = f"duplicate_{name}"

                names.append(name)
                dtypes.append(dtype)
                units.append(unit)

            # Check conflict columns
            elif idd in conflict_columns:
                resolved = False
                for cid, cvals in conflict_columns[idd].items():
                    if cid in column_ids:
                        dtype, name, unit = cvals
                        names.append(name)
                        dtypes.append(dtype)
                        units.append(unit)
                        resolved = True
                        break

                if not resolved:
                    # Fallback
                    name = f"unknown_{len(names)}"
                    names.append(name)
                    dtypes.append("<f4")
                    units.append(None)

            else:
                # Unknown columns
                name = f"unknown_{len(names)}"
                if self.debug:
                    print(f"Unknown column ID {col_id} assigned to '{name}'")
                names.append(name)
                dtypes.append("<f4")
                units.append(None)

        return names, dtypes, units, flags


"""
BioLogic Parser - Integration with parser infrastructure

Inherits from SingleFileParser and integrates MPRReader for binary parsing.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import hashlib

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

import polars as pl
# from .mpr_reader import MPRReader


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
            
            if hasattr(self, 'last_log_metadata') and self.last_log_metadata:
                log_data = self.last_log_metadata
                
                # Extract OLE timestamp if available
                if 'ole_timestamp' in log_data:
                    ole_timestamp = log_data['ole_timestamp']
                    if ole_timestamp and ole_timestamp > 0:
                        acquisition_start = self._convert_ole_timestamp(ole_timestamp)
                        if self.debug:
                            print(f"Using extracted acquisition timestamp: {acquisition_start}")
                
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
            
            # Add absolute timestamps using extracted acquisition_start
            if INTEGRATED_MODE and hasattr(metadata, 'acquisition_start'):
                universal_df = self.mpr_reader._add_absolute_timestamps(universal_df, metadata.acquisition_start)
            elif isinstance(metadata, dict) and 'acquisition_start' in metadata:
                universal_df = self.mpr_reader._add_absolute_timestamps(universal_df, metadata['acquisition_start'])

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