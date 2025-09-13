# Development Roadmap - Future Session Priorities

**Document Status**: Development Planning  
**Created**: September 3, 2025  
**Session Context**: Post-BioLogic parser integration and Explorer modal fixes

## Overview

Three key development areas identified for future sessions, representing expansion from current working baseline to comprehensive multi-instrument analysis platform with enhanced data access patterns.

## Current Status Baseline

### ✅ **Completed Foundation**
- **VersaStudio Parser**: Complete (.par + .par.csv) with 29-column universal schema
- **BioLogic Parser**: Working MPR parsing with 8 core columns mapped
- **Explorer Tab**: Working Perspective modal with segment inspection
- **Registry System**: Auto-discovery analysis framework
- **Backend API**: Polars-based data processing with Arrow serialization
- **Multi-Interface**: Panel web app, CLI, Python API working

## Priority 1: Enhanced BioLogic Parser Integration

### **Current State**
- **✅ Working**: Basic MPR parsing with YADG binary reader
- **✅ Integrated**: 8 core columns mapped to universal schema  
- **❌ Limited**: Only ~3% of available BioLogic data utilized
- **❌ Schema Gaps**: Universal schema missing advanced electrochemical columns

### **Development Tasks**

#### **1.1 Universal Schema Extension**
**Problem**: Current 29-column schema insufficient for advanced electrochemical measurements

**Required New Columns**:
```python
# Three-electrode systems
'counter_electrode_potential_v'     # Ece measurements
'reference_electrode_potential_v'   # Reference electrode data
'auxiliary_electrode_potential_v'   # Auxiliary electrode

# Advanced EIS parameters  
'impedance_phase_deg'              # Phase angle measurements
'impedance_real_ohm'               # Real impedance component
'impedance_imaginary_ohm'          # Imaginary impedance component
'frequency_hz'                     # EIS frequency sweeps

# Technique-specific measurements
'analog_input_1_v'                 # External sensor inputs
'analog_input_2_v'                 # Secondary measurements  
'control_voltage_v'                # Applied control signals
'step_time_s'                      # Technique step timing

# Advanced cycling parameters
'half_cycle_number'                # Half-cycle counting
'z_cycle_number'                   # Z-cycle measurements
'dq_dt_ma_h'                       # Capacity derivative
'power_w'                          # Power calculations (if not present)
```

**Implementation Strategy**:
1. **Audit Current Schema**: Review universal schema completeness
2. **BioLogic Column Analysis**: Map 247 YADG columns to missing schema columns
3. **Schema Migration**: Add new columns with proper Polars dtypes
4. **Backward Compatibility**: Ensure existing VersaStudio data still works
5. **Database Migration**: Update database schema and existing data

#### **1.2 Complete Column Mapping**
**Current**: 8/247 columns mapped (~3% utilization)  
**Target**: 50+ core columns mapped (~20% utilization covering 90% of use cases)

**Priority Column Categories**:
```python
# Impedance measurements (EIS techniques)
impedance_columns = [
    "Re(Z)/Ohm", "Im(Z)/Ohm", "|Z|/Ohm", 
    "Phase(Z)/deg", "freq/Hz"
]

# Multi-electrode measurements  
electrode_columns = [
    "Ece/V", "ref1/V", "ref2/V",
    "Analog IN 1/V", "Analog IN 2/V"  
]

# Advanced technique parameters
technique_columns = [
    "control/V", "step time/s", "dQ/mA.h",
    "half cycle", "z cycle", "Energy charge/W.h"
]

# Environmental monitoring
environment_columns = [
    "Temperature/°C", "Pressure/bar",
    "External sensor 1", "External sensor 2"
]
```

#### **1.3 YADG Techniques Integration - CRITICAL**
**Missing Functionality**: Only using YADG column definitions, ignoring comprehensive technique system

**YADG techniques.py Features to Integrate**:
- **17 Technique Definitions**: CA, CP, CV, CVA, GCPL, GEIS, LSV, MB, OCV, PEIS, WAIT, ZIR, MP, CoV, CoC, BCD, LOOP
- **Parameter Extraction**: `technique_params_dtypes` for parsing technique-specific parameters
- **Unit Conversion**: `param_from_key()`, `unit_map` for proper unit handling
- **Current Range Mapping**: 180+ current range definitions
- **Resolution Calculations**: `get_devs()` for measurement accuracy
- **Data Processing**: `split_control()` for technique-specific data handling

**Integration Steps**:
1. **Download Full YADG**: Get complete `yadg/extractors/eclab/` module
2. **Functionality Audit**: Compare current vs full YADG implementation
3. **Selective Integration**: Identify critical missing functionality
4. **Enhanced Metadata**: Extract technique parameters and experimental conditions
5. **Professional Documentation**: Research-grade experimental metadata

#### **1.4 File Format Extension**
**Current**: `.mpr` files only  
**Target**: Complete BioLogic ecosystem support

**Additional Formats**:
- **`.mps` files**: Settings/method files (framework exists)
- **`.mpt` files**: Text export files (framework exists)  
- **Multi-file experiments**: Linked MPR+MPS combinations

---

## Priority 2: Jupyter Notebook Interface Development

### **Current State**
- **✅ Existing**: Basic Jupyter example (`examples/jupyter_example.ipynb`)
- **❌ Limited**: Simple API calls only, no UI functionality replication
- **❌ Manual**: Requires extensive coding for basic operations

### **Development Vision**
**Goal**: Non-interactive Jupyter interface that mimics web UI functionality through simple Python module

**Target User Experience**:
```python
# Simple module approach - no complex coding required
from electrochemical_jupyter import EChemNotebook

# Initialize notebook interface
notebook = EChemNotebook()

# Replicate Cell Management functionality  
notebook.create_cell("TEST_CELL", chemistry="Li_ion")
notebook.add_files("experiment.par", "experiment.par.csv", cell="TEST_CELL")
notebook.list_cells()  # DataFrame display

# Replicate Group Management functionality
notebook.create_group("TEST_CELL", "Rest_Phases") 
notebook.add_segments_to_group("Rest_Phases", ["seg_001", "seg_003"])
notebook.show_groups("TEST_CELL")  # Visual group summary

# Replicate Explorer functionality  
notebook.plot_analysis("TEST_CELL", analysis="resistance_analysis")
notebook.show_segment_inspector("seg_001")  # Perspective in notebook cell

# Replicate Data Analysis functionality
notebook.run_comprehensive_analytics(["TEST_CELL"])
notebook.export_research_dataset(["TEST_CELL"], format="csv")
```

### **Implementation Architecture**

#### **2.1 Core Module Structure**
```python
electrochemical_jupyter/
├── __init__.py                    # Main EChemNotebook class
├── cell_management.py             # Cell creation, file management
├── group_management.py            # Group operations, templated groups  
├── analysis_runner.py             # Registry-driven analysis execution
├── plotting.py                    # Matplotlib/Plotly visualization  
├── data_export.py                 # Export utilities for research
└── display_helpers.py             # Rich display formatting
```

#### **2.2 Backend Integration Strategy**
**Approach**: Thin wrapper over existing backend API with enhanced display

```python
# Leverage existing backend infrastructure
from src_clean.backend import get_backend_api

class EChemNotebook:
    def __init__(self):
        self.api = get_backend_api()  # Reuse existing API
        self.display = NotebookDisplay()  # Enhanced formatting
    
    def create_cell(self, name, **kwargs):
        result = self.api.create_cell(name, **kwargs)
        return self.display.format_cell_result(result)  # Rich display
```

#### **2.3 Display Enhancement Features**
- **Rich DataFrames**: Styled pandas/polars display with scientific formatting
- **Interactive Plots**: Plotly/matplotlib plots with hover information
- **Progress Indicators**: Processing status for long operations
- **Error Handling**: User-friendly error messages with suggestions
- **Export Integration**: One-click export to various formats

#### **2.4 Advanced Features**
```python
# Registry system integration
notebook.list_available_analyses()  # Show all registry analyses
notebook.get_analysis_help("resistance_analysis")  # Documentation

# Batch operations
notebook.batch_process_files(file_pairs, cell_mapping)
notebook.batch_create_groups(group_definitions)

# Research workflow
notebook.create_research_notebook("Li_aging_study")  # Template generation
notebook.auto_document_experiment(cells=["CELL1", "CELL2"])  # Auto-documentation
```

---

## Priority 3: Enhanced Jupyter Notebook Data Functionality  

### **Current State**
- **❌ Basic**: Minimal data access patterns in existing notebook
- **❌ Manual**: Requires low-level API knowledge
- **❌ Limited**: No advanced data manipulation utilities

### **Development Vision**
**Goal**: Comprehensive data functionality for research workflows in Jupyter environment

### **Data Access Enhancement**

#### **3.1 Advanced Data Querying**
```python
# High-level data access patterns
data = notebook.get_research_data(
    cells=["CELL1", "CELL2"],
    techniques=["Rest", "GCPL"],
    temperature_range=(20, 30),
    time_range=("2025-01-01", "2025-03-01")
)

# Segment-level analysis
segments = notebook.query_segments(
    capacity_range=(0.1, 2.0),  # Ah
    voltage_range=(3.0, 4.2),   # V
    technique="Rest"
)

# Cross-cell comparisons
comparison = notebook.compare_cells(
    cells=["CELL1", "CELL2"], 
    metrics=["capacity_fade", "resistance_growth"]
)
```

#### **3.2 Advanced Analytics Integration**
```python
# Registry-driven analytics in notebook
results = notebook.run_analytics(
    segments=["seg_001", "seg_002"],
    analyses=["kinetics", "resistance", "equilibrium"]
)

# Custom analysis workflows
workflow = notebook.create_analysis_workflow([
    ("load_data", {"cells": ["CELL1"]}),
    ("filter_rest_segments", {}),
    ("extract_time_constants", {}), 
    ("statistical_analysis", {}),
    ("export_results", {"format": "xlsx"})
])
```

#### **3.3 Data Visualization Enhancement**
```python
# Advanced plotting capabilities
notebook.plot_aging_analysis(
    cells=["CELL1", "CELL2"],
    plot_type="capacity_fade",
    interactive=True
)

# Multi-axis comparative plots
notebook.plot_multi_cell_comparison(
    cells=["CELL1", "CELL2", "CELL3"],
    y_axes=["capacity_ah", "resistance_ohm"],
    x_axis="cycle_number"
)

# Perspective integration in notebook
notebook.inspect_segment_data(
    segment_id="seg_001",
    display_mode="inline"  # Embedded Perspective widget
)
```

#### **3.4 Research Data Export**
```python
# Publication-ready exports
notebook.export_publication_data(
    cells=["CELL1", "CELL2"],
    format="nature_energy",  # Journal-specific formatting
    include_metadata=True
)

# Statistical analysis exports  
notebook.export_statistical_summary(
    analysis="aging_study",
    format="xlsx",
    include_plots=True
)

# Raw data exports with metadata
notebook.export_research_dataset(
    cells=["CELL1", "CELL2"],
    include_analytics=True,
    format="hdf5"  # For large datasets
)
```

### **Implementation Strategy**

#### **3.1 Data Layer Enhancement**
- **Caching System**: Intelligent data caching for repeated analysis
- **Lazy Loading**: On-demand data loading for large datasets
- **Memory Management**: Efficient handling of multi-cell datasets
- **Progress Tracking**: Visual progress bars for long operations

#### **3.2 Integration Points**
- **Backend API**: Leverage existing lazy data service
- **Registry System**: Full integration with analysis registry
- **Export System**: Enhanced export capabilities
- **Plotting System**: Rich visualization with publication quality

#### **3.3 User Experience Focus**
- **Documentation**: Comprehensive examples and tutorials
- **Error Handling**: Helpful error messages and recovery suggestions
- **Performance**: Fast response for interactive data exploration
- **Flexibility**: Both simple and advanced usage patterns

---

## Development Workflow

### **Recommended Session Approach**
1. **Understand**: Review current state and user requirements
2. **Plan**: Design implementation approach with clear milestones  
3. **Code/Document**: Implement with comprehensive documentation
4. **Test**: Validate with real data and user workflows
5. **Iterate**: Refine based on testing results

### **Success Metrics**
- **BioLogic Parser**: >50 columns mapped, technique metadata extraction
- **Jupyter Interface**: UI functionality replicated with simple API
- **Data Functionality**: Research workflows achievable in <10 lines of code

### **Documentation Standards**
- **Technical Implementation**: Complete code documentation
- **User Guide**: Usage examples and workflows
- **Integration Guide**: How components work together
- **Migration Guide**: Upgrading existing notebooks/workflows

---

## Current Session Issues (September 12, 2025)

### **🚨 BioLogic current_a Mapping Bug (UNFIXED)**

**Issue**: Universal schema mapping prioritizes `control_I` over `I` for `current_a` column, causing Rest phases to show `nan` instead of actual measured current values.

**Root Cause**: In `src_clean/parsers/biologic.py:190-201`, the logic uses:
```python
if "control_I" in df.columns:
    # Use control_I (preferred) - THIS IS THE PROBLEM
elif "I" in df.columns:
    # Use I as fallback
```

**Problem**: For Rest phases (mode 3), `control_I` is correctly `nan` (no control active), but the measured current is in column `I` (0.000000 for Rest). The current logic discards the actual measured current.

**Investigation Files**:
- `debug_simple_current.py` - Shows raw `I` vs universal `current_a` mismatch
- `debug_current_columns.py` - Complete current column analysis  
- `debug_raw_flags.py` - BioLogic flag pattern investigation
- `debug_flag_patterns.py` - Flag correlation with physical reality

**Required Fix**: Modify mapping logic to handle Rest phases correctly - use measured current (`I`) when control current (`control_I`) is `nan`.

**Status**: Investigation complete, fix implementation pending.

---

## Conclusion

These three priorities represent the evolution from current working baseline to a comprehensive, research-grade electrochemical analysis platform with multiple access patterns (web UI, Jupyter, CLI) and multi-instrument support (VersaStudio + BioLogic).

**Key Benefits After Implementation**:
- **Universal Instrument Support**: Complete BioLogic + VersaStudio capability
- **Flexible Analysis Environment**: Web UI + Jupyter + CLI access patterns  
- **Research-Grade Functionality**: Publication-ready data analysis and export
- **Developer-Friendly**: Simple APIs for complex electrochemical analysis

**Each priority builds on current foundation while expanding platform capabilities significantly.**