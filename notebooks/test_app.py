import panel as pn
import param
import pandas as pd
import numpy as np
import io
from typing import Optional

# Enable Panel extensions
pn.extension('tabulator', 'bokeh')


class FileInputTestApp(param.Parameterized):
    """
    Test application for Panel fileInput functionality with param.watch
    Demonstrates proper use of param.watch for reactive updates
    """

    # Parameters
    file_input = param.Parameter(default=None)
    uploaded_filename = param.String(default="No file uploaded")
    file_size = param.String(default="0 bytes")
    file_type = param.String(default="Unknown")
    processing_status = param.String(default="Ready")
    data_preview = param.DataFrame(default=pd.DataFrame())

    def __init__(self, **params):
        super().__init__(**params)

        # Set up the Panel widgets first
        self.setup_widgets()

        # Set up parameter watchers - this is the proper param.watch approach
        self.param.watch(self.handle_file_upload, 'file_input')
        self.param.watch(self.update_filename_display, 'uploaded_filename')
        self.param.watch(self.update_size_display, 'file_size')
        self.param.watch(self.update_type_display, 'file_type')
        self.param.watch(self.update_status_display, 'processing_status')
        self.param.watch(self.update_data_table, 'data_preview')

    def setup_widgets(self):
        """Initialize Panel widgets"""

        # File input widget - accepts common data formats
        self.file_widget = pn.widgets.FileInput(
            name="Upload Data File",
            accept='.csv,.xlsx,.json,.txt,.parquet',
            multiple=False,
            height=60
        )

        # Link the widget to the parameter
        self.file_widget.link(self, value='file_input')

        # Status indicators - these will be updated via param.watch
        self.filename_indicator = pn.pane.Markdown("**Filename:** No file uploaded")
        self.size_indicator = pn.pane.Markdown("**Size:** 0 bytes")
        self.type_indicator = pn.pane.Markdown("**Type:** Unknown")
        self.status_indicator = pn.pane.Markdown("**Status:** Ready")

        # Data preview table
        self.data_table = pn.widgets.Tabulator(
            value=pd.DataFrame(),
            pagination='remote',
            page_size=10,
            sizing_mode='stretch_width',
            height=300
        )

        # Action buttons
        self.clear_button = pn.widgets.Button(
            name="Clear File",
            button_type="primary",
            width=100
        )
        self.clear_button.on_click(self.clear_file)

        self.process_button = pn.widgets.Button(
            name="Process File",
            button_type="success",
            width=100,
            disabled=True
        )
        self.process_button.on_click(self.process_file)

        # Debug output for watching parameter changes
        self.debug_output = pn.pane.Markdown("**Debug Log:**\n- App initialized")

    def update_filename_display(self, event):
        """Update filename display - triggered by param.watch"""
        self.filename_indicator.object = f"**Filename:** {event.new}"
        self.add_debug_message(f"Filename updated: {event.new}")

    def update_size_display(self, event):
        """Update file size display - triggered by param.watch"""
        self.size_indicator.object = f"**Size:** {event.new}"
        self.add_debug_message(f"File size updated: {event.new}")

    def update_type_display(self, event):
        """Update file type display - triggered by param.watch"""
        self.type_indicator.object = f"**Type:** {event.new}"
        self.add_debug_message(f"File type updated: {event.new}")

    def update_status_display(self, event):
        """Update processing status display - triggered by param.watch"""
        status_color = "green" if event.new == "Complete" else "blue"
        if "Error" in event.new:
            status_color = "red"
        self.status_indicator.object = f"**Status:** <span style='color:{status_color}'>{event.new}</span>"
        self.add_debug_message(f"Status updated: {event.new}")

    def update_data_table(self, event):
        """Update data table - triggered by param.watch"""
        if not event.new.empty:
            self.data_table.value = event.new
            rows, cols = event.new.shape
            self.add_debug_message(f"Data table updated: {rows} rows, {cols} columns")
        else:
            self.data_table.value = pd.DataFrame()
            self.add_debug_message("Data table cleared")

    def add_debug_message(self, message):
        """Add a debug message to track param.watch triggers"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        current_debug = self.debug_output.object
        new_debug = f"{current_debug}\n- [{timestamp}] {message}"

        # Keep only last 10 messages
        lines = new_debug.split('\n')
        if len(lines) > 11:  # Header + 10 messages
            lines = lines[:1] + lines[-10:]
            new_debug = '\n'.join(lines)

        self.debug_output.object = new_debug

    def handle_file_upload(self, event):
        """
        Handle file upload event - triggered by param.watch on file_input
        This demonstrates the main parameter watching functionality
        """
        if event.new is None:
            self.add_debug_message("File input cleared")
            return

        try:
            self.processing_status = "Processing file..."

            # Panel FileInput gives us raw bytes
            file_bytes = event.new
            self.add_debug_message(f"Received {len(file_bytes)} bytes")

            # Get filename from the widget itself
            filename = getattr(self.file_widget, 'filename', 'uploaded_file.csv')
            self.uploaded_filename = filename
            self.add_debug_message(f"Widget filename: {filename}")

            # Get file size from bytes
            size_bytes = len(file_bytes)
            self.file_size = self.format_file_size(size_bytes)

            # Determine file type from filename
            filename_lower = filename.lower()
            if filename_lower.endswith('.csv'):
                self.file_type = "CSV"
            elif filename_lower.endswith('.xlsx'):
                self.file_type = "Excel"
            elif filename_lower.endswith('.json'):
                self.file_type = "JSON"
            elif filename_lower.endswith('.parquet'):
                self.file_type = "Parquet"
            else:
                self.file_type = "Text/Other"

            # Enable process button
            self.process_button.disabled = False

            # Update status
            self.processing_status = "File uploaded - ready to process"

        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            self.processing_status = error_msg
            self.process_button.disabled = True
            self.add_debug_message(f"Error in file upload: {str(e)}")

    def process_file(self, event):
        """Process the uploaded file and create a preview"""
        if self.file_input is None:
            return

        try:
            self.processing_status = "Reading file data..."

            # Panel FileInput gives us raw bytes
            file_bytes = self.file_input
            self.add_debug_message(f"Processing {len(file_bytes)} bytes")

            # Convert bytes to file-like object
            file_content = io.BytesIO(file_bytes)

            # Read based on file type
            if self.file_type == "CSV":
                df = pd.read_csv(file_content)
            elif self.file_type == "Excel":
                df = pd.read_excel(file_content)
            elif self.file_type == "JSON":
                df = pd.read_json(file_content)
            elif self.file_type == "Parquet":
                df = pd.read_parquet(file_content)
            else:
                # For text files, decode and create preview
                content = file_bytes.decode('utf-8', errors='ignore')
                lines = content.split('\n')[:10]  # First 10 lines
                df = pd.DataFrame({'Line': range(1, len(lines) + 1), 'Content': lines})

            # Update data_preview parameter - this will trigger the watcher
            self.data_preview = df.head(100)  # Limit preview to first 100 rows

            # Update status with data info - this will trigger its watcher
            rows, cols = df.shape
            self.processing_status = f"Complete - {rows} rows, {cols} columns"
            self.add_debug_message(f"Successfully loaded: {rows} rows, {cols} columns")

        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            self.processing_status = error_msg
            self.data_preview = pd.DataFrame()  # This will trigger the data table watcher
            self.add_debug_message(f"Error processing: {str(e)}")

    def clear_file(self, event):
        """Clear the uploaded file and reset all parameters"""
        # Clear the file input - this will trigger the file_input watcher
        self.file_input = None
        self.file_widget.value = None

        # Reset all parameters - each will trigger their respective watchers
        self.uploaded_filename = "No file uploaded"
        self.file_size = "0 bytes"
        self.file_type = "Unknown"
        self.processing_status = "Ready"
        self.data_preview = pd.DataFrame()

        # Disable process button
        self.process_button.disabled = True

        self.add_debug_message("All parameters cleared")

    @staticmethod
    def format_file_size(size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 bytes"

        size_names = ["bytes", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"

    def create_layout(self):
        """Create the Panel layout"""

        # Header
        header = pn.pane.Markdown(
            "# Panel FileInput Test App\n"
            "*Testing param.watch functionality with file uploads*\n\n"
            "This app demonstrates proper use of `param.watch` for reactive parameter updates."
        )

        # File upload section
        upload_section = pn.Column(
            pn.pane.Markdown("## File Upload"),
            self.file_widget,
            pn.Row(self.clear_button, self.process_button),
            width=600
        )

        # Status section
        status_section = pn.Column(
            pn.pane.Markdown("## File Information"),
            self.filename_indicator,
            self.size_indicator,
            self.type_indicator,
            self.status_indicator,
            width=600
        )

        # Debug section to show param.watch activity
        debug_section = pn.Column(
            pn.pane.Markdown("## Debug Log (param.watch triggers)"),
            self.debug_output,
            width=600,
            height=200,
            scroll=True
        )

        # Data preview section
        preview_section = pn.Column(
            pn.pane.Markdown("## Data Preview"),
            self.data_table,
            sizing_mode='stretch_width'
        )

        # Create main layout
        layout = pn.Column(
            header,
            pn.Row(
                upload_section,
                status_section,
                sizing_mode='stretch_width'
            ),
            debug_section,
            preview_section,
            sizing_mode='stretch_width',
            margin=(20, 20)
        )

        return layout


def create_app():
    """Create and return the Panel application"""

    # Create the test app instance
    app = FileInputTestApp()

    # Create the layout
    layout = app.create_layout()

    # Add sample data generation for testing param.watch
    sample_data_button = pn.widgets.Button(
        name="Generate Sample CSV",
        button_type="light",
        width=150
    )

    def generate_sample_data(event):
        """Generate sample CSV data for testing param.watch triggers"""
        # Create sample battery data
        np.random.seed(42)
        n_samples = 100

        data = {
            'battery_id': [f'BATT_{i:03d}' for i in range(n_samples)],
            'voltage': np.random.normal(3.7, 0.1, n_samples),
            'current': np.random.normal(1.5, 0.3, n_samples),
            'temperature': np.random.normal(25, 5, n_samples),
            'capacity_mah': np.random.normal(2500, 200, n_samples),
            'cycle_count': np.random.randint(0, 1000, n_samples),
            'soh_percent': np.random.normal(85, 10, n_samples)
        }

        df = pd.DataFrame(data)
        csv_content = df.to_csv(index=False)

        # Create a file-like object that mimics Panel's FileInput
        class MockFileInput:
            def __init__(self, content, filename):
                self.file = io.BytesIO(content.encode())
                self.filename = filename

        # This will trigger the param.watch on file_input
        app.file_input = MockFileInput(csv_content, 'sample_battery_data.csv')

        # Auto-process the sample data
        app.process_file(None)

    sample_data_button.on_click(generate_sample_data)

    # Add testing section
    testing_section = pn.Column(
        pn.pane.Markdown("### Testing param.watch"),
        pn.pane.Markdown("Click to generate sample data and watch the param.watch triggers in the debug log:"),
        sample_data_button
    )

    # Insert testing section into the layout
    layout[1][0].append(testing_section)

    return layout


# Create the app
if __name__ == "__main__":
    # For running as a script
    app_layout = create_app()
    app_layout.show(port=5007)
else:
    # For serving with panel serve
    app_layout = create_app()
    app_layout.servable()