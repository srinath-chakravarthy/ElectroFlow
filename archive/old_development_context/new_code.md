```"""
Cell Manager Tab for Panel UI.

Provides a consolidated interface for creating, viewing, and managing battery cells.
"""

import panel as pn
import param
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import tempfile
import sys
import logging

logger = logging.getLogger(__name__)

# Re-establish src path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from backend_api import BackendAPI
from io_utils.storage_v2 import DatabaseStorageManager

class CellManagerTab(param.Parameterized):
    """
    Consolidated cell management interface for creating and organizing battery cells.
    """
    
    # Parameters for reactive UI
    active_cell_id = param.Integer(default=None, allow_None=True, doc="Active cell ID")
    active_cell_name = param.String(default="", doc="Active cell name") 
    refresh_trigger = param.Number(default=0, doc="Trigger for refreshing data")
    
    def __init__(self, backend_api: BackendAPI, **params):
        super().__init__(**params)
        self.api = backend_api
        self.layout = None
        self.cells_table = None
        self.active_cell_files_table = None
        self._cells_df = None  # Store cells dataframe for selection handling
        
        # UI components
        self.file_input = pn.widgets.FileInput(accept='.par,.csv', multiple=True)
        self.selected_files_display = pn.pane.HTML("")
        self.upload_status = pn.pane.HTML("")
        
        self.setup_layout()
    
    def setup_layout(self):
        """Setup the complete cell manager layout."""
        
        # Cell creation form
        create_cell_form = self._create_cell_form()
        
        # Cells table with selection
        cells_table = self._create_cells_table()
        
        # File upload section
        file_upload_section = self._create_file_upload_section()
        
        # Active cell status and files display
        active_cell_status = self._create_active_cell_status_display()
        active_cell_files_display = self._create_active_cell_files_table()
        
        self.layout = pn.Column(
            "## Cell & File Management",
            pn.Row(
                pn.Column("### Create New Cell", create_cell_form, width=400),
                pn.Column("### All Cells", cells_table, width=500)
            ),
            "---",
            pn.Column(
                "### Active Cell File Management",
                active_cell_status,
                file_upload_section,
                "#### Existing Files",
                active_cell_files_display,
            ),
            width=1200
        )
        
    def _create_cell_form(self):
        """Create cell creation form."""
        cell_name_input = pn.widgets.TextInput(name="Cell Name", placeholder="e.g., CELL_001")
        create_button = pn.widgets.Button(name="Create Cell", button_type="primary")
        status_message = pn.pane.HTML("")
        
        def create_cell_callback(event):
            if not cell_name_input.value:
                status_message.object = '<p style="color: red;">Cell name is required</p>'
                return
            
            result = self.api.create_cell(cell_name=cell_name_input.value)
            if result['success']:
                status_message.object = f'<p style="color: green;">{result["message"]}</p>'
                cell_name_input.value = ""
                self.refresh_trigger += 1  # Trigger table refresh
            else:
                status_message.object = f'<p style="color: red;">Error: {result["error"]}</p>'
        
        create_button.on_click(create_cell_callback)
        
        return pn.Column(cell_name_input, create_button, status_message)

    def _create_cells_table(self):
        """Create reactive cells table."""
        @pn.depends(self.param.refresh_trigger)
        def get_cells_table(*args):
            result = self.api.get_all_cells()
            if not result['success']:
                return pn.pane.HTML(f'<p style="color: red;">Error loading cells: {result["error"]}</p>')
            
            self.cells_data = result['cells']
            if not self.cells_data:
                return pn.pane.HTML("<p>No cells found. Create your first cell.</p>")
                
            df = pd.DataFrame(self.cells_data)
            self._cells_df = df.copy()
            
            table = pn.widgets.Tabulator(
                df, 
                pagination='remote', 
                page_size=10, 
                selectable='single',
                sizing_mode='stretch_width',
                height=300
            )

            def on_selection_change(event):
                if event.new:
                    selected_index = event.new[0]
                    selected_row = self._cells_df.iloc[selected_index]
                    self.active_cell_id = int(selected_row['id'])
                    self.active_cell_name = str(selected_row['cell_name'])
                else:
                    self.active_cell_id = None
                    self.active_cell_name = ""
            
            table.param.watch(on_selection_change, 'selection')
            return table
        
        return get_cells_table

    def _create_active_cell_status_display(self):
        """Create reactive status display for the active cell."""
        @pn.depends(self.param.active_cell_name)
        def get_status_display(active_cell_name):
            if active_cell_name:
                return pn.pane.HTML(
                    f"<h5>Active Cell: {active_cell_name}</h5>",
                    styles={'color': 'green'}
                )
            return pn.pane.HTML("<h5>No active cell selected</h5>")
        return get_status_display

    def _create_file_upload_section(self):
        """Create a working file upload section with FileInput widget."""
        
        self.file_input = pn.widgets.FileInput(accept='.par,.csv', multiple=True)
        self.selected_files_display = pn.pane.HTML("")
        self.upload_button = pn.widgets.Button(name="Upload Files", button_type="primary")
        self.upload_status = pn.pane.HTML("")
        
        # Event handler for display only
        def on_file_change(event):
            if event.new:
                filenames = [f[0] for f in event.new]
                self._update_file_upload_display(filenames)
            else:
                self._update_file_upload_display([])
        self.file_input.param.watch(on_file_change, 'value')
        
        # The main event handler for the upload workflow
        self.upload_button.on_click(self._handle_upload)
        
        return pn.Column(
            "#### File Upload",
            self.file_input,
            self.selected_files_display,
            self.upload_button,
            self.upload_status,
        )

    def _update_file_upload_display(self, filenames: List[str]):
        """Update the file list display based on FileInput selection."""
        if not filenames:
            self.selected_files_display.object = "<p>No files selected.</p>"
            return
        html = "<h6>Selected Files:</h6><ul>"
        for name in filenames:
            html += f"<li>{name}</li>"
        html += "</ul>"
        self.selected_files_display.object = html
    
    def _handle_upload(self, event):
        """Handles the complete file upload workflow on button click."""
        if not self.active_cell_id:
            self.upload_status.object = '<p style="color: red;">Please select a cell first.</p>'
            return
        
        uploaded_files = self.file_input.value
        if not uploaded_files:
            self.upload_status.object = '<p style="color: red;">No files selected for upload.</p>'
            return

        temp_paths = []
        try:
            self.upload_status.object = '<p style="color: orange;">Processing files...</p>'
            
            for filename, file_content in uploaded_files:
                temp_path = Path(tempfile.gettempdir()) / filename
                temp_path.write_bytes(file_content)
                temp_paths.append(temp_path)
            
            # The backend API handles the file type validation and processing logic
            result = self.api.add_files_to_cell(self.active_cell_name, temp_paths)
            
            if result['success']:
                self.upload_status.object = f'<p style="color: green;">Upload complete. Success: {result["summary"]["successful_uploads"]}, Failed: {result["summary"]["failed_uploads"]}.</p>'
                self.file_input.value = []  # Clear the input
                self.refresh_trigger += 1  # Refresh the files table
            else:
                self.upload_status.object = f'<p style="color: red;">Upload failed: {result["error"]}</p>'

        except Exception as e:
            logger.error(f"Upload failed with an exception: {e}")
            self.upload_status.object = f'<p style="color: red;">Upload failed: {str(e)}</p>'
        finally:
            # Cleanup temporary files
            for p in temp_paths:
                p.unlink(missing_ok=True)

    def _create_active_cell_files_table(self):
        """Create a reactive files table for the active cell."""
        @pn.depends(self.param.active_cell_id, self.param.refresh_trigger)
        def get_files_table(active_cell_id, refresh_trigger):
            if not active_cell_id:
                return pn.pane.HTML("<p>Select a cell to view its files.</p>")
            
            result = self.api.get_cell_files(active_cell_id)
            if not result['success']:
                return pn.pane.HTML(f'<p style="color: red;">Error: {result["error"]}</p>')

            files = result['files']
            if not files:
                return pn.pane.HTML("<p>No files found for this cell.</p>")
            
            df = pd.DataFrame(files)
            display_df = df[['original_filename', 'file_type', 'processing_status', 'upload_timestamp']]
            return pn.widgets.Tabulator(display_df, pagination='remote', page_size=10, selectable=True)
        
        return get_files_table```

```"""
Data Processing Tab for Panel UI.

Provides interface for cell data processing, technique selection, 
group management, and manual plotting.
"""

import panel as pn
import param
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import polars as pl
import json
import sys

# Add src directory to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from backend_api import BackendAPI
from visualization.plot_templates import PlotTemplates


class DataProcessingTab(param.Parameterized):
    """
    Cell data processing interface with a clear, technique-centric workflow.
    """
    
    # Parameters for reactive UI
    active_cell_id = param.Integer(default=None, allow_None=True, doc="Active cell ID")
    active_cell_name = param.String(default="", doc="Active cell name")
    
    # Internal state for selections
    selected_file_ids = param.List(default=[], doc="Selected file IDs")
    selected_techniques = param.List(default=[], doc="Selected technique references")
    selected_group_id = param.Integer(default=None, allow_None=True, doc="Selected group ID")
    refresh_trigger = param.Number(default=0, doc="Trigger for refreshing data")

    def __init__(self, backend_api: BackendAPI, **params):
        super().__init__(**params)
        self.api = backend_api
        self.layout = None
        self.plot_templates = PlotTemplates()
        
        # UI components
        self.files_table = self._create_files_table()
        self.techniques_table = self._create_techniques_table()
        self.groups_table = self._create_groups_table()
        self.plot_display = pn.pane.Plotly(width=730, height=400)
        self.analytics_display = pn.pane.HTML("")

        self.setup_layout()
    
    def setup_layout(self):
        """Setup the complete data processing layout."""
        
        # Left side: Data selection (Files → Techniques)
        data_selection_section = pn.Column(
            "### Data Selection",
            "#### Files",
            self.files_table,
            "---",
            "#### Techniques",
            self.techniques_table,
            width=600
        )
        
        # Right side: Group management and plotting
        group_management_section = pn.Column(
            "### Group Management & Plotting",
            self._create_group_creation_form(),
            "---",
            "#### Existing Groups",
            self.groups_table,
            "---",
            self._create_plotting_section(),
            width=750
        )
        
        # Main layout
        self.layout = pn.Column(
            "## Cell Data Processing",
            self._create_active_cell_status(),
            pn.Row(
                data_selection_section,
                group_management_section,
                sizing_mode="stretch_width"
            ),
            width=1400
        )
        
    def _create_active_cell_status(self):
        """Create active cell status display."""
        @pn.depends(self.param.active_cell_name)
        def get_status_display(active_cell_name):
            if active_cell_name:
                return pn.pane.HTML(
                    f"<h4>Processing Data for Cell: {active_cell_name}</h4>",
                    styles={'color': 'blue'}
                )
            return pn.pane.HTML(
                "<h4>No active cell selected. Please select a cell from the Cell Management tab.</h4>"
            )
        return get_status_display

    def _create_files_table(self):
        """Create reactive files table."""
        @pn.depends(self.param.active_cell_id, self.param.refresh_trigger)
        def get_files_table_content(*args):
            if not self.active_cell_id:
                return pn.pane.HTML("<p style='color: #666;'>No active cell selected</p>")
            
            result = self.api.get_cell_files(self.active_cell_id)
            if not result['success']:
                return pn.pane.HTML(f'<p style="color: red;">Error: {result["error"]}</p>')
            
            files = result['files']
            if not files:
                return pn.pane.HTML("<p>No files found.</p>")
            
            df = pd.DataFrame(files)
            table = pn.widgets.Tabulator(df, pagination='remote', page_size=8, selectable='checkbox')
            
            def on_file_selection_change(event):
                selected_indices = event.new if event.new else []
                selected_file_ids = [files[i]['file_id'] for i in selected_indices]
                self.selected_file_ids = selected_file_ids
            
            table.param.watch(on_file_selection_change, 'selection')
            return table
        
        return get_files_table_content

    def _create_techniques_table(self):
        """Create reactive techniques table based on file selection."""
        @pn.depends(self.param.selected_file_ids)
        def get_techniques_table_content(selected_file_ids):
            if not selected_file_ids:
                return pn.pane.HTML("<p>Select files above to view techniques</p>")
            
            all_techniques = []
            for file_id in selected_file_ids:
                segments = self.api.db.get_file_segments(file_id)
                all_techniques.extend([
                    {'file_id': file_id, 'segment_number': s['segment_number'], 'technique_name': s['technique_name']}
                    for s in segments
                ])
            
            if not all_techniques:
                return pn.pane.HTML("<p>No techniques found in selected files.</p>")
            
            df = pd.DataFrame(all_techniques)
            table = pn.widgets.Tabulator(df, pagination='remote', page_size=8, selectable='checkbox')
            
            def on_technique_selection_change(event):
                selected_indices = event.new if event.new else []
                selected_techniques = [
                    {'file_id': all_techniques[i]['file_id'], 'segment_number': all_techniques[i]['segment_number']}
                    for i in selected_indices
                ]
                self.selected_techniques = selected_techniques
            
            table.param.watch(on_technique_selection_change, 'selection')
            return table
            
        return get_techniques_table_content

    def _create_group_creation_form(self):
        """Create group creation form."""
        group_name_input = pn.widgets.TextInput(name="Group Name", placeholder="e.g., Cycle_1_to_5")
        create_button = pn.widgets.Button(name="Create Group", button_type="primary")
        status_message = pn.pane.HTML("")

        def create_group_callback(event):
            if not self.active_cell_id or not group_name_input.value or not self.selected_techniques:
                status_message.object = '<p style="color: red;">Cell, name, and techniques are required.</p>'
                return
            
            try:
                self.api.db.create_user_group(
                    cell_id=self.active_cell_id,
                    group_name=group_name_input.value,
                    techniques=self.selected_techniques
                )
                status_message.object = '<p style="color: green;">Group created successfully.</p>'
                self.refresh_trigger += 1
            except Exception as e:
                status_message.object = f'<p style="color: red;">Error: {str(e)}</p>'

        create_button.on_click(create_group_callback)
        return pn.Column("#### Create New Group", group_name_input, create_button, status_message)

    def _create_groups_table(self):
        """Create reactive groups table."""
        @pn.depends(self.param.active_cell_id, self.param.refresh_trigger)
        def get_groups_table_content(*args):
            if not self.active_cell_id:
                return pn.pane.HTML("<p>No active cell selected.</p>")
            
            groups = self.api.db.get_cell_groups(self.active_cell_id)
            if not groups:
                return pn.pane.HTML("<p>No groups found.</p>")
            
            df = pd.DataFrame(groups)
            table = pn.widgets.Tabulator(df[['group_name', 'group_type', 'created_at']], selectable=1, pagination='remote')
            
            def on_group_selection_change(event):
                selected_index = event.new[0] if event.new else None
                self.selected_group_id = groups[selected_index]['id'] if selected_index is not None else None

            table.param.watch(on_group_selection_change, 'selection')
            return table

        return get_groups_table_content

    def _create_plotting_section(self):
        """Create plotting and analytics controls."""
        plot_button = pn.widgets.Button(name="Generate Plot", button_type="primary")
        plot_type_select = pn.widgets.Select(name="Plot Type", options=["Voltage vs Time", "Current vs Time", "Nyquist Plot"])
        
        def generate_plot_callback(event):
            if not self.selected_group_id:
                self.plot_display.object = self.plot_templates._create_error_figure("No group selected.")
                return
            
            group_data = self.api.group_analytics.load_group_data(self.selected_group_id)
            if group_data is None or group_data.is_empty():
                self.plot_display.object = self.plot_templates._create_error_figure("No data found for this group.")
                return
            
            plot_type = plot_type_select.value
            if plot_type == "Voltage vs Time":
                fig = self.plot_templates.create_voltage_time_plot(group_data)
            # Add other plot types here
            else:
                fig = self.plot_templates._create_error_figure(f"Plot type '{plot_type}' not supported.")
            
            self.plot_display.object = fig
        
        plot_button.on_click(generate_plot_callback)
        return pn.Column(
            "#### Plotting & Analytics",
            pn.Row(plot_type_select, plot_button),
            self.plot_display,
            self.analytics_display
        )

    def set_active_cell(self, cell_id: int, cell_name: str):
        """Set the active cell for data processing."""
        self.active_cell_id = cell_id
        self.active_cell_name = cell_name
        self.selected_file_ids = []
        self.selected_techniques = []
        self.refresh_trigger += 1 # Trigger table refresh```
```
"""
Main Panel application for battery data analyzer.
"""

import panel as pn
import param
from pathlib import Path
import sys
import logging
import pandas as pd
from typing import List

# Configure Panel
pn.extension('plotly', 'tabulator')

# Add src directory to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from backend_api import BackendAPI
from ui.components.cell_manager import CellManagerTab
from ui.components.data_processing import DataProcessingTab

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatteryAnalyzerApp(param.Parameterized):
    """
    Main Panel application for battery data processing and analysis.
    """
    
    def __init__(self, data_dir: Path = None, db_path: Path = None, **params):
        super().__init__(**params)
        
        self.data_dir = data_dir or Path("data")
        self.db_path = db_path or (self.data_dir / "battery_analyzer.db")
        self.api = BackendAPI(self.data_dir, self.db_path)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the complete UI with all components."""
        
        self.cell_manager = CellManagerTab(self.api)
        self.data_processing = DataProcessingTab(self.api)
        
        self._setup_active_cell_sharing()
        
        header = self._create_header()
        
        self.tabs = pn.Tabs(
            ("Cell & File Management", self.cell_manager.layout),
            ("Cell Data Processing", self.data_processing.layout),
            tabs_location='above',
            width=1400
        )
        
        footer = self._create_footer()
        
        self.layout = pn.Column(
            header,
            self.tabs,
            footer,
            width=1400
        )
    
    def _setup_active_cell_sharing(self):
        """Setup active cell sharing between tabs."""
        def sync_active_cell(event):
            self.data_processing.set_active_cell(
                self.cell_manager.active_cell_id,
                self.cell_manager.active_cell_name
            )
        
        self.cell_manager.param.watch(sync_active_cell, ['active_cell_id', 'active_cell_name'])
        
    def _create_header(self):
        """Create application header."""
        db_stats = self.api.get_database_stats()
        stats_text = "Database stats unavailable"
        if db_stats['success']:
            stats = db_stats['stats']
            stats_text = f"Cells: {stats.get('cells_count', 0)} | Files: {stats.get('files_count', 0)}"
        
        app_info = f"""
        <div style="background: #f8f9fa; padding: 15px;">
            <h1 style="margin: 0;">🔋 Battery Data Analyzer</h1>
            <p style="margin: 5px 0;">{stats_text}</p>
        </div>
        """
        return pn.pane.HTML(app_info, width=1400)
    
    def _create_footer(self):
        """Create application footer with utility buttons."""
        backup_btn = pn.widgets.Button(name="Backup Database", button_type="light")
        refresh_btn = pn.widgets.Button(name="Refresh All", button_type="light")
        
        def backup_database(event):
            backup_path = self.data_dir / "backups" / f"backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path.parent.mkdir(exist_ok=True)
            self.api.backup_database(backup_path)
        
        def refresh_all(event):
            self.cell_manager.refresh_trigger += 1
            self.data_processing.refresh_trigger += 1
        
        backup_btn.on_click(backup_database)
        refresh_btn.on_click(refresh_all)
        
        return pn.Row(backup_btn, refresh_btn)

    def serve(self, port: int = 5007, show: bool = True):
        return pn.serve(self.layout, port=port, show=show)```

```def create_app(data_dir: Path = None, db_path: Path = None) -> BatteryAnalyzerApp:
    return BatteryAnalyzerApp(data_dir, db_path)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Battery Data Analyzer - Panel UI")
    parser.add_argument("--data-dir", type=Path, default="data")
    args = parser.parse_args()
    app = create_app(data_dir=args.data_dir)
    app.serve()

if __name__ == "__main__":
    main()```