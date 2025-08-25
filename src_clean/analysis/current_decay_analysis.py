"""
Current Decay Analysis Function

Registry-compatible analysis function for current decay kinetics analysis.
Replaces the get_electrochemical_current_decay_analysis() method and ElectrochemicalInsights integration.
"""

from typing import List, Dict, Any
import json
import pandas as pd
import numpy as np


def current_decay_analysis_function(segments: List[Dict[str, Any]], settings: Dict[str, Any]) -> pd.DataFrame:
    """
    Analyze current decay kinetics from potentiostatic segments.
    
    This function replaces:
    - get_electrochemical_current_decay_analysis() in api.py
    - Integration with ElectrochemicalInsights
    
    Args:
        segments: List of segment dictionaries with analysis_results JSON
        settings: Analysis settings including fit criteria
        
    Returns:
        Dictionary with current decay analysis results
    """
    
    try:
        if not segments:
            return {"error": "No segments provided for current decay analysis"}
        
        # Filter for potentiostatic techniques
        potentiostatic_segments = [seg for seg in segments 
                                 if seg.get('fundamental_technique', '').lower() in 
                                 ['potentiostatic', 'potentio', 'cv', 'chronoamperometry', 'ca']]
        
        if not potentiostatic_segments:
            return {"error": "No potentiostatic segments found for current decay analysis"}
        
        # Get analysis settings
        min_r_squared = settings.get('min_r_squared', 0.8)
        min_duration = settings.get('min_duration_s', 10)  # Minimum duration for meaningful decay
        
        # Extract decay data from analysis_results JSON
        decay_data = []
        
        for segment in potentiostatic_segments:
            analysis_results = segment.get('analysis_results', {})
            if not analysis_results or not isinstance(analysis_results, dict):
                continue
            
            # Extract current decay information
            decay_info = {
                'segment_id': segment.get('id'),
                'start_time_s': segment.get('start_time_s'),
                'duration_s': segment.get('duration_s'),
                'technique': segment.get('fundamental_technique'),
                'start_current_a': segment.get('start_current_a'),
                'end_current_a': segment.get('end_current_a'),
                'applied_voltage_v': segment.get('start_potential_v')  # Potentiostatic voltage
            }
            
            # Extract decay fit parameters from JSON
            fit_data = _extract_decay_fit_parameters(analysis_results)
            decay_info.update(fit_data)
            
            # Calculate decay metrics if current data available
            if decay_info.get('start_current_a') and decay_info.get('end_current_a'):
                start_current = abs(decay_info['start_current_a'])  # Use absolute current
                end_current = abs(decay_info['end_current_a'])
                
                if start_current > 0:
                    decay_ratio = end_current / start_current
                    decay_info['current_decay_ratio'] = decay_ratio
                    
                    # Percent decay
                    decay_percent = (1 - decay_ratio) * 100
                    decay_info['current_decay_percent'] = decay_percent
            
            # Quality assessment
            duration_ok = decay_info.get('duration_s', 0) >= min_duration
            fit_ok = decay_info.get('r_squared', 0) >= min_r_squared
            
            decay_info['meets_duration_criteria'] = duration_ok
            decay_info['meets_fit_criteria'] = fit_ok
            decay_info['decay_quality'] = 'good' if (duration_ok and fit_ok) else 'poor'
            
            decay_data.append(decay_info)
        
        if not decay_data:
            return pd.DataFrame(columns=['segment_id', 'error_message'])
        
        # Create core DataFrame from segments
        core_df = pd.DataFrame(potentiostatic_segments)
        
        # Create analysis DataFrame
        analysis_df = pd.DataFrame(decay_data)
        
        # Rename 'id' to 'segment_id' for consistency before merge
        core_df = core_df.rename(columns={'id': 'segment_id'})
        
        # Merge core + analysis columns
        df = pd.merge(core_df, analysis_df, on='segment_id', suffixes=('', '_analysis'))
        df['analysis_type'] = 'current_decay_analysis'
        df['quality_score'] = df['decay_quality'].map({'good': 1.0, 'poor': 0.0})
        
        # Calculate summary statistics and add as columns
        summary = _calculate_decay_summary(decay_data, settings)
        for key, value in summary.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    df[f'summary_{key}_{sub_key}'] = sub_value
            else:
                df[f'summary_{key}'] = value
                
        # Add electrochemical insights as columns
        insights = _interpret_decay_data(decay_data, settings)
        for key, value in insights.items():
            df[f'insight_{key}'] = value
            
        return df
        
    except Exception as e:
        error_df = pd.DataFrame([{
            'segment_id': None,
            'error_message': f"Current decay analysis failed: {str(e)}",
            'analysis_type': 'current_decay_analysis'
        }])
        return error_df


def _extract_decay_fit_parameters(analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract current decay fit parameters from JSON analysis_results.
    
    Looks for exponential decay fits: I(t) = I0 * exp(-t/tau) + I_ss
    """
    
    fit_data = {}
    
    # Try to extract exponential decay parameters
    if 'current_decay_fit' in analysis_results:
        decay_fit = analysis_results['current_decay_fit']
        fit_data.update({
            'i0_a': decay_fit.get('I0'),  # Initial current
            'i_ss_a': decay_fit.get('I_ss'),  # Steady-state current
            'tau_s': decay_fit.get('tau'),  # Time constant
            'r_squared': decay_fit.get('r_squared'),
            'fit_type': 'exponential_decay'
        })
    
    # Try alternative JSON structures
    elif 'decay_parameters' in analysis_results:
        params = analysis_results['decay_parameters']
        fit_data.update({
            'i0_a': params.get('initial_current_a'),
            'i_ss_a': params.get('steady_state_current_a'),
            'tau_s': params.get('time_constant_s'),
            'r_squared': params.get('fit_quality'),
            'fit_type': 'exponential_decay'
        })
    
    # Try flat JSON structure (direct key access)
    else:
        possible_keys = {
            'I0': 'i0_a',
            'I_ss': 'i_ss_a',
            'tau': 'tau_s',
            'decay_tau': 'tau_s',
            'initial_current': 'i0_a',
            'steady_state_current': 'i_ss_a',
            'time_constant': 'tau_s',
            'r_squared': 'r_squared'
        }
        
        for json_key, internal_key in possible_keys.items():
            if json_key in analysis_results:
                fit_data[internal_key] = analysis_results[json_key]
        
        if 'i0_a' in fit_data or 'tau_s' in fit_data:
            fit_data['fit_type'] = 'exponential_decay'
    
    return fit_data


def _calculate_decay_summary(decay_data: List[Dict[str, Any]], 
                           settings: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate summary statistics for current decay data."""
    
    if not decay_data:
        return {}
    
    # Filter high-quality fits
    good_quality = [d for d in decay_data if d.get('decay_quality') == 'good']
    
    summary = {
        'total_segments': len(decay_data),
        'good_quality_fits': len(good_quality),
        'fit_success_rate': len(good_quality) / len(decay_data) if decay_data else 0
    }
    
    # Time constant statistics
    tau_values = [d.get('tau_s') for d in good_quality 
                 if d.get('tau_s') is not None]
    
    if tau_values:
        summary['time_constant_stats'] = {
            'mean_s': np.mean(tau_values),
            'std_s': np.std(tau_values),
            'min_s': np.min(tau_values),
            'max_s': np.max(tau_values),
            'count': len(tau_values)
        }
    
    # Current decay statistics
    decay_ratios = [d.get('current_decay_ratio') for d in good_quality 
                   if d.get('current_decay_ratio') is not None]
    
    if decay_ratios:
        summary['decay_ratio_stats'] = {
            'mean': np.mean(decay_ratios),
            'std': np.std(decay_ratios),
            'min': np.min(decay_ratios),
            'max': np.max(decay_ratios)
        }
    
    # R² distribution
    r_squared_values = [d.get('r_squared', 0) for d in good_quality]
    if r_squared_values:
        summary['r_squared_stats'] = {
            'mean': np.mean(r_squared_values),
            'std': np.std(r_squared_values),
            'min': np.min(r_squared_values),
            'max': np.max(r_squared_values)
        }
    
    return summary


def _interpret_decay_data(decay_data: List[Dict[str, Any]], 
                        settings: Dict[str, Any]) -> Dict[str, str]:
    """
    Provide electrochemical interpretation of current decay data.
    
    Replaces the _interpret_current_decay() method from ElectrochemicalInsights.
    """
    
    if not decay_data:
        return {"general": "No current decay data available for interpretation"}
    
    insights = {}
    good_quality = [d for d in decay_data if d.get('decay_quality') == 'good']
    
    # Quality assessment
    fit_success_rate = len(good_quality) / len(decay_data)
    if fit_success_rate > 0.8:
        insights["fit_quality"] = "Excellent current decay fits"
    elif fit_success_rate > 0.5:
        insights["fit_quality"] = "Good current decay fits"
    else:
        insights["fit_quality"] = "Poor current decay fits - check potentiostatic conditions"
    
    # Time constant analysis
    tau_values = [d.get('tau_s') for d in good_quality 
                 if d.get('tau_s') is not None]
    
    if tau_values:
        avg_tau = np.mean(tau_values)
        
        if avg_tau < 1:
            insights["decay_kinetics"] = f"Fast current decay (τ = {avg_tau:.2f} s) - rapid equilibration"
        elif avg_tau < 10:
            insights["decay_kinetics"] = f"Moderate current decay (τ = {avg_tau:.2f} s)"
        elif avg_tau < 100:
            insights["decay_kinetics"] = f"Slow current decay (τ = {avg_tau:.1f} s)"
        else:
            insights["decay_kinetics"] = f"Very slow current decay (τ = {avg_tau:.0f} s) - slow kinetics"
    
    # Current magnitude analysis
    initial_currents = [abs(d.get('i0_a', 0)) for d in good_quality 
                       if d.get('i0_a') is not None]
    
    if initial_currents:
        avg_initial = np.mean(initial_currents)
        
        if avg_initial > 1e-3:  # > 1 mA
            insights["current_magnitude"] = f"High initial current ({avg_initial*1000:.1f} mA)"
        elif avg_initial > 1e-6:  # > 1 µA
            insights["current_magnitude"] = f"Moderate initial current ({avg_initial*1e6:.1f} µA)"
        else:
            insights["current_magnitude"] = f"Low initial current ({avg_initial*1e9:.1f} nA)"
    
    # Decay completeness analysis
    decay_percentages = [d.get('current_decay_percent') for d in good_quality 
                        if d.get('current_decay_percent') is not None]
    
    if decay_percentages:
        avg_decay = np.mean(decay_percentages)
        
        if avg_decay > 90:
            insights["decay_completeness"] = f"Excellent current decay ({avg_decay:.1f}% reduction)"
        elif avg_decay > 70:
            insights["decay_completeness"] = f"Good current decay ({avg_decay:.1f}% reduction)"
        elif avg_decay > 50:
            insights["decay_completeness"] = f"Moderate current decay ({avg_decay:.1f}% reduction)"
        else:
            insights["decay_completeness"] = f"Poor current decay ({avg_decay:.1f}% reduction) - incomplete equilibration"
    
    return insights