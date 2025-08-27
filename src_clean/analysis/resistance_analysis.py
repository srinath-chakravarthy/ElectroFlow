"""
Resistance Analysis Function

Registry-compatible analysis function for electrochemical resistance analysis.
Replaces the _run_resistance_analysis() method and ElectrochemicalInsights integration.
"""

from typing import List, Dict, Any
import json
import pandas as pd
import numpy as np

from .json_field_extractor import get_json_field_extractor


def resistance_analysis_function(segments: List[Dict[str, Any]], settings: Dict[str, Any], **kwargs) -> pd.DataFrame:
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
    include_segment_data = kwargs.get('include_segment_data', True)
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
        
        # Extract resistance data using JSONFieldExtractor with 'current_pulse' schema
        extractor = get_json_field_extractor()
        resistance_data = []
        
        for segment in galv_segments:
            analysis_results = segment.get('analysis_results', {})
            if not analysis_results or not isinstance(analysis_results, dict):
                continue
            
            # Use JSONFieldExtractor to get all current_pulse fields automatically
            extracted_fields = extractor.extract_all_fields(analysis_results, 'current_pulse')
            
            # Build resistance info with core segment data + extracted fields
            resistance_info = {
                'id': segment.get('id')
                # 'start_time_s': segment.get('start_time_s'),
                # 'duration_s': segment.get('duration_s'),
                # 'technique': segment.get('fundamental_technique')
            }
            
            # Add all extracted fields from current_pulse schema
            resistance_info.update(extracted_fields)
            
            # Calculate quality metrics using expert assessment
            ir_value = extracted_fields.get('ir_immediate_ohm')
            current_change = abs(segment.get('end_current_a', 0) - segment.get('start_current_a', 0))
            resistance_info['calculation_quality'] = _assess_resistance_quality(ir_value, current_change)
            
            resistance_data.append(resistance_info)
        
        if not resistance_data:
            # Return empty DataFrame with proper columns for error case
            return pd.DataFrame(columns=['id', 'error_message'])
        
        # Create analysis DataFrame from resistance data
        analysis_df = pd.DataFrame(resistance_data)
        
        if include_segment_data:
            # Create core DataFrame from segments (full segment data)
            core_df = pd.DataFrame(galv_segments)
            # Merge core + analysis columns using 'id'
            df = pd.merge(core_df, analysis_df, on='id', suffixes=('', '_analysis'))
        else:
            # Return only id + analytics columns for clean joining
            df = analysis_df.copy()
        
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
        
        # Add computed ratio columns for advanced plotting
        if 'ir_immediate_ohm' in df.columns and 'ir_30s_ohm' in df.columns:
            # Calculate instantaneous/30s resistance ratio 
            df['resistance_ratio_immediate_30s'] = df['ir_immediate_ohm'] / df['ir_30s_ohm']
            # Handle division by zero or invalid values
            df['resistance_ratio_immediate_30s'] = df['resistance_ratio_immediate_30s'].replace([float('inf'), -float('inf')], None)
        
        # Add electrochemical insights as columns
        insights = _interpret_resistance_data(resistance_data)
        for key, value in insights.items():
            df[f'insight_{key}'] = value
        
        # Apply analysis prefix to all columns except base columns
        base_columns = ['id']  # Don't prefix these
        analysis_id = 'resistance_analytics'
        
        # Create mapping for column renaming
        column_mapping = {}
        for col in df.columns:
            if col not in base_columns:
                column_mapping[col] = f"{analysis_id}_{col}"
        
        # Rename columns with prefix
        df = df.rename(columns=column_mapping)
            
        return df
        
    except Exception as e:
        # Return error as DataFrame with prefixed columns
        analysis_id = 'resistance_analytics'
        error_df = pd.DataFrame([{
            'id': None,
            f'{analysis_id}_error_message': f"Resistance analysis failed: {str(e)}",
            f'{analysis_id}_analysis_type': 'resistance_analysis'
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
    
    # Consistency analysis (from ECI 1.0)
    if immediate_resistances and len(immediate_resistances) > 1:
        resistance_std = np.std(immediate_resistances)
        cv = resistance_std / avg_resistance if avg_resistance > 0 else 0
        
        if cv < 0.1:  # CV < 10%
            insights["consistency"] = "Consistent resistance values across measurements"
        elif cv < 0.2:  # CV < 20% 
            insights["consistency"] = "Moderately consistent resistance values"
        else:
            insights["consistency"] = "Variable resistance - check measurement conditions"
            
        insights["coefficient_of_variation"] = f"CV: {cv:.1%}"
    
    return insights


def _assess_resistance_quality(resistance: float, current_change: float) -> str:
    """
    Assess resistance calculation quality using physics-based thresholds.
    
    Ported from ElectrochemicalInsights 1.0 _assess_resistance_quality() method.
    """
    if resistance is None:
        return "invalid"
    
    if abs(current_change) < 1e-6:  # No current change
        return "invalid"
    elif abs(resistance) > 1000:  # > 1kΩ seems unrealistic for battery
        return "poor"
    elif abs(resistance) < 0.001:  # < 1mΩ seems too low
        return "poor"
    else:
        return "good"