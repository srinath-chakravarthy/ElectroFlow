"""
Resistance Analysis Function

Registry-compatible analysis function for electrochemical resistance analysis.
Replaces the _run_resistance_analysis() method and ElectrochemicalInsights integration.
"""

from typing import List, Dict, Any
import json
import pandas as pd


def resistance_analysis_function(segments: List[Dict[str, Any]], settings: Dict[str, Any]) -> pd.DataFrame:
    """
    Calculate instantaneous resistance from galvanostatic segments.
    
    This function replaces:
    - _run_resistance_analysis() in main_tab.py
    - get_electrochemical_resistance_analysis() in api.py  
    - Integration with ElectrochemicalInsights
    
    Args:
        segments: List of segment dictionaries with analysis_results JSON
        settings: Analysis settings including time_points to analyze
        
    Returns:
        Dictionary with resistance analysis results
    """
    
    try:
        if not segments:
            return {"error": "No segments provided for resistance analysis"}
        
        # Filter for galvanostatic techniques
        galv_segments = [seg for seg in segments 
                        if seg.get('fundamental_technique', '').lower() in ['galvanostatic', 'galv', 'cc']]
        
        if not galv_segments:
            return {"error": "No galvanostatic segments found for resistance analysis"}
        
        # Get time points to analyze
        time_points = settings.get('time_points', ['immediate', '10s'])
        
        # Extract resistance data from analysis_results JSON
        resistance_data = []
        
        for segment in galv_segments:
            analysis_results = segment.get('analysis_results', {})
            if not analysis_results or not isinstance(analysis_results, dict):
                continue
            
            # Extract resistance values based on JSON structure
            resistance_info = {
                'segment_id': segment.get('id'),
                'start_time_s': segment.get('start_time_s'),
                'duration_s': segment.get('duration_s'),
                'technique': segment.get('fundamental_technique'),
                'baseline_voltage_v': analysis_results.get('baseline_voltage_v'),
                'average_current_a': analysis_results.get('average_current_a')
            }
            
            # Extract resistance at different time points
            for time_point in time_points:
                if time_point == 'immediate':
                    resistance_info['ir_immediate_ohm'] = analysis_results.get('ir_immediate_ohm')
                elif time_point == '10s':
                    resistance_info['ir_10s_ohm'] = analysis_results.get('ir_10s_ohm')
                elif time_point == '30s':
                    resistance_info['ir_30s_ohm'] = analysis_results.get('ir_30s_ohm')
            
            # Calculate quality metrics
            resistance_info['calculation_quality'] = 'good' if resistance_info.get('ir_immediate_ohm') else 'invalid'
            
            resistance_data.append(resistance_info)
        
        if not resistance_data:
            # Return empty DataFrame with proper columns for error case
            return pd.DataFrame(columns=['segment_id', 'error_message'])
        
        # Create core DataFrame from segments
        core_df = pd.DataFrame(galv_segments)
        
        # Create analysis DataFrame from resistance data
        analysis_df = pd.DataFrame(resistance_data)
        
        # Rename 'id' to 'segment_id' for consistency before merge
        core_df = core_df.rename(columns={'id': 'segment_id'})
        
        # Merge core + analysis columns
        df = pd.merge(core_df, analysis_df, on='segment_id', suffixes=('', '_analysis'))
        
        # Add standard columns required by registry
        df['analysis_type'] = 'resistance_analysis'
        df['quality_score'] = df['calculation_quality'].map({'good': 1.0, 'invalid': 0.0})
        
        # Add summary statistics as columns for easy access
        for time_point in time_points:
            col_name = f'ir_{time_point}_ohm' if time_point != 'immediate' else 'ir_immediate_ohm'
            if col_name in df.columns:
                values = df[col_name].dropna()
                if len(values) > 0:
                    df[f'{col_name}_mean'] = float(values.mean())
                    df[f'{col_name}_std'] = float(values.std())
        
        # Add electrochemical insights as columns
        insights = _interpret_resistance_data(resistance_data)
        for key, value in insights.items():
            df[f'insight_{key}'] = value
            
        return df
        
    except Exception as e:
        # Return error as DataFrame
        error_df = pd.DataFrame([{
            'segment_id': None,
            'error_message': f"Resistance analysis failed: {str(e)}",
            'analysis_type': 'resistance_analysis'
        }])
        return error_df


def _interpret_resistance_data(resistance_data: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Provide electrochemical interpretation of resistance data.
    
    Replaces the _interpret_resistance_analysis() method from ElectrochemicalInsights.
    """
    
    if not resistance_data:
        return {"general": "No resistance data available for interpretation"}
    
    insights = {}
    
    # Calculate average immediate resistance
    immediate_resistances = [r.get('ir_immediate_ohm') for r in resistance_data 
                           if r.get('ir_immediate_ohm') is not None]
    
    if immediate_resistances:
        avg_resistance = sum(immediate_resistances) / len(immediate_resistances)
        
        if avg_resistance < 0.01:  # < 10 mΩ
            insights["resistance_level"] = "Very low resistance - excellent conductivity"
        elif avg_resistance < 0.1:  # < 100 mΩ
            insights["resistance_level"] = "Low resistance - good conductivity" 
        elif avg_resistance < 1.0:  # < 1 Ω
            insights["resistance_level"] = "Moderate resistance"
        else:
            insights["resistance_level"] = "High resistance - check connections"
        
        insights["average_resistance"] = f"Average IR: {avg_resistance:.3f} Ω"
    
    # Quality assessment
    valid_count = len([r for r in resistance_data if r.get('calculation_quality') == 'good'])
    total_count = len(resistance_data)
    
    if valid_count == total_count:
        insights["data_quality"] = "All measurements valid"
    elif valid_count > total_count * 0.8:
        insights["data_quality"] = f"Good data quality ({valid_count}/{total_count} valid)"
    else:
        insights["data_quality"] = f"Poor data quality ({valid_count}/{total_count} valid)"
    
    return insights