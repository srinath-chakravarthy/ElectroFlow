"""
Equilibrium Analysis Function

Registry-compatible analysis function for equilibrium voltage analysis.
Replaces the get_electrochemical_equilibrium_analysis() method and ElectrochemicalInsights integration.
"""

from typing import List, Dict, Any
import json
import pandas as pd
import numpy as np


def equilibrium_analysis_function(segments: List[Dict[str, Any]], settings: Dict[str, Any]) -> pd.DataFrame:
    """
    Analyze equilibrium voltage from segment data.
    
    This function replaces:
    - get_electrochemical_equilibrium_analysis() in api.py
    - Integration with ElectrochemicalInsights
    
    Args:
        segments: List of segment dictionaries with analysis_results JSON
        settings: Analysis settings including stability criteria
        
    Returns:
        Dictionary with equilibrium analysis results
    """
    
    try:
        if not segments:
            return {"error": "No segments provided for equilibrium analysis"}
        
        # Get analysis settings
        min_duration = settings.get('min_duration_s', 60)  # Minimum duration for equilibrium
        max_drift_rate = settings.get('max_drift_rate_mv_per_min', 1.0)  # Maximum drift rate
        
        # Extract equilibrium data from segments
        equilibrium_data = []
        
        for segment in segments:
            analysis_results = segment.get('analysis_results', {})
            if not analysis_results or not isinstance(analysis_results, dict):
                continue
            
            # Extract equilibrium information
            equilibrium_info = {
                'segment_id': segment.get('id'),
                'start_time_s': segment.get('start_time_s'),
                'duration_s': segment.get('duration_s'),
                'technique': segment.get('fundamental_technique'),
                'start_voltage_v': segment.get('start_potential_v'),
                'end_voltage_v': segment.get('end_potential_v')
            }
            
            # Extract equilibrium analysis from JSON
            if 'equilibrium_voltage_v' in analysis_results:
                equilibrium_info['equilibrium_voltage_v'] = analysis_results['equilibrium_voltage_v']
            elif 'V_eq' in analysis_results:
                equilibrium_info['equilibrium_voltage_v'] = analysis_results['V_eq']
            
            # Extract stability metrics
            if 'is_stable' in analysis_results:
                equilibrium_info['is_stable'] = analysis_results['is_stable']
            
            if 'drift_rate_mv_min' in analysis_results:
                equilibrium_info['drift_rate_mv_min'] = analysis_results['drift_rate_mv_min']
            
            # Calculate voltage change if not available
            if equilibrium_info.get('start_voltage_v') and equilibrium_info.get('end_voltage_v'):
                voltage_change = equilibrium_info['end_voltage_v'] - equilibrium_info['start_voltage_v']
                equilibrium_info['voltage_change_v'] = voltage_change
                
                # Estimate drift rate if not available
                if 'drift_rate_mv_min' not in equilibrium_info and equilibrium_info.get('duration_s'):
                    duration_min = equilibrium_info['duration_s'] / 60.0
                    if duration_min > 0:
                        drift_rate_mv_min = abs(voltage_change * 1000 / duration_min)  # mV/min
                        equilibrium_info['drift_rate_mv_min'] = drift_rate_mv_min
            
            # Assess equilibrium quality
            duration_ok = equilibrium_info.get('duration_s', 0) >= min_duration
            drift_ok = equilibrium_info.get('drift_rate_mv_min', float('inf')) <= max_drift_rate
            
            equilibrium_info['meets_duration_criteria'] = duration_ok
            equilibrium_info['meets_drift_criteria'] = drift_ok
            equilibrium_info['equilibrium_quality'] = 'good' if (duration_ok and drift_ok) else 'poor'
            
            equilibrium_data.append(equilibrium_info)
        
        if not equilibrium_data:
            return pd.DataFrame(columns=['segment_id', 'error_message'])
        
        # Create core DataFrame from segments
        core_df = pd.DataFrame(segments)
        
        # Create analysis DataFrame
        analysis_df = pd.DataFrame(equilibrium_data)
        
        # Rename 'id' to 'segment_id' for consistency before merge
        core_df = core_df.rename(columns={'id': 'segment_id'})
        
        # Merge core + analysis columns
        df = pd.merge(core_df, analysis_df, on='segment_id', suffixes=('', '_analysis'))
        df['analysis_type'] = 'equilibrium_analysis'
        df['quality_score'] = df['equilibrium_quality'].map({'good': 1.0, 'poor': 0.0})
        
        # Calculate summary statistics
        summary = _calculate_equilibrium_summary(equilibrium_data, settings)
        
        # Add summary and insights as columns
        for key, value in summary.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    df[f'summary_{key}_{sub_key}'] = sub_value
            else:
                df[f'summary_{key}'] = value
                
        # Electrochemical insights
        insights = _interpret_equilibrium_data(equilibrium_data, settings)
        for key, value in insights.items():
            df[f'insight_{key}'] = value
            
        return df
        
    except Exception as e:
        error_df = pd.DataFrame([{
            'segment_id': None,
            'error_message': f"Equilibrium analysis failed: {str(e)}",
            'analysis_type': 'equilibrium_analysis'
        }])
        return error_df


def _calculate_equilibrium_summary(equilibrium_data: List[Dict[str, Any]], 
                                 settings: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate summary statistics for equilibrium data."""
    
    if not equilibrium_data:
        return {}
    
    # Filter high-quality measurements
    good_quality = [e for e in equilibrium_data if e.get('equilibrium_quality') == 'good']
    
    summary = {
        'total_segments': len(equilibrium_data),
        'good_quality_segments': len(good_quality),
        'quality_ratio': len(good_quality) / len(equilibrium_data) if equilibrium_data else 0
    }
    
    # Equilibrium voltage statistics
    eq_voltages = [e.get('equilibrium_voltage_v') for e in good_quality 
                  if e.get('equilibrium_voltage_v') is not None]
    
    if eq_voltages:
        summary['equilibrium_voltage_stats'] = {
            'mean_v': np.mean(eq_voltages),
            'std_v': np.std(eq_voltages),
            'min_v': np.min(eq_voltages),
            'max_v': np.max(eq_voltages),
            'count': len(eq_voltages)
        }
    
    # Drift rate statistics
    drift_rates = [e.get('drift_rate_mv_min') for e in good_quality 
                  if e.get('drift_rate_mv_min') is not None]
    
    if drift_rates:
        summary['drift_rate_stats'] = {
            'mean_mv_min': np.mean(drift_rates),
            'std_mv_min': np.std(drift_rates),
            'min_mv_min': np.min(drift_rates),
            'max_mv_min': np.max(drift_rates),
            'count': len(drift_rates)
        }
    
    # Duration statistics
    durations = [e.get('duration_s') for e in equilibrium_data 
                if e.get('duration_s') is not None]
    
    if durations:
        summary['duration_stats'] = {
            'mean_s': np.mean(durations),
            'std_s': np.std(durations),
            'min_s': np.min(durations),
            'max_s': np.max(durations)
        }
    
    return summary


def _interpret_equilibrium_data(equilibrium_data: List[Dict[str, Any]], 
                              settings: Dict[str, Any]) -> Dict[str, str]:
    """
    Provide electrochemical interpretation of equilibrium data.
    
    Replaces the _interpret_equilibrium_analysis() method from ElectrochemicalInsights.
    """
    
    if not equilibrium_data:
        return {"general": "No equilibrium data available for interpretation"}
    
    insights = {}
    good_quality = [e for e in equilibrium_data if e.get('equilibrium_quality') == 'good']
    quality_ratio = len(good_quality) / len(equilibrium_data)
    
    # Quality assessment
    if quality_ratio > 0.8:
        insights["data_quality"] = "Excellent equilibrium data quality"
    elif quality_ratio > 0.5:
        insights["data_quality"] = "Good equilibrium data quality"
    else:
        insights["data_quality"] = "Poor equilibrium data quality - check measurement conditions"
    
    # Equilibrium voltage analysis
    eq_voltages = [e.get('equilibrium_voltage_v') for e in good_quality 
                  if e.get('equilibrium_voltage_v') is not None]
    
    if eq_voltages:
        voltage_range = np.max(eq_voltages) - np.min(eq_voltages)
        mean_voltage = np.mean(eq_voltages)
        
        insights["equilibrium_voltage"] = f"Average equilibrium: {mean_voltage:.3f} V"
        
        if voltage_range < 0.01:  # < 10 mV
            insights["voltage_stability"] = "Excellent voltage stability"
        elif voltage_range < 0.05:  # < 50 mV
            insights["voltage_stability"] = "Good voltage stability"
        else:
            insights["voltage_stability"] = "Poor voltage stability - investigate system"
    
    # Drift rate analysis
    drift_rates = [e.get('drift_rate_mv_min') for e in good_quality 
                  if e.get('drift_rate_mv_min') is not None]
    
    if drift_rates:
        avg_drift = np.mean(drift_rates)
        max_allowed = settings.get('max_drift_rate_mv_per_min', 1.0)
        
        if avg_drift < max_allowed * 0.5:
            insights["drift_assessment"] = f"Low drift rate ({avg_drift:.2f} mV/min) - stable equilibrium"
        elif avg_drift < max_allowed:
            insights["drift_assessment"] = f"Acceptable drift rate ({avg_drift:.2f} mV/min)"
        else:
            insights["drift_assessment"] = f"High drift rate ({avg_drift:.2f} mV/min) - poor equilibrium"
    
    # Duration assessment
    durations = [e.get('duration_s') for e in equilibrium_data 
                if e.get('duration_s') is not None]
    
    if durations:
        avg_duration = np.mean(durations)
        min_required = settings.get('min_duration_s', 60)
        
        if avg_duration >= min_required * 2:
            insights["duration_assessment"] = f"Long equilibration time ({avg_duration/60:.1f} min) - thorough"
        elif avg_duration >= min_required:
            insights["duration_assessment"] = f"Adequate equilibration time ({avg_duration/60:.1f} min)"
        else:
            insights["duration_assessment"] = f"Short equilibration time ({avg_duration/60:.1f} min) - may be incomplete"
    
    return insights