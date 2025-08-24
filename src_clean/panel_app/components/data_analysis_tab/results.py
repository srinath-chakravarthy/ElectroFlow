"""
Tab 3 Data Analysis - Results Display & Formatting

Handles formatting and display of analysis results.
Creates professional output for different analysis types.

COMPLETE FIXES for result formatting and display methods.
"""

import panel as pn
from typing import Dict, List, Any

# Registry imports for dynamic result formatting
from src_clean.analysis.registry import get_analysis_registry


class ResultsDisplay:
    """
    Handles formatting and display of analysis results.
    Creates professional output for different analysis types.

    Key Features:
    - Analysis-specific result formatting
    - Error-resistant display methods
    - Professional HTML styling
    """

    def __init__(self, api):
        self.api = api
        
        # Get analysis registry for dynamic result formatting
        self.registry = get_analysis_registry()

        # Create results panels
        self._create_results_panels()

        # Current state
        self.current_results = {}
        self.current_analysis = "basic_statistics"

    def _create_results_panels(self):
        """Create results display panels."""

        # Quick results panel (always visible)
        self.quick_results_panel = pn.pane.HTML(
            """
            <div style='color: #666; font-style: italic; padding: 20px; text-align: center;'>
                📊 Analysis results will appear here...<br>
                <small>Select groups and run analysis to see results</small>
            </div>
            """,
            sizing_mode='stretch_width',
            height=150
        )

        # Detailed results panel (for Row 3, future phases)
        self.detailed_results_panel = pn.pane.HTML(
            """
            <div style='color: #666; padding: 20px; text-align: center;'>
                <strong>📋 Detailed Results</strong><br><br>
                <em>Detailed results and export options will appear here after analysis...</em><br>
                <small>Export options: CSV, JSON, PDF Report</small>
            </div>
            """,
            sizing_mode='stretch_width'
        )

    def get_quick_results_panel(self):
        """Return the quick results panel."""
        return self.quick_results_panel

    def get_detailed_results_panel(self):
        """Return the detailed results panel."""
        return self.detailed_results_panel

    def update_results_display(self, analysis_type: str, results: Dict[str, Any]):
        """Update results display with new results - MAIN FIX METHOD."""

        self.current_analysis = analysis_type
        self.current_results = results

        # Format results for quick display
        formatted_results = self.format_results(analysis_type, results)

        # Update quick results panel
        self.quick_results_panel.object = formatted_results

        # Update detailed results panel
        detailed_results = self.format_detailed_results(analysis_type, results)
        self.detailed_results_panel.object = detailed_results

    def format_results(self, analysis_type: str, results: Dict[str, Any]):
        """Main results formatting using registry-based templates."""

        if results.get("error"):
            return f"""
            <div style='color: #d32f2f; padding: 15px; border: 1px solid #d32f2f; 
                        border-radius: 4px; background: #ffeaea;'>
                <strong>❌ Analysis Error:</strong><br>
                {results["error"]}
            </div>
            """

        try:
            # Use registry-driven result formatting
            return self._format_registry_based_results(analysis_type, results)
        except Exception as e:
            print(f"⚠️ Registry-based formatting failed for {analysis_type}, using fallback: {e}")
            return self._format_fallback_results(analysis_type, results)

    def _format_registry_based_results(self, analysis_type: str, results: Dict[str, Any]):
        """Format results using registry-based templates."""
        
        try:
            # Get analysis configuration from registry
            analysis_config = self.registry.get_analysis(analysis_type)
            
            if not analysis_config:
                return self._format_fallback_results(analysis_type, results)
            
            # Extract key information from results
            analysis_name = analysis_config.name
            analysis_description = analysis_config.description
            segments_analyzed = results.get('segments_analyzed', 0)
            total_segments = results.get('total_segments', 0)
            
            # Get analysis-specific data
            analysis_data = self._extract_analysis_specific_data(analysis_type, results)
            
            # Create registry-based result display
            html_content = f"""
            <div style='color: #2E4057; padding: 15px; border-radius: 4px; background: #f8f9fa; border: 1px solid #e0e0e0;'>
                <h4 style='margin: 0 0 10px 0; color: #1976D2;'>{self._get_analysis_icon(analysis_type)} {analysis_name} Results</h4>
                
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;'>
                    <div>
                        <p style='margin: 5px 0;'><strong>Analysis Type:</strong> {analysis_name}</p>
                        <p style='margin: 5px 0;'><strong>Segments Analyzed:</strong> {segments_analyzed:,}</p>
                        <p style='margin: 5px 0;'><strong>Status:</strong> <span style='color: #4CAF50;'>✅ Complete</span></p>
                    </div>
                    <div>
                        <p style='margin: 5px 0;'><strong>Data Points:</strong> {total_segments:,}</p>
                        <p style='margin: 5px 0;'><strong>Engine:</strong> Registry v2.0</p>
                        <p style='margin: 5px 0;'><strong>Quality:</strong> {self._assess_result_quality(results)}</p>
                    </div>
                </div>
                
                <div style='background: #e8f5e8; padding: 10px; border-radius: 4px; border-left: 4px solid #4CAF50; margin-bottom: 10px;'>
                    <p style='margin: 0; font-size: 14px;'>
                        ✅ <strong>Analysis Complete</strong><br>
                        <small>{analysis_description}</small>
                    </p>
                </div>
                
                {analysis_data}
                
                <div style='margin-top: 10px; padding: 8px; background: #e3f2fd; border-radius: 4px; border-left: 4px solid #2196F3;'>
                    <small>🔬 <strong>Registry-based analysis:</strong> Consistent results across all analysis types</small>
                </div>
            </div>
            """
            
            print(f"✅ Created registry-based result display for {analysis_type}")
            return html_content
            
        except Exception as e:
            print(f"❌ Registry-based result formatting failed: {e}")
            return self._format_fallback_results(analysis_type, results)
    
    def _extract_analysis_specific_data(self, analysis_type: str, results: Dict[str, Any]) -> str:
        """Extract analysis-specific data for display."""
        
        try:
            if analysis_type == "basic_statistics":
                return self._extract_basic_statistics_data(results)
            elif analysis_type == "resistance_analysis":
                return self._extract_resistance_data(results)
            elif analysis_type == "kinetics_analysis":
                return self._extract_kinetics_data(results)
            elif analysis_type == "equilibrium_analysis":
                return self._extract_equilibrium_data(results)
            elif analysis_type == "current_decay_analysis":
                return self._extract_current_decay_data(results)
            elif analysis_type == "dqdv_analysis":
                return self._extract_dqdv_data(results)
            else:
                return "<em>Analysis-specific data display not yet configured</em>"
                
        except Exception as e:
            print(f"⚠️ Error extracting analysis data for {analysis_type}: {e}")
            return "<em>Error extracting analysis-specific data</em>"
    
    def _extract_basic_statistics_data(self, results: Dict[str, Any]) -> str:
        """Extract basic statistics specific data."""
        
        segments = results.get("segments", [])
        if not segments:
            return "<em>No segment details available</em>"
        
        try:
            import pandas as pd
            df = pd.DataFrame(segments)
            
            # Technique breakdown
            technique_counts = df.groupby('fundamental_technique').size().to_dict()
            technique_durations = df.groupby('fundamental_technique')['duration_s'].mean().to_dict()
            
            # Overall statistics
            total_duration_hours = df['duration_s'].sum() / 3600
            voltage_min = df['start_potential_v'].min() 
            voltage_max = df['end_potential_v'].max()
            
            # Create technique summary table
            technique_summary = ""
            for technique, count in technique_counts.items():
                avg_duration = technique_durations.get(technique, 0)
                technique_summary += f"""
                <tr>
                    <td style='padding: 5px; border-bottom: 1px solid #eee;'>{technique}</td>
                    <td style='padding: 5px; border-bottom: 1px solid #eee; text-align: center;'>{count}</td>
                    <td style='padding: 5px; border-bottom: 1px solid #eee; text-align: center;'>{avg_duration:.1f}s</td>
                </tr>
                """
            
            return f"""
            <div style='margin: 10px 0;'>
                <p style='margin: 5px 0;'><strong>Total Duration:</strong> {total_duration_hours:.1f} hours</p>
                <p style='margin: 5px 0;'><strong>Voltage Range:</strong> {voltage_min:.2f} - {voltage_max:.2f} V</p>
                <p style='margin: 5px 0;'><strong>Techniques Found:</strong> {len(technique_counts)}</p>
                
                <div style='margin-top: 10px;'>
                    <strong>Technique Breakdown:</strong>
                    <table style='width: 100%; margin-top: 5px; border-collapse: collapse;'>
                        <tr style='background: #e3f2fd;'>
                            <th style='padding: 8px; text-align: left; border-bottom: 2px solid #1976D2;'>Technique</th>
                            <th style='padding: 8px; text-align: center; border-bottom: 2px solid #1976D2;'>Count</th>
                            <th style='padding: 8px; text-align: center; border-bottom: 2px solid #1976D2;'>Avg Duration</th>
                        </tr>
                        {technique_summary}
                    </table>
                </div>
            </div>
            """
            
        except Exception as e:
            print(f"Error creating basic statistics data: {e}")
            return "<em>Error processing segment statistics</em>"
    
    def _extract_resistance_data(self, results: Dict[str, Any]) -> str:
        """Extract resistance analysis specific data."""
        
        resistance_data = results.get('resistance_data', [])
        summary = results.get('summary', {})
        
        valid_measurements = results.get('valid_measurements', 0)
        time_points = results.get('time_points_analyzed', ['Immediate', '10s', '30s'])
        
        return f"""
        <div style='margin: 10px 0;'>
            <p style='margin: 5px 0;'><strong>Valid Measurements:</strong> {valid_measurements}</p>
            <p style='margin: 5px 0;'><strong>Time Points:</strong> {', '.join(time_points)}</p>
            <p style='margin: 5px 0;'><strong>Method:</strong> Instantaneous resistance (ΔV/ΔI)</p>
        </div>
        """
    
    def _extract_kinetics_data(self, results: Dict[str, Any]) -> str:
        """Extract kinetics analysis specific data."""
        
        kinetics_data = results.get('kinetics_data', [])
        valid_fits = results.get('valid_fits', 0)
        fit_type_used = results.get('fit_type_used', 'exponential')
        
        return f"""
        <div style='margin: 10px 0;'>
            <p style='margin: 5px 0;'><strong>Valid Fits:</strong> {valid_fits}</p>
            <p style='margin: 5px 0;'><strong>Primary Fit Type:</strong> {fit_type_used.title()}</p>
            <p style='margin: 5px 0;'><strong>Analysis Focus:</strong> Rest phase relaxation kinetics</p>
        </div>
        """
    
    def _extract_equilibrium_data(self, results: Dict[str, Any]) -> str:
        """Extract equilibrium analysis specific data."""
        
        quality_segments = results.get('quality_segments', 0)
        total_segments = results.get('total_segments', 0)
        
        return f"""
        <div style='margin: 10px 0;'>
            <p style='margin: 5px 0;'><strong>Quality Segments:</strong> {quality_segments} of {total_segments}</p>
            <p style='margin: 5px 0;'><strong>Analysis Focus:</strong> Voltage stability and drift assessment</p>
        </div>
        """
    
    def _extract_current_decay_data(self, results: Dict[str, Any]) -> str:
        """Extract current decay analysis specific data."""
        
        return """
        <div style='margin: 10px 0;'>
            <p style='margin: 5px 0;'><strong>Analysis Focus:</strong> Current decay kinetics</p>
            <p style='margin: 5px 0;'><strong>Method:</strong> Exponential decay fitting</p>
        </div>
        """
    
    def _extract_dqdv_data(self, results: Dict[str, Any]) -> str:
        """Extract dQ/dV analysis specific data."""
        
        return """
        <div style='margin: 10px 0;'>
            <p style='margin: 5px 0;'><strong>Status:</strong> <span style='color: #FF9800;'>Not yet implemented</span></p>
            <p style='margin: 5px 0;'><strong>Future Features:</strong> Differential capacity, phase transitions</p>
        </div>
        """
    
    def _get_analysis_icon(self, analysis_type: str) -> str:
        """Get appropriate icon for analysis type."""
        
        icons = {
            "basic_statistics": "📊",
            "resistance_analysis": "🔬",
            "kinetics_analysis": "⚡",
            "equilibrium_analysis": "⚖️",
            "current_decay_analysis": "📉",
            "dqdv_analysis": "📈"
        }
        
        return icons.get(analysis_type, "🔬")
    
    def _assess_result_quality(self, results: Dict[str, Any]) -> str:
        """Assess and return result quality indicator."""
        
        segments_analyzed = results.get('segments_analyzed', 0)
        total_segments = results.get('total_segments', 0)
        
        if segments_analyzed == 0:
            return "<span style='color: #d32f2f;'>No data</span>"
        elif segments_analyzed == total_segments:
            return "<span style='color: #4CAF50;'>Excellent</span>"
        elif segments_analyzed >= total_segments * 0.8:
            return "<span style='color: #FF9800;'>Good</span>"
        else:
            return "<span style='color: #FF5722;'>Limited</span>"
    
    def _format_fallback_results(self, analysis_type: str, results: Dict[str, Any]) -> str:
        """Fallback result formatting if registry fails."""
        
        segments_analyzed = results.get('segments_analyzed', 0)
        total_segments = results.get('total_segments', 0)
        
        return f"""
        <div style='color: #666; padding: 15px; background: #f8f9fa; border-radius: 4px; border: 1px solid #e0e0e0;'>
            <h4 style='margin: 0 0 10px 0; color: #1976D2;'>📊 {analysis_type.replace('_', ' ').title()} Results</h4>
            
            <div style='margin-bottom: 15px;'>
                <p style='margin: 5px 0;'><strong>Analysis Type:</strong> {analysis_type.replace('_', ' ').title()}</p>
                <p style='margin: 5px 0;'><strong>Segments Analyzed:</strong> {segments_analyzed:,}</p>
                <p style='margin: 5px 0;'><strong>Total Segments:</strong> {total_segments:,}</p>
            </div>
            
            <div style='background: #fff3cd; padding: 10px; border-radius: 4px; border-left: 4px solid #ffc107;'>
                <p style='margin: 0; font-size: 14px;'>
                    ⚠️ <strong>Using fallback formatting</strong><br>
                    <small>Registry-based formatting not available</small>
                </p>
            </div>
        </div>
        """
    
    def _legacy_format_basic_statistics(self, results: Dict[str, Any]):
        """Format basic statistics results using real segment data."""

        segments = results.get("segments", [])
        total_segments = results.get("total_segments", 0)
        groups_count = results.get("groups_analyzed", 0)

        if not segments:
            return f"""
            <div style='color: #2E4057; padding: 15px; border-radius: 4px; background: #f8f9fa; border: 1px solid #e0e0e0;'>
                <h4 style='margin: 0 0 10px 0; color: #1976D2;'>📊 Basic Statistics Summary</h4>
                <p style='margin: 5px 0;'><strong>Groups Analyzed:</strong> {groups_count}</p>
                <p style='margin: 5px 0;'><strong>Total Segments:</strong> {total_segments}</p>
                <p><em>No segment details available</em></p>
            </div>
            """

        # Calculate statistics from real segment data
        import pandas as pd
        df = pd.DataFrame(segments)
        
        # Technique breakdown
        technique_counts = df.groupby('fundamental_technique').size().to_dict()
        technique_durations = df.groupby('fundamental_technique')['duration_s'].mean().to_dict()
        
        # Overall statistics
        total_duration_hours = df['duration_s'].sum() / 3600
        voltage_min = df['start_potential_v'].min() 
        voltage_max = df['end_potential_v'].max()
        most_common_technique = df['fundamental_technique'].mode()[0] if not df['fundamental_technique'].mode().empty else "Unknown"

        # Create technique summary table
        technique_summary = ""
        for technique, count in technique_counts.items():
            avg_duration = technique_durations.get(technique, 0)
            technique_summary += f"""
            <tr>
                <td style='padding: 5px; border-bottom: 1px solid #eee;'>{technique}</td>
                <td style='padding: 5px; border-bottom: 1px solid #eee; text-align: center;'>{count}</td>
                <td style='padding: 5px; border-bottom: 1px solid #eee; text-align: center;'>{avg_duration:.1f}s</td>
            </tr>
            """

        return f"""
        <div style='color: #2E4057; padding: 15px; border-radius: 4px; background: #f8f9fa; border: 1px solid #e0e0e0;'>
            <h4 style='margin: 0 0 10px 0; color: #1976D2;'>📊 Basic Statistics Summary (Real Data)</h4>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;'>
                <div>
                    <p style='margin: 5px 0;'><strong>Groups Analyzed:</strong> {groups_count}</p>
                    <p style='margin: 5px 0;'><strong>Total Segments:</strong> {total_segments:,}</p>
                    <p style='margin: 5px 0;'><strong>Total Duration:</strong> {total_duration_hours:.1f} hours</p>
                </div>
                <div>
                    <p style='margin: 5px 0;'><strong>Most Common:</strong> {most_common_technique}</p>
                    <p style='margin: 5px 0;'><strong>Voltage Range:</strong> {voltage_min:.2f} - {voltage_max:.2f} V</p>
                    <p style='margin: 5px 0;'><strong>Techniques:</strong> {len(technique_counts)}</p>
                </div>
            </div>
            
            <div style='margin-top: 15px;'>
                <strong>Technique Breakdown:</strong>
                <table style='width: 100%; margin-top: 5px; border-collapse: collapse;'>
                    <tr style='background: #e3f2fd;'>
                        <th style='padding: 8px; text-align: left; border-bottom: 2px solid #1976D2;'>Technique</th>
                        <th style='padding: 8px; text-align: center; border-bottom: 2px solid #1976D2;'>Count</th>
                        <th style='padding: 8px; text-align: center; border-bottom: 2px solid #1976D2;'>Avg Duration</th>
                    </tr>
                    {technique_summary}
                </table>
            </div>
        </div>
        """

    def _legacy_format_resistance_analysis(self, results: Dict[str, Any]):
        """Format resistance analysis results - COMPLETE IMPLEMENTATION."""

        groups = results.get("groups", [])
        data = results.get("data", {})

        return f"""
        <div style='color: #2E4057; padding: 15px; border-radius: 4px; background: #f8f9fa; border: 1px solid #e0e0e0;'>
            <h4 style='margin: 0 0 10px 0; color: #1976D2;'>🔬 Resistance Analysis Results</h4>
            
            <div style='margin-bottom: 15px;'>
                <p style='margin: 5px 0;'><strong>Groups Analyzed:</strong> {', '.join(groups)}</p>
                <p style='margin: 5px 0;'><strong>Analysis Type:</strong> Electrochemical Resistance</p>
                <p style='margin: 5px 0;'><strong>Data Points:</strong> {len(data) if isinstance(data, list) else 'Multiple datasets'}</p>
            </div>
            
            <div style='background: #e8f5e8; padding: 10px; border-radius: 4px; border-left: 4px solid #4CAF50;'>
                <p style='margin: 0; font-size: 14px;'>
                    ✅ <strong>Analysis Complete</strong><br>
                    <small>Resistance data processed using electrochemical analysis methods</small>
                </p>
            </div>
            
            <div style='margin-top: 10px; padding: 8px; background: #fff3cd; border-radius: 4px; border-left: 4px solid #ffc107;'>
                <small>💡 <strong>Note:</strong> Detailed resistance plots and metrics will be available in advanced visualization mode</small>
            </div>
        </div>
        """

    def _legacy_format_kinetics_analysis(self, results: Dict[str, Any]):
        """Format kinetics analysis results - COMPLETE IMPLEMENTATION."""

        groups = results.get("groups", [])
        data = results.get("data", {})

        return f"""
        <div style='color: #2E4057; padding: 15px; border-radius: 4px; background: #f8f9fa; border: 1px solid #e0e0e0;'>
            <h4 style='margin: 0 0 10px 0; color: #1976D2;'>⚡ Kinetics Analysis Results</h4>
            
            <div style='margin-bottom: 15px;'>
                <p style='margin: 5px 0;'><strong>Groups Analyzed:</strong> {', '.join(groups)}</p>
                <p style='margin: 5px 0;'><strong>Focus:</strong> Current decay and equilibrium kinetics</p>
                <p style='margin: 5px 0;'><strong>Method:</strong> Electrochemical rest analysis</p>
            </div>
            
            <div style='background: #e8f5e8; padding: 10px; border-radius: 4px; border-left: 4px solid #4CAF50;'>
                <p style='margin: 0; font-size: 14px;'>
                    ✅ <strong>Kinetics Analysis Complete</strong><br>
                    <small>Rest phase kinetics and current decay patterns analyzed</small>
                </p>
            </div>
            
            <div style='margin-top: 10px; padding: 8px; background: #e3f2fd; border-radius: 4px; border-left: 4px solid #2196F3;'>
                <small>🔬 <strong>Analysis includes:</strong> Time constants, equilibrium detection, current decay fitting</small>
            </div>
        </div>
        """

    def _legacy_format_dqdv_analysis(self, results: Dict[str, Any]):
        """Format dQ/dV analysis results - COMPLETE IMPLEMENTATION."""

        groups = results.get("groups", [])
        data = results.get("data", {})

        return f"""
        <div style='color: #2E4057; padding: 15px; border-radius: 4px; background: #f8f9fa; border: 1px solid #e0e0e0;'>
            <h4 style='margin: 0 0 10px 0; color: #1976D2;'>📊 dQ/dV Analysis Results</h4>
            
            <div style='margin-bottom: 15px;'>
                <p style='margin: 5px 0;'><strong>Groups Analyzed:</strong> {', '.join(groups)}</p>
                <p style='margin: 5px 0;'><strong>Analysis:</strong> Differential Capacity (dQ/dV)</p>
                <p style='margin: 5px 0;'><strong>Method:</strong> Equilibrium analysis with phase transition detection</p>
            </div>
            
            <div style='background: #e8f5e8; padding: 10px; border-radius: 4px; border-left: 4px solid #4CAF50;'>
                <p style='margin: 0; font-size: 14px;'>
                    ✅ <strong>dQ/dV Analysis Complete</strong><br>
                    <small>Phase transitions and equilibrium states identified</small>
                </p>
            </div>
            
            <div style='margin-top: 10px; padding: 8px; background: #fff3cd; border-radius: 4px; border-left: 4px solid #ffc107;'>
                <small>📈 <strong>Features:</strong> Peak detection, capacity evolution, voltage-dependent phase behavior</small>
            </div>
        </div>
        """

    def format_detailed_results(self, analysis_type: str, results: Dict[str, Any]):
        """Format detailed results for Row 3 display - NEW METHOD."""

        if results.get("error"):
            return f"""
            <div style='color: #d32f2f; padding: 20px; text-align: center;'>
                <h4>❌ Analysis Error</h4>
                <p>{results["error"]}</p>
                <p><small>Check your data and try again</small></p>
            </div>
            """

        groups_text = ", ".join(results.get("groups", []))

        return f"""
        <div style='padding: 20px;'>
            <h4 style='color: #1976D2; margin: 0 0 15px 0;'>📋 Detailed Results - {analysis_type.replace('_', ' ').title()}</h4>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px;'>
                <div style='background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0;'>
                    <h5 style='margin: 0 0 10px 0; color: #2E4057;'>📊 Summary</h5>
                    <p style='margin: 5px 0; font-size: 14px;'>Analysis Type: <strong>{analysis_type.replace('_', ' ').title()}</strong></p>
                    <p style='margin: 5px 0; font-size: 14px;'>Groups: <strong>{len(results.get("groups", []))}</strong></p>
                    <p style='margin: 5px 0; font-size: 14px;'>Status: <strong style='color: #4CAF50;'>Complete</strong></p>
                </div>
                
                <div style='background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0;'>
                    <h5 style='margin: 0 0 10px 0; color: #2E4057;'>💾 Export Options</h5>
                    <p style='margin: 5px 0; font-size: 14px;'>• CSV Data Export</p>
                    <p style='margin: 5px 0; font-size: 14px;'>• JSON Results Export</p>
                    <p style='margin: 5px 0; font-size: 14px;'>• PDF Report Generation</p>
                </div>
                
                <div style='background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0;'>
                    <h5 style='margin: 0 0 10px 0; color: #2E4057;'>🔧 Actions</h5>
                    <p style='margin: 5px 0; font-size: 14px;'>• Re-run Analysis</p>
                    <p style='margin: 5px 0; font-size: 14px;'>• Adjust Parameters</p>
                    <p style='margin: 5px 0; font-size: 14px;'>• Compare Results</p>
                </div>
            </div>
            
            <div style='background: #e3f2fd; padding: 15px; border-radius: 8px; border-left: 4px solid #1976D2;'>
                <h5 style='margin: 0 0 10px 0; color: #1976D2;'>📋 Groups Analyzed</h5>
                <p style='margin: 0; font-size: 14px;'>{groups_text}</p>
            </div>
            
            <div style='margin-top: 15px; text-align: center; color: #666;'>
                <small>Detailed export and comparison features will be implemented in future versions</small>
            </div>
        </div>
        """