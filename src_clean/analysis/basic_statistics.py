"""
Basic Statistics Analysis Function

Registry-compatible analysis function for basic statistical summary.
Replaces the _run_basic_statistics_analysis() method in main_tab.py.
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np


def basic_statistics_analysis(segments: List[Dict[str, Any]], settings: Dict[str, Any]) -> pd.DataFrame:
    """
    Calculate basic statistics for segment data.
    
    This function replaces the logic in _run_basic_statistics_analysis()
    and works with the registry system.
    
    Args:
        segments: List of segment dictionaries with segment data
        settings: Analysis settings including metrics to analyze
        
    Returns:
        Dictionary with analysis results compatible with existing UI
    """
    
    try:
        if not segments:
            return pd.DataFrame(columns=['segment_id', 'error_message'])
        
        # Get metrics to analyze from settings
        metrics = settings.get('metrics', ['duration_s', 'start_potential_v', 'end_potential_v'])
        
        # Create DataFrame from segments (already has core columns)
        df = pd.DataFrame(segments)
        
        # Rename 'id' to 'segment_id' for consistency
        if 'id' in df.columns:
            df = df.rename(columns={'id': 'segment_id'})
        
        # Add standard columns required by registry
        df['analysis_type'] = 'basic_statistics'
        
        # Calculate statistics for each metric and add as columns
        for metric in metrics:
            if metric in df.columns:
                values = df[metric].dropna()
                
                if len(values) > 0:
                    df[f'{metric}_mean'] = float(values.mean())
                    df[f'{metric}_std'] = float(values.std())
                    df[f'{metric}_min'] = float(values.min())
                    df[f'{metric}_max'] = float(values.max())
                    df[f'{metric}_median'] = float(values.median())
                    df[f'{metric}_count'] = int(len(values))
                else:
                    df[f'{metric}_mean'] = 0.0
                    df[f'{metric}_std'] = 0.0
                    df[f'{metric}_min'] = 0.0
                    df[f'{metric}_max'] = 0.0
                    df[f'{metric}_median'] = 0.0
                    df[f'{metric}_count'] = 0
        
        # Add technique information
        if 'fundamental_technique' in df.columns:
            technique_counts = df['fundamental_technique'].value_counts().to_dict()
            for technique, count in technique_counts.items():
                df[f'technique_count_{technique}'] = count
        
        # Add group information if available
        if 'group_name' in df.columns:
            group_counts = df['group_name'].value_counts().to_dict()
            for group, count in group_counts.items():
                df[f'group_count_{group}'] = count
        
        # Add time range analysis
        if 'start_time_s' in df.columns:
            start_times = df['start_time_s'].dropna()
            if len(start_times) > 0:
                df['time_range_hours'] = float((start_times.max() - start_times.min()) / 3600)
                df['first_segment_time'] = float(start_times.min())
                df['last_segment_time'] = float(start_times.max())
        
        # Add overall metrics
        df['total_segments_analyzed'] = len(segments)
        df['metrics_analyzed'] = ','.join(metrics)
        df['quality_score'] = 1.0  # Basic statistics always succeeds
        
        return df
        
    except Exception as e:
        # Return error as DataFrame
        error_df = pd.DataFrame([{
            'segment_id': None,
            'error_message': f"Basic statistics analysis failed: {str(e)}",
            'analysis_type': 'basic_statistics'
        }])
        return error_df