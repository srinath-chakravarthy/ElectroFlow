# Electrochemical Data Explorer - Implementation Specification

## Project Goal
Create a unified visual data explorer for electrochemical analysis that enables rapid, interactive exploration of segment-level data across single or multiple cells.

## Core Requirements

### **User Workflow**
1. **Primary Selection**: User selects cells (multi-select checkboxes)
2. **Secondary Selection**: User selects technique from dropdown 
3. **Auto-Configuration**: System auto-populates interface based on selections
4. **Interactive Exploration**: User modifies plot parameters and sees immediate updates

### **Data Architecture**
- **Single DataFrame**: ~90 columns, max 50k rows, loaded once in memory
- **In-Memory Operations**: All filtering via pandas boolean indexing
- **No Complex Queries**: Avoid backend calls during exploration

## Interface Components

### **Primary Controls**
- **Cell Selection**: Multi-select widget for available cells
- **Technique Selection**: Dropdown for fundamental techniques (REST, Galvanostatic, Potentiostatic, EIS)
- **Plot Trigger**: Button to generate auto-configured interface

### **Auto-Generated Interface (Post-Plot Button)**
- **Y-Metrics**: Multi-select from auto-detected numeric columns for selected technique
- **X-Axis Variable**: Dropdown with context-appropriate options
- **Plot Type**: Toggle between Line/Scatter and Distribution plots
- **Grouping/Coloring**: Dropdown for categorical variables
- **Filters**: Auto-generated quality and temporal filters

## Plot Types & X-Axis Logic

### **Line/Scatter Plots**
**X-Axis Options:**
- Time variables: `time_s`, `start_timestamp`, `cumulative_duration_s`
- Capacity variables: `cumulative_charge_ah`, `cumulative_discharge_ah`, `capacity_cumulative_ah`
- Voltage variables: `start_potential_v`, `end_potential_v`

### **Distribution Plots** 
**X-Axis Options:**
- Any selected Y-metric becomes the distribution variable
- System shows distribution of selected metric across chosen grouping

## Grouping & Coloring

### **Available Grouping Options (Auto-Detected)**
- `cell_name`: When multiple cells selected
- `temperature_c`: When temperature variation exists (discrete values: 10°C, 20°C, etc.)
- `quality_level`: Generated quality categories (High/Medium/Low based on analysis success)
- `None`: No grouping/single color

### **Implementation Logic**
```python
# Auto-detect available grouping options
available_grouping = ['None']
if len(selected_cells) > 1:
    available_grouping.append('cell_name')
if df_filtered['temperature_c'].nunique() > 1:
    available_grouping.append('temperature_c')  
if has_quality_variation(df_filtered):
    available_grouping.append('quality_level')
```

## Filter System

### **Dual Filter Approach: Temporal + Data-Based**

#### **Temporal Filters (Always Available)**
- **Duration Filter**: Minimum segment duration (dropdown: 60s, 30s, 10s, Any)
- **Point Count Filter**: Minimum data points (dropdown: 100, 50, 10, 5, Any)
- **Time Range Filter**: Optional start/end time bounds

#### **Data-Based Filters (Analysis-Specific)**

**For Fit-Based Techniques (REST, Potentiostatic):**
- Fit quality checkboxes: Successful only (R² ≥ 0.9), Include partial (R² ≥ 0.7), Include failed
- R² threshold slider/dropdown

**For Calculation-Based Techniques (IR, Statistics):**  
- Data sufficiency checkboxes: Clean calculations only, Include partial, Include failed
- Error status filters

### **Filter Implementation Pattern**
```python
# Base temporal filtering
temporal_mask = (
    (df['duration_s'] >= duration_threshold) & 
    (df['point_count'] >= point_threshold)
)

# Analysis-specific data filtering
if is_fit_based_technique(technique):
    data_mask = (df['R_squared'] >= r_squared_threshold) & (df['fit_converged'] == True)
else:
    data_mask = (df['calculation_success'] == True)

# Combine filters
final_df = df[temporal_mask & data_mask]
```

## Auto-Population Logic

### **Column Detection**
- **Numeric Columns**: `df.select_dtypes(include=[np.number]).columns`
- **Categorical Columns**: `df.select_dtypes(include=['category', 'object']).columns`
- **Technique-Specific Filtering**: Filter columns based on analysis type

### **Quality Assessment**
- **Fit-Based**: Use R², fit_converged, rmse columns
- **Calculation-Based**: Use success flags, error_status columns
- **Universal**: Check for null values, outliers

## Data Feedback System

### **Data Availability Reporting**
Display real-time feedback on filter results:
```
📊 Filter Results:
✅ Cell_1: 23 segments (18 high quality, 5 partial)
✅ Cell_2: 15 segments (12 high quality, 3 partial)  
❌ Cell_3: No segments match current filters
⚠️  Cell_4: 8 segments (quality issues detected)
```

### **Interactive Updates**
- All filter changes trigger immediate plot updates
- Show/hide data availability warnings
- Dynamic axis label updates based on selections

## Technical Implementation Notes

### **Performance Considerations**
- **Data Decimation**: For >10k points, implement intelligent decimation
- **Lazy Loading**: Only compute expensive operations when needed
- **Caching**: Cache filtered DataFrames for common filter combinations

### **Error Handling**
- **Empty Results**: Clear messaging when filters produce no data
- **Missing Columns**: Graceful fallback when expected columns missing
- **Plot Failures**: Informative error messages with suggested fixes

### **Required UI Architecture Patterns**

#### **Cell-Centric Design**
- **Tabulator for cell display**: Use tabulator to show available cells in table format (follow existing Tab 2 patterns)
- **Cell selection as primary**: Multi-cell selection drives all subsequent interface updates
- **Multi-select capability**: Enable checkbox or similar multi-select patterns for cell selection

#### **Data Display Components**
- **Tabulator for data feedback**: Use tabulator for showing filtered results and data availability ("Cell_1: 23 segments")
- **hvplot for visualization**: Use established hvplot library for all plotting (consistent with existing tabs)
- **Existing plotting patterns**: Follow established decimation and styling patterns from Tab 1 data viewer

#### **Integration Constraints**
- **DataFrame-first approach**: Work with pandas DataFrames throughout, avoid nested dictionaries
- **Memory-based operations**: Use pandas boolean indexing for filtering, not SQL queries
- **API integration**: Use existing `api.get_*` methods rather than direct database calls
- **Component isolation**: Ensure no breaking changes to existing Tab 1/2/3 functionality

### **Integration Points**
- **Existing Backend**: Use `api.get_all_segments_dataframe()` for data loading
- **Registry System**: Leverage existing column auto-discovery where applicable  
- **Panel Patterns**: Follow established widget and layout patterns from existing tabs
- **Status Feedback**: Use existing status bar patterns for user feedback and progress indication

## Success Criteria

### **User Experience**
- **Rapid Iteration**: Change cells/technique/filters with <2 second response
- **Clear Feedback**: Always show what data is available/unavailable
- **Intuitive Flow**: Cell → Technique → Auto-configured exploration

### **Technical Performance**
- **Memory Efficient**: Single DataFrame load, efficient filtering
- **Responsive UI**: Immediate visual feedback on parameter changes
- **Robust**: Handle edge cases gracefully (no data, missing columns, etc.)

## Future Extension Points

### **Phase 2 Capabilities (Not Required Initially)**
- **Drill-Down**: Click on data points to investigate raw segment data
- **Export Options**: Save plots and filtered data
- **Custom Calculations**: User-defined metric calculations
- **Advanced Grouping**: Multi-level categorical grouping

### **Integration Opportunities**
- **Tab 3 Connection**: "Analyze this cell in detail" button → jump to single-cell Tab 3
- **Publication Mode**: Toggle to publication-ready plot styling
- **Saved Views**: Bookmark interesting filter/plot combinations