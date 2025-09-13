#!/usr/bin/env python3
"""Debug GCPL transition from Rest -> CC to find the offset issue."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser

# GCPL file
gcpl_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr")

def debug_gcpl_transitions():
    """Debug the Rest -> CC transitions in GCPL file."""
    
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
    
    print("=== GCPL TRANSITION DEBUG ===\n")
    
    # Look at first 20 rows around the transition
    flags = raw_data['flags'][:20]
    control = raw_data['control'][:20]
    ns_values = raw_data['Ns'][:20]
    
    print("Raw data around Rest -> CC transition:")
    print("Row | Ns | flags | mode | control")
    print("----|----|----|------|--------")
    
    for i in range(len(flags)):
        flag_val = flags[i]
        control_val = control[i]
        ns = ns_values[i]
        mode = int(flag_val) & 0b00000011
        
        print(f"{i:3d} | {ns:2d} | {flag_val:3d} | {mode:4d} | {control_val:8.3f}")
    
    print(f"\n=== WHAT HAPPENS WITH OLD YADG LOGIC ===")
    print("For GCPL files, modes 1 and 3 both use control_val as current:")
    
    for i in range(len(flags)):
        flag_val = flags[i]
        control_val = control[i]
        ns = ns_values[i]
        mode = int(flag_val) & 0b00000011
        
        # Apply old YADG logic
        if mode in {1, 3}:  # Old logic: both galvanostatic
            current_assignment = f"control_I = {control_val:.3f}"
        elif mode == 2:
            current_assignment = "control_V = control_val"
        else:
            current_assignment = "nan"
            
        transition = ""
        if i > 0 and ns_values[i] != ns_values[i-1]:
            transition = " ← TRANSITION"
            
        print(f"Row {i:2d}: Ns={ns} mode={mode} → {current_assignment}{transition}")

if gcpl_file.exists():
    debug_gcpl_transitions()
else:
    print(f"❌ File not found: {gcpl_file}")