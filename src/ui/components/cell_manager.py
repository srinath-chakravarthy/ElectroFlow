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
    selected_cell = param.String(default="", doc="Currently selected cell")
    refresh_trigger = param.Number(default=0, doc="Trigger for refreshing data")
    
    def __init__(self, backend_api, **params):
        super().__init__(**params)
        self.api = backend_api
        self.layout = None
        self.cells_table = None
        self.cell_details_pane = None
        self.create_cell_form = None
        self.setup_layout()
    
    def setup_layout(self):
        """Setup the complete cell manager layout."""
        
        # Create cell form
        self.create_cell_form = self._create_cell_form()
        
        # Cells table
        self.cells_table = self._create_cells_table()
        
        # Cell details pane
        self.cell_details_pane = pn.pane.HTML(
            "<p>Select a cell to view details</p>",
            width=400, height=300
        )
        
        # Main layout
        self.layout = pn.Column(
            "## Cell Management",
            pn.Row(
                pn.Column(
                    "### Create New Cell",
                    self.create_cell_form,
                    width=500
                ),
                pn.Column(
                    "### Cell Details",
                    self.cell_details_pane,
                    width=400
                )
            ),
            "### Existing Cells",
            self.cells_table,
            width=1000
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
        """Create reactive cells table."""
        
        @pn.depends(self.refresh_trigger)
        def get_cells_data():
            """Get cells data from backend."""
            result = self.api.get_all_cells()
            if result['success']:
                cells = result['cells']
                if cells:
                    # Convert to DataFrame for table display
                    df = pd.DataFrame(cells)
                    # Format columns for display
                    display_columns = ['cell_name', 'description', 'chemistry', 'capacity_ah', 
                                     'file_count', 'processed_count', 'created_at']
                    available_columns = [col for col in display_columns if col in df.columns]
                    df = df[available_columns]
                    
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
                    df = df.rename(columns=column_names)
                    
                    # Create table with selection
                    table = pn.widgets.Tabulator(
                        df,
                        pagination='remote',
                        page_size=10,
                        selectable='checkbox',
                        width=950,
                        height=300
                    )
                    
                    # Handle selection
                    def on_selection_change(event):
                        if event.new:
                            selected_index = event.new[0]
                            selected_cell_name = df.iloc[selected_index]['Cell Name']
                            self.selected_cell = selected_cell_name
                            self._update_cell_details(selected_cell_name)
                    
                    table.param.watch(on_selection_change, 'selection')
                    
                    return table
                else:
                    return pn.pane.HTML("<p>No cells found. Create your first cell above.</p>")
            else:
                return pn.pane.HTML(f'<p style="color: red;">Error loading cells: {result["error"]}</p>')
        
        return pn.pane.HTML("Loading cells...", width=950)  # Placeholder, will be replaced
    
    def _update_cell_details(self, cell_name: str):
        """Update cell details pane."""
        result = self.api.get_cell_details(cell_name)
        
        if result['success']:
            cell = result['cell']
            summary = cell.get('summary', {})
            
            # Format cell details HTML
            html = f"""
            <div style="padding: 10px;">
                <h3>{cell['cell_name']}</h3>
                <p><strong>Description:</strong> {cell.get('description', 'N/A')}</p>
                <p><strong>Chemistry:</strong> {cell.get('chemistry', 'N/A')}</p>
                <p><strong>Capacity:</strong> {cell.get('capacity_ah', 'N/A')} Ah</p>
                <p><strong>Notes:</strong> {cell.get('notes', 'N/A')}</p>
                
                <h4>File Summary</h4>
                <p><strong>Total Files:</strong> {summary.get('total_files', 0)}</p>
                <p><strong>Total Data Points:</strong> {summary.get('total_points', 0):,}</p>
                <p><strong>Total Duration:</strong> {summary.get('total_duration_hours', 0):.2f} hours</p>
                <p><strong>Techniques:</strong> {', '.join(summary.get('techniques_used', []))}</p>
                
                <h4>Timeline</h4>
                <p><strong>Created:</strong> {cell.get('created_at', 'N/A')}</p>
                <p><strong>Last Updated:</strong> {cell.get('updated_at', 'N/A')}</p>
            </div>
            """
            
            self.cell_details_pane.object = html
        else:
            self.cell_details_pane.object = f'<p style="color: red;">Error: {result["error"]}</p>'
    
    @pn.depends('refresh_trigger', watch=True)
    def refresh_cells_table(self):
        """Refresh the cells table when trigger changes."""
        if self.layout and len(self.layout) > 2:
            # Replace the table
            self.layout[2] = self._create_cells_table_widget()
    
    def _create_cells_table_widget(self):
        """Create the actual table widget."""
        result = self.api.get_all_cells()
        if result['success']:
            cells = result['cells']
            if cells:
                # Convert to DataFrame for table display
                df = pd.DataFrame(cells)
                # Format columns for display
                display_columns = ['cell_name', 'description', 'chemistry', 'capacity_ah', 
                                 'file_count', 'processed_count', 'created_at']
                available_columns = [col for col in display_columns if col in df.columns]
                df = df[available_columns]
                
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
                df = df.rename(columns=column_names)
                
                # Create table with selection
                table = pn.widgets.Tabulator(
                    df,
                    pagination='remote',
                    page_size=10,
                    selectable='checkbox',
                    width=950,
                    height=300
                )
                
                # Handle selection
                def on_selection_change(event):
                    if event.new:
                        selected_index = event.new[0]
                        selected_cell_name = df.iloc[selected_index]['Cell Name']
                        self.selected_cell = selected_cell_name
                        self._update_cell_details(selected_cell_name)
                
                table.param.watch(on_selection_change, 'selection')
                
                return table
            else:
                return pn.pane.HTML("<p>No cells found. Create your first cell above.</p>")
        else:
            return pn.pane.HTML(f'<p style="color: red;">Error loading cells: {result["error"]}</p>')