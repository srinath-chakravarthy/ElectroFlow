#!/usr/bin/env python3
"""
Quick test of the fixed backend API methods
"""

import sys
import json
from pathlib import Path

# Add src_clean to path
sys.path.append(str(Path(__file__).parent / "src_clean"))

from backend.api import get_backend_api

def main():
    api = get_backend_api()
    
    # Get cell and groups
    cells = api.get_cells()
    cell_name = cells[0]['name']
    print(f"Testing with cell: {cell_name}")
    
    # Use get_user_groups instead of get_cell_groups  
    groups = api.get_user_groups(cell_name)
    if not groups:
        print("No groups found - creating test group")
        result = api.create_group(cell_name, "TEST_KINETICS", "Test group for kinetics")
        if result.success:
            group_id = result.group_id
            print(f"Created group: {group_id}")
            
            # Add some segments to the group
            segments = api.get_cell_segments(cell_name)
            rest_segments = [s['id'] for s in segments if s['technique_name'].upper() == 'REST' and s['analysis_status'] == 'completed'][:5]
            
            if rest_segments:
                api.add_segments_to_group(group_id, rest_segments)
                print(f"Added {len(rest_segments)} REST segments to group")
            
        else:
            print(f"Failed to create group: {result.error}")
            return
    else:
        group_id = groups[0]['group_id']
        print(f"Using existing group: {group_id}")
    
    print(f"\n🔍 TESTING EQUILIBRIUM ANALYSIS API:")
    equilibrium_result = api.get_electrochemical_equilibrium_analysis([group_id])
    
    if isinstance(equilibrium_result, dict):
        print(f"✅ Success! Response keys: {list(equilibrium_result.keys())}")
        
        if 'individual_equilibrium' in equilibrium_result:
            individual_equilibrium = equilibrium_result['individual_equilibrium']
            print(f"📊 Found {len(individual_equilibrium)} individual equilibrium analyses")
            
            if individual_equilibrium:
                sample = individual_equilibrium[0]
                print(f"🔍 Sample equilibrium analysis:")
                for key, value in sample.items():
                    print(f"   {key}: {type(value)} = {value}")
                
                # Check for time constants and diffusion coefficients
                time_constants = [e.get('time_constant_s') for e in individual_equilibrium if e.get('time_constant_s')]
                diffusion_coeffs = [e.get('diffusion_coefficient_cm2_s') for e in individual_equilibrium if e.get('diffusion_coefficient_cm2_s')]
                
                print(f"\n📈 ANALYSIS SUMMARY:")
                print(f"Time constants found: {len(time_constants)}")
                if time_constants:
                    print(f"Sample time constants: {time_constants[:3]}")
                    
                print(f"Diffusion coefficients found: {len(diffusion_coeffs)}")
                if diffusion_coeffs:
                    print(f"Sample diffusion coefficients: {diffusion_coeffs[:3]}")
        
        if 'diffusion_coefficients' in equilibrium_result:
            diff_coeffs = equilibrium_result['diffusion_coefficients']
            print(f"📊 Diffusion coefficients dict: {len(diff_coeffs)} entries")
            
    else:
        print(f"❌ Failed: {equilibrium_result}")

if __name__ == "__main__":
    main()