"""
Group Management Tab - Clean Implementation with Dropdown Groups

Modern 3-column layout with database-driven columns and dropdown group selection.
"""

import panel as pn
import param
import pandas as pd
import numpy as np
import hvplot.pandas
from typing import List, Dict, Any, Optional

# Ensure extensions are loaded
pn.extension('tabulator', 'bokeh')

class GroupManagementTab(param.Parameterized):
    """
    Professional group management component with clean dropdown-based design.

    Layout:
    - Left: Segments table (40%) - all segments with multi-select
    - Middle: Group management (25%) - dropdown + group contents table
    - Right: Real-time preview (35%) - visualization of selected segments
    """

    current_cell = param.String(default="", doc="Currently selected cell")
    selected_group_id = param.String(default="", doc="Currently selected group ID")
    status_message = param.String(default="", doc="Status message for main app")

    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api

        # Get dynamic schemas from database
        self.segments_schema = self._get_segments_schema()

        # Create components
        self._create_components()

        # Populate initial data
        self._populate_initial_data()

    def _get_segments_schema(self) -> Dict[str, Dict]:
        try:
            schema = self.api.get_segments_display_schema()
            if schema:
                # Filter out unwanted columns
                skip_columns = {
                    'created_at', 'updated_at', 'analysis_results', 'segment_metadata',
                    'original_filename',  # Hide the long filename
                    'file_id'  # Hide file_id - not needed for segment selection
                }

                filtered_schema = {k: v for k, v in schema.items() if k not in skip_columns}
                print(f"Loaded {len(filtered_schema)} columns (filtered from {len(schema)})")
                return filtered_schema
        except Exception as e:
            print(f"Failed to get segments schema: {e}")

        # Fallback minimal schema
        print("Using fallback schema")
        return {
            'id': {
                'display_name': 'ID',
                'formatter': lambda x: str(x) if x is not None else "",
                'width': 80
            },
            'fundamental_technique': {
                'display_name': 'Technique',
                'formatter': lambda x: str(x) if x is not None else "",
                'width': 120
            }
        }

    def _create_empty_segments_dataframe(self) -> pd.DataFrame:
        """Create empty DataFrame with proper columns from schema."""
        columns = list(self.segments_schema.keys())
        return pd.DataFrame(columns=columns)

    def _format_segments_data(self, segments: List[Dict]) -> pd.DataFrame:
        """Format segments data according to schema."""
        if not segments:
            return self._create_empty_segments_dataframe()

        formatted_data = []
        for segment in segments:
            row = {}
            for col_name, col_config in self.segments_schema.items():
                raw_value = segment.get(col_name)
                formatter = col_config.get('formatter', lambda x: str(x) if x is not None else "")

                try:
                    row[col_name] = formatter(raw_value)
                except Exception:
                    row[col_name] = str(raw_value) if raw_value is not None else ""

            formatted_data.append(row)

        df = pd.DataFrame(formatted_data)
        # Only keep columns that are in the schema
        return df[list(self.segments_schema.keys())]

    def _format_group_contents_data(self, segments: List[Dict]) -> pd.DataFrame:
        """Format group contents data - simplified view without file_id."""
        if not segments:
            return self._create_empty_segments_dataframe()

        # Define simplified schema for group contents (file-agnostic)
        group_contents_schema = {
            'id': self.segments_schema.get('id', {'formatter': str}),
            'fundamental_technique': self.segments_schema.get('fundamental_technique', {'formatter': str}),
            'start_time_s': self.segments_schema.get('start_time_s', {'formatter': str}),
            'duration_s': self.segments_schema.get('duration_s', {'formatter': str}),
            'start_potential_v': self.segments_schema.get('start_potential_v', {'formatter': str}),
            'end_potential_v': self.segments_schema.get('end_potential_v', {'formatter': str})
        }

        formatted_data = []
        for segment in segments:
            row = {}
            for col_name, col_config in group_contents_schema.items():
                if col_name in self.segments_schema:  # Only include if available in main schema
                    raw_value = segment.get(col_name)
                    formatter = col_config.get('formatter', lambda x: str(x) if x is not None else "")

                    try:
                        row[col_name] = formatter(raw_value)
                    except Exception:
                        row[col_name] = str(raw_value) if raw_value is not None else ""

            formatted_data.append(row)

        df = pd.DataFrame(formatted_data)
        # Only keep columns that exist in both schemas
        available_columns = [col for col in group_contents_schema.keys() if col in df.columns]
        return df[available_columns] if available_columns else pd.DataFrame()

    def _create_components(self):
        """Create all UI components."""

        # === TOP BAR: CELL SELECTOR ===
        self.cell_selector = pn.widgets.Select(
            name="Select Cell",
            options=[("No cells available", "")],
            width=300,
            margin=(5, 5)
        )
        self.cell_selector.param.watch(self._on_cell_selected, 'value')

        # === LEFT COLUMN: SEGMENTS TABLE ===
        self.segments_tabulator = pn.widgets.Tabulator(
            value=self._create_empty_segments_dataframe(),
            pagination='remote',
            page_size=20,
            sizing_mode='stretch_width',
            selectable='checkbox',
            sortable=True,
            show_index=False,
            configuration={
                'layout': 'fitData',
                'height': '600px',
                'placeholder': 'Select a cell to view segments...',
                # 'responsiveLayout': 'hide',
                'tooltips': True,
                'columnDefaults': {'tooltip': True}
            },
            height=600,
            margin=(5, 5)
        )

        # Watch for selection changes for real-time preview
        self.segments_tabulator.param.watch(self._on_segments_selection_changed, 'selection')

        # === MIDDLE COLUMN TOP: GROUP MANAGEMENT ===

        # Group selector dropdown
        self.group_selector = pn.widgets.Select(
            name="Select Group",
            options=[("No groups available", "")],
            width=220,
            margin=(5, 5)
        )
        self.group_selector.param.watch(self._on_group_selected, 'value')

        # New group creation
        self.new_group_name = pn.widgets.TextInput(
            placeholder="New group name...",
            width=220,
            margin=(5, 5)
        )

        self.new_group_desc = pn.widgets.TextInput(
            placeholder="Description (optional)...",
            width=220,
            margin=(5, 5)
        )

        self.create_group_btn = pn.widgets.Button(
            name="📂 Create Group",
            button_type="primary",
            width=110,
            margin=(5, 5)
        )
        self.create_group_btn.on_click(self._on_create_group)

        self.delete_group_btn = pn.widgets.Button(
            name="🗑️ Delete",
            button_type="light",
            width=100,
            disabled=True,
            margin=(5, 5)
        )
        self.delete_group_btn.on_click(self._on_delete_group)

        # Group action buttons
        self.add_to_group_btn = pn.widgets.Button(
            name="➕ Add Selected",
            button_type="primary",
            width=220,
            disabled=True,
            margin=(10, 5)
        )
        self.add_to_group_btn.on_click(self._on_add_to_group)

        # === MIDDLE COLUMN BOTTOM: GROUP CONTENTS TABLE ===
        self.group_contents_tabulator = pn.widgets.Tabulator(
            value=self._create_empty_segments_dataframe(),
            pagination='remote',
            page_size=15,
            sizing_mode='stretch_width',
            selectable='checkbox',
            sortable=True,
            show_index=False,
            configuration={
                'layout': 'fitColumns',
                'height': '300px',
                'placeholder': 'Select a group to view contents...',
                'responsiveLayout': 'hide',
                'tooltips': True
            },
            height=300,
            margin=(5, 5)
        )
        
        # Watch for selection changes in group contents for real-time preview
        self.group_contents_tabulator.param.watch(self._on_group_contents_selection_changed, 'selection')

        self.remove_from_group_btn = pn.widgets.Button(
            name="➖ Remove Selected",
            button_type="light",
            width=220,
            disabled=True,
            margin=(5, 5)
        )
        self.remove_from_group_btn.on_click(self._on_remove_from_group)

        # === RIGHT COLUMN: REAL-TIME PREVIEW ===

        # Plot type selector
        self.plot_type_selector = pn.widgets.Select(
            name="Visualization",
            options=[
                ("Voltage Boundaries vs Time", "voltage_boundaries"),
                ("Voltage Range Bars", "voltage_ranges"),
                ("Time vs Duration Scatter", "time_duration"),
                ("Capacity vs Time", "capacity_time")
            ],
            value="voltage_boundaries",
            width=250,
            margin=(5, 5)
        )
        self.plot_type_selector.param.watch(self._on_plot_type_changed, 'value')

        # Preview plot area
        self.preview_plot = pn.pane.HoloViews(
            None,
            sizing_mode='stretch_width',
            height=350,
            margin=(5, 5)
        )
        
        # Show empty plot initially
        self._clear_preview()

        # Summary stats display
        self.summary_stats = pn.pane.HTML(
            self._create_empty_summary_html(),
            margin=(5, 5)
        )

        # Status display
        self.status_display = pn.pane.HTML(
            "<div style='color: #2E7D32; font-size: 14px; padding: 5px;'>✅ Ready for group management</div>",
            margin=(5, 5)
        )

    def _create_empty_preview_html(self) -> str:
        """Create empty preview plot HTML."""
        return """
        <div style='background: #FAFAFA; padding: 40px; border-radius: 4px; 
                    height: 300px; border: 1px solid #E0E0E0; text-align: center;
                    display: flex; flex-direction: column; justify-content: center;'>
            <div style='font-size: 48px; opacity: 0.3; margin-bottom: 20px;'>📊</div>
            <div style='color: #666; font-size: 16px; font-weight: 500;'>Select segments to see preview</div>
            <div style='color: #999; font-size: 14px; margin-top: 10px;'>Voltage boundaries, timing, and technique analysis</div>
        </div>
        """

    def _create_empty_summary_html(self) -> str:
        """Create empty summary stats HTML."""
        return """
        <div style='background: #F8F9FA; padding: 12px; border-radius: 4px; 
                    border: 1px solid #E0E0E0;'>
            <strong>Current Selection:</strong> No segments selected
        </div>
        """

    @property
    def panel(self):
        """Return the complete 3-column layout."""

        # Header
        header = pn.pane.HTML("""
        <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white; 
                    padding: 15px; border-radius: 8px 8px 0 0; margin: 0;'>
            <h2 style='margin: 0; font-size: 18px; font-weight: 600;'>
                🔗 Group Management
            </h2>
        </div>
        """, margin=(0, 0))

        # Top bar with cell selector
        top_bar = pn.Row(
            pn.pane.HTML("""
            <label style='font-weight: 600; color: #2E4057; margin-right: 10px; 
                          line-height: 30px; font-size: 14px;'>
                Cell:
            </label>
            """),
            self.cell_selector,
            pn.Spacer(),
            margin=(15, 15)
        )

        # Left column - Segments Table
        left_column = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                📋 All Segments
            </div>
            """),

            pn.pane.HTML("""
            <div style='font-size: 12px; color: #666; margin: 5px; padding: 8px;
                        background: #F8F9FA; border-radius: 4px;'>
                Select segments using checkboxes to add them to groups or view in preview.
            </div>
            """),

            self.segments_tabulator,

            # width=450,
            sizing_mode = 'stretch_width',
            margin=(10, 5),
            width_policy='max'
        )

        # Middle column - Group Management
        middle_column = pn.Column(
            # Top section - Group Operations
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                🏷️ Group Operations
            </div>
            """),

            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555; font-size: 13px;'>Select Group:</label>"),
                self.group_selector,
                margin=(5, 5)
            ),

            pn.Row(
                self.delete_group_btn,
                pn.Spacer(),
                margin=(5, 5)
            ),

            pn.pane.HTML("""
            <div style='color: #666; font-size: 13px; font-weight: 500; 
                        margin: 15px 5px 5px 5px; padding-top: 10px; 
                        border-top: 1px solid #E0E0E0;'>
                Create New Group
            </div>
            """),

            self.new_group_name,
            self.new_group_desc,

            pn.Row(
                self.create_group_btn,
                pn.Spacer(),
                margin=(10, 5)
            ),

            self.add_to_group_btn,

            # Bottom section - Group Contents
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                📄 Group Contents
            </div>
            """),

            self.group_contents_tabulator,
            self.remove_from_group_btn,

            # width=280,
            sizing_mode = 'stretch_width',
            margin=(10, 5),
            width_policy='min',
        )

        # Right column - Preview
        right_column = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                📈 Real-time Preview
            </div>
            """),

            self.plot_type_selector,
            self.preview_plot,
            self.summary_stats,

            # width=350,
            sizing_mode = 'stretch_width',
            margin=(10, 5),
            width_policy='fit'
        )

        # Main content
        main_content = pn.Row(
            left_column,
            middle_column,
            right_column,
            sizing_mode='stretch_width'
        )

        # Complete layout
        card_content = pn.Column(
            top_bar,
            main_content,
            self.status_display,
            styles={'background': 'white', 'border-radius': '0 0 8px 8px',
                   'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'margin': '0'}
        )

        return pn.Column(
            header,
            card_content,
            margin=(10, 10),
            styles={'border-radius': '8px', 'overflow': 'hidden'}
        )

    def _populate_initial_data(self):
        """Populate initial data - cell dropdown."""
        try:
            cells = self.api.get_cells()

            if cells and len(cells) > 0:
                # Format cell options with summary info
                options = []
                for cell in cells:
                    chemistry = cell.get('chemistry', 'Unknown')
                    display_name = f"{cell['name']} ({chemistry})"
                    options.append((display_name, cell['name']))

                self.cell_selector.options = options
                self._update_status(f"Found {len(cells)} cells", "success")
            else:
                self.cell_selector.options = [("No cells available", "")]
                self._update_status("No cells found - create cells first", "info")

        except Exception as e:
            self.cell_selector.options = [("Error loading cells", "")]
            self._update_status(f"Error loading cells: {str(e)}", "error")

    def _on_cell_selected(self, event):
        """Handle cell selection."""
        cell_name = event.new

        # Handle tuple from Select widget
        if isinstance(cell_name, tuple):
            cell_name = cell_name[1] if len(cell_name) > 1 else cell_name[0]

        if cell_name and cell_name != "":
            self.current_cell = cell_name
            self._refresh_segments()
            self._refresh_groups()
            self._clear_group_selection()
            self._update_status(f"Selected cell: {cell_name}", "success")
        else:
            self.current_cell = ""
            self.segments_tabulator.value = self._create_empty_segments_dataframe()
            self._clear_groups()
            self._clear_preview()
            self._update_status("No cell selected", "info")

    def _refresh_segments(self):
        """Refresh segments table for current cell."""
        if not self.current_cell:
            return

        try:
            segments = self.api.get_cell_segments(self.current_cell)
            formatted_df = self._format_segments_data(segments)
            self.segments_tabulator.value = formatted_df

            print(f"Loaded segments with columns: {list(formatted_df.columns)}")
            self._update_status(f"Loaded {len(segments)} segments", "success")

        except Exception as e:
            self.segments_tabulator.value = self._create_empty_segments_dataframe()
            self._update_status(f"Error loading segments: {str(e)}", "error")
        formatted_df = self._format_segments_data(segments)
        print(f"DEBUG: About to assign DF with columns: {list(formatted_df.columns)}")
        print(f"DEBUG: DF shape: {formatted_df.shape}")
        if not formatted_df.empty:
            print(f"DEBUG: First row sample: {formatted_df.iloc[0].to_dict()}")

        self.segments_tabulator.value = formatted_df
    def _refresh_groups(self):
        """Refresh groups dropdown for current cell."""
        if not self.current_cell:
            return

        try:
            groups = self.api.get_cell_groups_with_counts(self.current_cell)

            if groups and len(groups) > 0:
                options = []
                for group in groups:
                    count = group.get('segment_count', 0)
                    display_name = f"{group['group_name']} ({count} segments)"
                    options.append((display_name, str(group['group_id'])))

                self.group_selector.options = options
                self._update_status(f"Found {len(groups)} groups", "success")
            else:
                self.group_selector.options = [("No groups available", "")]
                self._update_status("No groups found - create your first group", "info")

        except Exception as e:
            self.group_selector.options = [("Error loading groups", "")]
            self._update_status(f"Error loading groups: {str(e)}", "error")

    def _on_group_selected(self, event):
        """Handle group selection."""
        group_id = event.new

        # Handle tuple from Select widget
        if isinstance(group_id, tuple):
            group_id = group_id[1] if len(group_id) > 1 else group_id[0]

        if group_id and group_id != "":
            self.selected_group_id = group_id
            self._refresh_group_contents()
            self.delete_group_btn.disabled = False
            self.add_to_group_btn.disabled = False
            # Update preview to show entire group
            self._update_preview()
        else:
            self._clear_group_selection()

    def _clear_group_selection(self):
        """Clear group selection and contents."""
        self.selected_group_id = ""
        self.group_contents_tabulator.value = self._create_empty_segments_dataframe()
        self.delete_group_btn.disabled = True
        self.add_to_group_btn.disabled = True
        self.remove_from_group_btn.disabled = True

    def _refresh_group_contents(self):
        """Refresh group contents table."""
        if not self.selected_group_id:
            return

        try:
            segments = self.api.get_group_segments(int(self.selected_group_id))
            formatted_df = self._format_group_contents_data(segments)  # Use file-agnostic formatting
            self.group_contents_tabulator.value = formatted_df

            self.remove_from_group_btn.disabled = len(segments) == 0

        except Exception as e:
            self.group_contents_tabulator.value = self._create_empty_segments_dataframe()
            self._update_status(f"Error loading group contents: {str(e)}", "error")

    def _clear_groups(self):
        """Clear groups dropdown and contents."""
        self.group_selector.options = [("No groups available", "")]
        self._clear_group_selection()

    def _on_segments_selection_changed(self, event):
        """Handle changes in segment selection for real-time preview."""
        self._update_preview()
        
    def _on_group_contents_selection_changed(self, event):
        """Handle changes in group contents selection for real-time preview."""
        self._update_preview()

    def _on_plot_type_changed(self, event):
        """Handle plot type change."""
        self._update_preview()

    def _update_preview(self):
        """Update the preview plot and summary stats."""
        try:
            # Check for selections in both tables
            # Priority: Group Contents selection > All Segments selection > Entire Group
            
            group_contents_selection = self.group_contents_tabulator.selection
            all_segments_selection = self.segments_tabulator.selection
            
            selected_segments = None
            selection_context = ""
            
            if group_contents_selection:
                # User selected specific segments within a group
                df = self.group_contents_tabulator.value
                if df is not None and not df.empty:
                    selected_segments = df.iloc[group_contents_selection]
                    selection_context = f"Selected {len(selected_segments)} segments from group"
            elif all_segments_selection:
                # User selected segments from all segments table
                df = self.segments_tabulator.value
                if df is not None and not df.empty:
                    selected_segments = df.iloc[all_segments_selection]
                    selection_context = f"Selected {len(selected_segments)} segments from all"
            elif self.selected_group_id:
                # Show entire group when group is selected but no specific segments
                df = self.group_contents_tabulator.value
                if df is not None and not df.empty:
                    selected_segments = df
                    selection_context = f"Entire group ({len(selected_segments)} segments)"
            
            if selected_segments is None or selected_segments.empty:
                self._clear_preview()
                return

            # Update summary stats with context
            self._update_summary_stats(selected_segments, selection_context)

            # Create plot preview
            plot_type = self.plot_type_selector.value
            self._create_preview_plot(selected_segments, plot_type)

        except Exception as e:
            self._update_status(f"Error updating preview: {str(e)}", "error")

    def _update_summary_stats(self, selected_segments: pd.DataFrame, context: str = ""):
        """Update summary statistics display with context awareness."""
        if selected_segments.empty:
            self.summary_stats.object = self._create_empty_summary_html()
            return

        # Count by technique
        technique_counts = {}
        if 'fundamental_technique' in selected_segments.columns:
            technique_counts = selected_segments['fundamental_technique'].value_counts().to_dict()

        # Build summary with context
        if context:
            summary_lines = [f"<strong>{context}</strong>"]
        else:
            summary_lines = [f"<strong>Current Selection:</strong> {len(selected_segments)} segments"]

        for technique, count in technique_counts.items():
            color = self._get_technique_color(technique)
            summary_lines.append(f"├─ {technique}: {count} segments <span style='color: {color}; font-size: 16px;'>●</span>")

        # Add ranges if available
        try:
            if 'start_time_s' in selected_segments.columns:
                time_values = pd.to_numeric(selected_segments['start_time_s'].astype(str).str.replace('s', ''), errors='coerce')
                if not time_values.isna().all():
                    time_range = f"{time_values.min():.0f}s - {time_values.max():.0f}s"
                    summary_lines.append(f"├─ Time Span: {time_range}")

            if 'start_potential_v' in selected_segments.columns:
                voltage_values = pd.to_numeric(selected_segments['start_potential_v'].astype(str).str.replace('V', ''), errors='coerce')
                if not voltage_values.isna().all():
                    voltage_range = f"{voltage_values.min():.3f}V - {voltage_values.max():.3f}V"
                    summary_lines.append(f"└─ Voltage Range: {voltage_range}")
                    
            # Add duration info if available
            if 'duration_s' in selected_segments.columns:
                duration_values = pd.to_numeric(selected_segments['duration_s'].astype(str).str.replace('s', ''), errors='coerce')
                if not duration_values.isna().all():
                    total_duration = duration_values.sum()
                    avg_duration = duration_values.mean()
                    summary_lines.append(f"├─ Total Duration: {total_duration:.0f}s")
                    summary_lines.append(f"└─ Average Duration: {avg_duration:.0f}s")
        except Exception:
            pass  # Skip ranges if parsing fails

        summary_html = f"""
        <div style='background: #E3F2FD; padding: 12px; border-radius: 4px; 
                    border: 1px solid #1976D2; border-left: 4px solid #1976D2;'>
            {('<br>'.join(summary_lines))}
        </div>
        """

        self.summary_stats.object = summary_html

    def _get_technique_color(self, technique: str) -> str:
        """Get color for technique type."""
        color_map = {
            'REST': '#1976D2',
            'CC': '#2E8B57',
            'GALVANOSTATIC': '#2E8B57',
            'EIS': '#9932CC',
            'CV': '#FF6347',
            'POTENTIOSTATIC': '#FFD700'
        }
        return color_map.get(technique, '#666666')

    def _create_preview_plot(self, selected_segments: pd.DataFrame, plot_type: str):
        """Create actual hvplot visualization."""
        try:
            if selected_segments.empty:
                self._clear_preview()
                return
            
            # Create plot based on type
            if plot_type == "voltage_boundaries":
                plot = self._create_voltage_boundaries_plot(selected_segments)
            elif plot_type == "voltage_ranges":
                plot = self._create_voltage_ranges_plot(selected_segments)
            elif plot_type == "time_duration":
                plot = self._create_time_duration_plot(selected_segments)
            elif plot_type == "capacity_time":
                plot = self._create_capacity_time_plot(selected_segments)
            else:
                plot = self._create_voltage_boundaries_plot(selected_segments)  # Default
            
            self.preview_plot.object = plot
            
        except Exception as e:
            self._update_status(f"Error creating plot: {str(e)}", "error")
            self._clear_preview()

    def _create_voltage_boundaries_plot(self, df: pd.DataFrame):
        """Create voltage boundaries vs time plot."""
        # Prepare data for plotting
        if 'start_time_s' not in df.columns or 'start_potential_v' not in df.columns:
            return self._create_empty_plot("Missing voltage/time data")
        
        # Convert columns to numeric, handling string values
        plot_df = df.copy()
        plot_df['time'] = pd.to_numeric(plot_df['start_time_s'].astype(str).str.replace('s', ''), errors='coerce')
        plot_df['start_v'] = pd.to_numeric(plot_df['start_potential_v'].astype(str).str.replace('V', ''), errors='coerce')
        
        if 'end_potential_v' in df.columns:
            plot_df['end_v'] = pd.to_numeric(plot_df['end_potential_v'].astype(str).str.replace('V', ''), errors='coerce')
        else:
            plot_df['end_v'] = plot_df['start_v']  # Fallback
        
        # Remove rows with NaN values
        plot_df = plot_df.dropna(subset=['time', 'start_v'])
        
        if plot_df.empty:
            return self._create_empty_plot("No valid voltage/time data")
        
        # Get technique for coloring
        technique_col = 'fundamental_technique' if 'fundamental_technique' in plot_df.columns else None
        
        # Create scatter plot for start voltages
        plot = plot_df.hvplot.scatter(
            x='time', y='start_v',
            color=technique_col,
            size=60,
            alpha=0.7,
            title="Voltage Boundaries vs Time",
            xlabel="Time (s)",
            ylabel="Potential (V)",
            legend='top_right',
            width=400,
            height=300
        )
        
        # Add end voltages if available and different
        if 'end_v' in plot_df.columns and not plot_df['end_v'].equals(plot_df['start_v']):
            end_plot = plot_df.hvplot.scatter(
                x='time', y='end_v',
                color=technique_col,
                size=40,
                alpha=0.5,
                marker='triangle'
            )
            plot = plot * end_plot
        
        return plot

    def _create_voltage_ranges_plot(self, df: pd.DataFrame):
        """Create voltage range bars plot."""
        if 'start_potential_v' not in df.columns:
            return self._create_empty_plot("Missing voltage data")
        
        plot_df = df.copy()
        plot_df['start_v'] = pd.to_numeric(plot_df['start_potential_v'].astype(str).str.replace('V', ''), errors='coerce')
        
        if 'end_potential_v' in df.columns:
            plot_df['end_v'] = pd.to_numeric(plot_df['end_potential_v'].astype(str).str.replace('V', ''), errors='coerce')
            plot_df['voltage_range'] = abs(plot_df['end_v'] - plot_df['start_v'])
        else:
            plot_df['voltage_range'] = 0.01  # Small default range
        
        plot_df = plot_df.dropna(subset=['start_v'])
        
        if plot_df.empty:
            return self._create_empty_plot("No valid voltage data")
        
        plot_df['segment_idx'] = range(len(plot_df))
        technique_col = 'fundamental_technique' if 'fundamental_technique' in plot_df.columns else None
        
        return plot_df.hvplot.bar(
            x='segment_idx', y='voltage_range',
            color=technique_col,
            title="Voltage Ranges by Segment",
            xlabel="Segment Index",
            ylabel="Voltage Range (V)",
            legend='top_right',
            width=400,
            height=300
        )

    def _create_time_duration_plot(self, df: pd.DataFrame):
        """Create time vs duration scatter plot."""
        if 'start_time_s' not in df.columns or 'duration_s' not in df.columns:
            return self._create_empty_plot("Missing time/duration data")
        
        plot_df = df.copy()
        plot_df['time'] = pd.to_numeric(plot_df['start_time_s'].astype(str).str.replace('s', ''), errors='coerce')
        plot_df['duration'] = pd.to_numeric(plot_df['duration_s'].astype(str).str.replace('s', ''), errors='coerce')
        
        plot_df = plot_df.dropna(subset=['time', 'duration'])
        
        if plot_df.empty:
            return self._create_empty_plot("No valid time/duration data")
        
        # Size by voltage range if available
        if 'start_potential_v' in plot_df.columns and 'end_potential_v' in plot_df.columns:
            plot_df['start_v'] = pd.to_numeric(plot_df['start_potential_v'].astype(str).str.replace('V', ''), errors='coerce')
            plot_df['end_v'] = pd.to_numeric(plot_df['end_potential_v'].astype(str).str.replace('V', ''), errors='coerce')
            plot_df['size'] = abs(plot_df['end_v'] - plot_df['start_v']) * 1000 + 50  # Scale for visibility
        else:
            plot_df['size'] = 100
        
        technique_col = 'fundamental_technique' if 'fundamental_technique' in plot_df.columns else None
        
        return plot_df.hvplot.scatter(
            x='time', y='duration',
            color=technique_col,
            size='size',
            alpha=0.7,
            title="Duration vs Start Time",
            xlabel="Start Time (s)",
            ylabel="Duration (s)",
            legend='top_right',
            width=400,
            height=300
        )

    def _create_capacity_time_plot(self, df: pd.DataFrame):
        """Create capacity vs time plot."""
        # This is a placeholder since capacity is computed during analysis
        if 'start_time_s' not in df.columns:
            return self._create_empty_plot("Missing time data")
        
        plot_df = df.copy()
        plot_df['time'] = pd.to_numeric(plot_df['start_time_s'].astype(str).str.replace('s', ''), errors='coerce')
        plot_df = plot_df.dropna(subset=['time'])
        
        if plot_df.empty:
            return self._create_empty_plot("No valid time data")
        
        # Create dummy capacity data (this would come from analysis in real implementation)
        plot_df['capacity'] = np.cumsum(np.random.normal(0.1, 0.05, len(plot_df)))
        technique_col = 'fundamental_technique' if 'fundamental_technique' in plot_df.columns else None
        
        return plot_df.hvplot.line(
            x='time', y='capacity',
            color=technique_col,
            title="Capacity vs Time (Placeholder)",
            xlabel="Time (s)",
            ylabel="Capacity (Ah)",
            legend='top_right',
            width=400,
            height=300
        )

    def _create_empty_plot(self, message: str = "No data to display"):
        """Create empty plot with message."""
        import holoviews as hv
        return hv.Text(0.5, 0.5, message).opts(
            width=400, height=300,
            xaxis=None, yaxis=None,
            title="Preview Plot"
        )

    def _clear_preview(self):
        """Clear preview plot and summary."""
        self.preview_plot.object = self._create_empty_plot("Select segments to see preview")
        self.summary_stats.object = self._create_empty_summary_html()

    # Group management methods
    def _on_create_group(self, event):
        """Create new group."""
        name = self.new_group_name.value.strip()
        if not name:
            self._update_status("Please enter a group name", "warning")
            return

        if not self.current_cell:
            self._update_status("Please select a cell first", "warning")
            return

        try:
            description = self.new_group_desc.value.strip()
            result = self.api.create_group(self.current_cell, name, description)

            if result.success:
                self._update_status(f"Created group: {name}", "success")
                self.new_group_name.value = ""
                self.new_group_desc.value = ""
                self._refresh_groups()
                # Select the new group
                if hasattr(result, 'file_id') and result.file_id:
                    self.group_selector.value = str(result.file_id)
            else:
                self._update_status(f"Error creating group: {result.error}", "error")

        except Exception as e:
            self._update_status(f"Error creating group: {str(e)}", "error")

    def _on_add_to_group(self, event):
        """Add selected segments to current group."""
        if not self.selected_group_id:
            self._update_status("Please select a group first", "warning")
            return

        selected_indices = self.segments_tabulator.selection
        if not selected_indices:
            self._update_status("Please select segments to add", "warning")
            return

        try:
            # Get segment IDs from selected rows
            df = self.segments_tabulator.value
            if df.empty:
                self._update_status("No segment data available", "error")
                return

            selected_segments = df.iloc[selected_indices]
            segment_ids = selected_segments['id'].tolist()

            result = self.api.add_segments_to_group(int(self.selected_group_id), segment_ids)

            if result.success:
                self._update_status(f"Added {len(segment_ids)} segments to group", "success")
                self._refresh_group_contents()
                self._refresh_groups()  # Update counts
                self.segments_tabulator.selection = []  # Clear selection
            else:
                self._update_status(f"Error adding segments: {result.error}", "error")

        except Exception as e:
            self._update_status(f"Error adding segments: {str(e)}", "error")

    def _on_remove_from_group(self, event):
        """Remove selected segments from current group."""
        if not self.selected_group_id:
            return

        selected_indices = self.group_contents_tabulator.selection
        if not selected_indices:
            self._update_status("Please select segments to remove", "warning")
            return

        try:
            # Get segment IDs from selected rows in group contents
            df = self.group_contents_tabulator.value
            if df.empty:
                self._update_status("No group content data available", "error")
                return

            selected_segments = df.iloc[selected_indices]
            segment_ids = selected_segments['id'].tolist()

            result = self.api.remove_segments_from_group(int(self.selected_group_id), segment_ids)

            if result.success:
                self._update_status(f"Removed {len(segment_ids)} segments from group", "success")
                self._refresh_group_contents()
                self._refresh_groups()  # Update counts
            else:
                self._update_status(f"Error removing segments: {result.error}", "error")

        except Exception as e:
            self._update_status(f"Error removing segments: {str(e)}", "error")

    def _on_delete_group(self, event):
        """Delete current group."""
        if not self.selected_group_id:
            return

        try:
            result = self.api.delete_group(int(self.selected_group_id))

            if result.success:
                self._update_status(f"Deleted group", "success")
                self._clear_group_selection()
                self._refresh_groups()
            else:
                self._update_status(f"Error deleting group: {result.error}", "error")

        except Exception as e:
            self._update_status(f"Error deleting group: {str(e)}", "error")

    def _update_status(self, message: str, status_type: str = "info"):
        """Update status with professional styling."""
        colors = {
            "success": ("#2E7D32", "✅"),
            "warning": ("#F57C00", "⚠️"),
            "error": ("#D32F2F", "❌"),
            "info": ("#1976D2", "ℹ️")
        }

        color, icon = colors.get(status_type, colors["info"])

        self.status_display.object = f"""
        <div style='color: {color}; font-size: 14px; padding: 8px; 
                    background: {color}15; border-radius: 4px; border-left: 3px solid {color};'>
            {icon} {message}
        </div>
        """


# Usage example for testing
if __name__ == "__main__":
    # Create mock API for testing
    class MockAPI:
        def get_cells(self):
            return [
                {'name': 'CELL_001', 'chemistry': 'Li_ion'},
                {'name': 'CELL_002', 'chemistry': 'NMC'}
            ]

        def get_segments_display_schema(self):
            return {
                'id': {'display_name': 'ID', 'formatter': lambda x: str(x) if x else "", 'width': 80},
                'fundamental_technique': {'display_name': 'Technique', 'formatter': lambda x: str(x) if x else "", 'width': 120},
                'start_time_s': {'display_name': 'Start Time', 'formatter': lambda x: f"{x:.0f}s" if x else "N/A", 'width': 100},
                'duration_s': {'display_name': 'Duration', 'formatter': lambda x: f"{x:.1f}s" if x else "N/A", 'width': 100},
                'start_potential_v': {'display_name': 'Start V', 'formatter': lambda x: f"{x:.3f}V" if x else "N/A", 'width': 100},
                'end_potential_v': {'display_name': 'End V', 'formatter': lambda x: f"{x:.3f}V" if x else "N/A", 'width': 100}
            }

        def get_cell_segments(self, cell_name):
            return [
                {'id': 1, 'fundamental_technique': 'REST', 'start_time_s': 0, 'duration_s': 300, 'start_potential_v': 3.75, 'end_potential_v': 3.82},
                {'id': 2, 'fundamental_technique': 'CC', 'start_time_s': 300, 'duration_s': 10, 'start_potential_v': 3.82, 'end_potential_v': 3.75},
                {'id': 3, 'fundamental_technique': 'EIS', 'start_time_s': 310, 'duration_s': 120, 'start_potential_v': 3.75, 'end_potential_v': 3.75}
            ]

        def get_cell_groups_with_counts(self, cell_name):
            return [
                {'group_id': 1, 'group_name': 'GITT Rest', 'segment_count': 2},
                {'group_id': 2, 'group_name': 'EIS Data', 'segment_count': 1}
            ]

        def get_group_segments(self, group_id):
            if group_id == 1:
                return [{'id': 1, 'fundamental_technique': 'REST', 'start_time_s': 0, 'duration_s': 300, 'start_potential_v': 3.75, 'end_potential_v': 3.82}]
            return []

        def create_group(self, cell_name, name, description):
            class Result:
                success = True
                error = None
                file_id = "3"
            return Result()

        def delete_group(self, group_id):
            class Result:
                success = True
                error = None
            return Result()

        def add_segments_to_group(self, group_id, segment_ids):
            class Result:
                success = True
                error = None
            return Result()

        def remove_segments_from_group(self, group_id, segment_ids):
            class Result:
                success = True
                error = None
            return Result()

    # Test the component
    api = MockAPI()
    tab = GroupManagementTab(api)

    app = pn.Column(
        tab.panel,
        sizing_mode='stretch_width'
    )

    app.show(port=5011)