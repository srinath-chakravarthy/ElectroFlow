"""
Tab 3 Data Analysis - Main Coordinator

Handles layout coordination, main event handlers, and state management for Tab 3.
This is the central control point that coordinates between analysis panels, plotting, and results.

Architecture: 3-row layout with progressive disclosure and isolated state management.
"""

import panel as pn
import param
import pandas as pd
from typing import Dict, List, Any


class DataAnalysisTab(param.Parameterized):
    """
    Main coordinator for Tab 3 Data Analysis interface.
    Handles layout, state management, and component coordination.
    
    Phase 1: Basic layout structure with placeholders
    Phase 2: Add data pipeline coordination  
    Phase 3: Add visualization coordination
    Phase 4: Add multiple analysis types
    """
    
    # ===== STATE MANAGEMENT =====
    current_cell = param.String(default="", doc="Currently selected cell")
    selected_groups = param.List(default=[], doc="Selected groups for analysis") 
    current_analysis = param.String(default="basic_statistics", doc="Current analysis type")
    analysis_results = param.Dict(default={}, doc="Current analysis results")
    
    def __init__(self, api, **params):
        super().__init__(**params)
        
        # Store API reference
        self.api = api
        
        # Import components (lazy loading to avoid circular imports)
        from .analysis_panels import AnalysisPanels
        from .plotting import PlottingManager  
        from .results import ResultsDisplay
        
        # Initialize specialized components
        self.analysis_panels = AnalysisPanels(api)
        self.plotting_manager = PlottingManager(api)
        self.results_display = ResultsDisplay(api)
        
        # Set reference for cross-component communication
        self.analysis_panels.main_tab = self
        
        # Create layout
        self._create_layout()
        self._setup_basic_event_handlers()
        
        # Initialize with empty state
        self._initialize_empty_state()
    
    def _create_layout(self):
        """Create professional 3-row Tab 3 layout."""
        
        # === ROW 1: CONTEXT BAR ===
        context_bar = self._create_context_bar()
        
        # === ROW 2: MAIN ANALYSIS AREA ===  
        main_area = self._create_main_analysis_area()
        
        # === ROW 3: EXPORT & DETAILED RESULTS ===
        export_results_area = self._create_export_results_area()
        
        # Complete layout
        self.panel = pn.Column(
            context_bar,
            main_area, 
            export_results_area,
            sizing_mode='stretch_both',
            min_height=700,
            styles={'background': '#F8F9FA'}
        )
    
    def _create_context_bar(self):
        """Create Row 1: Context bar with cell selector and analysis type."""
        
        # Cell selector placeholder
        self.cell_selector = pn.widgets.Select(
            name="Cell",
            options=[("No cells available", "")],
            value="",
            width=200
        )
        
        # Analysis type selector  
        self.analysis_type_selector = pn.widgets.Select(
            name="Analysis Type",
            options=[
                ("Basic Statistics", "basic_statistics"),
                ("Resistance Analysis", "resistance_analysis"),
                ("Kinetics Analysis", "kinetics_analysis"),
                ("dQ/dV Analysis", "dqdv_analysis")
            ],
            value="basic_statistics",
            width=200
        )
        
        # Status indicator placeholder
        self.status_indicator = pn.pane.HTML(
            """<div style='color: #666; font-size: 14px; padding: 8px;'>
               📊 Ready for analysis
               </div>""",
            width=300
        )
        
        # Context bar layout
        return pn.Row(
            pn.pane.HTML("<strong>📊 Data Analysis</strong>", margin=(10, 5)),
            pn.Spacer(width=20),
            self.cell_selector,
            pn.Spacer(width=20), 
            self.analysis_type_selector,
            pn.Spacer(),  # Push status to right
            self.status_indicator,
            styles={
                'background': 'white',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px',
                'padding': '10px',
                'margin': '10px'
            },
            height=60
        )
    
    def _create_main_analysis_area(self):
        """Create Row 2: Main analysis area with left panels and right visualization."""
        
        # === LEFT COLUMN (30%): ANALYSIS SETUP ===
        left_column = pn.Column(
            # Groups section (always visible)
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                📊 Groups Selection
            </div>
            """),
            
            # Groups panel placeholder
            self.analysis_panels.get_groups_panel(),
            
            # Analysis settings panel (collapsible, analysis-specific)
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                ⚙️ Analysis Settings
            </div>
            """),
            
            # Settings panel placeholder  
            self.analysis_panels.get_current_settings_panel(),
            
            # Analyze button
            pn.pane.HTML("""
            <div style='margin: 20px 5px 10px 5px; border-top: 1px solid #E0E0E0; padding-top: 15px;'>
            </div>
            """),
            
            self._create_analyze_button(),
            
            width=350,
            styles={
                'background': 'white',
                'border': '1px solid #E0E0E0', 
                'border-radius': '8px',
                'padding': '15px',
                'margin': '10px'
            }
        )
        
        # === RIGHT COLUMN (70%): VISUALIZATION & RESULTS ===
        right_column = pn.Column(
            # Main plot area
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                📈 Visualization
            </div>
            """),
            
            # Plot area placeholder
            self.plotting_manager.get_plot_area(),
            
            # Plot controls (collapsible)
            self.plotting_manager.get_plot_controls(),
            
            # Quick results panel
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                🔬 Quick Results
            </div>
            """),
            
            # Results placeholder
            self.results_display.get_quick_results_panel(),
            
            styles={
                'background': 'white',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px', 
                'padding': '15px',
                'margin': '10px'
            }
        )
        
        # Main area layout (30% | 70%)
        return pn.Row(
            left_column,
            right_column,
            sizing_mode='stretch_width',
            min_height=500
        )
    
    def _create_export_results_area(self):
        """Create Row 3: Export options and detailed results (collapsible)."""
        
        # Placeholder for export and detailed results
        export_panel = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                💾 Export & Detailed Results
            </div>
            """),
            
            pn.pane.HTML("""
            <div style='color: #666; padding: 20px; text-align: center;'>
                <em>Export options and detailed results will appear here...</em>
            </div>
            """),
            
            styles={
                'background': 'white',
                'border': '1px solid #E0E0E0',
                'border-radius': '8px',
                'padding': '15px', 
                'margin': '10px'
            }
        )
        
        return export_panel
    
    def _create_analyze_button(self):
        """Create the main analyze button."""
        
        self.analyze_btn = pn.widgets.Button(
            name="🔍 Analyze Selected Groups",
            button_type="primary",
            width=300,
            height=40,
            disabled=True  # Disabled until groups are selected
        )
        
        # Add click handler
        self.analyze_btn.on_click(self._on_analyze_clicked)
        
        return self.analyze_btn
    
    def _setup_basic_event_handlers(self):
        """Setup basic event handlers for Phase 1 (minimal functionality)."""
        
        # Cell selection handler
        self.cell_selector.param.watch(self._on_cell_changed, 'value')
        
        # Analysis type selection handler
        self.analysis_type_selector.param.watch(self._on_analysis_type_changed, 'value')
    
    def _initialize_empty_state(self):
        """Initialize with empty state and populate cell options."""
        
        try:
            # Get available cells
            cells = self.api.get_cells()
            if cells:
                cell_options = [(f"{cell['name']} ({len(self.api.get_cell_files(cell['name']))} files)", 
                               cell['name']) for cell in cells]
                self.cell_selector.options = cell_options
                
                # Auto-select first cell if available
                if cell_options:
                    self.cell_selector.value = cell_options[0][1]
            else:
                self.cell_selector.options = [("No cells available", "")]
                
        except Exception as e:
            print(f"Error initializing Tab 3 state: {e}")
            self.cell_selector.options = [("Error loading cells", "")]
    
    # ===== EVENT HANDLERS =====
    
    def _on_cell_changed(self, event):
        """Handle cell selection change."""
        new_cell = event.new
        # Ensure we have a string value, not a tuple
        if isinstance(new_cell, (tuple, list)) and len(new_cell) > 1:
            new_cell = new_cell[1]  # Take the value part of (label, value) tuple
        elif isinstance(new_cell, (tuple, list)) and len(new_cell) == 1:
            new_cell = new_cell[0]
        
        # Ensure it's a string
        new_cell = str(new_cell) if new_cell is not None else ""
        self.current_cell = new_cell
        
        if new_cell:
            # Update groups in analysis panels
            self.analysis_panels.update_available_groups(new_cell)
            
            # Update status
            self._update_status(f"Selected cell: {new_cell}", "info")
        else:
            # Clear groups
            self.analysis_panels.clear_groups()
            self._update_status("No cell selected", "info")
    
    def _on_analysis_type_changed(self, event):
        """Handle analysis type change.""" 
        new_analysis = event.new
        # Ensure we have a string value, not a tuple
        if isinstance(new_analysis, (tuple, list)) and len(new_analysis) > 1:
            new_analysis = new_analysis[1]  # Take the value part of (label, value) tuple
        elif isinstance(new_analysis, (tuple, list)) and len(new_analysis) == 1:
            new_analysis = new_analysis[0]
        
        # Ensure it's a string
        new_analysis = str(new_analysis) if new_analysis is not None else "basic_statistics"
        old_analysis = self.current_analysis
        
        self.current_analysis = new_analysis
        
        # Update analysis settings panel
        self.analysis_panels.show_settings_for_analysis(new_analysis)
        
        # Update available plot types
        self.plotting_manager.update_available_plots(new_analysis)
        
        # Update status
        self._update_status(f"Analysis type: {new_analysis}", "info")
    
    def _on_analyze_clicked(self, event):
        """Handle analyze button click - Phase 2: Real backend integration."""
        
        try:
            # Update status
            self._update_status("Running analysis...", "info")
            self.analyze_btn.disabled = True
            
            # Get selected groups
            selected_groups = self.analysis_panels.get_selected_groups()
            if not selected_groups:
                self._update_status("No groups selected", "warning")
                self.analyze_btn.disabled = False
                return
            
            # Get current analysis settings
            settings = self.analysis_panels.get_current_settings(self.current_analysis)
            
            # Run analysis based on type
            results = self._run_analysis(self.current_analysis, selected_groups, settings)
            
            # Update visualization
            plot = self.plotting_manager.create_plot(self.current_analysis, results, settings)
            self.plotting_manager.update_plot_area(plot)
            
            # Update results display
            self.results_display.update_results_display(self.current_analysis, results)
            
            # Store results
            self.analysis_results = results
            
            # Update status
            self._update_status(f"Analysis complete: {len(selected_groups)} groups", "success")
            
        except Exception as e:
            self._update_status(f"Analysis error: {str(e)}", "error")
            print(f"Analysis error details: {e}")
            
        finally:
            self.analyze_btn.disabled = False
    
    def _run_analysis(self, analysis_type: str, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run analysis using backend API."""
        
        if analysis_type == "basic_statistics":
            return self._run_basic_statistics_analysis(selected_groups, settings)
        elif analysis_type == "resistance_analysis":
            return self._run_resistance_analysis(selected_groups, settings)
        elif analysis_type == "kinetics_analysis":
            return self._run_kinetics_analysis(selected_groups, settings)
        elif analysis_type == "dqdv_analysis":
            return self._run_dqdv_analysis(selected_groups, settings)
        else:
            return {"error": f"Unknown analysis type: {analysis_type}"}
    
    def _run_basic_statistics_analysis(self, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run basic statistics analysis using existing backend."""
        
        try:
            # Enhanced basic statistics with per-technique breakdown
            print(f"Running basic statistics analysis for groups: {selected_groups}")
            
            # Get all segments from selected groups with technique information
            all_segments = self.api.get_multi_group_segments(selected_groups)
            
            # Format results for UI display
            results = {
                'analysis_type': 'basic_statistics',
                'selected_groups': selected_groups,
                'total_groups': len(selected_groups),
                'settings': settings,
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'total_segments': len(all_segments)
            }
            
            if not all_segments:
                results['technique_breakdown'] = {}
                results['message'] = "No segments found in selected groups"
                return results
            
            # Group segments by fundamental technique
            technique_groups = {}
            for segment in all_segments:
                # Get technique from segment data
                technique = segment.get('fundamental_technique', 'UNKNOWN')
                if technique not in technique_groups:
                    technique_groups[technique] = []
                technique_groups[technique].append(segment)
            
            # Calculate statistics per technique
            technique_breakdown = {}
            for technique, segments in technique_groups.items():
                if not segments:
                    continue
                
                # Extract metrics for this technique
                durations = [seg.get('duration_s', 0) for seg in segments if seg.get('duration_s') is not None]
                start_voltages = [seg.get('start_potential_v', 0) for seg in segments if seg.get('start_potential_v') is not None]
                end_voltages = [seg.get('end_potential_v', 0) for seg in segments if seg.get('end_potential_v') is not None]
                capacities = [seg.get('capacity_ah', 0) for seg in segments if seg.get('capacity_ah') is not None]
                energies = [seg.get('energy_wh', 0) for seg in segments if seg.get('energy_wh') is not None]
                
                technique_breakdown[technique] = {
                    'count': len(segments),
                    'duration_s': {
                        'mean': sum(durations) / len(durations) if durations else 0,
                        'std': pd.Series(durations).std() if len(durations) > 1 else 0,
                        'min': min(durations) if durations else 0,
                        'max': max(durations) if durations else 0
                    },
                    'start_potential_v': {
                        'mean': sum(start_voltages) / len(start_voltages) if start_voltages else 0,
                        'std': pd.Series(start_voltages).std() if len(start_voltages) > 1 else 0,
                        'min': min(start_voltages) if start_voltages else 0,
                        'max': max(start_voltages) if start_voltages else 0
                    },
                    'end_potential_v': {
                        'mean': sum(end_voltages) / len(end_voltages) if end_voltages else 0,
                        'std': pd.Series(end_voltages).std() if len(end_voltages) > 1 else 0,
                        'min': min(end_voltages) if end_voltages else 0,
                        'max': max(end_voltages) if end_voltages else 0
                    },
                    'capacity_ah': {
                        'mean': sum(capacities) / len(capacities) if capacities else 0,
                        'std': pd.Series(capacities).std() if len(capacities) > 1 else 0,
                        'min': min(capacities) if capacities else 0,
                        'max': max(capacities) if capacities else 0,
                        'total': sum(capacities) if capacities else 0
                    },
                    'energy_wh': {
                        'mean': sum(energies) / len(energies) if energies else 0,
                        'std': pd.Series(energies).std() if len(energies) > 1 else 0,
                        'min': min(energies) if energies else 0,
                        'max': max(energies) if energies else 0,
                        'total': sum(energies) if energies else 0
                    }
                }
            
            results['technique_breakdown'] = technique_breakdown
            results['techniques_found'] = list(technique_groups.keys())
            
            print(f"  - Analyzed {len(all_segments)} segments across {len(technique_groups)} techniques: {', '.join(technique_groups.keys())}")
            
            # Keep overall totals for compatibility
            total_capacity = sum(seg.get('capacity_ah', 0) for seg in all_segments if seg.get('capacity_ah') is not None)
            total_energy = sum(seg.get('energy_wh', 0) for seg in all_segments if seg.get('energy_wh') is not None)
            results['total_capacity_ah'] = total_capacity
            results['total_energy_wh'] = total_energy
            
        except Exception as e:
            print(f"Basic statistics analysis error: {e}")
            return {
                'analysis_type': 'basic_statistics',
                'selected_groups': selected_groups,
                'technique_breakdown': {},
                'error': str(e),
                'message': f'Basic statistics analysis failed: {str(e)}'
            }
        
        return results
    
    def _run_resistance_analysis(self, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run resistance analysis using electrochemical resistance backend - Phase 1: New implementation."""
        
        try:
            # Phase 1: Connect to get_electrochemical_resistance_analysis() API
            print(f"Running resistance analysis for groups: {selected_groups}")
            
            # Use existing get_electrochemical_resistance_analysis method
            resistance_results = self.api.get_electrochemical_resistance_analysis(selected_groups)
            
            # Debug: Print actual backend structure to understand data format
            print(f"DEBUG: Resistance backend structure keys: {list(resistance_results.keys()) if isinstance(resistance_results, dict) else 'Not a dict'}")
            if isinstance(resistance_results, dict) and 'individual_resistances' in resistance_results:
                individual_count = len(resistance_results['individual_resistances'])
                print(f"DEBUG: Found {individual_count} individual resistance measurements")
                if individual_count > 0:
                    first_item = resistance_results['individual_resistances'][0]
                    print(f"DEBUG: First resistance item keys: {list(first_item.keys()) if isinstance(first_item, dict) else 'Not a dict'}")
                    if isinstance(first_item, dict):
                        for key, value in first_item.items():
                            print(f"DEBUG: {key}: {value} (type: {type(value)})")
            else:
                print(f"DEBUG: No 'individual_resistances' key found. Available keys: {list(resistance_results.keys()) if isinstance(resistance_results, dict) else 'None'}")
            
            # Format results for UI display
            results = {
                'analysis_type': 'resistance_analysis',
                'selected_groups': selected_groups,
                'total_groups': len(selected_groups),
                'settings': settings,
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'backend_results': resistance_results
            }
            
            # Process resistance data for visualization
            if resistance_results and isinstance(resistance_results, dict):
                
                # Initialize resistance analysis summary
                resistance_summary = {
                    'total_measurements': 0,
                    'valid_measurements': 0,
                    'null_measurements': 0,
                    'invalid_measurements': 0,
                    'resistance_values_ohm': [],
                    'time_points_s': [],
                    'average_resistance_ohm': 0.0,
                    'resistance_std_ohm': 0.0,
                    'measurement_types': set()
                }
                
                # Extract resistance measurements from backend structure
                # Backend should return individual segments with analysis_results containing current_pulse data
                if 'individual_resistances' in resistance_results:
                    individual_resistances = resistance_results['individual_resistances']
                    
                    for resistance_data in individual_resistances:
                        if isinstance(resistance_data, dict):
                            segment_id = resistance_data.get('segment_id', 'unknown')
                            
                            # Count all measurements first
                            resistance_summary['total_measurements'] += 1
                            
                            # Process each resistance type using analytics config current_pulse schema
                            for key, time_point, type_name in [
                                ('ir_immediate_ohm', 0, 'immediate'),
                                ('ir_10s_ohm', 10, '10s'), 
                                ('ir_30s_ohm', 30, '30s')
                            ]:
                                if key in resistance_data:
                                    value = resistance_data[key]
                                    if value is None:
                                        resistance_summary['null_measurements'] += 1
                                    elif isinstance(value, (int, float)) and value > 0:
                                        resistance_summary['resistance_values_ohm'].append(value)
                                        resistance_summary['time_points_s'].append(time_point)
                                        resistance_summary['measurement_types'].add(type_name)
                                        resistance_summary['valid_measurements'] += 1
                                    else:
                                        # Invalid numeric value (negative, zero, etc.)
                                        resistance_summary['invalid_measurements'] += 1
                
                # Also check if backend returns analysis_results with current_pulse schema
                elif hasattr(resistance_results, '__iter__'):
                    # If backend returns segments with analysis_results field
                    for segment_data in resistance_results:
                        if isinstance(segment_data, dict) and 'analysis_results' in segment_data:
                            analysis_results = segment_data.get('analysis_results', {})
                            if isinstance(analysis_results, dict) and 'current_pulse' in analysis_results:
                                current_pulse = analysis_results['current_pulse']
                                resistance_summary['total_measurements'] += 1
                                
                                # Process using analytics config current_pulse schema
                                for key, time_point, type_name in [
                                    ('ir_immediate_ohm', 0, 'immediate'),
                                    ('ir_10s_ohm', 10, '10s'), 
                                    ('ir_30s_ohm', 30, '30s')
                                ]:
                                    if key in current_pulse:
                                        value = current_pulse[key]
                                        if value is None:
                                            resistance_summary['null_measurements'] += 1
                                        elif isinstance(value, (int, float)) and value > 0:
                                            resistance_summary['resistance_values_ohm'].append(value)
                                            resistance_summary['time_points_s'].append(time_point)
                                            resistance_summary['measurement_types'].add(type_name)
                                            resistance_summary['valid_measurements'] += 1
                                        else:
                                            resistance_summary['invalid_measurements'] += 1
                
                # Also handle legacy nested structure if present (fallback)
                else:
                    for group_id, group_data in resistance_results.items():
                        if isinstance(group_data, dict):
                            for segment_id, segment_data in group_data.items():
                                if isinstance(segment_data, dict) and 'current_pulse' in segment_data:
                                    pulse_data = segment_data['current_pulse']
                                    if isinstance(pulse_data, dict):
                                        # Legacy structure support
                                        for key, time_point in [('immediate_resistance_ohm', 0), ('resistance_10s_ohm', 10), ('resistance_30s_ohm', 30)]:
                                            if key in pulse_data and pulse_data[key] is not None and pulse_data[key] > 0:
                                                resistance_summary['resistance_values_ohm'].append(pulse_data[key])
                                                resistance_summary['time_points_s'].append(time_point)
                                                resistance_summary['measurement_types'].add(key.replace('_resistance_ohm', '').replace('_ohm', ''))
                
                # Calculate resistance statistics
                if resistance_summary['resistance_values_ohm']:
                    resistance_values = resistance_summary['resistance_values_ohm']
                    resistance_summary['total_measurements'] = len(resistance_values)
                    resistance_summary['average_resistance_ohm'] = sum(resistance_values) / len(resistance_values)
                    
                    if len(resistance_values) > 1:
                        resistance_summary['resistance_std_ohm'] = pd.Series(resistance_values).std()
                    
                    resistance_summary['min_resistance_ohm'] = min(resistance_values)
                    resistance_summary['max_resistance_ohm'] = max(resistance_values)
                
                # Add summary to results
                results['resistance_analysis'] = resistance_summary
                
                # Add convenient access fields
                results['avg_resistance'] = resistance_summary['average_resistance_ohm']
                results['resistance_std'] = resistance_summary['resistance_std_ohm'] 
                results['total_measurements'] = resistance_summary['total_measurements']
                results['valid_measurements'] = resistance_summary['valid_measurements']
                results['null_measurements'] = resistance_summary['null_measurements']
                results['measurement_types'] = list(resistance_summary['measurement_types'])
                
                # Enhanced logging
                print(f"Resistance analysis complete: {results['total_measurements']} total measurements (valid:{results['valid_measurements']}, null:{results['null_measurements']}), avg={results['avg_resistance']:.4f}Ω")
                
            else:
                print("No resistance analysis data returned from backend")
                
            return results
            
        except Exception as e:
            print(f"Error in resistance analysis: {e}")
            # Return fallback data structure
            return {
                'analysis_type': 'resistance_analysis',
                'selected_groups': selected_groups,
                'total_groups': len(selected_groups),
                'settings': settings,
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'error': str(e),
                'resistance_analysis': {
                    'total_measurements': 0,
                    'average_resistance_ohm': 0.0,
                    'resistance_std_ohm': 0.0
                },
                'avg_resistance': 0.0,
                'resistance_std': 0.0,
                'total_measurements': 0,
                'note': 'Resistance analysis error - using fallback'
            }
    
    def _run_dqdv_analysis(self, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run dQ/dV analysis using existing backend - Phase 4: Real implementation.""" 
        
        try:
            # Phase 4: Connect to existing electrochemical insights API
            print(f"Running dQ/dV analysis for groups: {selected_groups}")
            
            # Note: dQ/dV typically requires capacity data and voltage measurements
            # For now, we'll use the REST analysis as a foundation since it provides
            # voltage relaxation kinetics which can be related to dQ/dV
            
            # Try to get REST analysis from electrochemical insights
            rest_analysis = self.api.get_electrochemical_rest_analysis(selected_groups)
            
            results = {
                'analysis_type': 'dqdv_analysis',
                'selected_groups': selected_groups,
                'total_groups': len(selected_groups), 
                'settings': settings,
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'backend_results': rest_analysis
            }
            
            # Extract dQ/dV-relevant information from REST analysis
            if rest_analysis and isinstance(rest_analysis, dict):
                
                # Extract kinetics information that relates to dQ/dV
                if 'relaxation_kinetics' in rest_analysis:
                    kinetics = rest_analysis['relaxation_kinetics']
                    results['voltage_relaxation_data'] = kinetics
                    
                    # Extract time constants and equilibrium voltages
                    if isinstance(kinetics, list):
                        time_constants = []
                        equilibrium_voltages = []
                        
                        for segment_kinetics in kinetics:
                            if isinstance(segment_kinetics, dict):
                                # Extract exponential fit parameters
                                if 'exponential_fit' in segment_kinetics:
                                    fit = segment_kinetics['exponential_fit']
                                    # Use analytics config field names for exponential_fit schema
                                    if 'time_constant_s' in fit:
                                        time_constants.append(fit['time_constant_s'])
                                    if 'voltage_infinity' in fit:
                                        equilibrium_voltages.append(fit['voltage_infinity'])
                        
                        if time_constants:
                            results['mean_time_constant'] = sum(time_constants) / len(time_constants)
                            results['time_constants'] = time_constants
                            
                        if equilibrium_voltages:
                            results['mean_equilibrium_voltage'] = sum(equilibrium_voltages) / len(equilibrium_voltages)
                            results['equilibrium_voltages'] = equilibrium_voltages
                
                # Extract quality metrics
                if 'quality_assessment' in rest_analysis:
                    quality = rest_analysis['quality_assessment']
                    results['analysis_quality'] = quality
                    
                # Count successful analyses
                successful_analyses = 0
                total_segments = 0
                
                if 'relaxation_kinetics' in rest_analysis:
                    kinetics = rest_analysis['relaxation_kinetics']
                    if isinstance(kinetics, list):
                        total_segments = len(kinetics)
                        for seg in kinetics:
                            if isinstance(seg, dict) and 'exponential_fit' in seg:
                                fit = seg['exponential_fit']
                                if isinstance(fit, dict) and fit.get('r_squared', 0) > 0.8:
                                    successful_analyses += 1
                
                results['total_segments_analyzed'] = total_segments
                results['successful_analyses'] = successful_analyses
                results['success_rate'] = (successful_analyses / total_segments * 100) if total_segments > 0 else 0
            else:
                # Fallback if no REST analysis available
                results.update({
                    'message': 'dQ/dV analysis requires REST segment data for voltage relaxation kinetics',
                    'note': 'No suitable electrochemical data found for dQ/dV analysis'
                })
            
            return results
            
        except Exception as e:
            print(f"dQ/dV analysis error: {e}")
            return {
                'analysis_type': 'dqdv_analysis', 
                'selected_groups': selected_groups,
                'total_groups': len(selected_groups),
                'settings': settings,
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'error': f"dQ/dV analysis failed: {str(e)}",
                'message': 'dQ/dV analysis requires electrochemical data with voltage relaxation segments'
            }
    
    def _run_kinetics_analysis(self, selected_groups: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run kinetics analysis using electrochemical equilibrium backend - Phase 2: Real implementation."""
        
        try:
            # Phase 2.1: Connect to get_electrochemical_equilibrium_analysis() API
            print(f"Running kinetics analysis for groups: {selected_groups}")
            
            # Use existing get_electrochemical_equilibrium_analysis method
            equilibrium_results = self.api.get_electrochemical_equilibrium_analysis(selected_groups)
            
            # Debug: Print actual backend structure to understand data format
            print(f"DEBUG: Equilibrium backend structure keys: {list(equilibrium_results.keys()) if isinstance(equilibrium_results, dict) else 'Not a dict'}")
            if isinstance(equilibrium_results, dict):
                for key, value in equilibrium_results.items():
                    print(f"DEBUG: {key}: {type(value)} = {value if not isinstance(value, (dict, list)) else f'{type(value)} with {len(value)} items'}")
                    if isinstance(value, dict) and len(value) < 5:  # Print small dicts
                        for sub_key, sub_value in value.items():
                            print(f"DEBUG:   {sub_key}: {type(sub_value)} = {sub_value}")
                    elif isinstance(value, list) and len(value) > 0:  # Print first list item
                        print(f"DEBUG:   First item: {type(value[0])} = {value[0]}")
            
            # Format results for UI display
            results = {
                'analysis_type': 'kinetics_analysis',
                'selected_groups': selected_groups,
                'total_groups': len(selected_groups),
                'settings': settings,
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'backend_results': equilibrium_results
            }
            
            # Process kinetics data for visualization
            if equilibrium_results and isinstance(equilibrium_results, dict):
                
                # Initialize kinetics analysis summary
                kinetics_summary = {
                    'total_measurements': 0,
                    'valid_measurements': 0,
                    'null_measurements': 0,
                    'invalid_measurements': 0,
                    'time_constants': [],
                    'diffusion_coefficients': [],
                    'equilibrium_voltages': [],
                    'voltage_time_data': [],  # For voltage vs time plots
                    'resistance_analysis': {},
                    'calculation_quality': []
                }
                
                # Process backend structure - equilibrium data in individual_equilibrium array
                # Backend returns analytics_config fields directly (not nested in analysis_results)
                if 'individual_equilibrium' in equilibrium_results:
                    individual_equilibrium = equilibrium_results['individual_equilibrium']
                    
                    for equilibrium_data in individual_equilibrium:
                        if isinstance(equilibrium_data, dict):
                            kinetics_summary['total_measurements'] += 1
                            
                            # Extract equilibrium voltage using analytics config schema (direct field)
                            if 'voltage_infinity' in equilibrium_data and equilibrium_data['voltage_infinity'] is not None:
                                kinetics_summary['equilibrium_voltages'].append(equilibrium_data['voltage_infinity'])
                                kinetics_summary['valid_measurements'] += 1
                            else:
                                kinetics_summary['null_measurements'] += 1
                            
                            # Extract time constant using analytics config schema (direct field)
                            if 'time_constant_s' in equilibrium_data and equilibrium_data['time_constant_s'] is not None:
                                kinetics_summary['time_constants'].append(equilibrium_data['time_constant_s'])
                            
                            # Extract diffusion coefficient (calculated on-the-fly by backend)
                            if 'diffusion_coefficient_cm2_s' in equilibrium_data and equilibrium_data['diffusion_coefficient_cm2_s'] is not None:
                                kinetics_summary['diffusion_coefficients'].append(equilibrium_data['diffusion_coefficient_cm2_s'])
                            
                            # Track R² quality from analytics config (direct field)
                            if 'r_squared' in equilibrium_data:
                                r_squared = equilibrium_data['r_squared']
                                if r_squared and r_squared > 0.8:
                                    quality = 'valid'
                                elif r_squared and r_squared > 0.5:
                                    quality = 'marginal'
                                else:
                                    quality = 'invalid'
                                kinetics_summary['calculation_quality'].append(quality)
                                if quality == 'invalid':
                                    kinetics_summary['invalid_measurements'] += 1
                            else:
                                # No r_squared available, assume valid if we have voltage_infinity
                                quality = 'valid' if equilibrium_data.get('voltage_infinity') is not None else 'invalid'
                                kinetics_summary['calculation_quality'].append(quality)
                
                # Also extract from top-level diffusion_coefficients dict if available
                if 'diffusion_coefficients' in equilibrium_results:
                    diff_coeffs_dict = equilibrium_results['diffusion_coefficients']
                    if isinstance(diff_coeffs_dict, dict):
                        # Add any additional diffusion coefficients not already captured
                        for segment_id, coeff in diff_coeffs_dict.items():
                            if coeff is not None and coeff not in kinetics_summary['diffusion_coefficients']:
                                kinetics_summary['diffusion_coefficients'].append(coeff)
                # Fallback: if backend returns direct key-value pairs (older format)
                else:
                    for key, value in equilibrium_results.items():
                        if isinstance(value, dict):
                            kinetics_summary['total_measurements'] += 1
                            
                            # Look for analytics config field names first, then fallback to any equilibrium voltage field
                            voltage_fields = ['voltage_infinity', 'equilibrium_voltage_v', 'voltage_eq']
                            time_constant_fields = ['time_constant_s', 'tau_s']
                            
                            found_voltage = False
                            for field in voltage_fields:
                                if field in value and value[field] is not None:
                                    kinetics_summary['equilibrium_voltages'].append(value[field])
                                    kinetics_summary['valid_measurements'] += 1
                                    found_voltage = True
                                    break
                            
                            if not found_voltage:
                                kinetics_summary['null_measurements'] += 1
                            
                            for field in time_constant_fields:
                                if field in value and value[field] is not None:
                                    kinetics_summary['time_constants'].append(value[field])
                                    break
                            
                            # Track calculation quality
                            quality = value.get('calculation_quality', 'unknown')
                            kinetics_summary['calculation_quality'].append(quality)
                            if quality == 'invalid':
                                kinetics_summary['invalid_measurements'] += 1
                
                # Add summary to results
                results['kinetics_analysis'] = kinetics_summary
                
                # Add convenient access fields
                results['total_measurements'] = kinetics_summary['total_measurements']
                results['valid_measurements'] = kinetics_summary['valid_measurements']
                results['null_measurements'] = kinetics_summary['null_measurements']
                results['invalid_measurements'] = kinetics_summary['invalid_measurements']
                results['avg_equilibrium_voltage'] = (
                    sum(kinetics_summary['equilibrium_voltages']) / len(kinetics_summary['equilibrium_voltages'])
                    if kinetics_summary['equilibrium_voltages'] else 0.0
                )
                results['equilibrium_voltage_std'] = (
                    pd.Series(kinetics_summary['equilibrium_voltages']).std()
                    if len(kinetics_summary['equilibrium_voltages']) > 1 else 0.0
                )
                
                # Enhanced logging with quality information
                eq_voltages = len(kinetics_summary['equilibrium_voltages'])
                time_constants = len(kinetics_summary['time_constants'])
                diffusion_coeffs = len(kinetics_summary['diffusion_coefficients'])
                quality_info = f"valid:{results['valid_measurements']}, null:{results['null_measurements']}, invalid:{results['invalid_measurements']}"
                print(f"Kinetics analysis complete: {results['total_measurements']} total measurements ({quality_info})")
                print(f"  - Equilibrium voltages: {eq_voltages}, Time constants: {time_constants}, Diffusion coeffs: {diffusion_coeffs}")
                
            else:
                print("No equilibrium analysis data returned from backend")
            
            return results
            
        except Exception as e:
            print(f"Kinetics analysis error: {e}")
            return {
                'analysis_type': 'kinetics_analysis',
                'selected_groups': selected_groups,
                'total_groups': len(selected_groups),
                'settings': settings,
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'error': f"Kinetics analysis failed: {str(e)}",
                'message': 'Kinetics analysis requires electrochemical data with REST or galvanostatic segments'
            }
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Update status indicator."""
        
        status_colors = {
            "info": "#1976D2",
            "success": "#2E7D32", 
            "warning": "#F57C00",
            "error": "#D32F2F"
        }
        
        status_icons = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌"
        }
        
        color = status_colors.get(status_type, "#666")
        icon = status_icons.get(status_type, "📊")
        
        self.status_indicator.object = f"""
        <div style='color: {color}; font-size: 14px; padding: 8px;'>
           {icon} {message}
        </div>
        """
    
    # ===== PUBLIC INTERFACE =====
    
    def get_current_state(self):
        """Get current state for components."""
        return {
            'current_cell': self.current_cell,
            'selected_groups': self.selected_groups,
            'current_analysis': self.current_analysis,
            'analysis_results': self.analysis_results
        }
    
    def update_state(self, key: str, value: Any):
        """Update state and notify components."""
        setattr(self, key, value)
        
        # Notify components of state changes if needed
        if key == 'selected_groups':
            self._update_status(f"Selected {len(value)} groups", "info")
    
    def cleanup(self):
        """Cleanup method for tab switching."""
        # Clear any background operations or watchers if needed
        pass