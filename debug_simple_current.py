#!/usr/bin/env python3
"""Simple current column investigation."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

def simple_current_check():
    """Simple check of current columns."""
    
    parser = BiologicParser()
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    print("=== SIMPLE CURRENT CHECK ===\n")
    
    # Check boundary rows 8-13
    print("Raw data (after control splitting):")
    boundary = raw_df.slice(8, 6).select(['Ns', 'I', 'control_I'])
    
    for i, row in enumerate(boundary.iter_rows(named=True)):
        row_num = 8 + i
        ns = row['Ns']
        raw_I = row['I']
        control_I = row['control_I']
        
        # Handle NaN values
        control_I_str = "nan" if str(control_I) == "nan" else f"{control_I:.6f}"
        
        print(f"Row {row_num}: Ns={ns}, I={raw_I:.6f}, control_I={control_I_str}")
    
    print(f"\n=== UNIVERSAL SCHEMA COMPARISON ===")
    
    # Get universal schema
    result = parser.parse_data(mpr_file)
    universal_df = result.universal_data if hasattr(result, 'universal_data') else result.universal_data
    
    univ_boundary = universal_df.slice(8, 6).select(['segment_number', 'current_a'])
    
    print("Universal schema current_a:")
    for i, row in enumerate(univ_boundary.iter_rows(named=True)):
        row_num = 8 + i
        segment = row['segment_number']
        current_a = row['current_a']
        
        current_a_str = "nan" if str(current_a) == "nan" else f"{current_a:.6f}"
        print(f"Row {row_num}: segment={segment}, current_a={current_a_str}")
    
    print(f"\n=== KEY INSIGHT ===")
    print("The problem:")
    print("- Raw 'I' column has correct measured currents (0.000 for Rest)")
    print("- But universal 'current_a' shows nan values")
    print("- This suggests the universal mapping is using 'control_I' instead of 'I'")
    print("- For Rest phases, we want measured current ('I'), not control current ('control_I')")

if mpr_file.exists():
    simple_current_check()
else:
    print(f"❌ File not found: {mpr_file}")