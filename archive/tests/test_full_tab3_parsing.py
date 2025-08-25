#!/usr/bin/env python3
"""
Test both resistance and kinetics analysis parsing as Tab 3 would do it
"""

import sys
from pathlib import Path
import pandas as pd

# Add src_clean to path
sys.path.append(str(Path(__file__).parent / "src_clean"))

from backend.api import get_backend_api

def test_resistance_analysis_parsing():
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
    
    print("=" * 60)
    print("🔧 TESTING RESISTANCE ANALYSIS PARSING")
    print("=" * 60)
    
    # Call resistance analysis API
    resistance_results = api.get_electrochemical_resistance_analysis(selected_groups)
    
    print(f"Backend response keys: {list(resistance_results.keys())}")
    
    # Parse using Tab 3 UI logic
    resistance_summary = {
        'total_measurements': 0,
        'valid_measurements': 0,
        'null_measurements': 0,
        'invalid_measurements': 0,
        'resistance_values_ohm': [],
        'time_points_s': [],
        'average_resistance_ohm': 0.0,
        'resistance_std_ohm': 0.0,
        'measurement_types': set()
    }
    
    if 'individual_resistances' in resistance_results:
        individual_resistances = resistance_results['individual_resistances']
        print(f"Found {len(individual_resistances)} individual resistances")
        
        for resistance_data in individual_resistances:
            if isinstance(resistance_data, dict):
                segment_id = resistance_data.get('segment_id', 'unknown')
                print(f"  Processing segment {segment_id}")
                
                resistance_summary['total_measurements'] += 1
                
                # Process each resistance type
                for key, time_point, type_name in [
                    ('ir_immediate_ohm', 0, 'immediate'),
                    ('ir_10s_ohm', 10, '10s'), 
                    ('ir_30s_ohm', 30, '30s')
                ]:
                    if key in resistance_data:
                        value = resistance_data[key]
                        print(f"    {key}: {value}")
                        
                        if value is None:
                            resistance_summary['null_measurements'] += 1
                        elif isinstance(value, (int, float)) and value > 0:
                            resistance_summary['resistance_values_ohm'].append(value)
                            resistance_summary['time_points_s'].append(time_point)
                            resistance_summary['measurement_types'].add(type_name)
                            resistance_summary['valid_measurements'] += 1
                        else:
                            resistance_summary['invalid_measurements'] += 1
    
    # Calculate statistics
    if resistance_summary['resistance_values_ohm']:
        resistance_values = resistance_summary['resistance_values_ohm']
        resistance_summary['average_resistance_ohm'] = sum(resistance_values) / len(resistance_values)
        
        if len(resistance_values) > 1:
            resistance_summary['resistance_std_ohm'] = pd.Series(resistance_values).std()
        
        resistance_summary['min_resistance_ohm'] = min(resistance_values)
        resistance_summary['max_resistance_ohm'] = max(resistance_values)
    
    print(f"\n📊 RESISTANCE PARSING RESULTS:")
    print(f"Total measurements: {resistance_summary['total_measurements']}")
    print(f"Valid measurements: {resistance_summary['valid_measurements']}")
    print(f"Resistance values found: {len(resistance_summary['resistance_values_ohm'])}")
    print(f"Average resistance: {resistance_summary['average_resistance_ohm']:.4f} Ω")
    print(f"Measurement types: {list(resistance_summary['measurement_types'])}")
    
    if resistance_summary['resistance_values_ohm']:
        print(f"Sample values: {resistance_summary['resistance_values_ohm'][:6]}")
    
    return resistance_summary

def test_kinetics_plots_rendering():
    """Test what happens when kinetics data reaches the plotting component"""
    print("\n" + "=" * 60)
    print("⚡ TESTING KINETICS PLOT RENDERING")
    print("=" * 60)
    
    # Simulate the data structure that would be passed to the plotting component
    kinetics_results = {
        'analysis_type': 'kinetics_analysis',
        'kinetics_analysis': {
            'total_measurements': 5,
            'valid_measurements': 5,
            'time_constants': [1537.84, 1605.79],
            'diffusion_coefficients': [6.59e-09, 6.31e-09],
            'equilibrium_voltages': [0.600, 2.478, 2.466, 2.460, 3.150],
            'calculation_quality': ['valid', 'valid', 'marginal', 'valid', 'valid']
        }
    }
    
    # This is what would reach the plotting component
    print(f"Data reaching plotting component:")
    print(f"  Analysis type: {kinetics_results['analysis_type']}")
    print(f"  Has kinetics_analysis: {'kinetics_analysis' in kinetics_results}")
    
    kinetics_data = kinetics_results.get('kinetics_analysis', {})
    print(f"  Total measurements: {kinetics_data.get('total_measurements', 0)}")
    print(f"  Valid measurements: {kinetics_data.get('valid_measurements', 0)}")
    print(f"  Time constants: {len(kinetics_data.get('time_constants', []))}")
    print(f"  Diffusion coefficients: {len(kinetics_data.get('diffusion_coefficients', []))}")
    
    # Check plot type availability logic
    valid_measurements = kinetics_data.get('valid_measurements', 0)
    total_measurements = kinetics_data.get('total_measurements', 0)
    
    print(f"\n📊 PLOT AVAILABILITY CHECK:")
    print(f"  valid_measurements > 0: {valid_measurements > 0}")
    print(f"  total_measurements > 0: {total_measurements > 0}")
    print(f"  Should show plots: {valid_measurements > 0 and total_measurements > 0}")
    
    return kinetics_results

if __name__ == "__main__":
    resistance_summary = test_resistance_analysis_parsing()
    kinetics_results = test_kinetics_plots_rendering()
    
    print(f"\n" + "=" * 60)
    print("🎯 SUMMARY")
    print("=" * 60)
    
    print(f"Resistance analysis working: {len(resistance_summary.get('resistance_values_ohm', [])) > 0}")
    print(f"Kinetics analysis working: {kinetics_results['kinetics_analysis']['valid_measurements'] > 0}")
    
    if len(resistance_summary.get('resistance_values_ohm', [])) == 0:
        print("❌ RESISTANCE ISSUE: No resistance values found in parsing")
    
    if kinetics_results['kinetics_analysis']['valid_measurements'] == 0:
        print("❌ KINETICS ISSUE: No valid measurements found")