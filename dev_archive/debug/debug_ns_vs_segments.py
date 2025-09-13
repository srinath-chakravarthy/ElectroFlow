#!/usr/bin/env python3
"""Debug Ns vs segment_number mismatch in MB file."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Current MB file
mb_file = Path("/Users/srinathchakravarthy/Desktop/AR-3753_3_electrode_full_GITT_EIS_0_04_MB_C06.mpr")

def debug_ns_vs_segments():
    """Compare raw Ns values vs calculated segment_number."""
    
    parser = BiologicParser()
    
    # Get raw data (no segmentation yet)
    raw_df = parser.mpr_reader.parse_mpr_file(mb_file)
    print("=== RAW DATA ANALYSIS ===")
    print(f"Raw data shape: {raw_df.shape}")
    print(f"Raw columns: {raw_df.columns}")
    
    # Check raw Ns values
    raw_ns_values = raw_df['Ns'].unique().sort().to_list()
    print(f"Raw Ns values: {raw_ns_values}")
    print(f"Number of unique Ns: {len(raw_ns_values)}")
    
    # Apply our segmentation logic manually to see what happens
    print(f"\n=== OUR SEGMENTATION LOGIC ===")
    
    # This is the logic from _add_segment_numbers_to_raw_data()
    segmented_df = raw_df.with_columns([
        # Detect Ns changes
        (pl.col('Ns') != pl.col('Ns').shift(1, fill_value=-1)).alias('ns_change'),
    ]).with_columns([
        # Create segment numbers (1-based)
        (pl.col('ns_change').cast(pl.Int32).cum_sum()).alias('segment_number')
    ])
    
    # Check our calculated segment numbers
    our_segment_values = segmented_df['segment_number'].unique().sort().to_list()
    print(f"Our segment_number values: {our_segment_values}")
    print(f"Number of our segments: {len(our_segment_values)}")
    
    print(f"\n=== COMPARISON ===")
    print(f"Raw Ns count: {len(raw_ns_values)}")
    print(f"Our segment count: {len(our_segment_values)}")
    print(f"Match: {len(raw_ns_values) == len(our_segment_values)}")
    
    # Look at transitions in detail
    print(f"\n=== DETAILED TRANSITIONS ===")
    
    # Find all Ns transitions
    transitions = []
    for i in range(1, len(raw_df)):
        if raw_df['Ns'][i] != raw_df['Ns'][i-1]:
            transitions.append(i)
    
    print(f"Found {len(transitions)} Ns transitions at rows: {transitions[:10]}...")
    
    # Check first few transitions
    print(f"\nFirst 10 transitions:")
    print("Row | Prev_Ns | New_Ns | Our_Segment | Current_A | Flags")
    print("----|---------|--------|-------------|-----------|-------")
    
    for i, trans_row in enumerate(transitions[:10]):
        if trans_row < len(segmented_df):
            prev_ns = raw_df['Ns'][trans_row-1]
            new_ns = raw_df['Ns'][trans_row]
            our_seg = segmented_df['segment_number'][trans_row]
            
            # Check if current exists
            current_val = "N/A"
            if 'control_I' in segmented_df.columns:
                current_val = f"{segmented_df['control_I'][trans_row]:.3f}"
            
            flags = raw_df['flags'][trans_row]
            
            print(f"{trans_row:3d} | {prev_ns:7d} | {new_ns:6d} | {our_seg:11d} | {current_val:9s} | {flags:5d}")
    
    # Check for the specific issue: segment 2 with nan current in last rows
    print(f"\n=== SEGMENT 2 CURRENT VALUES ===")
    segment_2_data = segmented_df.filter(pl.col('segment_number') == 2)
    
    if len(segment_2_data) > 0:
        total_rows = len(segment_2_data)
        print(f"Segment 2 total rows: {total_rows}")
        
        # Check if we have current values
        if 'control_I' in segment_2_data.columns:
            control_i_values = segment_2_data['control_I']
            nan_count = control_i_values.is_null().sum()
            print(f"Segment 2 control_I nan count: {nan_count}")
            
            # Look at last 250 rows
            if total_rows >= 250:
                last_250 = segment_2_data.tail(250)['control_I']
                last_250_nan = last_250.is_null().sum() 
                print(f"Last 250 rows nan count: {last_250_nan}")
                
                # Show pattern of last few rows
                print(f"\nLast 10 rows of segment 2:")
                last_10 = segment_2_data.tail(10).select(['Ns', 'segment_number', 'control_I', 'flags'])
                print(last_10)

if mb_file.exists():
    debug_ns_vs_segments()
else:
    print(f"❌ File not found: {mb_file}")