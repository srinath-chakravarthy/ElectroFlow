#!/usr/bin/env python3
"""Test enhanced BioLogic mapping with mixed-mode segmentation and mode-aware current mapping."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test files
test_files = {
    'MB': Path("biologic_test_files/AR-3753_3_electrode_full_GITT_EIS_0_04_MB_C06.mpr"),
    'GCPL': Path("biologic_test_files/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr")
}

def test_enhanced_mapping():
    """Test the enhanced mixed-mode segmentation and mode-aware current mapping."""
    
    print("🧪 ENHANCED BIOLOGIC MAPPING TEST")
    print("=" * 80)
    
    for technique, file_path in test_files.items():
        if not file_path.exists():
            print(f"❌ {technique} file not found: {file_path}")
            continue
            
        print(f"\n📁 Testing {technique} file: {file_path.name}")
        print("-" * 60)
        
        parser = BiologicParser()
        
        try:
            # Get raw data for comparison
            raw_df = parser.mpr_reader.parse_mpr_file(file_path)
            
            # Test enhanced segmentation (raw level)
            enhanced_raw = parser._add_segment_numbers_to_raw_data(raw_df)
            
            # Parse with full enhanced pipeline
            parsed_data = parser.parse_file(file_path)
            enhanced_df = parsed_data.universal_data
            
            print(f"✅ Parsing successful!")
            print(f"   Raw data: {raw_df.shape}")
            print(f"   Enhanced segments: {len(enhanced_raw['segment_number'].unique())} (was {len(raw_df['Ns'].unique() if 'Ns' in raw_df.columns else [1])})")
            print(f"   Universal data: {enhanced_df.shape}")
            
            # Test specific enhancements
            
            # 1. Mixed-mode segmentation test
            if 'Ns' in raw_df.columns and 'flags' in raw_df.columns:
                # Check if segment 2 was split (CC-CV case)
                segment_analysis = enhanced_raw.group_by(['segment_number', 'Ns']).agg([
                    pl.len().alias('rows'),
                    ((pl.col('flags') & 0b00000011).unique()).alias('modes')
                ]).sort('segment_number')
                
                print(f"\n   📊 Segmentation Analysis:")
                mixed_segments = segment_analysis.filter(pl.col('modes').list.len() > 1)
                if len(mixed_segments) == 0:
                    print(f"   ✅ All segments are pure mode (no mixed-mode segments)")
                    print(f"   📈 Total segments: {len(segment_analysis)}")
                else:
                    print(f"   ⚠️ Found {len(mixed_segments)} mixed-mode segments")
                    print(mixed_segments)
            
            # 2. Current mapping test  
            if 'current_a' in enhanced_df.columns:
                current_stats = {
                    'non_null': enhanced_df['current_a'].count(),
                    'null': enhanced_df['current_a'].null_count(),
                    'min': enhanced_df['current_a'].min(),
                    'max': enhanced_df['current_a'].max(),
                    'mean': enhanced_df['current_a'].mean()
                }
                
                print(f"\n   ⚡ Current Mapping Results:")
                print(f"   current_a: {current_stats['non_null']}/{len(enhanced_df)} valid, range {current_stats['min']:.6f} to {current_stats['max']:.6f} A")
                
                # Check for applied values
                if 'current_applied_a' in enhanced_df.columns:
                    applied_current_valid = enhanced_df['current_applied_a'].count()
                    print(f"   current_applied_a: {applied_current_valid}/{len(enhanced_df)} valid")
                
                if 'potential_applied_v' in enhanced_df.columns:
                    applied_potential_valid = enhanced_df['potential_applied_v'].count()
                    print(f"   potential_applied_v: {applied_potential_valid}/{len(enhanced_df)} valid")
            
            # 3. Mode-specific current analysis (for MB files)
            if technique == 'MB' and 'flags' in raw_df.columns:
                print(f"\n   🎯 Mode-Aware Current Analysis:")
                
                # Compare raw vs enhanced current values by mode
                raw_with_mode = raw_df.with_columns([
                    (pl.col('flags') & 0b00000011).alias('mode')
                ])
                
                mode_comparison = raw_with_mode.group_by('mode').agg([
                    pl.len().alias('count'),
                    pl.col('I').mean().alias('raw_I_mean'),
                    pl.col('control_I').mean().alias('raw_control_I_mean')
                ]).sort('mode')
                
                enhanced_mode = enhanced_df.join(
                    raw_with_mode.select(['mode']).with_row_index(), 
                    left_on=pl.int_range(len(enhanced_df)), 
                    right_on='index',
                    how='left'
                ).group_by('mode').agg([
                    pl.col('current_a').mean().alias('enhanced_current_a_mean')
                ]).sort('mode')
                
                comparison = mode_comparison.join(enhanced_mode, on='mode', how='left')
                
                print("   Mode | Count | Raw I (mA) | Raw control_I (mA) | Enhanced current_a (A)")
                print("   -----|-------|------------|---------------------|----------------------")
                
                for row in comparison.iter_rows(named=True):
                    mode = row['mode']
                    mode_name = {1: 'Galvano', 2: 'Potentio', 3: 'Rest'}.get(mode, f'Mode{mode}')
                    count = row['count']
                    raw_i = row['raw_I_mean'] or 0
                    raw_control_i = row['raw_control_I_mean'] or 0  
                    enhanced_current_a = row['enhanced_current_a_mean'] or 0
                    
                    print(f"   {mode_name:>5} | {count:5d} | {raw_i:10.6f} | {raw_control_i:18.6f} | {enhanced_current_a:20.6f}")
            
        except Exception as e:
            print(f"❌ Error testing {technique}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎯 TEST COMPLETE")
    print("Check above results for:")
    print("1. ✅ Pure mode segmentation (no mixed-mode segments)")
    print("2. ✅ Valid current_a values for all rows")
    print("3. ✅ Applied values (current_applied_a, potential_applied_v) where appropriate")
    print("4. ✅ Mode-aware current mapping (rest mode uses control, others use measured)")

if __name__ == "__main__":
    test_enhanced_mapping()