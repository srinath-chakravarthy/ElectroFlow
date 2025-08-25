#!/usr/bin/env python3
"""
Test resistance analysis API to see why it's not working
"""

import sys
from pathlib import Path

# Add src_clean to path
sys.path.append(str(Path(__file__).parent / "src_clean"))

from backend.api import get_backend_api

def main():
    api = get_backend_api()
    
    # Get test data
    cells = api.get_cells()
    cell_name = cells[0]['name']
    groups = api.get_user_groups(cell_name)
    
    if not groups:
        print("No groups found for testing")
        return
        
    group_id = groups[0]['group_id']
    
    print(f"Testing resistance analysis with group {group_id}")
    
    # Check what resistance analysis method exists
    resistance_methods = [method for method in dir(api) if 'resistance' in method.lower()]
    print(f"Available resistance methods: {resistance_methods}")
    
    # Try the method that should exist
    try:
        print(f"\n🔍 TESTING get_electrochemical_resistance_analysis:")
        resistance_result = api.get_electrochemical_resistance_analysis([group_id])
        
        print(f"Result type: {type(resistance_result)}")
        print(f"Result: {resistance_result}")
        
        if isinstance(resistance_result, dict):
            print(f"Response keys: {list(resistance_result.keys())}")
            
            if 'individual_resistances' in resistance_result:
                individual_resistances = resistance_result['individual_resistances']
                print(f"Individual resistances: {len(individual_resistances)} entries")
                
                if individual_resistances:
                    sample = individual_resistances[0]
                    print(f"Sample resistance entry: {sample}")
        
    except AttributeError as e:
        print(f"Method not found: {e}")
        
        # Try to find what segments we have
        segments = api.get_group_segments(group_id)
        galv_segments = [s for s in segments if s['technique_name'].upper() == 'GALVANOSTATIC']
        
        print(f"Found {len(galv_segments)} GALVANOSTATIC segments in group")
        
        if galv_segments:
            sample_segment = galv_segments[0]
            print(f"Sample GALVANOSTATIC segment analysis_results:")
            analysis_results = sample_segment.get('analysis_results', {})
            if isinstance(analysis_results, str):
                import json
                try:
                    analysis_results = json.loads(analysis_results)
                except:
                    pass
            print(f"  {analysis_results}")

if __name__ == "__main__":
    main()