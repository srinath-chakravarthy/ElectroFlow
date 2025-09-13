#!/usr/bin/env python3
"""Test control_V fallback candidates in BioLogic data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Current MB file
mb_file = Path("/Users/srinathchakravarthy/Desktop/AR-3753_3_electrode_full_GITT_EIS_0_04_MB_C06.mpr")

def test_control_v_fallbacks():
    """Test potential fallback candidates for control_V mapping."""
    
    parser = BiologicParser()
    raw_df = parser.mpr_reader.parse_mpr_file(mb_file)
    
    print("=== CONTROL_V FALLBACK ANALYSIS ===\n")
    
    # Focus on mode 2 (potentiostatic) where control_V should be valid
    mode2_data = raw_df.with_columns([
        (pl.col('flags') & 0b00000011).alias('mode')
    ]).filter(pl.col('mode') == 2)
    
    print(f"Mode 2 (Potentiostatic) data: {len(mode2_data)} rows")
    
    if len(mode2_data) > 0:
        # Compare control_V with potential candidates
        print(f"\n=== POTENTIOSTATIC PHASE ANALYSIS ===")
        
        candidates = ['control_V', 'Ewe', '<Ewe>']
        available_candidates = [col for col in candidates if col in mode2_data.columns]
        
        print(f"Available potential candidates: {available_candidates}")
        
        # Statistical comparison
        stats_df = mode2_data.select(available_candidates).describe()
        print(f"\nStatistics for potentiostatic phase:")
        print(stats_df)
        
        # Sample values for pattern analysis
        print(f"\nFirst 20 potentiostatic phase values:")
        sample = mode2_data.head(20).select(['control_V', 'Ewe', '<Ewe>'] + 
                                          (['time', 'flags'] if 'time' in mode2_data.columns else []))
        print(sample)
        
        # Check if Ewe might be a reasonable fallback when control_V is invalid
        print(f"\n=== FALLBACK LOGIC TEST ===")
        
        # Test the fallback logic: use control_V if valid, else use Ewe
        fallback_test = mode2_data.with_columns([
            # Fallback logic: control_V preferred, Ewe as fallback
            pl.when(pl.col('control_V').is_not_null() & pl.col('control_V').is_not_nan())
            .then(pl.col('control_V'))
            .otherwise(pl.col('Ewe'))
            .alias('potential_applied_fallback')
        ]).select(['control_V', 'Ewe', 'potential_applied_fallback'])
        
        print("Fallback logic test (first 10 rows):")
        print(fallback_test.head(10))
        
        # Check how many would use fallback
        fallback_stats = mode2_data.with_columns([
            pl.col('control_V').is_not_null().alias('control_v_valid')
        ]).select([
            pl.col('control_v_valid').sum().alias('control_v_valid_count'),
            pl.len().alias('total_mode2_rows')
        ])
        
        print(f"\nFallback usage statistics:")
        print(fallback_stats)
        
    # Now check modes 1 and 3 for their Ewe patterns
    print(f"\n=== MODE 1 & 3 POTENTIAL PATTERNS ===")
    
    other_modes = raw_df.with_columns([
        (pl.col('flags') & 0b00000011).alias('mode')
    ]).filter(pl.col('mode').is_in([1, 3]))
    
    print(f"Modes 1&3 (Galvano/Rest) data: {len(other_modes)} rows")
    
    if len(other_modes) > 0:
        # Check Ewe distribution in these modes
        mode_ewe_stats = other_modes.group_by('mode').agg([
            pl.len().alias('count'),
            pl.col('Ewe').min().alias('ewe_min'),
            pl.col('Ewe').max().alias('ewe_max'),
            pl.col('Ewe').mean().alias('ewe_mean')
        ]).sort('mode')
        
        print("Ewe patterns in modes 1 & 3:")
        print(mode_ewe_stats)

if mb_file.exists():
    test_control_v_fallbacks()
else:
    print(f"❌ File not found: {mb_file}")