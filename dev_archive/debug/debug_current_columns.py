#!/usr/bin/env python3
"""Investigate all current-related columns to find the actual measured current."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

def investigate_current_columns():
    """Look at all current-related columns after processing."""
    
    parser = BiologicParser()
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    print("=== CURRENT COLUMN INVESTIGATION ===\n")
    
    print(f"Available columns: {raw_df.columns}")
    
    # Look for current-related columns
    current_columns = [col for col in raw_df.columns if 'I' in col or 'current' in col or 'control' in col]
    print(f"\nCurrent-related columns: {current_columns}")
    
    # Focus on boundary rows (8-13) to see all current columns
    print(f"\n=== BOUNDARY ROWS 8-13 ANALYSIS ===")
    
    boundary_data = raw_df.slice(8, 6).select(['Ns', 'flags'] + current_columns)
    
    print("All current-related values:")
    for i, row in enumerate(boundary_data.iter_rows(named=True)):
        row_num = 8 + i
        ns = row['Ns']
        flags = row['flags']
        mode = int(flags) & 0b00000011
        
        print(f"\nRow {row_num}: Ns={ns}, flags={flags}(mode={mode})")
        for col in current_columns:
            value = row[col]
            if col == 'I':
                print(f"  {col:15s}: {value:10.6f} ← RAW MEASURED CURRENT")
            elif col == 'control_I':
                print(f"  {col:15s}: {value:>10s} ← CONTROL TARGET (fixed)")
            elif col == 'control_V':
                print(f"  {col:15s}: {value:>10s} ← CONTROL VOLTAGE")
            else:
                print(f"  {col:15s}: {value:10.6f}")
    
    print(f"\n=== UNIVERSAL SCHEMA MAPPING INVESTIGATION ===")
    
    # Check what column is being used for universal 'current_a'
    # Let's trace through the mapping
    print("The key question: What column becomes 'current_a' in universal schema?")
    
    # Run full parsing to see universal schema
    result = parser.parse_data(mpr_file)
    universal_df = result['universal_data'] if hasattr(result, 'universal_data') else result.universal_data
    
    boundary_universal = universal_df.slice(8, 6).select(['segment_number', 'current_a'])
    
    print("\nUniversal schema current_a values:")
    for i, row in enumerate(boundary_universal.iter_rows(named=True)):
        row_num = 8 + i
        segment = row['segment_number']
        current_a = row['current_a']
        
        print(f"Row {row_num}: segment={segment}, current_a={current_a:10.6f}")
    
    print(f"\n=== THE INSIGHT ===")
    print("For Rest phases (mode 3):")
    print("- control_I should be nan (control not active) ✓")
    print("- BUT current_a should be the actual measured current from 'I' column")
    print("- The 'I' column always contains the real measured current")
    
    # Check if the mapping is using the wrong column
    print(f"\nCompare raw 'I' vs universal 'current_a':")
    raw_I = raw_df.slice(8, 6)['I'].to_list()
    univ_I = boundary_universal['current_a'].to_list()
    
    for i in range(6):
        row_num = 8 + i
        print(f"Row {row_num}: raw_I={raw_I[i]:8.6f}, universal_current_a={univ_I[i]:8.6f}")
        if abs(raw_I[i] - univ_I[i]) > 0.001:
            print(f"         ⚠️  MISMATCH! Universal schema not using raw I column")

if mpr_file.exists():
    investigate_current_columns()
else:
    print(f"❌ File not found: {mpr_file}")