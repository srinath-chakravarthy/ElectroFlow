"""
Central Analysis Engine - Registry-Based Analytics Dispatcher

Replaces 35+ redundant API methods with a single, unified analysis interface.
Integrates the universal query engine with the analysis registry to provide
clean separation between data access and analysis logic.

This engine consolidates:
- get_group_base_statistics()
- get_segment_subset_statistics()  
- get_electrochemical_rest_analysis()
- get_electrochemical_resistance_analysis()
- get_electrochemical_equilibrium_analysis()
- get_electrochemical_current_decay_analysis()
- get_unified_electrochemical_analysis()
- get_group_temporal_analytics()
- get_group_fit_quality_statistics()
- get_group_voltage_correlation_analytics()
- And 25+ other specialized methods
"""

from typing import List, Dict, Any, Union, Optional
import logging

from ..core.query_engine import get_segments_data
from ..core.query_filters import (
    QueryFilters, group_filter, segment_filter, statistics_filter, 
    AggregationType, QueryScope
)
from ..analysis.registry import get_analysis_registry, execute_analysis


logger = logging.getLogger(__name__)


class AnalysisEngine:
    """
    Central analysis dispatcher that replaces specialized API methods.
    
    Single entry point for all analytics that combines:
    - Universal query engine for data access
    - Analysis registry for computation
    - Standardized result formatting
    """
    
    def __init__(self):
        """Initialize with registry and query engine."""
        self.registry = get_analysis_registry()
    
    def get_analysis(self, 
                    analysis_type: str, 
                    data_filters: QueryFilters, 
                    settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Universal analysis method that replaces 35+ specialized API methods.
        
        This single method handles:
        - Data retrieval using universal query engine
        - Analysis execution using registry
        - Result formatting and error handling
        
        Args:
            analysis_type: Analysis to run ('basic_statistics', 'resistance_analysis', etc.)
            data_filters: QueryFilters specifying what data to analyze
            settings: Analysis-specific settings
            
        Returns:
            Dictionary with analysis results, compatible with existing UI expectations
        """
        
        try:
            # Validate analysis type
            analysis_config = self.registry.get_analysis(analysis_type)
            if not analysis_config:
                return {
                    "error": f"Unknown analysis type: {analysis_type}",
                    "available_analyses": [a.analysis_id for a in self.registry.list_analyses()]
                }
            
            # Get data using universal query engine
            logger.debug(f"Fetching data for {analysis_type} with filters: {data_filters}")
            
            # For most analyses, we need raw segment data
            if data_filters.aggregation == AggregationType.STATISTICS:
                # Statistics analysis - get pre-aggregated statistics
                data = get_segments_data(data_filters)
                
                # Convert to segment format for registry compatibility
                segments = [{"statistics": data, "analysis_type": analysis_type}]
            else:
                # Raw data analysis - get individual segments
                data_filters.aggregation = AggregationType.RAW
                segments = get_segments_data(data_filters)
            
            if not segments:
                return {
                    "error": "No data found matching the specified filters",
                    "analysis_type": analysis_type,
                    "filters_applied": str(data_filters)
                }
            
            logger.debug(f"Retrieved {len(segments)} segments for analysis")
            
            # Execute analysis using registry
            merged_settings = settings or {}
            result = execute_analysis(analysis_type, segments, merged_settings)
            
            # Add metadata for compatibility with existing UI
            if "error" not in result:
                result.update({
                    "data_source": "registry_engine",
                    "query_engine_version": "universal",
                    "segments_analyzed": len(segments) if isinstance(segments, list) else 1,
                    "filters_applied": self._summarize_filters(data_filters)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis engine error for {analysis_type}: {e}")
            return {
                "error": f"Analysis engine failure: {str(e)}",
                "analysis_type": analysis_type
            }
    
    def get_basic_statistics(self, group_ids: List[Union[str, int]]) -> Dict[str, Any]:
        """
        Replacement for get_group_base_statistics() API method.
        
        Args:
            group_ids: List of group IDs to analyze
            
        Returns:
            Statistics dictionary compatible with existing UI
        """
        filters = statistics_filter([str(gid) for gid in group_ids])
        return self.get_analysis("basic_statistics", filters)
    
    def get_segment_statistics(self, segment_ids: List[Union[str, int]]) -> Dict[str, Any]:
        """
        Replacement for get_segment_subset_statistics() API method.
        
        Args:
            segment_ids: List of segment IDs to analyze
            
        Returns:
            Statistics dictionary compatible with existing UI
        """
        filters = QueryFilters(
            segment_ids=[str(sid) for sid in segment_ids],
            aggregation=AggregationType.STATISTICS
        )
        return self.get_analysis("basic_statistics", filters)
    
    def get_electrochemical_analysis(self, 
                                   analysis_type: str,
                                   group_ids: List[Union[str, int]], 
                                   settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Universal electrochemical analysis method.
        
        Replaces:
        - get_electrochemical_rest_analysis()
        - get_electrochemical_resistance_analysis() 
        - get_electrochemical_equilibrium_analysis()
        - get_electrochemical_current_decay_analysis()
        
        Args:
            analysis_type: 'kinetics_analysis', 'resistance_analysis', etc.
            group_ids: List of group IDs to analyze
            settings: Analysis-specific settings
            
        Returns:
            Analysis results compatible with existing ElectrochemicalInsights format
        """
        filters = group_filter([str(gid) for gid in group_ids])
        return self.get_analysis(analysis_type, filters, settings)
    
    def get_unified_analysis(self, 
                           group_ids: List[Union[str, int]], 
                           analysis_types: List[str],
                           settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Replacement for get_unified_electrochemical_analysis() API method.
        
        Runs multiple analyses on the same data and combines results.
        
        Args:
            group_ids: List of group IDs to analyze
            analysis_types: List of analyses to run
            settings: Global settings for all analyses
            
        Returns:
            Combined analysis results
        """
        
        try:
            filters = group_filter([str(gid) for gid in group_ids])
            
            # Get segments once for all analyses (efficiency)
            segments = get_segments_data(filters)
            
            if not segments:
                return {
                    "error": "No segments found for unified analysis",
                    "group_ids": group_ids
                }
            
            # Run each analysis type
            results = {
                "analysis_types": analysis_types,
                "group_ids": group_ids,
                "total_segments": len(segments),
                "results": {}
            }
            
            for analysis_type in analysis_types:
                try:
                    # Use the segments we already retrieved
                    result = execute_analysis(analysis_type, segments, settings or {})
                    results["results"][analysis_type] = result
                except Exception as e:
                    results["results"][analysis_type] = {
                        "error": f"Failed {analysis_type}: {str(e)}"
                    }
            
            return results
            
        except Exception as e:
            return {
                "error": f"Unified analysis failed: {str(e)}",
                "group_ids": group_ids,
                "analysis_types": analysis_types
            }
    
    def get_available_analyses(self) -> List[Dict[str, Any]]:
        """
        Get list of available analysis types for UI generation.
        
        Returns:
            List of analysis configurations
        """
        analyses = self.registry.list_analyses()
        return [
            {
                "id": analysis.analysis_id,
                "name": analysis.name,
                "description": analysis.description,
                "category": analysis.category.value,
                "required_techniques": analysis.required_techniques,
                "available_plots": [plot.value for plot in analysis.available_plots]
            }
            for analysis in analyses
        ]
    
    def validate_analysis_request(self, 
                                analysis_type: str, 
                                data_filters: QueryFilters) -> tuple[bool, str]:
        """
        Validate that an analysis can be run with given filters.
        
        Args:
            analysis_type: Analysis to validate
            data_filters: Data filters to check
            
        Returns:
            (is_valid, error_message)
        """
        
        # Check if analysis exists
        analysis_config = self.registry.get_analysis(analysis_type)
        if not analysis_config:
            return False, f"Unknown analysis type: {analysis_type}"
        
        # Get sample of data to validate
        try:
            # Just get a few segments for validation (performance)
            data_filters.limit = 5
            segments = get_segments_data(data_filters)
            
            if not segments:
                return False, "No data found matching the specified filters"
            
            # Use registry validation
            return self.registry.validate_analysis_request(analysis_type, segments)
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _summarize_filters(self, filters: QueryFilters) -> Dict[str, Any]:
        """Create summary of applied filters for debugging/logging."""
        summary = {}
        
        if filters.group_ids:
            summary["groups"] = len(filters.group_ids)
        if filters.segment_ids:
            summary["segments"] = len(filters.segment_ids)
        if filters.fundamental_techniques:
            summary["techniques"] = filters.fundamental_techniques
        if filters.aggregation:
            summary["aggregation"] = filters.aggregation.value
            
        return summary


# === GLOBAL INSTANCE ===

_analysis_engine = None

def get_analysis_engine() -> AnalysisEngine:
    """Get global analysis engine instance."""
    global _analysis_engine
    if _analysis_engine is None:
        _analysis_engine = AnalysisEngine()
    return _analysis_engine


# === CONVENIENCE FUNCTIONS ===
# These provide the exact same interface as the old API methods for compatibility

def get_analysis(analysis_type: str, 
                data_filters: QueryFilters, 
                settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Universal analysis function (convenience)."""
    engine = get_analysis_engine()
    return engine.get_analysis(analysis_type, data_filters, settings)

def get_basic_statistics(group_ids: List[Union[str, int]]) -> Dict[str, Any]:
    """Replacement for get_group_base_statistics() (convenience)."""
    engine = get_analysis_engine()
    return engine.get_basic_statistics(group_ids)

def get_segment_statistics(segment_ids: List[Union[str, int]]) -> Dict[str, Any]:
    """Replacement for get_segment_subset_statistics() (convenience)."""
    engine = get_analysis_engine()
    return engine.get_segment_statistics(segment_ids)

def get_electrochemical_analysis(analysis_type: str,
                               group_ids: List[Union[str, int]], 
                               settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Universal electrochemical analysis (convenience)."""
    engine = get_analysis_engine()
    return engine.get_electrochemical_analysis(analysis_type, group_ids, settings)

def get_unified_analysis(group_ids: List[Union[str, int]], 
                       analysis_types: List[str],
                       settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Replacement for get_unified_electrochemical_analysis() (convenience)."""
    engine = get_analysis_engine()
    return engine.get_unified_analysis(group_ids, analysis_types, settings)