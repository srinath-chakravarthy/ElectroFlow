#!/usr/bin/env python3
"""Debug raw binary Ns values to see if the issue is in the instrument data or parsing."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    parser = BiologicParser()
    
    print("=== RAW BINARY NS INVESTIGATION ===\n")
    
    # Enable debug mode to see internal parser details
    parser.mpr_reader.debug = True
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    print("\n" + "="*50)
    print("FOCUSED TRANSITION ANALYSIS")
    print("="*50)
    
    # Look specifically at the boundary rows
    print("\nDetailed look at first 15 rows:")
    first_15 = raw_df.head(15).select(['Ns', 'time', 'I', 'Ewe'])
    
    for i, row in enumerate(first_15.iter_rows(named=True)):
        ns = row['Ns']
        time_val = row['time']
        current = row['I']
        voltage = row['Ewe']
        
        # Highlight the transition
        marker = " ← TRANSITION" if i > 0 and first_15[i-1, 'Ns'] != ns else ""
        print(f"Row {i:2d}: Ns={ns}, time={time_val:.3f}s, I={current:.6f}mA, Ewe={voltage:.6f}V{marker}")
    
    # Check if there's a pattern in the transitions
    print(f"\n" + "="*50)
    print("NS TRANSITION ANALYSIS")
    print("="*50)
    
    # Find all Ns transitions
    prev_ns = None
    transition_count = 0
    
    for i, ns in enumerate(raw_df['Ns'].to_list()[:50]):  # First 50 rows
        if prev_ns is not None and ns != prev_ns:
            transition_count += 1
            row_data = raw_df.slice(i-1, 3).select(['Ns', 'time', 'I'])  # 3 rows around transition
            print(f"\nTransition #{transition_count}: {prev_ns} → {ns} at row {i}")
            for j, trans_row in enumerate(row_data.iter_rows(named=True)):
                row_num = i-1+j
                marker = " ← CHANGE" if trans_row['Ns'] != prev_ns else ""
                print(f"  Row {row_num}: Ns={trans_row['Ns']}, I={trans_row['I']:.6f}mA{marker}")
        prev_ns = ns
    
    print(f"\n" + "="*50) 
    print("PHYSICAL INTERPRETATION")
    print("="*50)
    
    # The key question: should the first measurement with current be Ns=0 or Ns=1?
    print("\nKey Question: Which Ns should the first current-applying measurement belong to?")
    
    # Find first non-zero current
    first_nonzero_idx = None
    for i, current in enumerate(raw_df['I'].to_list()):
        if abs(current) > 0.001:  # 0.001 mA threshold
            first_nonzero_idx = i
            break
    
    if first_nonzero_idx is not None:
        context_rows = raw_df.slice(max(0, first_nonzero_idx-2), 5).select(['Ns', 'time', 'I'])
        print(f"\nContext around first non-zero current (row {first_nonzero_idx}):")
        for i, row in enumerate(context_rows.iter_rows(named=True)):
            actual_row = max(0, first_nonzero_idx-2) + i
            marker = " ← FIRST CURRENT" if abs(row['I']) > 0.001 and actual_row == first_nonzero_idx else ""
            print(f"  Row {actual_row}: Ns={row['Ns']}, I={row['I']:.6f}mA{marker}")
            
        # The critical question
        first_current_ns = raw_df[first_nonzero_idx, 'Ns']
        print(f"\n🔍 The first current-applying measurement has Ns={first_current_ns}")
        print("💭 QUESTION: Should this be Ns=0 (end of rest) or Ns=1 (start of CC)?")
        print("💭 EXPECTED: This should be Ns=1 (start of galvanostatic phase)")
        
        if first_current_ns == 0:
            print("❌ ISSUE: First current measurement is assigned to Ns=0 (Rest phase)")
            print("   This explains why Rest segment ends with CC current!")
        else:
            print("✅ OK: First current measurement is assigned to Ns=1+ (CC phase)")
            
else:
    print(f"❌ File not found: {mpr_file}")