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
pn.extension('tabulator')

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
                print(f"DEBUG: Raw schema from API: {list(schema.keys())}")
                print(f"DEBUG: Looking for 'capacity_cumulative_ah' in raw schema: {'capacity_cumulative_ah' in schema}")
                
                # Filter out unwanted columns
                skip_columns = {
                    'created_at', 'updated_at', 'analysis_results', 'segment_metadata',
                    'original_filename',  # Hide the long filename
                    'file_id'  # Hide file_id - not needed for segment selection
                }

                filtered_schema = {k: v for k, v in schema.items() if k not in skip_columns}
                print(f"DEBUG: After filtering: {list(filtered_schema.keys())}")
                print(f"DEBUG: 'capacity_cumulative_ah' after filtering: {'capacity_cumulative_ah' in filtered_schema}")
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

        # First create a DataFrame with ALL segment data to preserve full columns
        raw_df = pd.DataFrame(segments)
        
        # Then format only the display columns according to schema
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

        formatted_df = pd.DataFrame(formatted_data)
        
        # Keep display columns for the tabulator, but add back all raw columns for plotting
        display_columns = list(self.segments_schema.keys())
        for col in raw_df.columns:
            if col not in display_columns:
                formatted_df[col] = raw_df[col]
        
        return formatted_df

    def _format_group_contents_data(self, segments: List[Dict]) -> pd.DataFrame:
        """Format group contents data - simplified view without file_id."""
        if not segments:
            return self._create_empty_segments_dataframe()

        # First create a DataFrame with ALL segment data to preserve full columns
        raw_df = pd.DataFrame(segments)

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

        formatted_df = pd.DataFrame(formatted_data)
        
        # Keep display columns for the tabulator, but add back all raw columns for plotting
        display_columns = [col for col in group_contents_schema.keys() if col in formatted_df.columns]
        for col in raw_df.columns:
            if col not in display_columns:
                formatted_df[col] = raw_df[col]
                
        return formatted_df if not formatted_df.empty else pd.DataFrame()

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

        # Single group selector with visual distinction between template and user groups
        self.group_selector = pn.widgets.Select(
            name="Available Groups",
            options=[("No groups available", "")],
            width=220,
            margin=(5, 5)
        )
        self.group_selector.param.watch(self._on_group_selected, 'value')
        
        # Keep track of selected group type for button enabling/disabling
        self.selected_group_is_template = False

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

        self.copy_group_btn = pn.widgets.Button(
            name="📋 Copy Group",
            button_type="primary",
            width=105,
            disabled=True,
            margin=(5, 5)
        )
        self.copy_group_btn.on_click(self._on_copy_group)

        self.delete_group_btn = pn.widgets.Button(
            name="🗑️ Delete",
            button_type="light",
            width=100,
            disabled=True,
            margin=(5, 5)
        )
        self.delete_group_btn.on_click(self._on_delete_group)

        # Refresh button for template groups
        self.refresh_groups_btn = pn.widgets.Button(
            name="🔄 Refresh Groups",
            button_type="light",
            width=220,
            margin=(5, 5)
        )
        self.refresh_groups_btn.on_click(self._on_refresh_groups)

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

        # Summary stats display
        self.summary_stats = pn.pane.HTML(
            self._create_empty_summary_html(),
            margin=(5, 5)
        )
        
        # Show empty plot initially (after all components are created)
        self._clear_preview()

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
            # Top section - Group Selection
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                🏷️ Group Selection
            </div>
            """),

            # Single group selector with visual distinction
            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555; font-size: 13px;'>Select Group:</label>"),
                self.group_selector,
                pn.pane.HTML("""
                <div style='font-size: 11px; color: #666; margin-top: 2px;'>
                    🔧 Template groups | 📁 User groups
                </div>
                """),
                margin=(5, 5)
            ),

            # Group action buttons
            pn.Row(
                self.copy_group_btn,
                self.delete_group_btn,
                margin=(5, 5)
            ),

            # Refresh button
            self.refresh_groups_btn,

            # Create new group section
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
        """Refresh groups dropdown with combined template and user groups."""
        if not self.current_cell:
            return

        try:
            # Get both template and user groups
            template_groups = self.api.get_template_groups(self.current_cell)
            user_groups = self.api.get_user_groups(self.current_cell)
            
            print(f"DEBUG UI: Retrieved {len(template_groups)} template + {len(user_groups)} user groups")
            
            # Build combined options list with visual distinction
            all_options = []
            
            # Add template groups first with 🔧 icon
            if template_groups:
                for group in template_groups:
                    count = group.get('segment_count', 0)
                    # Format: "🔧 Rest (62 segments)"
                    technique = self._extract_technique_from_template_name(group['group_name'])
                    display_name = f"🔧 {technique} ({count} segments)"
                    # Store group info in value: "template:group_id"
                    all_options.append((display_name, f"template:{group['group_id']}"))
                    print(f"DEBUG UI: Template group - {group['group_name']} → {display_name}")
            
            # Add separator if we have both types
            if template_groups and user_groups:
                all_options.append(("─" * 30, "separator"))
            
            # Add user groups with 📁 icon
            if user_groups:
                for group in user_groups:
                    count = group.get('segment_count', 0)
                    # Format: "📁 My Custom Group (15 segments)"
                    display_name = f"📁 {group['group_name']} ({count} segments)"
                    # Store group info in value: "user:group_id"
                    all_options.append((display_name, f"user:{group['group_id']}"))
                    print(f"DEBUG UI: User group - {group['group_name']} → {display_name}")
            
            # Set options or show empty message
            if all_options:
                self.group_selector.options = all_options
                self._update_status(f"Found {len(template_groups)} template + {len(user_groups)} user groups", "success")
            else:
                self.group_selector.options = [("No groups available", "")]
                self._update_status("No groups found - create your first group", "info")
            
            print(f"DEBUG UI: Set {len(all_options)} total options in group selector")
            
            # Apply initial selection (without causing recursion)
            self._apply_initial_group_selection()

        except Exception as e:
            print(f"DEBUG UI: Exception in _refresh_groups: {e}")
            import traceback
            traceback.print_exc()
            self.group_selector.options = [("Error loading groups", "")]
            self._update_status(f"Error loading groups: {str(e)}", "error")

    def _extract_technique_from_template_name(self, group_name: str) -> str:
        """
        Extract technique name from template group name.
        "Template_All_Rest" -> "Rest"
        """
        if group_name.startswith("Template_All_"):
            return group_name.replace("Template_All_", "")
        else:
            # Fallback for non-standard template names
            return group_name.replace("Template_", "")

    def _format_template_group_name(self, group_name: str, segment_count: int) -> str:
        """
        Convert template group name for display.
        "Template_All_Rest" -> "Rest (5 segments)"
        """
        if group_name.startswith("Template_All_"):
            technique = group_name.replace("Template_All_", "")
            return f"{technique} ({segment_count} segments)"
        else:
            # Fallback for non-standard template names
            return f"{group_name} ({segment_count} segments)"

    def _apply_initial_group_selection(self):
        """Apply initial selection logic: first user group OR first template group."""
        # Clear current selection first
        self._clear_group_selection()
        
        # Skip initial selection to avoid recursion - user can manually select
        print("DEBUG UI: Skipping initial selection to avoid recursion issues")
        return

    def _on_group_selected(self, event):
        """Handle group selection from the unified dropdown."""
        selection = event.new

        # Handle tuple from Select widget
        if isinstance(selection, tuple):
            selection = selection[1] if len(selection) > 1 else selection[0]

        print(f"DEBUG UI: Group selected: {selection}")
        
        if selection and selection != "" and selection != "separator":
            # Parse selection: "template:group_id" or "user:group_id"
            if ":" in selection:
                group_type, group_id = selection.split(":", 1)
                is_template = (group_type == "template")
                
                print(f"DEBUG UI: Parsed selection - Type: {group_type}, ID: {group_id}")
                
                # Store selection info
                self.selected_group_id = group_id
                self.selected_group_is_template = is_template
                
                # Refresh group contents and preview
                self._refresh_group_contents()
                self._update_preview()
                
                # Enable/disable buttons based on group type
                self.copy_group_btn.disabled = False  # Can copy both types
                self.delete_group_btn.disabled = is_template  # Can't delete template groups
                self.add_to_group_btn.disabled = is_template  # Can't add to template groups
                
                print(f"DEBUG UI: Buttons - Copy: {not self.copy_group_btn.disabled}, Delete: {not self.delete_group_btn.disabled}, Add: {not self.add_to_group_btn.disabled}")
            else:
                print(f"DEBUG UI: Invalid selection format: {selection}")
                self._clear_group_selection()
        else:
            self._clear_group_selection()

    def _handle_group_selection(self, group_id: str, is_template: bool):
        """Legacy method - now handled by _on_group_selected."""
        # This method is no longer used but kept for compatibility
        pass

    def _clear_group_selection(self):
        """Clear group selection and contents."""
        self.selected_group_id = ""
        self.group_contents_tabulator.value = self._create_empty_segments_dataframe()
        self.delete_group_btn.disabled = True
        self.copy_group_btn.disabled = True
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
        print(f"DEBUG: Plot type changed to: {event.new}")  # Debug output
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
            # Handle tuple from Select widget
            if isinstance(plot_type, tuple):
                plot_type = plot_type[1] if len(plot_type) > 1 else plot_type[0]
            print(f"DEBUG: Creating plot with type: {plot_type}")  # Debug output
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
                    summary_lines.append(f"├─ Voltage Range: {voltage_range}")
                    
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

        # Add plot legend explanation
        current_plot_type = getattr(self.plot_type_selector, 'value', 'voltage_boundaries')
        # Handle tuple from Select widget
        if isinstance(current_plot_type, tuple):
            current_plot_type = current_plot_type[1] if len(current_plot_type) > 1 else current_plot_type[0]
        plot_legend = self._get_plot_legend(current_plot_type)
        if plot_legend:
            summary_lines.append(f"<br><strong>Plot Legend:</strong>")
            summary_lines.append(plot_legend)

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

    def _get_plot_legend(self, plot_type: str) -> str:
        """Get legend explanation for current plot type."""
        legends = {
            'voltage_boundaries': "● = Start voltage, ▲ = End voltage (colored by technique)",
            'voltage_ranges': "Bar height = voltage span (start→end), colored by technique",
            'time_duration': "Point size = voltage range, colored by technique",
            'capacity_time': "Line shows cumulative capacity over time, colored by technique"
        }
        return legends.get(plot_type, "Colors indicate different techniques")

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
                print(f"DEBUG: Selected segments columns before plot: {list(selected_segments.columns)}")
                print(f"DEBUG: Schema keys available: {list(self.segments_schema.keys())}")
                print(f"DEBUG: capacity_cumulative_ah in schema? {'capacity_cumulative_ah' in self.segments_schema}")
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
        
        # Get technique for coloring and map to actual colors
        if 'fundamental_technique' in plot_df.columns:
            plot_df['color'] = plot_df['fundamental_technique'].apply(self._get_technique_color)
            color_by = 'fundamental_technique'  # Use categorical coloring
        else:
            plot_df['color'] = '#1976D2'  # Default color
            color_by = None
        
        # Create scatter plot for start voltages
        plot = plot_df.hvplot.scatter(
            x='time', y='start_v',
            by=color_by,  # Use 'by' for categorical coloring instead of 'color'
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
                by=color_by,
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
        
        # Handle coloring for bar plot
        if 'fundamental_technique' in plot_df.columns:
            color_by = 'fundamental_technique'
        else:
            color_by = None
        
        return plot_df.hvplot.bar(
            x='segment_idx', y='voltage_range',
            by=color_by,
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
        
        # Handle coloring for scatter plot
        if 'fundamental_technique' in plot_df.columns:
            color_by = 'fundamental_technique'
        else:
            color_by = None
        
        return plot_df.hvplot.scatter(
            x='time', y='duration',
            by=color_by,
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
        """Create cumulative capacity vs cumulative time plot."""
        if 'start_time_s' not in df.columns:
            return self._create_empty_plot("Missing time data")
        
        plot_df = df.copy()
        
        # Convert time columns to numeric
        plot_df['start_time'] = pd.to_numeric(plot_df['start_time_s'].astype(str).str.replace('s', ''), errors='coerce')
        if 'end_time_s' in plot_df.columns:
            plot_df['end_time'] = pd.to_numeric(plot_df['end_time_s'].astype(str).str.replace('s', ''), errors='coerce')
        else:
            # Fallback if end_time not available
            plot_df['end_time'] = plot_df['start_time']
        
        # Sort by start time for proper accumulation
        plot_df = plot_df.sort_values('start_time').reset_index(drop=True)
        
        # Calculate segment durations and accumulate time
        plot_df['duration'] = plot_df['end_time'] - plot_df['start_time']
        plot_df['cumulative_time'] = plot_df['duration'].cumsum()
        
        # Use cumulative capacity data
        print(f"DEBUG: Available columns in plot_df: {list(plot_df.columns)}")
        print(f"DEBUG: Looking for 'capacity_cumulative_ah', found: {'capacity_cumulative_ah' in plot_df.columns}")
        if 'capacity_cumulative_ah' in plot_df.columns:
            print(f"DEBUG: Sample capacity values: {plot_df['capacity_cumulative_ah'].head()}")
            plot_df['capacity'] = pd.to_numeric(plot_df['capacity_cumulative_ah'], errors='coerce')
            plot_df = plot_df.dropna(subset=['capacity', 'cumulative_time'])
            print(f"DEBUG: After processing, {len(plot_df)} rows remain")
        else:
            return self._create_empty_plot("No cumulative capacity data available")
        
        if plot_df.empty:
            return self._create_empty_plot("No valid capacity/time data")
        
        # Handle coloring for line plot
        if 'fundamental_technique' in plot_df.columns:
            color_by = 'fundamental_technique'
        else:
            color_by = None
        
        return plot_df.hvplot.line(
            x='cumulative_time', y='capacity',
            by=color_by,
            title="Cumulative Capacity vs Cumulative Time",
            xlabel="Cumulative Time (s)",
            ylabel="Cumulative Capacity (Ah)",
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

    def _on_copy_group(self, event):
        """Copy current group to a new user group."""
        if not self.selected_group_id:
            return

        try:
            result = self.api.copy_group(int(self.selected_group_id))

            if result.success:
                self._update_status(result.message, "success")
                self._refresh_groups()
                # Select the new group
                if hasattr(result, 'file_id') and result.file_id:
                    # Find and select the new group in unified dropdown (user groups have "user:" prefix)
                    new_group_value = f"user:{result.file_id}"
                    for option in self.group_selector.options:
                        if option[1] == new_group_value:
                            self.group_selector.value = option
                            break
            else:
                self._update_status(f"Error copying group: {result.error}", "error")

        except Exception as e:
            self._update_status(f"Error copying group: {str(e)}", "error")

    def _on_refresh_groups(self, event):
        """Refresh all template groups for all cells."""
        try:
            print("=== REFRESH GROUPS BUTTON CLICKED ===")
            self._update_status("Refreshing template groups...", "info")
            
            # Get all cells first to see what we're working with
            cells = self.api.get_cells()
            print(f"DEBUG: Found {len(cells)} cells in database:")
            for cell in cells:
                print(f"  - {cell['name']} (ID: {cell['id']})")
            
            # Call the refresh API
            print("DEBUG: Calling api.refresh_all_template_groups()...")
            result = self.api.refresh_all_template_groups()
            
            print(f"DEBUG: Refresh result - Success: {result.success}")
            if result.success:
                print(f"DEBUG: Refresh message: {result.message}")
                print(f"DEBUG: Groups created/updated: {result.file_id}")  # Contains count
                
                self._update_status(result.message, "success")
                
                # Check groups for current cell after refresh
                if self.current_cell:
                    print(f"DEBUG: Checking groups for current cell '{self.current_cell}'...")
                    groups_before = len(self.group_selector.options)
                    
                    self._refresh_groups()
                    
                    groups_after = len(self.group_selector.options)
                    print(f"DEBUG: Groups before: {groups_before}, after: {groups_after}")
                    
                    # Show what groups exist now
                    template_groups = self.api.get_template_groups(self.current_cell)
                    user_groups = self.api.get_user_groups(self.current_cell)
                    print(f"DEBUG: Current groups for '{self.current_cell}':")
                    print(f"  Template groups: {len(template_groups)}")
                    for group in template_groups:
                        print(f"    - {group['group_name']} ({group['segment_count']} segments)")
                    print(f"  User groups: {len(user_groups)}")
                    for group in user_groups:
                        print(f"    - {group['group_name']} ({group['segment_count']} segments)")
            else:
                print(f"DEBUG: Refresh failed: {result.error}")
                self._update_status(f"Error refreshing template groups: {result.error}", "error")

        except Exception as e:
            print(f"DEBUG: Exception in refresh: {str(e)}")
            import traceback
            traceback.print_exc()
            self._update_status(f"Error refreshing template groups: {str(e)}", "error")

    def _on_delete_group(self, event):
        """Delete current group (user groups only)."""
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