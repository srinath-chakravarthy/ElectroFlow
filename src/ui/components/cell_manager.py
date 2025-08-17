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
            sizing_mode="stretch_width"
        )
        
        # File upload section
        upload_section = self._create_file_upload_section()
        
        # Active cell files table
        active_cell_files_table = self._create_active_cell_files_table()
        
        return pn.Column(
            "### Active Cell File Management",
            self.active_cell_status,
            upload_section,
            "---",
            "#### Existing Files",
            active_cell_files_table,
            sizing_mode="stretch_width"
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
                    
                    # Create table with single selection
                    table = pn.widgets.Tabulator(
                        display_df,
                        pagination='remote',
                        page_size=10,
                        selectable='single',  # Single cell selection only
                        sizing_mode='stretch_width',
                        height=300
                    )
                    
                    # Handle single selection - Panel Tabulator selection handling
                    def on_selection_change(event):
                        if hasattr(event, 'new') and event.new is not None:
                            selected_indices = event.new if isinstance(event.new, list) else [event.new]
                            if selected_indices and len(selected_indices) > 0:
                                selected_index = selected_indices[0]  # Take first selection for single mode
                                if selected_index < len(self._cells_df):
                                    selected_row = self._cells_df.iloc[selected_index]
                                    self.active_cell_id = int(selected_row['id'])
                                    self.active_cell_name = str(selected_row['cell_name'])
                                    self._update_active_cell_display()
                                    return
                        
                        # Clear selection
                        self.active_cell_id = None
                        self.active_cell_name = ""
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
                    sizing_mode="stretch_width"
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
                        sizing_mode='stretch_width',
                        height=250
                    )
                    
                    return table
                else:
                    return pn.pane.HTML(
                        f"<p>No files found for {self.active_cell_name}. Use the file upload section above to add files.</p>",
                        sizing_mode="stretch_width"
                    )
            else:
                return pn.pane.HTML(
                    f'<p style="color: red;">Error loading files: {result["error"]}</p>',
                    sizing_mode="stretch_width"
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
    
    def _create_file_upload_section(self):
        """Create local file browser section for dual file selection."""
        
        # File browser section
        file_browser = self._create_local_file_browser()
        
        # File association controls
        association_controls = self._create_file_association_controls()
        
        return pn.Row(
            pn.Column(
                "#### Local File Browser",
                file_browser,
                width=600
            ),
            pn.Column(
                "#### File Association",
                association_controls,
                width=400
            ),
            sizing_mode="stretch_width"
        )
    
    def _create_local_file_browser(self):
        """Create local file system browser for dual file selection."""
        from pathlib import Path
        
        # Initialize browser state
        self.current_directory = Path("/Users/srinathchakravarthy/")
        self.selected_files = []
        
        # Directory display
        self.current_dir_display = pn.pane.HTML(
            f"<p><strong>Current Directory:</strong> {self.current_directory}</p>",
            sizing_mode="stretch_width"
        )
        
        # Navigation controls
        home_button = pn.widgets.Button(name="Home", button_type="light", width=80)
        parent_button = pn.widgets.Button(name="Up", button_type="light", width=80)
        path_input = pn.widgets.TextInput(name="Path", value=str(self.current_directory), width=400)
        
        # File listing table
        self.file_table = self._create_file_listing_table()
        
        # Selected files display
        self.selected_files_display = pn.pane.HTML(
            "<p>No files selected</p>",
            sizing_mode="stretch_width",
            height=100
        )
        
        # Navigation handlers
        def go_home(event):
            self.current_directory = Path("/Users/srinathchakravarthy/")
            self._refresh_file_browser()
        
        def go_parent(event):
            if self.current_directory.parent != self.current_directory:  # Not root
                self.current_directory = self.current_directory.parent
                self._refresh_file_browser()
        
        def navigate_to_path(event):
            try:
                new_path = Path(path_input.value)
                if new_path.exists() and new_path.is_dir():
                    self.current_directory = new_path
                    self._refresh_file_browser()
                else:
                    path_input.value = str(self.current_directory)  # Reset to valid path
            except Exception:
                path_input.value = str(self.current_directory)  # Reset on error
        
        home_button.on_click(go_home)
        parent_button.on_click(go_parent)
        path_input.param.watch(navigate_to_path, 'value')
        
        return pn.Column(
            self.current_dir_display,
            pn.Row(home_button, parent_button, path_input),
            "#### File Listing (.par and .par.csv files)",
            self.file_table,
            "#### Selected Files",
            self.selected_files_display,
            sizing_mode="stretch_width"
        )
    
    def _create_file_association_controls(self):
        """Create file association controls for dual file processing."""
        
        # Temperature input (file-level metadata)
        temperature_input = pn.widgets.FloatInput(
            name="Temperature (°C)",
            value=25.0,
            step=0.1,
            width=150
        )
        
        # Applied potential interpretation
        potential_select = pn.widgets.Select(
            name="Applied Potential",
            value="2-electrode WE-CE voltage",
            options=[
                "2-electrode WE-CE voltage",
                "3-electrode WE-RE voltage", 
                "3-electrode CE-RE voltage",
                "Custom configuration"
            ],
            width=200
        )
        
        # Validation button
        validate_button = pn.widgets.Button(
            name="Validate Pairs",
            button_type="light",
            width=120
        )
        
        # Associate files button
        associate_button = pn.widgets.Button(
            name="Associate Files",
            button_type="primary",
            width=120
        )
        
        # Status message
        self.association_status = pn.pane.HTML("", sizing_mode="stretch_width")
        
        def validate_files_callback(event):
            """Validate selected dual file pairs."""
            if not self.selected_files:
                self.association_status.object = '<p style="color: orange;">No files selected</p>'
                return
            
            try:
                # Validate file pairs using backend API
                file_paths = [Path(f) for f in self.selected_files]
                result = self.api.validate_file_compatibility(file_paths)
                
                if result['success']:
                    html = "<h5>Validation Results</h5>"
                    
                    # Show dual pairs
                    if result['dual_pairs']:
                        html += "<h6>Dual File Pairs (.par + .par.csv)</h6>"
                        for pair in result['dual_pairs']:
                            status = "✓" if pair['valid'] else "✗"
                            color = "green" if pair['valid'] else "red"
                            par_name = Path(pair['par_file']).name
                            csv_name = Path(pair['csv_file']).name
                            html += f'<p style="color: {color};">{status} {par_name} + {csv_name}</p>'
                    
                    # Show individual files
                    single_files = [f for f in result['individual_files'] if not any(
                        f['file'] in [p['par_file'], p['csv_file']] for p in result.get('dual_pairs', [])
                    )]
                    if single_files:
                        html += "<h6>Single Files</h6>"
                        for file_result in single_files:
                            status = "✓" if file_result['valid'] else "✗"
                            color = "green" if file_result['valid'] else "red"
                            html += f'<p style="color: {color};">{status} {Path(file_result["file"]).name} ({file_result["type"]})</p>'
                    
                    self.association_status.object = html
                else:
                    self.association_status.object = f'<p style="color: red;">Validation failed: {result["error"]}</p>'
                    
            except Exception as e:
                self.association_status.object = f'<p style="color: red;">Validation error: {str(e)}</p>'
        
        def associate_files_callback(event):
            """Associate files with the active cell."""
            if not self.active_cell_id:
                self.association_status.object = '<p style="color: red;">No active cell selected</p>'
                return
            
            if not self.selected_files:
                self.association_status.object = '<p style="color: red;">No files selected</p>'
                return
            
            try:
                # Prepare file metadata
                file_metadata = {
                    'temperature_c': temperature_input.value,
                    'applied_potential_interpretation': potential_select.value
                }
                
                # Associate files using backend API (local file processing)
                file_paths = [Path(f) for f in self.selected_files]
                result = self.api.add_files_to_cell(
                    self.active_cell_name,  # Use cell name
                    file_paths,
                    upload_options={
                        'duplicate_handling': 'ask',
                        'temperature_c': file_metadata['temperature_c'],
                        'applied_potential_interpretation': file_metadata['applied_potential_interpretation']
                    }
                )
                
                if result['success']:
                    successful = result['summary']['successful_uploads']
                    failed = result['summary']['failed_uploads']
                    self.association_status.object = f'<p style="color: green;">✓ Associated {successful} files successfully. {failed} failed.</p>'
                    
                    # Clear selections
                    self.selected_files = []
                    self._update_selected_files_display()
                    
                    # Refresh file display
                    self.refresh_trigger += 1
                else:
                    self.association_status.object = f'<p style="color: red;">Association failed: {result["error"]}</p>'
                    
            except Exception as e:
                self.association_status.object = f'<p style="color: red;">Association error: {str(e)}</p>'
        
        validate_button.on_click(validate_files_callback)
        associate_button.on_click(associate_files_callback)
        
        return pn.Column(
            "<p><strong>File Metadata Configuration</strong></p>",
            temperature_input,
            potential_select,
            "<p><strong>Actions</strong></p>",
            pn.Row(validate_button, associate_button),
            "<p><strong>Status</strong></p>",
            self.association_status,
            sizing_mode="stretch_width"
        )
    
    def _create_file_listing_table(self):
        \"\"\"Create file listing table for current directory.\"\"\"
        try:
            # Get directory contents using backend API
            result = self.api.list_directory_contents(self.current_directory)
            
            if result['success']:
                contents = result['contents']
                if contents:
                    # Filter for supported files (.par and .par.csv)
                    supported_files = [
                        item for item in contents 
                        if item['type'] == 'file' and item['is_supported']
                    ]
                    
                    # Add parent directory entry if not root
                    if self.current_directory.parent != self.current_directory:
                        parent_entry = {
                            'name': '..',
                            'type': 'directory',
                            'size': '',
                            'modified': '',
                            'is_supported': False,
                            'path': str(self.current_directory.parent)
                        }
                        display_contents = [parent_entry] + supported_files
                    else:
                        display_contents = supported_files
                    
                    if display_contents:
                        # Convert to DataFrame
                        import pandas as pd
                        df = pd.DataFrame(display_contents)
                        
                        # Format for display
                        display_df = df[['name', 'type', 'size', 'modified']].copy()
                        display_df['size'] = display_df['size'].apply(
                            lambda x: f\"{x:,} bytes\" if x != '' and pd.notna(x) else \"\"
                        )
                        display_df = display_df.rename(columns={
                            'name': 'Name',
                            'type': 'Type',
                            'size': 'Size',
                            'modified': 'Modified'
                        })
                        
                        # Create table with selection
                        table = pn.widgets.Tabulator(
                            display_df,
                            selectable='checkbox',
                            width=580,
                            height=300,
                            pagination='local',
                            page_size=10
                        )
                        
                        # Handle file selection
                        def on_file_selection(event):
                            if hasattr(event, 'new') and event.new is not None:
                                selected_indices = event.new if isinstance(event.new, list) else [event.new]
                                selected_items = []
                                
                                for idx in selected_indices:
                                    if idx < len(display_contents):
                                        item = display_contents[idx]
                                        if item['type'] == 'directory':
                                            # Navigate to directory
                                            self.current_directory = Path(item['path'])
                                            self._refresh_file_browser()
                                            return
                                        elif item['is_supported']:
                                            selected_items.append(item['path'])
                                
                                self.selected_files = selected_items
                                self._update_selected_files_display()
                        
                        table.param.watch(on_file_selection, 'selection')
                        return table
                    else:
                        return pn.pane.HTML(\"<p>No supported files (.par, .par.csv) found in this directory</p>\", width=580)
                else:
                    return pn.pane.HTML(\"<p>Directory is empty</p>\", width=580)
            else:
                return pn.pane.HTML(f'<p style=\"color: red;\">Error: {result[\"error\"]}</p>', width=580)
                
        except Exception as e:
            return pn.pane.HTML(f'<p style=\"color: red;\">Browser error: {str(e)}</p>', width=580)
    
    def _refresh_file_browser(self):
        \"\"\"Refresh the file browser display.\"\"\"
        try:
            # Update current directory display
            self.current_dir_display.object = f\"<p><strong>Current Directory:</strong> {self.current_directory}</p>\"
            
            # Update path input (find it in the layout)
            if hasattr(self, 'layout') and self.layout:
                # Navigate to path input in layout structure and replace file table
                file_section = self.layout[4]  # File management section
                upload_section = file_section[2]  # Upload section  
                browser_column = upload_section[0]  # File browser column
                nav_row = browser_column[2]  # Navigation row
                path_input = nav_row[2]  # Path input widget
                path_input.value = str(self.current_directory)
                
                # Replace file table
                browser_column[4] = self._create_file_listing_table()
                
        except Exception as e:
            print(f\"Error refreshing file browser: {e}\")
    
    def _update_selected_files_display(self):
        \"\"\"Update the selected files display.\"\"\"
        if not self.selected_files:
            self.selected_files_display.object = \"<p>No files selected</p>\"
            return
        
        html = \"<h6>Selected Files:</h6><ul>\"
        for file_path in self.selected_files:
            file_name = Path(file_path).name
            file_type = \"PAR\" if file_path.endswith('.par') else \"PAR CSV\" if file_path.endswith('.par.csv') else \"Unknown\"
            html += f\"<li><strong>{file_name}</strong> ({file_type})</li>\"
        html += \"</ul>\"
        
        self.selected_files_display.object = html
    
    @pn.depends('refresh_trigger', watch=True)
    def refresh_cells_table(self, *args):
        """Refresh the cells table when trigger changes."""
        # The table will refresh automatically due to the @pn.depends decorator
        pass