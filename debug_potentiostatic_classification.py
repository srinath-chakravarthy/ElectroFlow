#!/usr/bin/env python3
"""Debug potentiostatic technique classification in BioLogic MB files."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.parsers.biologic import BiologicParser
import polars as pl

# Test file path
mpr_file = Path("/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_Redo_formation_after_GITT_to_check_04_MB_C05.mpr")

if mpr_file.exists():
    print("🔍 Debugging Potentiostatic Classification in MB File\n")
    
    # Create parser and get raw data
    parser = BiologicParser()
    raw_df = parser.mpr_reader.parse_mpr_file(mpr_file)
    
    # Get technique parameters
    tech_params = parser.mpr_reader.last_technique_parameters
    
    if tech_params and 'ctrl_type' in tech_params:
        ctrl_type = tech_params.get('ctrl_type', [])
        apply_ic = tech_params.get('Apply I/C', [])
        ctrl1_val = tech_params.get('ctrl1_val', [])
        
        print(f"📋 MB Parameter Arrays:")
        print(f"   ctrl_type length: {len(ctrl_type)}")
        print(f"   Apply I/C length: {len(apply_ic)}")
        print(f"   ctrl1_val length: {len(ctrl1_val)}")
        
        # Get unique Ns values
        unique_ns_values = raw_df['Ns'].unique().sort().to_list()
        print(f"\n🔢 Unique Ns values: {unique_ns_values}")
        
        # Analyze each Ns segment that gets classified as Potentiostatic (ID=7)
        print(f"\n🔬 Detailed Potentiostatic Analysis:")
        
        potentiostatic_segments = []
        for ns_val in unique_ns_values:
            if ns_val < len(ctrl_type):
                ct = int(ctrl_type[ns_val])
                aic = int(apply_ic[ns_val]) if ns_val < len(apply_ic) else 0
                cv = float(ctrl1_val[ns_val]) if ns_val < len(ctrl1_val) else 0.0
                
                # Check what gets classified as potentiostatic
                if ct == 17:  # This is our potentiostatic trigger
                    potentiostatic_segments.append(ns_val)
                    
                    # Get segment data for analysis
                    segment_data = raw_df.filter(pl.col('Ns') == ns_val)
                    point_count = len(segment_data)
                    
                    if point_count > 0:
                        start_time = segment_data['time'].min()
                        end_time = segment_data['time'].max()
                        duration = end_time - start_time
                        
                        ewe_min, ewe_max = segment_data['Ewe'].min(), segment_data['Ewe'].max()
                        i_min, i_max = segment_data['I'].min(), segment_data['I'].max()
                        i_avg = segment_data['I'].mean()
                        i_std = segment_data['I'].std()
                        
                        print(f"\n   Ns={ns_val} (Potentiostatic - ctrl_type=17):")
                        print(f"      Parameters: Apply I/C={aic}, ctrl1_val={cv:.6f}")
                        print(f"      Data: {point_count} points, {duration:.1f}s")
                        print(f"      Voltage: {ewe_min:.3f} - {ewe_max:.3f} V (range: {ewe_max-ewe_min:.3f} V)")
                        print(f"      Current: {i_min:.3f} - {i_max:.3f} mA (avg: {i_avg:.3f}, std: {i_std:.3f})")
                        
                        # Check if this looks like CC-CV behavior
                        voltage_range = ewe_max - ewe_min
                        current_variability = i_std / abs(i_avg) if abs(i_avg) > 0.001 else 0
                        
                        print(f"      Analysis:")
                        print(f"         Voltage range: {voltage_range:.3f} V ({'Large' if voltage_range > 0.1 else 'Small'})")
                        print(f"         Current variability: {current_variability:.3f} ({'High' if current_variability > 0.1 else 'Low'})")
                        
                        if voltage_range > 0.1 and current_variability > 0.1:
                            print(f"         🎯 Classification: Likely CC-CV (Constant Current → Constant Voltage)")
                        elif voltage_range > 0.05:
                            print(f"         🎯 Classification: Voltage-controlled (Potentiostatic)")
                        else:
                            print(f"         ❓ Classification: Unclear - may need refinement")
        
        print(f"\n📊 Summary:")
        print(f"   Total Ns segments with ctrl_type=17 (Potentiostatic): {len(potentiostatic_segments)}")
        print(f"   Segments: {potentiostatic_segments}")
        
        # Show all ctrl_type values and their counts
        print(f"\n📋 All ctrl_type Values and Frequencies:")
        ctrl_type_counts = {}
        for i, ct in enumerate(ctrl_type):
            if i in unique_ns_values:  # Only count Ns values that actually exist in data
                ctrl_type_counts[ct] = ctrl_type_counts.get(ct, 0) + 1
        
        technique_mapping = {
            4: "Rest/Wait (→ Rest/OCV ID=23)",
            17: "Complex/Multi-step (→ Potentiostatic ID=7)", 
            8: "Standard measurement (→ Galvanostatic/EIS ID=8/20)",
            0: "Default/standard (→ Rest/Galvanostatic ID=23/8)",
            5: "Measurement variant (→ Galvanostatic ID=8)"
        }
        
        for ct, count in sorted(ctrl_type_counts.items()):
            mapping_desc = technique_mapping.get(ct, f"Unknown (→ Fallback analysis)")
            print(f"   ctrl_type={ct}: {count} segments - {mapping_desc}")
            
else:
    print(f"❌ File not found: {mpr_file}")