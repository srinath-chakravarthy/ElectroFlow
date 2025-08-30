"""
Professional File Uploader Component - Large File Support with FileDropper

Clear step-by-step file processing with support for large files (>100MB) using Panel's FileDropper widget.
"""

import panel as pn
import param
from pathlib import Path

class FileUploader(param.Parameterized):
    """
    Professional file upload component with large file support via FileDropper.

    Features:
    - Large file support (>100MB) using FileDropper
    - Clear step-by-step workflow  
    - Professional visual feedback
    - Progress indicators
    - Clean file management
    - Drag & drop interface
    """

    selected_file = param.String(default="", doc="Currently selected file ID")
    status_message = param.String(default="", doc="Status message for main app")

    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        self.current_cell = None
        self._cached_files = {}  # Cache file info to avoid redundant API calls
        self._create_components()

    def _create_components(self):
        """Create professional UI components with FileDropper."""

        # Current cell display
        self.cell_display = pn.pane.HTML(
            """<div style='background: #FFF3E0; padding: 10px; border-radius: 4px; 
                          border-left: 4px solid #FF9800; text-align: center;'>
               <strong>Please select a cell first</strong>
               </div>""",
            margin=(5, 5)
        )

        # File droppers for large file support
        # FIXED: Larger, more prominent FileDroppers
        self.metadata_dropper = pn.widgets.FileDropper(
            # accepted_filetypes=['.par', '.PAR'],
            multiple=False,
            max_file_size='200MB',
            height=120,  # Much larger
            width=350,  # Wider
            margin=(10, 5)
        )

        self.data_dropper = pn.widgets.FileDropper(
            # accepted_filetypes=['.csv', '.par.csv', '.PAR.CSV', '.CSV'],
            multiple=False,
            max_file_size='200MB',
            height=120,  # Much larger
            width=350,  # Wider
            margin=(10, 5)
        )

        self.temperature_input = pn.widgets.NumberInput(
            value=25.0,
            start=-50,
            end=100,
            step=0.1,
            width=100,
            margin=(5, 5)
        )

        self.upload_btn = pn.widgets.Button(
            name="🚀 Process Files",
            button_type="primary",
            width=150,
            disabled=True,
            margin=(10, 5)
        )
        self.upload_btn.on_click(self._on_upload_files)

        # Processing status
        self.processing_status = pn.pane.HTML(
            "<div style='color: #666; font-size: 14px; padding: 5px;'>Ready for upload</div>",
            margin=(5, 5)
        )

        # File list components
        self.file_select = pn.widgets.Select(
            options=[],
            width=280,
            size=8,
            margin=(5, 5)
        )
        self.file_select.param.watch(self._on_file_selected, 'value')

        self.file_info_display = pn.pane.HTML(
            "<div style='color: #666; font-style: italic;'>Select a file to view details</div>",
            margin=(5, 5)
        )

        # File management buttons
        self.analyze_btn = pn.widgets.Button(
            name="📊 Analyze",
            button_type="primary",
            width=90,
            disabled=True,
            margin=(5, 5)
        )
        self.analyze_btn.on_click(self._on_analyze_file)

        self.delete_btn = pn.widgets.Button(
            name="🗑️ Delete",
            button_type="primary",
            width=80,
            disabled=True,
            margin=(5, 5)
        )
        self.delete_btn.on_click(self._on_delete_file)

        # File dropper watchers for upload readiness
        self.metadata_dropper.param.watch(self._check_upload_ready, 'value')
        self.data_dropper.param.watch(self._check_upload_ready, 'value')

    @property
    def panel(self):
        """Return professional card layout with proper FileDropper styling."""

        # Professional header (restore gradient)
        header = pn.pane.HTML("""
        <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white; 
                    padding: 15px; border-radius: 8px 8px 0 0; margin: 0;'>
            <h2 style='margin: 0; font-size: 18px; font-weight: 600;'>
                📁 File Operations
            </h2>
        </div>
        """, margin=(0, 0))

        # Current cell section
        cell_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 14px; font-weight: 600; margin: 15px 5px 10px 5px;'>
                Current Cell
            </div>
            """),
            self.cell_display,
            margin=(10, 10)
        )

        # Upload section with prominent drop zones
        # SNIPPET: Replace the upload_section in your panel property with this:

        upload_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                1. Upload & Process Files (Drag & Drop)
            </div>
            """),

            # Instructions
            pn.pane.HTML("""
            <div style='background: #F8F9FA; padding: 10px; border-radius: 4px; margin: 5px;'>
                Drag & drop large VersaStudio files (supports >100MB)
            </div>
            """),

            # Row 1: Metadata drop zone
            pn.Row(
                pn.pane.HTML(
                    "<label style='font-weight: 500; color: #555; font-size: 14px;'>Metadata File (.par):</label>"),
                margin=(10, 5)
            ),
            pn.Row(
                self.metadata_dropper,
                pn.pane.HTML("<small style='color: #666; margin-left: 10px;'>Supports up to 200MB</small>"),
                margin=(5, 5)
            ),

            # Row 2: Data drop zone
            pn.Row(
                pn.pane.HTML(
                    "<label style='font-weight: 500; color: #555; font-size: 14px;'>Data File (.par.csv):</label>"),
                margin=(10, 5)
            ),
            pn.Row(
                self.data_dropper,
                pn.pane.HTML("<small style='color: #666; margin-left: 10px;'>Supports up to 200MB</small>"),
                margin=(5, 5)
            ),

            # Row 3: Controls
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555;'>Temperature (°C):</label>"),
                    self.temperature_input,
                    width=150
                ),
                pn.Spacer(width=20),
                pn.Column(
                    pn.Spacer(height=20),
                    self.upload_btn,
                    width=200
                ),
                margin=(15, 5)
            ),

            self.processing_status,
            margin=(10, 10)
        )

        # File management section (restore original styling)
        files_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                2. Processed Files
            </div>
            """),

            pn.pane.HTML("""
            <div style='font-size: 12px; color: #666; margin: 5px; padding: 5px;'>
                Select a processed file to view details and analyze data:
            </div>
            """),

            self.file_select,
            self.file_info_display,

            pn.Row(
                self.analyze_btn,
                self.delete_btn,
                margin=(10, 5)
            ),

            margin=(10, 10)
        )

        # Complete card with proper styling
        card_content = pn.Column(
            cell_section,
            upload_section,
            files_section,
            styles={'background': 'white', 'border-radius': '0 0 8px 8px',
                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'margin': '0'}
        )

        return pn.Column(
            header,
            card_content,
            width=800,  # Fixed width
            margin=(10, 10),
            styles={'border-radius': '8px', 'overflow': 'hidden'}
        )

    def _add_dropper_styling(self):
        """Add custom CSS for FileDropper styling."""
        pn.config.raw_css.append("""
        .bk-input-group .file-dropper {
            border: 2px dashed #ccc !important;
            border-radius: 8px !important;
            background: #fafafa !important;
            transition: all 0.3s ease !important;
        }

        .bk-input-group .file-dropper:hover {
            border-color: #1976D2 !important;
            background: #f0f8ff !important;
        }

        .bk-input-group .file-dropper.dragover {
            border-color: #4CAF50 !important;
            background: #f0fff0 !important;
        }
        """)

    def set_current_cell(self, cell_name: str):
        """Set current cell and refresh UI."""
        self.current_cell = cell_name
        if cell_name:
            self.cell_display.object = f"""
            <div style='background: #E8F5E8; padding: 10px; border-radius: 4px; 
                        border-left: 4px solid #4CAF50; text-align: center;'>
                <strong>Selected Cell: {cell_name}</strong>
            </div>
            """
            self._refresh_file_list()
        else:
            self.cell_display.object = """
            <div style='background: #FFF3E0; padding: 10px; border-radius: 4px; 
                        border-left: 4px solid #FF9800; text-align: center;'>
                <strong>Please select a cell first</strong>
            </div>
            """
            self.file_select.options = []
            self.file_info_display.object = "<div style='color: #666; font-style: italic;'>No cell selected</div>"

        self._check_upload_ready(None)

    def _refresh_file_list(self):
        """Refresh the file list for current cell."""
        if not self.current_cell:
            return

        try:
            files = self.api.get_cell_files(self.current_cell)
            
            if files:
                # Cache file information for quick access
                self._cached_files = {file_info['file_id']: file_info for file_info in files}
                
                # Format options as (display_name, file_id) tuples  
                file_options = []
                for file_info in files:
                    # Create display name with status indicators
                    status_indicator = "✓" if file_info.get('segment_count', 0) > 0 else "⚠️"
                    segment_text = f"({file_info.get('segment_count', 0)} segments)" if file_info.get('segment_count', 0) > 0 else "(no segments)"
                    
                    display_name = f"{status_indicator} {file_info['original_filename']}... {segment_text}"
                    file_options.append((display_name, file_info['file_id']))
                
                self.file_select.options = file_options
            else:
                self.file_select.options = []
                self._cached_files = {}
                
        except Exception as e:
            self.file_select.options = []
            self._cached_files = {}
            print(f"Error refreshing files: {e}")

    def refresh_files(self):
        """Public method to refresh file list."""
        self._refresh_file_list()

    def _check_upload_ready(self, event):
        """Check if upload is ready with visual feedback."""
        
        # FileDropper.value is a dictionary mapping filenames to content
        has_metadata = self.metadata_dropper.value is not None and len(self.metadata_dropper.value) > 0
        has_data = self.data_dropper.value is not None and len(self.data_dropper.value) > 0
        
        print(f"Check upload ready - Metadata: {has_metadata}, Data: {has_data}, Cell: {self.current_cell}")
        self.upload_btn.disabled = not (has_metadata and has_data and self.current_cell)
        print(f"Button disabled: {self.upload_btn.disabled}")

    def _update_processing_status(self, message, status_type="info"):
        """Update processing status with color coding."""
        colors = {
            "info": "#666",
            "processing": "#2196F3", 
            "success": "#4CAF50",
            "error": "#F44336",
            "warning": "#FF9800"
        }
        
        color = colors.get(status_type, "#666")
        self.processing_status.object = f"""
        <div style='color: {color}; font-size: 14px; padding: 5px; font-weight: 500;'>
            {message}
        </div>
        """

    def _on_upload_files(self, event):
        """Handle file upload with progress feedback using FileDropper."""
        if not self.current_cell:
            self.status_message = "No cell selected"
            return

        # FileDropper stores files as dictionary mapping filenames to content
        if not (self.metadata_dropper.value and self.data_dropper.value and 
                len(self.metadata_dropper.value) > 0 and len(self.data_dropper.value) > 0):
            self.status_message = "Both .par and .par.csv files required"
            return

        # Show processing state
        self._update_processing_status("🔄 Processing files...", "processing")
        self.upload_btn.disabled = True

        try:
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # FileDropper stores files as dictionary: filename -> content
                metadata_filename = list(self.metadata_dropper.value.keys())[0]
                metadata_content = self.metadata_dropper.value[metadata_filename]
                
                data_filename = list(self.data_dropper.value.keys())[0]
                data_content = self.data_dropper.value[data_filename]

                # Save uploaded files temporarily
                metadata_path = temp_path / metadata_filename
                if isinstance(metadata_content, str):
                    metadata_path.write_text(metadata_content, encoding='utf-8')
                else:
                    metadata_path.write_bytes(metadata_content)

                data_path = temp_path / data_filename
                if isinstance(data_content, str):
                    data_path.write_text(data_content, encoding='utf-8')
                else:
                    data_path.write_bytes(data_content)

                # Process files
                result = self.api.process_dual_files(
                    metadata_path,
                    data_path,
                    self.current_cell,
                    temperature_c=self.temperature_input.value
                )

                if result.success:
                    self.status_message = f"Successfully processed {result.file_id}"
                    self._update_processing_status(f"✅ Successfully processed: {result.file_id}", "success")

                    # Clear upload widgets - FileDropper uses empty dict
                    self.metadata_dropper.value = {}
                    self.data_dropper.value = {}
                    self._check_upload_ready(None)

                    # Refresh file list
                    self._refresh_file_list()

                else:
                    self.status_message = f"Processing failed: {result.error}"
                    self._update_processing_status(f"❌ Processing failed: {result.error}", "error")

        except Exception as e:
            self.status_message = f"Upload error: {str(e)}"
            self._update_processing_status(f"❌ Upload error: {str(e)}", "error")
        finally:
            self.upload_btn.disabled = False

    def _on_file_selected(self, event):
        """Handle file selection with info display."""
        file_id = event.new
        if file_id:
            if isinstance(file_id, tuple):
                file_id = file_id[1]
            elif not isinstance(file_id, str):
                file_id = str(file_id)

            # Update selected file
            self.selected_file = file_id
            
            # Get file info from cache (already loaded by _refresh_file_list)
            try:
                file_info = self._cached_files.get(file_id)
                if file_info:
                    info_html = f"""
                    <div style='background: #F8F9FA; padding: 10px; border-radius: 4px; font-size: 13px;'>
                        <strong>{file_info.get('original_filename', 'Unknown')}</strong><br>
                        <small style='color: #666;'>
                        Size: {file_info.get('file_size_bytes', 0) / (1024*1024):.1f} MB<br>
                        Segments: {file_info.get('segment_count', 0)}<br>
                        Status: {file_info.get('processing_status', 'Unknown')}
                        </small>
                    </div>
                    """
                    self.file_info_display.object = info_html
                    
                    # Enable buttons
                    self.analyze_btn.disabled = False
                    self.delete_btn.disabled = False
                else:
                    self.file_info_display.object = "<div style='color: #f44336;'>File info not found in cache</div>"
                    
            except Exception as e:
                self.file_info_display.object = f"<div style='color: #f44336;'>Error loading file info: {str(e)}</div>"
        else:
            self.selected_file = ""
            self.file_info_display.object = "<div style='color: #666; font-style: italic;'>Select a file to view details</div>"
            self.analyze_btn.disabled = True
            self.delete_btn.disabled = True

    def _on_analyze_file(self, event):
        """Handle file analysis."""
        del event  # Unused parameter
        if self.selected_file:
            self.status_message = f"analyze:{self.selected_file}"

    def _on_delete_file(self, event):
        """Handle file deletion with confirmation."""
        del event  # Unused parameter
        file_selection = self.file_select.value
        if not file_selection:
            return

        # Extract file_id from tuple if needed (UI returns (display_name, file_id))
        if isinstance(file_selection, tuple):
            file_id = file_selection[1]  # Get the file_id part
        else:
            file_id = file_selection

        if not file_id:
            return

        try:
            result = self.api.delete_file(file_id)
            if result.success:
                self.status_message = f"File deleted successfully"
                self._refresh_file_list()
                # Clear selection
                self.file_select.value = None
                self._on_file_selected(type('Event', (), {'new': None})())
            else:
                self.status_message = f"Failed to delete file: {result.error}"

        except Exception as e:
            self.status_message = f"Failed to delete file {file_id}: Database operation failed: {str(e)}"