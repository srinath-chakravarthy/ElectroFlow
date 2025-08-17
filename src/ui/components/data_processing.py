"""
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
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from visualization.plot_templates import PlotTemplates


class DataProcessingTab(param.Parameterized):
    """
    Cell data processing interface with technique-centric workflow.
    
    Workflow: Active Cell → Files → Techniques → Groups → Manual Plotting
    """
    
    # Parameters for reactive UI
    active_cell_id = param.Integer(default=None, allow_None=True, doc="Active cell ID")
    active_cell_name = param.String(default="", doc="Active cell name")
    selected_file_ids = param.List(default=[], doc="Selected file IDs")
    selected_techniques = param.List(default=[], doc="Selected technique references")
    refresh_trigger = param.Number(default=0, doc="Trigger for refreshing data")
    
    def __init__(self, backend_api, **params):
        super().__init__(**params)
        self.api = backend_api
        self.layout = None
        self.files_table = None
        self.techniques_table = None
        self.groups_table = None
        self.plot_panel = None
        self.plot_templates = PlotTemplates()
        self.selected_group_id = None
        self.setup_layout()
    
    def setup_layout(self):
        """Setup the complete data processing layout."""
        
        # Left side: Data selection (Files → Techniques)
        data_selection_section = self._create_data_selection_section()
        
        # Right side: Group management and plotting
        group_management_section = self._create_group_management_section()
        
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
        
        @pn.depends(self.param.active_cell_name, self.param.active_cell_id)
        def get_status_display(*args):
            if self.active_cell_id:
                return pn.pane.HTML(
                    f"""
                    <div style="padding: 10px; background-color: #e6f3ff; border-left: 4px solid #0066cc; margin-bottom: 15px;">
                        <h4 style="margin: 0;">Processing Data for Cell: {self.active_cell_name}</h4>
                        <p style="margin: 5px 0;">Select files → techniques → create groups → plot results</p>
                    </div>
                    """,
                    width=1400
                )
            else:
                return pn.pane.HTML(
                    """
                    <div style="padding: 10px; background-color: #f5f5f5; border-left: 4px solid #999; margin-bottom: 15px;">
                        <p style="margin: 0; color: #666;">No active cell selected. Please select a cell from the Cell Management tab.</p>
                    </div>
                    """,
                    width=1400
                )
        
        return get_status_display
    
    def _create_data_selection_section(self):
        """Create the left side data selection section."""
        
        # Files section
        files_section = self._create_files_section()
        
        # Techniques section
        techniques_section = self._create_techniques_section()
        
        return pn.Column(
            "### Data Selection",
            files_section,
            "---",
            techniques_section,
            width=600
        )
    
    def _create_files_section(self):
        """Create files selection section."""
        
        @pn.depends(self.param.active_cell_id, self.param.refresh_trigger)
        def get_files_table(*args):
            if not self.active_cell_id:
                return pn.pane.HTML(
                    "<p style='color: #666;'>No active cell selected</p>",
                    width=580
                )
            
            # Get files for active cell
            result = self.api.get_cell_files(self.active_cell_id)
            if result['success']:
                files = result['files']
                if files:
                    # Convert to DataFrame
                    df = pd.DataFrame(files)
                    
                    # Format for display
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
                    
                    # Create table with selection
                    table = pn.widgets.Tabulator(
                        display_df,
                        pagination='remote',
                        page_size=8,
                        selectable='checkbox',
                        width=580,
                        height=200
                    )
                    
                    # Handle file selection
                    def on_file_selection_change(event):
                        if event.new:
                            selected_indices = event.new
                            selected_files = [files[i] for i in selected_indices]
                            self.selected_file_ids = [f['file_id'] for f in selected_files]
                            self._update_techniques_display()
                        else:
                            self.selected_file_ids = []
                            self._update_techniques_display()
                    
                    table.param.watch(on_file_selection_change, 'selection')
                    
                    return table
                else:
                    return pn.pane.HTML(
                        "<p>No files found. Upload files using the Cell Management tab.</p>",
                        width=580
                    )
            else:
                return pn.pane.HTML(
                    f'<p style="color: red;">Error loading files: {result["error"]}</p>',
                    width=580
                )
        
        return pn.Column(
            "#### Files",
            get_files_table,
            width=600
        )
    
    def _create_techniques_section(self):
        """Create techniques selection section."""
        
        # Techniques table placeholder
        self.techniques_display = pn.pane.HTML(
            "<p style='color: #666;'>Select files above to view techniques</p>",
            width=580
        )
        
        return pn.Column(
            "#### Techniques",
            self.techniques_display,
            width=600
        )
    
    def _update_techniques_display(self):
        """Update techniques display based on selected files."""
        if not self.selected_file_ids:
            self.techniques_display.object = "<p style='color: #666;'>Select files above to view techniques</p>"
            return
        
        # Get techniques for selected files
        all_techniques = []
        for file_id in self.selected_file_ids:
            segments = self.api.db.get_file_segments(file_id)
            for segment in segments:
                technique_ref = {
                    'file_id': file_id,
                    'segment_number': segment['segment_number'],
                    'technique_name': segment.get('technique_name', 'Unknown'),
                    'fundamental_technique': segment.get('fundamental_technique', 'Unknown'),
                    'start_time_s': segment.get('start_time_s', 0),
                    'end_time_s': segment.get('end_time_s', 0),
                    'point_count': segment.get('point_count', 0)
                }
                all_techniques.append(technique_ref)
        
        if all_techniques:
            # Create DataFrame for techniques
            df = pd.DataFrame(all_techniques)
            
            # Format for display
            display_df = df[['file_id', 'segment_number', 'fundamental_technique', 'technique_name', 'point_count']].copy()
            display_df.columns = ['File ID', 'Segment', 'Type', 'Technique', 'Points']
            
            # Create table with selection
            table = pn.widgets.Tabulator(
                display_df,
                pagination='remote',
                page_size=8,
                selectable='checkbox',
                width=580,
                height=200
            )
            
            # Handle technique selection
            def on_technique_selection_change(event):
                if event.new:
                    selected_indices = event.new
                    selected_refs = [all_techniques[i] for i in selected_indices]
                    # Store technique references for group creation
                    self.selected_techniques = [
                        {"file_id": ref['file_id'], "segment_number": ref['segment_number']}
                        for ref in selected_refs
                    ]
                else:
                    self.selected_techniques = []
            
            table.param.watch(on_technique_selection_change, 'selection')
            
            self.techniques_display.object = table
        else:
            self.techniques_display.object = "<p>No techniques found in selected files</p>"
    
    def _create_group_management_section(self):
        """Create the right side group management section."""
        
        # Group creation form
        group_creation_form = self._create_group_creation_form()
        
        # Existing groups table
        groups_section = self._create_groups_section()
        
        # Plotting section
        plotting_section = self._create_plotting_section()
        
        return pn.Column(
            "### Group Management & Plotting",
            group_creation_form,
            "---",
            groups_section,
            "---",
            plotting_section,
            width=750
        )
    
    def _create_group_creation_form(self):
        """Create group creation form."""
        
        # Form inputs
        group_name_input = pn.widgets.TextInput(
            name="Group Name",
            placeholder="e.g., Formation_Cycles, OCV_Analysis",
            width=200
        )
        
        group_type_select = pn.widgets.Select(
            name="Group Type",
            value="Custom",
            options=["OCV Analysis", "Rate Analysis", "Cycle Comparison", 
                    "EIS Analysis", "GITT Analysis", "Custom"],
            width=150
        )
        
        description_input = pn.widgets.TextInput(
            name="Description",
            placeholder="Brief description of the group",
            width=350
        )
        
        # Create button
        create_group_button = pn.widgets.Button(
            name="Create Group",
            button_type="primary",
            width=120
        )
        
        # Status message
        group_status_message = pn.pane.HTML("", width=700)
        
        def create_group_callback(event):
            """Handle group creation."""
            if not self.active_cell_id:
                group_status_message.object = '<p style="color: red;">No active cell selected</p>'
                return
            
            if not group_name_input.value or not group_name_input.value.strip():
                group_status_message.object = '<p style="color: red;">Group name is required</p>'
                return
                
            if not self.selected_techniques:
                group_status_message.object = '<p style="color: red;">No techniques selected</p>'
                return
            
            try:
                # Create group in database
                group_id = self.api.db.create_user_group(
                    cell_id=self.active_cell_id,
                    group_name=group_name_input.value.strip(),
                    group_type=group_type_select.value,
                    description=description_input.value or "",
                    techniques=self.selected_techniques
                )
                
                group_status_message.object = f'<p style="color: green;">Group "{group_name_input.value}" created successfully</p>'
                
                # Clear form
                group_name_input.value = ""
                description_input.value = ""
                group_type_select.value = "Custom"
                
                # Refresh groups display
                self.refresh_trigger += 1
                
            except Exception as e:
                group_status_message.object = f'<p style="color: red;">Error creating group: {str(e)}</p>'
        
        create_group_button.on_click(create_group_callback)
        
        return pn.Column(
            "#### Create New Group",
            pn.Row(group_name_input, group_type_select),
            description_input,
            pn.Row(create_group_button, pn.Spacer(width=20)),
            group_status_message
        )
    
    def _create_groups_section(self):
        """Create existing groups section."""
        
        @pn.depends(self.param.active_cell_id, self.param.refresh_trigger)
        def get_groups_table(*args):
            if not self.active_cell_id:
                return pn.pane.HTML(
                    "<p style='color: #666;'>No active cell selected</p>",
                    width=730
                )
            
            # Get groups for active cell
            groups = self.api.db.get_cell_groups(self.active_cell_id)
            if groups:
                # Convert to DataFrame
                df = pd.DataFrame(groups)
                
                # Format for display
                display_columns = ['group_name', 'group_type', 'description', 'created_at']
                available_columns = [col for col in display_columns if col in df.columns]
                display_df = df[available_columns]
                
                # Add technique count
                display_df['technique_count'] = df['techniques'].apply(
                    lambda x: len(x) if isinstance(x, list) else 0
                )
                
                # Rename columns
                column_names = {
                    'group_name': 'Group Name',
                    'group_type': 'Type',
                    'description': 'Description',
                    'technique_count': 'Techniques',
                    'created_at': 'Created'
                }
                display_df = display_df.rename(columns=column_names)
                
                # Create table with selection
                table = pn.widgets.Tabulator(
                    display_df,
                    pagination='remote',
                    page_size=5,
                    selectable='checkbox',
                    width=730,
                    height=150
                )
                
                # Handle group selection for plotting
                def on_group_selection_change(event):
                    if event.new:
                        selected_index = event.new[0]
                        selected_group = groups[selected_index]
                        self.selected_group_id = selected_group['id']
                    else:
                        self.selected_group_id = None
                
                table.param.watch(on_group_selection_change, 'selection')
                
                return table
            else:
                return pn.pane.HTML(
                    "<p>No groups found. Create groups from selected techniques above.</p>",
                    width=730
                )
        
        return pn.Column(
            "#### Existing Groups",
            get_groups_table
        )
    
    def _create_plotting_section(self):
        """Create manual plotting section."""
        
        # Plot type selection
        plot_type_select = pn.widgets.Select(
            name="Plot Type",
            value="Voltage vs Time",
            options=[
                "Voltage vs Time",
                "Current vs Time", 
                "Power vs Time",
                "Voltage vs Current",
                "Capacity vs Voltage",
                "Nyquist Plot (EIS)",
                "Bode Plot (EIS)",
                "Multi-Panel Overview"
            ],
            width=200
        )
        
        # Plot button
        plot_button = pn.widgets.Button(
            name="Generate Plot",
            button_type="primary",
            width=120
        )
        
        # View analytics button
        analytics_button = pn.widgets.Button(
            name="View Analytics",
            button_type="light",
            width=120
        )
        
        # Plot display area
        plot_display = pn.pane.Plotly(
            width=730,
            height=400
        )
        
        # Analytics display area
        analytics_display = pn.pane.HTML(
            "<p style='color: #666;'>Select a group and click 'View Analytics' to see analysis results</p>",
            width=730,
            height=200
        )
        
        def generate_plot_callback(event):
            """Handle plot generation."""
            if not self.selected_group_id:
                plot_display.object = self.plot_templates._create_error_figure("No group selected. Please select a group from the table above.")
                return
            
            try:
                # Load group data
                group_data = self._load_group_data_for_plotting(self.selected_group_id)
                if group_data is None or group_data.is_empty():
                    plot_display.object = self.plot_templates._create_error_figure("No data found for selected group")
                    return
                
                # Generate plot based on selected type
                plot_type = plot_type_select.value
                group_info = self.api.db.get_user_group_by_id(self.selected_group_id)
                title = f"{plot_type} - {group_info['group_name']}" if group_info else plot_type
                
                if plot_type == "Voltage vs Time":
                    fig = self.plot_templates.create_voltage_time_plot(group_data, title, group_by='technique_id')
                elif plot_type == "Current vs Time":
                    fig = self.plot_templates.create_current_time_plot(group_data, title, group_by='technique_id')
                elif plot_type == "Power vs Time":
                    fig = self.plot_templates.create_power_time_plot(group_data, title, group_by='technique_id')
                elif plot_type == "Voltage vs Current":
                    fig = self.plot_templates.create_iv_curve_plot(group_data, title, group_by='technique_id')
                elif plot_type == "Capacity vs Voltage":
                    fig = self.plot_templates.create_capacity_voltage_plot(group_data, title, group_by='technique_id')
                elif plot_type == "Nyquist Plot (EIS)":
                    fig = self.plot_templates.create_nyquist_plot(group_data, title, group_by='technique_id')
                elif plot_type == "Bode Plot (EIS)":
                    fig = self.plot_templates.create_bode_plot(group_data, title, group_by='technique_id')
                elif plot_type == "Multi-Panel Overview":
                    fig = self.plot_templates.create_multi_panel_overview(group_data, title)
                else:
                    fig = self.plot_templates._create_error_figure(f"Plot type '{plot_type}' not implemented")
                
                plot_display.object = fig
                
            except Exception as e:
                plot_display.object = self.plot_templates._create_error_figure(f"Plot generation error: {str(e)}")
        
        def view_analytics_callback(event):
            """Handle analytics viewing."""
            if not self.selected_group_id:
                analytics_display.object = "<p style='color: red;'>No group selected. Please select a group from the table above.</p>"
                return
            
            try:
                # Get group analytics
                result = self.api.analyze_group(self.selected_group_id)
                if result['success']:
                    analysis = result['analysis_result']
                    
                    # Format analytics for display
                    html = f"""
                    <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                        <h4>{analysis['group_name']} Analytics ({analysis['group_type']})</h4>
                        <p><strong>Techniques:</strong> {analysis['technique_count']}</p>
                        <p><strong>Data Points:</strong> {analysis['total_points']:,}</p>
                        <p><strong>Time Span:</strong> {analysis['time_span_hours']:.2f} hours</p>
                        <p><strong>Overall Quality:</strong> {analysis['quality_metrics'].get('overall_quality', 0):.3f}</p>
                        
                        <details>
                            <summary><strong>Detailed Results</strong></summary>
                            <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; font-size: 12px; max-height: 150px; overflow-y: auto;">
{json.dumps(analysis['analysis_results'], indent=2)}
                            </pre>
                        </details>
                    </div>
                    """
                    analytics_display.object = html
                else:
                    analytics_display.object = f"<p style='color: red;'>Analytics error: {result['error']}</p>"
                    
            except Exception as e:
                analytics_display.object = f"<p style='color: red;'>Analytics error: {str(e)}</p>"
        
        plot_button.on_click(generate_plot_callback)
        analytics_button.on_click(view_analytics_callback)
        
        return pn.Column(
            "#### Manual Plotting & Analytics",
            pn.Row(plot_type_select, plot_button, analytics_button),
            plot_display,
            "#### Group Analytics",
            analytics_display
        )
    
    def _load_group_data_for_plotting(self, group_id: int):
        """Load and combine data for a group for plotting."""
        try:
            group = self.api.db.get_user_group_by_id(group_id)
            if not group:
                return None
            
            group_data = []
            
            for technique_ref in group['techniques']:
                file_id = technique_ref['file_id']
                segment_number = technique_ref['segment_number']
                
                # Load processed file data
                data = self.api.storage.load_processed_file(file_id)
                if data is None:
                    continue
                
                # Filter to specific segment
                segment_data = data.filter(pl.col('segment_number') == segment_number)
                if segment_data.is_empty():
                    continue
                
                # Add group metadata for plotting
                segment_data = segment_data.with_columns([
                    pl.lit(file_id).alias('source_file_id'),
                    pl.lit(segment_number).alias('source_segment'),
                    pl.lit(f"{file_id}_seg{segment_number}").alias('technique_id')
                ])
                
                group_data.append(segment_data)
            
            if group_data:
                import polars as pl
                return pl.concat(group_data, how="vertical_relaxed")
            else:
                return None
                
        except Exception as e:
            print(f"Error loading group data: {e}")
            return None
    
    def set_active_cell(self, cell_id: int, cell_name: str):
        """Set the active cell for data processing."""
        self.active_cell_id = cell_id
        self.active_cell_name = cell_name
        # Clear selections when cell changes
        self.selected_file_ids = []
        self.selected_techniques = []
        self._update_techniques_display()