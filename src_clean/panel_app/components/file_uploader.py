"""
Professional File Uploader Component - Clean Workflow Design

Clear step-by-step file processing with professional styling and visual feedback.
"""

import panel as pn
import param
from pathlib import Path

class FileUploader(param.Parameterized):
    """
    Professional file upload component with clear workflow design.

    Features:
    - Clear step-by-step workflow
    - Professional visual feedback
    - Progress indicators
    - Clean file management
    """

    selected_file = param.String(default="", doc="Currently selected file ID")
    status_message = param.String(default="", doc="Status message for main app")

    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        self.current_cell = None
        self._create_components()

    def _create_components(self):
        """Create professional UI components."""

        # Current cell display
        self.cell_display = pn.pane.HTML(
            """<div style='background: #FFF3E0; padding: 10px; border-radius: 4px; 
                          border-left: 4px solid #FF9800; text-align: center;'>
               <strong>Please select a cell first</strong>
               </div>""",
            margin=(5, 5)
        )

        # Upload section components
        self.metadata_upload = pn.widgets.FileInput(
            accept=".par",
            multiple=False,
            width=280,
            margin=(5, 5)
        )

        self.data_upload = pn.widgets.FileInput(
            accept=".csv",
            multiple=False,
            width=280,
            margin=(5, 5)
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
        
        # Debug button for testing
        self.debug_btn = pn.widgets.Button(
            name="🔍 Check Status",
            button_type="light",
            width=120,
            margin=(5, 5)
        )
        self.debug_btn.on_click(self._debug_status)

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

        self.delete_file_btn = pn.widgets.Button(
            name="🗑️ Delete",
            button_type="light",
            width=90,
            disabled=True,
            margin=(5, 5)
        )
        self.delete_file_btn.on_click(self._on_delete_file)

        self.refresh_files_btn = pn.widgets.Button(
            name="🔄 Refresh",
            button_type="light",
            width=90,
            margin=(5, 5)
        )
        self.refresh_files_btn.on_click(self._on_refresh_files)

        # Watch for file selections to enable upload
        self.metadata_upload.param.watch(self._check_upload_ready, 'value')
        self.data_upload.param.watch(self._check_upload_ready, 'value')
        
        # Also watch for filename changes (alternative trigger)
        self.metadata_upload.param.watch(self._on_file_uploaded, 'filename')
        self.data_upload.param.watch(self._on_file_uploaded, 'filename')

    @property
    def panel(self):
        """Return professional card layout."""

        # Header with icon
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

        # Upload workflow section
        upload_section = pn.Column(
            pn.pane.HTML("""
            <div style='color: #2E4057; font-size: 16px; font-weight: 600; 
                        margin: 20px 5px 10px 5px; padding-bottom: 5px; 
                        border-bottom: 2px solid #E0E0E0;'>
                1. Upload & Process Files
            </div>
            """),

            # Step indicators
            pn.pane.HTML("""
            <div style='background: #F8F9FA; padding: 10px; border-radius: 4px; margin: 5px;'>
                <div style='font-size: 12px; color: #666; margin-bottom: 8px;'>
                    Upload paired VersaStudio files for processing:
                </div>
                <div style='font-size: 11px; color: #999;'>
                    • .par file contains metadata and ActionID mappings<br>
                    • .par.csv file contains the actual measurement data
                </div>
            </div>
            """),

            # File inputs
            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555; font-size: 14px;'>Metadata File (.par):</label>"),
                self.metadata_upload,
                margin=(5, 5)
            ),

            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555; font-size: 14px;'>Data File (.par.csv):</label>"),
                self.data_upload,
                margin=(5, 5)
            ),

            # Temperature and process
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555; font-size: 14px;'>Temperature (°C):</label>"),
                    self.temperature_input,
                    width=120
                ),
                pn.Spacer(width=10),
                pn.Column(
                    pn.Spacer(height=20),
                    pn.Row(self.upload_btn, self.debug_btn, margin=(0, 0)),
                    width=280
                ),
                margin=(10, 5)
            ),

            self.processing_status,
            margin=(10, 10)
        )

        # File management section
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
                self.delete_file_btn,
                self.refresh_files_btn,
                margin=(10, 5)
            ),

            margin=(10, 10)
        )

        # Complete card
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
            width=350,
            margin=(10, 10),
            styles={'border-radius': '8px', 'overflow': 'hidden'}
        )

    def set_current_cell(self, cell_name: str):
        """Set current cell with visual feedback."""
        self.current_cell = cell_name
        if cell_name:
            self.cell_display.object = f"""
            <div style='background: #E8F5E8; padding: 12px; border-radius: 4px; 
                        border-left: 4px solid #2E7D32; text-align: center;'>
                <strong style='color: #2E7D32;'>Current Cell:</strong> 
                <span style='color: #1B5E20; font-weight: 600;'>{cell_name}</span>
                <span style='color: #4CAF50; float: right;'>✓</span>
            </div>
            """
            self._refresh_file_list()
            self._check_upload_ready(None)
        else:
            self.cell_display.object = """
            <div style='background: #FFF3E0; padding: 12px; border-radius: 4px; 
                        border-left: 4px solid #FF9800; text-align: center;'>
                <strong style='color: #F57C00;'>Please select a cell first</strong>
            </div>
            """
            self.file_select.options = []
            self.upload_btn.disabled = True

    def _refresh_file_list(self):
        """Refresh file list with professional formatting."""
        if not self.current_cell:
            return

        try:
            files = self.api.get_cell_files(self.current_cell)

            if files:
                options = []
                for file_info in files:
                    original_name = file_info.get('original_filename', 'Unknown')
                    segment_count = file_info.get('segment_count', 0)

                    # Clean filename display
                    if len(original_name) > 25:
                        display_name = original_name[:22] + "..."
                    else:
                        display_name = original_name

                    formatted_name = f"✓ {display_name} ({segment_count} segments)"
                    options.append((formatted_name, file_info['file_id']))

                self.file_select.options = options

                # Update status
                self._update_processing_status(f"Found {len(files)} processed files", "success")
            else:
                self.file_select.options = []
                self._update_processing_status("No files processed yet", "info")

        except Exception as e:
            self.status_message = f"Error loading files: {str(e)}"
            self._update_processing_status("Error loading files", "error")

    def refresh_files(self):
        """Public method to refresh file list."""
        self._refresh_file_list()

    def _on_file_selected(self, event):
        """Handle file selection with info display."""
        file_id = event.new
        if file_id:
            if isinstance(file_id, tuple):
                file_id = file_id[1]
            elif not isinstance(file_id, str):
                file_id = str(file_id)

            self.selected_file = file_id
            self.delete_file_btn.disabled = False
            self.analyze_btn.disabled = False

            # Display file info
            try:
                files = self.api.get_cell_files(self.current_cell)
                file_info = next((f for f in files if f['file_id'] == file_id), None)

                if file_info:
                    original_name = file_info.get('original_filename', 'Unknown')
                    segment_count = file_info.get('segment_count', 0)
                    processing_date = file_info.get('processing_date', 'Unknown')

                    self.file_info_display.object = f"""
                    <div style='background: #F8F9FA; padding: 10px; border-radius: 4px; 
                                border-left: 3px solid #1976D2; margin: 5px 0;'>
                        <div style='font-weight: 600; color: #2E4057; margin-bottom: 5px;'>
                            File Details
                        </div>
                        <div style='font-size: 12px; color: #666;'>
                            <strong>Original:</strong> {original_name}<br>
                            <strong>Segments:</strong> {segment_count}<br>
                            <strong>Processed:</strong> {processing_date}
                        </div>
                    </div>
                    """
                else:
                    self.file_info_display.object = "<div style='color: #999; font-style: italic;'>File details not available</div>"

            except Exception:
                self.file_info_display.object = "<div style='color: #999; font-style: italic;'>Error loading file details</div>"
        else:
            self.delete_file_btn.disabled = True
            self.analyze_btn.disabled = True
            self.file_info_display.object = "<div style='color: #666; font-style: italic;'>Select a file to view details</div>"

    def _check_upload_ready(self, event):
        """Check if upload is ready with visual feedback."""
        has_metadata = self.metadata_upload.value is not None
        has_data = self.data_upload.value is not None
        has_cell = self.current_cell is not None

        # Debug logging to understand the current state
        print(f"DEBUG: Upload readiness check:")
        print(f"  - has_metadata: {has_metadata} (value: {type(self.metadata_upload.value).__name__})")
        print(f"  - has_data: {has_data} (value: {type(self.data_upload.value).__name__})")
        print(f"  - has_cell: {has_cell} (current_cell: {self.current_cell})")

        self.upload_btn.disabled = not (has_metadata and has_data and has_cell)

        # Update button text based on readiness
        if not has_cell:
            button_text = "🚀 Select Cell First"
        elif not has_metadata or not has_data:
            button_text = "🚀 Select Both Files"
        else:
            button_text = "🚀 Process Files"
        
        print(f"  - Setting button text to: {button_text}")
        self.upload_btn.name = button_text

    def _on_file_uploaded(self, event):
        """Handle file upload completion - alternative trigger."""
        print(f"DEBUG: File uploaded - filename: {event.new}")
        # Small delay to ensure value is set
        import time
        time.sleep(0.1)
        self._check_upload_ready(None)

    def _debug_status(self, event):
        """Manual debug trigger to check current state."""
        print(f"\n=== MANUAL DEBUG STATUS ===")
        self._check_upload_ready(None)
        print(f"Current button text: {self.upload_btn.name}")
        print(f"Button disabled: {self.upload_btn.disabled}")
        print(f"=========================\n")

    def _on_upload_files(self, event):
        """Handle file upload with progress feedback."""
        if not self.current_cell:
            self.status_message = "No cell selected"
            return

        if not (self.metadata_upload.value and self.data_upload.value):
            self.status_message = "Both .par and .par.csv files required"
            return

        # Show processing state
        self._update_processing_status("🔄 Processing files...", "processing")
        self.upload_btn.disabled = True

        try:
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Save uploaded files temporarily
                metadata_path = temp_path / self.metadata_upload.filename
                metadata_path.write_bytes(self.metadata_upload.value)

                data_path = temp_path / self.data_upload.filename
                data_path.write_bytes(self.data_upload.value)

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

                    # Clear upload widgets
                    self.metadata_upload.value = None
                    self.data_upload.value = None
                    self._check_upload_ready(None)

                    # Refresh file list
                    self._refresh_file_list()

                else:
                    self.status_message = f"Processing failed: {result.error}"
                    self._update_processing_status(f"❌ Processing failed: {result.error}", "error")
                    self.upload_btn.disabled = False

        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            self.status_message = error_msg
            self._update_processing_status(f"❌ {error_msg}", "error")
            self.upload_btn.disabled = False

    def _on_delete_file(self, event):
        """Handle file deletion with confirmation."""
        file_selection = self.file_select.value
        if not file_selection:
            return

        # Extract file_id from tuple if needed (UI returns (display_name, file_id))
        if isinstance(file_selection, tuple):
            file_id = file_selection[1]  # Get the file_id part
        else:
            file_id = file_selection

        try:
            result = self.api.delete_file(file_id)
            if result.success:
                self.status_message = result.message
                self._update_processing_status(f"🗑️ {result.message}", "success")
                self._refresh_file_list()
                self.selected_file = ""
            else:
                self.status_message = f"Failed to delete file: {result.error}"
                self._update_processing_status(f"❌ Failed to delete file: {result.error}", "error")

        except Exception as e:
            error_msg = f"Delete error: {str(e)}"
            self.status_message = error_msg
            self._update_processing_status(f"❌ {error_msg}", "error")

    def _on_refresh_files(self, event):
        """Handle file list refresh."""
        self._refresh_file_list()
        self._update_processing_status("🔄 Refreshed file list", "success")

    def _update_processing_status(self, message: str, status_type: str = "info"):
        """Update processing status with styling."""
        if status_type == "success":
            color = "#2E7D32"
            bg_color = "#E8F5E8"
        elif status_type == "error":
            color = "#D32F2F"
            bg_color = "#FFEBEE"
        elif status_type == "processing":
            color = "#1976D2"
            bg_color = "#E3F2FD"
        else:  # info
            color = "#666"
            bg_color = "#F5F5F5"

        self.processing_status.object = f"""
        <div style='color: {color}; background: {bg_color}; padding: 8px; 
                    border-radius: 4px; border-left: 3px solid {color}; font-size: 14px;'>
            {message}
        </div>
        """