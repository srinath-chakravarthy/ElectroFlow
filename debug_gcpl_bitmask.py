#!/usr/bin/env python3
"""Debug GCPL bitmask patterns to understand the transition issue."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser

# GCPL file
gcpl_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr")

def debug_gcpl_bitmasks():
    """Debug the bitmask patterns around transitions."""
    
    # Use the intercept approach to get raw data before control splitting
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
    raw_data = debug_reader.get_raw_data(gcpl_file)
    
    print("=== GCPL BITMASK ANALYSIS ===\n")
    
    # Look at first 20 rows around the transition
    flags = raw_data['flags'][:20]
    control = raw_data['control'][:20]
    ns_values = raw_data['Ns'][:20]
    time_values = raw_data['time'][:20]
    
    print("Row | Ns |      time      | flags | hex    | binary   | mode | control")
    print("----|----|----|-----------|------|----------|------|--------")
    
    for i in range(len(flags)):
        flag_val = flags[i]
        control_val = control[i]
        ns = ns_values[i]
        time_val = time_values[i]
        mode = int(flag_val) & 0b00000011
        hex_val = f"0x{flag_val:02X}"
        binary_val = f"{flag_val:08b}"
        
        # Highlight the problem row
        marker = " ←← PROBLEM!" if i == 6 else ""
        
        print(f"{i:3d} | {ns:2d} | {time_val:15.6f} | {flag_val:3d} | {hex_val:6s} | {binary_val} | {mode:4d} | {control_val:8.3f}{marker}")
    
    print(f"\n=== BIT ANALYSIS FOR PROBLEM ROW 6 ===")
    problem_flag = flags[6]
    print(f"Flag value: {problem_flag}")
    print(f"Hex: 0x{problem_flag:02X}")
    print(f"Binary: {problem_flag:08b}")
    print(f"Mode (bits 0-1): {problem_flag & 0b00000011}")
    print(f"Bit 2: {(problem_flag & 0b00000100) >> 2}")
    print(f"Bit 3: {(problem_flag & 0b00001000) >> 3}")
    print(f"Bit 4: {(problem_flag & 0b00010000) >> 4}")
    print(f"Bit 5: {(problem_flag & 0b00100000) >> 5}")
    print(f"Bit 6: {(problem_flag & 0b01000000) >> 6}")
    print(f"Bit 7: {(problem_flag & 0b10000000) >> 7}")
    
    print(f"\n=== COMPARISON WITH NORMAL REST (Row 0) ===")
    normal_flag = flags[0]
    print(f"Normal Rest Flag: {normal_flag} (0x{normal_flag:02X}, {normal_flag:08b})")
    print(f"Problem Flag:     {problem_flag} (0x{problem_flag:02X}, {problem_flag:08b})")
    print(f"Difference:       {problem_flag - normal_flag} (different bits)")

if gcpl_file.exists():
    debug_gcpl_bitmasks()
else:
    print(f"❌ File not found: {gcpl_file}")