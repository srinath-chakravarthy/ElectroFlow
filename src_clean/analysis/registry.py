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
from datetime import datetime
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
    
    # === OUTPUT SPECIFICATION ===
    output_columns: Dict[str, List[str]] = field(default_factory=dict)  # Categorized output columns
    # {
    #   "metrics": ["diffusion_coefficient_cm2_s", "time_constant_s"],     # For X/Y plotting
    #   "quality": ["r_squared", "rmse", "quality_score"],                # For distribution plots  
    #   "insights": ["analysis_type", "meets_criteria"]                   # For categorical/bar plots
    # }
    
    # === ANALYSIS FUNCTION ===
    analysis_function: Callable[..., Dict[str, Any]] = None
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
    
    # === SCHEMA TRACKING (Auto-populated) ===
    last_columns: Optional[List[str]] = None  # Last DataFrame columns returned
    last_schema_update: Optional[datetime] = None  # When schema was last updated
    
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
    
    def get_analyses_for_technique(self, technique_name: str) -> List[AnalysisConfig]:
        """
        Get all analyses applicable to a specific fundamental technique.
        
        Args:
            technique_name: Fundamental technique name (e.g., 'Rest', 'Galvanostatic')
            
        Returns:
            List of AnalysisConfig objects that apply to the given technique
        """
        applicable_analyses = []
        
        for analysis in self._analyses.values():
            if technique_name in analysis.required_techniques:
                applicable_analyses.append(analysis)
        
        return applicable_analyses
    
    def get_analysis_ids_for_technique(self, technique_name: str) -> List[str]:
        """
        Get analysis IDs for a specific fundamental technique.
        
        Args:
            technique_name: Fundamental technique name (e.g., 'Rest', 'Galvanostatic')
            
        Returns:
            List of analysis_id strings that apply to the given technique
        """
        analyses = self.get_analyses_for_technique(technique_name)
        return [analysis.analysis_id for analysis in analyses]
    
    def get_analysis_options_for_technique(self, technique_name: str) -> List[tuple[str, str]]:
        """
        Get analysis options for UI dropdowns, filtered by technique.
        
        Args:
            technique_name: Fundamental technique name (e.g., 'Rest', 'Galvanostatic')
            
        Returns:
            List of (display_name, analysis_id) tuples for analyses applicable to technique
        """
        analyses = self.get_analyses_for_technique(technique_name)
        return [(analysis.name, analysis.analysis_id) for analysis in analyses]
    
    def validate_analysis_request(self, analysis_id: str, segments: List[Dict[str, Any]]) -> tuple[bool, str]:
        """Validate that an analysis can be run with given data."""
        config = self.get_analysis(analysis_id)
        if not config:
            return False, f"Unknown analysis type: {analysis_id}"
        
        return config.validate_data(segments)
    
    def execute_analysis(self, analysis_id: str, segments: List[Dict[str, Any]], 
                        settings: Dict[str, Any], **kwargs) -> Dict[str, Any]:
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
            result = config.analysis_function(segments, merged_settings, **kwargs)
            
            # Handle DataFrame returns (new format) vs Dict returns (legacy)
            if hasattr(result, 'columns'):  # It's a DataFrame
                # Add metadata as DataFrame attributes for backward compatibility
                result.attrs.update({
                    "analysis_type": analysis_id,
                    "analysis_name": config.name,
                    "segment_count": len(segments),
                    "settings_used": merged_settings
                })
                
                # Auto-update schema tracking
                config.last_columns = list(result.columns)
                config.last_schema_update = datetime.now()
                
                return result
            else:
                # Legacy dictionary format - add metadata normally  
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
    
    # ===== REGISTRY VALIDATOR HELPER METHODS =====
    
    def validate_all_configs(self) -> Dict[str, List[str]]:
        """
        Validate all plot configurations against actual DataFrame schemas.
        
        Returns:
            Dict mapping analysis_id to list of validation issues
        """
        from .registry_validator import RegistryValidator
        validator = RegistryValidator()
        results = validator.validate_all_configs()
        
        # Convert to simple format
        issues = {}
        for analysis_id, validation_results in results.items():
            analysis_issues = []
            for result in validation_results:
                if not result.is_valid:
                    analysis_issues.append(f"{result.plot_name}: Missing {result.missing_columns}")
            issues[analysis_id] = analysis_issues
        
        return issues
    
    def get_available_columns(self, analysis_id: str) -> List[str]:
        """
        Get available DataFrame columns for an analysis by running it.
        
        Args:
            analysis_id: Analysis type to check
            
        Returns:
            List of column names available in the DataFrame  
        """
        from .registry_validator import RegistryValidator
        validator = RegistryValidator()
        return validator.get_available_columns(analysis_id)
    
    def get_metrics_columns(self, analysis_id: str) -> List[str]:
        """Get metric columns for X/Y axis plotting."""
        config = self.get_analysis(analysis_id)
        if config and config.output_columns:
            metrics = config.output_columns.get("metrics", [])
            return [f"{analysis_id}_{col}" for col in metrics]
        return []
    
    def get_quality_columns(self, analysis_id: str) -> List[str]:
        """Get quality columns for distribution analysis."""
        config = self.get_analysis(analysis_id)
        if config and config.output_columns:
            quality = config.output_columns.get("quality", [])
            return [f"{analysis_id}_{col}" for col in quality]
        return []
    
    def get_insight_columns(self, analysis_id: str) -> List[str]:
        """Get insight columns for categorical/bar plotting."""
        config = self.get_analysis(analysis_id)
        if config and config.output_columns:
            insights = config.output_columns.get("insights", [])
            return [f"{analysis_id}_{col}" for col in insights]
        return []
    
    def get_columns_by_category(self, analysis_id: str) -> Dict[str, List[str]]:
        """Get all columns organized by category for UI."""
        config = self.get_analysis(analysis_id)
        if config and config.output_columns:
            categorized = {}
            for category, columns in config.output_columns.items():
                categorized[category] = [f"{analysis_id}_{col}" for col in columns]
            return categorized
        return {}
    
    def get_all_output_columns(self, analysis_id: str) -> List[str]:
        """Get all output columns (all categories combined)."""
        config = self.get_analysis(analysis_id)
        if config and config.output_columns:
            all_columns = []
            for columns in config.output_columns.values():
                all_columns.extend([f"{analysis_id}_{col}" for col in columns])
            return sorted(all_columns)
        return []
    
    def add_plot_config(self, analysis_id: str, plot_name: str, 
                       plot_type: str, x_column: str, y_column: Optional[str] = None,
                       title: Optional[str] = None, x_label: Optional[str] = None,
                       y_label: Optional[str] = None) -> bool:
        """
        Add new plot configuration to existing analysis.
        
        Args:
            analysis_id: Analysis to add plot to
            plot_name: Name for the new plot
            plot_type: Type of plot ('line', 'scatter', 'histogram')
            x_column: X-axis column name
            y_column: Y-axis column name (optional for histograms)
            title: Plot title (auto-generated if None)
            x_label: X-axis label (auto-generated if None)  
            y_label: Y-axis label (auto-generated if None)
            
        Returns:
            True if successfully added, False otherwise
        """
        from .registry_validator import RegistryValidator
        validator = RegistryValidator()
        return validator.add_plot_config(analysis_id, plot_name, plot_type,
                                       x_column, y_column, title, x_label, y_label)
    
    def generate_config_report(self) -> str:
        """
        Generate comprehensive markdown report of all registry configurations.
        
        Returns:
            Markdown-formatted report string
        """
        from .registry_validator import RegistryValidator
        validator = RegistryValidator()
        return validator.generate_config_report()
    
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
            analysis_id="basic_statistics_analytics",
            name="Basic Statistics", 
            description="Statistical summary of segment metrics (mean, std, min, max)",
            category=AnalysisCategory.BASIC_STATISTICS,
            required_techniques=["Rest", "Galvanostatic", "Potentiostatic", "EIS", "Cyclic_Voltammetry"],  # Applicable to all
            min_segments=1,
            analysis_function=basic_statistics_analysis,
            output_columns={
                "metrics": ["duration_s_mean", "start_potential_v_mean", "end_potential_v_mean", 
                           "capacity_ah_mean", "energy_wh_mean", "time_range_hours"],
                "quality": ["duration_s_std", "start_potential_v_std", "end_potential_v_std", 
                           "duration_s_count", "total_segments_analyzed", "quality_score"],
                "insights": ["metrics_analyzed", "first_segment_time", "last_segment_time",
                            "technique_count_Rest", "technique_count_Galvanostatic"]
            },
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
            default_plot=PlotType.TIME_SERIES,
            plot_config={
                "Duration Distribution": {
                    "plot_type": "histogram",
                    "x_column": "duration_s",
                    "title": "Segment Duration Distribution",
                    "x_label": "Duration (s)",
                    "y_label": "Count"
                },
                "Voltage Range": {
                    "plot_type": "scatter",
                    "x_column": "start_potential_v",
                    "y_column": "end_potential_v",
                    "title": "Start vs End Potential",
                    "x_label": "Start Potential (V)",
                    "y_label": "End Potential (V)"
                }
            }
        ))
        
        # Resistance Analysis  
        self.register_analysis(AnalysisConfig(
            analysis_id="resistance_analytics",
            name="Resistance Analysis",
            description="Instantaneous resistance calculations from galvanostatic data",
            category=AnalysisCategory.ELECTROCHEMICAL,
            required_techniques=["Galvanostatic", "EIS"],
            min_segments=1,
            requires_analysis_results=True,
            analysis_function=resistance_analysis_function,
            output_columns={
                "metrics": ["ir_immediate_ohm", "ir_10s_ohm", "ir_30s_ohm", "baseline_voltage_v", 
                           "average_current_a", "pulse_duration_s", "resistance_ratio_immediate_30s"],
                "quality": ["calculation_quality", "quality_score", "ir_immediate_ohm_mean", 
                           "ir_immediate_ohm_std", "ir_10s_ohm_mean", "ir_10s_ohm_std"],
                "insights": ["insight_resistance_level", "insight_average_resistance", "insight_data_quality", 
                            "insight_consistency", "insight_coefficient_of_variation"]
            },
            settings_schema={
                "time_points": {
                    "type": "multiselect", 
                    "options": ["immediate", "10s", "30s"],
                    "default": ["immediate", "10s"]
                }
            },
            default_settings={"time_points": ["immediate", "10s"]},
            available_plots=[PlotType.TIME_SERIES, PlotType.XY_PLOT, PlotType.BAR_CHART],
            default_plot=PlotType.TIME_SERIES,
            plot_config={
                "Resistance vs Time": {
                    "plot_type": "line",
                    "x_column": "start_time_s",
                    "y_column": "ir_immediate_ohm",
                    "title": "Instantaneous Resistance Over Time",
                    "x_label": "Time (s)",
                    "y_label": "Resistance (Ω)"
                },
                "Resistance Distribution": {
                    "plot_type": "histogram",
                    "x_column": "ir_immediate_ohm",
                    "title": "Resistance Distribution",
                    "x_label": "Resistance (Ω)",
                    "y_label": "Count"
                },
                "Multi-Series Resistance": {
                    "plot_type": "line",
                    "x_column": "start_time_s",
                    "y_column": ["ir_immediate_ohm", "ir_10s_ohm", "ir_30s_ohm"],
                    "title": "All Resistance Types vs Time",
                    "x_label": "Time (s)",
                    "y_label": "Resistance (Ω)"
                },
                "Resistance vs Voltage": {
                    "plot_type": "scatter",
                    "x_column": "start_potential_v",
                    "y_column": ["ir_immediate_ohm", "ir_10s_ohm", "ir_30s_ohm"],
                    "title": "All Resistance Types vs Starting Potential",
                    "x_label": "Starting Potential (V)",
                    "y_label": "Resistance (Ω)"
                },
                "Resistance vs Voltage (Instantaneous)": {
                    "plot_type": "scatter",
                    "x_column": "start_potential_v",
                    "y_column": "ir_immediate_ohm",
                    "title": "Instantaneous Resistance vs Starting Potential",
                    "x_label": "Starting Potential (V)",
                    "y_label": "Instantaneous Resistance (Ω)"
                },
                "Resistance Ratio vs Time": {
                    "plot_type": "line",
                    "x_column": "start_time_s",
                    "y_column": "resistance_ratio_immediate_30s",
                    "title": "Resistance Ratio (Instantaneous/30s) vs Time",
                    "x_label": "Time (s)",
                    "y_label": "Resistance Ratio (Instantaneous/30s)"
                },
                "Resistance Ratio vs Voltage": {
                    "plot_type": "scatter",
                    "x_column": "start_potential_v",
                    "y_column": "resistance_ratio_immediate_30s",
                    "title": "Resistance Ratio (Instantaneous/30s) vs Starting Potential",
                    "x_label": "Starting Potential (V)",
                    "y_label": "Resistance Ratio (Instantaneous/30s)"
                }
            }
        ))
        
        # Kinetics Analysis
        self.register_analysis(AnalysisConfig(
            analysis_id="kinetics_analytics",
            name="Kinetics Analysis",
            description="Relaxation kinetics from REST phase analysis",
            category=AnalysisCategory.KINETICS,
            required_techniques=["Rest", "Potentiostatic"],
            min_segments=1,
            requires_analysis_results=True,
            analysis_function=kinetics_analysis_function,
            output_columns={
                "metrics": ["voltage_infinity", "voltage_amplitude", "current_infinity", "current_amplitude", 
                           "time_constant_s", "voltage_sqrt_amplitude", "current_sqrt_amplitude", "voltage_recovery_v"],
                "quality": ["r_squared", "rmse", "quality_score", "fit_quality", "diffusion_regime", 
                           "extraction_quality_exp", "extraction_quality_sqrt"],
                "insights": ["fit_type", "selection_reason", "analysis_type", "fit_type_used", 
                            "is_high_quality", "insight_dominant_process", "insight_data_quality", 
                            "insight_fit_quality", "insight_relaxation_speed", "insight_voltage_recovery"]
            },
            settings_schema={
                "analysis_status_filter": {
                    "type": "multiselect",
                    "options": ["completed", "partial", "failed"],
                    "default": ["completed", "partial"],
                    "description": "Filter segments by analysis status"
                },
                "min_duration_filter_s": {
                    "type": "float",
                    "min": 0,
                    "max": 3600,
                    "default": 1,
                    "description": "Minimum segment duration (seconds)"
                },
                "max_duration_filter_s": {
                    "type": "float",
                    "min": 1,
                    "max": 36000,
                    "default": 3600,
                    "description": "Maximum segment duration (seconds)"
                },
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
            default_settings={
                "analysis_status_filter": ["completed", "partial"],
                "min_duration_filter_s": 1,
                "max_duration_filter_s": 3600,
                "fit_type": "auto_best", 
                "min_r_squared": 0.8
            },
            available_plots=[PlotType.TIME_SERIES, PlotType.XY_PLOT],
            default_plot=PlotType.TIME_SERIES,
            plot_config={
                "Voltage Recovery vs Time": {
                    "plot_type": "line",
                    "x_column": "start_time_s",
                    "y_column": "end_voltage_v",
                    "title": "Voltage Recovery Over Time",
                    "x_label": "Time (s)",
                    "y_label": "End Voltage (V)"
                },
                "Fit Quality Distribution": {
                    "plot_type": "histogram",
                    "x_column": "r_squared",
                    "title": "Kinetics Fit Quality Distribution",
                    "x_label": "R²",
                    "y_label": "Count"
                },
                "Fit Quality Groups": {
                    "plot_type": "scatter",
                    "x_column": "start_time_s",
                    "y_column": "r_squared",
                    "by": "fit_quality",
                    "title": "R² by Fit Quality Groups",
                    "x_label": "Time (s)",
                    "y_label": "R² Value"
                }
            }
        ))
        
        # Equilibrium Analysis
        self.register_analysis(AnalysisConfig(
            analysis_id="equilibrium_analytics",
            name="Equilibrium Analysis",
            description="Time constants, diffusion coefficients, and equilibrium voltage analysis from REST segments",
            category=AnalysisCategory.THERMODYNAMICS,
            required_techniques=["Rest"],
            min_segments=1,
            requires_analysis_results=True,
            analysis_function=equilibrium_analysis_function,
            output_columns={
                "metrics": ["equilibrium_voltage_v", "voltage_infinity", "voltage_amplitude", "current_infinity", 
                           "current_amplitude", "time_constant_s", "voltage_change_v", "drift_rate_mv_min", 
                           "diffusion_coefficient_cm2_s"],
                "quality": ["r_squared", "rmse", "equilibrium_quality", "quality_score", "meets_duration_criteria", 
                           "meets_drift_criteria"],
                "insights": ["analysis_type", "insight_data_quality", "insight_equilibrium_voltage", 
                            "insight_voltage_stability", "insight_voltage_evolution", "insight_drift_assessment", 
                            "insight_duration_assessment"]
            },
            settings_schema={
                "analysis_status_filter": {
                    "type": "multiselect",
                    "options": ["completed", "partial", "failed"],
                    "default": ["completed", "partial"],
                    "description": "Filter segments by analysis status"
                },
                "min_duration_filter_s": {
                    "type": "float",
                    "min": 0,
                    "max": 3600,
                    "default": 1,
                    "description": "Minimum segment duration (seconds)"
                },
                "max_duration_filter_s": {
                    "type": "float",
                    "min": 1,
                    "max": 36000,
                    "default": 3600,
                    "description": "Maximum segment duration (seconds)"
                },
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
            default_settings={
                "analysis_status_filter": ["completed", "partial"],
                "min_duration_filter_s": 1,
                "max_duration_filter_s": 3600,
                "min_duration_s": 60, 
                "max_drift_rate_mv_per_min": 1.0
            },
            available_plots=[PlotType.TIME_SERIES, PlotType.XY_PLOT, PlotType.BOX_PLOT],
            default_plot=PlotType.TIME_SERIES,
            plot_config={
                "Equilibrium Voltage vs Time": {
                    "plot_type": "line",
                    "x_column": "start_time_s",
                    "y_column": "equilibrium_voltage_v",
                    "title": "Equilibrium Voltage Over Time",
                    "x_label": "Time (s)",
                    "y_label": "Equilibrium Voltage (V)"
                },
                "Drift Rate Distribution": {
                    "plot_type": "histogram",
                    "x_column": "drift_rate_mv_min",
                    "title": "Voltage Drift Rate Distribution",
                    "x_label": "Drift Rate (mV/min)",
                    "y_label": "Count"
                },
                "Time Constants vs Time": {
                    "plot_type": "line",
                    "x_column": "start_time_s",
                    "y_column": "time_constant_s",
                    "title": "Exponential Time Constants vs Time",
                    "x_label": "Time (s)",
                    "y_label": "Time Constant (s)"
                },
                "Time Constants vs Voltage": {
                    "plot_type": "scatter",
                    "x_column": "start_potential_v",
                    "y_column": "time_constant_s",
                    "title": "Exponential Time Constants vs Starting Potential",
                    "x_label": "Starting Potential (V)",
                    "y_label": "Time Constant (s)"
                },
                "Diffusion Coefficients vs Time": {
                    "plot_type": "line",
                    "x_column": "start_time_s",
                    "y_column": "diffusion_coefficient_cm2_s",
                    "title": "Diffusion Coefficients vs Time",
                    "x_label": "Time (s)",
                    "y_label": "Diffusion Coefficient (cm²/s)"
                },
                "Diffusion Coefficients vs Voltage": {
                    "plot_type": "scatter",
                    "x_column": "start_potential_v",
                    "y_column": "diffusion_coefficient_cm2_s",
                    "title": "Diffusion Coefficients vs Starting Potential",
                    "x_label": "Starting Potential (V)",
                    "y_label": "Diffusion Coefficient (cm²/s)"
                }
            }
        ))
        
        # Current Decay Analysis
        self.register_analysis(AnalysisConfig(
            analysis_id="current_decay_analytics",
            name="Current Decay Analysis",
            description="Potentiostatic current decay kinetics analysis",
            category=AnalysisCategory.KINETICS,
            required_techniques=["Potentiostatic"],
            min_segments=1,
            requires_analysis_results=True,
            analysis_function=current_decay_analysis_function,
            output_columns={
                "metrics": ["current_infinity", "current_amplitude", "time_constant_s", "i_ss_a", "i0_amplitude_a", 
                           "i0_a", "tau_s", "current_decay_ratio", "current_decay_percent"],
                "quality": ["r_squared", "rmse", "quality_score", "meets_duration_criteria", "meets_fit_criteria", 
                           "fit_quality", "decay_quality", "extraction_quality"],
                "insights": ["fit_type", "extraction_method", "kinetic_regime", "decay_completeness", 
                            "analysis_type", "insight_fit_quality", "insight_decay_kinetics", 
                            "insight_time_constant_analysis", "insight_current_magnitude", "insight_decay_completeness"]
            },
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
            default_plot=PlotType.TIME_SERIES,
            plot_config={
                "Decay Constant vs Time": {
                    "plot_type": "line",
                    "x_column": "start_time_s",
                    "y_column": "tau_s",
                    "title": "Current Decay Constant Over Time",
                    "x_label": "Time (s)",
                    "y_label": "Decay Constant (s)"
                },
                "Current Drop Distribution": {
                    "plot_type": "histogram",
                    "x_column": "current_decay_percent",
                    "title": "Current Decay Distribution",
                    "x_label": "Current Drop (%)",
                    "y_label": "Count"
                }
            }
        ))
        
        # dQ/dV Analysis (placeholder - not implemented yet)
        # self.register_analysis(AnalysisConfig(
        #     analysis_id="dqdv_analysis",
        #     name="dQ/dV Analysis",
        #     description="Differential capacity analysis (coming soon)",
        #     category=AnalysisCategory.THERMODYNAMICS,
        #     min_segments=1,
        #     analysis_function=lambda segments, settings: pd.DataFrame([{
        #         'segment_id': None,
        #         'error_message': "dQ/dV analysis not implemented yet. Coming in future version.",
        #         'analysis_type': 'dqdv_analysis',
        #         'placeholder': True
        #     }]),
        #     available_plots=[PlotType.TIME_SERIES],
        #     default_plot=PlotType.TIME_SERIES,
        #     plot_config={
        #         "Placeholder Plot 1": {
        #             "plot_type": "line",
        #             "x_column": "segment_id",
        #             "y_column": "placeholder",
        #             "title": "dQ/dV Analysis (Coming Soon)",
        #             "x_label": "Segment ID",
        #             "y_label": "Placeholder"
        #         },
        #         "Placeholder Plot 2": {
        #             "plot_type": "histogram",
        #             "x_column": "placeholder",
        #             "title": "dQ/dV Distribution (Coming Soon)",
        #             "x_label": "Placeholder",
        #             "y_label": "Count"
        #         }
        #     }
        # ))


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
                    settings: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
    """Execute analysis (convenience function)."""
    registry = get_analysis_registry()
    return registry.execute_analysis(analysis_id, segments, settings or {}, **kwargs)

def validate_analysis_request(analysis_id: str, segments: List[Dict[str, Any]]) -> tuple[bool, str]:
    """Validate analysis request (convenience function)."""
    registry = get_analysis_registry()
    return registry.validate_analysis_request(analysis_id, segments)