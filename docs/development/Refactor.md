# Analytics System Refactor - Implementation Instructions

## Implementation Approach
**These are suggested patterns and examples.** Use your Python knowledge and the existing codebase patterns to implement the best solution. When you find established patterns in the project during your audit, extend those instead of forcing new approaches. Focus on achieving clean separation, standard interfaces, and registry configuration using whatever implementation fits the existing code style.

## Project Structure
```
project_root/
├── src_clean/              # All source code
│   ├── backend/           # API and business logic  
│   ├── panel_app/         # UI components (Panel framework)
│   ├── parsers/           # File parsing logic
│   └── core/              # Database and utilities
├── data_clean/            # Data storage
│   ├── electrochemical.db # SQLite database
│   └── [cell_folders]/    # File storage structure
└── [other files]
```

## Problem
Current analytics system requires 2 days of UI debugging per new analysis due to:
- 15+ specialized API methods with different return formats
- Same routing logic duplicated in 5+ UI files  
- Inefficient data transformations (dict → list → dict → DataFrame)

## Solution
Replace specialized methods with generic registry-driven system using standard DataFrame format.

## Pre-Refactor Investigation

**CRITICAL: Run this audit first to identify all dependencies:**

```bash
# Find all usage of specialized analytics methods
grep -r "get_electrochemical_" src_clean/
grep -r "resistance_analysis" src_clean/  
grep -r "kinetics_analysis" src_clean/
grep -r "dqdv_analysis" src_clean/

# Check which components need updating
grep -r "_run_analysis" src_clean/
grep -r "_create.*_plot" src_clean/
```

Document findings: Which tabs/CLI/jupyter use specialized methods?

## Implementation Plan

### Phase 1: Create Registry Foundation
**Files to create:**
- `src_clean/analysis/registry.py` - Configuration registry
- `src_clean/analysis/engine.py` - Pure analytics engine

**Registry format:**
```python
ANALYSIS_REGISTRY = {
    "resistance_analysis": {
        "name": "Resistance Analysis",
        "calculation_method": "calculate_resistance_analysis", 
        "unit": "Ω",
        "plot_types": {
            "time_series": {"x": "time_s", "y": "value", "by": "group_id"},
            "histogram": {"y": "value"}
        }
    }
}
```

**Standard DataFrame columns (every analysis must return):**
```
time_s | value | group_id | segment_id | analysis_type | quality_score | technique | unit
```

**Files to modify:**
- `src_clean/backend/api.py` - Add generic `get_analysis()` method
- Keep all existing specialized methods during Phase 1

### Phase 2: Convert to DataFrame-First
**Pattern: Replace dictionary building with direct DataFrame returns**

**In database methods:** Replace `[dict(row) for row in cursor.fetchall()]` with `pd.read_sql()`

**In calculation methods:** Change return from custom dict to standard DataFrame:
```python
# OLD
def get_electrochemical_resistance_analysis(self, groups):
    return {"individual_resistances": [...], "summary_statistics": {...}}

# NEW  
def calculate_resistance_analysis(self, groups) -> pd.DataFrame:
    segments_df = pd.read_sql(query, connection)
    segments_df['value'] = calculate_resistance(segments_df) 
    segments_df['analysis_type'] = 'resistance'
    return segments_df[STANDARD_COLUMNS]
```

### Phase 3: Replace UI Routing Logic
**Files to modify with EXACT changes:**

**`src_clean/panel_app/main_tab.py`:**
- Replace `_run_analysis()` if/elif chain with registry lookup
- PRESERVE: All Panel widgets, layout, status updates, event handlers
- CHANGE ONLY: The routing logic inside methods

**`src_clean/panel_app/plotting.py`:**
- Replace specialized `_create_X_plot()` methods with generic DataFrame plotting  
- PRESERVE: `_create_hvplot_with_standards()`, `_wrap_plot_in_container()`, all Panel patterns
- CHANGE ONLY: Data extraction logic (dict navigation → DataFrame operations)

**`src_clean/panel_app/results.py`:**
- Replace specialized formatting with generic DataFrame display
- PRESERVE: Panel display patterns, HTML styling
- CHANGE ONLY: Data processing logic

**`src_clean/panel_app/analysis_panels.py`:**
- Replace `show_settings_for_analysis()` if/elif with registry
- PRESERVE: Widget configurations, `options=[(name, value)]` tuples, Panel layouts
- CHANGE ONLY: Panel visibility logic

### Phase 4: Update All Dependent Components
**Based on Phase 1 audit, update these components:**

**CLI (if uses analytics):**
- `src_clean/cli/` - Update to use generic `get_analysis()` 
- Create `analytics.py` with direct AnalyticsEngine calls

**Jupyter (if exists):**  
- Create `src_clean/jupyter/analytics.py` with notebook-friendly interface

**Other Tabs (if use analytics):**
- Tab 1: Check if file processing triggers analytics
- Tab 2: Check if group management uses analytics methods

### Phase 5: Remove Legacy Methods
**Only after ALL components updated:**
- Delete specialized API methods from `src_clean/backend/api.py`
- Delete specialized calculation methods  
- Keep only generic `get_analysis()` interface

## Key Implementation Rules

### Data Flow Requirements
- Database → DataFrame (1 step) 
- API → DataFrame passthrough (0 steps)
- UI → DataFrame to plot (1 step)
- Total: 2 transformations (currently 4)

### UI Preservation Rules
**PRESERVE (don't change):**
- Panel widget syntax: `pn.widgets.Select(options=[...])`
- Layout patterns: `pn.Column()`, `pn.Row()`, responsive sizing
- Event handlers: `.param.watch()`, `.on_click()`  
- Helper methods: `_create_hvplot_with_standards()`, status updates
- CSS styling, professional design patterns

**CHANGE (refactor only):**
- if/elif routing chains → registry lookups
- Dictionary navigation → DataFrame column access
- Custom dict processing → standard DataFrame operations
- Specialized API calls → generic `get_analysis()` calls

### Interface Independence
- `AnalyticsEngine`: Zero Panel/param/UI dependencies
- Calculation methods: Pure functions returning DataFrames
- Registry: Plain Python data structures
- UI layer: Thin wrapper consuming AnalyticsEngine

## Success Validation

### Test Each Phase
- [ ] Phase 1: Registry loads, generic API works alongside existing
- [ ] Phase 2: Calculations return standard DataFrames
- [ ] Phase 3: UI works with generic methods, same user experience
- [ ] Phase 4: All interfaces (CLI/Jupyter/other tabs) work with generic methods
- [ ] Phase 5: Only generic methods exist, everything still works

### Final Verification
- [ ] Add new analysis in 30 minutes (registry + calculation only)
- [ ] Zero UI changes needed for new analysis
- [ ] CLI analytics work independently  
- [ ] Same analysis works in web/CLI/jupyter
- [ ] Performance suitable for on-the-fly analytics

## Expected Outcomes
- **Development speed**: 2 days → 30 minutes per new analysis
- **Code reduction**: 1000+ UI lines → ~200 lines  
- **API simplification**: 15+ methods → 2-3 generic methods
- **Maintainability**: Change 1 registry file vs 5+ UI files

The refactored system will be clean, maintainable, debuggable, and enable rapid feature development focused on electrochemical calculations rather than software plumbing.