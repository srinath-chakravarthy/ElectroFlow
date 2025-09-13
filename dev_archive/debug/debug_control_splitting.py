#!/usr/bin/env python3
"""Debug control column splitting around boundary rows."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

def debug_mpr_processing_steps(file_path):
    """Step through MPR processing to isolate where boundary corruption occurs."""
    
    parser = BiologicParser()
    
    # Step 1: Get the raw data BEFORE any processing
    print("=== STEP 1: RAW BINARY DATA (before control splitting) ===")
    
    # We need to manually call the internal methods to intercept the data
    # This requires looking into the MPRReader's internals
    
    # Enable debug
    parser.mpr_reader.debug = False  # Disable debug spam
    
    # Parse the file but intercept at key points
    raw_df = parser.mpr_reader.parse_mpr_file(file_path)
    
    # Check boundary rows in final output
    print("Final output - boundary analysis (rows 9-13):")
    boundary_data = raw_df.slice(9, 5).select(['Ns', 'time', 'I', 'control_I'])
    
    for i, row in enumerate(boundary_data.iter_rows(named=True)):
        row_num = 9 + i
        ns = row['Ns']
        current_I = row['I']
        control_I = row['control_I']
        
        # Check for discrepancy
        discrepancy = ""
        if row_num == 10:  # This should be last Ns=0 row
            if abs(current_I) > 0.001:
                discrepancy = " ⚠️  CORRUPTED - should be 0.0"
        elif row_num == 11:  # First Ns=1 row
            if abs(current_I) < 0.001:
                discrepancy = " ⚠️  CORRUPTED - should be ~14.4mA"
        
        print(f"Row {row_num}: Ns={ns}, I={current_I:.6f}mA, control_I={control_I}{discrepancy}")

def debug_control_splitting_internals():
    """Examine the control splitting logic in detail."""
    
    print("\n=== CONTROL SPLITTING ANALYSIS ===")
    
    # The key insight: check if the flags column mode detection is correct
    # around the boundary
    
    parser = BiologicParser()
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    print("Boundary flags analysis (rows 9-13):")
    if 'flags' in raw_df.columns:
        boundary_data = raw_df.slice(9, 5).select(['Ns', 'flags', 'I', 'control_I'])
        
        for i, row in enumerate(boundary_data.iter_rows(named=True)):
            row_num = 9 + i
            ns = row['Ns']
            flags = row['flags']
            current_I = row['I']
            control_I = row['control_I']
            
            # Decode mode from flags
            mode = int(flags) & 0b00000011
            mode_name = {1: "Galvanostatic", 2: "Potentiostatic", 3: "Galvanostatic"}.get(mode, f"Unknown({mode})")
            
            print(f"Row {row_num}: Ns={ns}, flags={flags:08b}, mode={mode}({mode_name}), I={current_I:.6f}mA")
    else:
        print("No flags column found!")

if mpr_file.exists():
    debug_mpr_processing_steps(mpr_file)
    debug_control_splitting_internals()
else:
    print(f"❌ File not found: {mpr_file}")