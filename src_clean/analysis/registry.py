"""
Analysis Registry - Central Analysis Function Registry

Registry-based system for electrochemical analysis functions that replaces
the complex if/elif routing chains throughout the UI and backend.

This registry enables:
- 30-minute analysis development (vs 2+ days of UI debugging)
- Single source of truth for available analyses  
- Automatic UI generation from registry configuration
- Clean separation of analysis logic from routing logic
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Optional, Union
from enum import Enum
import pandas as pd

from ..core.query_filters import QueryFilters, AggregationType


class AnalysisCategory(Enum):
    """Categories of electrochemical analysis for organization."""
    BASIC_STATISTICS = "basic_statistics"
    ELECTROCHEMICAL = "electrochemical" 
    KINETICS = "kinetics"
    THERMODYNAMICS = "thermodynamics"
    IMPEDANCE = "impedance"
    CUSTOM = "custom"


class PlotType(Enum):
    """Available plot types for analysis visualization."""
    TIME_SERIES = "time_series"
    XY_PLOT = "xy_plot" 
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"
    HEATMAP = "heatmap"
    BAR_CHART = "bar_chart"
    CUSTOM = "custom"


@dataclass
class AnalysisConfig:
    """
    Configuration for a single analysis type.
    
    Defines everything needed for an analysis:
    - Data requirements and filtering
    - Analysis function to call
    - UI settings and plot options
    - Results formatting
    """
    
    # === BASIC INFO ===
    analysis_id: str                    # Unique identifier (e.g., "resistance_analysis")
    name: str                          # Display name (e.g., "Resistance Analysis") 
    description: str                   # User-facing description
    category: AnalysisCategory         # Analysis category for organization
    
    # === DATA REQUIREMENTS ===
    required_techniques: List[str] = field(default_factory=list)  # ['Rest', 'Galvanostatic']
    min_segments: int = 1              # Minimum segments required
    requires_analysis_results: bool = False  # Needs JSON analysis_results
    
    # === ANALYSIS FUNCTION ===
    analysis_function: Callable[[List[Dict[str, Any]], Dict[str, Any]], Dict[str, Any]] = None
    data_preparation: Optional[Callable] = None  # Optional data preprocessing
    
    # === UI CONFIGURATION ===
    settings_schema: Dict[str, Any] = field(default_factory=dict)  # UI settings definition
    default_settings: Dict[str, Any] = field(default_factory=dict)  # Default setting values
    
    # === VISUALIZATION ===
    available_plots: List[PlotType] = field(default_factory=list)
    default_plot: Optional[PlotType] = None
    plot_config: Dict[str, Any] = field(default_factory=dict)
    
    # === RESULTS FORMAT ===
    result_template: Optional[str] = None  # HTML template for results display
    export_formats: List[str] = field(default_factory=lambda: ["json"])  # Available export formats
    
    def validate_data(self, segments: List[Dict[str, Any]]) -> tuple[bool, str]:
        """
        Validate that segment data meets analysis requirements.
        
        Returns:
            (is_valid, error_message)
        """
        if len(segments) < self.min_segments:
            return False, f"Analysis requires at least {self.min_segments} segments, got {len(segments)}"
        
        if self.required_techniques:
            available_techniques = set(seg.get('fundamental_technique', '').lower() for seg in segments)
            required_set = set(technique.lower() for technique in self.required_techniques)
            if not required_set.issubset(available_techniques):
                missing = required_set - available_techniques
                return False, f"Analysis requires techniques: {missing}"
        
        if self.requires_analysis_results:
            segments_with_results = [seg for seg in segments 
                                   if seg.get('analysis_results') and 
                                   isinstance(seg['analysis_results'], dict)]
            if len(segments_with_results) < self.min_segments:
                return False, f"Analysis requires segments with analysis_results, found {len(segments_with_results)}"
        
        return True, ""


class AnalysisRegistry:
    """
    Central registry for all analysis types.
    
    Replaces if/elif routing chains in:
    - main_tab.py (_run_analysis method)
    - plotting.py (plot creation methods)  
    - analysis_panels.py (settings routing)
    - results.py (format routing)
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._analyses: Dict[str, AnalysisConfig] = {}
        self._categories: Dict[AnalysisCategory, List[str]] = {}
        
        # Register default analyses
        self._register_default_analyses()
    
    def register_analysis(self, config: AnalysisConfig):
        """
        Register a new analysis type.
        
        This is the main way to add new analyses - just create an AnalysisConfig
        and register it. No UI changes needed.
        """
        self._analyses[config.analysis_id] = config
        
        # Update category index
        if config.category not in self._categories:
            self._categories[config.category] = []
        if config.analysis_id not in self._categories[config.category]:
            self._categories[config.category].append(config.analysis_id)
    
    def get_analysis(self, analysis_id: str) -> Optional[AnalysisConfig]:
        """Get analysis configuration by ID."""
        return self._analyses.get(analysis_id)
    
    def list_analyses(self, category: Optional[AnalysisCategory] = None) -> List[AnalysisConfig]:
        """List available analyses, optionally filtered by category."""
        if category:
            analysis_ids = self._categories.get(category, [])
            return [self._analyses[aid] for aid in analysis_ids]
        else:
            return list(self._analyses.values())
    
    def get_analysis_options(self, category: Optional[AnalysisCategory] = None) -> List[tuple[str, str]]:
        """
        Get analysis options for UI dropdowns.
        
        Returns:
            List of (display_name, analysis_id) tuples
        """
        analyses = self.list_analyses(category)
        return [(analysis.name, analysis.analysis_id) for analysis in analyses]
    
    def validate_analysis_request(self, analysis_id: str, segments: List[Dict[str, Any]]) -> tuple[bool, str]:
        """Validate that an analysis can be run with given data."""
        config = self.get_analysis(analysis_id)
        if not config:
            return False, f"Unknown analysis type: {analysis_id}"
        
        return config.validate_data(segments)
    
    def execute_analysis(self, analysis_id: str, segments: List[Dict[str, Any]], 
                        settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute analysis with given data and settings.
        
        This replaces the if/elif chains in _run_analysis() methods.
        """
        config = self.get_analysis(analysis_id)
        if not config:
            return {"error": f"Unknown analysis type: {analysis_id}"}
        
        # Validate data
        is_valid, error_msg = config.validate_data(segments)
        if not is_valid:
            return {"error": error_msg}
        
        # Apply data preparation if specified
        if config.data_preparation:
            segments = config.data_preparation(segments, settings)
        
        # Merge default settings
        merged_settings = config.default_settings.copy()
        merged_settings.update(settings)
        
        try:
            # Execute analysis function
            result = config.analysis_function(segments, merged_settings)
            
            # Add metadata
            result.update({
                "analysis_type": analysis_id,
                "analysis_name": config.name,
                "segment_count": len(segments),
                "settings_used": merged_settings
            })
            
            return result
            
        except Exception as e:
            return {
                "error": f"Analysis execution failed: {str(e)}",
                "analysis_type": analysis_id
            }
    
    def get_settings_schema(self, analysis_id: str) -> Dict[str, Any]:
        """Get UI settings schema for an analysis."""
        config = self.get_analysis(analysis_id)
        return config.settings_schema if config else {}
    
    def get_default_settings(self, analysis_id: str) -> Dict[str, Any]:
        """Get default settings for an analysis."""
        config = self.get_analysis(analysis_id)
        return config.default_settings if config else {}
    
    def get_available_plots(self, analysis_id: str) -> List[PlotType]:
        """Get available plot types for an analysis."""
        config = self.get_analysis(analysis_id)
        return config.available_plots if config else []
    
    def get_plot_config(self, analysis_id: str) -> Dict[str, Any]:
        """Get plot configuration for an analysis."""
        config = self.get_analysis(analysis_id)
        return config.plot_config if config else {}
    
    def _register_default_analyses(self):
        """Register the default analyses that replace existing specialized methods."""
        
        # Import analysis functions
        from .basic_statistics import basic_statistics_analysis
        from .resistance_analysis import resistance_analysis_function
        from .kinetics_analysis import kinetics_analysis_function
        from .equilibrium_analysis import equilibrium_analysis_function
        from .current_decay_analysis import current_decay_analysis_function
        
        # Basic Statistics Analysis
        self.register_analysis(AnalysisConfig(
            analysis_id="basic_statistics",
            name="Basic Statistics", 
            description="Statistical summary of segment metrics (mean, std, min, max)",
            category=AnalysisCategory.BASIC_STATISTICS,
            min_segments=1,
            analysis_function=basic_statistics_analysis,
            settings_schema={
                "metrics": {
                    "type": "multiselect",
                    "options": ["duration_s", "start_potential_v", "end_potential_v", 
                              "capacity_ah", "energy_wh"],
                    "default": ["duration_s", "start_potential_v", "end_potential_v"]
                }
            },
            default_settings={"metrics": ["duration_s", "start_potential_v", "end_potential_v"]},
            available_plots=[PlotType.TIME_SERIES, PlotType.HISTOGRAM, PlotType.BOX_PLOT],
            default_plot=PlotType.TIME_SERIES
        ))
        
        # Resistance Analysis  
        self.register_analysis(AnalysisConfig(
            analysis_id="resistance_analysis",
            name="Resistance Analysis",
            description="Instantaneous resistance calculations from galvanostatic data",
            category=AnalysisCategory.ELECTROCHEMICAL,
            required_techniques=["Galvanostatic"],
            min_segments=1,
            requires_analysis_results=True,
            analysis_function=resistance_analysis_function,
            settings_schema={
                "time_points": {
                    "type": "multiselect", 
                    "options": ["immediate", "10s", "30s"],
                    "default": ["immediate", "10s"]
                }
            },
            default_settings={"time_points": ["immediate", "10s"]},
            available_plots=[PlotType.TIME_SERIES, PlotType.XY_PLOT, PlotType.BAR_CHART],
            default_plot=PlotType.TIME_SERIES
        ))
        
        # Kinetics Analysis
        self.register_analysis(AnalysisConfig(
            analysis_id="kinetics_analysis", 
            name="Kinetics Analysis",
            description="Relaxation kinetics from REST phase analysis",
            category=AnalysisCategory.KINETICS,
            required_techniques=["Rest"],
            min_segments=1,
            requires_analysis_results=True,
            analysis_function=kinetics_analysis_function,
            settings_schema={
                "fit_type": {
                    "type": "select",
                    "options": ["exponential", "sqrt_t", "auto_best"],
                    "default": "auto_best"
                },
                "min_r_squared": {
                    "type": "float",
                    "min": 0.0,
                    "max": 1.0,
                    "default": 0.8
                }
            },
            default_settings={"fit_type": "auto_best", "min_r_squared": 0.8},
            available_plots=[PlotType.TIME_SERIES, PlotType.XY_PLOT],
            default_plot=PlotType.TIME_SERIES
        ))
        
        # Equilibrium Analysis
        self.register_analysis(AnalysisConfig(
            analysis_id="equilibrium_analysis",
            name="Equilibrium Analysis",
            description="Equilibrium voltage analysis and stability assessment",
            category=AnalysisCategory.THERMODYNAMICS,
            min_segments=1,
            analysis_function=equilibrium_analysis_function,
            settings_schema={
                "min_duration_s": {
                    "type": "float",
                    "min": 1,
                    "default": 60,
                    "description": "Minimum duration for equilibrium (seconds)"
                },
                "max_drift_rate_mv_per_min": {
                    "type": "float", 
                    "min": 0.1,
                    "max": 10.0,
                    "default": 1.0,
                    "description": "Maximum drift rate (mV/min)"
                }
            },
            default_settings={"min_duration_s": 60, "max_drift_rate_mv_per_min": 1.0},
            available_plots=[PlotType.TIME_SERIES, PlotType.XY_PLOT, PlotType.BOX_PLOT],
            default_plot=PlotType.TIME_SERIES
        ))
        
        # Current Decay Analysis
        self.register_analysis(AnalysisConfig(
            analysis_id="current_decay_analysis",
            name="Current Decay Analysis",
            description="Potentiostatic current decay kinetics analysis",
            category=AnalysisCategory.KINETICS,
            required_techniques=["Potentiostatic"],
            min_segments=1,
            requires_analysis_results=True,
            analysis_function=current_decay_analysis_function,
            settings_schema={
                "min_r_squared": {
                    "type": "float",
                    "min": 0.0,
                    "max": 1.0,
                    "default": 0.8,
                    "description": "Minimum R² for decay fits"
                },
                "min_duration_s": {
                    "type": "float",
                    "min": 1,
                    "default": 10,
                    "description": "Minimum duration for decay analysis (seconds)"
                }
            },
            default_settings={"min_r_squared": 0.8, "min_duration_s": 10},
            available_plots=[PlotType.TIME_SERIES, PlotType.XY_PLOT],
            default_plot=PlotType.TIME_SERIES
        ))
        
        # dQ/dV Analysis (placeholder - not implemented yet)
        self.register_analysis(AnalysisConfig(
            analysis_id="dqdv_analysis",
            name="dQ/dV Analysis", 
            description="Differential capacity analysis (coming soon)",
            category=AnalysisCategory.THERMODYNAMICS,
            min_segments=1,
            analysis_function=lambda segments, settings: {
                "error": "dQ/dV analysis not implemented yet. Coming in future version.",
                "placeholder": True
            },
            available_plots=[PlotType.TIME_SERIES],
            default_plot=PlotType.TIME_SERIES
        ))


# === GLOBAL REGISTRY INSTANCE ===

_analysis_registry = None

def get_analysis_registry() -> AnalysisRegistry:
    """Get global analysis registry instance."""
    global _analysis_registry
    if _analysis_registry is None:
        _analysis_registry = AnalysisRegistry()
    return _analysis_registry


# === CONVENIENCE FUNCTIONS ===

def register_analysis(config: AnalysisConfig):
    """Register new analysis type (convenience function)."""
    registry = get_analysis_registry()
    registry.register_analysis(config)

def get_analysis_options() -> List[tuple[str, str]]:
    """Get all analysis options for UI dropdowns.""" 
    registry = get_analysis_registry()
    return registry.get_analysis_options()

def execute_analysis(analysis_id: str, segments: List[Dict[str, Any]], 
                    settings: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute analysis (convenience function)."""
    registry = get_analysis_registry()
    return registry.execute_analysis(analysis_id, segments, settings or {})

def validate_analysis_request(analysis_id: str, segments: List[Dict[str, Any]]) -> tuple[bool, str]:
    """Validate analysis request (convenience function)."""
    registry = get_analysis_registry()
    return registry.validate_analysis_request(analysis_id, segments)