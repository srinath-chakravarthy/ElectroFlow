"""
Tab 3 Data Analysis - Results Display & Formatting

Handles formatting and display of analysis results.
Creates professional output for different analysis types.

Architecture: Results formatting dispatcher with analysis-specific methods.
"""

import panel as pn
from typing import Dict, List, Any


class ResultsDisplay:
    """
    Handles formatting and display of analysis results.
    Creates professional output for different analysis types.
    
    Phase 1: Basic results placeholders
    Phase 2: Simple results display with backend data
    Phase 3: Analysis-specific results formatting
    Phase 4: Advanced export and detailed results
    """
    
    def __init__(self, api):
        self.api = api
        
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
            width=450,
            height=150
        )
        
        # Detailed results panel (for Row 3, future phases)
        self.detailed_results_panel = pn.pane.HTML(
            """
            <div style='color: #666; padding: 20px;'>
                <em>Detailed results and export options will be available in future phases...</em>
            </div>
            """,
            width=800
        )
    
    def get_quick_results_panel(self):
        """Return the quick results panel."""
        return self.quick_results_panel
    
    def get_detailed_results_panel(self):
        """Return the detailed results panel."""
        return self.detailed_results_panel
    
    # ===== RESULTS FORMATTING =====
    
    def format_results(self, analysis_type: str, results: Dict[str, Any]):
        """Main results formatting dispatcher."""
        
        try:
            if analysis_type == "basic_statistics":
                return self._format_basic_statistics_results(results)
            elif analysis_type == "resistance_analysis":
                return self._format_resistance_results(results)
            elif analysis_type == "dqdv_analysis":
                return self._format_dqdv_results(results)
            elif analysis_type == "kinetics_analysis":
                return self._format_kinetics_results(results)
            else:
                return self._format_generic_results(results)
                
        except Exception as e:
            return self._format_error_results(f"Error formatting results: {str(e)}")
    
    def _format_basic_statistics_results(self, results: Dict[str, Any]):
        """Format basic statistics results with real backend data."""
        
        # Check if we have real backend data
        has_real_data = 'backend_results' in results or any(key.endswith('_mean') for key in results.keys())
        data_source = "Real electrochemical analysis" if has_real_data else "Simulated data"
        
        # Use real data or fallback to placeholder
        if not results:
            results = {
                'total_segments': 45,
                'total_groups': 3,
                'duration_mean': 125.4,
                'duration_std': 23.1,
                'voltage_mean': 3.85,
                'voltage_std': 0.12,
                'capacity_mean': 0.045,
                'capacity_std': 0.008
            }
        
        html_content = f"""
        <div style='background: #F8F9FA; padding: 15px; border-radius: 6px; border: 1px solid #E0E0E0;'>
            <div style='color: #2E4057; font-weight: 600; font-size: 16px; margin-bottom: 12px;'>
                🔬 Basic Statistics Results
            </div>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;'>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Total Segments:</strong> {results.get('total_segments', 'N/A')}
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Total Groups:</strong> {results.get('total_groups', 'N/A')}
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Duration:</strong> {results.get('duration_mean', 0):.1f} ± {results.get('duration_std', 0):.1f} s
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Voltage:</strong> {results.get('voltage_mean', 0):.3f} ± {results.get('voltage_std', 0):.3f} V
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Capacity:</strong> {results.get('capacity_mean', 0):.4f} ± {results.get('capacity_std', 0):.4f} Ah
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Energy:</strong> {results.get('energy_mean', 0):.4f} ± {results.get('energy_std', 0):.4f} Wh
                </div>
            </div>
            
            <div style='color: #666; font-size: 12px; margin-top: 8px;'>
                <em>{data_source} • {results.get('analysis_timestamp', 'Current session')}</em>
            </div>
        </div>
        """
        
        return html_content
    
    def _format_resistance_results(self, results: Dict[str, Any]):
        """Format resistance analysis results with IR resistance data."""
        
        resistance_analysis = results.get('resistance_analysis', {})
        
        if not resistance_analysis:
            html_content = """
            <div style='background: #FFF3E0; padding: 15px; border-radius: 6px; border: 1px solid #F57C00;'>
                <div style='color: #F57C00; font-weight: 600; font-size: 16px; margin-bottom: 10px;'>
                    ⚡ Resistance Analysis Results
                </div>
                <div style='color: #666; font-style: italic;'>
                    No resistance analysis data available
                </div>
            </div>
            """
            return html_content
        
        # Extract resistance summary data
        total_measurements = resistance_analysis.get('total_measurements', 0)
        valid_measurements = resistance_analysis.get('valid_measurements', 0)
        average_resistance = resistance_analysis.get('average_resistance_ohm', 0.0)
        resistance_std = resistance_analysis.get('resistance_std_ohm', 0.0)
        measurement_types = list(resistance_analysis.get('measurement_types', []))
        
        # Determine data quality
        quality_score = (valid_measurements / total_measurements) * 100 if total_measurements > 0 else 0
        quality_indicator = (
            "🟢 Excellent" if quality_score >= 90 else
            "🟡 Good" if quality_score >= 70 else
            "🔴 Poor" if quality_score >= 50 else
            "❌ Failed"
        )
        
        html_content = f"""
        <div style='background: #FFF3E0; padding: 15px; border-radius: 6px; border: 1px solid #F57C00;'>
            <div style='color: #F57C00; font-weight: 600; font-size: 16px; margin-bottom: 12px;'>
                ⚡ Resistance Analysis Results
            </div>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;'>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Measurements:</strong> {valid_measurements} of {total_measurements}
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Data Quality:</strong> {quality_indicator} ({quality_score:.0f}%)
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Avg Resistance:</strong> {average_resistance:.4f} Ω
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Std Deviation:</strong> ±{resistance_std:.4f} Ω
                </div>
            </div>
            
            <div style='color: #666; font-size: 12px; margin-top: 8px;'>
                <em>IR resistance analysis • Types measured: {', '.join(measurement_types)}</em>
            </div>
        </div>
        """
        
        return html_content
    
    def _format_dqdv_results(self, results: Dict[str, Any]):
        """Format dQ/dV analysis results with real electrochemical insights data."""
        
        insights = results.get('electrochemical_insights', {})
        rest_analysis = insights.get('rest_analysis', {})
        
        if not rest_analysis:
            html_content = """
            <div style='background: #E3F2FD; padding: 15px; border-radius: 6px; border: 1px solid #1976D2;'>
                <div style='color: #1976D2; font-weight: 600; font-size: 16px; margin-bottom: 10px;'>
                    📈 dQ/dV Analysis Results
                </div>
                <div style='color: #666; font-style: italic;'>
                    No electrochemical insights data available for dQ/dV analysis
                </div>
            </div>
            """
            return html_content
        
        # Analyze rest segments for voltage relaxation
        total_rest_segments = len(rest_analysis)
        analyzed_segments = 0
        total_time_constant = 0
        total_voltage_drop = 0
        avg_r_squared = 0
        
        for segment_data in rest_analysis.values():
            if segment_data and 'voltage_relaxation' in segment_data:
                analyzed_segments += 1
                relaxation = segment_data['voltage_relaxation']
                total_time_constant += relaxation.get('time_constant_s', 0.0)
                total_voltage_drop += relaxation.get('voltage_drop_mv', 0.0)
                avg_r_squared += relaxation.get('r_squared', 0.0)
        
        if analyzed_segments > 0:
            avg_time_constant = total_time_constant / analyzed_segments
            avg_voltage_drop = total_voltage_drop / analyzed_segments
            avg_r_squared = avg_r_squared / analyzed_segments
        else:
            avg_time_constant = avg_voltage_drop = avg_r_squared = 0
        
        quality_indicator = "🟢 Excellent" if avg_r_squared > 0.9 else "🟡 Good" if avg_r_squared > 0.7 else "🔴 Poor"
        
        html_content = f"""
        <div style='background: #E3F2FD; padding: 15px; border-radius: 6px; border: 1px solid #1976D2;'>
            <div style='color: #1976D2; font-weight: 600; font-size: 16px; margin-bottom: 12px;'>
                📈 dQ/dV Analysis Results
            </div>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;'>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Rest Segments:</strong> {analyzed_segments} of {total_rest_segments}
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Fit Quality:</strong> {quality_indicator} (R²={avg_r_squared:.3f})
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Avg Time Constant:</strong> {avg_time_constant:.1f} s
                </div>
                <div style='background: white; padding: 8px; border-radius: 4px; border: 1px solid #E8E8E8;'>
                    <strong>Avg Voltage Drop:</strong> {avg_voltage_drop:.1f} mV
                </div>
            </div>
            
            <div style='color: #666; font-size: 12px; margin-top: 8px;'>
                <em>Electrochemical insights backend • Voltage relaxation analysis complete</em>
            </div>
        </div>
        """
        
        return html_content
    
    def _format_kinetics_results(self, results: Dict[str, Any]):
        """Format kinetics analysis results with comprehensive electrochemical data."""
        
        kinetics_data = results.get('kinetics_analysis', {})
        
        if not kinetics_data:
            html_content = """
            <div style='background: #E8F5E8; padding: 15px; border-radius: 6px; border: 1px solid #2E7D32;'>
                <div style='color: #2E7D32; font-weight: 600; font-size: 16px; margin-bottom: 10px;'>
                    ⚡ Kinetics Analysis Results
                </div>
                <div style='color: #666; font-style: italic;'>
                    No kinetics analysis data available
                </div>
            </div>
            """
            return html_content
        
        # Extract analysis components (using correct field names from main_tab.py)
        time_constants = kinetics_data.get('time_constants', [])
        diffusion_coeffs = kinetics_data.get('diffusion_coefficients', [])
        equilibrium_voltages = kinetics_data.get('equilibrium_voltages', [])
        
        # Calculate summary statistics
        num_time_constants = len(time_constants)
        num_diffusion_coeffs = len(diffusion_coeffs)
        num_equilibrium_points = len(equilibrium_voltages)
        
        # Calculate average values
        avg_time_constant = sum(time_constants) / len(time_constants) if time_constants else 0.0
        avg_diffusion_coeff = sum(diffusion_coeffs) / len(diffusion_coeffs) if diffusion_coeffs else 0.0
        avg_equilibrium_voltage = sum(equilibrium_voltages) / len(equilibrium_voltages) if equilibrium_voltages else 0.0
        
        # Get average resistance from results (if available)
        resistance_analysis = results.get('resistance_analysis', {})
        avg_resistance = resistance_analysis.get('average_resistance_ohm', 0.0)
        
        # Determine analysis completeness
        completeness_score = 0
        if num_time_constants > 0: completeness_score += 25
        if num_diffusion_coeffs > 0: completeness_score += 25
        if avg_resistance > 0: completeness_score += 25
        if num_equilibrium_points > 0: completeness_score += 25
        
        completeness_indicator = (
            "🟢 Complete" if completeness_score == 100 else
            "🟡 Partial" if completeness_score >= 50 else
            "🔴 Limited"
        )
        
        html_content = f"""
        <div style='background: #E8F5E8; padding: 10px; border-radius: 4px; border: 1px solid #2E7D32;'>
            <div style='color: #2E7D32; font-weight: 600; font-size: 14px; margin-bottom: 8px;'>
                ⚡ Kinetics Analysis Summary
            </div>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px;'>
                <div style='background: white; padding: 5px; border-radius: 3px; border: 1px solid #E8E8E8; font-size: 11px;'>
                    <strong>Equilibrium V:</strong> {avg_equilibrium_voltage:.4f} V ({len(equilibrium_voltages)} points)
                </div>
                <div style='background: white; padding: 5px; border-radius: 3px; border: 1px solid #E8E8E8; font-size: 11px;'>
                    <strong>Status:</strong> {completeness_indicator} ({completeness_score}%)
                </div>
            </div>
            
            <div style='color: #666; font-size: 10px; text-align: center;'>
                <em>📊 Detailed kinetics analysis available in plot area below</em>
            </div>
        </div>
        """
        
        return html_content
    
    def _format_generic_results(self, results: Dict[str, Any]):
        """Format generic results."""
        
        html_content = f"""
        <div style='background: #FFF3E0; padding: 15px; border-radius: 6px; border: 1px solid #F57C00;'>
            <div style='color: #F57C00; font-weight: 600; font-size: 16px; margin-bottom: 10px;'>
                📊 Analysis Results
            </div>
            <div style='color: #666;'>
                Results available: {len(results) if results else 0} items
            </div>
        </div>
        """
        
        return html_content
    
    def _format_error_results(self, error_message: str):
        """Format error results."""
        
        html_content = f"""
        <div style='background: #FFEBEE; padding: 15px; border-radius: 6px; border: 1px solid #D32F2F;'>
            <div style='color: #D32F2F; font-weight: 600; font-size: 16px; margin-bottom: 10px;'>
                ❌ Analysis Error
            </div>
            <div style='color: #666; font-size: 14px;'>
                {error_message}
            </div>
        </div>
        """
        
        return html_content
    
    # ===== RESULTS MANAGEMENT =====
    
    def update_results_display(self, analysis_type: str, results: Dict[str, Any]):
        """Update results display with new results."""
        
        self.current_analysis = analysis_type
        self.current_results = results
        
        # Format results for quick display
        formatted_results = self.format_results(analysis_type, results)
        
        # Update quick results panel
        self.quick_results_panel.object = formatted_results
    
    def clear_results_display(self):
        """Clear results display."""
        
        self.current_results = {}
        
        self.quick_results_panel.object = """
        <div style='color: #666; font-style: italic; padding: 20px; text-align: center;'>
            📊 Analysis results will appear here...<br>
            <small>Select groups and run analysis to see results</small>
        </div>
        """
    
    # ===== EXPORT FUNCTIONALITY (FUTURE PHASES) =====
    
    def create_detailed_results_table(self, analysis_type: str, results: Dict[str, Any]):
        """Create detailed results table for export."""
        # Phase 4: Implementation
        pass
    
    def prepare_results_for_export(self, analysis_type: str, results: Dict[str, Any], format: str):
        """Prepare results for export in specified format."""
        # Phase 4: Implementation  
        pass
    
    def create_results_summary_text(self, analysis_type: str, results: Dict[str, Any]):
        """Create text summary of results."""
        # Phase 4: Implementation
        pass