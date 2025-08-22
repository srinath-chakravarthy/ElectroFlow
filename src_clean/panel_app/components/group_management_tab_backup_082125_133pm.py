"""
Professional Group Management Tab - Two-Tabulator Interface with Independent Cell Selection

Clean group organization interface with professional styling matching existing components.
"""

import panel as pn
import param
import pandas as pd
from typing import List, Dict, Any, Optional
pn.extension('tabulator')

class GroupManagementTab(param.Parameterized):
    """
    Professional group management component with two-tabulator design.

    Features:
    - Independent cell selection within tab
    - Panel 1: All segments with multi-selection and highlighting
    - Panel 2: Group contents with management controls
    - Professional styling consistent with existing interface
    - Database-driven operations (replace mock calls with real API)
    """

    current_cell = param.String(default="", doc="Currently selected cell")
    selected_group = param.String(default="", doc="Currently selected group ID")
    status_message = param.String(default="", doc="Status message for main app")

    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        self.current_group_segments = set()  # Cache for highlighting
        self._create_components()

        self._populate_initial_data()

    def _create_components(self):
        """Create professional UI components."""

        # === CELL SELECTION ===

        self.cell_selector = pn.widgets.Select(
            name="Select Cell",
            options=[],
            width=200,
            margin=(5, 5)
        )
        self.cell_selector.param.watch(self._on_cell_selected, 'value')

        # === PANEL 1: ALL SEGMENTS ===

        # Segments tabulator (all segments from current cell)
        self.segments_tabulator = pn.widgets.Tabulator(
            value=[],  # Will be populated when cell is selected
            pagination='remote',
            page_size=25,
            sizing_mode='stretch_width',
            selectable='checkbox',
            sortable=True,
            show_index=False,
            configuration={
                'layout': 'fitColumns',
                'height': '400px',
                'placeholder': 'Select a cell to view segments...',
                'responsiveLayout': 'hide',
                'tooltips': True,
                'columnDefaults': {
                    'tooltip': True
                }
            },
            height=400,
            margin=(5, 5)
        )

        # Panel 1 controls
        self.show_group_btn = pn.widgets.Button(
            name="👁️ Show Group",
            button_type="light",
            width=120,
            disabled=True,
            margin=(5, 5)
        )
        self.show_group_btn.on_click(self._on_show_group)

        self.add_to_group_btn = pn.widgets.Button(
            name="➕ Add Selected",
            button_type="primary",
            width=130,
            disabled=True,
            margin=(5, 5)
        )
        self.add_to_group_btn.on_click(self._on_add_to_group)

        self.clear_highlight_btn = pn.widgets.Button(
            name="🔄 Clear",
            button_type="light",
            width=80,
            margin=(5, 5)
        )
        self.clear_highlight_btn.on_click(self._on_clear_highlight)

        # === PANEL 2: GROUP MANAGEMENT ===

        # Group selector dropdown
        self.group_selector = pn.widgets.Select(
            name="Select Group",
            options=[],
            width=250,
            margin=(5, 5)
        )
        self.group_selector.param.watch(self._on_group_selected, 'value')

        # New group creation
        self.new_group_name = pn.widgets.TextInput(
            placeholder="New group name...",
            width=180,
            margin=(5, 5)
        )

        self.new_group_desc = pn.widgets.TextInput(
            placeholder="Description (optional)...",
            width=180,
            margin=(5, 5)
        )

        self.create_group_btn = pn.widgets.Button(
            name="📂 Create",
            button_type="primary",
            width=90,
            margin=(5, 5)
        )
        self.create_group_btn.on_click(self._on_create_group)

        # Group info display
        self.group_info_display = pn.pane.HTML(
            """<div style='background: #F8F9FA; padding: 12px; border-radius: 4px; color: #666; text-align: center;'>
               <strong>No group selected</strong><br>
               <small>Create a new group or select from dropdown</small>
               </div>""",
            margin=(5, 5)
        )

        # Group contents tabulator
        self.group_contents_tabulator = pn.widgets.Tabulator(
            value=pd.DataFrame(),
            pagination='remote',
            page_size=15,
            sizing_mode='stretch_width',
            selectable='checkbox',
            sortable=True,
            show_index=False,
            configuration={
                'layout': 'fitColumns',
                'height': '300px',
                'placeholder': 'Group is empty...',
                'responsiveLayout': 'hide'
            },
            height=300,
            margin=(5, 5)
        )

        # Panel 2 controls
        self.remove_from_group_btn = pn.widgets.Button(
            name="➖ Remove Selected",
            button_type="light",
            width=140,
            disabled=True,
            margin=(5, 5)
        )
        self.remove_from_group_btn.on_click(self._on_remove_from_group)

        self.delete_group_btn = pn.widgets.Button(
            name="🗑️ Delete Group",
            button_type="light",
            width=120,
            disabled=True,
            margin=(5, 5)
        )
        self.delete_group_btn.on_click(self._on_delete_group)

        # Status display
        self.status_display = pn.pane.HTML(
            "<div style='color: #2E7D32; font-size: 14px; padding: 5px;'>✅ Ready for group management</div>",
            margin=(5, 5)
        )

    def _populate_initial_data(self):
        """Populate dropdowns after components are created."""
        try:
            cells = self.api.get_cells()

            if cells:
                options = [(cell['name'], cell['name']) for cell in cells]
                self.cell_selector.options = options
                self._update_status(f"Found {len(cells)} cells", "success")
            else:
                self.cell_selector.options = []
                self._update_status("No cells found", "info")

        except Exception as e:
            self._update_status(f"Error loading cells: {str(e)}", "error")

    @property
    def panel(self):
        """Return professional card layout."""

        # Header with icon
        header = pn.pane.HTML("""
        <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white; 
                    padding: 15px; border-radius: 8px 8px 0 0; margin: 0;'>
            <h2 style='margin: 0; font-size: 18px; font-weight: 600;'>
                🔗 Group Management
            </h2>
        </div>
        """, margin=(0, 0))

        # Cell selection section
        cell_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 14px; font-weight: 600; margin: 15px 5px 10px 5px;'>
                Select Cell
            </div>
            """),
            self.cell_selector,
            margin=(10, 10)
        )

        # Panel 1: All Segments
        panel1 = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 15px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                All Segments
            </div>
            """),

            pn.pane.HTML("""
            <div style='font-size: 12px; color: #666; margin: 5px; padding: 8px;
                        background: #F8F9FA; border-radius: 4px;'>
                Select segments using checkboxes, then add to groups or highlight existing group members.
            </div>
            """),

            self.segments_tabulator,

            pn.Row(
                self.show_group_btn,
                self.add_to_group_btn,
                self.clear_highlight_btn,
                margin=(10, 5)
            ),

            width=500,
            margin=(10, 10)
        )

        # Panel 2: Group Management
        panel2 = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 15px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                Group Management
            </div>
            """),

            # Group selection section
            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555; font-size: 14px;'>Existing Groups:</label>"),
                self.group_selector,
                margin=(5, 5)
            ),

            # New group creation section
            pn.pane.HTML("""
            <div style='color: #666; font-size: 14px; font-weight: 500; margin: 15px 5px 5px 5px;'>
                Create New Group
            </div>
            """),

            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 12px; color: #666;'>Group Name:</label>"),
                    self.new_group_name,
                    width=200
                ),
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 12px; color: #666;'>&nbsp;</label>"),
                    self.create_group_btn,
                    width=110
                ),
                margin=(0, 5)
            ),

            pn.Column(
                pn.pane.HTML("<label style='font-size: 12px; color: #666;'>Description:</label>"),
                self.new_group_desc,
                margin=(0, 5)
            ),

            # Group info display
            self.group_info_display,

            # Group contents
            pn.pane.HTML("""
            <div style='color: #666; font-size: 14px; font-weight: 500; margin: 15px 5px 5px 5px;'>
                Group Contents
            </div>
            """),

            self.group_contents_tabulator,

            pn.Row(
                self.remove_from_group_btn,
                self.delete_group_btn,
                margin=(10, 5)
            ),

            width=450,
            margin=(10, 10)
        )

        # Main content area
        main_content = pn.Column(
            cell_section,
            pn.Row(
                panel1,
                panel2,
                sizing_mode='stretch_width'
            )
        )

        # Status section
        status_section = pn.Column(
            self.status_display,
            margin=(5, 10)
        )

        # Complete card
        card_content = pn.Column(
            main_content,
            status_section,
            styles={'background': 'white', 'border-radius': '0 0 8px 8px',
                   'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'margin': '0'}
        )

        return pn.Column(
            header,
            card_content,
            margin=(10, 10),
            styles={'border-radius': '8px', 'overflow': 'hidden'}
        )

    def _on_cell_selected(self, event):
        """Handle cell selection from dropdown."""
        cell_id = event.new
        
        # Handle tuple case from Select widget (display_name, actual_value)
        if isinstance(cell_id, tuple):
            cell_id = cell_id[1] if len(cell_id) > 1 else cell_id[0]
        elif not isinstance(cell_id, str):
            cell_id = str(cell_id) if cell_id is not None else ""
        
        if cell_id:
            self.current_cell = cell_id
            self._refresh_segments()
            self._refresh_groups()
            self._update_status(f"Loaded cell: {cell_id}", "success")
        else:
            self.current_cell = ""
            self.segments_tabulator.value = []
            self.group_selector.options = []
            self.group_contents_tabulator.value = []
            self._update_status("No cell selected", "info")

    def _refresh_segments(self):
        """Refresh all segments for current cell."""
        if not self.current_cell:
            return

        try:
            segments = self.api.get_cell_segments(self.current_cell)

            # Format for tabulator
            formatted_segments = []
            for segment in segments:
                formatted_segments.append({
                    'segment_id': str(segment['id']),
                    'technique': segment['fundamental_technique'],
                    'start_time': f"{segment.get('start_time_s', 0):.0f}s",
                    'duration': f"{segment.get('duration_s', 0):.1f}s",
                    'start_voltage': f"{segment.get('start_potential_v', 0):.3f}V" if segment.get('start_potential_v') else "N/A",
                    'end_voltage': f"{segment.get('end_potential_v', 0):.3f}V" if segment.get('end_potential_v') else "N/A",
                    'file_name': segment.get('original_filename', 'Unknown'),
                    'quality': f"{segment.get('quality', 0):.2f}" if segment.get('quality') else "N/A"
                })

            self.segments_tabulator.value = formatted_segments
            self._update_status(f"Loaded {len(segments)} segments", "success")

        except Exception as e:
            self._update_status(f"Error loading segments: {str(e)}", "error")

    def _refresh_groups(self):
        """Refresh groups dropdown for current cell."""
        if not self.current_cell:
            return

        try:
            groups = self.api.get_groups(self.current_cell)

            if groups:
                options = [(f"📁 {group['group_name']} ({group['segment_count']} segments)",
                           group['group_id']) for group in groups]
                self.group_selector.options = options
                self._update_status(f"Found {len(groups)} groups", "success")
            else:
                self.group_selector.options = []
                self._update_status("No groups found - create your first group", "info")

        except Exception as e:
            self._update_status(f"Error loading groups: {str(e)}", "error")

    def _on_group_selected(self, event):
        """Handle group selection."""
        group_id = event.new
        
        # Handle tuple case from Select widget (display_name, actual_value)
        if isinstance(group_id, tuple):
            group_id = group_id[1] if len(group_id) > 1 else group_id[0]
        elif not isinstance(group_id, str):
            group_id = str(group_id) if group_id is not None else ""
        
        if group_id:
            self.selected_group = group_id
            self._refresh_group_contents()
            self._update_group_info()
            self.show_group_btn.disabled = False
            self.add_to_group_btn.disabled = False
            self.delete_group_btn.disabled = False
        else:
            self.selected_group = ""
            self.group_contents_tabulator.value = []
            self.show_group_btn.disabled = True
            self.add_to_group_btn.disabled = True
            self.delete_group_btn.disabled = True

    def _refresh_group_contents(self):
        """Refresh contents of selected group."""
        if not self.selected_group:
            return

        try:
            segments = self.api.get_group_segments(int(self.selected_group))

            # Format for tabulator (same format as Panel 1)
            formatted_segments = []
            for segment in segments:
                formatted_segments.append({
                    'segment_id': str(segment['id']),
                    'technique': segment['fundamental_technique'],
                    'start_time': f"{segment.get('start_time_s', 0):.0f}s",
                    'duration': f"{segment.get('duration_s', 0):.1f}s",
                    'start_voltage': f"{segment.get('start_potential_v', 0):.3f}V" if segment.get('start_potential_v') else "N/A",
                    'end_voltage': f"{segment.get('end_potential_v', 0):.3f}V" if segment.get('end_potential_v') else "N/A",
                    'file_name': segment.get('original_filename', 'Unknown')
                })

            self.group_contents_tabulator.value = formatted_segments
            self.remove_from_group_btn.disabled = len(formatted_segments) == 0

        except Exception as e:
            self._update_status(f"Error loading group contents: {str(e)}", "error")

    def _update_group_info(self):
        """Update group info display."""
        if not self.selected_group:
            return

        try:
            group_info = self.api.get_group_info(int(self.selected_group))
            
            if group_info:
                self.group_info_display.object = f"""
                <div style='background: #E8F5E8; padding: 12px; border-radius: 4px; 
                            border-left: 4px solid #2E7D32;'>
                    <div style='font-weight: 600; color: #2E7D32; margin-bottom: 5px;'>
                        📁 {group_info['group_name']}
                    </div>
                    <div style='font-size: 12px; color: #1B5E20;'>
                        <strong>Segments:</strong> {group_info['segment_count']}<br>
                        <strong>Created:</strong> {group_info.get('created_at', 'Unknown')}<br>
                        <strong>Description:</strong> {group_info.get('description', 'No description')}
                    </div>
                </div>
                """
            else:
                self.group_info_display.object = f"""
                <div style='background: #FFEBEE; padding: 12px; border-radius: 4px; 
                            border-left: 4px solid #D32F2F; text-align: center;'>
                    <strong style='color: #D32F2F;'>Group not found</strong>
                </div>
                """

        except Exception as e:
            self.group_info_display.object = f"""
            <div style='background: #FFEBEE; padding: 12px; border-radius: 4px; 
                        border-left: 4px solid #D32F2F; text-align: center;'>
                <strong style='color: #D32F2F;'>Error loading group info</strong>
            </div>
            """

    def _on_show_group(self, event):
        """Highlight group segments in Panel 1."""
        if not self.selected_group:
            return

        try:
            segments = self.api.get_group_segments(int(self.selected_group))
            self.current_group_segments = {str(seg['id']) for seg in segments}

            # Apply highlighting to segments tabulator
            self._apply_highlighting()
            self._update_status(f"Highlighted {len(segments)} segments in group", "success")

        except Exception as e:
            self._update_status(f"Error highlighting group: {str(e)}", "error")

    def _apply_highlighting(self):
        """Apply visual highlighting to segments in current group."""
        # Note: In a real implementation, you'd update the tabulator's row formatting
        # This is a simplified version - actual highlighting would require
        # custom tabulator configuration or CSS classes
        pass

    def _on_add_to_group(self, event):
        """Add selected segments to current group."""
        if not self.selected_group:
            self._update_status("Please select a group first", "warning")
            return

        selected_indices = self.segments_tabulator.selection
        if not selected_indices:
            self._update_status("Please select segments to add", "warning")
            return

        try:
            # Get segment data from table value using selected indices
            table_data = self.segments_tabulator.value
            if not table_data or not isinstance(table_data, list):
                self._update_status("No segment data available", "error")
                return
                
            selected_segments = [table_data[i] for i in selected_indices if i < len(table_data)]
            segment_ids = [seg['segment_id'] for seg in selected_segments]

            result = self.api.add_segments_to_group(int(self.selected_group), segment_ids)

            if result.success:
                self._update_status(result.message, "success")
                self.status_message = result.message

                # Refresh group contents
                self._refresh_group_contents()
                self._update_group_info()

                # Clear selection in segments table
                self.segments_tabulator.selection = []
            else:
                self._update_status(f"Error adding segments: {result.error}", "error")

        except Exception as e:
            self._update_status(f"Error adding segments: {str(e)}", "error")

    def _on_remove_from_group(self, event):
        """Remove selected segments from current group."""
        if not self.selected_group:
            return

        selected_indices = self.group_contents_tabulator.selection
        if not selected_indices:
            self._update_status("Please select segments to remove", "warning")
            return

        try:
            # Get segment data from table value using selected indices
            table_data = self.group_contents_tabulator.value
            if not table_data or not isinstance(table_data, list):
                self._update_status("No segment data available", "error")
                return
                
            selected_segments = [table_data[i] for i in selected_indices if i < len(table_data)]
            segment_ids = [seg['segment_id'] for seg in selected_segments]

            result = self.api.remove_segments_from_group(int(self.selected_group), segment_ids)

            if result.success:
                self._update_status(result.message, "success")
                self.status_message = result.message

                # Refresh group contents
                self._refresh_group_contents()
                self._update_group_info()
            else:
                self._update_status(f"Error removing segments: {result.error}", "error")

        except Exception as e:
            self._update_status(f"Error removing segments: {str(e)}", "error")

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
                self._update_status(result.message, "success")
                self.status_message = result.message

                # Clear form
                self.new_group_name.value = ""
                self.new_group_desc.value = ""

                # Refresh groups and select new one
                self._refresh_groups()
                self.group_selector.value = int(result.file_id)  # Using file_id field for group_id
            else:
                self._update_status(f"Error creating group: {result.error}", "error")

        except Exception as e:
            self._update_status(f"Error creating group: {str(e)}", "error")

    def _on_delete_group(self, event):
        """Delete current group."""
        if not self.selected_group:
            return

        try:
            result = self.api.delete_group(int(self.selected_group))

            if result.success:
                self._update_status(result.message, "success")
                self.status_message = result.message

                # Clear selection and refresh
                self.group_selector.value = None
                self._refresh_groups()
            else:
                self._update_status(f"Error deleting group: {result.error}", "error")

        except Exception as e:
            self._update_status(f"Error deleting group: {str(e)}", "error")

    def _on_clear_highlight(self, event):
        """Clear highlighting in segments table."""
        self.current_group_segments = set()
        self._apply_highlighting()  # Remove highlighting
        self._update_status("Cleared highlighting", "success")

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



# Usage example for integration with main app
# if __name__ == "__main__":
#     # Example of how to integrate with existing app
#
#     class MockAPI:
#         """Mock API for testing"""
#         pass
#
#     # Create component
#     api = MockAPI()
#     group_tab = GroupManagementTab(api)
#
#     # Create Panel app for testing
#     pn.extension('tabulator')
#
#     app = pn.Column(
#         group_tab.panel,
#         sizing_mode='stretch_width'
#     )
#
#     app.show(port=5008)