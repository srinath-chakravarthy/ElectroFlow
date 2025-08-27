# Explorer UI Redesign Plan - Analysis-Centric Intent-Based Design

**Version:** 1.0  
**Date:** August 27, 2025  
**Status:** Ready for Implementation  
**Target:** Tab 3 - Electrochemical Explorer UI Enhancement

## Overview

Complete redesign of the Electrochemical Explorer UI from technique-based to analysis-centric organization with intent-based sections and context-sensitive controls.

## Design Philosophy

### Current Issues
- **Technique-centric**: Users must know which technique to select first
- **Column overload**: 50+ columns with no categorization or guidance  
- **Static controls**: Same plot options regardless of analysis type
- **No units awareness**: Plot axes lack proper unit labels and context

### New Approach
- **Analysis-centric**: Focus on what users want to analyze, not data source
- **Intent-based sections**: Organize by analytical intent (Trends/Quality/Insights)
- **Context-sensitive**: Plot options adapt to selected analysis type
- **Units-aware**: Smart defaults and proper unit labeling throughout

## UI Architecture

### Three-Tier Organization

#### 1. **Trends Section**
**Purpose**: Time-series and relationship analysis  
**Plot Type**: X-Y scatter/line plots  
**Data Focus**: Quantitative metrics over time or vs. other variables

**Analyses Available**:
- Basic Statistics Analytics (7 metrics)
- Resistance Analytics (6 metrics) 
- Kinetics Analytics (5 metrics)
- Equilibrium Analytics (6 metrics)
- Current Decay Analytics (4 metrics)

#### 2. **Quality Section**  
**Purpose**: Distribution and statistical analysis  
**Plot Type**: Histograms, box plots, violin plots  
**Data Focus**: Statistical distributions and data quality assessment

**Analyses Available**: Same as Trends but focusing on distribution columns

#### 3. **Insights Section**
**Purpose**: Categorical and comparative analysis  
**Plot Type**: Bar charts, categorical plots  
**Data Focus**: Technique comparisons, group analysis, categorical breakdowns

**Analyses Available**: Same as Trends but focusing on categorical columns

### Column Categorization System

Each analysis declares three column types:

```python
output_columns = {
    "metrics": ["time_constant_s", "diffusion_coeff_cm2_s"],     # X-Y plotting
    "quality": ["r_squared", "fit_quality_score"],              # Distributions  
    "insights": ["dominant_process", "analysis_type"]           # Categorical
}
```

## Implementation Roadmap

### Phase 1: Registry Enhancements (Backend)
**Duration**: 1-2 sessions  
**Files**: `src_clean/analysis/registry.py`

1. **Add units metadata** to AnalysisConfig:
   ```python
   units_metadata: Dict[str, str] = field(default_factory=dict)
   # {"time_constant_s": "seconds", "diffusion_coeff_cm2_s": "cm²/s"}
   ```

2. **Add analysis descriptions** for UI tooltips:
   ```python
   column_descriptions: Dict[str, str] = field(default_factory=dict)
   ```

3. **Update all 5 analyses** with units and descriptions

4. **Add registry helper methods**:
   - `get_metrics_columns(analysis_id, include_units=True)`
   - `get_quality_columns(analysis_id, include_units=True)` 
   - `get_insight_columns(analysis_id, include_units=True)`
   - `get_column_unit(analysis_id, column_name)`

### Phase 2: Column Selection UI (Frontend Core)
**Duration**: 2-3 sessions  
**Files**: `src_clean/panel_app/components/electrochemical_explorer_tab.py`

1. **Replace technique selector** with analysis-centric tabs:
   ```python
   analysis_tabs = pn.Tabs(
       ("Trends", trends_panel),
       ("Quality", quality_panel), 
       ("Insights", insights_panel)
   )
   ```

2. **Create section panels** for each intent:
   - Expandable sections per analysis type
   - Multi-select column choosers with units display
   - Column count indicators

3. **Implement column filtering logic**:
   - Filter by analysis applicability to current cell data
   - Show/hide sections based on data availability
   - Real-time column count updates

### Phase 3: Context-Sensitive Plot Configuration (Modal)
**Duration**: 2-3 sessions  
**Files**: New modal dialog system

1. **Create plot configuration modal**:
   - Triggered after column selection and "Plot" button
   - Context-aware based on selected analysis and columns
   - Smart defaults for axes and plot types

2. **Implement axis configuration**:
   - X-axis selector with time-based smart defaults
   - Y-axis multi-select with unit grouping
   - Automatic unit detection and labeling

3. **Add plot type suggestions**:
   - Line plots for time-series data
   - Scatter for correlations  
   - Overlays for multi-metric comparison

### Phase 4: Enhanced Plotting with Units (Visualization)
**Duration**: 2-3 sessions  
**Files**: Plotting logic and hvplot integration

1. **Units-aware plot generation**:
   - Automatic axis labeling with units
   - Unit consistency checking
   - Smart axis scaling based on unit types

2. **Enhanced plot features**:
   - Multi-axis support for different units
   - Hover tooltips with full metadata
   - Export capabilities with unit preservation

3. **Plot optimization**:
   - Efficient data handling for large datasets
   - Progressive loading for responsive UI
   - Plot caching for repeated configurations

### Phase 5: Integration and Polish (Finalization)
**Duration**: 1-2 sessions  
**Files**: Testing, documentation, integration

1. **End-to-end testing**:
   - All analysis types with real data
   - UI responsiveness and error handling
   - Performance validation

2. **Documentation updates**:
   - User guide sections
   - Developer documentation
   - API documentation

3. **Final integration**:
   - Ensure backward compatibility
   - Clean up old code
   - Performance optimization

## Technical Specifications

### Data Flow
```
Cell Selection → Registry Analysis Discovery → Column Categorization → Intent-Based UI → Context-Sensitive Configuration → Units-Aware Plotting
```

### Registry Integration Points
- `get_analysis_options()` for available analyses
- `output_columns` for column categorization
- `applicable_techniques` for data filtering
- New units and metadata fields

### UI Component Structure
```
ElectrochemicalExplorerTab
├── CellSelector (existing)
├── AnalysisTabsPanel (new)
│   ├── TrendsSection
│   ├── QualitySection  
│   └── InsightsSection
├── PlotConfigModal (new)
└── EnhancedPlotPane (enhanced)
```

## Expected Benefits

### User Experience
- **Intuitive workflow**: Analysis intent → Column selection → Plot configuration
- **Reduced cognitive load**: Clear categorization and guidance
- **Faster insights**: Smart defaults and context-sensitive options
- **Professional output**: Proper units and axis labeling

### Developer Experience  
- **Extensible architecture**: Easy to add new analyses and columns
- **Maintainable code**: Clear separation of concerns
- **Registry-driven**: Automatic UI generation from analysis configs
- **Future-ready**: Supports advanced features like multi-plot layouts

### Technical Improvements
- **Better performance**: Eliminates unnecessary analysis execution
- **Robust architecture**: Static declarations prevent runtime failures
- **Scalable design**: Handles growing number of analyses and columns
- **Units awareness**: Foundation for advanced analytical features

## Implementation Notes

### Backward Compatibility
- Current plot generation logic preserved as fallback
- Existing analysis functions unchanged
- Database schema unaffected

### Performance Considerations
- Static column discovery eliminates runtime analysis execution
- Lazy loading of analysis sections based on data availability
- Efficient caching of registry metadata

### Future Extensions
- Multi-plot layouts (Phase 6)
- Advanced statistical overlays
- Interactive plot annotations
- Export to publication formats

---

**This design provides a comprehensive foundation for professional electrochemical data analysis with an intuitive, analysis-centric interface that scales with user expertise and dataset complexity.**