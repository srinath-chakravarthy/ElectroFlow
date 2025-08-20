"""
Professional Cell Manager Component - Clean Card Design

Modern, scientific interface with proper visual hierarchy and professional styling.
"""

import panel as pn
import param
from typing import List, Dict, Any

class CellManager(param.Parameterized):
    """
    Professional cell management component with card-based design.

    Features:
    - Clean card layout with proper spacing
    - Organized form sections
    - Professional color scheme
    - Clear visual hierarchy
    """

    selected_cell = param.String(default="", doc="Currently selected cell name")
    status_message = param.String(default="", doc="Status message for main app")

    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        self._create_components()
        self._refresh_cell_list()

    def _create_components(self):
        """Create professional UI components."""

        # === CELL CREATION SECTION ===

        # Basic info row
        self.new_cell_name = pn.widgets.TextInput(
            placeholder="e.g., CELL_001",
            width=180,
            margin=(5, 5)
        )

        self.cell_chemistry = pn.widgets.Select(
            value="Li_ion",
            options=["Li_ion", "Li_metal", "Na_ion", "LFP", "NMC", "Other"],
            width=100,
            margin=(5, 5)
        )

        # Description
        self.cell_description = pn.widgets.TextInput(
            placeholder="Brief description (e.g., Formation cycles)",
            width=290,
            margin=(5, 5)
        )

        # Battery specs row
        self.capacity_ah = pn.widgets.NumberInput(
            value=None,
            step=0.1,
            start=0,
            width=140,
            margin=(5, 5)
        )

        # Electrode details
        self.cathode_material = pn.widgets.TextInput(
            placeholder="e.g., NMC811",
            width=140,
            margin=(5, 5)
        )

        self.cathode_mass_mg = pn.widgets.NumberInput(
            value=None,
            step=0.1,
            start=0,
            width=140,
            margin=(5, 5)
        )

        self.anode_material = pn.widgets.TextInput(
            placeholder="e.g., Li metal",
            width=140,
            margin=(5, 5)
        )

        self.anode_mass_mg = pn.widgets.NumberInput(
            value=None,
            step=0.1,
            start=0,
            width=140,
            margin=(5, 5)
        )

        # Notes
        self.cell_notes = pn.widgets.TextAreaInput(
            placeholder="Optional notes and observations...",
            height=60,
            width=290,
            margin=(5, 5)
        )

        self.create_btn = pn.widgets.Button(
            name="Create Cell",
            button_type="primary",
            width=120,
            margin=(10, 5)
        )
        self.create_btn.on_click(self._on_create_cell)

        # === CELL LIST SECTION ===

        self.cell_select = pn.widgets.Select(
            options=[],
            width=290,
            size=8,
            margin=(5, 5)
        )
        self.cell_select.param.watch(self._on_cell_selected, 'value')

        # Management buttons
        self.refresh_btn = pn.widgets.Button(
            name="🔄 Refresh",
            button_type="light",
            width=90,
            margin=(5, 5)
        )
        self.refresh_btn.on_click(self._on_refresh)

        self.delete_btn = pn.widgets.Button(
            name="🗑️ Delete",
            button_type="light",
            width=90,
            disabled=True,
            margin=(5, 5)
        )
        self.delete_btn.on_click(self._on_delete_cell)

        # Selected cell display
        self.selected_display = pn.pane.HTML(
            """<div style='background: #E3F2FD; padding: 10px; border-radius: 4px; border-left: 4px solid #1976D2;'>
               <strong>Selected:</strong> <span style='color: #1976D2;'>None</span>
               </div>""",
            margin=(10, 5)
        )

        # Status display
        self.status_pane = pn.pane.HTML(
            "<div style='color: #2E7D32; font-size: 14px; padding: 5px;'>✅ Ready</div>",
            margin=(5, 5)
        )

    @property
    def panel(self):
        """Return professional card layout."""

        # Header with icon
        header = pn.pane.HTML("""
        <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white; 
                    padding: 15px; border-radius: 8px 8px 0 0; margin: 0;'>
            <h2 style='margin: 0; font-size: 18px; font-weight: 600;'>
                🔋 Cell Management
            </h2>
        </div>
        """, margin=(0, 0))

        # Create cell section
        create_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 15px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                Create New Cell
            </div>
            """),

            # Basic info
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555;'>Cell Name:</label>"),
                    self.new_cell_name,
                    width=200
                ),
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555;'>Chemistry:</label>"),
                    self.cell_chemistry,
                    width=120
                ),
                margin=(0, 5)
            ),

            # Description
            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555;'>Description:</label>"),
                self.cell_description,
                margin=(5, 5)
            ),

            # Battery specs
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555;'>Capacity (Ah):</label>"),
                    self.capacity_ah,
                    width=160
                ),
                pn.Spacer(width=20),
                margin=(5, 5)
            ),

            # Electrode details
            pn.pane.HTML("""
            <div style='color: #666; font-size: 14px; font-weight: 500; margin: 10px 5px 5px 5px;'>
                Electrode Details
            </div>
            """),

            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 12px; color: #666;'>Cathode Material:</label>"),
                    self.cathode_material,
                    width=160
                ),
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 12px; color: #666;'>Mass (mg):</label>"),
                    self.cathode_mass_mg,
                    width=160
                ),
                margin=(0, 5)
            ),

            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 12px; color: #666;'>Anode Material:</label>"),
                    self.anode_material,
                    width=160
                ),
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 12px; color: #666;'>Mass (mg):</label>"),
                    self.anode_mass_mg,
                    width=160
                ),
                margin=(0, 5)
            ),

            # Notes
            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555;'>Notes:</label>"),
                self.cell_notes,
                margin=(5, 5)
            ),

            # Create button
            pn.Row(
                pn.Spacer(),
                self.create_btn,
                margin=(10, 5)
            ),

            margin=(10, 10)
        )

        # Existing cells section
        existing_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                Existing Cells
            </div>
            """),

            self.cell_select,

            pn.Row(
                self.refresh_btn,
                self.delete_btn,
                pn.Spacer(),
                margin=(10, 5)
            ),

            self.selected_display,

            margin=(10, 10)
        )

        # Status section
        status_section = pn.Column(
            self.status_pane,
            margin=(5, 10)
        )

        # Complete card
        card_content = pn.Column(
            create_section,
            existing_section,
            status_section,
            styles={'background': 'white', 'border-radius': '0 0 8px 8px',
                   'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'margin': '0'}
        )

        return pn.Column(
            header,
            card_content,
            width=350,
            margin=(10, 10),
            styles={'border-radius': '8px', 'overflow': 'hidden'}
        )

    def _on_create_cell(self, event):
        """Handle cell creation with better feedback."""
        name = self.new_cell_name.value.strip()
        if not name:
            self._update_status("⚠️ Please enter a cell name", "warning")
            return

        try:
            result = self.api.create_cell(
                name=name,
                chemistry=self.cell_chemistry.value,
                description=self.cell_description.value.strip() or "",
                capacity_ah=self.capacity_ah.value,
                cathode_material=self.cathode_material.value.strip() or "",
                cathode_mass_mg=self.cathode_mass_mg.value,
                anode_material=self.anode_material.value.strip() or "",
                anode_mass_mg=self.anode_mass_mg.value,
                notes=self.cell_notes.value.strip() or ""
            )

            if result.success:
                self._update_status(f"✅ Created cell: {name}", "success")
                self.status_message = f"Created cell: {name}"

                # Clear form
                self._clear_form()

                # Refresh list and select new cell
                self._refresh_cell_list()
                self.cell_select.value = name

            else:
                self._update_status(f"❌ {result.error}", "error")

        except Exception as e:
            self._update_status(f"❌ Error: {str(e)}", "error")

    def _clear_form(self):
        """Clear the creation form."""
        self.new_cell_name.value = ""
        self.cell_description.value = ""
        self.capacity_ah.value = None
        self.cathode_material.value = ""
        self.cathode_mass_mg.value = None
        self.anode_material.value = ""
        self.anode_mass_mg.value = None
        self.cell_notes.value = ""

    def _on_cell_selected(self, event):
        """Handle cell selection with visual feedback."""
        cell_name = event.new
        if cell_name:
            if isinstance(cell_name, tuple):
                cell_name = cell_name[1]
            elif not isinstance(cell_name, str):
                cell_name = str(cell_name) if cell_name is not None else ""

            self.selected_cell = cell_name
            self.delete_btn.disabled = False

            # Update selected cell display with better styling
            self.selected_display.object = f"""
            <div style='background: #E8F5E8; padding: 12px; border-radius: 4px; 
                        border-left: 4px solid #2E7D32;'>
                <strong style='color: #2E7D32;'>Selected Cell:</strong> 
                <span style='color: #1B5E20; font-weight: 600;'>{cell_name}</span>
                <span style='color: #4CAF50; float: right;'>✓</span>
            </div>
            """
            self._update_status(f"Selected: {cell_name}", "success")
        else:
            self.delete_btn.disabled = True
            self.selected_display.object = """
            <div style='background: #F5F5F5; padding: 12px; border-radius: 4px; 
                        border-left: 4px solid #9E9E9E;'>
                <strong style='color: #666;'>Selected Cell:</strong> 
                <span style='color: #999;'>None</span>
            </div>
            """

    def _on_refresh(self, event):
        """Handle refresh with feedback."""
        self._refresh_cell_list()
        self._update_status("🔄 Refreshed cell list", "success")

    def _on_delete_cell(self, event):
        """Handle cell deletion with confirmation."""
        if not self.cell_select.value:
            return

        cell_name = self.cell_select.value

        # Simple confirmation (in production, use a modal)
        self._update_status(f"⚠️ Delete {cell_name}? Click Delete again to confirm", "warning")

        try:
            cell = self.api.get_cell_by_name(cell_name)
            if cell:
                success = self.api.delete_cell(cell['id'])
                if success:
                    self._update_status(f"✅ Deleted cell: {cell_name}", "success")
                    self.status_message = f"Deleted cell: {cell_name}"
                    self._refresh_cell_list()
                else:
                    self._update_status(f"❌ Failed to delete {cell_name}", "error")

        except Exception as e:
            self._update_status(f"❌ Error: {str(e)}", "error")

    def _refresh_cell_list(self):
        """Refresh cell list with better formatting."""
        try:
            cells = self.api.get_cells()

            if cells:
                options = []
                for cell in cells:
                    file_count = cell.get('file_count', 0)
                    chemistry = cell.get('chemistry', 'Unknown')

                    # Professional formatting
                    if file_count == 0:
                        files_text = "no files"
                    elif file_count == 1:
                        files_text = "1 file"
                    else:
                        files_text = f"{file_count} files"

                    display_name = f"● {cell['name']} ({chemistry}) - {files_text}"
                    options.append((display_name, cell['name']))

                self.cell_select.options = options
                self._update_status(f"Found {len(cells)} cells", "success")
            else:
                self.cell_select.options = []
                self._update_status("No cells found - create your first cell above", "info")

        except Exception as e:
            self._update_status(f"❌ Error loading cells: {str(e)}", "error")

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

        self.status_pane.object = f"""
        <div style='color: {color}; font-size: 14px; padding: 8px; 
                    background: {color}15; border-radius: 4px; border-left: 3px solid {color};'>
            {icon} {message}
        </div>
        """