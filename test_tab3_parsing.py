#!/usr/bin/env python3
"""
Test Tab 3 UI parsing with the fixed backend
"""

import sys
from pathlib import Path

# Add src_clean to path
sys.path.append(str(Path(__file__).parent / "src_clean"))

from backend.api import get_backend_api

# Simulate the Tab 3 parsing logic
def test_kinetics_analysis_parsing():
    api = get_backend_api()
    
    # Get test data
    cells = api.get_cells()
    cell_name = cells[0]['name']
    groups = api.get_user_groups(cell_name)
    
    if not groups:
        print("No groups found for testing")
        return
        
    group_id = groups[0]['group_id']
    selected_groups = [group_id]
    
    print(f"Testing kinetics analysis parsing with group {group_id}")
    
    # Call the backend API (same as Tab 3 does)
    equilibrium_results = api.get_electrochemical_equilibrium_analysis(selected_groups)
    
    print(f"Backend response keys: {list(equilibrium_results.keys())}")
    
    # Parse using the same logic as Tab 3 UI
    kinetics_summary = {
        'total_measurements': 0,
        'valid_measurements': 0,
        'null_measurements': 0,
        'invalid_measurements': 0,
        'time_constants': [],
        'diffusion_coefficients': [],
        'equilibrium_voltages': [],
        'calculation_quality': []
    }
    
    if 'individual_equilibrium' in equilibrium_results:
        individual_equilibrium = equilibrium_results['individual_equilibrium']
        print(f"Found {len(individual_equilibrium)} individual equilibrium entries")
        
        for equilibrium_data in individual_equilibrium:
            if isinstance(equilibrium_data, dict):
                kinetics_summary['total_measurements'] += 1
                
                # Extract equilibrium voltage
                if 'voltage_infinity' in equilibrium_data and equilibrium_data['voltage_infinity'] is not None:
                    kinetics_summary['equilibrium_voltages'].append(equilibrium_data['voltage_infinity'])
                    kinetics_summary['valid_measurements'] += 1
                else:
                    kinetics_summary['null_measurements'] += 1
                
                # Extract time constant
                if 'time_constant_s' in equilibrium_data and equilibrium_data['time_constant_s'] is not None:
                    kinetics_summary['time_constants'].append(equilibrium_data['time_constant_s'])
                    print(f"  ✅ Found time constant: {equilibrium_data['time_constant_s']:.2f} s")
                
                # Extract diffusion coefficient
                if 'diffusion_coefficient_cm2_s' in equilibrium_data and equilibrium_data['diffusion_coefficient_cm2_s'] is not None:
                    kinetics_summary['diffusion_coefficients'].append(equilibrium_data['diffusion_coefficient_cm2_s'])
                    print(f"  ✅ Found diffusion coefficient: {equilibrium_data['diffusion_coefficient_cm2_s']:.2e} cm²/s")
                
                # Track R² quality
                if 'r_squared' in equilibrium_data:
                    r_squared = equilibrium_data['r_squared']
                    if r_squared and r_squared > 0.8:
                        quality = 'valid'
                    elif r_squared and r_squared > 0.5:
                        quality = 'marginal'
                    else:
                        quality = 'invalid'
                    kinetics_summary['calculation_quality'].append(quality)
                    if quality == 'invalid':
                        kinetics_summary['invalid_measurements'] += 1
                else:
                    quality = 'valid' if equilibrium_data.get('voltage_infinity') is not None else 'invalid'
                    kinetics_summary['calculation_quality'].append(quality)
    
    # Also extract from top-level diffusion_coefficients dict
    if 'diffusion_coefficients' in equilibrium_results:
        diff_coeffs_dict = equilibrium_results['diffusion_coefficients']
        print(f"Top-level diffusion coefficients: {len(diff_coeffs_dict)} entries")
        for segment_id, coeff in diff_coeffs_dict.items():
            if coeff is not None and coeff not in kinetics_summary['diffusion_coefficients']:
                kinetics_summary['diffusion_coefficients'].append(coeff)
    
    # Print final summary
    print(f"\n📊 PARSING RESULTS:")
    print(f"Total measurements: {kinetics_summary['total_measurements']}")
    print(f"Valid measurements: {kinetics_summary['valid_measurements']}")
    print(f"Null measurements: {kinetics_summary['null_measurements']}")
    print(f"Invalid measurements: {kinetics_summary['invalid_measurements']}")
    print(f"Time constants found: {len(kinetics_summary['time_constants'])}")
    print(f"Diffusion coefficients found: {len(kinetics_summary['diffusion_coefficients'])}")
    print(f"Equilibrium voltages found: {len(kinetics_summary['equilibrium_voltages'])}")
    
    if kinetics_summary['time_constants']:
        print(f"Sample time constants: {kinetics_summary['time_constants'][:3]}")
    if kinetics_summary['diffusion_coefficients']:
        print(f"Sample diffusion coefficients: {[f'{d:.2e}' for d in kinetics_summary['diffusion_coefficients'][:3]]}")
    if kinetics_summary['equilibrium_voltages']:
        print(f"Sample equilibrium voltages: {kinetics_summary['equilibrium_voltages'][:3]}")

if __name__ == "__main__":
    test_kinetics_analysis_parsing()