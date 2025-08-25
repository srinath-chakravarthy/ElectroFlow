# UI Patterns - Registry System Implementation

**Purpose:** Document UI patterns to preserve during registry-based refactor

## Panel Framework Patterns to PRESERVE

### Widget Creation Patterns
```python
# Standard widget creation - PRESERVE
self.analysis_selector = pn.widgets.Select(
    name="Analysis Type",
    options=[("Display Name", "registry_key"), ...],
    value="default_key",
    width=200
)

# Event handler registration - PRESERVE  
self.analysis_selector.param.watch(self._on_analysis_changed, 'value')
```

### Layout Patterns
```python
# Column/Row layouts - PRESERVE
pn.Column(
    widget1,
    widget2,
    width=320,
    styles={'background': 'white', 'border': '1px solid #E0E0E0'}
)

# Responsive sizing - PRESERVE
sizing_mode='stretch_width',
min_height=400
```

### Status and Error Display
```python
# Status updates - PRESERVE
self.status_indicator.object = f"<div style='color: {color};'>{icon} {message}</div>"

# Error handling display - PRESERVE
return pn.pane.Markdown(f"**Error:** {error_message}")
```

### Professional Styling
```python
# Card-style containers - PRESERVE
styles={
    'background': 'white',
    'border': '1px solid #E0E0E0', 
    'border-radius': '8px',
    'padding': '15px',
    'margin': '10px'
}
```

## Plotting Patterns to PRESERVE

### HoloViews/hvplot Integration
```python
# DataFrame to hvplot - PRESERVE (enhance for registry)
plot = df.hvplot.line(
    x='time_s',
    y='value',
    by='group_id',
    title='Analysis Results',
    tools=['pan', 'wheel_zoom', 'reset', 'save']
)

# Plot container wrapping - PRESERVE
self.plot_pane = pn.pane.HoloViews(plot, sizing_mode='stretch_width')
```

## Routing Patterns to REPLACE

### Current If/Elif Chains - REPLACE
```python
# OLD pattern - REPLACE with registry
if analysis_type == "basic_statistics":
    return self._create_basic_stats_plot(data, settings)
elif analysis_type == "resistance_analysis":
    return self._create_resistance_plot(data, settings) 
elif analysis_type == "kinetics_analysis":
    return self._create_kinetics_plot(data, settings)

# NEW pattern - registry-driven
plot_config = ANALYSIS_REGISTRY[analysis_type]["plot_types"][plot_type]
return self._create_generic_plot(df, plot_config)
```

### Settings Panel Routing - REPLACE
```python
# OLD pattern - REPLACE
def show_settings_for_analysis(self, analysis_type):
    if analysis_type == "basic_statistics":
        self.basic_statistics_panel.visible = True
    elif analysis_type == "resistance_analysis": 
        self.resistance_panel.visible = True
    # etc...

# NEW pattern - registry-driven  
def show_settings_for_analysis(self, analysis_type):
    panel_config = ANALYSIS_REGISTRY[analysis_type]["settings_panel"]
    self._show_panel_by_config(panel_config)
```

## Data Access Patterns to REPLACE

### Dictionary Navigation - REPLACE
```python
# OLD pattern - REPLACE
backend_data = data.get('data', data)
individual_resistances = backend_data.get('individual_resistances', [])
core_segments = backend_data.get('core_segment_data', [])

for measurement, segment in zip(individual_resistances, core_segments):
    value = measurement.get('ir_immediate_ohm')
    voltage = segment.get('start_potential_v')

# NEW pattern - DataFrame operations
analysis_df = data  # Direct DataFrame from registry
for _, row in analysis_df.iterrows():
    value = row['value'] 
    voltage = row['start_potential_v']  # From joined segment data
```

## Component Communication to ENHANCE

### Cross-Component Updates
```python
# PRESERVE but enhance with registry events
def _on_analysis_type_changed(self, event):
    new_analysis = event.new
    
    # Registry lookup instead of if/elif
    analysis_config = ANALYSIS_REGISTRY[new_analysis]
    
    # Update settings panel
    self.analysis_panels.show_settings_for_analysis(new_analysis, analysis_config)
    
    # Update available plots  
    self.plotting_manager.update_available_plots(new_analysis, analysis_config)
```

## Error Handling Patterns to PRESERVE/ENHANCE

### Try/Catch with User Feedback
```python
# PRESERVE pattern but enhance with registry error handling
try:
    # Registry-based analysis call
    result_df = self.analytics_engine.get_analysis(analysis_type, groups, settings)
    
    # Update UI with success
    self._update_status(f"Analysis complete: {len(result_df)} results", "success")
    
except AnalysisError as e:
    # Preserve error display pattern
    self._update_status(f"Analysis error: {str(e)}", "error") 
    return pn.pane.Markdown(f"**Analysis Error:** {str(e)}")
```

## State Management to PRESERVE

### Parameterized State
```python
# PRESERVE param-based state management
class DataAnalysisTab(param.Parameterized):
    current_analysis = param.String(default="resistance_analysis")
    selected_groups = param.List(default=[])
    analysis_results = param.Dict(default={})  # May change to DataFrame
```

## Future Enhancements

### Registry-Driven Widget Generation
```python
# FUTURE: Generate settings widgets from registry config
def _create_settings_from_registry(self, analysis_config):
    settings_config = analysis_config.get("settings", {})
    widgets = []
    
    for setting_name, setting_config in settings_config.items():
        widget = self._create_widget_by_type(setting_config)
        widgets.append(widget)
    
    return pn.Column(*widgets)
```

### Auto-Generated Plot Options
```python
# FUTURE: Plot type options from registry
def update_available_plots(self, analysis_type):
    analysis_config = ANALYSIS_REGISTRY[analysis_type]
    plot_options = [(config["name"], plot_type) 
                   for plot_type, config in analysis_config["plot_types"].items()]
    self.plot_type_select.options = plot_options
```

## Migration Strategy

1. **Phase 1**: Add registry lookups alongside existing if/elif chains
2. **Phase 2**: Replace data transformation with DataFrame operations  
3. **Phase 3**: Replace routing logic with registry dispatch
4. **Phase 4**: Remove old patterns and consolidate code
5. **Phase 5**: Add registry-driven enhancements