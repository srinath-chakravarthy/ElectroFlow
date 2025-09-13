#!/usr/bin/env python3
"""Examine actual flags patterns to understand what they really mean."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

def analyze_flag_patterns():
    """Analyze flag patterns to understand what they really mean."""
    
    parser = BiologicParser()
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    print("=== FLAG PATTERN ANALYSIS ===\n")
    
    # Get all unique flag values and their contexts
    flag_analysis = raw_df.select(['Ns', 'flags', 'I', 'control', 'Ewe']).head(100)  # First 100 rows
    
    print("All unique flag values in first 100 rows:")
    unique_flags = flag_analysis['flags'].unique().sort().to_list()
    print(f"Unique flags: {unique_flags}")
    
    for flag_val in unique_flags:
        binary = f"{flag_val:08b}"
        bit0_1 = flag_val & 0b00000011  # YADG's "mode"
        bit2 = (flag_val & 0b00000100) >> 2
        bit3 = (flag_val & 0b00001000) >> 3
        bit4 = (flag_val & 0b00010000) >> 4
        bit5 = (flag_val & 0b00100000) >> 5
        print(f"  Flag {flag_val:3d} = 0b{binary} → bits[1:0]={bit0_1}, bit2={bit2}, bit3={bit3}, bit4={bit4}, bit5={bit5}")
    
    print(f"\n=== FLAG CORRELATION WITH ACTUAL DATA ===")
    
    # Group by flag values and see what the data looks like
    for flag_val in unique_flags[:8]:  # First 8 flag values
        rows_with_flag = flag_analysis.filter(pl.col('flags') == flag_val)
        
        if len(rows_with_flag) > 0:
            # Get statistics for this flag
            ns_values = rows_with_flag['Ns'].unique().sort().to_list()
            i_values = rows_with_flag['I'].to_list()
            control_values = rows_with_flag['control'].to_list()
            
            # Classify currents
            zero_currents = sum(1 for i in i_values if abs(i) < 0.001)
            nonzero_currents = len(i_values) - zero_currents
            
            avg_i = sum(abs(i) for i in i_values) / len(i_values)
            avg_control = sum(abs(c) for c in control_values) / len(control_values)
            
            print(f"\nFlag {flag_val} (0b{flag_val:08b}):")
            print(f"  Appears in Ns: {ns_values}")
            print(f"  Current stats: {zero_currents} zero, {nonzero_currents} non-zero (avg: {avg_i:.3f}mA)")
            print(f"  Control stats: avg {avg_control:.3f}")
            print(f"  YADG mode: {flag_val & 0b00000011}")
            
            # Show pattern
            if zero_currents == len(i_values):
                print(f"  → Pattern: ALL ZERO CURRENT (likely Rest phase)")
            elif nonzero_currents == len(i_values):
                print(f"  → Pattern: ALL NON-ZERO CURRENT (likely Active phase)")
            else:
                print(f"  → Pattern: MIXED CURRENT (likely Transition)")
    
    print(f"\n=== SPECIFIC BOUNDARY ANALYSIS ===")
    
    # Look at our specific problem area (rows 8-13)
    boundary_data = raw_df.slice(8, 6).select(['Ns', 'flags', 'I', 'control'])
    
    print("Our problematic boundary (rows 8-13):")
    for i, row in enumerate(boundary_data.iter_rows(named=True)):
        row_num = 8 + i
        flag = row['flags']
        ns = row['Ns']
        current = row['I']
        control = row['control']
        
        binary = f"{flag:08b}"
        yadg_mode = flag & 0b00000011
        
        # Physical reality check
        is_rest = abs(current) < 0.001
        phase_type = "REST" if is_rest else "ACTIVE"
        
        print(f"Row {row_num}: flag={flag}(0b{binary}) Ns={ns} I={current:.3f} → {phase_type}")
        print(f"         YADG says mode={yadg_mode}, control={control:.3f}")
        
        # What should the flag mean?
        if is_rest and yadg_mode in {1, 3}:
            print(f"         ⚠️  CONTRADICTION: Rest phase but YADG thinks galvanostatic")
        elif not is_rest and yadg_mode == 2:
            print(f"         ⚠️  CONTRADICTION: Active phase but YADG thinks potentiostatic")
        else:
            print(f"         ✓ Consistent")

if mpr_file.exists():
    analyze_flag_patterns()
else:
    print(f"❌ File not found: {mpr_file}")