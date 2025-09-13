#!/usr/bin/env python3
"""Test control_V mapping patterns in BioLogic data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Current MB file
mb_file = Path("/Users/srinathchakravarthy/Desktop/AR-3753_3_electrode_full_GITT_EIS_0_04_MB_C06.mpr")

def test_control_v_patterns():
    """Test what control_V values exist and their patterns."""
    
    parser = BiologicParser()
    
    # Get raw data with control columns
    raw_df = parser.mpr_reader.parse_mpr_file(mb_file)
    
    print("=== CONTROL_V MAPPING ANALYSIS ===\n")
    print(f"Raw data shape: {raw_df.shape}")
    print(f"Raw columns: {raw_df.columns}")
    
    # Check if control_V exists
    if 'control_V' in raw_df.columns:
        control_v_stats = {
            'total_rows': len(raw_df),
            'non_null_count': raw_df['control_V'].count(),
            'null_count': raw_df['control_V'].null_count(),
            'unique_values': len(raw_df['control_V'].unique()),
            'min': raw_df['control_V'].min(),
            'max': raw_df['control_V'].max(),
            'mean': raw_df['control_V'].mean()
        }
        
        print(f"control_V statistics:")
        for key, value in control_v_stats.items():
            print(f"  {key}: {value}")
        
        # Check patterns by mode
        print(f"\n=== CONTROL_V BY MODE ===")
        
        mode_analysis = raw_df.with_columns([
            (pl.col('flags') & 0b00000011).alias('mode')
        ]).group_by('mode').agg([
            pl.count().alias('count'),
            pl.col('control_V').is_not_null().sum().alias('control_V_valid'),
            pl.col('control_V').is_null().sum().alias('control_V_null'),
            pl.col('control_V').min().alias('control_V_min'),
            pl.col('control_V').max().alias('control_V_max'),
        ]).sort('mode')
        
        print("Mode analysis:")
        print(mode_analysis)
        
        # Look at potential columns that might map to control_V
        print(f"\n=== POTENTIAL MAPPING CANDIDATES ===")
        
        potential_columns = [col for col in raw_df.columns if 'ewe' in col.lower() or 'potential' in col.lower() or 'voltage' in col.lower()]
        print(f"Potential-related columns: {potential_columns}")
        
        # Check if we have Ewe values where control_V is valid
        if 'Ewe' in raw_df.columns:
            cv_valid_data = raw_df.filter(pl.col('control_V').is_not_null())
            if len(cv_valid_data) > 0:
                print(f"\nWhere control_V is valid ({len(cv_valid_data)} rows):")
                print(f"  control_V range: {cv_valid_data['control_V'].min():.6f} to {cv_valid_data['control_V'].max():.6f}")
                print(f"  Ewe range: {cv_valid_data['Ewe'].min():.6f} to {cv_valid_data['Ewe'].max():.6f}")
                
                # Sample values
                sample = cv_valid_data.head(10).select(['control_V', 'Ewe', 'flags'])
                print(f"\nSample values:")
                print(sample)
        
    else:
        print("❌ control_V column not found in raw data")
    
    # Check current universal schema mapping for comparison
    print(f"\n=== CURRENT UNIVERSAL SCHEMA MAPPING ===")
    
    from src_clean.parsers.configs.biologic_mappings import BIOLOGIC_TO_UNIVERSAL_MAPPING
    
    mapped_columns = []
    unmapped_columns = []
    
    for col in raw_df.columns:
        if col in BIOLOGIC_TO_UNIVERSAL_MAPPING:
            mapped_columns.append(f"{col} -> {BIOLOGIC_TO_UNIVERSAL_MAPPING[col]}")
        else:
            unmapped_columns.append(col)
    
    print("Mapped columns:")
    for mapping in mapped_columns:
        print(f"  {mapping}")
    
    print(f"\nUnmapped columns ({len(unmapped_columns)}):")
    for col in unmapped_columns[:10]:  # Show first 10
        print(f"  {col}")
    if len(unmapped_columns) > 10:
        print(f"  ... and {len(unmapped_columns) - 10} more")

if mb_file.exists():
    test_control_v_patterns()
else:
    print(f"❌ File not found: {mb_file}")