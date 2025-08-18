# Electrochemical Analysis Suite

## Project Overview

A modular, instrument-agnostic desktop application for R&D electrochemical data analysis that enables researchers to process, analyze, and compare experimental data from multiple potentiostat manufacturers.

## Primary Goal

Create a universal platform for electrochemical data analysis that:

1. **Universal Data Processing**: Import data from multiple potentiostat manufacturers (VersaStudio, BioLogic) into a standardized universal schema
2. **Segment-Based Analysis**: Automatically identify and analyze individual experimental segments (fundamental electrochemical techniques) with precise data boundaries  
3. **Flexible Grouping**: Create custom logical groupings of segments for comparative analysis across experiments and time
4. **Research Workflow**: Provide both GUI and programmatic access (CLI, Python scripts, Jupyter) for reproducible analysis

## Core Principles

- **Clean Architecture**: Modular, testable components with clear separation of concerns
- **Universal Schema**: All data converted to instrument-agnostic format for consistent analysis
- **Segment-Centric**: Each fundamental technique is an independent analytical unit with precise row boundaries
- **Multi-Interface**: GUI for exploration, CLI/scripts for automation and reproducibility

## Architecture Overview

### Backend (Clean & Minimal)
```
1. validate_files(paths) → format check only
2. get_parser(paths) → VersaStudioParser | BioLogicParser  
3. parser.parse_files(paths) → DataFile (universal schema)
4. store_data_file(DataFile, cell_name) → atomic DB + parquet commit
5. get_file_data(file_id) → load universal parquet
```

### Database Schema
```
Cells (id, name, metadata...)
├── Files (id, cell_id, raw_paths[], parquet_path, metadata...)
    ├── Experimental_Segments (id, file_id, fundamental_technique_id, 
                               start_row, end_row, start_elapsed_s, end_elapsed_s,
                               start_time, end_time, analytics_json)

Fundamental_Techniques (id, name, description)
VersaStudio_Technique_Map (action_id → fundamental_technique_id)
BioLogic_Technique_Map (technique_code → fundamental_technique_id)
```

### Data Flow
```
Raw Files → Parser → Universal DataFile → Parquet (universal schema)
                                       → DB (metadata + segments with row boundaries)
```

## Parsing Rules

### VersaStudio
- **.par file** → Metadata ONLY (experiment info, ActionID mappings, timestamps)
- **.par.csv file** → Data ONLY (calibrated measurements)
- **Schemas**: VERSASTUDIO_CSV_SCHEMA → UNIVERSAL_SCHEMA

### BioLogic (Future)
- **.mps/.mpt files** → Combined metadata + data
- **Schemas**: BIOLOGIC_SCHEMA → UNIVERSAL_SCHEMA

## Universal Schema

29-column standardized schema for all instruments:

```python
UNIVERSAL_SCHEMA = {
    # Core Time & Indexing (6 columns)
    'time_s': pl.Float64,              # Relative time from experiment start
    'timestamp': pl.Datetime,          # Absolute timestamp for traceability
    'segment_number': pl.Int64, 
    'point_number': pl.Int64, 
    'loop_number': pl.Int64, 
    'battery_cycle': pl.Int64,
    
    # Electrochemical Core (6 columns)
    'potential_v': pl.Float64, 
    'current_a': pl.Float64, 
    'potential_applied_v': pl.Float64, 
    'current_applied_a': pl.Float64,
    'potential_avg_v': pl.Float64, 
    'current_avg_a': pl.Float64,
    
    # Battery Analytics (4 columns)
    'charge_capacity_ah': pl.Float64, 
    'energy_wh': pl.Float64, 
    'power_w': pl.Float64, 
    'temperature_c': pl.Float64,
    
    # EIS (5 columns)
    'frequency_hz': pl.Float64, 
    'impedance_real_ohm': pl.Float64, 
    'impedance_imag_ohm': pl.Float64,
    'impedance_mag_ohm': pl.Float64, 
    'impedance_phase_deg': pl.Float64,
    
    # Status & Advanced (8 columns)
    'current_range': pl.Int64, 
    'potential_range': pl.Int64, 
    'mode': pl.Utf8, 
    'technique_id': pl.Int64, 
    'status_flags': pl.Int64,
    'ce_potential_v': pl.Float64, 
    'cell_potential_v': pl.Float64, 
    'ac_amplitude_v': pl.Float64, 
    'aux_voltage_v': pl.Float64
}
```

## UI Architecture

### Top Half (Cell Loading & File Processing)
```
Cell Tree → Upload Modal → Validation → Processing → Storage → On-demand Preview
```

### Future: Bottom Half (Analysis Interface)
```
Segments List | Group Management | Analysis Placeholder
```

## Success Metrics

- Parse and analyze data from 30-60 cells efficiently
- Support VersaStudio (.par/.csv) and BioLogic (.mps/.mpt) formats  
- Enable rapid segment grouping and comparative analysis
- Provide both interactive and programmatic interfaces
- Clean, testable, modular codebase

## Implementation Status

See `implementation_guide.md` and `project_status.md` for current progress and next steps.