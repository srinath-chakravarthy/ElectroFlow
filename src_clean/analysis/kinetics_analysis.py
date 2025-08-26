"""
Kinetics Analysis Function

Registry-compatible analysis function for relaxation kinetics analysis.
Replaces the _run_kinetics_analysis() method and ElectrochemicalInsights integration.
"""

from typing import List, Dict, Any, Optional
import json
import pandas as pd
import numpy as np

from .json_field_extractor import get_json_field_extractor


def kinetics_analysis_function(segments: List[Dict[str, Any]], settings: Dict[str, Any], **kwargs) -> pd.DataFrame:
    """
    Analyze relaxation kinetics from REST phase segments.
    
    This function replaces:
    - _run_kinetics_analysis() in main_tab.py
    - get_electrochemical_rest_analysis() in api.py
    - Integration with ElectrochemicalInsights
    
    Args:
        segments: List of segment dictionaries with analysis_results JSON
        settings: Analysis settings including fit_type and quality thresholds
        include_segment_data: If True (default), include all segment columns.
                            If False, return only id + analytics columns.
        
    Returns:
        DataFrame with kinetics analysis results
    """
    include_segment_data = kwargs.get('include_segment_data', True)
    try:
        if not segments:
            return {"error": "No segments provided for kinetics analysis"}
        
        # Filter for REST technique segments
        rest_segments = [seg for seg in segments 
                        if seg.get('fundamental_technique', '').lower() in ['rest', 'ocp', 'ocv']]
        
        if not rest_segments:
            return {"error": "No REST segments found for kinetics analysis"}
        
        # Apply pre-analysis filters from settings
        # TODO: Debug filtering issues - temporarily disabled
        # filtered_segments = _apply_pre_analysis_filters(rest_segments, settings)
        # if not filtered_segments:
        #     return pd.DataFrame(columns=['segment_id', 'error_message'])
        filtered_segments = rest_segments  # Use all REST segments for now
        
        # Get analysis settings
        fit_type = settings.get('fit_type', 'auto_best')
        min_r_squared = settings.get('min_r_squared', 0.8)
        
        # Extract kinetics data from analysis_results JSON
        kinetics_data = []
        
        for segment in filtered_segments:
            analysis_results = segment.get('analysis_results', {})
            if not analysis_results or not isinstance(analysis_results, dict):
                continue
            
            # Extract relaxation kinetics based on JSON structure
            kinetics_info = {
                'id': segment.get('id')
                # 'start_time_s': segment.get('start_time_s'),
                # 'duration_s': segment.get('duration_s'),
                # 'technique': segment.get('fundamental_technique'),
                # 'start_voltage_v': segment.get('start_potential_v'),
                # 'end_voltage_v': segment.get('end_potential_v')
            }
            
            # Extract fit parameters - try different JSON structures
            fit_data = _extract_fit_parameters(analysis_results, fit_type)
            kinetics_info.update(fit_data)
            
            # Calculate derived parameters
            if segment.get('start_voltage_v') and segment.get('end_voltage_v'):
                kinetics_info['voltage_recovery_v'] = (segment['end_voltage_v'] -
                                                     segment['start_voltage_v'])
            
            # Quality assessment using expert methods
            r_squared = kinetics_info.get('r_squared', 0)
            kinetics_info['fit_quality'] = _assess_fit_quality(r_squared)
            
            # Diffusion regime assessment
            time_constant = kinetics_info.get('time_constant_s')
            kinetics_info['diffusion_regime'] = _assess_diffusion_regime(time_constant)
            
            kinetics_data.append(kinetics_info)
        
        if not kinetics_data:
            # Return empty DataFrame with proper columns for error case
            return pd.DataFrame(columns=['id', 'error_message'])
        
        # Filter by quality if requested
        if min_r_squared > 0:
            high_quality_data = [k for k in kinetics_data if k.get('r_squared', 0) >= min_r_squared]
        else:
            high_quality_data = kinetics_data
        
        # Create analysis DataFrame from kinetics data
        analysis_df = pd.DataFrame(kinetics_data)
        
        if include_segment_data:
            # Create core DataFrame from filtered segments (full segment data)
            core_df = pd.DataFrame(filtered_segments)
            # Merge core + analysis columns using 'id'
            df = pd.merge(core_df, analysis_df, on='id', suffixes=('', '_analysis'))
        else:
            # Return only id + analytics columns for clean joining
            df = analysis_df.copy()
        
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
            'id': None,
            'error_message': f"Kinetics analysis failed: {str(e)}",
            'analysis_type': 'kinetics_analysis'
        }])
        return error_df


def _extract_fit_parameters(analysis_results: Dict[str, Any], fit_type: str) -> Dict[str, Any]:
    """
    Extract fit parameters using JSONFieldExtractor with exponential_fit and sqrt_fit schemas.
    
    Handles auto-best fit selection between exponential and sqrt(t) models.
    """
    
    extractor = get_json_field_extractor()
    fit_data = {}
    
    # Extract exponential fit fields using analytics_config schema
    exp_fields = extractor.extract_all_fields(analysis_results, 'exponential_fit')
    exp_fields_quality, exp_quality = extractor.extract_with_quality(analysis_results, 'exponential_fit')
    
    # Extract sqrt fit fields using analytics_config schema  
    sqrt_fields = extractor.extract_all_fields(analysis_results, 'sqrt_fit')
    sqrt_fields_quality, sqrt_quality = extractor.extract_with_quality(analysis_results, 'sqrt_fit')
    
    # Auto-best fit selection based on R² and data quality
    if fit_type == 'auto_best':
        exp_r2 = exp_fields.get('r_squared', 0)
        sqrt_r2 = sqrt_fields.get('r_squared', 0)
        
        # Choose best fit based on R² and quality
        if exp_r2 > sqrt_r2 and exp_quality > 0.5:
            fit_data.update(exp_fields)
            fit_data['fit_type'] = 'exponential'
            fit_data['selection_reason'] = f'Exponential R²={exp_r2:.3f} > Sqrt R²={sqrt_r2:.3f}'
        elif sqrt_quality > 0.5:
            fit_data.update(sqrt_fields)  
            fit_data['fit_type'] = 'sqrt_t'
            fit_data['selection_reason'] = f'Sqrt R²={sqrt_r2:.3f} > Exponential R²={exp_r2:.3f}'
        elif exp_quality > sqrt_quality:
            fit_data.update(exp_fields)
            fit_data['fit_type'] = 'exponential'
            fit_data['selection_reason'] = f'Exponential quality={exp_quality:.2f} better'
        else:
            fit_data.update(sqrt_fields)
            fit_data['fit_type'] = 'sqrt_t'
            fit_data['selection_reason'] = f'Sqrt quality={sqrt_quality:.2f} better'
    elif fit_type == 'exponential':
        fit_data.update(exp_fields)
        fit_data['fit_type'] = 'exponential'
    elif fit_type in ['sqrt_t', 'sqrt']:
        fit_data.update(sqrt_fields)
        fit_data['fit_type'] = 'sqrt_t'
    else:
        # Default to auto_best behavior
        if exp_fields.get('r_squared', 0) > sqrt_fields.get('r_squared', 0):
            fit_data.update(exp_fields)
            fit_data['fit_type'] = 'exponential'
        else:
            fit_data.update(sqrt_fields)
            fit_data['fit_type'] = 'sqrt_t'
    
    # Add data quality scores for diagnostics
    fit_data['extraction_quality_exp'] = exp_quality
    fit_data['extraction_quality_sqrt'] = sqrt_quality
    
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
    
    # Diffusion regime counting (from ECI 1.0)
    regimes = [k.get('diffusion_regime', 'unknown') for k in kinetics_data]
    regime_counts = {regime: regimes.count(regime) for regime in set(regimes) if regime != 'unknown'}
    
    if regime_counts:
        total_known = sum(regime_counts.values())
        if regime_counts.get('diffusion_limited', 0) > total_known * 0.5:
            insights['dominant_process'] = 'Diffusion-limited relaxation dominates'
        elif regime_counts.get('fast_kinetics', 0) > total_known * 0.5:
            insights['dominant_process'] = 'Fast charge transfer kinetics'  
        else:
            insights['dominant_process'] = 'Mixed kinetic and diffusion control'
    
    # Fit quality assessment with expert categorization
    high_quality_fits = [k for k in kinetics_data 
                        if k.get('fit_quality') in ['excellent', 'good']]
    fit_success_rate = len(high_quality_fits) / len(kinetics_data)
    
    # Enhanced quality assessment (from ECI 1.0)
    if fit_success_rate > 0.7:
        insights["data_quality"] = "High quality relaxation data suitable for analysis"
    else:
        insights["data_quality"] = "Moderate quality data, interpret with caution"
    
    # Traditional R² assessment for compatibility  
    r2_high_quality = [k for k in kinetics_data if k.get('r_squared', 0) >= min_r_squared]
    if len(r2_high_quality) > len(kinetics_data) * 0.8:
        insights["fit_quality"] = "Excellent fit quality - reliable kinetics analysis"
    elif len(r2_high_quality) > len(kinetics_data) * 0.5:
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


def _assess_fit_quality(r_squared: float) -> str:
    """
    Assess fit quality based on R² value using expert thresholds.
    
    Ported from ElectrochemicalInsights 1.0 _assess_fit_quality() method.
    """
    if r_squared >= 0.95:
        return "excellent"
    elif r_squared >= 0.90:
        return "good"
    elif r_squared >= 0.80:
        return "fair"
    else:
        return "poor"


def _assess_diffusion_regime(time_constant: Optional[float]) -> str:
    """
    Assess diffusion regime based on time constant using electrochemical knowledge.
    
    Ported from ElectrochemicalInsights 1.0 _assess_diffusion_regime() method.
    """
    if time_constant is None or time_constant <= 0:
        return "unknown"
    
    if time_constant < 10:
        return "fast_kinetics"
    elif time_constant < 100:
        return "mixed_control"
    else:
        return "diffusion_limited"


def _apply_pre_analysis_filters(segments: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Apply pre-analysis filters to segments based on settings.
    
    Args:
        segments: List of segment dictionaries
        settings: Analysis settings including filters
        
    Returns:
        Filtered list of segments
    """
    filtered_segments = segments.copy()
    
    # Filter by analysis_status
    analysis_status_filter = settings.get('analysis_status_filter', ['completed', 'partial'])
    if analysis_status_filter:
        filtered_segments = [seg for seg in filtered_segments 
                           if seg.get('analysis_status') in analysis_status_filter]
    
    # Filter by duration range
    min_duration = settings.get('min_duration_filter_s', 0)
    max_duration = settings.get('max_duration_filter_s', float('inf'))
    
    filtered_segments = [seg for seg in filtered_segments 
                        if min_duration <= seg.get('duration_s', 0) <= max_duration]
    
    print(f"✅ Pre-analysis filtering: {len(segments)} → {len(filtered_segments)} segments")
    if len(filtered_segments) < len(segments):
        print(f"   Filtered out: {len(segments) - len(filtered_segments)} segments")
        
    return filtered_segments