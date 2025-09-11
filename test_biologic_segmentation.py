#!/usr/bin/env python3
"""Test that BioLogic parser already produces segmented data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser

mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    print("🧪 Testing BioLogic segmentation in integrated mode\n")
    
    # Parse with full integration
    parser = BiologicParser()
    result = parser.parse_data(mpr_file)
    
    if hasattr(result, 'universal_data'):
        df = result.universal_data
    else:
        df = result['universal_data']
    
    print(f"📊 Final DataFrame: {df.shape}")
    
    # Check segmentation columns
    if 'segment_number' in df.columns:
        segments = df['segment_number'].unique().sort()
        print(f"✅ segment_number column present: {segments.to_list()}")
        print(f"📈 Total segments created: {len(segments)}")
    else:
        print("❌ segment_number column MISSING")
    
    if 'technique_id' in df.columns:
        tech_ids = df['technique_id'].unique().sort()
        print(f"✅ technique_id column present: {tech_ids.to_list()}")
    else:
        print("❌ technique_id column MISSING")
    
    # Show segment boundaries
    if 'segment_number' in df.columns:
        print(f"\n📊 Segment analysis:")
        for seg_num in segments[:5]:  # First 5 segments
            segment_data = df.filter(df['segment_number'] == seg_num)
            point_count = len(segment_data)
            start_time = segment_data['time_s'].min()
            end_time = segment_data['time_s'].max() 
            duration = end_time - start_time
            tech_id = segment_data['technique_id'][0] if 'technique_id' in df.columns else 'N/A'
            
            print(f"   Segment {seg_num}: {point_count} points, {duration:.1f}s, technique_id={tech_id}")
    
    print(f"\n🎯 RESULT: BioLogic parser {'✅ ALREADY PRODUCES' if 'segment_number' in df.columns else '❌ MISSING'} segmented data!")
    
else:
    print(f"❌ File not found: {mpr_file}")