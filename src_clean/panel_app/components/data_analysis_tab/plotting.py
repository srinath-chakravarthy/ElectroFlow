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
        """Create dQ/dV analysis plot with real electrochemical insights data."""
        
        if not data or 'electrochemical_insights' not in data:
            return self._create_empty_plot("No dQ/dV analysis data available")
        
        # Get current plot type
        plot_type = self.plot_type_selector.value
        
        if plot_type == "dqdv_voltage":
            return self._create_dqdv_voltage_table(data)
        elif plot_type == "peak_analysis":
            return self._create_dqdv_peak_analysis(data)  
        elif plot_type == "overlay_comparison":
            return self._create_dqdv_overlay_comparison(data)
        else:
            return self._create_dqdv_voltage_table(data)  # Default
    
    def _create_kinetics_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create kinetics analysis plot with real electrochemical data."""
        
        if not data or 'kinetics_analysis' not in data:
            return self._create_empty_plot("No kinetics analysis data available")
        
        # Get current plot type
        plot_type = self.plot_type_selector.value
        
        if plot_type == "voltage_time":
            return self._create_kinetics_voltage_table(data)
        elif plot_type == "kinetics_fit":
            return self._create_kinetics_fit_summary(data)
        elif plot_type == "fit_quality":
            return self._create_kinetics_quality_table(data)
        else:
            return self._create_kinetics_voltage_table(data)  # Default
    
    # ===== dQ/dV VISUALIZATION METHODS =====
    
    def _create_dqdv_voltage_table(self, data: Dict[str, Any]):
        """Create dQ/dV voltage relaxation analysis table."""
        
        insights = data.get('electrochemical_insights', {})
        rest_analysis = insights.get('rest_analysis', {})
        
        # Extract voltage relaxation data
        rest_data = []
        for segment_id, segment_data in rest_analysis.items():
            if segment_data and 'voltage_relaxation' in segment_data:
                relaxation = segment_data['voltage_relaxation']
                rest_data.append({
                    'segment_id': segment_id,
                    'initial_v': relaxation.get('initial_voltage_v', 0.0),
                    'equilibrium_v': relaxation.get('equilibrium_voltage_v', 0.0), 
                    'time_constant_s': relaxation.get('time_constant_s', 0.0),
                    'r_squared': relaxation.get('r_squared', 0.0),
                    'voltage_drop_mv': relaxation.get('voltage_drop_mv', 0.0)
                })
        
        if not rest_data:
            return self._create_empty_plot("No voltage relaxation data available for dQ/dV analysis")
        
        # Create summary table
        total_segments = len(rest_data)
        avg_time_constant = sum(d['time_constant_s'] for d in rest_data) / total_segments
        avg_voltage_drop = sum(d['voltage_drop_mv'] for d in rest_data) / total_segments
        
        # Build HTML table
        rows_html = ""
        for i, row in enumerate(rest_data[:10]):  # Show first 10
            style = "background: white;" if i % 2 == 0 else "background: #F8F9FA;"
            rows_html += f"""
            <tr style='{style}'>
                <td style='padding: 8px; border-bottom: 1px solid #E0E0E0;'>{row['segment_id'][:12]}...</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{row['initial_v']:.3f}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{row['equilibrium_v']:.3f}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{row['time_constant_s']:.1f}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{row['voltage_drop_mv']:.1f}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{row['r_squared']:.3f}</td>
            </tr>
            """
        
        voltage_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>⚡ dQ/dV - Voltage Relaxation Analysis</h3>
                <div style='color: #666; font-size: 12px;'>
                    {total_segments} rest segments analyzed<br>
                    <em>Electrochemical insights backend</em>
                </div>
            </div>
            
            <table style='width: 100%; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                <thead>
                    <tr style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white;'>
                        <th style='padding: 12px; text-align: left; font-weight: 600;'>Segment</th>
                        <th style='padding: 12px; text-align: right; font-weight: 600;'>Initial V</th>
                        <th style='padding: 12px; text-align: right; font-weight: 600;'>Equilibrium V</th>
                        <th style='padding: 12px; text-align: right; font-weight: 600;'>τ (s)</th>
                        <th style='padding: 12px; text-align: right; font-weight: 600;'>ΔV (mV)</th>
                        <th style='padding: 12px; text-align: right; font-weight: 600;'>R²</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            
            <div style='margin-top: 20px; padding: 12px; background: #E3F2FD; border-radius: 6px; border-left: 4px solid #1976D2;'>
                <strong style='color: #1976D2;'>Analysis Summary:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Average time constant: <strong>{avg_time_constant:.1f} s</strong><br>
                    Average voltage drop: <strong>{avg_voltage_drop:.1f} mV</strong><br>
                    {f"Showing first 10 of {total_segments} segments" if total_segments > 10 else f"All {total_segments} segments displayed"}
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(voltage_html)
    
    def _create_dqdv_peak_analysis(self, data: Dict[str, Any]):
        """Create dQ/dV peak analysis placeholder."""
        return self._create_empty_plot("dQ/dV peak analysis visualization will be enhanced in future phases")
    
    def _create_dqdv_overlay_comparison(self, data: Dict[str, Any]):
        """Create dQ/dV overlay comparison placeholder."""
        return self._create_empty_plot("dQ/dV overlay comparison will be enhanced in future phases")
    
    # ===== KINETICS VISUALIZATION METHODS =====
    
    def _create_kinetics_voltage_table(self, data: Dict[str, Any]):
        """Create kinetics voltage analysis table."""
        
        kinetics_data = data.get('kinetics_analysis', {})
        
        # Extract time constants data
        time_constants = kinetics_data.get('time_constants', [])
        diffusion_coeffs = kinetics_data.get('diffusion_coefficients', [])
        resistance_data = kinetics_data.get('resistance_analysis', {})
        
        if not time_constants and not diffusion_coeffs:
            return self._create_empty_plot("No kinetics analysis data available")
        
        # Build time constants table
        tc_rows = ""
        for i, tc in enumerate(time_constants[:8]):  # Show first 8
            style = "background: white;" if i % 2 == 0 else "background: #F8F9FA;"
            tc_rows += f"""
            <tr style='{style}'>
                <td style='padding: 8px; border-bottom: 1px solid #E0E0E0;'>τ{i+1}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{tc:.2f}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0;'>Voltage relaxation</td>
            </tr>
            """
        
        # Build diffusion coefficients table  
        dc_rows = ""
        for i, dc in enumerate(diffusion_coeffs[:5]):
            style = "background: white;" if i % 2 == 0 else "background: #F8F9FA;"
            dc_rows += f"""
            <tr style='{style}'>
                <td style='padding: 8px; border-bottom: 1px solid #E0E0E0;'>D{i+1}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{dc:.2e}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0;'>cm²/s</td>
            </tr>
            """
        
        # Resistance summary
        resistance_summary = ""
        if resistance_data:
            avg_resistance = resistance_data.get('average_resistance_ohm', 0.0)
            resistance_summary = f"""
            <div style='margin-top: 20px; padding: 12px; background: #FFF3E0; border-radius: 6px; border-left: 4px solid #FF9800;'>
                <strong style='color: #FF9800;'>Resistance Analysis:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Average IR resistance: <strong>{avg_resistance:.4f} Ω</strong><br>
                    Analysis method: Current pulse response
                </div>
            </div>
            """
        
        kinetics_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>⚗️ Kinetics - Voltage & Time Analysis</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(time_constants)} time constants<br>
                    <em>Electrochemical kinetics backend</em>
                </div>
            </div>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 20px;'>
                <div>
                    <h4 style='color: #1976D2; margin-bottom: 10px;'>Time Constants</h4>
                    <table style='width: 100%; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                        <thead>
                            <tr style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white;'>
                                <th style='padding: 10px; text-align: left; font-weight: 600;'>Parameter</th>
                                <th style='padding: 10px; text-align: right; font-weight: 600;'>Value (s)</th>
                                <th style='padding: 10px; text-align: right; font-weight: 600;'>Process</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tc_rows}
                        </tbody>
                    </table>
                </div>
                
                <div>
                    <h4 style='color: #1976D2; margin-bottom: 10px;'>Diffusion Coefficients</h4>
                    <table style='width: 100%; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                        <thead>
                            <tr style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white;'>
                                <th style='padding: 10px; text-align: left; font-weight: 600;'>Parameter</th>
                                <th style='padding: 10px; text-align: right; font-weight: 600;'>Value</th>
                                <th style='padding: 10px; text-align: right; font-weight: 600;'>Units</th>
                            </tr>
                        </thead>
                        <tbody>
                            {dc_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            
            {resistance_summary}
        </div>
        """
        
        return pn.pane.HTML(kinetics_html)
    
    def _create_kinetics_fit_summary(self, data: Dict[str, Any]):
        """Create kinetics fit quality summary."""
        
        kinetics_data = data.get('kinetics_analysis', {})
        equilibrium_data = kinetics_data.get('equilibrium_analysis', {})
        
        if not equilibrium_data:
            return self._create_empty_plot("No equilibrium analysis data available for fit summary")
        
        # Extract equilibrium voltages
        eq_voltages = []
        for segment_id, eq_data in equilibrium_data.items():
            if eq_data and 'equilibrium_voltage_v' in eq_data:
                eq_voltages.append({
                    'segment_id': segment_id,
                    'equilibrium_v': eq_data['equilibrium_voltage_v'],
                    'confidence': eq_data.get('confidence_level', 0.0),
                    'method': eq_data.get('analysis_method', 'Unknown')
                })
        
        if not eq_voltages:
            return self._create_empty_plot("No equilibrium voltage data available")
        
        # Summary statistics
        avg_voltage = sum(d['equilibrium_v'] for d in eq_voltages) / len(eq_voltages)
        voltage_std = (sum((d['equilibrium_v'] - avg_voltage)**2 for d in eq_voltages) / len(eq_voltages))**0.5
        avg_confidence = sum(d['confidence'] for d in eq_voltages) / len(eq_voltages)
        
        fit_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>🎯 Kinetics Fit - Equilibrium Analysis</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(eq_voltages)} equilibrium points<br>
                    <em>High confidence kinetics fitting</em>
                </div>
            </div>
            
            <div style='display: grid; grid-template-columns: 2fr 1fr; gap: 20px;'>
                <div style='padding: 20px; background: #F8F9FA; border-radius: 8px; border-left: 4px solid #4CAF50;'>
                    <h4 style='color: #4CAF50; margin-top: 0;'>Equilibrium Voltage Summary</h4>
                    <div style='margin-bottom: 15px;'>
                        <div style='font-size: 18px; font-weight: 600; color: #2E4057;'>{avg_voltage:.4f} ± {voltage_std:.4f} V</div>
                        <div style='color: #666; font-size: 14px;'>Mean equilibrium voltage</div>
                    </div>
                    <div style='margin-bottom: 15px;'>
                        <div style='font-size: 16px; font-weight: 600; color: #2E4057;'>{avg_confidence:.1%}</div>
                        <div style='color: #666; font-size: 14px;'>Average confidence level</div>
                    </div>
                    <div>
                        <div style='font-size: 16px; font-weight: 600; color: #2E4057;'>{len(eq_voltages)}</div>
                        <div style='color: #666; font-size: 14px;'>Segments analyzed</div>
                    </div>
                </div>
                
                <div style='padding: 20px; background: #E8F5E8; border-radius: 8px;'>
                    <h4 style='color: #4CAF50; margin-top: 0;'>Fit Quality</h4>
                    <div style='text-align: center;'>
                        <div style='font-size: 36px; color: #4CAF50; margin: 10px 0;'>
                            {"✓" if avg_confidence > 0.8 else "⚠" if avg_confidence > 0.6 else "✗"}
                        </div>
                        <div style='font-weight: 600; color: #2E4057;'>
                            {"Excellent" if avg_confidence > 0.8 else "Good" if avg_confidence > 0.6 else "Poor"} Fit
                        </div>
                        <div style='color: #666; font-size: 12px; margin-top: 5px;'>
                            Based on confidence metrics
                        </div>
                    </div>
                </div>
            </div>
            
            <div style='margin-top: 20px; padding: 12px; background: #E3F2FD; border-radius: 6px; border-left: 4px solid #1976D2;'>
                <strong style='color: #1976D2;'>Kinetics Analysis Notes:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Equilibrium voltages extracted from voltage relaxation curves<br>
                    High confidence indicates stable electrochemical equilibrium<br>
                    Voltage variation: {(voltage_std/avg_voltage*100):.2f}% relative standard deviation
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(fit_html)
    
    def _create_kinetics_quality_table(self, data: Dict[str, Any]):
        """Create kinetics fit quality assessment table."""
        return self._create_empty_plot("Kinetics fit quality table will be enhanced in future phases")
    
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
        
        # Handle Panel HTML objects vs strings
        if plot_object is None:
            self.plot_area.object = ""
        elif hasattr(plot_object, 'object'):
            # If it's a Panel HTML pane, extract the HTML content
            self.plot_area.object = plot_object.object
        elif isinstance(plot_object, str):
            # If it's already a string, use it directly
            self.plot_area.object = plot_object
        else:
            # Convert to string as fallback
            self.plot_area.object = str(plot_object)
        
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