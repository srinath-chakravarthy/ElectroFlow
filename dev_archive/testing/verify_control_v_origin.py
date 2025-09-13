#!/usr/bin/env python3
"""Verify that control_V is created by our splitting logic, not raw BioLogic data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.mpr_reader import MPRReader
import polars as pl

# Current MB file
mb_file = Path("/Users/srinathchakravarthy/Desktop/AR-3753_3_electrode_full_GITT_EIS_0_04_MB_C06.mpr")

def verify_control_v_origin():
    """Check if control_V exists in raw data vs created by splitting."""
    
    reader = MPRReader()
    
    print("=== CONTROL_V ORIGIN VERIFICATION ===\n")
    
    # Step 1: Get truly raw data (before any splitting)
    try:
        with open(mb_file, 'rb') as f:
            # Parse header and modules 
            reader.header = reader._parse_header(f)
            reader.modules = reader._parse_modules(f)
            
            # Get raw column definitions from BioLogic binary format
            print("Raw BioLogic columns from binary format:")
            for module in reader.modules:
                if hasattr(module, 'data_columns') and module.data_columns:
                    print(f"  Module columns: {list(module.data_columns.keys())}")
                    for col_id, (dtype, name, unit) in module.data_columns.items():
                        if 'control' in name.lower() or 'ewe' in name.lower():
                            print(f"    ID {col_id}: {name} ({dtype}, {unit})")
    
    except Exception as e:
        print(f"Error reading raw format: {e}")
    
    # Step 2: Check what parse_mpr_file returns (after our processing)
    print(f"\n=== AFTER OUR PROCESSING ===")
    processed_df = reader.parse_mpr_file(mb_file)
    print(f"Processed columns: {processed_df.columns}")
    
    control_related = [col for col in processed_df.columns if 'control' in col.lower()]
    print(f"Control-related columns: {control_related}")
    
    # Step 3: Check what exists in the raw data_dict before splitting
    print(f"\n=== CHECKING CONTROL SPLITTING LOGIC ===")
    print("From mpr_reader.py _split_control_column() method:")
    print("- Input: 'control' column (raw from BioLogic)")
    print("- Output: 'control_I' and 'control_V' columns (our creation)")
    print("- Logic: Based on mode flags (1=Galvano→control_I, 2=Potentio→control_V)")

if mb_file.exists():
    verify_control_v_origin()
else:
    print(f"❌ File not found: {mb_file}")