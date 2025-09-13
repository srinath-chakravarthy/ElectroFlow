#!/usr/bin/env python3
"""Show raw columns by intercepting before control splitting."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl
import numpy as np

# Test file path  
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

def show_raw_columns_before_splitting():
    """Show all raw columns before control splitting."""
    
    # Create a custom class to intercept the data
    class DebugMPRReader:
        def __init__(self):
            from src_clean.parsers.mpr_reader import MPRReader
            self.reader = MPRReader(debug=False)
            
        def parse_with_intercept(self, file_path):
            # Call the original parse method but intercept the data_dict
            original_split = self.reader._split_control_column
            intercepted_data = {}
            
            def intercept_split(data_dict):
                # Store the data before splitting
                intercepted_data.update(data_dict)
                # Call original split
                return original_split(data_dict)
            
            # Replace the method temporarily
            self.reader._split_control_column = intercept_split
            
            # Parse the file
            result = self.reader.parse_mpr_file(file_path)
            
            return intercepted_data, result
    
    debug_reader = DebugMPRReader()
    raw_data_dict, processed_df = debug_reader.parse_with_intercept(mpr_file)
    
    print("=== RAW BINARY COLUMNS (before control splitting) ===\n")
    
    # Show available columns
    print(f"Available columns: {list(raw_data_dict.keys())}")
    
    # Focus on key columns for rows 8-13
    key_columns = ['Ns', 'flags', 'time', 'control', 'I', 'Ewe']
    
    print(f"\n=== ROWS 8-13 ANALYSIS ===")
    
    for row_num in range(8, 14):
        print(f"\nRow {row_num}:")
        for col in key_columns:
            if col in raw_data_dict:
                value = raw_data_dict[col][row_num]
                
                if col == 'flags':
                    # Decode flags  
                    mode = int(value) & 0b00000011
                    mode_name = {0: "Unknown", 1: "Galv", 2: "Pot", 3: "Galv"}.get(mode, f"Mode{mode}")
                    print(f"  {col}: {value} (0b{value:08b}) → mode={mode} ({mode_name})")
                    
                elif col in ['time', 'control', 'I', 'Ewe']:
                    print(f"  {col}: {value:.6f}")
                else:
                    print(f"  {col}: {value}")
    
    print(f"\n=== CONTROL COLUMN ANALYSIS ===")
    
    for row_num in range(8, 14):
        ns = raw_data_dict['Ns'][row_num]
        flags = raw_data_dict['flags'][row_num]  
        control = raw_data_dict['control'][row_num]
        measured_I = raw_data_dict['I'][row_num]
        mode = int(flags) & 0b00000011
        
        print(f"Row {row_num}: Ns={ns}, mode={mode}, control={control:.6f}, measured_I={measured_I:.6f}")
        
        # Analysis
        if mode in {1, 3}:  # Galvanostatic
            print(f"  → Control splitting will set control_I = {control:.6f}")
            if abs(control - measured_I) > 0.01:
                print(f"  ⚠️  MISMATCH: control ({control:.6f}) ≠ measured_I ({measured_I:.6f})")
        else:
            print(f"  → Control splitting will set control_I = nan")

if mpr_file.exists():
    show_raw_columns_before_splitting()
else:
    print(f"❌ File not found: {mpr_file}")