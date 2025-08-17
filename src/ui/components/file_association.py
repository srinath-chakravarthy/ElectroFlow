"""
File Association Tab for Panel UI.

Provides interface for uploading and associating files with battery cells.
Supports both single .par files and dual .par + .par.csv processing.
"""

import panel as pn
import param
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd


class FileAssociationTab(param.Parameterized):
    """
    File upload and cell association interface.
    
    Features:
    - File browser with default directory
    - Cell selection dropdown
    - Dual file processing (.par + .par.csv)
    - Upload progress indicators
    - File validation
    """
    
    # Parameters for reactive UI
    current_directory = param.String(default="/Users/srinathchakravarthy/", doc="Current browse directory")
    selected_files = param.List(default=[], doc="Currently selected files")
    selected_cell = param.String(default="", doc="Selected target cell")
    upload_in_progress = param.Boolean(default=False, doc="Upload in progress flag")
    
    def __init__(self, backend_api, **params):
        super().__init__(**params)
        self.api = backend_api
        self.default_directory = Path("/Users/srinathchakravarthy/")
        self.layout = None
        self.file_browser = None
        self.file_list_pane = None
        self.cell_selector = None
        self.upload_status = None
        self.setup_layout()
    
    def setup_layout(self):
        """Setup the complete file association layout."""
        
        # File browser section
        file_browser_section = self._create_file_browser()
        
        # File selection section
        file_selection_section = self._create_file_selection()
        
        # Upload section
        upload_section = self._create_upload_section()
        
        # Main layout
        self.layout = pn.Column(
            "## File Association",
            "Upload and associate .par and .par.csv files with battery cells",
            pn.Row(
                file_browser_section,
                pn.Column(
                    file_selection_section,
                    upload_section,
                    width=500
                )
            ),
            width=1200
        )
    
    def _create_file_browser(self):
        """Create file browser widget."""
        
        # Current directory display
        current_dir_pane = pn.pane.HTML(
            f"<p><strong>Current Directory:</strong> {self.current_directory}</p>",
            width=600
        )
        
        # Directory navigation
        nav_buttons = pn.Row(
            pn.widgets.Button(name="Home", width=80),
            pn.widgets.Button(name="Up", width=80),
            pn.widgets.TextInput(name="Path", value=str(self.current_directory), width=400)
        )
        
        # File list table
        self.file_browser = self._create_file_table()
        
        # Wire up navigation
        home_btn, up_btn, path_input = nav_buttons[0], nav_buttons[1], nav_buttons[2]
        
        def go_home(event):
            self.current_directory = str(self.default_directory)
            path_input.value = self.current_directory
            self._refresh_file_browser()
        
        def go_up(event):
            current_path = Path(self.current_directory)
            if current_path.parent != current_path:  # Not root
                self.current_directory = str(current_path.parent)
                path_input.value = self.current_directory
                self._refresh_file_browser()
        
        def navigate_to_path(event):
            new_path = Path(path_input.value)
            if new_path.exists() and new_path.is_dir():
                self.current_directory = str(new_path)
                self._refresh_file_browser()
            else:
                path_input.value = self.current_directory  # Reset to valid path
        
        home_btn.on_click(go_home)
        up_btn.on_click(go_up)
        path_input.param.watch(navigate_to_path, 'value')
        
        return pn.Column(
            "### File Browser",
            current_dir_pane,
            nav_buttons,
            self.file_browser,
            width=700
        )
    
    def _create_file_table(self):
        """Create file listing table."""
        result = self.api.list_directory_contents(Path(self.current_directory))
        
        if result['success']:
            contents = result['contents']
            if contents:
                # Convert to DataFrame
                df = pd.DataFrame(contents)
                
                # Format for display
                display_df = df[['name', 'type', 'size', 'modified', 'is_supported']].copy()
                display_df['size'] = display_df['size'].apply(
                    lambda x: f"{x:,} bytes" if pd.notna(x) else ""
                )
                display_df = display_df.rename(columns={
                    'name': 'Name',
                    'type': 'Type',
                    'size': 'Size', 
                    'modified': 'Modified',
                    'is_supported': 'Supported'
                })
                
                # Create table
                table = pn.widgets.Tabulator(
                    display_df,
                    selectable='checkbox',
                    width=650,
                    height=400,
                    pagination='local',
                    page_size=15
                )
                
                # Handle selection and navigation
                def on_click(event):
                    if event.new:
                        selected_indices = event.new
                        selected_items = []
                        for idx in selected_indices:
                            item = contents[idx]
                            if item['type'] == 'directory':
                                # Navigate to directory
                                if item['name'] == '..':
                                    new_path = Path(self.current_directory).parent
                                else:
                                    new_path = Path(item['path'])
                                self.current_directory = str(new_path)
                                self._refresh_file_browser()
                                return
                            elif item['is_supported']:
                                selected_items.append(item['path'])
                        
                        self.selected_files = selected_items
                        self._update_file_selection()
                
                table.param.watch(on_click, 'selection')
                return table
            else:
                return pn.pane.HTML("<p>Directory is empty</p>", width=650)
        else:
            return pn.pane.HTML(f'<p style="color: red;">Error: {result["error"]}</p>', width=650)
    
    def _refresh_file_browser(self):
        """Refresh the file browser."""
        if self.layout:
            # Update current directory display
            self.layout[2][0][1].object = f"<p><strong>Current Directory:</strong> {self.current_directory}</p>"
            # Update path input
            self.layout[2][0][2][2].value = self.current_directory
            # Replace file table
            self.layout[2][0][3] = self._create_file_table()
    
    def _create_file_selection(self):
        """Create file selection display."""
        
        self.file_list_pane = pn.pane.HTML(
            "<p>No files selected</p>",
            width=450, height=200
        )
        
        # Validation button
        validate_button = pn.widgets.Button(
            name="Validate Files",
            button_type="primary",
            width=150
        )
        
        validation_results_pane = pn.pane.HTML("", width=450)
        
        def validate_files(event):
            if not self.selected_files:
                validation_results_pane.object = '<p style="color: orange;">No files selected</p>'
                return
            
            file_paths = [Path(f) for f in self.selected_files]
            result = self.api.validate_file_compatibility(file_paths)
            
            if result['success']:
                html = "<h4>Validation Results</h4>"
                
                # Individual file results
                for file_result in result['individual_files']:
                    status = "✓" if file_result['valid'] else "✗"
                    color = "green" if file_result['valid'] else "red"
                    html += f'<p style="color: {color};">{status} {Path(file_result["file"]).name} ({file_result["type"]})</p>'
                    if file_result.get('error'):
                        html += f'<p style="color: red; margin-left: 20px;">Error: {file_result["error"]}</p>'
                
                # Dual file pairs
                if result['dual_pairs']:
                    html += "<h5>Dual File Pairs (Recommended)</h5>"
                    for pair in result['dual_pairs']:
                        status = "✓" if pair['valid'] else "✗"
                        color = "green" if pair['valid'] else "red"
                        par_name = Path(pair['par_file']).name
                        csv_name = Path(pair['csv_file']).name
                        html += f'<p style="color: {color};">{status} {par_name} + {csv_name}</p>'
                
                validation_results_pane.object = html
            else:
                validation_results_pane.object = f'<p style="color: red;">Validation failed: {result["error"]}</p>'
        
        validate_button.on_click(validate_files)
        
        return pn.Column(
            "### Selected Files",
            self.file_list_pane,
            validate_button,
            validation_results_pane
        )
    
    def _update_file_selection(self):
        """Update file selection display."""
        if not self.selected_files:
            self.file_list_pane.object = "<p>No files selected</p>"
            return
        
        html = "<h4>Selected Files:</h4><ul>"
        for file_path in self.selected_files:
            file_name = Path(file_path).name
            file_type = "PAR" if file_path.endswith('.par') else "PAR CSV" if file_path.endswith('.par.csv') else "Unknown"
            html += f"<li><strong>{file_name}</strong> ({file_type})</li>"
        html += "</ul>"
        
        self.file_list_pane.object = html
    
    def _create_upload_section(self):
        """Create upload controls section."""
        
        # Cell selector
        self.cell_selector = self._create_cell_selector()
        
        # Upload options
        duplicate_handling = pn.widgets.Select(
            name="Duplicate Handling",
            value="ask",
            options=["ask", "replace", "keep_both", "skip"],
            width=200
        )
        
        # Temperature input (file-level metadata)
        temperature_input = pn.widgets.FloatInput(
            name="Temperature (°C)",
            value=None,
            placeholder="Optional temperature",
            width=200
        )
        
        # Applied potential interpretation configuration
        applied_potential_config = pn.widgets.Select(
            name="Applied Potential Interpretation",
            value="2-electrode WE-CE voltage",
            options=[
                "2-electrode WE-CE voltage", 
                "3-electrode WE-RE voltage",
                "3-electrode CE-RE voltage",
                "Custom configuration"
            ],
            width=300
        )
        
        # Configuration description
        config_description = pn.pane.HTML(
            """
            <div style="font-size: 12px; color: #666; margin-top: 5px;">
                <strong>Default:</strong> 2-electrode (WE-CE) - Standard battery measurement<br>
                <strong>3-electrode (WE-RE):</strong> Working electrode vs reference<br>
                <strong>3-electrode (CE-RE):</strong> Counter electrode vs reference
            </div>
            """,
            width=300
        )
        
        # Upload buttons
        upload_single_btn = pn.widgets.Button(
            name="Upload Single Files",
            button_type="primary",
            width=180
        )
        
        upload_dual_btn = pn.widgets.Button(
            name="Upload Dual Files",
            button_type="success",
            width=180
        )
        
        # Status display
        self.upload_status = pn.pane.HTML("", width=450, height=150)
        
        # Upload handlers
        def upload_single_files(event):
            if not self.selected_files:
                self.upload_status.object = '<p style="color: orange;">No files selected</p>'
                return
            
            if not self.selected_cell:
                self.upload_status.object = '<p style="color: orange;">No cell selected</p>'
                return
            
            self.upload_in_progress = True
            upload_single_btn.disabled = True
            upload_dual_btn.disabled = True
            
            try:
                file_paths = [Path(f) for f in self.selected_files]
                
                # Prepare upload options with temperature and applied potential config
                upload_options = {
                    'duplicate_handling': duplicate_handling.value,
                    'temperature_c': temperature_input.value,
                    'applied_potential_interpretation': applied_potential_config.value
                }
                
                result = self.api.add_files_to_cell(
                    self.selected_cell, 
                    file_paths, 
                    upload_options
                )
                
                if result['success']:
                    summary = result['summary']
                    html = f"""
                    <div style="color: green;">
                        <h4>Upload Complete</h4>
                        <p>Total files: {summary['total_files']}</p>
                        <p>Successful uploads: {summary['successful_uploads']}</p>
                        <p>Failed uploads: {summary['failed_uploads']}</p>
                    </div>
                    """
                    
                    # Show individual results
                    if result['results']:
                        html += "<h5>Individual Results:</h5><ul>"
                        for file_result in result['results']:
                            file_name = Path(file_result['file']).name
                            if file_result['success']:
                                html += f"<li style='color: green;'>✓ {file_name} ({file_result['status']})</li>"
                            else:
                                error = file_result.get('error', 'Unknown error')
                                html += f"<li style='color: red;'>✗ {file_name}: {error}</li>"
                        html += "</ul>"
                    
                    self.upload_status.object = html
                else:
                    self.upload_status.object = f'<p style="color: red;">Upload failed: {result["error"]}</p>'
                    
            except Exception as e:
                self.upload_status.object = f'<p style="color: red;">Upload error: {str(e)}</p>'
            finally:
                self.upload_in_progress = False
                upload_single_btn.disabled = False
                upload_dual_btn.disabled = False
        
        def upload_dual_files(event):
            # Find dual file pairs
            par_files = [f for f in self.selected_files if f.endswith('.par')]
            csv_files = [f for f in self.selected_files if f.endswith('.par.csv')]
            
            if not par_files or not csv_files:
                self.upload_status.object = '<p style="color: orange;">Need both .par and .par.csv files for dual upload</p>'
                return
            
            if not self.selected_cell:
                self.upload_status.object = '<p style="color: orange;">No cell selected</p>'
                return
            
            # Find matching pairs
            dual_pairs = []
            for par_file in par_files:
                par_path = Path(par_file)
                csv_name = par_path.name + '.csv'
                for csv_file in csv_files:
                    if Path(csv_file).name == csv_name:
                        dual_pairs.append((Path(par_file), Path(csv_file)))
                        break
            
            if not dual_pairs:
                self.upload_status.object = '<p style="color: orange;">No matching .par/.par.csv pairs found</p>'
                return
            
            self.upload_in_progress = True
            upload_single_btn.disabled = True
            upload_dual_btn.disabled = True
            
            try:
                # Prepare upload options with temperature and applied potential config
                upload_options = {
                    'duplicate_handling': duplicate_handling.value,
                    'temperature_c': temperature_input.value,
                    'applied_potential_interpretation': applied_potential_config.value
                }
                
                results = []
                for par_path, csv_path in dual_pairs:
                    result = self.api.add_dual_files_to_cell(
                        self.selected_cell,
                        par_path,
                        csv_path,
                        upload_options
                    )
                    results.append({
                        'par_file': par_path.name,
                        'csv_file': csv_path.name,
                        'result': result
                    })
                
                # Format results
                html = "<h4>Dual File Upload Results</h4>"
                for pair_result in results:
                    if pair_result['result']['success']:
                        html += f"""
                        <div style="color: green;">
                            <p>✓ {pair_result['par_file']} + {pair_result['csv_file']}</p>
                            <p style="margin-left: 20px;">Status: {pair_result['result']['status']}</p>
                        </div>
                        """
                    else:
                        html += f"""
                        <div style="color: red;">
                            <p>✗ {pair_result['par_file']} + {pair_result['csv_file']}</p>
                            <p style="margin-left: 20px;">Error: {pair_result['result']['error']}</p>
                        </div>
                        """
                
                self.upload_status.object = html
                
            except Exception as e:
                self.upload_status.object = f'<p style="color: red;">Dual upload error: {str(e)}</p>'
            finally:
                self.upload_in_progress = False
                upload_single_btn.disabled = False
                upload_dual_btn.disabled = False
        
        upload_single_btn.on_click(upload_single_files)
        upload_dual_btn.on_click(upload_dual_files)
        
        return pn.Column(
            "### Upload to Cell",
            self.cell_selector,
            duplicate_handling,
            temperature_input,
            applied_potential_config,
            config_description,
            pn.Row(upload_single_btn, upload_dual_btn),
            "### Upload Status",
            self.upload_status
        )
    
    def _create_cell_selector(self):
        """Create cell selection dropdown."""
        result = self.api.get_all_cells()
        
        if result['success']:
            cells = result['cells']
            if cells:
                cell_options = [cell['cell_name'] for cell in cells]
                selector = pn.widgets.Select(
                    name="Target Cell",
                    options=cell_options,
                    width=200
                )
                
                def on_cell_change(event):
                    self.selected_cell = event.new
                
                selector.param.watch(on_cell_change, 'value')
                return selector
            else:
                return pn.pane.HTML('<p style="color: orange;">No cells available. Create a cell first.</p>')
        else:
            return pn.pane.HTML(f'<p style="color: red;">Error loading cells: {result["error"]}</p>')