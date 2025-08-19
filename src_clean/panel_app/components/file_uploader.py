"""
File Uploader Component

Handles file upload, processing, and file management in Panel interface.
"""

import panel as pn
import param
from pathlib import Path

class FileUploader(param.Parameterized):
    """
    File upload and management component.
    
    Provides:
    - File upload (.par + .par.csv)
    - File processing and validation
    - File list with delete functionality
    - File selection for visualization
    """
    
    selected_file = param.String(default="", doc="Currently selected file ID")
    status_message = param.String(default="", doc="Status message for main app")
    
    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        self.current_cell = None
        
        self._create_components()
    
    def _create_components(self):
        """Create the UI components."""
        self.header = pn.pane.HTML("""
        <h3 style='margin: 10px 0; color: #2E4057;'>
            📁 File Operations
        </h3>
        """)
        
        # File upload section
        self.upload_info = pn.pane.HTML(
            "<p style='color: #666;'>Select a cell first</p>"
        )
        
        # File list
        self.file_select = pn.widgets.Select(
            name="Select File",
            options=[],
            width=320,
            size=10
        )
        self.file_select.param.watch(self._on_file_selected, 'value')
        
        # Delete button
        self.delete_file_btn = pn.widgets.Button(
            name="Delete File",
            button_type="light", 
            width=120,
            disabled=True
        )
        self.delete_file_btn.on_click(self._on_delete_file)
        
        # Upload widgets
        self.metadata_upload = pn.widgets.FileInput(
            accept=".par",
            multiple=False,
            name="Select .par file",
            width=200
        )
        
        self.data_upload = pn.widgets.FileInput(
            accept=".csv", 
            multiple=False,
            name="Select .par.csv file",
            width=200
        )
        
        self.upload_btn = pn.widgets.Button(
            name="Process Files",
            button_type="primary",
            width=120,
            disabled=True
        )
        self.upload_btn.on_click(self._on_upload_files)
        
        # Watch for file selections to enable upload
        self.metadata_upload.param.watch(self._check_upload_ready, 'value')
        self.data_upload.param.watch(self._check_upload_ready, 'value')
    
    @property  
    def panel(self):
        """Return the Panel layout."""
        return pn.Column(
            self.header,
            self.upload_info,
            
            # Upload section
            pn.pane.HTML("<b>Upload New Files:</b>"),
            self.metadata_upload,
            self.data_upload,
            self.upload_btn,
            
            pn.Spacer(height=20),
            
            # File list section
            pn.pane.HTML("<b>Processed Files:</b>"),
            self.file_select,
            self.delete_file_btn,
            
            width=340,
            margin=(10, 10)
        )
    
    def set_current_cell(self, cell_name: str):
        """Set current cell and refresh file list."""
        self.current_cell = cell_name
        if cell_name:
            self.upload_info.object = f"<p><b>Current Cell:</b> {cell_name}</p>"
            self._refresh_file_list()
        else:
            self.upload_info.object = "<p style='color: #666;'>Select a cell first</p>"
            self.file_select.options = []
    
    def _refresh_file_list(self):
        """Refresh file list for current cell."""
        if not self.current_cell:
            return
            
        try:
            files = self.api.get_cell_files(self.current_cell)
            
            if files:
                options = []
                for file_info in files:
                    display_name = f"{file_info['original_filename']} ({file_info['segment_count']} segments)"
                    options.append((display_name, file_info['file_id']))
                
                self.file_select.options = options
            else:
                self.file_select.options = []
                
        except Exception as e:
            self.status_message = f"Error loading files: {str(e)}"
            
    def refresh_files(self):
        """Public method to refresh file list."""
        self._refresh_file_list()
    
    def _on_file_selected(self, event):
        """Handle file selection."""
        file_id = event.new
        if file_id:
            self.selected_file = file_id
            self.delete_file_btn.disabled = False
        else:
            self.delete_file_btn.disabled = True
    
    def _check_upload_ready(self, event):
        """Check if upload files are ready."""
        has_metadata = self.metadata_upload.value is not None
        has_data = self.data_upload.value is not None
        self.upload_btn.disabled = not (has_metadata and has_data and self.current_cell)
    
    def _on_upload_files(self, event):
        """Handle file upload and processing."""
        if not self.current_cell:
            self.status_message = "No cell selected"
            return
            
        if not (self.metadata_upload.value and self.data_upload.value):
            self.status_message = "Both .par and .par.csv files required"
            return
            
        try:
            # Save uploaded files temporarily
            from tempfile import TemporaryDirectory
            import shutil
            
            with TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Save metadata file
                metadata_path = temp_path / self.metadata_upload.filename
                metadata_path.write_bytes(self.metadata_upload.value)
                
                # Save data file  
                data_path = temp_path / self.data_upload.filename
                data_path.write_bytes(self.data_upload.value)
                
                # Process files
                result = self.api.process_dual_files(
                    self.current_cell,
                    metadata_path,
                    data_path
                )
                
                if result.success:
                    self.status_message = f"Successfully processed {result.file_id}"
                    
                    # Clear upload widgets
                    self.metadata_upload.value = None
                    self.data_upload.value = None
                    self.upload_btn.disabled = True
                    
                    # Refresh file list
                    self._refresh_file_list()
                    
                else:
                    self.status_message = f"Processing failed: {result.error}"
                    
        except Exception as e:
            self.status_message = f"Upload error: {str(e)}"
    
    def _on_delete_file(self, event):
        """Handle file deletion."""
        file_id = self.file_select.value
        if not file_id:
            return
            
        try:
            success = self.api.delete_file(file_id)
            if success:
                self.status_message = f"Deleted file: {file_id}"
                self._refresh_file_list()
                self.selected_file = ""
            else:
                self.status_message = f"Failed to delete file: {file_id}"
                
        except Exception as e:
            self.status_message = f"Delete error: {str(e)}"