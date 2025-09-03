# Perspective Modal Implementation Guide

**Document Status**: Technical Reference  
**Created**: September 3, 2025  
**Issue**: Panel Modal + Perspective interaction conflicts  
**Current Solution**: Separate server modal with known closing issues

## Problem Summary

### Root Issue Discovered
**Critical Bug**: Missing column specification in Perspective widget
```python
# ❌ BROKEN - Incomplete column specification
columns=["time_s"]  

# ✅ WORKING - Both X and Y columns required
columns=["time_s", "potential_v"]  
```

**Impact**: Perspective widget requires both X and Y columns for proper initialization and rendering.

### Suspected Z-Index Conflicts
**Issue**: Panel's `pn.layout.Modal` creates stacking context conflicts with Perspective dropdown menus
- **Evidence**: GitHub issues from 1+ year ago with potential resolutions
- **Symptoms**: Perspective configuration menu (three dots) not accessible, data selection blocked
- **Status**: Suspected but not definitively proven - requires investigation of GitHub solutions

## Current Working Solution: Separate Server Modal

### Implementation
```python
def _open_segment_inspector_modal(self, arrow_data: bytes, segment_id: str):
    """Open Perspective modal with segment data."""
    try:
        # Convert Arrow bytes to DataFrame (Panel compatibility fix)
        import pyarrow as pa
        reader = pa.ipc.open_stream(pa.py_buffer(arrow_data))
        arrow_table = reader.read_all()
        df_for_perspective = arrow_table.to_pandas()
        
        # Create Perspective pane - CRITICAL: both X and Y columns
        perspective_pane = pn.pane.Perspective(
            df_for_perspective,
            plugin="d3_xy_scatter",
            columns=["time_s", "potential_v"],  # ⭐ BOTH columns required
            settings=True,
            width=1000,
            height=700,
            theme='material'
        )
        
        # Modal content
        modal_content = pn.Column(
            pn.pane.HTML(f"<h3>🔬 Segment {segment_id} Inspector</h3>"),
            pn.pane.HTML("<p>Hover over points to see raw data + analytical metadata</p>"),
            perspective_pane,
            pn.Row(
                pn.widgets.Button(name="Export Data", button_type="primary"),
                pn.widgets.Button(name="Close", button_type="light"),
                sizing_mode='stretch_width'
            ),
            sizing_mode='stretch_width'
        )
        
        # Separate server modal
        self._show_modal(modal_content)
        
    except Exception as e:
        logger.error(f"Failed to open segment inspector modal: {e}")
        self._update_status("Error creating segment inspector", "danger")

def _show_modal(self, content):
    """Show modal using separate server."""
    try:
        modal = pn.template.MaterialTemplate(
            title="Segment Inspector",
            sidebar=[],
            main=[content],
            header_background='#2596be',
        )
        
        # Separate server on port 5008
        modal.show(port=5008, autoreload=False, threaded=True)
        
    except Exception as e:
        logger.error(f"Failed to show modal: {e}")
        self._update_status("Modal display error - check logs", "danger")
```

### Known Issues with Current Solution

**🚨 Critical: Process Termination Issues**
- **Manual window closing**: User must manually close browser window
- **Ctrl+C ineffective**: Cannot terminate modal server with standard interrupt
- **Process persistence**: Requires `lsof` and manual process killing
- **Resource cleanup**: Modal servers may persist after main app termination

**Example process cleanup:**
```bash
# Find hanging modal processes
lsof -i :5008
lsof -i :5009

# Manual termination required
kill -9 <PID>
```

## Alternative Solution: On-Demand Tab Approach

### When to Use
- **If**: Z-index conflicts confirmed in Panel Modal + Perspective
- **If**: Separate server modal closing issues become problematic
- **If**: Need integrated user experience without window management

### Complete Code Diff for Migration

**1. Main App Changes** (`src_clean/panel_app/main_app.py`):

```python
# ADD: Dynamic tab methods
class ElectrochemicalApp(param.Parameterized):
    def __init__(self, **params):
        # ... existing code ...
        
        # CHANGE: Store tabs reference for dynamic access
        self.tabs = pn.Tabs(  # ⭐ Changed from local variable
            ("🔋 Cell & File Management", tab1_content),
            ("🔗 Group Management", tab2_content),
            ("📊 Data Analysis", tab3_content),
            ("🔬 Explorer", tab4_content),
            dynamic=True,
            sizing_mode='stretch_width'
        )
        
        # CHANGE: Pass parent reference
        self.electrochemical_explorer_tab = ElectrochemicalExplorerTabWrapper(
            api=self.api, 
            parent_app=self  # ⭐ Add parent reference
        )
        
        # ... existing layout code uses self.tabs ...

    # ADD: Dynamic tab management methods
    def add_inspector_tab(self, tab_name, tab_content):
        """Add dynamic segment inspector tab."""
        try:
            self.tabs.append((tab_name, tab_content))
            self.tabs.active = len(self.tabs) - 1
            print(f"✅ Added inspector tab: {tab_name}")
        except Exception as e:
            print(f"❌ Failed to add inspector tab: {e}")
    
    def remove_inspector_tab(self, tab_index):
        """Remove inspector tab and return to Explorer."""
        try:
            if tab_index >= 4:  # Only remove dynamic tabs
                del self.tabs[tab_index]
                self.tabs.active = 3  # Return to Explorer tab
                print(f"✅ Removed inspector tab at index {tab_index}")
        except Exception as e:
            print(f"❌ Failed to remove inspector tab: {e}")
```

**2. Explorer Component Changes** (`electrochemical_explorer_tab.py`):

```python
# CHANGE: Accept parent_app reference
class CleanElectrochemicalExplorer(param.Parameterized):
    def __init__(self, api, parent_app=None, **params):
        super().__init__(**params)
        self.api = api
        self.parent_app = parent_app  # ⭐ Store parent reference

# REMOVE: All modal-related code
# DELETE: self._create_segment_inspector()
# DELETE: self.segment_modal, self.segment_modal_close_btn
# DELETE: Modal from layout and callbacks

# REPLACE: Modal method with tab method
def _open_segment_inspector_tab(self, arrow_data: bytes, segment_id: str):
    """Open Perspective in new tab."""
    try:
        if not self.parent_app:
            self._update_status("Cannot open inspector: no parent app reference", "danger")
            return
            
        # Convert Arrow bytes to DataFrame
        import pyarrow as pa
        reader = pa.ipc.open_stream(pa.py_buffer(arrow_data))
        arrow_table = reader.read_all()
        df_for_perspective = arrow_table.to_pandas()
        
        # Create Perspective - CRITICAL: both columns
        perspective_pane = pn.pane.Perspective(
            df_for_perspective,
            plugin="d3_xy_scatter",
            columns=["time_s", "potential_v"],  # ⭐ Both columns required
            settings=True,
            height=700,
            theme='material',
            sizing_mode='stretch_width'
        )
        
        # Close button with tab cleanup
        close_button = pn.widgets.Button(
            name="Close Inspector", 
            button_type="light", 
            width=150
        )
        
        def close_inspector_tab(event):
            current_index = self.parent_app.tabs.active
            self.parent_app.remove_inspector_tab(current_index)
            self._update_status(f"Closed inspector for segment {segment_id}", "info")
        
        close_button.on_click(close_inspector_tab)
        
        # Tab content
        tab_content = pn.Column(
            pn.pane.HTML(f"<h3>🔬 Segment {segment_id} Inspector</h3>"),
            pn.pane.HTML("<p>Use the configuration menu to customize the view.</p>"),
            perspective_pane,
            pn.Row(pn.Spacer(), close_button, sizing_mode='stretch_width'),
            sizing_mode='stretch_both',
            margin=20
        )
        
        # Add to main app
        tab_name = f"📊 {segment_id}"
        self.parent_app.add_inspector_tab(tab_name, tab_content)
        
        self._update_status(f"Opened inspector for segment {segment_id} in new tab", "success")
        
    except Exception as e:
        logger.error(f"Failed to open segment inspector tab: {e}")
        self._update_status("Error creating segment inspector", "danger")

# CHANGE: Update click handler
def _handle_plot_click(self, x, y):
    # ... existing click detection code ...
    
    # CHANGE: Call tab method instead of modal
    self._open_segment_inspector_tab(arrow_data, segment_id)  # ⭐ Tab approach
```

**3. Wrapper Class Changes**:

```python
class ElectrochemicalExplorerTabWrapper(param.Parameterized):
    def __init__(self, api, parent_app=None, **params):  # ⭐ Accept parent_app
        super().__init__(**params)
        try:
            self.tab = CleanElectrochemicalExplorer(api, parent_app=parent_app)  # ⭐ Pass through
            self.panel = self.tab.panel
        except Exception as e:
            self.panel = pn.pane.Alert(f"Failed to initialize explorer: {e}", alert_type="danger")
```

## Data Display Requirements

### Current Issue
- **Limited Columns**: Current implementation shows only `["time_s", "potential_v"]`
- **User Control**: Should display ALL available columns from segment data
- **Perspective Configuration**: Let user decide plotting via Perspective's built-in controls

### Recommended Enhancement
```python
# Instead of hardcoded columns:
columns=["time_s", "potential_v"]

# Show all available columns:
columns=list(df_for_perspective.columns)  # Let Perspective handle all columns
```

## Related Documentation

- **[Complete User Guide → README.md](../README.md)** - Installation and usage
- **[Technical Architecture → CLAUDE.md](../CLAUDE.md)** - System architecture
- **[Registry System → registry/REGISTRY_SYSTEM_COMPLETE.md](registry/REGISTRY_SYSTEM_COMPLETE.md)** - Analysis framework
- **[Panel UI Components → panel_ui_components.md](panel_ui_components.md)** - UI component patterns

## Decision Matrix

| Approach | Perspective Interaction | Window Management | Process Cleanup | Development Complexity |
|----------|------------------------|-------------------|-----------------|----------------------|
| **Separate Server Modal** | ✅ Perfect | ❌ Manual closing | ❌ `lsof` required | ✅ Simple |
| **In-Page Modal** | ❌ Suspected z-index conflicts | ✅ Integrated | ✅ Clean | ✅ Simple |
| **On-Demand Tabs** | ✅ Perfect | ✅ Integrated | ✅ Clean | ⚠️ More complex |

## Conclusion

**Current Status**: Separate server modal works for Perspective interaction but has significant process management issues.

**Next Steps**: 
1. Investigate GitHub solutions for Panel Modal + Perspective z-index conflicts
2. Consider migrating to on-demand tabs if process issues become problematic
3. Enhance data display to show all available columns

**Critical Reminder**: Always specify both X and Y columns in Perspective widget configuration.