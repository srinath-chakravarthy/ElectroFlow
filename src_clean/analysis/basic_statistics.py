"""
Basic Statistics Analysis Function

Registry-compatible analysis function for basic statistical summary.
Replaces the _run_basic_statistics_analysis() method in main_tab.py.
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np


def basic_statistics_analysis(segments: List[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
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
            return {"error": "No segments provided for analysis"}
        
        # Get metrics to analyze from settings
        metrics = settings.get('metrics', ['duration_s', 'start_potential_v', 'end_potential_v'])
        
        # Convert to DataFrame for easy statistics
        df = pd.DataFrame(segments)
        
        # Calculate statistics for each metric
        statistics = {}
        
        for metric in metrics:
            if metric in df.columns:
                values = df[metric].dropna()
                
                if len(values) > 0:
                    statistics[metric] = {
                        "mean": float(values.mean()),
                        "std": float(values.std()),
                        "min": float(values.min()),
                        "max": float(values.max()),
                        "count": int(len(values)),
                        "median": float(values.median())
                    }
                else:
                    statistics[metric] = {
                        "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, 
                        "count": 0, "median": 0.0
                    }
        
        # Add technique breakdown
        if 'fundamental_technique' in df.columns:
            technique_counts = df['fundamental_technique'].value_counts().to_dict()
            technique_counts = {k: int(v) for k, v in technique_counts.items()}  # Convert to int
        else:
            technique_counts = {}
        
        # Group breakdown if available
        group_counts = {}
        if 'group_name' in df.columns:
            group_counts = df['group_name'].value_counts().to_dict()
            group_counts = {k: int(v) for k, v in group_counts.items()}
        
        # Time range analysis
        time_analysis = {}
        if 'start_time_s' in df.columns:
            start_times = df['start_time_s'].dropna()
            if len(start_times) > 0:
                time_analysis = {
                    "duration_hours": float((start_times.max() - start_times.min()) / 3600),
                    "first_segment": float(start_times.min()),
                    "last_segment": float(start_times.max())
                }
        
        return {
            "analysis_type": "basic_statistics",
            "segments": segments,  # Pass through for compatibility with existing plotting
            "statistics": statistics,
            "technique_counts": technique_counts,
            "group_counts": group_counts,
            "time_analysis": time_analysis,
            "total_segments": len(segments),
            "metrics_analyzed": metrics,
            "summary": f"Analyzed {len(segments)} segments across {len(technique_counts)} techniques"
        }
        
    except Exception as e:
        return {
            "error": f"Basic statistics analysis failed: {str(e)}",
            "analysis_type": "basic_statistics"
        }