"""
Cell Manager Tab V2 - Simplified and Clean Implementation

Focus on working event handling and basic functionality.
"""

import panel as pn
import param
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import tempfile


class CellManagerTabV2(param.Parameterized):
    """
    Simplified cell management interface with working event handling.
    """
    
    # Parameters for reactive UI
    selected_cell = param.String(default="", doc="Selected cell name")
    status_message = param.String(default="Ready", doc="Status message")
    
    def __init__(self, backend_api, **params):
        super().__init__(**params)
        self.api = backend_api
        self.layout = None
        self.cells_data = []  # Store cells data
        self.file_input = None
        self.setup_layout()
    
    def setup_layout(self):
        """Setup the complete layout with working components."""
        
        # Status display (reactive)
        status_display = pn.bind(self._create_status_display, self.param.status_message, self.param.selected_cell)
        
        # Cell selector (working dropdown)
        cell_selector = self._create_cell_selector()
        
        # File upload section
        file_upload_section = self._create_file_upload_section()
        
        # Cells table (with selection)
        cells_table = self._create_cells_table()
        
        # Active cell files (reactive)
        active_files = pn.bind(self._create_active_files_display, self.param.selected_cell)
        
        # Set up param watchers for reactive updates
        self.param.watch(self._on_selected_cell_change, 'selected_cell')
        self.param.watch(self._on_status_change, 'status_message')
        
        self.layout = pn.Column(
            "## Cell & File Management V2",
            status_display,
            "---",
            pn.Row(
                pn.Column(
                    "### Select Cell",
                    cell_selector,
                    width=300
                ),
                pn.Column(
                    "### All Cells",
                    cells_table,
                    width=500
                )
            ),
            "---",
            file_upload_section,
            "---",
            "### Active Cell Files",
            active_files,
            width=1200
        )
    
    def _on_selected_cell_change(self, event):
        """Handle selected cell parameter changes."""
        print(f"V2 DEBUG: Selected cell changed to: {event.new}")
        if event.new:
            print(f"V2 DEBUG: Cell '{event.new}' is now active")
        else:
            print("V2 DEBUG: No cell selected")
    
    def _on_status_change(self, event):
        """Handle status message parameter changes."""
        print(f"V2 DEBUG: Status changed to: {event.new}")
    
    def _create_status_display(self, status_message, selected_cell):
        """Create reactive status display."""
        if selected_cell:
            html = f"""
            <div style="padding: 10px; background-color: #e8f5e8; border: 1px solid #4CAF50;">
                <strong>Status:</strong> {status_message}<br>
                <strong>Active Cell:</strong> {selected_cell}
            </div>
            """
        else:
            html = f"""
            <div style="padding: 10px; background-color: #f5f5f5; border: 1px solid #ccc;">
                <strong>Status:</strong> {status_message}<br>
                <em>No cell selected</em>
            </div>
            """
        return pn.pane.HTML(html, width=600)
    
    def _create_cell_selector(self):
        """Create working dropdown cell selector."""
        # Get cells from API
        result = self.api.get_all_cells()
        if not result['success']:
            return pn.pane.HTML(f'<p style="color: red;">Error: {result["error"]}</p>')
        
        self.cells_data = result['cells']
        if not self.cells_data:
            return pn.pane.HTML('<p>No cells available. Create cells first.</p>')
        
        # Create dropdown
        cell_names = [""] + [cell['cell_name'] for cell in self.cells_data]
        
        dropdown = pn.widgets.Select(
            name="Select Cell",
            options=cell_names,
            value="",
            width=250
        )
        
        # Simple working event handler (using the pattern that works)
        def on_cell_select(event):
            print(f"V2 DEBUG: Cell selected: {event.new}")
            self.selected_cell = event.new if event.new else ""
            if event.new:
                self.status_message = f"Selected cell: {event.new}"
            else:
                self.status_message = "No cell selected"
        
        dropdown.param.watch(on_cell_select, 'value')
        
        return dropdown
    
    def _create_cells_table(self):
        """Create simple read-only cells table."""
        if not self.cells_data:
            return pn.pane.HTML("<p>No cells available</p>")
        
        # Create simple table
        df = pd.DataFrame(self.cells_data)
        display_columns = ['cell_name', 'description', 'chemistry', 'created_at']
        available_columns = [col for col in display_columns if col in df.columns]
        display_df = df[available_columns]
        
        # Rename for display
        column_names = {
            'cell_name': 'Cell Name',
            'description': 'Description',
            'chemistry': 'Chemistry',
            'created_at': 'Created'
        }
        display_df = display_df.rename(columns=column_names)
        
        table = pn.widgets.Tabulator(
            display_df,
            pagination='local',
            page_size=10,
            width=480,
            height=300,
            selectable=1  # Enable single row selection
        )
        
        # Add selection event handler for Tabulator
        def on_table_selection(event):
            print(f"V2 DEBUG: Tabulator selection event: {event}")
            if hasattr(event, 'new') and event.new is not None:
                try:
                    if isinstance(event.new, list) and len(event.new) > 0:
                        selected_index = event.new[0]
                        if 0 <= selected_index < len(self.cells_data):
                            selected_cell = self.cells_data[selected_index]
                            cell_name = selected_cell['cell_name']
                            print(f"V2 DEBUG: Tabulator selected cell: {cell_name}")
                            self.selected_cell = cell_name
                            self.status_message = f"Selected cell: {cell_name} (from table)"
                except Exception as e:
                    print(f"V2 DEBUG: Tabulator selection error: {e}")
        
        table.param.watch(on_table_selection, 'selection')
        
        return table
    
    def _create_file_upload_section(self):
        """Create a working file upload section with FileInput widget."""
        
        # File input widget
        self.file_input = pn.widgets.FileInput(
            accept='.par,.csv',
            multiple=True,
            sizing_mode="stretch_width",
            height=100
        )
        
        # Selected files display
        self.selected_files_display = pn.pane.HTML(
            "<p>No files selected. Choose .par and .par.csv files above.</p>",
            sizing_mode="stretch_width",
            height=100
        )
        
        # The only event handler is on the FileInput's 'value'
        # to update the display, not trigger processing
        def on_file_change(event):
            if event.new:
                filenames = [f[0] for f in event.new]
                self._update_file_upload_display(filenames)
            else:
                self._update_file_upload_display([])
        
        self.file_input.param.watch(on_file_change, 'value')
        
        # Upload button is the single point of entry for the upload process
        upload_button = pn.widgets.Button(
            name="Upload Files",
            button_type="primary",
            width=120
        )
        
        # Status area
        self.upload_status = pn.pane.HTML("", width=500, height=100)
        
        # Bind the entire upload workflow to the button click
        upload_button.on_click(self._handle_upload)
        
        return pn.Column(
            "### File Upload",
            "**Select .par and .par.csv files from your computer:**",
            self.file_input,
            "#### Selected Files",
            self.selected_files_display,
            pn.Row(
                upload_button, 
                pn.Spacer(width=20)
            ),
            self.upload_status
        )
    
    def _create_active_files_display(self, selected_cell):
        """Create reactive files display for selected cell."""
        if not selected_cell:
            return pn.pane.HTML("<p>Select a cell to view its files</p>")
        
        # Get cell ID from name
        cell_id = None
        for cell in self.cells_data:
            if cell['cell_name'] == selected_cell:
                cell_id = cell['id']
                break
        
        if not cell_id:
            return pn.pane.HTML(f"<p>Cell '{selected_cell}' not found</p>")
        
        # Get files for this cell
        result = self.api.get_cell_files(cell_id)
        if not result['success']:
            return pn.pane.HTML(f'<p style="color: red;">Error: {result["error"]}</p>')
        
        files = result['files']
        if not files:
            return pn.pane.HTML(f"<p>No files found for {selected_cell}</p>")
        
        # Create simple files table
        df = pd.DataFrame(files)
        display_columns = ['original_filename', 'file_type', 'processing_status', 'upload_timestamp']
        available_columns = [col for col in display_columns if col in df.columns]
        display_df = df[available_columns]
        
        # Rename columns
        column_names = {
            'original_filename': 'File Name',
            'file_type': 'Type',
            'processing_status': 'Status',
            'upload_timestamp': 'Uploaded'
        }
        display_df = display_df.rename(columns=column_names)
        
        return pn.widgets.Tabulator(
            display_df,
            pagination='local',
            page_size=10,
            width=800,
            height=200
        )
    
    def _on_file_selection_change(self, event):
        """Handle file selection changes."""
        try:
            print(f"V2 DEBUG: File selection changed. Event: {event}")
            print(f"V2 DEBUG: Event.new: {event.new}")
            print(f"V2 DEBUG: Event.new type: {type(event.new)}")
            
            if event.new:
                print(f"V2 DEBUG: Event.new length: {len(event.new)}")
                print(f"V2 DEBUG: First item type: {type(event.new[0]) if len(event.new) > 0 else 'N/A'}")
                
                # Safely extract filenames
                filenames = []
                for i, item in enumerate(event.new):
                    print(f"V2 DEBUG: Item {i}: {type(item)} - {item}")
                    if isinstance(item, tuple) and len(item) >= 1:
                        filenames.append(item[0])
                    else:
                        print(f"V2 DEBUG: Unexpected item format: {item}")
                        filenames.append(str(item))
                
                print(f"V2 DEBUG: Extracted filenames: {filenames}")
                self.status_message = f"Selected {len(filenames)} files: {', '.join(filenames[:3])}{'...' if len(filenames) > 3 else ''}"
            else:
                print("V2 DEBUG: No files selected")
                self.status_message = "No files selected"
                
            print("V2 DEBUG: File selection handler completed successfully")
            
        except Exception as e:
            print(f"V2 DEBUG: CRITICAL ERROR in file selection handler: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                self.status_message = f"File selection error: {str(e)}"
            except Exception as status_error:
                print(f"V2 DEBUG: Failed to update status: {status_error}")
    
    def _handle_upload(self, event):
        """Handle file upload button click."""
        try:
            print("V2 DEBUG: Upload button clicked")
            print(f"V2 DEBUG: Selected cell: {self.selected_cell}")
            print(f"V2 DEBUG: File input value: {self.file_input.value}")
            print(f"V2 DEBUG: File input value type: {type(self.file_input.value)}")
            
            if not self.selected_cell:
                self.upload_status.object = '<p style="color: red;">Please select a cell first</p>'
                self.status_message = "Error: No cell selected"
                return
            
            if not self.file_input.value:
                self.upload_status.object = '<p style="color: red;">Please select files first</p>'
                self.status_message = "Error: No files selected"
                return
            
            self.status_message = "Uploading files..."
            print("V2 DEBUG: Starting file processing...")
            
            # Save files to temp directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            temp_paths = []
            
            print(f"V2 DEBUG: Processing {len(self.file_input.value)} files")
            for i, (filename, file_obj) in enumerate(self.file_input.value):
                print(f"V2 DEBUG: Processing file {i+1}: {filename}")
                print(f"V2 DEBUG: File object type: {type(file_obj)}")
                print(f"V2 DEBUG: File size: {len(file_obj) if hasattr(file_obj, '__len__') else 'unknown'}")
                
                temp_path = temp_dir / filename
                print(f"V2 DEBUG: Writing to: {temp_path}")
                
                try:
                    temp_path.write_bytes(file_obj)
                    temp_paths.append(temp_path)
                    print(f"V2 DEBUG: Successfully saved {filename}")
                except Exception as write_error:
                    print(f"V2 DEBUG: Failed to write {filename}: {write_error}")
                    raise write_error
            
            print(f"V2 DEBUG: All files saved. Calling API...")
            print(f"V2 DEBUG: API call parameters:")
            print(f"  - selected_cell: {self.selected_cell}")
            print(f"  - temp_paths: {temp_paths}")
            
            # Upload via API
            result = self.api.add_files_to_cell(
                self.selected_cell,
                temp_paths,
                upload_options={'duplicate_handling': 'ask'}
            )
            
            print(f"V2 DEBUG: API result: {result}")
            
            if result['success']:
                summary = result['summary']
                self.upload_status.object = f'''
                <div style="color: green;">
                    <p><strong>Upload Complete!</strong></p>
                    <p>Successful: {summary['successful_uploads']}</p>
                    <p>Failed: {summary['failed_uploads']}</p>
                </div>
                '''
                self.status_message = f"Uploaded {summary['successful_uploads']} files"
                # Clear file input
                self.file_input.value = []
            else:
                self.upload_status.object = f'<p style="color: red;">Upload failed: {result["error"]}</p>'
                self.status_message = "Upload failed"
            
            # Clean up temp files
            print("V2 DEBUG: Cleaning up temp files...")
            for temp_path in temp_paths:
                try:
                    temp_path.unlink(missing_ok=True)
                    print(f"V2 DEBUG: Cleaned up: {temp_path}")
                except Exception as cleanup_error:
                    print(f"V2 DEBUG: Cleanup failed for {temp_path}: {cleanup_error}")
            
            print("V2 DEBUG: Upload handler completed successfully")
                    
        except Exception as e:
            print(f"V2 DEBUG: CRITICAL ERROR in upload handler: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                self.upload_status.object = f'<p style="color: red;">Error: {str(e)}</p>'
                self.status_message = f"Upload error: {str(e)}"
            except Exception as status_error:
                print(f"V2 DEBUG: Failed to update status: {status_error}")
    
    def _update_file_upload_display(self, filenames):
        """Update the file upload display with selected filenames."""
        if not filenames:
            self.selected_files_display.object = "<p>No files selected. Choose .par and .par.csv files above.</p>"
            self.status_message = "No files selected"
            return
        
        html = "<h6>Selected Files:</h6><ul>"
        for filename in filenames:
            file_type = "PAR" if filename.endswith('.par') else "PAR CSV" if filename.endswith('.par.csv') else "CSV"
            html += f"<li><strong>{filename}</strong> ({file_type})</li>"
        html += "</ul>"
        
        self.selected_files_display.object = html
        self.status_message = f"Selected {len(filenames)} files: {', '.join(filenames[:3])}{'...' if len(filenames) > 3 else ''}"
        print(f"V2 DEBUG: Updated display with {len(filenames)} files: {filenames}")