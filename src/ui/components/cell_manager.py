"""
Cell Manager Tab for Panel UI.

Provides interface for creating, viewing, and managing battery cells.
"""

import panel as pn
import param
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd


class CellManagerTab(param.Parameterized):
    """
    Cell management interface for creating and organizing battery cells.
    """
    
    # Parameters for reactive UI
    active_cell_id = param.Integer(default=None, allow_None=True, doc="Active cell ID")
    active_cell_name = param.String(default="", doc="Active cell name") 
    refresh_trigger = param.Number(default=0, doc="Trigger for refreshing data")
    
    def __init__(self, backend_api, **params):
        super().__init__(**params)
        self.api = backend_api
        self.layout = None
        self.cells_table = None
        self.active_cell_files_table = None
        self.create_cell_form = None
        self.active_cell_status = None
        self._cells_df = None  # Store cells dataframe for selection handling
        self.setup_layout()
    
    def setup_layout(self):
        """Setup the complete cell manager layout with active cell file management."""
        
        # Top section: Cell management
        cell_management_section = self._create_cell_management_section()
        
        # Bottom section: Active cell file management
        file_management_section = self._create_file_management_section()
        
        # Main layout
        self.layout = pn.Column(
            "## Cell & File Management",
            cell_management_section,
            "---",
            file_management_section,
            width=1200
        )
    
    def _create_cell_management_section(self):
        """Create the top section for cell management."""
        
        # Create cell form
        self.create_cell_form = self._create_cell_form()
        
        # Cells table with selection
        cells_table = self._create_cells_table()
        
        # Active cell controls
        active_cell_controls = self._create_active_cell_controls()
        
        return pn.Column(
            "### Cell Management",
            pn.Row(
                pn.Column(
                    "#### Create New Cell",
                    self.create_cell_form,
                    width=400
                ),
                pn.Column(
                    "#### Select Active Cell",
                    active_cell_controls,
                    width=300
                ),
                pn.Column(
                    "#### All Cells",
                    cells_table,
                    width=500
                )
            )
        )
    
    def _create_file_management_section(self):
        """Create the bottom section for active cell file management."""
        
        # Active cell status
        self.active_cell_status = pn.pane.HTML(
            "<p>No active cell selected</p>",
            width=1200
        )
        
        # Active cell files table
        active_cell_files_table = self._create_active_cell_files_table()
        
        return pn.Column(
            "### Active Cell File Management",
            self.active_cell_status,
            active_cell_files_table
        )
    
    def _create_cell_form(self):
        """Create cell creation form."""
        
        # Form inputs
        cell_name_input = pn.widgets.TextInput(
            name="Cell Name", 
            placeholder="e.g., CELL_001, TestCell_A",
            width=300
        )
        
        description_input = pn.widgets.TextInput(
            name="Description",
            placeholder="Brief description of the cell",
            width=300
        )
        
        chemistry_select = pn.widgets.Select(
            name="Chemistry",
            value="Li-ion",
            options=["Li-ion", "LFP", "NMC", "LCO", "NCA", "Other"],
            width=150
        )
        
        capacity_input = pn.widgets.FloatInput(
            name="Capacity (Ah)",
            value=None,
            step=0.001,
            width=150
        )
        
        notes_area = pn.widgets.TextAreaInput(
            name="Notes",
            placeholder="Additional notes about the cell",
            height=80,
            width=300
        )
        
        # Create button
        create_button = pn.widgets.Button(
            name="Create Cell",
            button_type="primary",
            width=150
        )
        
        # Status message
        status_message = pn.pane.HTML("", width=300)
        
        def create_cell_callback(event):
            """Handle cell creation."""
            # Validate inputs
            if not cell_name_input.value or not cell_name_input.value.strip():
                status_message.object = '<p style="color: red;">Cell name is required</p>'
                return
            
            # Call backend API
            result = self.api.create_cell(
                cell_name=cell_name_input.value.strip(),
                description=description_input.value or "",
                chemistry=chemistry_select.value,
                capacity_ah=capacity_input.value,
                notes=notes_area.value or ""
            )
            
            if result['success']:
                status_message.object = f'<p style="color: green;">{result["message"]}</p>'
                # Clear form
                cell_name_input.value = ""
                description_input.value = ""
                capacity_input.value = None
                notes_area.value = ""
                # Refresh cells table
                self.refresh_trigger += 1
            else:
                status_message.object = f'<p style="color: red;">Error: {result["error"]}</p>'
        
        create_button.on_click(create_cell_callback)
        
        return pn.Column(
            cell_name_input,
            description_input,
            pn.Row(chemistry_select, capacity_input),
            notes_area,
            create_button,
            status_message
        )
    
    def _create_cells_table(self):
        """Create reactive cells table with active cell selection."""
        
        @pn.depends(self.param.refresh_trigger)
        def get_cells_table(*args):
            """Get cells table widget."""
            result = self.api.get_all_cells()
            if result['success']:
                cells = result['cells']
                if cells:
                    # Convert to DataFrame for table display
                    df = pd.DataFrame(cells)
                    # Add database IDs for selection tracking
                    self._cells_df = df.copy()  # Store for selection handling
                    
                    # Format columns for display
                    display_columns = ['cell_name', 'description', 'chemistry', 'capacity_ah', 
                                     'file_count', 'processed_count', 'created_at']
                    available_columns = [col for col in display_columns if col in df.columns]
                    display_df = df[available_columns]
                    
                    # Rename columns for display
                    column_names = {
                        'cell_name': 'Cell Name',
                        'description': 'Description', 
                        'chemistry': 'Chemistry',
                        'capacity_ah': 'Capacity (Ah)',
                        'file_count': 'Files',
                        'processed_count': 'Processed',
                        'created_at': 'Created'
                    }
                    display_df = display_df.rename(columns=column_names)
                    
                    # Create table with selection
                    table = pn.widgets.Tabulator(
                        display_df,
                        pagination='remote',
                        page_size=10,
                        selectable='checkbox',
                        width=450,
                        height=300
                    )
                    
                    # Handle selection
                    def on_selection_change(event):
                        if event.new:
                            selected_index = event.new[0]
                            selected_row = self._cells_df.iloc[selected_index]
                            self.active_cell_id = selected_row['id']
                            self.active_cell_name = selected_row['cell_name']
                            self._update_active_cell_display()
                    
                    table.param.watch(on_selection_change, 'selection')
                    
                    return table
                else:
                    return pn.pane.HTML("<p>No cells found. Create your first cell above.</p>")
            else:
                return pn.pane.HTML(f'<p style="color: red;">Error loading cells: {result["error"]}</p>')
        
        return get_cells_table
    
    def _create_active_cell_controls(self):
        """Create active cell selection and status controls."""
        
        # Active cell status display
        @pn.depends(self.param.active_cell_name, self.param.active_cell_id)
        def get_active_cell_status(*args):
            if self.active_cell_id:
                return pn.pane.HTML(
                    f"<p><strong>Active Cell:</strong> {self.active_cell_name} (ID: {self.active_cell_id})</p>",
                    width=280
                )
            else:
                return pn.pane.HTML(
                    "<p style='color: #666;'>No active cell selected</p>",
                    width=280
                )
        
        # Clear selection button
        clear_button = pn.widgets.Button(
            name="Clear Selection",
            button_type="light",
            width=120
        )
        
        def clear_selection(event):
            self.active_cell_id = None
            self.active_cell_name = ""
            self._update_active_cell_display()
        
        clear_button.on_click(clear_selection)
        
        return pn.Column(
            get_active_cell_status,
            clear_button
        )
    
    def _create_active_cell_files_table(self):
        """Create reactive files table for the active cell."""
        
        @pn.depends(self.param.active_cell_id)
        def get_active_cell_files(*args):
            if not self.active_cell_id:
                return pn.pane.HTML(
                    "<p style='color: #666;'>Select a cell to view its files</p>",
                    width=1150
                )
            
            # Get files for active cell
            result = self.api.get_cell_files(self.active_cell_id)
            if result['success']:
                files = result['files']
                if files:
                    # Convert to DataFrame
                    df = pd.DataFrame(files)
                    
                    # Format columns for display
                    display_columns = ['original_filename', 'file_type', 'processing_status', 
                                     'temperature_c', 'upload_timestamp']
                    available_columns = [col for col in display_columns if col in df.columns]
                    display_df = df[available_columns]
                    
                    # Rename columns
                    column_names = {
                        'original_filename': 'File Name',
                        'file_type': 'Type',
                        'processing_status': 'Status',
                        'temperature_c': 'Temperature (°C)',
                        'upload_timestamp': 'Uploaded'
                    }
                    display_df = display_df.rename(columns=column_names)
                    
                    # Create table
                    table = pn.widgets.Tabulator(
                        display_df,
                        pagination='remote',
                        page_size=10,
                        selectable='checkbox',
                        width=1150,
                        height=250
                    )
                    
                    return table
                else:
                    return pn.pane.HTML(
                        f"<p>No files found for {self.active_cell_name}. Upload files using the File Association tab.</p>",
                        width=1150
                    )
            else:
                return pn.pane.HTML(
                    f'<p style="color: red;">Error loading files: {result["error"]}</p>',
                    width=1150
                )
        
        return get_active_cell_files
    
    def _update_active_cell_display(self):
        """Update the active cell status and files display."""
        if self.active_cell_id:
            # Update status display
            status_html = f"""
            <div style="padding: 10px; background-color: #f0f8ff; border-left: 4px solid #0066cc;">
                <h4 style="margin: 0;">Active Cell: {self.active_cell_name}</h4>
                <p style="margin: 5px 0;">ID: {self.active_cell_id} | Files will be displayed below</p>
            </div>
            """
        else:
            status_html = """
            <div style="padding: 10px; background-color: #f5f5f5; border-left: 4px solid #999;">
                <p style="margin: 0; color: #666;">No active cell selected. Choose a cell from the table above.</p>
            </div>
            """
        
        self.active_cell_status.object = status_html
    
    @pn.depends('refresh_trigger', watch=True)
    def refresh_cells_table(self, *args):
        """Refresh the cells table when trigger changes."""
        # The table will refresh automatically due to the @pn.depends decorator
        pass