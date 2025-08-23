"""
Tab 3 Data Analysis - Plotting & Visualization Management  

Handles all plotting functionality and plot controls.
Generates analysis-specific visualizations.

Architecture: Plot generation dispatcher with analysis-specific methods.
"""

import panel as pn
import holoviews as hv
import pandas as pd
from typing import Dict, List, Any, Optional


class PlottingManager:
    """
    Handles all plotting functionality and plot controls.
    Generates analysis-specific visualizations.
    
    Phase 1: Basic plot area placeholder and simple controls
    Phase 2: Basic plotting with backend data
    Phase 3: Analysis-specific plot generation
    Phase 4: Advanced plot controls and export
    """
    
    def __init__(self, api):
        self.api = api
        
        # Create plot controls and area
        self._create_plot_area()
        self._create_plot_controls()
        
        # Current state
        self.current_plot = None
        self.current_analysis = "basic_statistics"
        self.available_plot_types = ["summary_table"]
    
    def _create_plot_area(self):
        """Create main plot area."""
        
        # Initialize with placeholder
        self.plot_area = pn.pane.HTML(
            """
            <div style='border: 2px dashed #E0E0E0; border-radius: 8px; 
                        padding: 40px; text-align: center; color: #666;
                        background: #FAFAFA; min-height: 300px;
                        display: flex; align-items: center; justify-content: center;'>
                <div>
                    <div style='font-size: 48px; margin-bottom: 10px;'>📊</div>
                    <div style='font-size: 18px; margin-bottom: 5px;'>Ready for Analysis</div>
                    <div style='font-size: 14px;'>Select groups and click "Analyze" to generate plots</div>
                </div>
            </div>
            """,
            height=350,
            width=500
        )
        
    def get_plot_area(self):
        """Return the main plot area."""
        return self.plot_area
    
    def _create_plot_controls(self):
        """Create plot controls interface."""
        
        # Basic plot controls (always visible)
        self.plot_type_selector = pn.widgets.Select(
            name="Plot Type",
            options=[("Summary Table", "summary_table")],
            value="summary_table",
            width=200
        )
        
        self.export_plot_btn = pn.widgets.Button(
            name="💾 Export Plot",
            button_type="default",
            width=120,
            disabled=True  # Disabled until plot is generated
        )
        
        self.plot_settings_btn = pn.widgets.Button(
            name="⚙️ Settings",
            button_type="default",
            width=80,
            disabled=True  # Phase 1: disabled
        )
        
        # Basic controls row
        self.basic_controls = pn.Row(
            self.plot_type_selector,
            pn.Spacer(width=20),
            self.export_plot_btn,
            self.plot_settings_btn,
            margin=(10, 0)
        )
        
        # Advanced controls (placeholder for future phases)
        self.advanced_controls = pn.Column(
            pn.pane.HTML("""
            <div style='color: #666; font-style: italic; padding: 10px;'>
                Advanced plot controls will be available in future phases...
            </div>
            """),
            collapsed=True,  # Start collapsed
            visible=False    # Hidden in Phase 1
        )
        
        # Complete plot controls
        self.plot_controls = pn.Column(
            self.basic_controls,
            self.advanced_controls,
            width=500
        )
    
    def get_plot_controls(self):
        """Return the plot controls panel."""
        return self.plot_controls
    
    # ===== PLOT GENERATION =====
    
    def create_plot(self, analysis_type: str, data: Dict[str, Any], settings: Dict[str, Any]) -> Any:
        """Main plot generation dispatcher."""
        
        try:
            if analysis_type == "basic_statistics":
                return self._create_basic_statistics_plot(data, settings)
            elif analysis_type == "dqdv_analysis":
                return self._create_dqdv_plot(data, settings)
            elif analysis_type == "kinetics_analysis":
                return self._create_kinetics_plot(data, settings)
            else:
                return self._create_empty_plot(f"Unknown analysis type: {analysis_type}")
                
        except Exception as e:
            return self._create_empty_plot(f"Error creating plot: {str(e)}")
    
    def _create_basic_statistics_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create basic statistics visualization - Phase 3: Enhanced with real data."""
        
        if not data:
            return self._create_empty_plot("No data available for basic statistics")
        
        # Phase 3: Enhanced visualization with real backend data
        
        # Get current plot type
        plot_type = self.plot_type_selector.value
        
        if plot_type == "summary_table":
            return self._create_statistics_table(data)
        elif plot_type == "histogram":
            return self._create_statistics_histogram(data)  
        elif plot_type == "box_plot":
            return self._create_statistics_boxplot(data)
        else:
            return self._create_statistics_table(data)  # Default
    
    def _create_statistics_table(self, data: Dict[str, Any]):
        """Create enhanced statistics table with real data."""
        
        # Extract real values with fallback
        duration_mean = data.get('duration_mean', 0)
        duration_std = data.get('duration_std', 0) 
        voltage_mean = data.get('voltage_mean', 0)
        voltage_std = data.get('voltage_std', 0)
        capacity_mean = data.get('capacity_mean', 0)
        capacity_std = data.get('capacity_std', 0)
        total_segments = data.get('total_segments', 0)
        total_groups = data.get('total_groups', 0)
        
        # Check if we have real data or fallback
        has_real_data = 'backend_results' in data
        data_source = "Real electrochemical analysis" if has_real_data else "Simulated data"
        
        summary_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>📊 Basic Statistics Summary</h3>
                <div style='color: #666; font-size: 12px;'>
                    {total_groups} groups • {total_segments} segments<br>
                    <em>{data_source}</em>
                </div>
            </div>
            
            <table style='width: 100%; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                <thead>
                    <tr style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white;'>
                        <th style='padding: 12px; text-align: left; font-weight: 600;'>Metric</th>
                        <th style='padding: 12px; text-align: right; font-weight: 600;'>Mean</th>
                        <th style='padding: 12px; text-align: right; font-weight: 600;'>Std Dev</th>
                        <th style='padding: 12px; text-align: right; font-weight: 600;'>Units</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style='background: white;'>
                        <td style='padding: 10px; border-bottom: 1px solid #E0E0E0; font-weight: 500;'>Duration</td>
                        <td style='padding: 10px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{duration_mean:.1f}</td>
                        <td style='padding: 10px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>±{duration_std:.1f}</td>
                        <td style='padding: 10px; text-align: right; border-bottom: 1px solid #E0E0E0; color: #666;'>seconds</td>
                    </tr>
                    <tr style='background: #F8F9FA;'>
                        <td style='padding: 10px; border-bottom: 1px solid #E0E0E0; font-weight: 500;'>Start Voltage</td>
                        <td style='padding: 10px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{voltage_mean:.3f}</td>
                        <td style='padding: 10px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>±{voltage_std:.3f}</td>
                        <td style='padding: 10px; text-align: right; border-bottom: 1px solid #E0E0E0; color: #666;'>V</td>
                    </tr>
                    <tr style='background: white;'>
                        <td style='padding: 10px; border-bottom: 1px solid #E0E0E0; font-weight: 500;'>Capacity</td>
                        <td style='padding: 10px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{capacity_mean:.4f}</td>
                        <td style='padding: 10px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>±{capacity_std:.4f}</td>
                        <td style='padding: 10px; text-align: right; border-bottom: 1px solid #E0E0E0; color: #666;'>Ah</td>
                    </tr>
                </tbody>
            </table>
            
            <div style='margin-top: 20px; padding: 12px; background: #E3F2FD; border-radius: 6px; border-left: 4px solid #1976D2;'>
                <strong style='color: #1976D2;'>Analysis Details:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Analyzed {total_groups} groups with {total_segments} total segments<br>
                    Timestamp: {data.get('analysis_timestamp', 'Unknown')}<br>
                    {f"Error: {data['error']}" if 'error' in data else "Analysis completed successfully"}
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(summary_html)
    
    def _create_statistics_histogram(self, data: Dict[str, Any]):
        """Create histogram visualization for statistics."""
        
        # Phase 3: Placeholder for future histogram implementation
        return self._create_empty_plot("Histogram visualization will be implemented in future phases")
    
    def _create_statistics_boxplot(self, data: Dict[str, Any]):
        """Create box plot visualization for statistics."""
        
        # Phase 3: Placeholder for future box plot implementation
        return self._create_empty_plot("Box plot visualization will be implemented in future phases")
    
    def _create_dqdv_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create dQ/dV analysis plot."""
        
        # Phase 1: Placeholder
        return self._create_empty_plot("dQ/dV plotting will be implemented in Phase 3")
    
    def _create_kinetics_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create kinetics analysis plot."""
        
        # Phase 1: Placeholder  
        return self._create_empty_plot("Kinetics plotting will be implemented in Phase 3")
    
    def _create_empty_plot(self, message: str = "No data to display"):
        """Create empty plot with message."""
        
        return pn.pane.HTML(f"""
        <div style='border: 2px dashed #E0E0E0; border-radius: 8px; 
                    padding: 40px; text-align: center; color: #666;
                    background: #FAFAFA; min-height: 200px;
                    display: flex; align-items: center; justify-content: center;'>
            <div>
                <div style='font-size: 36px; margin-bottom: 10px;'>📈</div>
                <div style='font-size: 16px;'>{message}</div>
            </div>
        </div>
        """)
    
    # ===== PLOT MANAGEMENT =====
    
    def update_plot_area(self, plot_object):
        """Update the plot area with new plot."""
        
        self.current_plot = plot_object
        self.plot_area.object = plot_object
        
        # Enable export button when plot is available
        self.export_plot_btn.disabled = (plot_object is None)
    
    def update_available_plots(self, analysis_type: str):
        """Update available plot types for analysis."""
        
        self.current_analysis = analysis_type
        
        # Update available plot types based on analysis
        if analysis_type == "basic_statistics":
            plot_options = [
                ("Summary Table", "summary_table"),
                ("Histogram", "histogram"),
                ("Box Plot", "box_plot")
            ]
        elif analysis_type == "dqdv_analysis":
            plot_options = [
                ("dQ/dV vs Voltage", "dqdv_voltage"),
                ("Peak Analysis", "peak_analysis"),
                ("Overlay Comparison", "overlay_comparison")
            ]
        elif analysis_type == "kinetics_analysis":
            plot_options = [
                ("Voltage vs Time", "voltage_time"),
                ("Kinetics Fit", "kinetics_fit"), 
                ("Fit Quality", "fit_quality")
            ]
        else:
            plot_options = [("Summary Table", "summary_table")]
        
        # Update selector options
        self.plot_type_selector.options = plot_options
        self.plot_type_selector.value = plot_options[0][1]  # Select first option
    
    # ===== STYLING AND UTILITIES =====
    
    def _apply_electrochemical_styling(self, plot):
        """Apply professional electrochemical styling to plots."""
        # Phase 3: Add professional styling
        return plot
    
    def _create_publication_plot(self, plot, settings: Dict[str, Any]):
        """Create publication-ready version of plot."""
        # Phase 4: Add publication formatting
        return plot
    
    # ===== EXPORT FUNCTIONALITY =====
    
    def export_current_plot(self, format: str = "png", **kwargs):
        """Export current plot to specified format.""" 
        
        if self.current_plot is None:
            return False
        
        # Phase 1: Placeholder
        print(f"Plot export functionality will be implemented in Phase 4")
        print(f"Requested format: {format}")
        return True