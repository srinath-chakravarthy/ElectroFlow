#!/usr/bin/env python3
"""Analyze current column patterns across BioLogic techniques."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Current MB file (we know this one works)
mb_file = Path("/Users/srinathchakravarthy/Desktop/AR-3753_3_electrode_full_GITT_EIS_0_04_MB_C06.mpr")

def analyze_technique_current_patterns():
    """Analyze current column patterns in our MB file by technique segments."""
    
    parser = BiologicParser()
    
    print("=== BIOLOGIC TECHNIQUE CURRENT ANALYSIS ===\n")
    
    # Get RAW data from MPR reader (parser level only!)
    try:
        raw_df = parser.mpr_reader.parse_mpr_file(mb_file)
        print(f"✅ Raw MPR data: {raw_df.shape}")
        print(f"Raw columns: {raw_df.columns}")
        
        # Check current-related columns in raw data
        current_cols = [col for col in raw_df.columns if 'current' in col.lower() or col == 'I']
        print(f"Current-related columns: {current_cols}")
        
    except Exception as e:
        print(f"❌ Failed to get raw data: {e}")
        return
    
    # Add basic segmentation for technique analysis
    segmented_df = raw_df.with_columns([
        (pl.col('Ns') != pl.col('Ns').shift(1, fill_value=-1)).alias('ns_change'),
    ]).with_columns([
        (pl.col('ns_change').cast(pl.Int32).cum_sum()).alias('segment_number')
    ])
    
    # Get unique segments and their Ns values to understand techniques
    segment_info = segmented_df.group_by(['segment_number', 'Ns']).agg([
        pl.len().alias('row_count'),
        (pl.col('flags') & 0b00000011).alias('modes').unique().sort()
    ]).sort('segment_number')
    
    print(f"\n=== SEGMENT-BASED TECHNIQUE ANALYSIS ===")
    print(f"Found {len(segment_info)} segments")
    print(f"First 10 segments:")
    print(segment_info.head(10))
    
    # Specific analysis: What happens in different modes?
    print(f"\n=== MODE-SPECIFIC CURRENT ANALYSIS ===")
    
    if 'flags' in raw_df.columns and 'I' in raw_df.columns and 'control_I' in raw_df.columns:
        mode_analysis = raw_df.with_columns([
            (pl.col('flags') & 0b00000011).alias('mode')
        ]).group_by('mode').agg([
            pl.len().alias('count'),
            pl.col('I').is_not_null().sum().alias('I_valid'),
            pl.col('control_I').is_not_null().sum().alias('control_I_valid'),
            pl.col('I').mean().alias('I_mean'),
            pl.col('control_I').mean().alias('control_I_mean'),
            pl.col('I').min().alias('I_min'),
            pl.col('I').max().alias('I_max'),
            pl.col('control_I').min().alias('control_I_min'),
            pl.col('control_I').max().alias('control_I_max')
        ]).sort('mode')
        
        print("Mode-specific I vs control_I patterns:")
        for row in mode_analysis.iter_rows(named=True):
            mode = row['mode']
            mode_name = {1: 'Galvanostatic', 2: 'Potentiostatic', 3: 'Rest/OCV'}.get(mode, f'Mode_{mode}')
            print(f"\n  {mode_name} (Mode {mode}): {row['count']} rows")
            print(f"    I column: {row['I_valid']}/{row['count']} valid, range {row['I_min']:.6f} to {row['I_max']:.6f} mA, mean {row['I_mean']:.6f}")
            print(f"    control_I: {row['control_I_valid']}/{row['count']} valid, range {row['control_I_min']:.6f} to {row['control_I_max']:.6f} mA, mean {row['control_I_mean']:.6f}")

if mb_file.exists():
    analyze_technique_current_patterns()
else:
    print(f"❌ File not found: {mb_file}")