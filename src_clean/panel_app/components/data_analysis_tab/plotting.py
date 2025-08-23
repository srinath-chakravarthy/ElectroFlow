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
            height=500,
            width=700
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
            elif analysis_type == "resistance_analysis":
                return self._create_resistance_plot(data, settings)
            elif analysis_type == "kinetics_analysis":
                return self._create_kinetics_plot(data, settings)
            elif analysis_type == "dqdv_analysis":
                return self._create_dqdv_plot(data, settings)
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
        """Create histogram visualization for per-technique statistics with real electrochemical data."""
        
        technique_breakdown = data.get('technique_breakdown', {})
        techniques_found = data.get('techniques_found', [])
        total_segments = data.get('total_segments', 0)
        
        if not technique_breakdown:
            return self._create_empty_plot("No statistical data available for histogram")
        
        # Extract data for histogram visualization
        metrics_data = []
        for metric_name, metric_stats in backend_results.items():
            if isinstance(metric_stats, dict) and 'count' in metric_stats:
                count = metric_stats.get('count', 0)
                mean = metric_stats.get('mean', 0)
                std = metric_stats.get('std', 0)
                
                # Create distribution info for display
                metrics_data.append({
                    'metric': metric_name.replace('_', ' ').title(),
                    'mean': mean,
                    'std': std,
                    'count': count,
                    'min': metric_stats.get('min', 0),
                    'max': metric_stats.get('max', 0)
                })
        
        if not metrics_data:
            return self._create_empty_plot("No statistical distributions available")
        
        # Create histogram visualization with distribution data
        histogram_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>📊 Statistical Distributions - Histogram View</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(metrics_data)} metrics analyzed<br>
                    <em>Distribution analysis from backend</em>
                </div>
            </div>
            
            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;'>
        """
        
        # Create distribution cards for each metric
        for i, metric in enumerate(metrics_data[:6]):  # Show first 6 metrics
            # Calculate distribution range for visual representation
            range_val = metric['max'] - metric['min']
            normalized_std = (metric['std'] / range_val * 100) if range_val > 0 else 0
            
            # Color scheme for different metrics
            colors = ['#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#C62828', '#00796B']
            color = colors[i % len(colors)]
            
            histogram_html += f"""
                <div style='background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid {color};'>
                    <h4 style='color: {color}; margin: 0 0 12px 0; font-size: 16px;'>{metric['metric']}</h4>
                    
                    <!-- Distribution visualization -->
                    <div style='background: #F5F5F5; height: 80px; border-radius: 4px; margin-bottom: 12px; position: relative; overflow: hidden;'>
                        <div style='position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); 
                                    width: {min(normalized_std + 20, 90)}%; height: 60%; background: {color}; 
                                    border-radius: 4px 4px 0 0; opacity: 0.3;'></div>
                        <div style='position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); 
                                    width: 8px; height: 80%; background: {color}; border-radius: 2px;'></div>
                        <div style='position: absolute; top: 8px; right: 8px; font-size: 10px; color: #666;'>n={metric['count']}</div>
                    </div>
                    
                    <!-- Statistics -->
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;'>
                        <div><strong>Mean:</strong> {metric['mean']:.3f}</div>
                        <div><strong>Std:</strong> {metric['std']:.3f}</div>
                        <div><strong>Min:</strong> {metric['min']:.3f}</div>
                        <div><strong>Max:</strong> {metric['max']:.3f}</div>
                    </div>
                </div>
            """
        
        histogram_html += """
            </div>
            
            <div style='margin-top: 20px; padding: 12px; background: #E3F2FD; border-radius: 6px; border-left: 4px solid #1976D2;'>
                <strong style='color: #1976D2;'>Distribution Analysis:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Visual representation shows mean (dark bar) and standard deviation (light area)<br>
                    Each metric's distribution characteristics displayed with sample count<br>
                    Data sourced from electrochemical analysis backend
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(histogram_html)
    
    def _create_statistics_boxplot(self, data: Dict[str, Any]):
        """Create box plot visualization for statistics with real electrochemical data."""
        
        backend_results = data.get('backend_results', {})
        
        if not backend_results:
            return self._create_empty_plot("No statistical data available for box plots")
        
        # Extract data for box plot visualization
        metrics_data = []
        for metric_name, metric_stats in backend_results.items():
            if isinstance(metric_stats, dict) and all(k in metric_stats for k in ['min', 'max', 'mean']):
                metrics_data.append({
                    'metric': metric_name.replace('_', ' ').title(),
                    'min': metric_stats.get('min', 0),
                    'q1': metric_stats.get('mean', 0) - metric_stats.get('std', 0) * 0.5,  # Approx Q1
                    'median': metric_stats.get('mean', 0),  # Use mean as median approximation
                    'q3': metric_stats.get('mean', 0) + metric_stats.get('std', 0) * 0.5,  # Approx Q3
                    'max': metric_stats.get('max', 0),
                    'mean': metric_stats.get('mean', 0),
                    'std': metric_stats.get('std', 0),
                    'count': metric_stats.get('count', 0)
                })
        
        if not metrics_data:
            return self._create_empty_plot("No statistical distributions available for box plots")
        
        # Create box plot visualization
        boxplot_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>📦 Statistical Distributions - Box Plot View</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(metrics_data)} metrics analyzed<br>
                    <em>Five-number summary from backend</em>
                </div>
            </div>
            
            <div style='display: flex; flex-direction: column; gap: 20px;'>
        """
        
        # Create box plot for each metric
        for i, metric in enumerate(metrics_data[:8]):  # Show first 8 metrics
            # Normalize values for visual representation (0-100 scale)
            value_range = metric['max'] - metric['min']
            if value_range == 0:
                continue
                
            # Calculate positions as percentages
            q1_pos = ((metric['q1'] - metric['min']) / value_range) * 80 + 10
            median_pos = ((metric['median'] - metric['min']) / value_range) * 80 + 10  
            q3_pos = ((metric['q3'] - metric['min']) / value_range) * 80 + 10
            mean_pos = ((metric['mean'] - metric['min']) / value_range) * 80 + 10
            
            # Color scheme for different metrics
            colors = ['#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#C62828', '#00796B', '#795548', '#607D8B']
            color = colors[i % len(colors)]
            
            boxplot_html += f"""
                <div style='background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid {color};'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;'>
                        <h4 style='color: {color}; margin: 0; font-size: 16px;'>{metric['metric']}</h4>
                        <span style='color: #666; font-size: 12px;'>n = {metric['count']}</span>
                    </div>
                    
                    <!-- Box plot visualization -->
                    <div style='position: relative; height: 60px; background: #F8F9FA; border-radius: 6px; margin-bottom: 15px;'>
                        <!-- Whisker line (min to max) -->
                        <div style='position: absolute; top: 50%; left: 10%; right: 10%; height: 2px; background: {color}; transform: translateY(-50%);'></div>
                        
                        <!-- Box (Q1 to Q3) -->
                        <div style='position: absolute; top: 25%; left: {q1_pos}%; width: {q3_pos - q1_pos}%; height: 50%; 
                                    background: {color}; opacity: 0.3; border-radius: 3px;'></div>
                        <div style='position: absolute; top: 25%; left: {q1_pos}%; width: {q3_pos - q1_pos}%; height: 50%; 
                                    border: 2px solid {color}; border-radius: 3px;'></div>
                        
                        <!-- Median line -->
                        <div style='position: absolute; top: 20%; left: {median_pos}%; width: 2px; height: 60%; background: {color};'></div>
                        
                        <!-- Mean marker (diamond) -->
                        <div style='position: absolute; top: 50%; left: {mean_pos}%; width: 8px; height: 8px; 
                                    background: {color}; transform: translate(-50%, -50%) rotate(45deg); border: 1px solid white;'></div>
                        
                        <!-- Min/Max markers -->
                        <div style='position: absolute; top: 35%; left: 10%; width: 2px; height: 30%; background: {color};'></div>
                        <div style='position: absolute; top: 35%; right: 10%; width: 2px; height: 30%; background: {color};'></div>
                        
                        <!-- Value labels -->
                        <div style='position: absolute; top: -15px; left: 10%; font-size: 10px; color: #666; transform: translateX(-50%);'>{metric['min']:.3f}</div>
                        <div style='position: absolute; top: -15px; right: 10%; font-size: 10px; color: #666; transform: translateX(50%);'>{metric['max']:.3f}</div>
                        <div style='position: absolute; bottom: -15px; left: {median_pos}%; font-size: 10px; color: {color}; transform: translateX(-50%);'>{metric['median']:.3f}</div>
                    </div>
                    
                    <!-- Statistics summary -->
                    <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; font-size: 11px; text-align: center;'>
                        <div style='padding: 4px; background: #F5F5F5; border-radius: 3px;'>
                            <div style='font-weight: bold; color: {color};'>Q1</div>
                            <div>{metric['q1']:.3f}</div>
                        </div>
                        <div style='padding: 4px; background: #F5F5F5; border-radius: 3px;'>
                            <div style='font-weight: bold; color: {color};'>Median</div>
                            <div>{metric['median']:.3f}</div>
                        </div>
                        <div style='padding: 4px; background: #F5F5F5; border-radius: 3px;'>
                            <div style='font-weight: bold; color: {color};'>Q3</div>
                            <div>{metric['q3']:.3f}</div>
                        </div>
                        <div style='padding: 4px; background: #F5F5F5; border-radius: 3px;'>
                            <div style='font-weight: bold; color: {color};'>Mean</div>
                            <div>{metric['mean']:.3f}</div>
                        </div>
                    </div>
                </div>
            """
        
        boxplot_html += """
            </div>
            
            <div style='margin-top: 20px; padding: 12px; background: #E8F5E8; border-radius: 6px; border-left: 4px solid #388E3C;'>
                <strong style='color: #388E3C;'>Box Plot Legend:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    📦 <strong>Box:</strong> Q1 to Q3 (interquartile range) • 
                    <strong>Line in box:</strong> Median • 
                    <strong>Diamond:</strong> Mean • 
                    <strong>Whiskers:</strong> Min to Max range<br>
                    Statistical quartiles approximated from mean and standard deviation
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(boxplot_html)
    
    # ===== RESISTANCE ANALYSIS METHODS =====
    
    def _create_resistance_plot(self, data: Dict[str, Any], settings: Dict[str, Any]):
        """Create resistance analysis plot with real electrochemical resistance data."""
        
        if not data or 'resistance_analysis' not in data:
            return self._create_empty_plot("No resistance analysis data available")
        
        # Get current plot type
        plot_type = self.plot_type_selector.value
        
        if plot_type == "resistance_time":
            return self._create_resistance_time_plot(data)
        elif plot_type == "resistance_distribution":
            return self._create_resistance_distribution_plot(data)
        elif plot_type == "resistance_summary":
            return self._create_resistance_summary_plot(data)
        else:
            return self._create_resistance_time_plot(data)  # Default
    
    def _create_resistance_time_plot(self, data: Dict[str, Any]):
        """Create resistance vs time plot with real IR resistance data."""
        
        resistance_analysis = data.get('resistance_analysis', {})
        
        # Check if we have any data structure to work with
        if not resistance_analysis:
            return self._create_empty_plot("No resistance analysis data available")
        
        # Handle case where we have measurements but no valid resistance values
        valid_measurements = resistance_analysis.get('valid_measurements', 0)
        total_measurements = resistance_analysis.get('total_measurements', 0)
        null_measurements = resistance_analysis.get('null_measurements', 0)
        invalid_measurements = resistance_analysis.get('invalid_measurements', 0)
        
        if total_measurements == 0:
            return self._create_empty_plot("No resistance measurements found in backend data")
        
        if valid_measurements == 0:
            # We have measurements but they're all null/invalid - show diagnostic info
            diagnostic_html = f"""
            <div style='padding: 20px;'>
                <div style='background: #FFF3CD; border: 1px solid #F0AD4E; border-radius: 8px; padding: 20px;'>
                    <h3 style='color: #8A6D3B; margin: 0 0 15px 0;'>📊 Resistance Analysis Diagnostic</h3>
                    <div style='color: #8A6D3B; font-size: 14px; line-height: 1.5;'>
                        <strong>Data Status:</strong><br>
                        • Total measurements found: {total_measurements}<br>
                        • Valid measurements: {valid_measurements}<br>
                        • Null measurements: {null_measurements}<br>
                        • Invalid measurements: {invalid_measurements}<br><br>
                        
                        <strong>Possible causes:</strong><br>
                        • Insufficient current pulse data for resistance calculation<br>
                        • Data quality issues in source files<br>
                        • Calculation algorithm unable to determine valid IR values<br><br>
                        
                        <em>Try selecting different groups with current pulse segments or check data quality in the original files.</em>
                    </div>
                </div>
            </div>
            """
            return pn.pane.HTML(diagnostic_html)
        
        # We have valid measurements, proceed with normal plotting
        resistance_values = resistance_analysis.get('resistance_values_ohm', [])
        if not resistance_values:
            return self._create_empty_plot("No valid resistance values available for time plot")
        
        # Extract resistance and time data
        resistance_values = resistance_analysis['resistance_values_ohm']
        time_points = resistance_analysis['time_points_s']
        measurement_types = resistance_analysis.get('measurement_types', set())
        
        if len(resistance_values) != len(time_points):
            return self._create_empty_plot("Resistance and time data length mismatch")
        
        # Group data by time points for visualization
        time_groups = {}
        for i, (resistance, time_point) in enumerate(zip(resistance_values, time_points)):
            if time_point not in time_groups:
                time_groups[time_point] = []
            time_groups[time_point].append(resistance)
        
        # Sort by time points
        sorted_times = sorted(time_groups.keys())
        
        # Create resistance vs time visualization
        resistance_time_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>⚡ Resistance vs Time Analysis</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(resistance_values)} measurements<br>
                    <em>IR resistance evolution</em>
                </div>
            </div>
            
            <!-- Time series visualization -->
            <div style='background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px;'>
                <div style='height: 200px; background: #F8F9FA; border-radius: 6px; position: relative; margin-bottom: 15px;'>
        """
        
        # Calculate plot dimensions and scaling
        if sorted_times:
            max_time = max(sorted_times)
            max_resistance = max(resistance_values)
            min_resistance = min(resistance_values)
            resistance_range = max_resistance - min_resistance
            
            # Plot points and connecting lines
            plot_points = []
            for time_point in sorted_times:
                resistances = time_groups[time_point]
                avg_resistance = sum(resistances) / len(resistances)
                
                # Calculate positions (10% margins)
                x_pos = (time_point / max_time * 80 + 10) if max_time > 0 else 50
                y_pos = (1 - (avg_resistance - min_resistance) / resistance_range) * 80 + 10 if resistance_range > 0 else 50
                
                plot_points.append((x_pos, y_pos, time_point, avg_resistance, len(resistances)))
                
                # Color based on measurement type
                color = '#FF5722' if time_point == 0 else '#2196F3' if time_point == 10 else '#4CAF50'
                
                resistance_time_html += f"""
                    <!-- Data point -->
                    <div style='position: absolute; left: {x_pos}%; top: {y_pos}%; width: 8px; height: 8px; 
                                background: {color}; border-radius: 50%; border: 2px solid white; 
                                transform: translate(-50%, -50%); z-index: 10;' 
                         title='Time: {time_point}s, Resistance: {avg_resistance:.4f}Ω (n={len(resistances)})'></div>
                """
            
            # Connect points with lines
            if len(plot_points) > 1:
                for i in range(len(plot_points) - 1):
                    x1, y1, _, _, _ = plot_points[i]
                    x2, y2, _, _, _ = plot_points[i + 1]
                    
                    # Simple line approximation using CSS
                    resistance_time_html += f"""
                        <div style='position: absolute; left: {x1}%; top: {y1}%; 
                                    width: {abs(x2-x1)}%; height: 2px; background: #666; 
                                    transform-origin: left center; opacity: 0.5;'></div>
                    """
            
            # Add axis labels
            resistance_time_html += f"""
                <!-- Y-axis labels -->
                <div style='position: absolute; left: -40px; top: 10%; color: #666; font-size: 10px; transform: translateY(-50%);'>{max_resistance:.4f}Ω</div>
                <div style='position: absolute; left: -40px; bottom: 10%; color: #666; font-size: 10px; transform: translateY(50%);'>{min_resistance:.4f}Ω</div>
                
                <!-- X-axis labels -->
                <div style='position: absolute; bottom: -20px; left: 10%; color: #666; font-size: 10px; transform: translateX(-50%);'>0s</div>
                <div style='position: absolute; bottom: -20px; right: 10%; color: #666; font-size: 10px; transform: translateX(50%);'>{max_time}s</div>
            """
        
        resistance_time_html += """
                </div>
                
                <!-- Legend -->
                <div style='display: flex; gap: 20px; justify-content: center; font-size: 12px;'>
                    <div style='display: flex; align-items: center; gap: 5px;'>
                        <div style='width: 12px; height: 12px; background: #FF5722; border-radius: 50%;'></div>
                        <span>Immediate (0s)</span>
                    </div>
                    <div style='display: flex; align-items: center; gap: 5px;'>
                        <div style='width: 12px; height: 12px; background: #2196F3; border-radius: 50%;'></div>
                        <span>10s Response</span>
                    </div>
                    <div style='display: flex; align-items: center; gap: 5px;'>
                        <div style='width: 12px; height: 12px; background: #4CAF50; border-radius: 50%;'></div>
                        <span>30s Response</span>
                    </div>
                </div>
            </div>
            
            <div style='margin-top: 15px; padding: 12px; background: #FFF3E0; border-radius: 6px; border-left: 4px solid #FF9800;'>
                <strong style='color: #FF9800;'>IR Resistance Analysis:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Time-resolved internal resistance measurements from current pulse analysis<br>
        """
        
        # Add summary statistics
        if resistance_analysis.get('total_measurements', 0) > 0:
            avg_resistance = resistance_analysis['average_resistance_ohm']
            resistance_std = resistance_analysis.get('resistance_std_ohm', 0)
            
            resistance_time_html += f"""
                    Average resistance: <strong>{avg_resistance:.4f} ± {resistance_std:.4f} Ω</strong> 
                    ({resistance_analysis['total_measurements']} measurements)
            """
        
        resistance_time_html += """
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(resistance_time_html)
    
    def _create_resistance_distribution_plot(self, data: Dict[str, Any]):
        """Create resistance distribution analysis plot with statistical breakdown."""
        
        resistance_analysis = data.get('resistance_analysis', {})
        
        # Check if we have any data structure to work with
        if not resistance_analysis:
            return self._create_empty_plot("No resistance analysis data available")
        
        # Handle case where we have measurements but no valid resistance values
        valid_measurements = resistance_analysis.get('valid_measurements', 0)
        total_measurements = resistance_analysis.get('total_measurements', 0)
        
        if total_measurements == 0:
            return self._create_empty_plot("No resistance measurements found in backend data")
        
        if valid_measurements == 0:
            null_measurements = resistance_analysis.get('null_measurements', 0)
            invalid_measurements = resistance_analysis.get('invalid_measurements', 0)
            
            diagnostic_html = f"""
            <div style='padding: 20px;'>
                <div style='background: #FFF3CD; border: 1px solid #F0AD4E; border-radius: 8px; padding: 20px;'>
                    <h3 style='color: #8A6D3B; margin: 0 0 15px 0;'>📊 Resistance Distribution Diagnostic</h3>
                    <div style='color: #8A6D3B; font-size: 14px; line-height: 1.5;'>
                        <strong>Data Status:</strong><br>
                        • Total measurements: {total_measurements}<br>
                        • Valid measurements: {valid_measurements}<br>
                        • Null measurements: {null_measurements}<br>
                        • Invalid measurements: {invalid_measurements}<br><br>
                        
                        <em>No valid resistance values available for distribution analysis. See time plot for detailed diagnostic information.</em>
                    </div>
                </div>
            </div>
            """
            return pn.pane.HTML(diagnostic_html)
        
        # We have valid measurements, proceed with normal plotting
        resistance_values = resistance_analysis.get('resistance_values_ohm', [])
        if not resistance_values:
            return self._create_empty_plot("No valid resistance values available for distribution plot")
        
        # Extract resistance data
        resistance_values = resistance_analysis['resistance_values_ohm']
        time_points = resistance_analysis['time_points_s']
        measurement_types = resistance_analysis.get('measurement_types', set())
        
        # Group by measurement type (time point)
        type_groups = {}
        for resistance, time_point in zip(resistance_values, time_points):
            time_label = f"{time_point}s"
            if time_label not in type_groups:
                type_groups[time_label] = []
            type_groups[time_label].append(resistance)
        
        # Calculate statistics for each group
        group_stats = {}
        for time_label, resistances in type_groups.items():
            if resistances:
                group_stats[time_label] = {
                    'mean': sum(resistances) / len(resistances),
                    'min': min(resistances),
                    'max': max(resistances),
                    'count': len(resistances),
                    'std': pd.Series(resistances).std() if len(resistances) > 1 else 0
                }
        
        # Create distribution visualization
        distribution_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>📊 Resistance Distribution Analysis</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(resistance_values)} measurements<br>
                    <em>{len(type_groups)} measurement types</em>
                </div>
            </div>
            
            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px;'>
        """
        
        # Create distribution card for each measurement type
        colors = ['#FF5722', '#2196F3', '#4CAF50', '#FF9800', '#9C27B0']
        for i, (time_label, stats) in enumerate(sorted(group_stats.items(), key=lambda x: float(x[0][:-1]))):
            color = colors[i % len(colors)]
            
            # Calculate distribution visualization parameters
            range_val = stats['max'] - stats['min']
            mean_pos = ((stats['mean'] - stats['min']) / range_val * 80 + 10) if range_val > 0 else 50
            std_width = (stats['std'] / range_val * 40) if range_val > 0 else 10
            
            distribution_html += f"""
                <div style='background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid {color};'>
                    <h4 style='color: {color}; margin: 0 0 12px 0; font-size: 16px;'>{time_label} Measurements</h4>
                    
                    <!-- Distribution visualization -->
                    <div style='background: #F5F5F5; height: 60px; border-radius: 4px; margin-bottom: 12px; position: relative; overflow: hidden;'>
                        <!-- Range line -->
                        <div style='position: absolute; top: 50%; left: 10%; right: 10%; height: 2px; background: #DDD; transform: translateY(-50%);'></div>
                        
                        <!-- Standard deviation area -->
                        <div style='position: absolute; top: 25%; left: {mean_pos - std_width/2}%; width: {std_width}%; height: 50%; 
                                    background: {color}; opacity: 0.2; border-radius: 3px;'></div>
                        
                        <!-- Mean line -->
                        <div style='position: absolute; top: 20%; left: {mean_pos}%; width: 3px; height: 60%; background: {color};'></div>
                        
                        <!-- Min/Max markers -->
                        <div style='position: absolute; top: 35%; left: 10%; width: 2px; height: 30%; background: {color}; opacity: 0.7;'></div>
                        <div style='position: absolute; top: 35%; right: 10%; width: 2px; height: 30%; background: {color}; opacity: 0.7;'></div>
                        
                        <!-- Count indicator -->
                        <div style='position: absolute; top: 5px; right: 5px; font-size: 10px; color: #666; background: white; padding: 2px 4px; border-radius: 2px;'>n={stats['count']}</div>
                        
                        <!-- Value labels -->
                        <div style='position: absolute; bottom: -18px; left: 10%; font-size: 9px; color: #666; transform: translateX(-50%);'>{stats['min']:.4f}</div>
                        <div style='position: absolute; bottom: -18px; right: 10%; font-size: 9px; color: #666; transform: translateX(50%);'>{stats['max']:.4f}</div>
                        <div style='position: absolute; top: -15px; left: {mean_pos}%; font-size: 9px; color: {color}; transform: translateX(-50%);'>{stats['mean']:.4f}</div>
                    </div>
                    
                    <!-- Statistics -->
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px;'>
                        <div><strong>Mean:</strong> {stats['mean']:.4f} Ω</div>
                        <div><strong>Std:</strong> {stats['std']:.4f} Ω</div>
                        <div><strong>Range:</strong> {stats['max'] - stats['min']:.4f} Ω</div>
                        <div><strong>CV:</strong> {(stats['std']/stats['mean']*100):.1f}%</div>
                    </div>
                </div>
            """
        
        # Overall statistics summary
        overall_mean = resistance_analysis['average_resistance_ohm']
        overall_std = resistance_analysis.get('resistance_std_ohm', 0)
        total_measurements = resistance_analysis['total_measurements']
        
        distribution_html += f"""
            </div>
            
            <!-- Overall summary -->
            <div style='background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #607D8B;'>
                <h4 style='color: #607D8B; margin: 0 0 15px 0;'>📈 Overall Distribution Summary</h4>
                
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 15px;'>
                    <div style='text-align: center; padding: 10px; background: #F5F5F5; border-radius: 6px;'>
                        <div style='font-size: 18px; font-weight: bold; color: #607D8B;'>{overall_mean:.4f}</div>
                        <div style='font-size: 12px; color: #666;'>Mean Resistance (Ω)</div>
                    </div>
                    <div style='text-align: center; padding: 10px; background: #F5F5F5; border-radius: 6px;'>
                        <div style='font-size: 18px; font-weight: bold; color: #607D8B;'>±{overall_std:.4f}</div>
                        <div style='font-size: 12px; color: #666;'>Standard Deviation (Ω)</div>
                    </div>
                    <div style='text-align: center; padding: 10px; background: #F5F5F5; border-radius: 6px;'>
                        <div style='font-size: 18px; font-weight: bold; color: #607D8B;'>{total_measurements}</div>
                        <div style='font-size: 12px; color: #666;'>Total Measurements</div>
                    </div>
                    <div style='text-align: center; padding: 10px; background: #F5F5F5; border-radius: 6px;'>
                        <div style='font-size: 18px; font-weight: bold; color: #607D8B;'>{(overall_std/overall_mean*100):.1f}%</div>
                        <div style='font-size: 12px; color: #666;'>Coefficient of Variation</div>
                    </div>
                </div>
                
                <div style='color: #666; font-size: 13px; border-top: 1px solid #E0E0E0; padding-top: 10px;'>
                    <strong>Analysis Notes:</strong> Distribution shows resistance variation across measurement time points. 
                    Lower CV indicates more consistent resistance measurements.
                </div>
            </div>
            
            <div style='margin-top: 20px; padding: 12px; background: #E8F5E8; border-radius: 6px; border-left: 4px solid #4CAF50;'>
                <strong style='color: #4CAF50;'>Distribution Legend:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    📊 <strong>Colored area:</strong> Standard deviation range • 
                    <strong>Dark line:</strong> Mean value • 
                    <strong>End markers:</strong> Min/Max range<br>
                    CV (Coefficient of Variation) = Standard Deviation / Mean × 100%
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(distribution_html)
    
    def _create_resistance_summary_plot(self, data: Dict[str, Any]):
        """Create comprehensive IR resistance analysis summary plot."""
        
        resistance_analysis = data.get('resistance_analysis', {})
        
        if not resistance_analysis:
            return self._create_empty_plot("No resistance analysis data available for summary")
        
        # Extract comprehensive data including quality metrics
        total_measurements = resistance_analysis.get('total_measurements', 0)
        valid_measurements = resistance_analysis.get('valid_measurements', 0)
        null_measurements = resistance_analysis.get('null_measurements', 0)
        invalid_measurements = resistance_analysis.get('invalid_measurements', 0)
        
        avg_resistance = resistance_analysis.get('average_resistance_ohm', 0)
        resistance_std = resistance_analysis.get('resistance_std_ohm', 0)
        measurement_types = resistance_analysis.get('measurement_types', set())
        calculation_quality = resistance_analysis.get('calculation_quality', [])
        
        resistance_values = resistance_analysis.get('resistance_values_ohm', [])
        time_points = resistance_analysis.get('time_points_s', [])
        
        # Handle case where we have no valid measurements but show comprehensive diagnostic
        if valid_measurements == 0 and total_measurements > 0:
            diagnostic_html = f"""
            <div style='padding: 20px;'>
                <div style='background: #FFF3CD; border: 1px solid #F0AD4E; border-radius: 8px; padding: 20px;'>
                    <h3 style='color: #8A6D3B; margin: 0 0 15px 0;'>🔍 Comprehensive Resistance Analysis Summary</h3>
                    
                    <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;'>
                        <div style='text-align: center; padding: 15px; background: white; border-radius: 8px; border: 2px solid #F0AD4E;'>
                            <div style='font-size: 24px; font-weight: bold; color: #8A6D3B;'>{total_measurements}</div>
                            <div style='font-size: 12px; color: #8A6D3B;'>Total Measurements</div>
                        </div>
                        <div style='text-align: center; padding: 15px; background: white; border-radius: 8px; border: 2px solid #D32F2F;'>
                            <div style='font-size: 24px; font-weight: bold; color: #D32F2F;'>{valid_measurements}</div>
                            <div style='font-size: 12px; color: #D32F2F;'>Valid Values</div>
                        </div>
                        <div style='text-align: center; padding: 15px; background: white; border-radius: 8px; border: 2px solid #9E9E9E;'>
                            <div style='font-size: 24px; font-weight: bold; color: #9E9E9E;'>{null_measurements}</div>
                            <div style='font-size: 12px; color: #9E9E9E;'>Null Values</div>
                        </div>
                        <div style='text-align: center; padding: 15px; background: white; border-radius: 8px; border: 2px solid #FF5722;'>
                            <div style='font-size: 24px; font-weight: bold; color: #FF5722;'>{invalid_measurements}</div>
                            <div style='font-size: 12px; color: #FF5722;'>Invalid Values</div>
                        </div>
                    </div>
                    
                    <div style='color: #8A6D3B; font-size: 14px; line-height: 1.6;'>
                        <strong>Calculation Quality Status:</strong><br>
                        • Quality indicators: {', '.join(set(calculation_quality)) if calculation_quality else 'None available'}<br>
                        • Measurement types attempted: {', '.join(measurement_types) if measurement_types else 'None detected'}<br><br>
                        
                        <strong>Recommendations:</strong><br>
                        • Verify current pulse segments are present in selected groups<br>
                        • Check data quality and ensure sufficient sampling rate<br>
                        • Consider using groups with galvanostatic charge/discharge segments<br>
                        • Validate that original data files contain current step changes for IR calculation
                    </div>
                </div>
            </div>
            """
            return pn.pane.HTML(diagnostic_html)
        
        # Calculate additional statistics for valid measurements
        min_resistance = min(resistance_values) if resistance_values else 0
        max_resistance = max(resistance_values) if resistance_values else 0
        resistance_range = max_resistance - min_resistance
        cv_percent = (resistance_std / avg_resistance * 100) if avg_resistance > 0 else 0
        
        # Quality assessment
        quality_score = 0
        quality_indicators = []
        
        if total_measurements >= 10:
            quality_score += 25
            quality_indicators.append("✅ Sufficient measurements (≥10)")
        else:
            quality_indicators.append("⚠️ Limited measurements (<10)")
            
        if cv_percent <= 15:
            quality_score += 25
            quality_indicators.append("✅ Low variability (CV ≤ 15%)")
        elif cv_percent <= 30:
            quality_score += 15
            quality_indicators.append("⚠️ Moderate variability (CV 15-30%)")
        else:
            quality_indicators.append("❌ High variability (CV > 30%)")
            
        if len(measurement_types) >= 2:
            quality_score += 25
            quality_indicators.append("✅ Multi-timepoint analysis")
        else:
            quality_indicators.append("⚠️ Single timepoint only")
            
        if avg_resistance > 0:
            quality_score += 25
            quality_indicators.append("✅ Valid resistance measurements")
        else:
            quality_indicators.append("❌ Invalid resistance values")
        
        quality_label = ("Excellent" if quality_score >= 90 else 
                        "Good" if quality_score >= 70 else 
                        "Moderate" if quality_score >= 50 else "Poor")
        
        # Create summary visualization
        summary_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>📋 IR Resistance Analysis Summary</h3>
                <div style='color: #666; font-size: 12px;'>
                    Complete analysis report<br>
                    <em>Quality: {quality_label}</em>
                </div>
            </div>
            
            <!-- Key metrics overview -->
            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px;'>
                <div style='background: linear-gradient(135deg, #FF5722 0%, #FF8A65 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold; margin-bottom: 5px;'>{avg_resistance:.4f} Ω</div>
                    <div style='font-size: 14px; opacity: 0.9;'>Average IR Resistance</div>
                </div>
                <div style='background: linear-gradient(135deg, #2196F3 0%, #64B5F6 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold; margin-bottom: 5px;'>±{resistance_std:.4f} Ω</div>
                    <div style='font-size: 14px; opacity: 0.9;'>Standard Deviation</div>
                </div>
                <div style='background: linear-gradient(135deg, #4CAF50 0%, #81C784 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold; margin-bottom: 5px;'>{total_measurements}</div>
                    <div style='font-size: 14px; opacity: 0.9;'>Total Measurements</div>
                </div>
                <div style='background: linear-gradient(135deg, #FF9800 0%, #FFB74D 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;'>
                    <div style='font-size: 24px; font-weight: bold; margin-bottom: 5px;'>{cv_percent:.1f}%</div>
                    <div style='font-size: 14px; opacity: 0.9;'>Coefficient of Variation</div>
                </div>
            </div>
            
            <!-- Detailed analysis -->
            <div style='display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 20px;'>
                <div style='background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                    <h4 style='color: #2E4057; margin: 0 0 15px 0;'>📊 Statistical Analysis</h4>
                    
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;'>
                        <div style='padding: 10px; background: #F5F5F5; border-radius: 6px;'>
                            <div style='font-size: 12px; color: #666; margin-bottom: 3px;'>Minimum Resistance</div>
                            <div style='font-size: 16px; font-weight: bold; color: #2E4057;'>{min_resistance:.4f} Ω</div>
                        </div>
                        <div style='padding: 10px; background: #F5F5F5; border-radius: 6px;'>
                            <div style='font-size: 12px; color: #666; margin-bottom: 3px;'>Maximum Resistance</div>
                            <div style='font-size: 16px; font-weight: bold; color: #2E4057;'>{max_resistance:.4f} Ω</div>
                        </div>
                        <div style='padding: 10px; background: #F5F5F5; border-radius: 6px;'>
                            <div style='font-size: 12px; color: #666; margin-bottom: 3px;'>Resistance Range</div>
                            <div style='font-size: 16px; font-weight: bold; color: #2E4057;'>{resistance_range:.4f} Ω</div>
                        </div>
                        <div style='padding: 10px; background: #F5F5F5; border-radius: 6px;'>
                            <div style='font-size: 12px; color: #666; margin-bottom: 3px;'>Measurement Types</div>
                            <div style='font-size: 16px; font-weight: bold; color: #2E4057;'>{len(measurement_types)}</div>
                        </div>
                    </div>
                    
                    <div style='border-top: 1px solid #E0E0E0; padding-top: 10px;'>
                        <div style='font-size: 12px; color: #666; margin-bottom: 5px;'>Measurement Distribution:</div>
                        <div style='font-size: 13px;'>{', '.join([f"{t}s" for t in sorted(set(time_points))])}</div>
                    </div>
                </div>
                
                <div style='background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                    <h4 style='color: #2E4057; margin: 0 0 15px 0;'>🎯 Quality Assessment</h4>
                    
                    <div style='text-align: center; margin-bottom: 15px;'>
                        <div style='font-size: 36px; margin-bottom: 5px;'>
                            {"🟢" if quality_score >= 90 else "🟡" if quality_score >= 70 else "🟠" if quality_score >= 50 else "🔴"}
                        </div>
                        <div style='font-size: 18px; font-weight: bold; color: #2E4057; margin-bottom: 3px;'>{quality_label}</div>
                        <div style='font-size: 14px; color: #666;'>{quality_score}/100 points</div>
                    </div>
                    
                    <div style='font-size: 11px; color: #666;'>
                        {chr(10).join(quality_indicators)}
                    </div>
                </div>
            </div>
            
            <div style='padding: 15px; background: #E3F2FD; border-radius: 6px; border-left: 4px solid #1976D2;'>
                <strong style='color: #1976D2;'>IR Resistance Summary:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Internal resistance analysis based on current pulse response measurements. 
                    Lower CV values indicate more consistent electrode behavior. 
                    Multi-timepoint analysis provides insights into resistance evolution dynamics.
                </div>
            </div>
        </div>
        """
        
        return pn.pane.HTML(summary_html)
    
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
        """Create kinetics voltage analysis table - Phase 2.2: Voltage vs time kinetics plots."""
        
        kinetics_data = data.get('kinetics_analysis', {})
        
        # Check if we have any data structure to work with
        if not kinetics_data:
            return self._create_empty_plot("No kinetics analysis data available")
        
        # Handle case where we have measurements but no valid kinetics values
        valid_measurements = kinetics_data.get('valid_measurements', 0)
        total_measurements = kinetics_data.get('total_measurements', 0)
        null_measurements = kinetics_data.get('null_measurements', 0)
        invalid_measurements = kinetics_data.get('invalid_measurements', 0)
        
        if total_measurements == 0:
            return self._create_empty_plot("No kinetics measurements found in backend data")
        
        if valid_measurements == 0:
            # We have measurements but they're all null/invalid - show diagnostic info
            diagnostic_html = f"""
            <div style='padding: 20px;'>
                <div style='background: #FFF3CD; border: 1px solid #F0AD4E; border-radius: 8px; padding: 20px;'>
                    <h3 style='color: #8A6D3B; margin: 0 0 15px 0;'>⚗️ Kinetics Analysis Diagnostic</h3>
                    <div style='color: #8A6D3B; font-size: 14px; line-height: 1.5;'>
                        <strong>Data Status:</strong><br>
                        • Total measurements found: {total_measurements}<br>
                        • Valid measurements: {valid_measurements}<br>
                        • Null measurements: {null_measurements}<br>
                        • Invalid measurements: {invalid_measurements}<br><br>
                        
                        <strong>Possible causes:</strong><br>
                        • No equilibrium segments available for kinetics analysis<br>
                        • Voltage relaxation data quality insufficient for curve fitting<br>
                        • Equilibrium calculation algorithm unable to determine valid parameters<br><br>
                        
                        <em>Try selecting groups with rest/relaxation segments or check data quality in the original files.</em>
                    </div>
                </div>
            </div>
            """
            return pn.pane.HTML(diagnostic_html)
        
        # Extract kinetics data
        time_constants = kinetics_data.get('time_constants', [])
        diffusion_coeffs = kinetics_data.get('diffusion_coefficients', [])
        equilibrium_voltages = kinetics_data.get('equilibrium_voltages', [])
        calculation_quality = kinetics_data.get('calculation_quality', [])
        
        # Show meaningful diagnostic even with some valid data
        if not time_constants and not diffusion_coeffs and not equilibrium_voltages:
            return self._create_empty_plot("No valid kinetics parameters (time constants, diffusion coefficients, or equilibrium voltages) available")
        
        # Build equilibrium voltage table (main kinetics data)
        eq_voltage_rows = ""
        for i, voltage in enumerate(equilibrium_voltages[:10]):  # Show first 10
            style = "background: white;" if i % 2 == 0 else "background: #F8F9FA;"
            eq_voltage_rows += f"""
            <tr style='{style}'>
                <td style='padding: 8px; border-bottom: 1px solid #E0E0E0;'>V_eq{i+1}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{voltage:.4f}</td>
                <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0;'>V</td>
            </tr>
            """
        
        # Build time constants table (if available)
        tc_rows = ""
        if time_constants:
            for i, tc in enumerate(time_constants[:8]):  # Show first 8
                style = "background: white;" if i % 2 == 0 else "background: #F8F9FA;"
                tc_rows += f"""
                <tr style='{style}'>
                    <td style='padding: 8px; border-bottom: 1px solid #E0E0E0;'>τ{i+1}</td>
                    <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{tc:.2f}</td>
                    <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0;'>s</td>
                </tr>
                """
        else:
            tc_rows = """
            <tr><td colspan='3' style='padding: 12px; text-align: center; color: #666; font-style: italic;'>
                No time constants available
            </td></tr>
            """
        
        # Build diffusion coefficients table (if available)  
        dc_rows = ""
        if diffusion_coeffs:
            for i, dc in enumerate(diffusion_coeffs[:5]):
                style = "background: white;" if i % 2 == 0 else "background: #F8F9FA;"
                dc_rows += f"""
                <tr style='{style}'>
                    <td style='padding: 8px; border-bottom: 1px solid #E0E0E0;'>D{i+1}</td>
                    <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0; font-family: monospace;'>{dc:.2e}</td>
                    <td style='padding: 8px; text-align: right; border-bottom: 1px solid #E0E0E0;'>cm²/s</td>
                </tr>
                """
        else:
            dc_rows = """
            <tr><td colspan='3' style='padding: 12px; text-align: center; color: #666; font-style: italic;'>
                No diffusion coefficients available
            </td></tr>
            """
        
        # Quality summary
        quality_stats = {}
        for quality in calculation_quality:
            quality_stats[quality] = quality_stats.get(quality, 0) + 1
        
        quality_summary = ""
        if quality_stats:
            quality_items = [f"{quality}: {count}" for quality, count in quality_stats.items()]
            quality_summary = f"""
            <div style='margin-top: 20px; padding: 12px; background: #E8F5E8; border-radius: 6px; border-left: 4px solid #4CAF50;'>
                <strong style='color: #4CAF50;'>Calculation Quality:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    {' • '.join(quality_items)}<br>
                    Analysis method: Equilibrium voltage calculation
                </div>
            </div>
            """
        
        kinetics_html = f"""
        <div style='width: 100%; max-width: 700px; padding: 10px; margin: 0; overflow: hidden; box-sizing: border-box;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;'>
                <h3 style='color: #2E4057; margin: 0; font-size: 18px;'>⚗️ Kinetics Analysis - Voltage & Time</h3>
                <div style='color: #666; font-size: 11px; text-align: right;'>
                    {len(equilibrium_voltages)} equilibrium voltages<br>
                    <em>Electrochemical equilibrium backend</em>
                </div>
            </div>
            
            <!-- Primary equilibrium voltage data -->
            <div style='margin-bottom: 12px;'>
                <h4 style='color: #1976D2; margin-bottom: 6px; font-size: 14px;'>Equilibrium Voltages</h4>
                <div style='max-height: 180px; overflow-y: auto;'>
                    <table style='width: 100%; border-collapse: collapse; box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 11px;'>
                        <thead>
                            <tr style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white;'>
                                <th style='padding: 6px; text-align: left; font-weight: 600;'>Parameter</th>
                                <th style='padding: 6px; text-align: right; font-weight: 600;'>Value</th>
                                <th style='padding: 6px; text-align: right; font-weight: 600;'>Unit</th>
                            </tr>
                        </thead>
                        <tbody>
                            {eq_voltage_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 10px;'>
                <div style='max-height: 140px;'>
                    <h4 style='color: #1976D2; margin-bottom: 6px; font-size: 13px;'>Time Constants</h4>
                    <div style='max-height: 120px; overflow-y: auto;'>
                        <table style='width: 100%; border-collapse: collapse; box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 10px;'>
                            <thead>
                                <tr style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white;'>
                                    <th style='padding: 4px; text-align: left; font-weight: 600;'>Param</th>
                                    <th style='padding: 4px; text-align: right; font-weight: 600;'>Value</th>
                                    <th style='padding: 4px; text-align: right; font-weight: 600;'>Unit</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tc_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div style='max-height: 140px;'>
                    <h4 style='color: #1976D2; margin-bottom: 6px; font-size: 13px;'>Diffusion Coefficients</h4>
                    <div style='max-height: 120px; overflow-y: auto;'>
                        <table style='width: 100%; border-collapse: collapse; box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 10px;'>
                            <thead>
                                <tr style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white;'>
                                    <th style='padding: 4px; text-align: left; font-weight: 600;'>Param</th>
                                    <th style='padding: 4px; text-align: right; font-weight: 600;'>Value</th>
                                    <th style='padding: 4px; text-align: right; font-weight: 600;'>Unit</th>
                                </tr>
                            </thead>
                            <tbody>
                                {dc_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            {quality_summary}
        </div>
        """
        
        return pn.pane.HTML(kinetics_html)
    
    def _create_kinetics_fit_summary(self, data: Dict[str, Any]):
        """Create kinetics fit quality summary - Phase 2.3: Equilibrium voltage analysis plots."""
        
        kinetics_data = data.get('kinetics_analysis', {})
        
        # Check if we have any data structure to work with
        if not kinetics_data:
            return self._create_empty_plot("No kinetics analysis data available")
        
        # Handle case where we have measurements but no valid kinetics values
        valid_measurements = kinetics_data.get('valid_measurements', 0)
        total_measurements = kinetics_data.get('total_measurements', 0)
        
        if total_measurements == 0:
            return self._create_empty_plot("No kinetics measurements found in backend data")
        
        if valid_measurements == 0:
            return self._create_empty_plot("No valid equilibrium measurements available for fit analysis")
        
        # Extract kinetics data
        equilibrium_voltages = kinetics_data.get('equilibrium_voltages', [])
        calculation_quality = kinetics_data.get('calculation_quality', [])
        time_constants = kinetics_data.get('time_constants', [])
        diffusion_coeffs = kinetics_data.get('diffusion_coefficients', [])
        
        if not equilibrium_voltages:
            return self._create_empty_plot("No equilibrium voltage data available for fit summary")
        
        # Summary statistics
        avg_voltage = sum(equilibrium_voltages) / len(equilibrium_voltages)
        voltage_std = (sum((v - avg_voltage)**2 for v in equilibrium_voltages) / len(equilibrium_voltages))**0.5 if len(equilibrium_voltages) > 1 else 0.0
        
        # Quality statistics
        quality_stats = {}
        for quality in calculation_quality:
            quality_stats[quality] = quality_stats.get(quality, 0) + 1
        
        valid_count = quality_stats.get('valid', 0)
        invalid_count = quality_stats.get('invalid', 0)
        quality_percentage = (valid_count / len(calculation_quality) * 100) if calculation_quality else 0
        
        fit_html = f"""
        <div style='padding: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <h3 style='color: #2E4057; margin: 0;'>🎯 Kinetics Fit - Equilibrium Analysis</h3>
                <div style='color: #666; font-size: 12px;'>
                    {len(equilibrium_voltages)} equilibrium points<br>
                    <em>Quality: {quality_percentage:.0f}% valid</em>
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
                        <div style='font-size: 16px; font-weight: 600; color: #2E4057;'>{valid_count}/{total_measurements}</div>
                        <div style='color: #666; font-size: 14px;'>Valid measurements</div>
                    </div>
                    <div>
                        <div style='font-size: 16px; font-weight: 600; color: #2E4057;'>{len(time_constants + diffusion_coeffs)}</div>
                        <div style='color: #666; font-size: 14px;'>Kinetic parameters</div>
                    </div>
                </div>
                
                <div style='padding: 20px; background: #E8F5E8; border-radius: 8px;'>
                    <h4 style='color: #4CAF50; margin-top: 0;'>Data Quality</h4>
                    <div style='text-align: center;'>
                        <div style='font-size: 36px; color: #4CAF50; margin: 10px 0;'>
                            {"✓" if quality_percentage > 80 else "⚠" if quality_percentage > 60 else "✗"}
                        </div>
                        <div style='font-weight: 600; color: #2E4057;'>
                            {"Excellent" if quality_percentage > 80 else "Good" if quality_percentage > 60 else "Poor"} Quality
                        </div>
                        <div style='color: #666; font-size: 12px; margin-top: 5px;'>
                            {quality_percentage:.0f}% valid calculations
                        </div>
                    </div>
                </div>
            </div>
            
            <div style='margin-top: 20px; padding: 12px; background: #E3F2FD; border-radius: 6px; border-left: 4px solid #1976D2;'>
                <strong style='color: #1976D2;'>Kinetics Analysis Notes:</strong><br>
                <div style='color: #666; font-size: 14px; margin-top: 5px;'>
                    Equilibrium voltages extracted from electrochemical equilibrium analysis<br>
                    High quality indicates stable measurements suitable for kinetics modeling<br>
                    Voltage variation: {(voltage_std/avg_voltage*100 if avg_voltage > 0 else 0):.2f}% coefficient of variation
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
        elif analysis_type == "resistance_analysis":
            plot_options = [
                ("Resistance vs Time", "resistance_time"),
                ("Resistance Distribution", "resistance_distribution"),
                ("IR Analysis Summary", "resistance_summary")
            ]
        elif analysis_type == "kinetics_analysis":
            plot_options = [
                ("Voltage vs Time", "voltage_time"),
                ("Kinetics Fit", "kinetics_fit"), 
                ("Fit Quality", "fit_quality")
            ]
        elif analysis_type == "dqdv_analysis":
            plot_options = [
                ("dQ/dV vs Voltage", "dqdv_voltage"),
                ("Peak Analysis", "peak_analysis"),
                ("Overlay Comparison", "overlay_comparison")
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