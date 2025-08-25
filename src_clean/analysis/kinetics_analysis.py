"""
Kinetics Analysis Function

Registry-compatible analysis function for relaxation kinetics analysis.
Replaces the _run_kinetics_analysis() method and ElectrochemicalInsights integration.
"""

from typing import List, Dict, Any
import json
import pandas as pd
import numpy as np


def kinetics_analysis_function(segments: List[Dict[str, Any]], settings: Dict[str, Any]) -> pd.DataFrame:
    """
    Analyze relaxation kinetics from REST phase segments.
    
    This function replaces:
    - _run_kinetics_analysis() in main_tab.py
    - get_electrochemical_rest_analysis() in api.py
    - Integration with ElectrochemicalInsights
    
    Args:
        segments: List of segment dictionaries with analysis_results JSON
        settings: Analysis settings including fit_type and quality thresholds
        
    Returns:
        Dictionary with kinetics analysis results
    """
    
    try:
        if not segments:
            return {"error": "No segments provided for kinetics analysis"}
        
        # Filter for REST technique segments
        rest_segments = [seg for seg in segments 
                        if seg.get('fundamental_technique', '').lower() in ['rest', 'ocp']]
        
        if not rest_segments:
            return {"error": "No REST segments found for kinetics analysis"}
        
        # Get analysis settings
        fit_type = settings.get('fit_type', 'auto_best')
        min_r_squared = settings.get('min_r_squared', 0.8)
        
        # Extract kinetics data from analysis_results JSON
        kinetics_data = []
        
        for segment in rest_segments:
            analysis_results = segment.get('analysis_results', {})
            if not analysis_results or not isinstance(analysis_results, dict):
                continue
            
            # Extract relaxation kinetics based on JSON structure
            kinetics_info = {
                'segment_id': segment.get('id'),
                'start_time_s': segment.get('start_time_s'),
                'duration_s': segment.get('duration_s'),
                'technique': segment.get('fundamental_technique'),
                'start_voltage_v': segment.get('start_potential_v'),
                'end_voltage_v': segment.get('end_potential_v')
            }
            
            # Extract fit parameters - try different JSON structures
            fit_data = _extract_fit_parameters(analysis_results, fit_type)
            kinetics_info.update(fit_data)
            
            # Calculate derived parameters
            if kinetics_info.get('start_voltage_v') and kinetics_info.get('end_voltage_v'):
                kinetics_info['voltage_recovery_v'] = (kinetics_info['end_voltage_v'] - 
                                                     kinetics_info['start_voltage_v'])
            
            # Quality assessment
            r_squared = kinetics_info.get('r_squared', 0)
            kinetics_info['fit_quality'] = 'good' if r_squared >= min_r_squared else 'poor'
            
            kinetics_data.append(kinetics_info)
        
        if not kinetics_data:
            # Return empty DataFrame with proper columns for error case
            return pd.DataFrame(columns=['segment_id', 'error_message'])
        
        # Filter by quality if requested
        if min_r_squared > 0:
            high_quality_data = [k for k in kinetics_data if k.get('r_squared', 0) >= min_r_squared]
        else:
            high_quality_data = kinetics_data
        
        # Create core DataFrame from segments
        core_df = pd.DataFrame(rest_segments)
        
        # Create analysis DataFrame from kinetics data
        analysis_df = pd.DataFrame(kinetics_data)
        
        # Rename 'id' to 'segment_id' for consistency before merge
        core_df = core_df.rename(columns={'id': 'segment_id'})
        
        # Merge core + analysis columns
        df = pd.merge(core_df, analysis_df, on='segment_id', suffixes=('', '_analysis'))
        
        # Add standard columns required by registry
        df['analysis_type'] = 'kinetics_analysis'
        df['quality_score'] = df.get('r_squared', 0.0)
        
        # Add summary statistics as columns
        summary = _calculate_kinetics_summary(kinetics_data, high_quality_data)
        for key, value in summary.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    df[f'summary_{key}_{sub_key}'] = sub_value
            else:
                df[f'summary_{key}'] = value
        
        # Add electrochemical insights as columns
        insights = _interpret_kinetics_data(kinetics_data, settings)
        for key, value in insights.items():
            df[f'insight_{key}'] = value
            
        # Add analysis parameters as columns
        df['fit_type_used'] = fit_type
        df['min_r_squared_threshold'] = min_r_squared
        df['is_high_quality'] = df['r_squared'] >= min_r_squared
            
        return df
        
    except Exception as e:
        # Return error as DataFrame
        error_df = pd.DataFrame([{
            'segment_id': None,
            'error_message': f"Kinetics analysis failed: {str(e)}",
            'analysis_type': 'kinetics_analysis'
        }])
        return error_df


def _extract_fit_parameters(analysis_results: Dict[str, Any], fit_type: str) -> Dict[str, Any]:
    """
    Extract fit parameters from JSON analysis_results.
    
    Handles different JSON structures and fit types (exponential, sqrt_t, auto_best).
    """
    
    fit_data = {}
    
    # Try to extract exponential fit parameters
    if 'exponential_fit' in analysis_results:
        exp_fit = analysis_results['exponential_fit']
        fit_data.update({
            'v_equilibrium_v': exp_fit.get('V_eq'),
            'tau_s': exp_fit.get('tau'),
            'r_squared': exp_fit.get('r_squared'),
            'fit_type': 'exponential'
        })
    
    # Try to extract sqrt(t) fit parameters  
    if 'sqrt_t_fit' in analysis_results:
        sqrt_fit = analysis_results['sqrt_t_fit']
        fit_data.update({
            'v_infinity_v': sqrt_fit.get('V_infinity'),
            'a_coefficient': sqrt_fit.get('A'),
            'r_squared': sqrt_fit.get('r_squared'),
            'fit_type': 'sqrt_t'
        })
    
    # Handle flat JSON structure (direct key access)
    if not fit_data:
        # Try direct key extraction
        possible_keys = {
            'V_eq': 'v_equilibrium_v',
            'tau': 'tau_s', 
            'V_infinity': 'v_infinity_v',
            'A': 'a_coefficient',
            'r_squared': 'r_squared'
        }
        
        for json_key, internal_key in possible_keys.items():
            if json_key in analysis_results:
                fit_data[internal_key] = analysis_results[json_key]
        
        # Determine fit type based on available parameters
        if 'v_equilibrium_v' in fit_data and 'tau_s' in fit_data:
            fit_data['fit_type'] = 'exponential'
        elif 'v_infinity_v' in fit_data and 'a_coefficient' in fit_data:
            fit_data['fit_type'] = 'sqrt_t'
    
    # Auto-best fit selection
    if fit_type == 'auto_best' and 'fit_type' not in fit_data:
        # If both fits are available, choose the better one based on R²
        exp_r2 = analysis_results.get('exponential_fit', {}).get('r_squared', 0)
        sqrt_r2 = analysis_results.get('sqrt_t_fit', {}).get('r_squared', 0)
        
        if exp_r2 > sqrt_r2:
            fit_data['fit_type'] = 'exponential'
        else:
            fit_data['fit_type'] = 'sqrt_t'
    
    return fit_data


def _calculate_kinetics_summary(kinetics_data: List[Dict[str, Any]], 
                               high_quality_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary statistics for kinetics data."""
    
    summary = {
        'total_segments': len(kinetics_data),
        'high_quality_fits': len(high_quality_data),
        'fit_success_rate': len(high_quality_data) / len(kinetics_data) if kinetics_data else 0
    }
    
    if high_quality_data:
        # R² distribution
        r_squared_values = [k.get('r_squared', 0) for k in high_quality_data]
        summary['r_squared_stats'] = {
            'mean': np.mean(r_squared_values),
            'std': np.std(r_squared_values),
            'min': np.min(r_squared_values),
            'max': np.max(r_squared_values)
        }
        
        # Voltage recovery analysis
        voltage_recoveries = [k.get('voltage_recovery_v') for k in high_quality_data 
                            if k.get('voltage_recovery_v') is not None]
        if voltage_recoveries:
            summary['voltage_recovery_stats'] = {
                'mean_v': np.mean(voltage_recoveries),
                'std_v': np.std(voltage_recoveries),
                'min_v': np.min(voltage_recoveries),
                'max_v': np.max(voltage_recoveries)
            }
        
        # Time constant analysis (for exponential fits)
        tau_values = [k.get('tau_s') for k in high_quality_data 
                     if k.get('tau_s') is not None and k.get('fit_type') == 'exponential']
        if tau_values:
            summary['tau_stats'] = {
                'mean_s': np.mean(tau_values),
                'std_s': np.std(tau_values),
                'min_s': np.min(tau_values),
                'max_s': np.max(tau_values)
            }
    
    return summary


def _interpret_kinetics_data(kinetics_data: List[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, str]:
    """
    Provide electrochemical interpretation of kinetics data.
    
    Replaces the _interpret_relaxation_kinetics() method from ElectrochemicalInsights.
    """
    
    if not kinetics_data:
        return {"general": "No kinetics data available for interpretation"}
    
    insights = {}
    min_r_squared = settings.get('min_r_squared', 0.8)
    
    # Fit quality assessment
    high_quality_fits = [k for k in kinetics_data if k.get('r_squared', 0) >= min_r_squared]
    fit_success_rate = len(high_quality_fits) / len(kinetics_data)
    
    if fit_success_rate > 0.8:
        insights["fit_quality"] = "Excellent fit quality - reliable kinetics analysis"
    elif fit_success_rate > 0.5:
        insights["fit_quality"] = "Good fit quality - generally reliable analysis"
    else:
        insights["fit_quality"] = "Poor fit quality - results should be interpreted carefully"
    
    # Time constant analysis
    if high_quality_fits:
        tau_values = [k.get('tau_s') for k in high_quality_fits 
                     if k.get('tau_s') is not None]
        
        if tau_values:
            avg_tau = np.mean(tau_values)
            if avg_tau < 10:
                insights["relaxation_speed"] = "Fast relaxation (τ < 10s) - rapid equilibration"
            elif avg_tau < 100:
                insights["relaxation_speed"] = "Moderate relaxation (10s < τ < 100s)"
            else:
                insights["relaxation_speed"] = "Slow relaxation (τ > 100s) - slow equilibration"
            
            insights["average_time_constant"] = f"Average τ: {avg_tau:.1f} s"
    
    # Voltage recovery analysis
    voltage_recoveries = [k.get('voltage_recovery_v') for k in high_quality_fits 
                         if k.get('voltage_recovery_v') is not None]
    
    if voltage_recoveries:
        avg_recovery = np.mean(voltage_recoveries)
        if abs(avg_recovery) > 0.1:
            insights["voltage_recovery"] = f"Significant voltage recovery: {avg_recovery:.3f} V"
        else:
            insights["voltage_recovery"] = f"Small voltage recovery: {avg_recovery:.3f} V"
    
    return insights