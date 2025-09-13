#!/usr/bin/env python3
"""Show all columns before control splitting to understand the raw binary data."""

import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.mpr_reader import MPRReader
from src_clean.parsers.configs.biologic_mappings import data_columns, flag_columns

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

def debug_raw_binary_before_splitting():
    """Show raw binary data before any processing."""
    
    reader = MPRReader(debug=True)
    
    print("=== RAW BINARY DATA BEFORE CONTROL SPLITTING ===\n")
    
    # We need to intercept the data BEFORE control splitting
    # This requires modifying the parsing process
    
    # Parse file and extract modules
    with open(mpr_file, 'rb') as f:
        data = f.read()
    
    # Find data module (simplified version of internal logic)
    modules = reader._extract_modules(data)
    
    data_module = None
    technique = "MB"  # We know this is MB from earlier debug
    
    for module_data, version, name in modules:
        if name == "VMP data":
            data_module = module_data
            break
    
    if data_module is None:
        print("No data module found!")
        return
    
    # Parse data module header
    n_datapoints = np.frombuffer(data_module, offset=0x0000, dtype="<u4", count=1)[0]
    n_columns = np.frombuffer(data_module, offset=0x0004, dtype="|u1", count=1)[0]
    
    print(f"Data points: {n_datapoints}")
    print(f"Columns: {n_columns}")
    
    # Parse column IDs (version 11 format)
    column_ids = np.frombuffer(data_module, offset=0x005, dtype=">u2", count=n_columns)
    data_offset = 0x3EF
    
    print(f"Column IDs: {list(column_ids)}")
    
    # Parse columns
    names, dtypes, units, flags_info = reader._parse_columns(list(column_ids), technique)
    
    print(f"Column names: {names}")
    print(f"Data types: {dtypes}")
    
    # Create structured array
    data_dtype = np.dtype(list(zip(names, dtypes)))
    values = np.frombuffer(data_module, offset=data_offset, dtype=data_dtype, count=n_datapoints)
    
    print(f"\n=== RAW BINARY DATA (rows 8-13, BEFORE control splitting) ===")
    
    # Show the key columns for rows 8-13
    key_columns = ['Ns', 'flags', 'time', 'control', 'I', 'Ewe']
    available_columns = [col for col in key_columns if col in names]
    
    print(f"Available key columns: {available_columns}")
    
    for row_num in range(8, min(14, n_datapoints)):
        print(f"\nRow {row_num}:")
        for col in available_columns:
            if col in names:
                value = values[col][row_num]
                if col == 'flags':
                    # Decode flags
                    mode = int(value) & 0b00000011
                    mode_name = {0: "Unknown", 1: "Galv", 2: "Pot", 3: "Galv"}.get(mode, f"Mode{mode}")
                    print(f"  {col}: {value} (binary: {value:08b}, mode: {mode}={mode_name})")
                elif col in ['time', 'control', 'I', 'Ewe']:
                    print(f"  {col}: {value:.6f}")
                else:
                    print(f"  {col}: {value}")
    
    print(f"\n=== COLUMN INTERPRETATION ===")
    print("Key insight:")
    print("- 'control' column contains the MIXED current/voltage control values")
    print("- 'I' column contains the ACTUAL measured current")
    print("- 'flags' determines whether 'control' should be interpreted as current or voltage")
    print("- Control splitting creates 'control_I' and 'control_V' from 'control' + 'flags'")

if mpr_file.exists():
    debug_raw_binary_before_splitting()
else:
    print(f"❌ File not found: {mpr_file}")