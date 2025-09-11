#!/usr/bin/env python3
"""Analyze BioLogic segmentation data for database schema requirements."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    print("🔍 Analyzing BioLogic segmentation data for database requirements\n")
    
    # Create parser and get raw data
    parser = BiologicParser()
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    print(f"📊 Raw data shape: {raw_df.shape}")
    print(f"📋 Raw columns: {raw_df.columns}")
    
    # Analyze segmentation columns
    if "Ns" in raw_df.columns:
        ns_values = raw_df["Ns"].unique().sort()
        print(f"\n🔢 Ns (sequence) values: {ns_values.to_list()}")
        print(f"📈 Number of segments: {len(ns_values)}")
        
        # Analyze each segment
        print(f"\n📊 Segment analysis:")
        for ns_val in ns_values[:5]:  # First 5 segments
            segment_data = raw_df.filter(pl.col("Ns") == ns_val)
            start_time = segment_data["time"].min()
            end_time = segment_data["time"].max()
            duration = end_time - start_time
            point_count = len(segment_data)
            
            # Get potential and current ranges
            ewe_range = f"{segment_data['Ewe'].min():.3f} - {segment_data['Ewe'].max():.3f} V"
            
            # Use control_I if available (YADG control splitting), otherwise fallback to I
            current_col = 'control_I' if 'control_I' in segment_data.columns else 'I'
            i_range = f"{segment_data[current_col].min():.3f} - {segment_data[current_col].max():.3f} mA"
            
            print(f"   Ns={ns_val}: {point_count} points, {duration:.1f}s, Ewe={ewe_range}, I={i_range}")
    
    # Check technique information
    if hasattr(parser.mpr_reader, 'last_technique_parameters'):
        tech_params = parser.mpr_reader.last_technique_parameters
        if tech_params:
            print(f"\n🔧 Technique Information:")
            print(f"   Btech: {tech_params.get('_btech_name', 'Unknown')}")
            print(f"   Ftech: {tech_params.get('_ftech_name', 'Unknown')}")
            if '_parameter_sequences' in tech_params:
                print(f"   Parameter sequences: {len(tech_params['_parameter_sequences'])}")
    
    # Get full universal schema data using the proper parser method
    result = parser.parse_data(mpr_file)
    complete_df = result['universal_data'] if isinstance(result, dict) else result.universal_data
    
    # Analyze what columns have data vs nulls
    print(f"\n📋 Universal Schema Column Analysis:")
    data_columns = []
    null_columns = []
    
    for col in sorted(complete_df.columns):
        non_null_count = complete_df[col].count()
        if non_null_count > 0:
            data_columns.append(f"{col} ({non_null_count} values)")
        else:
            null_columns.append(col)
    
    print(f"✅ Columns with data ({len(data_columns)}):")
    for col in data_columns[:10]:  # First 10
        print(f"   {col}")
    if len(data_columns) > 10:
        print(f"   ... and {len(data_columns) - 10} more")
    
    print(f"\n❌ Columns with null values ({len(null_columns)}):")
    for col in null_columns[:10]:  # First 10  
        print(f"   {col}")
    if len(null_columns) > 10:
        print(f"   ... and {len(null_columns) - 10} more")
    
    # Analyze final segments from universal schema with technique mapping
    if 'segment_number' in complete_df.columns:
        final_segments = complete_df['segment_number'].unique().sort()
        # Filter out None values
        final_segments = [s for s in final_segments.to_list() if s is not None]
        print(f"\n🎯 FINAL SEGMENT ANALYSIS:")
        print(f"   • Universal schema segments: {final_segments}")
        print(f"   • Total segments created: {len(final_segments)}")
        
        # Technique ID to name mapping
        technique_names = {
            0: 'Unknown',
            1: 'CV', 
            7: 'Potentiostatic',
            8: 'Galvanostatic',
            20: 'EIS',
            23: 'Rest/OCV'
        }
        
        # Analyze per-segment techniques
        if 'technique_id' in complete_df.columns:
            segment_techniques = complete_df.select(['segment_number', 'technique_id']).unique().sort('segment_number')
            
            print(f"\n🔬 Per-Segment Technique Analysis:")
            for row in segment_techniques.iter_rows(named=True):
                segment = row['segment_number']
                tech_id = row['technique_id']
                tech_name = technique_names.get(tech_id, f'Unknown_{tech_id}')
                
                if segment is not None and segment <= 10:  # First 10 segments
                    print(f"   Segment {segment}: technique_id={tech_id} ({tech_name})")
            
            if len(final_segments) > 10:
                print(f"   ... and {len(final_segments) - 10} more segments")
            
            # Technique summary statistics
            unique_techniques = complete_df['technique_id'].unique().sort()
            print(f"\n📊 Technique Distribution:")
            for tech_id in unique_techniques.to_list():
                if tech_id is not None:
                    count = len(complete_df.filter(pl.col('technique_id') == tech_id))
                    tech_name = technique_names.get(tech_id, f'Unknown_{tech_id}')
                    print(f"   {tech_name} (ID={tech_id}): {count:,} data points")
        
        # Show first few segment details
        print(f"\n📊 Universal Schema Segment Details:")
        for seg_num in final_segments[:5]:  # First 5 segments
            segment_data = complete_df.filter(pl.col('segment_number') == seg_num)
            if len(segment_data) > 0:
                start_time = segment_data['time_s'].min()
                end_time = segment_data['time_s'].max() 
                duration = end_time - start_time
                point_count = len(segment_data)
                
                # Get potential and current ranges from universal columns
                potential_range = f"{segment_data['potential_v'].min():.3f} - {segment_data['potential_v'].max():.3f} V"
                current_range = f"{segment_data['current_a'].min():.6f} - {segment_data['current_a'].max():.6f} A"
                
                # Get technique info for this segment
                tech_info = ""
                if 'technique_id' in segment_data.columns:
                    tech_id = segment_data['technique_id'][0]
                    tech_name = technique_names.get(tech_id, f'Unknown_{tech_id}')
                    tech_info = f", Technique: {tech_name}"
                
                print(f"   Segment {seg_num}: {point_count} points, {duration:.1f}s, V={potential_range}, I={current_range}{tech_info}")
    
    print(f"\n🎯 SEGMENT DATABASE REQUIREMENTS:")
    if 'segment_number' in complete_df.columns:
        segments_count = len([s for s in complete_df['segment_number'].unique().to_list() if s is not None])
        print(f"   • Segments to store: {segments_count}")
    else:
        print(f"   • Segments to store: {len(ns_values) if 'Ns' in raw_df.columns else 'Unknown'}")
    print(f"   • Total data points: {complete_df.shape[0]:,}")
    print(f"   • Universal columns with data: {len(data_columns)}")
    print(f"   • Time range: {complete_df['time_s'].min():.1f} - {complete_df['time_s'].max():.1f} seconds")
    
else:
    print(f"❌ File not found: {mpr_file}")