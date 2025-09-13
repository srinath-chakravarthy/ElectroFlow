#!/usr/bin/env python3
"""Analyze current column patterns across all BioLogic technique types."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test files for different techniques
test_files = {
    'GCPL': Path("biologic_test_files/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr"),
    'PEIS': Path("biologic_test_files/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_06_PEIS_C05.mpr"), 
    'GEIS': Path("biologic_test_files/AR3677_3Electrode_GEIS_02_GEIS_C06.mpr"),
    'OCV': Path("biologic_test_files/AR3677_3Electrode_GEIS_01_OCV_C06.mpr"),
    'MB': Path("biologic_test_files/AR-3753_3_electrode_full_GITT_EIS_0_04_MB_C06.mpr")
}

def analyze_technique_file(technique_name: str, file_path: Path):
    """Analyze current patterns for a specific technique file."""
    
    print(f"\n{'='*60}")
    print(f"ANALYZING {technique_name} TECHNIQUE")
    print(f"File: {file_path.name}")
    print(f"{'='*60}")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    parser = BiologicParser()
    
    try:
        # Get raw data from MPR reader
        raw_df = parser.mpr_reader.parse_mpr_file(file_path)
        print(f"✅ Raw data: {raw_df.shape}")
        print(f"Columns: {raw_df.columns}")
        
        # Check current-related columns
        current_cols = [col for col in raw_df.columns if 'current' in col.lower() or col == 'I']
        print(f"Current-related columns: {current_cols}")
        
        # Check if we have the expected columns for current mapping
        has_I = 'I' in raw_df.columns
        has_control_I = 'control_I' in raw_df.columns 
        has_control_V = 'control_V' in raw_df.columns
        
        print(f"Column availability: I={has_I}, control_I={has_control_I}, control_V={has_control_V}")
        
        # Mode analysis if we have flags
        if 'flags' in raw_df.columns:
            mode_analysis = raw_df.with_columns([
                (pl.col('flags') & 0b00000011).alias('mode')
            ]).group_by('mode').agg([
                pl.len().alias('count')
            ]).sort('mode')
            
            print(f"Mode distribution:")
            for row in mode_analysis.iter_rows(named=True):
                mode = row['mode']
                mode_name = {1: 'Galvanostatic', 2: 'Potentiostatic', 3: 'Rest/OCV'}.get(mode, f'Mode_{mode}')
                print(f"  {mode_name} (Mode {mode}): {row['count']} rows")
        
        # Current value analysis by mode
        if has_I and 'flags' in raw_df.columns:
            print(f"\nCurrent value analysis by mode:")
            
            current_by_mode = raw_df.with_columns([
                (pl.col('flags') & 0b00000011).alias('mode')
            ]).group_by('mode').agg([
                pl.len().alias('count'),
                pl.col('I').min().alias('I_min'),
                pl.col('I').max().alias('I_max'),
                pl.col('I').mean().alias('I_mean'),
                pl.col('I').is_not_null().sum().alias('I_valid')
            ]).sort('mode')
            
            for row in current_by_mode.iter_rows(named=True):
                mode = row['mode']
                mode_name = {1: 'Galvanostatic', 2: 'Potentiostatic', 3: 'Rest/OCV'}.get(mode, f'Mode_{mode}')
                print(f"  {mode_name}: I range {row['I_min']:.6f} to {row['I_max']:.6f} mA, mean {row['I_mean']:.6f}, valid {row['I_valid']}/{row['count']}")
        
        # Control_I analysis if available
        if has_control_I and 'flags' in raw_df.columns:
            print(f"\nControl_I analysis by mode:")
            
            control_by_mode = raw_df.with_columns([
                (pl.col('flags') & 0b00000011).alias('mode')
            ]).group_by('mode').agg([
                pl.len().alias('count'),
                pl.col('control_I').min().alias('control_I_min'),
                pl.col('control_I').max().alias('control_I_max'),
                pl.col('control_I').mean().alias('control_I_mean'),
                pl.col('control_I').is_not_null().sum().alias('control_I_valid'),
                pl.col('control_I').is_null().sum().alias('control_I_null')
            ]).sort('mode')
            
            for row in control_by_mode.iter_rows(named=True):
                mode = row['mode']
                mode_name = {1: 'Galvanostatic', 2: 'Potentiostatic', 3: 'Rest/OCV'}.get(mode, f'Mode_{mode}')
                print(f"  {mode_name}: control_I range {row['control_I_min']:.6f} to {row['control_I_max']:.6f} mA")
                print(f"    valid {row['control_I_valid']}/{row['count']}, null {row['control_I_null']}")
        
        # Segmentation info
        if 'Ns' in raw_df.columns:
            segment_count = len(raw_df['Ns'].unique())
            print(f"\nSegmentation: {segment_count} unique Ns values")
            
            # First few Ns values with row counts
            ns_distribution = raw_df.group_by('Ns').agg([
                pl.len().alias('row_count')
            ]).sort('Ns').head(10)
            
            print(f"First 10 Ns segments:")
            for row in ns_distribution.iter_rows(named=True):
                print(f"  Ns {row['Ns']}: {row['row_count']} rows")
        
        print(f"\n✅ {technique_name} analysis complete")
        
    except Exception as e:
        print(f"❌ Failed to analyze {technique_name}: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run analysis on all technique files."""
    
    print("🔬 BIOLOGIC TECHNIQUE CURRENT MAPPING ANALYSIS")
    print("=" * 80)
    
    # Analyze each technique
    for technique, file_path in test_files.items():
        analyze_technique_file(technique, file_path)
    
    print(f"\n{'='*80}")
    print("📋 ANALYSIS SUMMARY")
    print(f"{'='*80}")
    print("Refer to output above for detailed current column patterns by technique.")
    print("Key questions to answer:")
    print("1. Which techniques have 'I' column vs only 'control_I'?")
    print("2. What are the value patterns for each technique type?")
    print("3. How should universal schema mapping prioritize columns?")

if __name__ == "__main__":
    main()