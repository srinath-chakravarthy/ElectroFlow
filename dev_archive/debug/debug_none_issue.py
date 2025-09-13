#!/usr/bin/env python3
"""Debug the None segment_number issue in detail."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    parser = BiologicParser()
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    print("=== DEBUGGING None segment_number ISSUE ===\n")
    
    # Replicate the exact logic from _add_segment_numbers_to_raw_data
    print("Step 1: Raw Ns values (first 20 rows):")
    print(raw_df.select(['Ns']).head(20))
    
    print("\nStep 2: Apply shift(1) and mark changes:")
    test_df = raw_df.with_columns([
        pl.col('Ns').shift(1).alias('Ns_shifted'),
        (pl.col('Ns') != pl.col('Ns').shift(1)).alias('ns_change')
    ])
    
    print("First 20 rows showing shift logic:")
    print(test_df.select(['Ns', 'Ns_shifted', 'ns_change']).head(20))
    
    print("\nStep 3: Apply cumsum and +1:")
    test_df = test_df.with_columns([
        pl.col('ns_change').cast(pl.Int32).alias('ns_change_int'),
        pl.col('ns_change').cast(pl.Int32).cum_sum().alias('cum_sum'),
        (pl.col('ns_change').cast(pl.Int32).cum_sum() + 1).alias('segment_number_calc')
    ])
    
    print("First 20 rows showing cumsum logic:")
    print(test_df.select(['Ns', 'ns_change', 'ns_change_int', 'cum_sum', 'segment_number_calc']).head(20))
    
    print("\nStep 4: Check for None values:")
    none_count = test_df['segment_number_calc'].null_count()
    print(f"None values in segment_number_calc: {none_count}")
    
    if none_count > 0:
        print("Rows with None segment_number_calc:")
        none_rows = test_df.filter(pl.col('segment_number_calc').is_null())
        print(none_rows.select(['Ns', 'Ns_shifted', 'ns_change', 'cum_sum', 'segment_number_calc']).head(10))
    
    print("\nStep 5: Verify segment assignments:")
    # Check unique segment numbers
    unique_segments = test_df['segment_number_calc'].unique().sort()
    print(f"Unique segment numbers: {unique_segments.to_list()}")
    
    # Check first few segments in detail
    print("\nDetailed segment analysis:")
    for seg_num in [1, 2, 3]:
        if seg_num in unique_segments.to_list():
            seg_data = test_df.filter(pl.col('segment_number_calc') == seg_num)
            ns_values = seg_data['Ns'].unique().to_list()
            print(f"  Segment {seg_num}: {len(seg_data)} points, Ns values: {ns_values}")
    
    print("\nStep 6: Check boundary between Ns=0 and Ns=1:")
    # Find the exact row where Ns changes from 0 to 1
    ns_changes = test_df.with_row_count().filter(pl.col('ns_change') == True)
    print("Rows where Ns changes:")
    print(ns_changes.select(['row_nr', 'Ns', 'Ns_shifted', 'segment_number_calc']).head(10))
    
    # Check what happens at the Ns=0 to Ns=1 boundary
    transition_rows = test_df.with_row_count().slice(8, 8)  # Around the transition
    print(f"\nRows around Ns=0→Ns=1 transition:")
    print(transition_rows.select(['row_nr', 'Ns', 'Ns_shifted', 'ns_change', 'segment_number_calc', 'I']))
    
else:
    print(f"❌ File not found: {mpr_file}")