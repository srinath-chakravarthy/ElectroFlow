"""
BioLogic MPR Binary Reader

Pure binary parsing utility for BioLogic MPR files using YADG logic.
Handles binary module processing, timestamp extraction, and raw data parsing.
No inheritance dependencies - standalone utility class.

Key Features:
- Binary MPR file structure parsing (settings, data, log modules)
- OLE timestamp extraction and conversion 
- Raw electrochemical data extraction
- Absolute timestamp calculation
- Debug logging for validation

Usage:
    reader = MPRReader(debug=True)
    raw_data, log_metadata = reader.parse_mpr_file(file_path)
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import polars as pl
import struct

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
        self.last_log_metadata = {}

    def parse_mpr_file(self, file_path: Path) -> pl.DataFrame:
        """
        Parse MPR file and return raw Polars DataFrame.
        
        Args:
            file_path: Path to .mpr file
            
        Returns:
            Polars DataFrame with raw electrochemical data
        """
        # Read and validate file
        with open(file_path, 'rb') as f:
            mpr_bytes = f.read()
        
        # Check file magic
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

                return header
            except (ValueError, IndexError, struct.error):
                continue

        if self.debug:
            print("Warning: Could not parse module header")
        return None

    def _get_header_size(self, module: bytes) -> int:
        """Get header size for module data offset."""
        for dtype in module_header_dtypes:
            if len(module) >= dtype.itemsize:
                return dtype.itemsize
        return 0

    def _extract_technique(self, module_data: bytes) -> str:
        """Extract technique name from settings module - basic implementation."""
        if len(module_data) > 0:
            technique_id = module_data[0]
            # Basic technique mapping - will be enhanced with parameter extraction
            technique_map = {
                0x04: "GCPL",
                0x0B: "OCV", 
                0x1D: "PEIS",
                0x1E: "GEIS",
                0x18: "CA",
                0x19: "CP"
            }
            return technique_map.get(technique_id, f"Unknown_{technique_id:02x}")
        return "Unknown"

    def _process_data_module(self, module_data: bytes, version: int, technique: str) -> pl.DataFrame:
        """Process data module and extract measurement data."""
        try:
            if len(module_data) < 5:
                raise ValueError("Data module too small")

            # Read data header
            n_datapoints = int.from_bytes(module_data[0:4], byteorder='little')
            n_columns = module_data[4]
            
            if self.debug:
                print(f"Data module: {n_datapoints} points, {n_columns} columns")

            # Read column IDs
            column_ids = list(module_data[5:5+n_columns])
            
            # Determine data start offset based on version
            data_offsets = [0x195, 0x196, 0x3ef]  # Common offsets
            data_offset = data_offsets[0]  # Default
            
            if data_offset >= len(module_data):
                raise ValueError("Data offset beyond module size")
            
            # Parse column information
            column_info = []
            for col_id in column_ids:
                if col_id in data_columns:
                    dtype_str, name, unit = data_columns[col_id]
                    # Handle technique-dependent column names
                    if col_id in technique_dependent_ids:
                        name = technique_dependent_ids[col_id].get(technique, name)
                    column_info.append((dtype_str, name, unit))
                else:
                    # Handle flag columns or unknown columns
                    column_info.append(('<f4', f'unknown_{col_id}', None))
            
            # Calculate row size and extract data
            row_size = sum(np.dtype(dtype).itemsize for dtype, _, _ in column_info)
            data_section = module_data[data_offset:]
            
            if len(data_section) < n_datapoints * row_size:
                if self.debug:
                    print(f"Warning: Expected {n_datapoints * row_size} bytes, got {len(data_section)}")
                n_datapoints = len(data_section) // row_size
            
            # Extract data arrays
            data_dict = {}
            current_offset = 0
            
            for dtype_str, name, unit in column_info:
                dtype = np.dtype(dtype_str)
                
                # Extract column data
                column_data = []
                for i in range(n_datapoints):
                    row_start = i * row_size + current_offset
                    if row_start + dtype.itemsize <= len(data_section):
                        value = np.frombuffer(data_section[row_start:row_start + dtype.itemsize], 
                                            dtype=dtype, count=1)[0]
                        column_data.append(value)
                    else:
                        column_data.append(np.nan)
                
                data_dict[name] = column_data
                current_offset += dtype.itemsize
            
            # Create Polars DataFrame
            return pl.DataFrame(data_dict)
            
        except Exception as e:
            if self.debug:
                print(f"Error processing data module: {e}")
            # Return minimal DataFrame
            return pl.DataFrame({"time": [0], "current": [0], "potential": [0]})