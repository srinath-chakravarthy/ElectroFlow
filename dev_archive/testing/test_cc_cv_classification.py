#!/usr/bin/env python3
"""Test enhanced CC-CV classification for ctrl_type=17 segments."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    print("🔍 Testing Enhanced CC-CV Classification\n")
    
    # Create parser and get raw data
    parser = BiologicParser()
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    # Get technique parameters
    tech_params = parser.mpr_reader.last_technique_parameters
    
    if tech_params and 'ctrl_type' in tech_params:
        ctrl_type = tech_params.get('ctrl_type', [])
        
        # Find ctrl_type=17 segments
        unique_ns_values = raw_df['Ns'].unique().sort().to_list()
        ctrl_17_segments = []
        
        for ns_val in unique_ns_values:
            if ns_val < len(ctrl_type) and int(ctrl_type[ns_val]) == 17:
                ctrl_17_segments.append(ns_val)
        
        print(f"📋 Found {len(ctrl_17_segments)} segments with ctrl_type=17: {ctrl_17_segments}")
        
        # Test each segment with enhanced classification
        for ns_val in ctrl_17_segments:
            print(f"\n🔬 Testing Ns={ns_val}:")
            
            # Test the new classification method
            technique_id = parser._classify_ctrl_type_17(raw_df, ns_val)
            technique_name = {8: "Galvanostatic (CC-CV)", 7: "Potentiostatic"}.get(technique_id, "Unknown")
            
            # Get segment data for analysis
            segment_data = raw_df.filter(pl.col('Ns') == ns_val)
            
            if len(segment_data) > 0:
                voltage_min = float(segment_data['Ewe'].min())
                voltage_max = float(segment_data['Ewe'].max())
                voltage_range = voltage_max - voltage_min
                
                current_avg = abs(float(segment_data['I'].mean()))
                current_std = float(segment_data['I'].std()) if len(segment_data) > 1 else 0.0
                current_variability = current_std / current_avg if current_avg > 0.001 else 0.0
                
                duration = float(segment_data['time'].max() - segment_data['time'].min())
                point_count = len(segment_data)
                
                print(f"   📊 Classification: {technique_name} (ID={technique_id})")
                print(f"   📈 Voltage range: {voltage_range:.3f} V ({voltage_min:.3f} - {voltage_max:.3f})")
                print(f"   ⚡ Current: avg={current_avg:.3f} mA, variability={current_variability:.3f}")
                print(f"   ⏱️  Duration: {duration:.1f}s ({duration/3600:.1f}h), Points: {point_count:,}")
                
                # Show decision criteria
                is_large_voltage_range = voltage_range > 0.5
                is_controlled_current = current_variability < 0.1
                is_long_duration = duration > 3600
                is_sufficient_data = point_count > 1000
                
                print(f"   🎯 CC-CV Criteria:")
                print(f"      Large voltage range (>0.5V): {'✅' if is_large_voltage_range else '❌'} ({voltage_range:.3f}V)")
                print(f"      Controlled current (<0.1 var): {'✅' if is_controlled_current else '❌'} ({current_variability:.3f})")
                print(f"      Long duration (>1h): {'✅' if is_long_duration else '❌'} ({duration/3600:.1f}h)")
                print(f"      Sufficient data (>1000 pts): {'✅' if is_sufficient_data else '❌'} ({point_count:,})")
                
                # Final assessment
                if (is_large_voltage_range and is_controlled_current and 
                    is_long_duration and is_sufficient_data):
                    print(f"   ✅ Assessment: CC-CV Battery Charging Pattern Detected")
                else:
                    print(f"   ❌ Assessment: Pure Potentiostatic or Short Multi-step")
    
    # Now test complete parser pipeline
    print(f"\n🎯 Testing Complete Parser Pipeline:")
    result = parser.parse_data(mpr_file)
    complete_df = result['universal_data'] if isinstance(result, dict) else result.universal_data
    
    # Check technique distribution after enhancement
    technique_names = {
        0: 'Unknown',
        1: 'CV', 
        7: 'Potentiostatic',
        8: 'Galvanostatic',
        20: 'EIS',
        23: 'Rest/OCV'
    }
    
    unique_techniques = complete_df['technique_id'].unique().sort()
    print(f"\n📊 Enhanced Technique Distribution:")
    for tech_id in unique_techniques.to_list():
        if tech_id is not None:
            count = len(complete_df.filter(pl.col('technique_id') == tech_id))
            tech_name = technique_names.get(tech_id, f'Unknown_{tech_id}')
            print(f"   {tech_name} (ID={tech_id}): {count:,} data points")
    
else:
    print(f"❌ File not found: {mpr_file}")