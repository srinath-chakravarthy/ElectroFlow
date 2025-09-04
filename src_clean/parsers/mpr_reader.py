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
from .configs.biologic_techniques import technique_params_dtypes


class MPRReader:
    """Pure binary parsing utility for MPR files."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.last_log_metadata = {}
        self.last_technique_parameters = {}

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
        data_df, log_metadata, technique_parameters = self._process_modules(mpr_bytes)
        
        # Store metadata for access by BiologicParser
        self.last_log_metadata = log_metadata
        self.last_technique_parameters = technique_parameters
        
        if self.debug and technique_parameters:
            print(f"Technique parameters extracted: {technique_parameters.get('_technique_name', 'Unknown')}")
            print(f"Number of sequences: {technique_parameters.get('_ns', 0)}")
        
        if self.debug and 'ole_timestamp' in log_metadata:
            print(f"OLE timestamp extracted: {log_metadata['ole_timestamp']}")
        
        return data_df

    def _process_modules(self, content: bytes) -> tuple[pl.DataFrame, dict, dict]:
        """Process all modules and extract data with log metadata and technique parameters."""
        modules = content.split(b"MODULE")[1:]
        data_df = None
        log_metadata = {}
        technique = ""
        technique_parameters = {}

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
                ftech = self._map_btech_to_ftech(technique)
                technique_parameters = self._extract_technique_parameters(module_data, technique)
                
                # Store both Btech and Ftech for later use
                technique_parameters['_btech_name'] = technique  # BioLogic technique
                technique_parameters['_ftech_name'] = ftech      # Fundamental technique
            elif name == "VMP data":
                data_df = self._process_data_module(module_data, version, technique)
            elif name == "VMP LOG":
                log_metadata = self._process_log_module(module_data)

        if data_df is None:
            raise ValueError("No data module found in MPR file")

        return data_df, log_metadata, technique_parameters

    def _process_log_module(self, module_data: bytes) -> dict:
        """
        Process BioLogic log module to extract acquisition timestamp and metadata.
        
        Log module contains:
        - OLE timestamp (offset 0x0249) - Microsoft OLE date format
        - Device info, software versions, channel data
        
        Uses YADG-compatible approach with proper module header validation
        to ensure correct offset calculations for timestamp extraction.
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
                        print(f"Extracted OLE timestamp at 0x{offset:04x}: {value}")
                        
            except Exception as e:
                if self.debug:
                    print(f"Could not extract {field_name} at offset 0x{offset:04x}: {e}")
                continue
        
        # Validate OLE timestamp
        ole_timestamp = log_metadata.get('ole_timestamp')
        if self.debug:
            if ole_timestamp and 1000 < ole_timestamp < 100000:
                print(f"Valid OLE timestamp: {ole_timestamp}")
            else:
                print(f"Invalid OLE timestamp: {ole_timestamp}")
        
        return log_metadata
    
    def _get_dtype_size(self, dtype_str: str) -> int:
        """Get size in bytes for a numpy dtype string."""
        if dtype_str == "pascal":
            return 256  # Conservative estimate for pascal strings
        else:
            return np.dtype(dtype_str).itemsize
    
    def _read_pascal_string(self, data: bytes, offset: int) -> str:
        """Read a Pascal string (length-prefixed) from binary data.
        
        Uses windows-1252 encoding for YADG compatibility.
        """
        try:
            if offset >= len(data):
                return ""
            
            length = data[offset]
            if offset + 1 + length > len(data):
                return ""
            
            string_bytes = data[offset + 1:offset + 1 + length]
            return string_bytes.decode('windows-1252', errors='ignore').strip()
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
        """Read module header using YADG logic with proper format selection."""
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

                # YADG's validation logic: check if length makes sense
                length = header.get("length", header.get("max_length", 0))
                expected_size = dtype.itemsize + length
                
                if len(module) >= expected_size:
                    return header
                    
            except (ValueError, IndexError, struct.error):
                continue

        if self.debug:
            print("Warning: Could not parse module header")
        return None

    def _get_header_size(self, module: bytes) -> int:
        """Get header size for module data offset using YADG validation.
        
        Uses YADG's approach: try each header dtype and validate that
        module_length == header_size + data_length. This ensures correct
        offset calculations for subsequent data reading.
        
        Critical for timestamp extraction - incorrect header sizes cause
        corrupted OLE timestamp values.
        """
        for mhd in module_header_dtypes:
            try:
                if len(module) >= mhd.itemsize:
                    # Read header and validate length matches
                    header_bytes = module[:mhd.itemsize]
                    header = np.frombuffer(header_bytes, dtype=mhd, count=1)[0]
                    
                    # Convert to dict for easier access
                    header_dict = {}
                    for field_name in mhd.names:
                        value = header[field_name]
                        # Decode bytes fields
                        if isinstance(value, bytes):
                            header_dict[field_name] = value.decode('windows-1252', errors='ignore').strip()
                        else:
                            header_dict[field_name] = value
                    
                    # Validate: total module length should match header + data length
                    expected_length = mhd.itemsize + header_dict["length"]
                    if len(module) == expected_length:
                        return mhd.itemsize
            except (UnicodeDecodeError, ValueError, KeyError):
                continue
        
        # Fallback to first matching size if validation fails
        for dtype in module_header_dtypes:
            if len(module) >= dtype.itemsize:
                return dtype.itemsize
        return 0

    def _extract_technique(self, module_data: bytes) -> str:
        """Extract technique name from settings module using YADG mapping."""
        if len(module_data) > 0:
            technique_id = module_data[0]
            if self.debug:
                print(f"Technique ID from settings: 0x{technique_id:02x}")
            
            # Use YADG technique mapping
            if technique_id in technique_params_dtypes:
                technique_name, _ = technique_params_dtypes[technique_id]
                if self.debug:
                    print(f"Identified technique: {technique_name}")
                return technique_name
            else:
                unknown_name = f"Unknown_{technique_id:02x}"
                if self.debug:
                    print(f"Unknown technique ID: 0x{technique_id:02x}")
                return unknown_name
        return "Unknown"

    def _map_btech_to_ftech(self, btech_name: str, ns_value: int = None) -> str:
        """
        Map BioLogic technique (Btech) to fundamental technique (Ftech).
        
        Args:
            btech_name: BioLogic technique name (e.g., "GCPL", "CV")
            ns_value: Sequence number within Btech (for future complex mapping)
            
        Returns:
            Fundamental technique name (e.g., "cc", "rest", "cv")
        """
        from .configs.biologic_mappings import BTECH_TO_FTECH_BASE_MAPPING
        
        # For now, use base mapping (Ns-specific mapping can be added later)
        return BTECH_TO_FTECH_BASE_MAPPING.get(btech_name, "unknown")

    def _extract_technique_parameters(self, module_data: bytes, technique: str) -> dict:
        """
        Extract technique parameters from settings module using YADG logic.
        
        Based on YADG's approach for parameter sequence extraction.
        Returns structured parameter data for technique interpretation.
        """
        if len(module_data) == 0:
            return {}
        
        technique_id = module_data[0]
        if technique_id not in technique_params_dtypes:
            if self.debug:
                print(f"No parameter structure for technique 0x{technique_id:02x}")
            return {}
        
        technique_name, params_dtypes_list = technique_params_dtypes[technique_id]
        
        if self.debug:
            print(f"Extracting parameters for {technique_name} (0x{technique_id:02x})")
        
        # Try multiple possible parameter offsets (from YADG mpr.py)
        offsets = [0x0572, 0x1845, 0x1846, 0x1847]
        
        for offset in offsets:
            if offset + 4 > len(module_data):
                continue
                
            try:
                # Get number of parameter sequences
                n_params = np.frombuffer(module_data, offset=offset + 0x0002, dtype="<u2", count=1)[0]
                
                if self.debug:
                    print(f"Trying offset 0x{offset:04x}, found {n_params} parameter sequences")
                
                # Try each dtype structure
                for params_dtype, version_info in params_dtypes_list:
                    if len(params_dtype) == n_params:
                        if self.debug:
                            print(f"Using parameter structure with {len(params_dtype)} parameters")
                        
                        # Get number of sequences
                        ns = np.frombuffer(module_data, offset=offset, dtype="<u2", count=1)[0]
                        
                        if offset + 0x0004 + ns * params_dtype.itemsize > len(module_data):
                            continue
                        
                        # Extract parameter sequences
                        rawparams = np.frombuffer(
                            module_data, 
                            offset=offset + 0x0004, 
                            dtype=params_dtype, 
                            count=ns
                        )
                        
                        # Convert to parameter dictionary
                        params = {}
                        for field_name in params_dtype.names:
                            params[field_name] = [param[field_name] for param in rawparams]
                        
                        params['_ns'] = ns  # Store number of sequences
                        params['_technique_id'] = technique_id
                        params['_technique_name'] = technique_name
                        
                        if self.debug:
                            print(f"Successfully extracted {ns} parameter sequences for {technique_name}")
                            print(f"Parameter fields: {list(params_dtype.names)}")
                        
                        return params
                        
            except Exception as e:
                if self.debug:
                    print(f"Failed to extract parameters at offset 0x{offset:04x}: {e}")
                continue
        
        if self.debug:
            print(f"No valid parameter structure found for {technique_name}")
        return {}

    def _process_data_module(self, module_data: bytes, version: int, technique: str) -> pl.DataFrame:
        """Process data module and extract measurement data."""
        try:
            if len(module_data) < 5:
                raise ValueError("Data module too small")

            # Read data header using YADG approach
            n_datapoints = np.frombuffer(module_data, offset=0x0000, dtype="<u4", count=1)[0]
            n_columns = np.frombuffer(module_data, offset=0x0004, dtype="|u1", count=1)[0]

            if self.debug:
                print(f"Data points: {n_datapoints}, Columns: {n_columns}")

            if n_datapoints == 0 or n_columns == 0:
                raise ValueError("No data points or columns")

            # Version-specific column ID parsing (following YADG logic)
            if version in {10, 11}:
                column_ids = np.frombuffer(module_data, offset=0x005, dtype=">u2", count=n_columns)
                data_offset = 0x3EF
            elif version in {2, 3}:
                column_ids = np.frombuffer(module_data, offset=0x005, dtype="<u2", count=n_columns)
                data_offset = 0x195 if version == 2 else 0x196
            else:
                # Default approach
                column_ids = np.frombuffer(module_data, offset=0x005, dtype="<u2", count=n_columns)
                data_offset = 0x195

            if self.debug:
                print(f"Column IDs: {list(column_ids)}")
                print(f"Using data offset: 0x{data_offset:X}")

            if data_offset >= len(module_data):
                raise ValueError("Data offset beyond module size")
            
            # Parse columns using YADG logic
            names, dtypes, units, flags = self._parse_columns(list(column_ids), technique)
            
            if self.debug:
                print(f"Parsed column names: {names}")
                print(f"Parsed dtypes: {dtypes}")

            # Create numpy dtype for structured array
            data_dtype = np.dtype(list(zip(names, dtypes)))

            # Parse binary data using YADG approach
            try:
                values = np.frombuffer(module_data, offset=data_offset, dtype=data_dtype, count=n_datapoints)

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
            
        except Exception as e:
            if self.debug:
                print(f"Error processing data module: {e}")
            # Return minimal DataFrame
            return pl.DataFrame({"time": [0], "current": [0], "potential": [0]})

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