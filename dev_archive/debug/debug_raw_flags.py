#!/usr/bin/env python3
"""Examine raw flags patterns to understand BioLogic flag meanings."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr")

def analyze_raw_flags():
    """Analyze raw flags by looking at the patterns."""
    
    # Use the intercept approach from before to get raw data
    class DebugMPRReader:
        def __init__(self):
            from src_clean.parsers.mpr_reader import MPRReader
            self.reader = MPRReader(debug=False)
            
        def get_raw_data(self, file_path):
            original_split = self.reader._split_control_column
            raw_data = {}
            
            def intercept_split(data_dict):
                raw_data.update(data_dict)
                return original_split(data_dict)
            
            self.reader._split_control_column = intercept_split
            self.reader.parse_mpr_file(file_path)
            return raw_data
    
    debug_reader = DebugMPRReader()
    raw_data = debug_reader.get_raw_data(mpr_file)
    
    print("=== RAW FLAG ANALYSIS ===\n")
    
    # Get first 100 flag values and their contexts
    flags = raw_data['flags'][:100]
    ns_values = raw_data['Ns'][:100]
    i_values = raw_data['I'][:100]
    control_values = raw_data['control'][:100]
    
    # Find unique flag patterns
    unique_flags = sorted(set(flags))
    print(f"Unique flag values in first 100 rows: {unique_flags}")
    
    print(f"\n=== FLAG BREAKDOWN ===")
    for flag_val in unique_flags:
        binary = f"{flag_val:08b}"
        
        # Different bit interpretations
        yadg_mode = flag_val & 0b00000011      # Bits 0-1 (YADG's "mode")
        bit2 = (flag_val & 0b00000100) >> 2   # Bit 2
        bit3 = (flag_val & 0b00001000) >> 3   # Bit 3  
        bit4 = (flag_val & 0b00010000) >> 4   # Bit 4
        bit5 = (flag_val & 0b00100000) >> 5   # Bit 5
        
        print(f"Flag {flag_val:3d} = 0b{binary}")
        print(f"  YADG mode (bits 0-1): {yadg_mode}")
        print(f"  Individual bits: [5]={bit5} [4]={bit4} [3]={bit3} [2]={bit2}")
    
    print(f"\n=== CORRELATION WITH PHYSICAL REALITY ===")
    
    # Group data by flag and see what happens
    flag_contexts = {}
    for i in range(len(flags)):
        flag = flags[i]
        if flag not in flag_contexts:
            flag_contexts[flag] = {'ns': [], 'currents': [], 'controls': []}
        
        flag_contexts[flag]['ns'].append(ns_values[i])
        flag_contexts[flag]['currents'].append(i_values[i])
        flag_contexts[flag]['controls'].append(control_values[i])
    
    for flag_val in unique_flags[:6]:  # First 6 flags
        context = flag_contexts[flag_val]
        
        # Analyze currents for this flag
        currents = context['currents']
        controls = context['controls'] 
        ns_vals = set(context['ns'])
        
        zero_count = sum(1 for i in currents if abs(i) < 0.001)
        nonzero_count = len(currents) - zero_count
        
        avg_current = sum(abs(i) for i in currents) / len(currents) if currents else 0
        avg_control = sum(abs(c) for c in controls) / len(controls) if controls else 0
        
        yadg_mode = flag_val & 0b00000011
        
        print(f"\nFlag {flag_val} (0b{flag_val:08b}) - YADG mode {yadg_mode}:")
        print(f"  Occurs in Ns: {sorted(ns_vals)}")
        print(f"  Currents: {zero_count} zero, {nonzero_count} non-zero (avg: {avg_current:.3f}mA)")
        print(f"  Controls: avg {avg_control:.3f}")
        
        # Pattern recognition
        if zero_count == len(currents):
            print(f"  → This flag = ZERO CURRENT ONLY (Rest/OCV)")
            if yadg_mode in {1, 3}:
                print(f"    ⚠️  YADG thinks galvanostatic but all currents are zero!")
        elif nonzero_count == len(currents):
            print(f"  → This flag = NON-ZERO CURRENT ONLY (Active control)")
        else:
            print(f"  → This flag = MIXED CURRENTS (Transition?)")
    
    print(f"\n=== OUR SPECIFIC BOUNDARY PROBLEM ===")
    
    # Focus on our boundary rows (8-13)
    print("Boundary rows 8-13:")
    for row_num in range(8, 14):
        if row_num < len(flags):
            flag = flags[row_num]
            ns = ns_values[row_num]
            current = i_values[row_num]
            control = control_values[row_num]
            
            yadg_mode = flag & 0b00000011
            is_zero = abs(current) < 0.001
            
            print(f"Row {row_num}: flag={flag:3d}(0b{flag:08b}) Ns={ns} I={current:8.3f} control={control:8.3f}")
            
            # The key insight
            if is_zero and yadg_mode in {1, 3}:
                print(f"         ❌ YADG WRONG: Zero current but mode={yadg_mode} (galvanostatic)")
            elif not is_zero and yadg_mode == 2:
                print(f"         ❌ YADG WRONG: Non-zero current but mode={yadg_mode} (potentiostatic)")
            else:
                print(f"         ✓ YADG OK: Current pattern matches mode={yadg_mode}")

if mpr_file.exists():
    analyze_raw_flags()
else:
    print(f"❌ File not found: {mpr_file}")