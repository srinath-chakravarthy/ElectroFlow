# Registry System Integration - Debugging Reference

**Created:** August 24, 2025  
**Context:** Phase 3 Complete - Testing full Tab 3 registry integration  
**Branch:** `dev-clean-registry`

## Quick Context

We just completed transforming **16 Tab 3 routing points** from hard-coded if/elif logic to a **unified registry-driven architecture**. All 4 Tab 3 components now use the registry system.

## Registry Architecture Overview

```
User Input → analysis_panels.py (settings) → main_tab.py (execution) → analysis_engine.py (registry dispatch) → plotting.py (visualization) → results.py (formatting)
```

## Key Integration Points to Test

### 1. **Settings → Analysis Execution Flow**
**File:** `main_tab.py:_run_analysis()` ← `analysis_panels.py:get_current_settings()`
```python
# Should call: engine.get_analysis(analysis_type, data_filters, settings)
# Fallback: self._run_analysis_fallback() if registry fails
```

### 2. **Registry → Settings Panel Generation**
**File:** `analysis_panels.py:_create_registry_based_settings_panels()`
```python
# Should dynamically create settings panels from registry.list_analyses()
# Watch for: Widget creation errors, missing analysis configurations
```

### 3. **Analysis Results → Plot Generation**
**File:** `plotting.py:_create_registry_driven_plot()`
```python
# Should extract DataFrames and use generic plotting configurations
# Watch for: Data structure mismatches, missing plot configurations
```

### 4. **Analysis Results → Formatted Display**
**File:** `results.py:_format_registry_based_results()`
```python
# Should use registry config to format results consistently
# Watch for: Missing analysis names, data extraction errors
```

## Common Debugging Scenarios

### **Scenario 1: "No analysis results appearing"**
**Check:**
1. `main_tab.py` - Is `engine.get_analysis()` being called?
2. `analysis_engine.py` - Are results being returned properly?
3. Console logs for "✅ Registry analysis" vs "⚠️ Registry analysis failed"

### **Scenario 2: "Settings panel not updating"**
**Check:**
1. `analysis_panels.py:show_settings_for_analysis()` - Is correct panel being shown?
2. Registry cache in `settings_panels_cache` - Are panels being created?
3. Console logs for "✅ Created registry-based settings panel"

### **Scenario 3: "Plots not displaying"**
**Check:**
1. `plotting.py:_extract_dataframe_for_plotting()` - Is DataFrame being created?
2. Plot configuration in `_create_generic_dataframe_plot()` - Are plot configs found?
3. Console logs for "✅ Created registry-driven plot" vs fallback messages

### **Scenario 4: "Registry fallback being used"**
**Check:**
1. Registry import paths - Are `get_analysis_registry()` imports working?
2. Analysis registration - Are all analyses properly registered?
3. Console logs for "⚠️ Registry-based [component] failed, using fallback"

## Key Console Log Messages

**Success Messages:**
- `✅ Registry analysis {analysis_type}: {segments} segments`
- `✅ Created registry-based settings panel for {analysis_name}`  
- `✅ Created registry-driven plot for {analysis_type}: {plot_type}`
- `✅ Created registry-based result display for {analysis_type}`

**Warning Messages:**
- `⚠️ Registry analysis failed, using fallback: {error}`
- `⚠️ No registry settings found for {analysis_type}, using fallback`
- `⚠️ Using fallback plot options for {analysis_type}`
- `⚠️ Registry-based formatting failed for {analysis_type}, using fallback`

**Error Messages:**
- `❌ Error showing settings for {analysis_type}: {error}`
- `❌ Registry-driven plot creation failed: {error}`
- `❌ Registry-based result formatting failed: {error}`

## Testing Workflow

1. **Start Panel App:** `python echem_web.py`
2. **Navigate to Tab 3:** Data Analysis tab
3. **Select Cell & Groups:** Choose test groups
4. **Try Each Analysis Type:** basic_statistics, resistance_analysis, kinetics_analysis
5. **Check Each Component:** Settings display, analysis execution, plot generation, results display
6. **Monitor Console:** Look for ✅ success vs ⚠️ fallback vs ❌ error messages

## Fallback Safety Net

Every component has fallback mechanisms:
- **analysis_panels.py**: Falls back to simple settings panels
- **plotting.py**: Falls back to basic technique count plots  
- **results.py**: Falls back to generic result display
- **main_tab.py**: Falls back to original API methods

**This means the system should NEVER completely break - it will degrade gracefully to working functionality.**

## Files Modified in Phase 3

1. `src_clean/panel_app/components/data_analysis_tab/main_tab.py`
2. `src_clean/panel_app/components/data_analysis_tab/analysis_panels.py`  
3. `src_clean/panel_app/components/data_analysis_tab/plotting.py`
4. `src_clean/panel_app/components/data_analysis_tab/results.py`
5. `REFACTOR_PROGRESS.md`

## Registry Foundation (Phases 1-2)

**Already Working and Tested:**
- `src_clean/core/query_engine.py` - Universal query system ✅
- `src_clean/analysis/registry.py` - Analysis registry ✅  
- `src_clean/backend/analysis_engine.py` - Central dispatcher ✅
- All analysis functions (basic_statistics, resistance_analysis, etc.) ✅

**Test Script:** `python test_analysis_engine.py` (should show all ✅ working)

## Success Criteria

✅ **Registry-Driven**: All Tab 3 components use registry instead of hard-coded routing  
✅ **Zero Breaking Changes**: Tab 1/2, CLI, existing functionality unchanged  
✅ **Graceful Fallbacks**: System degrades to working functionality if registry fails  
✅ **30-Minute Goal**: Framework ready for rapid new analysis development  
✅ **Electrochemical Focus**: User can focus on algorithms vs UI plumbing