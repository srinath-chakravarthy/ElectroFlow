# Electrochemical Explorer UI Redesign - Implementation Plan

## Overview
Transform the current accordion-based explorer into a clean, modern interface with 30/70 layout, multi-plot support, and smart analysis selection.

## Core Design Changes

### 1. Layout Transformation
**Current**: Fixed 300px left panel + right panel  
**New**: 30% / 70% proportional layout

```python
# Layout Structure - NO FIXED WIDTHS
main_layout = pn.Row(
    left_panel,   # 30% - analysis selection
    right_panel,  # 70% - config + visualization
    sizing_mode='stretch_width'  # Key: proportional scaling
)
```

### 2. Left Panel - Clean Analysis Selection
**Replace**: Accordion structure  
**With**: Simple categorical selection

**Structure**:
- Analysis Category (Radio buttons)
- Specific Analysis (Dropdown - updates based on category)  
- Cell Selection (Multi-select)
- Temperature Filter (Dropdown)
- Status indicator

**Integration Note**: Use existing `registry.get_analysis_options()` to populate dropdowns dynamically.

### 3. Right Panel - Two-Section Design
**Top Section (120px)**: Plot configuration bar
**Bottom Section (Flexible)**: Dynamic plot grid

## Multi-Plot Architecture

### Plot State Management
**Concept**: Each plot is self-contained with its own state

```python
class PlotState(param.Parameterized):
    # Analysis config
    analysis_type = param.String()
    x_axis = param.String() 
    y_axis = param.String()
    
    # View controls (NEW)
    x_range_start = param.Number()
    x_range_end = param.Number()
    
    # Units (NEW)  
    x_unit = param.String()
    y_unit = param.String()
```

### Dynamic Grid Layout
**Grid Logic**: Automatic layout based on plot count

```python
# Grid patterns
1 plot:  [████████████████]  # Full width
2 plots: [████████][████████]  # Side by side  
3 plots: [████████████████]   # Top full
         [████████][████████]  # Bottom split
4 plots: [████████][████████]  # 2x2 grid
         [████████][████████]
```

**Implementation**: Use Panel's Row/Column with `sizing_mode='stretch_both'`

## Key Features Implementation

### 1. Plot Selection Mechanism
**User Flow**: Click any plot → Top controls switch to that plot's config

**Visual Feedback**:
- Active plot: Highlighted border
- Inactive plots: Subtle styling
- Top bar shows "Plot X Configuration"

### 2. Range Sliders & Units
**Auto-updating sliders** based on data bounds:

```python
@param.depends('active_plot', 'plot_config.analysis_type')
def create_range_controls():
    # Get data bounds from current analysis
    bounds = get_data_bounds(current_analysis, x_col, y_col)
    
    x_slider = pn.widgets.RangeSlider(
        name=f"X Range ({x_unit})",
        start=bounds.x_min,
        end=bounds.x_max,
        value=(current_x_range)
    )
```

### 3. Units Integration
**Registry Enhancement**: Each analysis declares units metadata

```python
# Registry provides this info
analysis_config = {
    "output_columns": ["time_s", "ir_immediate_ohm"],
    "units_metadata": {
        "time_s": ("Time", "seconds", "s"),
        "ir_immediate_ohm": ("Resistance", "ohms", "Ω")
    }
}
```

## Implementation Steps

### Phase 1: Layout Restructure
1. **Replace fixed width with proportional** (30/70 split)
2. **Create clean left panel** with radio buttons + dropdowns
3. **Restructure right panel** into config bar + plot area
4. **Remove accordion components**

### Phase 2: Multi-Plot Foundation  
1. **Create PlotState class** for compartmentalized state
2. **Implement plot grid manager** with automatic layouts
3. **Add plot selection mechanism** (click to activate)
4. **Create add/remove plot controls**

### Phase 3: Range Controls & Units
1. **Add range sliders** to top configuration bar
2. **Implement data-bound ranges** that update with analysis changes
3. **Integrate units metadata** from registry
4. **Add proper axis labeling** with units

### Phase 4: Polish & Integration
1. **Connect to existing registry system** for analysis options
2. **Integrate with current cell/data selection**
3. **Add plot synchronization options** (sync axes across plots)
4. **Implement export/save functionality**

## Integration Points

### With Existing Registry System
- Use `registry.get_analysis_categories()` for left panel options
- Use `registry.get_output_columns(analysis_id)` for axis options  
- Use `registry.get_units_metadata(analysis_id)` for proper labeling

### With Current Data Pipeline
- Maintain existing `api.get_research_dataset()` calls
- Use existing cell selection logic
- Preserve temperature filtering functionality

### With Plot Generation
- Enhance existing hvplot integration with range controls
- Add units to plot titles, axes, tooltips
- Implement multi-plot layout rendering

## Key Implementation Notes

### State Management Strategy
- **Each plot manages own state** (analysis, ranges, units)
- **Explorer coordinates** active plot, grid layout
- **Simple param.depends** for auto-updates

### No Complex JavaScript
- **Pure Panel widgets** for all interactions
- **Param system handles** state changes automatically  
- **Click handlers** just update param values

### Backward Compatibility
- **Preserve existing analysis functions** unchanged
- **Keep current data format** and API calls
- **Maintain registry integration** points

This redesign maximizes screen real estate while providing a much cleaner, more intuitive interface for multi-plot electrochemical analysis.