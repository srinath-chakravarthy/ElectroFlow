"""
Professional Data Analysis Tab - Two Column Layout

Left: Selection & Statistics | Right: Visualization Panel
Clean data analysis interface with professional styling matching existing components.
"""

import panel as pn
import param
import pandas as pd
from typing import List, Dict, Any, Optional


class DataAnalysisTab(param.Parameterized):
    """
    Professional data analysis component with two-column design.

    Features:
    - Left Column: Cell/Group/Segment selection with statistics
    - Right Column: Visualization panel (imported separately)
    - Button-driven workflow with explicit user control
    - Multi-group and segment subset analysis
    """

    current_cell = param.String(default="", doc="Currently selected cell")
    selected_groups = param.List(default=[], doc="Currently selected group IDs")
    selected_segments = param.List(default=[], doc="Currently selected segment IDs")
    status_message = param.String(default="", doc="Status message for main app")

    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        self.loaded_segments = []  # Cache for current segments
        self._create_components()

        # Import visualization component (separate file)
        try:
            from .visualization_panel import VisualizationPanel
            self.viz_panel = VisualizationPanel(api=self.api)
            self._setup_viz_connections()
        except ImportError:
            # Placeholder if visualization panel not yet implemented
            self.viz_panel = self._create_viz_placeholder()

    def _create_components(self):
        """Create professional UI components for left column."""

        # === CELL SELECTION ===

        self.cell_selector = pn.widgets.Select(
            name="Select Cell",
            options=[],
            width=280,
            margin=(5, 5)
        )
        self.cell_selector.param.watch(self._on_cell_selected, 'value')

        # === GROUPS SELECTION ===

        self.groups_table = pn.widgets.Tabulator(
            value=[],
            pagination='remote',
            page_size=8,
            sizing_mode='stretch_width',
            selectable='checkbox',  # Multi-select
            sortable=True,
            show_index=False,
            configuration={
                'layout': 'fitColumns',
                'height': '200px',
                'placeholder': 'Select a cell to view groups...',
                'responsiveLayout': 'hide'
            },
            height=200,
            margin=(5, 5)
        )

        self.load_segments_btn = pn.widgets.Button(
            name="📋 Load Segments",
            button_type="primary",
            width=150,
            disabled=True,
            margin=(10, 5)
        )
        self.load_segments_btn.on_click(self._on_load_segments)

        # === SEGMENTS SELECTION ===

        self.segments_table = pn.widgets.Tabulator(
            value=[],
            pagination='remote',
            page_size=12,
            sizing_mode='stretch_width',
            selectable='checkbox',  # Multi-select for sub-selection
            sortable=True,
            show_index=False,
            configuration={
                'layout': 'fitColumns',
                'height': '300px',
                'placeholder': 'Load segments from selected groups...',
                'responsiveLayout': 'hide'
            },
            height=300,
            margin=(5, 5)
        )

        self.calculate_stats_btn = pn.widgets.Button(
            name="📊 Calculate Stats for Selected",
            button_type="primary",
            width=200,
            disabled=True,
            margin=(10, 5)
        )
        self.calculate_stats_btn.on_click(self._on_calculate_stats)

        # === STATISTICS DISPLAY ===

        self.stats_info_display = pn.pane.HTML(
            """<div style='background: #F8F9FA; padding: 12px; border-radius: 4px; color: #666; text-align: center;'>
               <strong>No data loaded</strong><br>
               <small>Select cell and groups to view statistics</small>
               </div>""",
            margin=(5, 5)
        )

        self.stats_table = pn.widgets.Tabulator(
            value=[],
            pagination='remote',
            page_size=10,
            sizing_mode='stretch_width',
            show_index=False,
            configuration={
                'layout': 'fitColumns',
                'height': '250px',
                'placeholder': 'No statistics calculated...'
            },
            height=250,
            visible=False,
            margin=(5, 5)
        )

        # Key metrics cards
        self.key_metrics_display = pn.Column(
            visible=False,
            margin=(5, 5)
        )

        # Status display
        self.status_display = pn.pane.HTML(
            "<div style='color: #2E7D32; font-size: 14px; padding: 5px;'>✅ Ready for data analysis</div>",
            margin=(5, 5)
        )

    def _create_viz_placeholder(self):
        """Create placeholder for visualization panel."""
        return pn.pane.HTML(
            """<div style='background: #F0F8F0; padding: 40px; border-radius: 8px; 
                          border: 2px dashed #4CAF50; text-align: center; height: 600px;
                          display: flex; flex-direction: column; justify-content: center;'>
               <div style='font-size: 48px; opacity: 0.3; margin-bottom: 20px;'>📊</div>
               <h3 style='color: #2E7D32; margin: 10px 0;'>Visualization Panel</h3>
               <p style='color: #4CAF50; margin: 5px 0;'>
                   Interactive plots will appear here based on your selections
               </p>
               <small style='color: #666; margin-top: 20px;'>
                   visualization_panel.py - Coming soon
               </small>
               </div>""",
            sizing_mode='stretch_both'
        )

    @property
    def panel(self):
        """Return professional two-column layout."""

        # Header with icon
        header = pn.pane.HTML("""
        <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white; 
                    padding: 15px; border-radius: 8px 8px 0 0; margin: 0;'>
            <h2 style='margin: 0; font-size: 18px; font-weight: 600;'>
                📊 Data Analysis & Visualization
            </h2>
        </div>
        """, margin=(0, 0))

        # Left Column - Selection & Statistics
        left_column = pn.Column(
            # Cell Selection Section
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 15px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                1. Cell Selection
            </div>
            """),

            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555; font-size: 14px;'>Select Cell:</label>"),
                self.cell_selector,
                margin=(5, 10)
            ),

            # Groups Selection Section
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                2. Groups Selection
            </div>
            """),

            pn.pane.HTML("""
            <div style='font-size: 12px; color: #666; margin: 5px; padding: 8px;
                        background: #F8F9FA; border-radius: 4px;'>
                Select one or more groups using checkboxes, then load their segments.
            </div>
            """),

            self.groups_table,

            pn.Row(
                self.load_segments_btn,
                margin=(5, 10)
            ),

            # Segments Selection Section
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                3. Segments & Statistics
            </div>
            """),

            self.segments_table,

            pn.Row(
                self.calculate_stats_btn,
                margin=(5, 10)
            ),

            # Statistics Display Section
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                4. Statistics Summary
            </div>
            """),

            self.stats_info_display,
            self.stats_table,
            self.key_metrics_display,

            # Status
            self.status_display,

            width=400,
            margin=(10, 10),
            styles={'background': 'white', 'border-radius': '0 0 0 8px',
                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)'}
        )

        # Right Column - Visualization Panel
        right_column = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 15px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                Interactive Visualization
            </div>
            """),

            self.viz_panel.panel if hasattr(self.viz_panel, 'panel') else self.viz_panel,

            margin=(10, 10),
            styles={'background': 'white', 'border-radius': '0 0 8px 0',
                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)'}
        )

        # Main two-column layout
        main_content = pn.Row(
            left_column,
            right_column,
            sizing_mode='stretch_width'
        )

        # Complete card
        return pn.Column(
            header,
            main_content,
            margin=(10, 10),
            styles={'border-radius': '8px', 'overflow': 'hidden'}
        )

    def set_current_cell(self, cell_name: str):
        """Set current cell and refresh groups."""
        self.current_cell = cell_name
        if cell_name:
            self._refresh_groups()
            self._update_status(f"Selected cell: {cell_name}", "success")
        else:
            self.groups_table.value = []
            self.segments_table.value = []
            self._clear_statistics()
            self._update_status("No cell selected", "info")

    def _refresh_groups(self):
        """Refresh groups for current cell."""
        if not self.current_cell:
            return

        try:
            # Mock API call - replace with real backend
            groups = self._mock_get_cell_groups(self.current_cell)

            # Format for tabulator
            formatted_groups = []
            for group in groups:
                formatted_groups.append({
                    'group_id': group['group_id'],
                    'group_name': group['name'],
                    'segment_count': group['segment_count'],
                    'created_at': group['created_at'],
                    'description': group.get('description', '')
                })

            self.groups_table.value = formatted_groups
            self.load_segments_btn.disabled = len(formatted_groups) == 0
            self._update_status(f"Loaded {len(groups)} groups", "success")

        except Exception as e:
            self._update_status(f"Error loading groups: {str(e)}", "error")

    def _on_cell_selected(self, event):
        """Handle cell selection."""
        cell_name = event.new
        if isinstance(cell_name, tuple):
            cell_name = cell_name[1] if len(cell_name) > 1 else cell_name[0]
        elif not isinstance(cell_name, str):
            cell_name = str(cell_name) if cell_name is not None else ""

        self.set_current_cell(cell_name)

    def _on_load_segments(self, event):
        """Load segments from selected groups."""
        selected_indices = self.groups_table.selection
        if not selected_indices:
            self._update_status("Please select groups first", "warning")
            return

        try:
            # Get group data from table value using selected indices
            table_data = self.groups_table.value
            if not table_data or not isinstance(table_data, list):
                self._update_status("No group data available", "error")
                return
                
            selected_groups = [table_data[i] for i in selected_indices if i < len(table_data)]
            self.selected_groups = [group['group_id'] for group in selected_groups]

            # Load all segments from selected groups
            all_segments = []
            for group in selected_groups:
                group_segments = self._mock_get_group_segments(group['group_id'])
                all_segments.extend(group_segments)

            # Format for segments table
            formatted_segments = []
            for segment in all_segments:
                formatted_segments.append({
                    'segment_id': segment['segment_id'],
                    'technique': segment['technique'],
                    'start_potential_v': f"{segment['start_potential_v']:.3f}V",
                    'end_potential_v': f"{segment['end_potential_v']:.3f}V",
                    'duration_s': f"{segment['duration_s']:.1f}s",
                    'capacity_ah': f"{segment.get('capacity_ah', 0):.4f}",
                    'energy_wh': f"{segment.get('energy_wh', 0):.4f}",
                    'group_name': segment.get('group_name', 'Unknown')
                })

            self.segments_table.value = formatted_segments
            # Auto-select all segments (use row indices, not data)
            self.segments_table.selection = list(range(len(formatted_segments)))
            self.loaded_segments = all_segments

            # Auto-calculate statistics for all loaded segments
            self._calculate_and_display_stats(all_segments)

            self.calculate_stats_btn.disabled = False
            self._update_status(f"Loaded {len(all_segments)} segments from {len(selected_groups)} groups", "success")

            # Update visualization panel
            self._update_visualization(all_segments)

        except Exception as e:
            self._update_status(f"Error loading segments: {str(e)}", "error")

    def _on_calculate_stats(self, event):
        """Calculate statistics for selected segments."""
        selected_indices = self.segments_table.selection
        if not selected_indices:
            self._update_status("Please select segments first", "warning")
            return

        try:
            # Get segment data from table value using selected indices
            table_data = self.segments_table.value
            if not table_data or not isinstance(table_data, list):
                self._update_status("No segment data available", "error")
                return
                
            selected_segments = [table_data[i] for i in selected_indices if i < len(table_data)]
            
            # Get full segment data for selected segments using segment_id
            selected_segment_ids = [seg['segment_id'] for seg in selected_segments]
            segment_data = [seg for seg in self.loaded_segments
                            if seg['segment_id'] in selected_segment_ids]

            self._calculate_and_display_stats(segment_data)
            self._update_status(f"Calculated stats for {len(segment_data)} selected segments", "success")

            # Update visualization panel
            self._update_visualization(segment_data)

        except Exception as e:
            self._update_status(f"Error calculating statistics: {str(e)}", "error")

    def _calculate_and_display_stats(self, segments_data):
        """Calculate and display statistics for given segments."""
        if not segments_data:
            return

        # Calculate base metrics statistics
        stats = self._calculate_base_statistics(segments_data)

        # Display statistics info
        num_segments = len(segments_data)
        num_groups = len(set(seg.get('group_name', 'Unknown') for seg in segments_data))

        self.stats_info_display.object = f"""
        <div style='background: #E8F5E8; padding: 12px; border-radius: 4px; 
                    border-left: 4px solid #2E7D32;'>
            <div style='font-weight: 600; color: #2E7D32; margin-bottom: 5px;'>
                📊 Statistics Overview
            </div>
            <div style='font-size: 12px; color: #1B5E20;'>
                <strong>Segments:</strong> {num_segments}<br>
                <strong>Groups:</strong> {num_groups}<br>
                <strong>Techniques:</strong> {len(set(seg['technique'] for seg in segments_data))}
            </div>
        </div>
        """

        # Format statistics for table
        stats_rows = []
        for metric, values in stats.items():
            stats_rows.append({
                'metric': metric.replace('_', ' ').title(),
                'mean': f"{values['mean']:.4f}",
                'std': f"{values['std']:.4f}",
                'min': f"{values['min']:.4f}",
                'max': f"{values['max']:.4f}",
                'count': values['count']
            })

        self.stats_table.value = stats_rows
        self.stats_table.visible = True

        # Display key metrics cards
        self._display_key_metrics(stats)

    def _calculate_base_statistics(self, segments_data):
        """Calculate statistics for all base metrics using actual column names."""
        import numpy as np

        # Use actual column names from segments table
        base_metrics = [
            'start_potential_v', 'end_potential_v', 'start_current_a', 'end_current_a',
            'duration_s', 'capacity_ah', 'energy_wh'
        ]

        stats = {}
        for metric in base_metrics:
            values = [seg.get(metric, 0) for seg in segments_data]
            values = [v for v in values if v is not None]  # Remove None values

            if values:
                stats[metric] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'count': len(values),
                    'values': values
                }
            else:
                stats[metric] = {
                    'mean': 0, 'std': 0, 'min': 0, 'max': 0, 'count': 0, 'values': []
                }

        return stats

    def _display_key_metrics(self, stats):
        """Display key metrics as cards using actual column names."""
        # Voltage recovery using actual column names
        voltage_recovery = stats['end_potential_v']['mean'] - stats['start_potential_v']['mean']
        voltage_recovery_std = np.sqrt(stats['end_potential_v']['std'] ** 2 + stats['start_potential_v']['std'] ** 2)

        # Duration info using actual column name
        duration_mean = stats['duration_s']['mean']
        duration_std = stats['duration_s']['std']

        # Capacity info
        capacity_mean = stats['capacity_ah']['mean']
        capacity_std = stats['capacity_ah']['std']

        cards = [
            pn.pane.HTML(f"""
            <div style='background: #E8F5E8; border-left: 4px solid #2E7D32; 
                        padding: 12px; border-radius: 4px; margin: 5px 0;'>
                <div style='color: #2E7D32; font-weight: 600; font-size: 14px;'>Voltage Recovery</div>
                <div style='color: #1B5E20; font-size: 16px; font-weight: 700;'>
                    {voltage_recovery:.3f} ± {voltage_recovery_std:.3f} V
                </div>
            </div>
            """),

            pn.pane.HTML(f"""
            <div style='background: #E3F2FD; border-left: 4px solid #1976D2; 
                        padding: 12px; border-radius: 4px; margin: 5px 0;'>
                <div style='color: #1976D2; font-weight: 600; font-size: 14px;'>Average Duration</div>
                <div style='color: #0D47A1; font-size: 16px; font-weight: 700;'>
                    {duration_mean:.1f} ± {duration_std:.1f} s
                </div>
            </div>
            """),

            pn.pane.HTML(f"""
            <div style='background: #FFF3E0; border-left: 4px solid #F57C00; 
                        padding: 12px; border-radius: 4px; margin: 5px 0;'>
                <div style='color: #F57C00; font-weight: 600; font-size: 14px;'>Total Capacity</div>
                <div style='color: #E65100; font-size: 16px; font-weight: 700;'>
                    {capacity_mean:.4f} ± {capacity_std:.4f} Ah
                </div>
            </div>
            """)
        ]

        self.key_metrics_display.objects = cards
        self.key_metrics_display.visible = True

    def _clear_statistics(self):
        """Clear all statistics displays."""
        self.stats_info_display.object = """
        <div style='background: #F8F9FA; padding: 12px; border-radius: 4px; color: #666; text-align: center;'>
            <strong>No data loaded</strong><br>
            <small>Select cell and groups to view statistics</small>
        </div>
        """
        self.stats_table.value = []
        self.stats_table.visible = False
        self.key_metrics_display.objects = []
        self.key_metrics_display.visible = False

    def _setup_viz_connections(self):
        """Setup connections to visualization panel."""
        if hasattr(self.viz_panel, 'update_data'):
            # Connect data updates to visualization panel
            pass

    def _update_visualization(self, segments_data):
        """Update visualization panel with current data."""
        if hasattr(self.viz_panel, 'update_data'):
            self.viz_panel.update_data(segments_data)

    def _update_status(self, message: str, status_type: str = "info"):
        """Update status with professional styling."""
        if status_type == "success":
            color = "#2E7D32"
            icon = "✅"
        elif status_type == "warning":
            color = "#F57C00"
            icon = "⚠️"
        elif status_type == "error":
            color = "#D32F2F"
            icon = "❌"
        else:  # info
            color = "#1976D2"
            icon = "ℹ️"

        self.status_display.object = f"""
        <div style='color: {color}; font-size: 14px; padding: 8px; 
                    background: {color}15; border-radius: 4px; border-left: 3px solid {color};'>
            {icon} {message}
        </div>
        """

    # === MOCK API METHODS (REPLACE WITH REAL BACKEND) ===

    def _mock_get_cell_groups(self, cell_id):
        """Mock groups data - replace with real API call."""
        return [
            {
                'group_id': 'group_001',
                'name': 'GITT Rest Phases',
                'segment_count': 8,
                'created_at': '2025-08-20',
                'description': 'All rest phases from GITT experiments'
            },
            {
                'group_id': 'group_002',
                'name': 'EIS Measurements',
                'segment_count': 3,
                'created_at': '2025-08-20',
                'description': 'Impedance spectroscopy data'
            },
            {
                'group_id': 'group_003',
                'name': 'Formation Cycles',
                'segment_count': 12,
                'created_at': '2025-08-19',
                'description': 'Initial formation protocol'
            }
        ]

    def _mock_get_group_segments(self, group_id):
        """Mock group segments - replace with real API call."""
        if group_id == 'group_001':  # GITT Rest Phases
            return [
                {
                    'segment_id': 'seg_001',
                    'technique': 'REST',
                    'start_potential_v': 3.75,
                    'end_potential_v': 3.82,
                    'start_current_a': 0.001,
                    'end_current_a': 0.0005,
                    'duration_s': 300.0,
                    'capacity_ah': 0.0,
                    'energy_wh': 0.0,
                    'group_name': 'GITT Rest Phases'
                },
                {
                    'segment_id': 'seg_003',
                    'technique': 'REST',
                    'start_potential_v': 3.78,
                    'end_potential_v': 3.85,
                    'start_current_a': 0.0008,
                    'end_current_a': 0.0003,
                    'duration_s': 295.0,
                    'capacity_ah': 0.0,
                    'energy_wh': 0.0,
                    'group_name': 'GITT Rest Phases'
                }
            ]
        elif group_id == 'group_002':  # EIS Measurements
            return [
                {
                    'segment_id': 'seg_004',
                    'technique': 'EIS',
                    'start_potential_v': 3.83,
                    'end_potential_v': 3.83,
                    'start_current_a': 0.0,
                    'end_current_a': 0.0,
                    'duration_s': 120.0,
                    'capacity_ah': 0.0,
                    'energy_wh': 0.0,
                    'group_name': 'EIS Measurements'
                }
            ]
        elif group_id == 'group_003':  # Formation Cycles
            return [
                {
                    'segment_id': 'seg_005',
                    'technique': 'CC',
                    'start_potential_v': 3.0,
                    'end_potential_v': 4.2,
                    'start_current_a': 0.1,
                    'end_current_a': 0.1,
                    'duration_s': 3600.0,
                    'capacity_ah': 0.1,
                    'energy_wh': 0.37,
                    'group_name': 'Formation Cycles'
                },
                {
                    'segment_id': 'seg_006',
                    'technique': 'CC',
                    'start_potential_v': 4.2,
                    'end_potential_v': 3.0,
                    'start_current_a': -0.1,
                    'end_current_a': -0.1,
                    'duration_s': 3200.0,
                    'capacity_ah': -0.089,
                    'energy_wh': -0.31,
                    'group_name': 'Formation Cycles'
                }
            ]
        return []


# Usage example for integration with main app
if __name__ == "__main__":
    # Example of how to integrate with existing app

    class MockAPI:
        """Mock API for testing"""
        pass


    # Create component
    api = MockAPI()
    analysis_tab = DataAnalysisTab(api)

    # Set test cell
    analysis_tab.set_current_cell("CELL_001")

    # Create Panel app for testing
    pn.extension('tabulator')

    app = pn.Column(
        analysis_tab.panel,
        sizing_mode='stretch_width'
    )

    app.show(port=5009)