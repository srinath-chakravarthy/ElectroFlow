#!/usr/bin/env python3
"""Debug segment 2 mixed control issue - CC-CV step analysis."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Current MB file
mb_file = Path("/Users/srinathchakravarthy/Desktop/AR-3753_3_electrode_full_GITT_EIS_0_04_MB_C06.mpr")

def debug_segment2_mixed_control():
    """Analyze segment 2 for mixed control (CC-CV) patterns."""
    
    parser = BiologicParser()
    
    # Get raw data with our segmentation
    raw_df = parser.mpr_reader.parse_mpr_file(mb_file)
    
    # Apply segmentation
    segmented_df = raw_df.with_columns([
        (pl.col('Ns') != pl.col('Ns').shift(1, fill_value=-1)).alias('ns_change'),
    ]).with_columns([
        (pl.col('ns_change').cast(pl.Int32).cum_sum()).alias('segment_number')
    ])
    
    print("=== SEGMENT 2 MIXED CONTROL ANALYSIS ===\n")
    
    # Extract segment 2 data
    segment_2 = segmented_df.filter(pl.col('segment_number') == 2)
    total_rows = len(segment_2)
    
    print(f"Segment 2 total rows: {total_rows}")
    print(f"Segment 2 Ns value: {segment_2['Ns'][0]}")
    
    # Analyze modes and flags throughout segment 2
    print(f"\n=== MODE AND FLAG ANALYSIS ===")
    
    # Get unique mode/flag combinations
    mode_flag_analysis = segment_2.with_columns([
        (pl.col('flags') & 0b00000011).alias('mode')
    ]).select(['mode', 'flags', 'control_I', 'control_V']).unique().sort(['flags'])
    
    print("Unique mode/flag combinations in segment 2:")
    print(mode_flag_analysis)
    
    # Check distribution of modes
    mode_counts = segment_2.with_columns([
        (pl.col('flags') & 0b00000011).alias('mode')
    ]).group_by('mode').agg([
        pl.count().alias('count'),
        pl.col('control_I').is_null().sum().alias('control_I_nan_count'),
        pl.col('control_V').is_null().sum().alias('control_V_nan_count')
    ]).sort('mode')
    
    print(f"\nMode distribution in segment 2:")
    print(mode_counts)
    
    # Look for the transition point where control_I becomes NaN
    print(f"\n=== FINDING NaN TRANSITION POINT ===")
    
    # Find where control_I changes from valid to NaN
    control_i_values = segment_2['control_I'].to_list()
    flags_values = segment_2['flags'].to_list()
    
    transition_point = None
    for i in range(1, len(control_i_values)):
        prev_val = control_i_values[i-1]
        curr_val = control_i_values[i]
        
        # Check if transition from valid to NaN
        if not (str(prev_val) == 'nan') and str(curr_val) == 'nan':
            transition_point = i
            break
    
    if transition_point:
        print(f"Control_I becomes NaN at row {transition_point} of segment 2")
        
        # Look around the transition point
        start_idx = max(0, transition_point - 5)
        end_idx = min(len(segment_2), transition_point + 5)
        
        print(f"\nTransition context (rows {start_idx} to {end_idx-1}):")
        print("Row | Flags | Mode | Control_I | Control_V | I_column")
        print("----|-------|------|-----------|-----------|----------")
        
        for i in range(start_idx, end_idx):
            flags = flags_values[i]
            mode = flags & 0b00000011
            control_i = control_i_values[i]
            control_v = segment_2['control_V'][i]
            i_col = segment_2['I'][i] if 'I' in segment_2.columns else 'N/A'
            
            control_i_str = "nan" if str(control_i) == 'nan' else f"{control_i:.3f}"
            control_v_str = "nan" if str(control_v) == 'nan' else f"{control_v:.3f}"
            i_col_str = "nan" if str(i_col) == 'nan' else f"{i_col:.3f}"
            
            marker = " ←← TRANSITION" if i == transition_point else ""
            
            print(f"{i:3d} | {flags:5d} | {mode:4d} | {control_i_str:9s} | {control_v_str:9s} | {i_col_str:9s}{marker}")
    
    # Check if this is CC-CV by looking at control patterns
    print(f"\n=== CC-CV DETECTION ===")
    
    valid_control_i_count = segment_2.filter(pl.col('control_I').is_not_null()).shape[0] 
    valid_control_v_count = segment_2.filter(pl.col('control_V').is_not_null()).shape[0]
    
    print(f"Rows with valid control_I: {valid_control_i_count}")
    print(f"Rows with valid control_V: {valid_control_v_count}")
    
    if valid_control_i_count > 0 and valid_control_v_count > 0:
        print("✅ CONFIRMED: Segment 2 is mixed control (CC-CV)")
        print("Problem: Our control splitting logic can't handle mode transitions within a segment")
    else:
        print("❓ Not clearly CC-CV, investigating other patterns...")
        
        # Check actual I column values where control_I is NaN
        nan_section = segment_2.filter(pl.col('control_I').is_null())
        if len(nan_section) > 0:
            i_values_in_nan_section = nan_section['I']
            i_stats = {
                'min': i_values_in_nan_section.min(),
                'max': i_values_in_nan_section.max(),
                'mean': i_values_in_nan_section.mean()
            }
            print(f"I column stats where control_I is NaN: {i_stats}")

if mb_file.exists():
    debug_segment2_mixed_control()
else:
    print(f"❌ File not found: {mb_file}")