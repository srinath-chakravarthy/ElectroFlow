#!/usr/bin/env python3
"""Check the next transition in GCPL data to confirm the pattern."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser

# GCPL file
gcpl_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr")

def debug_next_transition():
    """Find and analyze the next transition in GCPL data."""
    
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
    
    print("=== FINDING NEXT TRANSITION ===\n")
    
    flags = raw_data['flags']
    control = raw_data['control']
    ns_values = raw_data['Ns']
    time_values = raw_data['time']
    
    # Find the CC->Rest transition (Ns=1 to Ns=0) around row 145
    cc_to_rest_transition = None
    
    for i in range(1, len(ns_values)):
        if ns_values[i-1] == 1 and ns_values[i] == 0:
            cc_to_rest_transition = i
            print(f"CC->Rest transition at row {i}: Ns {ns_values[i-1]} -> {ns_values[i]}")
            break
    
    if cc_to_rest_transition is None:
        print("No CC->Rest transition found in data")
        return
    
    print(f"\n=== CC->REST TRANSITION ANALYSIS ===")
    # Look at rows around the CC->Rest transition
    start_idx = max(0, cc_to_rest_transition - 5)
    end_idx = min(len(flags), cc_to_rest_transition + 5)
    
    print(f"Analyzing rows {start_idx} to {end_idx-1} around CC->Rest transition:")
    print("Row | Ns |      time      | flags | hex  | binary   | mode | control")
    print("----|----|----|-----------|------|------|----------|------|--------")
    
    for i in range(start_idx, end_idx):
        flag_val = flags[i]
        control_val = control[i]
        ns = ns_values[i]
        time_val = time_values[i]
        mode = int(flag_val) & 0b00000011
        hex_val = f"0x{flag_val:02X}"
        binary_val = f"{flag_val:08b}"
        
        # Check for transition artifacts
        marker = ""
        if i > 0:
            prev_flag = flags[i-1]
            prev_mode = int(prev_flag) & 0b00000011
            if mode == prev_mode and flag_val != prev_flag:
                marker = " ←← TRANSITION ARTIFACT"
        
        print(f"{i:3d} | {ns:2d} | {time_val:15.6f} | {flag_val:3d} | {hex_val:4s} | {binary_val} | {mode:4d} | {control_val:8.3f}{marker}")
    
    # Now find and analyze Rest->CC transition 
    rest_to_cc_start = None
    for i in range(cc_to_rest_transition + 1, len(ns_values)):
        if ns_values[i-1] == 0 and ns_values[i] == 1:
            rest_to_cc_start = i
            print(f"\nRest->CC transition at row {i}: Ns {ns_values[i-1]} -> {ns_values[i]}")
            break
    
    if rest_to_cc_start:
        print(f"\n=== REST->CC TRANSITION ANALYSIS ===")
        # Look at rows around the Rest->CC transition
        start_idx = max(0, rest_to_cc_start - 5)
        end_idx = min(len(flags), rest_to_cc_start + 5)
        
        print(f"Analyzing rows {start_idx} to {end_idx-1} around Rest->CC transition:")
        print("Row | Ns |      time      | flags | hex  | binary   | mode | control")
        print("----|----|----|-----------|------|------|----------|------|--------")
        
        for i in range(start_idx, end_idx):
            flag_val = flags[i]
            control_val = control[i]
            ns = ns_values[i]
            time_val = time_values[i]
            mode = int(flag_val) & 0b00000011
            hex_val = f"0x{flag_val:02X}"
            binary_val = f"{flag_val:08b}"
            
            # Check for transition artifacts
            marker = ""
            if i > 0:
                prev_flag = flags[i-1]
                prev_mode = int(prev_flag) & 0b00000011
                if mode == prev_mode and flag_val != prev_flag:
                    marker = " ←← TRANSITION ARTIFACT"
            
            print(f"{i:3d} | {ns:2d} | {time_val:15.6f} | {flag_val:3d} | {hex_val:4s} | {binary_val} | {mode:4d} | {control_val:8.3f}{marker}")
    
    print(f"\n=== PATTERN ANALYSIS ===")
    print("Looking for:")
    print("1. Same mode but different flag (transition artifact)")
    print("2. Does transition artifact use NEXT segment's control value?")

if gcpl_file.exists():
    debug_next_transition()
else:
    print(f"❌ File not found: {gcpl_file}")