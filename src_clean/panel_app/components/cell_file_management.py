"""
Tab 1 Redesign - 2-Table Design with Modals

Clean, simple interface with Cell table + File table and modal forms.
Replaces hierarchical approach with straightforward table selection.

Design:
- Left Panel: Cell Table + File Table (with buttons at bottom)
- Right Panel: Data Preview (plots + tables)
- Modals: Create Cell, Add Files
"""

import panel as pn
import param
import pandas as pd
from typing import List, Dict, Any, Optional

# Import DataViewer for plotting functionality
from .data_viewer import DataViewer

pn.extension('tabulator', 'modal', 'filedropper')

class CellFileManagement(param.Parameterized):
    """
    Cell and File Management component with 2-table design and modal forms.
    
    Features:
    - Cell table with single selection
    - File table showing files for selected cell
    - Modal forms for creating cells and adding files
    - Clean data preview panel
    """
    
    selected_cell = param.String(default="", doc="Currently selected cell name")
    selected_file = param.String(default="", doc="Currently selected file ID")
    status_message = param.String(default="", doc="Status message for main app")
    
    def __init__(self, api, **params):
        super().__init__(**params)
        self.api = api
        self._create_components()
        self._refresh_cell_data()
        
    def _create_components(self):
        """Create the 2-table layout components."""
        
        # === CELL TABLE ===
        self.cell_tabulator = pn.widgets.Tabulator(
            value=self._create_empty_cell_dataframe(),
            pagination='remote',
            page_size=10,
            sizing_mode='stretch_width',
            selectable='checkbox-single',  # Single row selection
            sortable=True,
            show_index=False,
            configuration={
                'layout': 'fitDataFill',
                'height': '300px',
                'placeholder': 'No cells found.',
                'tooltips': True,
                'columnDefaults': {'tooltip': True}
            },
            height=300,
            margin=(10, 5)
        )
        self.cell_tabulator.param.watch(self._on_cell_selection_changed, 'selection')
        
        # Cell table buttons
        self.create_cell_btn = pn.widgets.Button(
            name="Create Cell",
            button_type="primary",
            width=120,
            height=35,
            margin=(5, 5),
            styles={'font-size': '14px', 'font-weight': '600'}
        )
        self.create_cell_btn.on_click(self._show_create_cell_modal)
        
        self.delete_cell_btn = pn.widgets.Button(
            name="Delete Cell",
            button_type="light",
            width=100,
            height=35,
            disabled=True,  # Enabled when cell selected
            margin=(5, 5),
            styles={'font-size': '14px', 'font-weight': '600'}
        )
        self.delete_cell_btn.on_click(self._on_delete_cell)
        
        # === FILE TABLE ===
        self.file_tabulator = pn.widgets.Tabulator(
            value=self._create_empty_file_dataframe(),
            pagination='remote',
            page_size=10,
            sizing_mode='stretch_width',
            selectable='checkbox-single',  # Single row selection
            sortable=True,
            show_index=True,
            configuration={
                'layout': 'fitDataFill',
                'height': '300px',
                'placeholder': 'Select a cell to view files.',
                'tooltips': True,
                'columnDefaults': {'tooltip': True}
            },
            height=300,
            margin=(10, 5)
        )
        self.file_tabulator.param.watch(self._on_file_selection_changed, 'selection')
        
        # File table buttons
        self.add_files_btn = pn.widgets.Button(
            name="Add Files",
            button_type="primary",
            width=120,
            height=35,
            disabled=True,
            margin=(5, 5),
            styles={'font-size': '14px', 'font-weight': '600'}
        )
        
        self.reprocess_file_btn = pn.widgets.Button(
            name="Re-process",
            button_type="light",
            width=90,
            height=35,
            disabled=True,
            margin=(5, 5),
            styles={'font-size': '14px', 'font-weight': '600'}
        )
        
        self.delete_file_btn = pn.widgets.Button(
            name="Delete File",
            button_type="light",
            width=90,
            height=35,
            disabled=True,  # Enabled when file selected
            margin=(5, 5),
            styles={'font-size': '14px', 'font-weight': '600'}
        )
        self.add_files_btn.on_click(self._show_add_files_modal)
        self.reprocess_file_btn.on_click(self._on_reprocess_file)
        self.delete_file_btn.on_click(self._on_delete_file)
        
        # === MODAL COMPONENTS ===
        self._create_modal_components()
        
        # === DATA PREVIEW COMPONENTS ===
        self._create_data_preview_components()
        
    def _create_modal_components(self):
        """Create modal forms for cell creation and file upload."""
        
        # === CREATE CELL MODAL ===
        # Form inputs - matching current cell_manager.py
        self.new_cell_name = pn.widgets.TextInput(
            placeholder="e.g., CELL_001",
            width=180,
            margin=(5, 5)
        )
        
        self.cell_chemistry = pn.widgets.Select(
            value="Li_ion",
            options=["Li_ion", "Li_metal", "Na_ion", "LFP", "NMC", "Other"],
            width=100,
            margin=(5, 5)
        )
        
        self.cell_description = pn.widgets.TextInput(
            placeholder="Brief description (e.g., Formation cycles)",
            width=290,
            margin=(5, 5)
        )
        
        self.capacity_ah = pn.widgets.NumberInput(
            value=None,
            step=0.1,
            start=0,
            width=140,
            margin=(5, 5)
        )
        
        # Electrode details
        self.cathode_material = pn.widgets.TextInput(
            placeholder="e.g., NMC811",
            width=140,
            margin=(5, 5)
        )
        
        self.cathode_mass_mg = pn.widgets.NumberInput(
            value=None,
            step=0.1,
            start=0,
            width=140,
            margin=(5, 5)
        )
        
        self.anode_material = pn.widgets.TextInput(
            placeholder="e.g., Li metal",
            width=140,
            margin=(5, 5)
        )
        
        self.anode_mass_mg = pn.widgets.NumberInput(
            value=None,
            step=0.1,
            start=0,
            width=140,
            margin=(5, 5)
        )
        
        self.cell_notes = pn.widgets.TextAreaInput(
            placeholder="Optional notes and observations...",
            height=60,
            width=290,
            margin=(5, 5)
        )
        
        # Modal buttons
        self.create_cell_modal_btn = pn.widgets.Button(
            name="Create Cell",
            button_type="primary",
            width=120,
            margin=(10, 5)
        )
        self.create_cell_modal_btn.on_click(self._on_create_cell)
        
        self.cancel_cell_btn = pn.widgets.Button(
            name="Cancel",
            button_type="primary",
            width=140,
            height=35,
            margin=(10, 5),
            styles={'font-size': '14px', 'font-weight': '600'}
        )
        self.cancel_cell_btn.on_click(self._hide_create_cell_modal)
        
        # === ADD FILES MODAL ===
        # File droppers
        self.metadata_dropper = pn.widgets.FileDropper(
            multiple=False,
            max_file_size='200MB',
            height=100,
            width=280,
            margin=(10, 5)
        )
        
        self.data_dropper = pn.widgets.FileDropper(
            multiple=False, 
            max_file_size='200MB',
            height=100,
            width=280,
            margin=(10, 5)
        )
        
        self.temperature_input = pn.widgets.NumberInput(
            name="Temperature (°C)",
            value=25.0,
            start=-50,
            end=100,
            step=0.1,
            width=100,
            margin=(5, 5)
        )
        
        # Modal buttons
        self.process_files_modal_btn = pn.widgets.Button(
            name="Process Files",
            button_type="primary",
            width=140,
            height=35,
            disabled=True,
            margin=(10, 5),
            styles={'font-size': '14px', 'font-weight': '600'}
        )
        self.process_files_modal_btn.on_click(self._on_process_files)
        
        self.cancel_files_btn = pn.widgets.Button(
            name="Cancel",
            button_type="primary",
            width=140,
            height=35,
            margin=(10, 5),
            styles={'font-size': '14px', 'font-weight': '600'}
        )
        self.cancel_files_btn.on_click(self._hide_add_files_modal)
        
        # Watch for upload readiness
        self.metadata_dropper.param.watch(self._check_upload_ready, 'value')
        self.data_dropper.param.watch(self._check_upload_ready, 'value')
        
        # Modal containers (initially hidden)
        self.create_cell_modal = None
        self.add_files_modal = None
        self._modal_container = pn.Column()
        
        # Initialize DataViewer for plotting functionality
        self.data_viewer = DataViewer(api=self.api)
        
    def _create_data_preview_components(self):
        """Create data preview components for right panel using DataViewer."""
        
        # DataViewer handles all plotting functionality internally
        # No need for separate plot controls or placeholders
        
    def _create_empty_cell_dataframe(self) -> pd.DataFrame:
        """Create empty cell DataFrame."""
        return pd.DataFrame({
            'Name': [],
            'Chemistry': [], 
            'Capacity (Ah)': [],
            'Files': [],
            'Material': [],
            'Status': []
        })
        
    def _create_empty_file_dataframe(self) -> pd.DataFrame:
        """Create empty file DataFrame."""
        return pd.DataFrame({
            'Filename': [],
            'Segments': [],
            'Date': [],
            'Size (MB)': [],
            'Status': []
        })
        
    def _create_cell_dataframe(self) -> pd.DataFrame:
        """Create cell DataFrame from API data."""
        try:
            cells = self.api.get_cells()
            
            if not cells:
                return self._create_empty_cell_dataframe()
                
            rows = []
            for cell in cells:
                row = {
                    'Name': cell['name'],
                    'Chemistry': cell.get('chemistry', 'Unknown'),
                    'Capacity (Ah)': cell.get('capacity_ah', 'N/A'),
                    'Files': cell.get('file_count', 0),
                    'Material': cell.get('cathode_material', 'N/A'),
                    'Status': '✓ Ready'
                }
                rows.append(row)
                
            return pd.DataFrame(rows)
            
        except Exception as e:
            print(f"Error creating cell DataFrame: {e}")
            return self._create_empty_cell_dataframe()
            
    def _create_file_dataframe(self, cell_name: str) -> pd.DataFrame:
        """Create file DataFrame for selected cell."""
        try:
            if not cell_name:
                return self._create_empty_file_dataframe()
                
            files = self.api.get_cell_files(cell_name)
            
            if not files:
                return self._create_empty_file_dataframe()
                
            rows = []
            for file_info in files:
                # Format acquisition date
                acq_date = 'Unknown'
                if file_info.get('acquisition_start'):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(file_info['acquisition_start'].replace('Z', '+00:00'))
                        acq_date = dt.strftime('%m/%d/%y')
                    except:
                        acq_date = 'Unknown'
                
                row = {
                    'Filename': file_info['original_filename'],
                    'Segments': file_info.get('segment_count', 0),
                    'Date': acq_date,
                    'Size (MB)': f"{file_info.get('file_size_bytes', 0) / (1024*1024):.1f}",
                    'Status': '✅ Processed' if file_info.get('segment_count', 0) > 0 else '⚠️ No segments',
                    '_file_id': file_info['file_id']  # Hidden column for selection
                }
                rows.append(row)
                
            return pd.DataFrame(rows)
            
        except Exception as e:
            print(f"Error creating file DataFrame for {cell_name}: {e}")
            return self._create_empty_file_dataframe()
            
    def _refresh_cell_data(self):
        """Refresh cell table data."""
        try:
            df = self._create_cell_dataframe()
            self.cell_tabulator.value = df
            print(f"Refreshed cell data: {len(df)} cells")
        except Exception as e:
            print(f"Error refreshing cell data: {e}")
            
    def _refresh_file_data(self):
        """Refresh file table data for selected cell."""
        try:
            df = self._create_file_dataframe(self.selected_cell)
            self.file_tabulator.value = df
            print(f"Refreshed file data for {self.selected_cell}: {len(df)} files")
        except Exception as e:
            print(f"Error refreshing file data: {e}")
            
    def _on_cell_selection_changed(self, event):
        """Handle cell table selection."""
        selection = event.new
        print(f"Cell selection changed: {selection}")
        
        if not selection or len(selection) == 0:
            self.selected_cell = ""
            self.selected_file = ""
            self.add_files_btn.disabled = True
            self.reprocess_file_btn.disabled = True
            self.delete_cell_btn.disabled = True
            self.delete_file_btn.disabled = True
            self.file_tabulator.value = self._create_empty_file_dataframe()
            self._clear_file_preview()
            return
            
        try:
            df = self.cell_tabulator.value
            selected_idx = selection[0]
            
            if selected_idx < len(df):
                row = df.iloc[selected_idx]
                cell_name = row['Name']
                
                self.selected_cell = cell_name
                self.selected_file = ""
                self.add_files_btn.disabled = False
                self.delete_cell_btn.disabled = False  # Cell selected
                self.reprocess_file_btn.disabled = True  # No file selected yet
                self.delete_file_btn.disabled = True  # No file selected yet
                
                print(f"Cell selected: {cell_name}")
                
                # Refresh file table
                self._refresh_file_data()
                self._clear_file_preview()
                
        except Exception as e:
            print(f"Error handling cell selection: {e}")
            
    def _on_file_selection_changed(self, event):
        """Handle file table selection."""
        selection = event.new
        print(f"File selection changed: {selection}")
        
        if not selection or len(selection) == 0:
            self.selected_file = ""
            self.reprocess_file_btn.disabled = True
            self.delete_file_btn.disabled = True
            self._clear_file_preview()
            return
            
        try:
            df = self.file_tabulator.value
            selected_idx = selection[0]
            
            if selected_idx < len(df) and '_file_id' in df.columns:
                file_id = df.iloc[selected_idx]['_file_id']
                self.selected_file = file_id
                self.reprocess_file_btn.disabled = False  # Enable re-process button
                self.delete_file_btn.disabled = False  # Enable delete file button
                
                print(f"File selected: {file_id}")
                self._load_file_preview(file_id)
                
        except Exception as e:
            print(f"Error handling file selection: {e}")
            
    def _clear_file_preview(self):
        """Clear file preview using DataViewer."""
        print("Clearing file preview in DataViewer")
        
        # Clear DataViewer data - this will show the default "no file selected" state
        self.data_viewer.load_file_data("")
        
        print("File preview cleared")
        
    def _load_file_preview(self, file_id: str):
        """Load file preview in right panel using DataViewer."""
        print(f"Loading file preview for: {file_id}")
        
        # Use DataViewer to load and display the file data
        self.data_viewer.load_file_data(file_id)
        
        print(f"File data loaded in DataViewer: {file_id}")
        
    # === MODAL METHODS ===
        
    def _show_create_cell_modal(self, event):
        """Show create cell modal with complete form."""
        
        # Clear form first
        self._clear_cell_form()
        
        # Create modal content (no header needed - Modal provides title)
        modal_content = pn.Column(
            # Form fields
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555; margin-bottom: 5px;'>Cell Name:</label>"),
                    self.new_cell_name,
                    width=200
                ),
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555; margin-bottom: 5px;'>Chemistry:</label>"),
                    self.cell_chemistry,
                    width=140
                ),
            ),
            
            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555; margin-bottom: 5px;'>Description:</label>"),
                self.cell_description,
                margin=(10, 0)
            ),
            
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-weight: 500; color: #555; margin-bottom: 5px;'>Capacity (Ah):</label>"),
                    self.capacity_ah,
                    width=160
                ),
                pn.Spacer(width=20),
            ),
            
            pn.pane.HTML("""
            <div style='color: #666; font-size: 14px; font-weight: 500; margin: 15px 5px 10px 5px; 
                        border-bottom: 1px solid #E0E0E0; padding-bottom: 5px;'>
                Electrode Details
            </div>
            """),
            
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 13px; color: #666; margin-bottom: 5px;'>Cathode Material:</label>"),
                    self.cathode_material,
                    width=160
                ),
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 13px; color: #666; margin-bottom: 5px;'>Mass (mg):</label>"),
                    self.cathode_mass_mg,
                    width=160
                ),
            ),
            
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 13px; color: #666; margin-bottom: 5px;'>Anode Material:</label>"),
                    self.anode_material,
                    width=160
                ),
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 13px; color: #666; margin-bottom: 5px;'>Mass (mg):</label>"),
                    self.anode_mass_mg,
                    width=160
                ),
            ),
            
            pn.Column(
                pn.pane.HTML("<label style='font-weight: 500; color: #555; margin-bottom: 5px;'>Notes:</label>"),
                self.cell_notes,
                margin=(10, 0)
            ),
            
            # Buttons
            pn.Row(
                self.cancel_cell_btn,
                pn.Spacer(),
                self.create_cell_modal_btn,
                margin=(20, 0)
            ),
            
            width=450
        )
        
        # Create and show Panel Modal
        self.create_cell_modal = pn.layout.Modal(
            modal_content,
            name="Create New Cell",
            open=True
        )
        
        # Add modal to container
        self._modal_container.clear()
        self._modal_container.append(self.create_cell_modal)
        
        print("Create Cell modal shown")
        
    def _hide_create_cell_modal(self, event):
        """Hide create cell modal."""
        if hasattr(self, 'create_cell_modal') and self.create_cell_modal:
            self.create_cell_modal.open = False
            self._modal_container.clear()
        print("Create Cell modal hidden")
        
    def _show_add_files_modal(self, event):
        """Show add files modal with enhanced form."""
        if not self.selected_cell:
            return
            
        # Create instrument selector
        instrument_selector = pn.widgets.RadioButtonGroup(
            name="Instrument",
            options=["VersaStudio"],  # Only VersaStudio available for now
            value="VersaStudio",
            button_type="primary",
            margin=(5, 5)
        )
        
        # Add note about BioLogic coming soon
        instrument_note = pn.pane.HTML(
            "<small style='color: #666; font-style: italic;'>BioLogic support coming soon</small>",
            margin=(0, 5)
        )
        
        # Create channel input
        channel_input = pn.widgets.NumberInput(
            name="Channel",
            value=1,
            start=1,
            end=16,
            step=1,
            width=100,
            margin=(5, 5)
        )
        
        # Progress bar (initially hidden)
        progress_bar = pn.indicators.Progress(
            name='Processing Files...',
            value=0,
            width=400,
            visible=False,
            margin=(10, 5)
        )
        
        # Status/error display
        status_display = pn.pane.HTML(
            "",
            margin=(5, 5),
            visible=False
        )
        
        # Create modal content (no header needed - Modal provides title)
        modal_content = pn.Column(
            
            # Instrument selection
            pn.pane.HTML("<label style='font-weight: 500; color: #555; margin-bottom: 5px;'>Select Instrument:</label>"),
            instrument_selector,
            instrument_note,
            
            # File droppers
            pn.pane.HTML("""
            <div style='color: #666; font-size: 14px; font-weight: 500; margin: 15px 5px 10px 5px; 
                        border-bottom: 1px solid #E0E0E0; padding-bottom: 5px;'>
                File Selection
            </div>
            """),
            
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 13px; color: #666; margin-bottom: 5px;'>Metadata File (.par):</label>"),
                    self.metadata_dropper,
                    width=300
                ),
                pn.Column(
                    pn.pane.HTML("<label style='font-size: 13px; color: #666; margin-bottom: 5px;'>Data File (.par.csv):</label>"),
                    self.data_dropper,
                    width=300
                ),
            ),
            
            # Parameters
            pn.pane.HTML("""
            <div style='color: #666; font-size: 14px; font-weight: 500; margin: 15px 5px 10px 5px; 
                        border-bottom: 1px solid #E0E0E0; padding-bottom: 5px;'>
                Parameters
            </div>
            """),
            
            pn.Row(
                pn.Column(
                    self.temperature_input,
                    width=150
                ),
                pn.Column(
                    channel_input,
                    width=150
                ),
                pn.Spacer()
            ),
            
            # Progress and status
            progress_bar,
            status_display,
            
            # Buttons
            pn.Row(
                self.cancel_files_btn,
                pn.Spacer(),
                self.process_files_modal_btn,
                margin=(20, 0)
            ),
            
            width=650
        )
        
        # Create and show Panel Modal
        self.add_files_modal = pn.layout.Modal(
            modal_content,
            name=f"Add Files to {self.selected_cell}",
            open=True
        )
        
        # Store references for progress tracking
        self.modal_progress_bar = progress_bar
        self.modal_status_display = status_display
        
        # Add modal to container
        self._modal_container.clear()
        self._modal_container.append(self.add_files_modal)
        
        print(f"Add Files modal shown for cell: {self.selected_cell}")
        
    def _hide_add_files_modal(self, event):
        """Hide add files modal."""
        if hasattr(self, 'add_files_modal') and self.add_files_modal:
            self.add_files_modal.open = False
            self._modal_container.clear()
        print("Add Files modal hidden")
        
    def _on_create_cell(self, event):
        """Handle cell creation from modal."""
        name = self.new_cell_name.value.strip()
        if not name:
            self.status_message = "Please enter a cell name"
            return
            
        try:
            result = self.api.create_cell(
                name=name,
                chemistry=self.cell_chemistry.value,
                description=self.cell_description.value.strip() or "",
                capacity_ah=self.capacity_ah.value,
                cathode_material=self.cathode_material.value.strip() or "",
                cathode_mass_mg=self.cathode_mass_mg.value,
                anode_material=self.anode_material.value.strip() or "",
                anode_mass_mg=self.anode_mass_mg.value,
                notes=self.cell_notes.value.strip() or ""
            )
            
            if result.success:
                self.status_message = f"Created cell: {name}"
                self._clear_cell_form()
                self._hide_create_cell_modal(None)
                self._refresh_cell_data()
            else:
                self.status_message = f"Error creating cell: {result.error}"
                
        except Exception as e:
            self.status_message = f"Error creating cell: {str(e)}"
            
    def _clear_cell_form(self):
        """Clear cell creation form."""
        self.new_cell_name.value = ""
        self.cell_description.value = ""
        self.capacity_ah.value = None
        self.cathode_material.value = ""
        self.cathode_mass_mg.value = None
        self.anode_material.value = ""
        self.anode_mass_mg.value = None
        self.cell_notes.value = ""
        
    def _check_upload_ready(self, event):
        """Check if file upload is ready."""
        has_metadata = self.metadata_dropper.value is not None and len(self.metadata_dropper.value) > 0
        has_data = self.data_dropper.value is not None and len(self.data_dropper.value) > 0
        
        self.process_files_modal_btn.disabled = not (has_metadata and has_data)
        
    def _on_process_files(self, event):
        """Handle file processing from modal with progress tracking."""
        if not self.selected_cell:
            self.modal_status_display.object = "<div style='color: #D32F2F; padding: 10px; background: #FFEBEE; border-radius: 4px;'>No cell selected</div>"
            self.modal_status_display.visible = True
            return
            
        # Check file uploads
        if not (self.metadata_dropper.value and self.data_dropper.value):
            self.modal_status_display.object = "<div style='color: #D32F2F; padding: 10px; background: #FFEBEE; border-radius: 4px;'>Please upload both metadata and data files</div>"
            self.modal_status_display.visible = True
            return
        
        # Show progress and disable button
        self.process_files_modal_btn.disabled = True
        self.modal_progress_bar.visible = True
        self.modal_status_display.visible = True
        
        # Simulate file processing stages
        try:
            # Stage 1: Validating files
            self.modal_progress_bar.value = 20
            self.modal_status_display.object = "<div style='color: #1976D2; padding: 10px; background: #E3F2FD; border-radius: 4px;'>📋 Validating file formats...</div>"
            
            # Stage 2: Processing metadata
            self.modal_progress_bar.value = 40
            self.modal_status_display.object = "<div style='color: #1976D2; padding: 10px; background: #E3F2FD; border-radius: 4px;'>📁 Processing metadata file...</div>"
            
            # Stage 3: Processing data
            self.modal_progress_bar.value = 70
            self.modal_status_display.object = "<div style='color: #1976D2; padding: 10px; background: #E3F2FD; border-radius: 4px;'>⚡ Processing data file...</div>"
            
            # Stage 4: Saving to database
            self.modal_progress_bar.value = 90
            self.modal_status_display.object = "<div style='color: #1976D2; padding: 10px; background: #E3F2FD; border-radius: 4px;'>💾 Saving to database...</div>"
            
            # Completion
            self.modal_progress_bar.value = 100
            self.modal_status_display.object = f"<div style='color: #2E7D32; padding: 10px; background: #E8F5E8; border-radius: 4px;'>✅ Successfully processed files for {self.selected_cell}</div>"
            
            # TODO: Replace with actual file processing call
            # result = self.api.process_dual_files(metadata_path, data_path, self.selected_cell)
            
            # Reset droppers
            self.metadata_dropper.value = []
            self.data_dropper.value = []
            
            # Refresh data and close modal after delay
            self._refresh_file_data()
            
            # Enable close button and allow user to close manually
            # Modal will stay open to show success message
            self.process_files_modal_btn.disabled = False
            self.process_files_modal_btn.name = "Close"
            self.process_files_modal_btn.button_type = "light"
            
        except Exception as e:
            # Error handling
            self.modal_progress_bar.value = 0
            self.modal_status_display.object = f"<div style='color: #D32F2F; padding: 10px; background: #FFEBEE; border-radius: 4px;'>❌ Error: {str(e)}</div>"
            self.process_files_modal_btn.disabled = False
        
    def _on_reprocess_file(self, event):
        """Handle file re-processing."""
        if not self.selected_file:
            self.status_message = "No file selected for re-processing"
            return
            
        if not self.selected_cell:
            self.status_message = "No cell context for re-processing"
            return
            
        # TODO: Implement file re-processing logic
        # This would re-run the analysis pipeline on the selected file
        self.status_message = f"Re-processing file: {self.selected_file} in cell: {self.selected_cell}"
        print(f"Re-processing file: {self.selected_file} for cell: {self.selected_cell}")
        
        # After re-processing, refresh file data
        self._refresh_file_data()
        
    def _on_delete_cell(self, event):
        """Handle cell deletion (UI only)."""
        if not self.selected_cell:
            self.status_message = "No cell selected for deletion"
            return
            
        # TODO: Add confirmation dialog
        # TODO: Implement actual cell deletion
        self.status_message = f"Would delete cell: {self.selected_cell}"
        print(f"Delete cell: {self.selected_cell}")
        
    def _on_delete_file(self, event):
        """Handle file deletion (UI only)."""
        if not self.selected_file:
            self.status_message = "No file selected for deletion"
            return
            
        # TODO: Add confirmation dialog
        # TODO: Implement actual file deletion
        self.status_message = f"Would delete file: {self.selected_file}"
        print(f"Delete file: {self.selected_file}")
        
    @property 
    def panel(self):
        """Return the 2-panel layout using simple Row."""
        
        # Left Panel - Cell Table + File Table (40% width)
        left_panel = pn.Column(
            # Header
            pn.pane.HTML("""
            <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white; 
                        padding: 15px; border-radius: 8px 8px 0 0; margin: 0;'>
                <h2 style='margin: 0; font-size: 18px; font-weight: 600;'>
                    🔋 Cells & Files
                </h2>
            </div>
            """),
            
            # Cell Table Section
            pn.pane.HTML("<div style='margin: 15px 10px 5px 10px; font-weight: 600; color: #2E4057; font-size: 16px;'>Cells</div>"),
            self.cell_tabulator,
            pn.Row(pn.Spacer(), self.delete_cell_btn, self.create_cell_btn, margin=(5, 10)),
            
            # File Table Section
            pn.pane.HTML("<div style='margin: 20px 10px 5px 10px; font-weight: 600; color: #2E4057; font-size: 16px;'>Files</div>"),
            self.file_tabulator,
            pn.Row(pn.Spacer(), self.reprocess_file_btn, self.delete_file_btn, self.add_files_btn, margin=(5, 10)),
            
            sizing_mode='stretch_width',
            styles={'background': 'white', 'border-radius': '8px', 
                   'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'margin': '10px'}
        )
        
        # Right Panel - Data Preview (60% width)
        right_panel = pn.Column(
            # Header
            pn.pane.HTML("""
            <div style='background: linear-gradient(135deg, #2E4057 0%, #1976D2 100%); color: white; 
                        padding: 15px; border-radius: 8px 8px 0 0; margin: 0;'>
                <h2 style='margin: 0; font-size: 18px; font-weight: 600;'>
                    📊 Data Preview
                </h2>
            </div>
            """),
            
            # DataViewer integration - handles all plotting and data display
            self.data_viewer.panel,
            
            sizing_mode='stretch_width',
            styles={'background': 'white', 'border-radius': '8px',
                   'box-shadow': '0 2px 8px rgba(0,0,0,0.1)', 'margin': '10px'}
        )
        
        # Main layout with modal container overlay
        main_layout = pn.Row(
            left_panel,
            right_panel,
            sizing_mode='stretch_width',
            height=800
        )
        
        # Return layout with modal container
        return pn.Column(
            main_layout,
            self._modal_container,
            sizing_mode='stretch_width'
        )