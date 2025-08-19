"""
Cell Manager Component

Handles cell creation, selection, and management in a clean Panel interface.
"""

import panel as pn
import param
from typing import List, Dict, Any

class CellManager(param.Parameterized):
    """
    Cell management component for Panel interface.
    
    Provides:
    - Cell list with file counts
    - New cell creation
    - Cell selection
    - Cell deletion with confirmation
    """
    
    # Parameters for component communication
    selected_cell = param.String(default="", doc="Currently selected cell name")
    status_message = param.String(default="", doc="Status message for main app")
    
    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        
        # Create UI components
        self._create_components()
        self._refresh_cell_list()
    
    def _create_components(self):
        """Create the UI components."""
        # Header
        self.header = pn.pane.HTML("""
        <h3 style='margin: 10px 0; color: #2E4057;'>
            📋 Cell Management
        </h3>
        """)
        
        # Cell creation
        self.new_cell_name = pn.widgets.TextInput(
            placeholder="Enter cell name (e.g., CELL_001)",
            width=250
        )
        
        self.cell_chemistry = pn.widgets.Select(
            value="Li_ion",
            options=["Li_ion", "Li_metal", "Na_ion", "Other"],
            width=120
        )
        
        self.cell_notes = pn.widgets.TextAreaInput(
            placeholder="Optional notes...",
            height=60,
            width=250
        )
        
        self.create_btn = pn.widgets.Button(
            name="Create Cell",
            button_type="primary",
            width=100
        )
        self.create_btn.on_click(self._on_create_cell)
        
        # Cell list
        self.cell_select = pn.widgets.Select(
            name="Select Cell",
            options=[],
            width=250,
            size=8
        )
        self.cell_select.param.watch(self._on_cell_selected, 'value')
        
        # Management buttons
        self.refresh_btn = pn.widgets.Button(
            name="Refresh",
            button_type="light",
            width=80
        )
        self.refresh_btn.on_click(self._on_refresh)
        
        self.delete_btn = pn.widgets.Button(
            name="Delete",
            button_type="light",
            width=80,
            disabled=True
        )
        self.delete_btn.on_click(self._on_delete_cell)
        
        # Status display
        self.status_pane = pn.pane.HTML(
            "<p style='color: #666; font-size: 0.9em;'>Ready</p>",
            width=250,
            height=30
        )
    
    @property
    def panel(self):
        """Return the Panel layout."""
        return pn.Column(
            self.header,
            
            # Cell creation section
            pn.pane.HTML("<b>Create New Cell:</b>"),
            self.new_cell_name,
            pn.Row(
                pn.pane.HTML("Chemistry:", width=70),
                self.cell_chemistry
            ),
            self.cell_notes,
            self.create_btn,
            
            pn.Spacer(height=20),
            
            # Cell selection section
            pn.pane.HTML("<b>Existing Cells:</b>"),
            self.cell_select,
            pn.Row(self.refresh_btn, self.delete_btn),
            
            pn.Spacer(height=10),
            self.status_pane,
            
            width=280,
            margin=(10, 10)
        )
    
    def _on_create_cell(self, event):
        """Handle cell creation."""
        name = self.new_cell_name.value.strip()
        if not name:
            self._update_status("❌ Please enter a cell name", error=True)
            return
        
        try:
            result = self.api.create_cell(
                name=name,
                chemistry=self.cell_chemistry.value,
                notes=self.cell_notes.value.strip() or None
            )
            
            if result.success:
                self._update_status(f"✅ Created cell: {name}")
                self.status_message = f"Created cell: {name}"
                
                # Clear form
                self.new_cell_name.value = ""
                self.cell_notes.value = ""
                
                # Refresh list and select new cell
                self._refresh_cell_list()
                self.cell_select.value = name
                
            else:
                self._update_status(f"❌ {result.error}", error=True)
                
        except Exception as e:
            self._update_status(f"❌ Error: {str(e)}", error=True)
    
    def _on_cell_selected(self, event):
        """Handle cell selection."""
        cell_name = event.new
        if cell_name:
            self.selected_cell = cell_name
            self.delete_btn.disabled = False
            self._update_status(f"Selected: {cell_name}")
        else:
            self.delete_btn.disabled = True
    
    def _on_refresh(self, event):
        """Handle refresh button."""
        self._refresh_cell_list()
        self._update_status("Refreshed cell list")
    
    def _on_delete_cell(self, event):
        """Handle cell deletion."""
        if not self.cell_select.value:
            return
            
        cell_name = self.cell_select.value
        
        # Simple confirmation (Panel doesn't have built-in dialogs)
        # In a real app, you'd use a modal or custom confirmation widget
        self._update_status(f"⚠️ Delete {cell_name}? Click Delete again to confirm", error=True)
        
        # For now, implement simple deletion
        # TODO: Add proper confirmation modal
        try:
            # Get cell info first
            cell = self.api.get_cell_by_name(cell_name)
            if cell:
                success = self.api.delete_cell(cell['id'])
                if success:
                    self._update_status(f"✅ Deleted cell: {cell_name}")
                    self.status_message = f"Deleted cell: {cell_name}"
                    self._refresh_cell_list()
                else:
                    self._update_status(f"❌ Failed to delete {cell_name}", error=True)
            
        except Exception as e:
            self._update_status(f"❌ Error: {str(e)}", error=True)
    
    def _refresh_cell_list(self):
        """Refresh the cell list from database."""
        try:
            cells = self.api.get_cells()
            
            if cells:
                # Format: "CELL_001 (Li_ion) - 3 files"
                options = []
                for cell in cells:
                    file_count = cell.get('file_count', 0)
                    display_name = f"{cell['name']} ({cell['chemistry']}) - {file_count} files"
                    options.append((display_name, cell['name']))
                
                self.cell_select.options = options
                self._update_status(f"Found {len(cells)} cells")
            else:
                self.cell_select.options = []
                self._update_status("No cells found")
                
        except Exception as e:
            self._update_status(f"❌ Error loading cells: {str(e)}", error=True)
    
    def _update_status(self, message: str, error: bool = False):
        """Update status display."""
        color = "#d32f2f" if error else "#2e7d32"
        self.status_pane.object = f"""
        <p style='color: {color}; font-size: 0.9em; margin: 5px 0;'>
            {message}
        </p>
        """