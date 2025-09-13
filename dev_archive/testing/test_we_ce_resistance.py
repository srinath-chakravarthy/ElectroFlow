#!/usr/bin/env python3
"""Test WE and CE electrode-specific resistance analysis."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src_clean.backend import get_backend_api
import pandas as pd

def test_we_ce_resistance():
    """Test electrode-specific resistance analysis with BioLogic data."""
    
    print("🔍 Testing WE and CE Electrode-Specific Resistance Analysis\n")
    
    api = get_backend_api()
    
    # Get all cells
    cells = api.get_cells()
    if not cells:
        print("❌ No cells found. Please process some BioLogic files first.")
        return
    
    print(f"📋 Found {len(cells)} cells")
    
    # Look for cells with segments
    for cell in cells:
        cell_id = cell.get('cell_id', cell.get('id', 'unknown'))
        segments = api.get_cell_segments(cell_id)
        
        if not segments:
            continue
            
        print(f"\n🔬 Testing cell: {cell_id} ({len(segments)} segments)")
        
        # Filter for galvanostatic segments (most likely to have resistance data)
        galv_segments = [s for s in segments if s.get('technique_id') == 8]  # Galvanostatic
        
        if not galv_segments:
            print(f"   ❌ No galvanostatic segments found")
            continue
            
        print(f"   ✅ Found {len(galv_segments)} galvanostatic segments")
        
        # Test resistance analysis on first few segments
        test_segments = galv_segments[:3]  # First 3 segments
        
        try:
            # Run resistance analysis
            result = api.get_segments_with_analytics(
                [s['id'] for s in test_segments], 
                analytics_types=['resistance_analysis']
            )
            
            if result and len(result) > 0:
                df = pd.DataFrame(result)
                
                # Check what resistance columns we have
                resistance_cols = [col for col in df.columns if 'ir_' in col and 'ohm' in col]
                we_resistance_cols = [col for col in resistance_cols if col.startswith('we_')]
                ce_resistance_cols = [col for col in resistance_cols if col.startswith('ce_')]
                cell_resistance_cols = [col for col in resistance_cols if not col.startswith(('we_', 'ce_'))]
                
                print(f"\n   📊 Resistance Analysis Results:")
                print(f"      Cell resistance columns: {len(cell_resistance_cols)} - {cell_resistance_cols}")
                print(f"      WE resistance columns: {len(we_resistance_cols)} - {we_resistance_cols}")
                print(f"      CE resistance columns: {len(ce_resistance_cols)} - {ce_resistance_cols}")
                
                # Show sample data for first segment
                if len(result) > 0:
                    first_segment = result[0]
                    print(f"\n   📈 Sample Resistance Values (Segment {first_segment.get('id')}):")
                    
                    # Cell resistance
                    if 'ir_immediate_ohm' in first_segment:
                        print(f"      Cell IR (immediate): {first_segment['ir_immediate_ohm']:.6f} Ω")
                    if 'ir_10s_ohm' in first_segment:
                        print(f"      Cell IR (10s): {first_segment['ir_10s_ohm']:.6f} Ω")
                        
                    # WE resistance
                    if 'we_ir_immediate_ohm' in first_segment:
                        print(f"      WE IR (immediate): {first_segment['we_ir_immediate_ohm']:.6f} Ω")
                    if 'we_ir_10s_ohm' in first_segment:
                        print(f"      WE IR (10s): {first_segment['we_ir_10s_ohm']:.6f} Ω")
                        
                    # CE resistance  
                    if 'ce_ir_immediate_ohm' in first_segment:
                        print(f"      CE IR (immediate): {first_segment['ce_ir_immediate_ohm']:.6f} Ω")
                    if 'ce_ir_10s_ohm' in first_segment:
                        print(f"      CE IR (10s): {first_segment['ce_ir_10s_ohm']:.6f} Ω")
                
                # Check if we have electrode-specific data
                has_we_data = any(col in df.columns and df[col].notna().any() for col in we_resistance_cols)
                has_ce_data = any(col in df.columns and df[col].notna().any() for col in ce_resistance_cols)
                
                print(f"\n   🎯 Electrode-Specific Analysis Status:")
                print(f"      WE resistance data: {'✅ Available' if has_we_data else '❌ Not available'}")
                print(f"      CE resistance data: {'✅ Available' if has_ce_data else '❌ Not available'}")
                
                if has_we_data or has_ce_data:
                    print(f"   🎉 SUCCESS: Electrode-specific resistance analysis working!")
                    return True
                else:
                    print(f"   ⚠️  Cell resistance working, but no electrode-specific data")
                    
            else:
                print(f"   ❌ No resistance analysis results returned")
                
        except Exception as e:
            print(f"   ❌ Error during resistance analysis: {e}")
            
    print(f"\n❌ No electrode-specific resistance data found in any cells")
    return False

if __name__ == "__main__":
    test_we_ce_resistance()