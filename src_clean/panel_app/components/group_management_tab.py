"""
Professional Group Management Tab - Two-Tabulator Interface with Independent Cell Selection

Clean group organization interface with professional styling matching existing components.
"""

import panel as pn
import param
from typing import List, Dict, Any, Optional

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
            value=[],
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
            # REPLACE WITH REAL API CALL
            cells = self._mock_get_cells()  # Replace with: self.api.get_cells()

            if cells:
                options = [(cell['name'], cell['id']) for cell in cells]
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
            # REPLACE WITH REAL API CALL
            segments = self._mock_get_cell_segments(self.current_cell)  # Replace with: self.api.get_cell_segments(self.current_cell)

            # Format for tabulator
            formatted_segments = []
            for segment in segments:
                formatted_segments.append({
                    'segment_id': segment['segment_id'],
                    'technique': segment['technique'],
                    'start_time': f"{segment['start_time']:.0f}s",
                    'duration': f"{segment['duration']:.1f}s",
                    'start_voltage': f"{segment['start_voltage']:.3f}V",
                    'end_voltage': f"{segment['end_voltage']:.3f}V",
                    'file_name': segment['file_name'],
                    'quality': f"{segment.get('quality', 0):.2f}"
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
            # REPLACE WITH REAL API CALL
            groups = self._mock_get_groups(self.current_cell)  # Replace with: self.api.get_groups(self.current_cell)

            if groups:
                options = [(f"📁 {group['name']} ({group['segment_count']} segments)",
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
            # REPLACE WITH REAL API CALL
            segments = self._mock_get_group_segments(self.selected_group)  # Replace with: self.api.get_group_segments(self.selected_group)

            # Format for tabulator (same format as Panel 1)
            formatted_segments = []
            for segment in segments:
                formatted_segments.append({
                    'segment_id': segment['segment_id'],
                    'technique': segment['technique'],
                    'start_time': f"{segment['start_time']:.0f}s",
                    'duration': f"{segment['duration']:.1f}s",
                    'start_voltage': f"{segment['start_voltage']:.3f}V",
                    'end_voltage': f"{segment['end_voltage']:.3f}V",
                    'file_name': segment['file_name']
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
            # REPLACE WITH REAL API CALL
            group_info = self._mock_get_group_info(self.selected_group)  # Replace with: self.api.get_group_info(self.selected_group)

            self.group_info_display.object = f"""
            <div style='background: #E8F5E8; padding: 12px; border-radius: 4px; 
                        border-left: 4px solid #2E7D32;'>
                <div style='font-weight: 600; color: #2E7D32; margin-bottom: 5px;'>
                    📁 {group_info['name']}
                </div>
                <div style='font-size: 12px; color: #1B5E20;'>
                    <strong>Segments:</strong> {group_info['segment_count']}<br>
                    <strong>Created:</strong> {group_info['created_at']}<br>
                    <strong>Description:</strong> {group_info.get('description', 'No description')}
                </div>
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
            # REPLACE WITH REAL API CALL
            segments = self._mock_get_group_segments(self.selected_group)  # Replace with: self.api.get_group_segments(self.selected_group)
            self.current_group_segments = {seg['segment_id'] for seg in segments}

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

        selected_segments = self.segments_tabulator.selection
        if not selected_segments:
            self._update_status("Please select segments to add", "warning")
            return

        try:
            segment_ids = [seg['segment_id'] for seg in selected_segments]

            # REPLACE WITH REAL API CALL
            result = self._mock_add_segments_to_group(self.selected_group, segment_ids)  # Replace with: self.api.add_segments_to_group(self.selected_group, segment_ids)

            if result['success']:
                self._update_status(f"Added {len(segment_ids)} segments to group", "success")
                self.status_message = f"Added {len(segment_ids)} segments to group"

                # Refresh group contents
                self._refresh_group_contents()
                self._update_group_info()

                # Clear selection in segments table
                self.segments_tabulator.selection = []
            else:
                self._update_status(f"Error adding segments: {result['error']}", "error")

        except Exception as e:
            self._update_status(f"Error adding segments: {str(e)}", "error")

    def _on_remove_from_group(self, event):
        """Remove selected segments from current group."""
        if not self.selected_group:
            return

        selected_segments = self.group_contents_tabulator.selection
        if not selected_segments:
            self._update_status("Please select segments to remove", "warning")
            return

        try:
            segment_ids = [seg['segment_id'] for seg in selected_segments]

            # REPLACE WITH REAL API CALL
            result = self._mock_remove_segments_from_group(self.selected_group, segment_ids)  # Replace with: self.api.remove_segments_from_group(self.selected_group, segment_ids)

            if result['success']:
                self._update_status(f"Removed {len(segment_ids)} segments from group", "success")
                self.status_message = f"Removed {len(segment_ids)} segments from group"

                # Refresh group contents
                self._refresh_group_contents()
                self._update_group_info()
            else:
                self._update_status(f"Error removing segments: {result['error']}", "error")

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

            # REPLACE WITH REAL API CALL
            result = self._mock_create_group(self.current_cell, name, description)  # Replace with: self.api.create_group(self.current_cell, name, description)

            if result['success']:
                self._update_status(f"Created group: {name}", "success")
                self.status_message = f"Created group: {name}"

                # Clear form
                self.new_group_name.value = ""
                self.new_group_desc.value = ""

                # Refresh groups and select new one
                self._refresh_groups()
                self.group_selector.value = result['group_id']
            else:
                self._update_status(f"Error creating group: {result['error']}", "error")

        except Exception as e:
            self._update_status(f"Error creating group: {str(e)}", "error")

    def _on_delete_group(self, event):
        """Delete current group."""
        if not self.selected_group:
            return

        try:
            # REPLACE WITH REAL API CALL
            result = self._mock_delete_group(self.selected_group)  # Replace with: self.api.delete_group(self.selected_group)

            if result['success']:
                group_name = result.get('group_name', 'Unknown')
                self._update_status(f"Deleted group: {group_name}", "success")
                self.status_message = f"Deleted group: {group_name}"

                # Clear selection and refresh
                self.group_selector.value = None
                self._refresh_groups()
            else:
                self._update_status(f"Error deleting group: {result['error']}", "error")

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

    # === MOCK API METHODS (REPLACE WITH REAL BACKEND) ===

    def _mock_get_cells(self):
        """Mock cells data - replace with real API call."""
        return [
            {'id': 'cell_001', 'name': 'CELL_001'},
            {'id': 'cell_002', 'name': 'CELL_002'},
            {'id': 'cell_003', 'name': 'CELL_003'}
        ]

    def _mock_get_cell_segments(self, cell_id):
        """Mock segments data - replace with real API call."""
        return [
            {
                'segment_id': 'seg_001',
                'technique': 'REST',
                'start_time': 0.0,
                'duration': 300.0,
                'start_voltage': 3.75,
                'end_voltage': 3.82,
                'file_name': 'gitt_part1.par',
                'quality': 0.95
            },
            {
                'segment_id': 'seg_002',
                'technique': 'CC',
                'start_time': 300.0,
                'duration': 10.0,
                'start_voltage': 3.82,
                'end_voltage': 3.75,
                'file_name': 'gitt_part1.par',
                'quality': 0.88
            },
            {
                'segment_id': 'seg_003',
                'technique': 'REST',
                'start_time': 310.0,
                'duration': 300.0,
                'start_voltage': 3.75,
                'end_voltage': 3.83,
                'file_name': 'gitt_part1.par',
                'quality': 0.92
            },
            {
                'segment_id': 'seg_004',
                'technique': 'EIS',
                'start_time': 610.0,
                'duration': 120.0,
                'start_voltage': 3.83,
                'end_voltage': 3.83,
                'file_name': 'eis_test.par',
                'quality': 0.97
            }
        ]

    def _mock_get_groups(self, cell_id):
        """Mock groups data - replace with real API call."""
        return [
            {
                'group_id': 'group_001',
                'name': 'GITT Rest Phases',
                'segment_count': 2,
                'created_at': '2025-08-20',
                'description': 'All rest phases from GITT experiments'
            },
            {
                'group_id': 'group_002',
                'name': 'EIS Measurements',
                'segment_count': 1,
                'created_at': '2025-08-20',
                'description': 'Impedance spectroscopy data'
            }
        ]

    def _mock_get_group_segments(self, group_id):
        """Mock group segments - replace with real API call."""
        if group_id == 'group_001':  # GITT Rest Phases
            return [
                {
                    'segment_id': 'seg_001',
                    'technique': 'REST',
                    'start_time': 0.0,
                    'duration': 300.0,
                    'start_voltage': 3.75,
                    'end_voltage': 3.82,
                    'file_name': 'gitt_part1.par'
                },
                {
                    'segment_id': 'seg_003',
                    'technique': 'REST',
                    'start_time': 310.0,
                    'duration': 300.0,
                    'start_voltage': 3.75,
                    'end_voltage': 3.83,
                    'file_name': 'gitt_part1.par'
                }
            ]
        elif group_id == 'group_002':  # EIS Measurements
            return [
                {
                    'segment_id': 'seg_004',
                    'technique': 'EIS',
                    'start_time': 610.0,
                    'duration': 120.0,
                    'start_voltage': 3.83,
                    'end_voltage': 3.83,
                    'file_name': 'eis_test.par'
                }
            ]
        return []

    def _mock_get_group_info(self, group_id):
        """Mock group info - replace with real API call."""
        groups = {
            'group_001': {
                'name': 'GITT Rest Phases',
                'segment_count': 2,
                'created_at': '2025-08-20 10:30',
                'description': 'All rest phases from GITT experiments'
            },
            'group_002': {
                'name': 'EIS Measurements',
                'segment_count': 1,
                'created_at': '2025-08-20 11:45',
                'description': 'Impedance spectroscopy data'
            }
        }
        return groups.get(group_id, {})

    def _mock_create_group(self, cell_id, name, description):
        """Mock group creation - replace with real API call."""
        # Simulate success
        return {
            'success': True,
            'group_id': f'group_{len(self._mock_get_groups(cell_id)) + 1:03d}'
        }

    def _mock_delete_group(self, group_id):
        """Mock group deletion - replace with real API call."""
        return {
            'success': True,
            'group_name': 'Test Group'
        }

    def _mock_add_segments_to_group(self, group_id, segment_ids):
        """Mock adding segments to group - replace with real API call."""
        return {'success': True}

    def _mock_remove_segments_from_group(self, group_id, segment_ids):
        """Mock removing segments from group - replace with real API call."""
        return {'success': True}


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