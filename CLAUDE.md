# Battery Data Analyzer - Universal Electrochemical Data Processing

## Project Overview

A standardized system for parsing, analyzing, and storing electrochemical battery data from potentiostats. Designed for small-scale research (30-60 cells) with focus on experimental workflow efficiency and universal technique analysis.

## Final Goal

Create a web application where users can:
1. Upload cell information and data files (.par format initially)
2. Get automatic parsing, fundamental analytics, and technique segmentation
3. Create custom user groups for comparative analysis
4. Export results and visualizations

## Current Implementation Status

### ✅ Completed Foundation
- **VersaStudio Parser**: Robust .par file parsing with line-by-line metadata + Polars for data
- **DataFile/DataFileGroup**: Single file and fragmented file handling with continuous timestamps
- **24-column standardized schema**: Explicit types, handles GB-sized files efficiently
- **Parser factory**: Auto-detection framework ready for multi-instrument support
- **Basic error handling**: Graceful parsing failures with detailed error messages

### 🔧 Needs Refactoring
Current code has solid foundation but needs restructuring for:
- Universal schema (currently VersaStudio-specific)
- Analysis layer integration
- Better separation of concerns

## Implementation Plan

### Phase 1: Foundation Refactor (URGENT - Deadline Tomorrow)
1. **Universal Schema Design**: 29-column unified schema for VersaStudio + BioLogic
2. **File Upload & Storage**: Source-agnostic upload with cell-level raw storage
3. **Individual File Parsing**: Each file parsed independently → parquet + metadata JSON
4. **Duplicate Handling**: User choice to replace or keep duplicates with timestamp disambiguation
5. **Fundamental Analytics**: Auto-computed analysis stored per file

#### Universal 29-Column Schema
```python
UNIVERSAL_SCHEMA = [
    # Core Time & Indexing (6 columns)
    'time_s',              # Relative time from experiment start (seconds)
    'timestamp',           # Absolute timestamp (ISO format) for traceability
    'segment_number', 'point_number', 'loop_number', 'battery_cycle',
    
    # Electrochemical Core (6 columns)
    'potential_v', 'current_a', 'potential_applied_v', 'current_applied_a',
    'potential_avg_v', 'current_avg_a',
    
    # Battery Analytics (4 columns)
    'charge_capacity_ah', 'energy_wh', 'power_w', 'temperature_c',
    
    # EIS (5 columns)
    'frequency_hz', 'impedance_real_ohm', 'impedance_imag_ohm', 
    'impedance_mag_ohm', 'impedance_phase_deg',
    
    # Status & Advanced (8 columns)
    'current_range', 'potential_range', 'mode', 'technique_id', 'status_flags',
    'ce_potential_v', 'cell_potential_v', 'ac_amplitude_v', 'aux_voltage_v'
]
```

#### Benefits of Including Absolute Timestamps
1. **Data Exploration**: Correlate with external events (temperature, lab conditions)
2. **Multi-file Visualization**: Plot data from different files on same absolute timeline
3. **Traceability**: Essential audit trail for research documentation and reproducibility
4. **Gap Detection**: Easily identify interruptions in fragmented experiments
5. **Cross-experiment Analysis**: Compare experiments from different time periods

#### VersaStudio → Universal Mapping
```python
VERSASTUDIO_MAPPING = {
    # Time mappings
    'Elapsed Time(s)': 'time_s',
    'timestamp': 'timestamp',  # Computed from DateAcquired + TimeAcquired + elapsed time
    
    # Direct mappings
    'Segment #': 'segment_number',
    'Point #': 'point_number', 
    'E(V)': 'potential_v',
    'I(A)': 'current_a',
    'E Applied(V)': 'potential_applied_v',
    'Frequency(Hz)': 'frequency_hz',
    'Current Range': 'current_range',
    'Status': 'status_flags',
    'ActionId': 'technique_id',
    'AC Amplitude': 'ac_amplitude_v',
    'ADC Sync Input(V)': 'aux_voltage_v',
    
    # Impedance mappings (use Z over E for impedance)
    'Z Real': 'impedance_real_ohm',
    'Z Imag': 'impedance_imag_ohm',
    
    # Computed columns
    'power_w': lambda row: row['potential_v'] * row['current_a'],
    'impedance_mag_ohm': lambda row: (row['impedance_real_ohm']**2 + row['impedance_imag_ohm']**2)**0.5,
    'impedance_phase_deg': lambda row: np.degrees(np.arctan2(row['impedance_imag_ohm'], row['impedance_real_ohm'])),
    
    # NaN columns for VersaStudio (BioLogic-specific)
    'potential_avg_v': None,  # Not available in VersaStudio
    'current_avg_a': None,    # Not available in VersaStudio
    'ce_potential_v': None,   # No counter electrode in VersaStudio
    'cell_potential_v': None, # No cell potential measurement
}
```

#### BioLogic → Universal Mapping
```python
BIOLOGIC_MAPPING = {
    # Time mappings
    'time/s': 'time_s',
    'timestamp': 'timestamp',  # Computed from acquisition_start + elapsed time
    
    # Direct mappings
    'Ewe/V': 'potential_v',
    '<Ewe>/V': 'potential_avg_v',
    'Ece/V': 'ce_potential_v',
    'Ewe-Ece/V': 'cell_potential_v',
    'control/V': 'potential_applied_v',
    'P/W': 'power_w',
    'freq/Hz': 'frequency_hz',
    'Re(Z)/Ohm': 'impedance_real_ohm',
    '-Im(Z)/Ohm': 'impedance_imag_ohm',  # Note: BioLogic uses -Im
    '|Z|/Ohm': 'impedance_mag_ohm',
    'Phase(Z)/deg': 'impedance_phase_deg',
    'mode': 'mode',
    'cycle number': 'battery_cycle',  # Note: This is NOT true battery cycles!
    'loop number': 'segment_number',
    
    # Unit conversions
    'I/mA': ('current_a', lambda x: x / 1000),           # mA → A
    '<I>/mA': ('current_avg_a', lambda x: x / 1000),     # mA → A  
    'control/mA': ('current_applied_a', lambda x: x / 1000), # mA → A
    '(Q-Qo)/C': ('charge_capacity_ah', lambda x: x / 3600), # C → Ah
    '(Q-Qo)/mA.h': ('charge_capacity_ah', lambda x: x / 1000), # mAh → Ah
    
    # Computed impedance (fix sign convention)
    'impedance_imag_ohm': lambda row: -row['-Im(Z)/Ohm'],  # Fix BioLogic sign
}
```

#### Timestamp-Based Individual File Processing
```python
# Each file is parsed independently and stored separately
def parse_individual_file(file_path):
    """Parse single file with proper timestamps - NO merging at parse time"""
    
    # Extract start timestamp from file metadata
    start_timestamp = extract_file_timestamp(file_path)
    
    # Parse data with relative time
    data = parse_file_data(file_path)
    
    # Add absolute timestamps to each row
    data = data.with_columns([
        (pl.lit(start_timestamp) + 
         pl.duration(seconds=pl.col('time_s'))).alias('timestamp')
    ])
    
    # Store as individual parquet file
    output_path = f"processed/{cell_id}_{file_id}_processed.parquet"
    data.write_parquet(output_path)
    
    # Store metadata separately
    metadata = {
        "file_metadata": {
            "original_file": file_path.name,
            "start_timestamp": start_timestamp.isoformat(),
            "file_hash": calculate_hash(file_path),
            "parser_version": "2.0.0"
        },
        "analysis_results": {...}  # Fundamental analytics
    }
    
    return DataFile(data, metadata)

# File merging ONLY happens during user grouping or analysis
def merge_files_for_user_group(file_list):
    """Merge multiple DataFiles when user creates groups - NOT during parsing"""
    
    # Sort files by timestamp
    sorted_files = sorted(file_list, key=lambda f: f.start_timestamp)
    
    combined_data = []
    cumulative_time = 0.0
    
    for data_file in sorted_files:
        df = data_file.data.clone()
        
        # Adjust time_s for continuity across files
        if cumulative_time > 0:
            df = df.with_columns([
                (pl.col('time_s') + cumulative_time).alias('time_s')
            ])
        
        # Keep original absolute timestamps unchanged
        combined_data.append(df)
        cumulative_time = df.get_column('time_s').max()
    
    return pl.concat(combined_data, how="vertical_relaxed")
```

#### File Upload & Storage Strategy
```python
def upload_file(source_file_path, cell_id):
    """Upload file from any location and store in cell's raw directory"""
    
    cell_raw_dir = f"data/cells/{cell_id}/raw/"
    target_filename = source_file_path.name  # e.g., "formation_cycle1.par"
    target_path = cell_raw_dir / target_filename
    
    if target_path.exists():
        # User choice for duplicate handling
        user_choice = prompt_user(
            f"File '{target_filename}' already exists. What do you want to do?",
            options=[
                "Replace existing file (overwrites analysis)",
                "Keep both (timestamp added to new file)", 
                "Skip this upload"
            ]
        )
        
        if user_choice == "replace":
            copy_file(source_file_path, target_path)
            return process_file(target_path, cell_id, replace_existing=True)
            
        elif user_choice == "keep_both":
            # Add timestamp: formation_cycle1_20250815_143022.par
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{target_path.stem}_{timestamp}{target_path.suffix}"
            new_path = cell_raw_dir / new_filename
            
            copy_file(source_file_path, new_path)
            return process_file(new_path, cell_id, replace_existing=False)
            
        else:  # skip
            return "upload_skipped"
    else:
        # New file - copy and process
        copy_file(source_file_path, target_path)
        return process_file(target_path, cell_id, replace_existing=False)

def process_file(raw_file_path, cell_id, replace_existing=False):
    """Process file stored in cell's raw directory"""
    
    # Generate file_id from stored filename
    file_id = f"{cell_id}_{raw_file_path.stem}"
    
    # Parse and analyze
    data_file = parse_file(raw_file_path)  # Universal 29-column output
    
    # Store processed data
    processed_path = f"data/cells/{cell_id}/processed/{file_id}.parquet"
    analysis_path = f"data/cells/{cell_id}/analysis_results/{file_id}.json"
    
    data_file.data.write_parquet(processed_path)
    save_analysis_results(analysis_path, data_file.analysis)
    
    if replace_existing:
        update_affected_user_groups(file_id)  # Refresh groups referencing this file
    
    return file_id
```

#### Data Storage Structure (Source-Agnostic)
```
data/cells/CELL_001/
├── raw/                                    # Centralized raw storage
│   ├── formation_cycle1.par               # Original upload
│   ├── formation_cycle1_20250815_143022.par  # Duplicate with timestamp  
│   ├── gitt_measurement.par
│   └── aging_test.par
├── processed/                              # Parsed parquet files
│   ├── CELL_001_formation_cycle1.parquet  # From original
│   ├── CELL_001_formation_cycle1_20250815_143022.parquet  # From duplicate
│   ├── CELL_001_gitt_measurement.parquet
│   └── CELL_001_aging_test.parquet
├── analysis_results/                       # Analysis JSON files
│   ├── CELL_001_formation_cycle1.json
│   ├── CELL_001_formation_cycle1_20250815_143022.json
│   └── CELL_001_gitt_measurement.json
├── user_groups/                           # User-defined groupings
│   ├── formation_complete.json           # May reference multiple files
│   └── aging_rests.json
└── metadata.json                         # Cell-level metadata
```

### Phase 2: Fundamental Analytics Engine
Implement automatic analysis for every data file upon parsing:

#### Core Analytics (Auto-computed)
1. **CC Analysis**: 
   - Capacity calculation (Ah, mAh)
   - Energy calculation (Wh)
   - Efficiency tracking
   - Average voltage/current

2. **Pulse Analysis** (max 1 minute duration):
   - Resistance calculation (ΔV/ΔI)
   - Voltage drop measurement
   - Pulse duration tracking
   - Current uniformity assessment

3. **Rest Phase Analysis** (Universal curve fitting):
   ```python
   "exponential_fit": {
       "V_eq": 3.819,      # Equilibrium voltage
       "V_drop": 0.069,    # Initial voltage drop  
       "tau": 45.2,        # Time constant
       "r_squared": 0.94,  # Goodness of fit
       "fitting_type": "single_exponential",
       "fit_error_rmse": 0.002
   }
   ```

4. **CV Analysis**:
   - Peak detection (anodic/cathodic)
   - Scan rate effects
   - Capacitance calculation
   - Reversibility assessment

5. **EIS Analysis** (Basic only):
   - Nyquist plot generation
   - Bode plot generation
   - Data quality metrics
   - Export to external tools (Relaxis integration)

#### Storage Architecture
```python
# File-level metadata with fast access indices
{
    "file_metadata": {
        "original_file": "GITT_charge_cycle1.par",
        "file_hash": "sha256:abc123...",
        "parser_version": "2.0.0",
        "cell_id": "CELL_001"  # User-editable
    },
    
    "data_indices": {
        "action_boundaries": {
            "action_1": {"start_row": 0, "end_row": 1250},
            "action_5": {"start_row": 5671, "end_row": 948974}
        },
        "technique_index": {
            "pulse_phases": [1, 3, 5, 7],
            "rest_phases": [2, 4, 6, 8],
            "eis_phases": [15, 16, 17]
        }
    },
    
    "analysis_results": {
        "action_5_pulse": {
            "resistance": 0.05,
            "voltage_drop": 0.025,
            "fit_quality": 0.98
        },
        "action_6_rest": {
            "exponential_fit": {...},
            "fitted_curve": [...],     # For visualization
            "residuals": [...],        # Fit quality
            "time_points": [...]       # X-axis data
        }
    }
}
```

### Phase 3: Cell-Level User Grouping System
Enable technique-level grouping within each cell, with cross-cell comparison capabilities:

#### Per-Cell Grouping
```python
# CELL_001/user_groups/aging_rests.json
{
    "group_name": "aging_rests",
    "cell_id": "CELL_001", 
    "description": "Rest phases for aging analysis",
    "segments": [
        "cell001_file01_action05_rest",
        "cell001_file02_action08_rest", 
        "cell001_file03_action11_rest"
    ],
    "group_analytics": {
        "avg_time_constant": 45.2,
        "time_constant_trend": "increasing",
        "fit_quality_avg": 0.94
    }
}
```

#### Cross-Cell Comparison Interface
```python
# Compare same group across cells
compare_groups(
    cells=["CELL_001", "CELL_002", "CELL_003"],
    group_name="aging_rests",
    metric="time_constant"
)

# Compare specific actions across cells  
compare_actions(
    cells=["CELL_001", "CELL_002"],
    action_pattern="action_05_rest",
    analysis_type="exponential_fit"
)

# Compare cells for same technique
compare_technique(
    cells=["CELL_001", "CELL_002"], 
    technique="rest",
    conditions={"duration": ">300", "fit_quality": ">0.9"}
)
```

#### CLI Examples
```bash
# Create group within a cell
battery-analyzer group create CELL_001 "formation_rests" \
  --technique rest \
  --file-pattern "formation*" \
  --min-duration 300

# Compare same group across cells
battery-analyzer compare group "aging_rests" \
  --cells CELL_001,CELL_002,CELL_003 \
  --metric time_constant \
  --plot

# Compare specific action across cells
battery-analyzer compare action "action_05_rest" \
  --cells CELL_001,CELL_002 \
  --output comparison_report.json
```

### Phase 4: Web Application
1. **File Upload Interface**: 
   - Drag-and-drop multiple .par files
   - Cell information input (ID, chemistry, capacity, notes)
   - Automatic parsing and analysis

2. **Analysis Dashboard**:
   - Real-time processing status
   - Technique detection and segmentation display
   - Automatic fundamental analysis results

3. **Grouping Interface**:
   - Visual technique timeline for each cell
   - Interactive grouping tools
   - Group analytics and comparison views

4. **Export System**:
   - Analysis results (JSON, CSV)
   - Visualization plots (PNG, SVG)
   - Research reports (PDF)

## Key Design Principles

### Universal Analysis
- **Technique-agnostic**: Same analysis applies regardless of underlying experiment type
- **Instrument-independent**: Works with any potentiostat (VersaStudio, BioLogic, future)
- **Automatic processing**: Parse → analyze → store in one step

### Flat Segmentation Structure
- **No rigid hierarchy**: Users can group by any metadata combination
- **Rich metadata**: Every segment carries full experimental context
- **Flexible querying**: Database-like operations for complex analysis

### Research Workflow Focused
- **Cell-centric organization**: Matches 30-60 cell research scale
- **Fragmented file handling**: Solves interrupted experiment problem
- **Editable metadata**: Easy corrections without data reprocessing

## Technical Requirements

### Dependencies
- **Core**: Python 3.9+, Polars, NumPy, SciPy
- **Analysis**: scikit-learn (curve fitting), matplotlib/plotly (visualization)
- **Storage**: JSON (metadata), Parquet (data), SQLite (optional indexing)
- **Web**: FastAPI, React/Vue.js, file upload handling
- **External**: galvani (BioLogic parsing when added)

### Performance Targets
- **Large files**: Handle 1GB+ .par files efficiently
- **Response time**: <2 seconds for analysis of typical files
- **Concurrent processing**: Multiple file uploads with progress tracking
- **Memory efficiency**: Stream processing for large datasets

### Data Organization
```
data/
├── cells/
│   ├── CELL_001/
│   │   ├── raw/                   # Original .par files
│   │   ├── processed/             # Parsed parquet files  
│   │   ├── analysis_results/      # Analysis JSON files
│   │   ├── user_groups/           # Cell-specific user groupings
│   │   │   ├── aging_rests.json
│   │   │   ├── formation_cycles.json
│   │   │   └── high_quality_fits.json
│   │   └── metadata.json          # Cell-specific metadata
│   ├── CELL_002/
│   │   ├── raw/
│   │   ├── processed/
│   │   ├── analysis_results/
│   │   ├── user_groups/           # Independent groupings per cell
│   │   │   ├── aging_rests.json   # Same name, different cell data
│   │   │   └── temperature_study.json
│   │   └── metadata.json
└── cell_registry.json             # Master cell list
```

## Success Metrics

1. **Parsing reliability**: >99% success rate on real experimental files
2. **Analysis accuracy**: Curve fitting R² > 0.9 for quality rest phases
3. **User efficiency**: Reduce analysis time from hours to minutes
4. **Workflow integration**: Seamless file upload → results workflow
5. **Research utility**: Enable new insights through flexible grouping

## Next Steps (Immediate)

1. **Refactor current VersaStudio parser** to output universal 28-column schema
2. **Implement fundamental analysis engine** with curve fitting for rest phases
3. **Create storage system** with metadata + indices + analysis results
4. **Build basic CLI** for testing and validation
5. **Design web interface mockups** for user testing

## Future Extensions

- **BioLogic support**: Add galvani-based parser
- **Advanced analytics**: Machine learning for pattern recognition  
- **Database backend**: PostgreSQL for large-scale data management
- **API integration**: Connect with laboratory information systems
- **Collaborative features**: Share groups and analyses between researchers