#!/usr/bin/env python3
"""Check MB file transitions to see if they have the same pattern as GCPL."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser

# MB file
mb_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

def debug_mb_transitions():
    """Check MB file transitions around first few Ns changes."""
    
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
    raw_data = debug_reader.get_raw_data(mb_file)
    
    print("=== MB FILE TRANSITION ANALYSIS ===\n")
    
    flags = raw_data['flags']
    control = raw_data['control']
    ns_values = raw_data['Ns']
    time_values = raw_data['time']
    i_values = raw_data['I']  # MB files have I column
    
    print("MB file has I column:", 'I' in raw_data)
    print("First few Ns values:", ns_values[:20])
    
    # Find first few transitions
    transitions = []
    for i in range(1, min(100, len(ns_values))):  # Check first 100 rows
        if ns_values[i] != ns_values[i-1]:
            transitions.append((i, ns_values[i-1], ns_values[i]))
            if len(transitions) >= 3:  # Get first 3 transitions
                break
    
    print(f"\nFound {len(transitions)} transitions:")
    for i, (row, from_ns, to_ns) in enumerate(transitions):
        print(f"{i+1}. Row {row}: Ns {from_ns} -> {to_ns}")
    
    # Analyze each transition
    for i, (transition_row, from_ns, to_ns) in enumerate(transitions):
        print(f"\n=== TRANSITION {i+1}: Ns {from_ns} -> {to_ns} (Row {transition_row}) ===")
        
        # Look at rows around this transition
        start_idx = max(0, transition_row - 3)
        end_idx = min(len(flags), transition_row + 3)
        
        print("Row | Ns |      time      | flags | hex  | binary   | mode | control |    I    ")
        print("----|----|----|-----------|------|------|----------|------|---------|--------")
        
        for j in range(start_idx, end_idx):
            flag_val = flags[j]
            control_val = control[j]
            ns = ns_values[j]
            time_val = time_values[j]
            i_val = i_values[j]
            mode = int(flag_val) & 0b00000011
            hex_val = f"0x{flag_val:02X}"
            binary_val = f"{flag_val:08b}"
            
            # Check for transition artifacts
            marker = ""
            if j > 0:
                prev_flag = flags[j-1]
                prev_mode = int(prev_flag) & 0b00000011
                if mode == prev_mode and flag_val != prev_flag:
                    marker = " ←← TRANSITION ARTIFACT"
            
            print(f"{j:3d} | {ns:2d} | {time_val:15.6f} | {flag_val:3d} | {hex_val:4s} | {binary_val} | {mode:4d} | {control_val:8.3f} | {i_val:8.3f}{marker}")
    
    print(f"\n=== MB vs GCPL COMPARISON ===")
    print("Key questions:")
    print("1. Do MB files have the same transition artifact pattern?")
    print("2. Do we need the complex MB logic or can we use the simple previous-control fix?")
    print("3. Is the 'I' column already correct without our MB specialization?")

if mb_file.exists():
    debug_mb_transitions()
else:
    print(f"❌ File not found: {mb_file}")