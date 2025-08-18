# Battery Data Analyzer - Active Development Guide

## Current Status

**✅ COMPLETED**: Core backend architecture with universal schema, SQLite storage, and fundamental analytics.

**⚠️ ARCHITECTURAL PIVOT**: Moving from Panel UI to native Qt application due to Panel reliability issues (websocket disconnections, FileInput widget crashes).

**🎯 CURRENT FOCUS**: Qt desktop application with single-cell workflow - file upload, data visualization, grouping, and analysis.

### Key Architecture Features Implemented

#### ✅ Dual File System Architecture
- **`.par` files**: Raw VersaStudio technique structure and ActionId mapping  
- **`.par.csv` files**: Calibrated export data from VersaStudio (EIS calibrated, processed measurements)
- **Automatic validation**: Ensures matching file pairs exist before processing
- **Local file processing**: No web upload limits, handles GB-sized files efficiently
- **Tab 1 integration**: Complete file browser with dual file selection and validation

#### 🔄 UI Architecture Transition
- **Previous**: Panel web UI (deprecated due to reliability issues)
- **Current**: Qt desktop application development
- **Backend**: Preserved - all core functionality works via BackendAPI
- **Benefits**: Native performance, reliable file handling, proper event system

## Active Work Instructions

### Universal Schema Reference (UPDATED - Management/Analytics Focus)

**21-Column Universal Schema** (Refined for essential measurements):
```python
UNIVERSAL_COLUMNS = [
    # Core Time & Indexing (4 columns)
    'time_s', 'timestamp', 'segment_number', 'point_number',
    
    # Electrochemical Core (6 columns)  
    'potential_v', 'current_a', 'potential_applied_v', 'potential_avg_v', 'current_avg_a',
    'ce_re_potential_v',
    
    # EIS Measurements (4 columns)
    'frequency_hz', 'impedance_real_ohm', 'impedance_imag_ohm', 'impedance_phase_deg',
    
    # Calculated Analytics (3 columns)
    'power_w', 'charge_capacity_ah', 'energy_wh',
    
    # Environmental (1 column)
    'temperature_c',
    
    # Experimental Context (3 columns)
    'technique_id', 'technique_name', 'fundamental_technique'
]
```

### VersaStudio .par.csv Calibrated Data Mapping
```python
VERSASTUDIO_CSV_MAPPING = {
    # Core measurements from .par.csv export
    'Potential (V)': 'potential_v',
    'Current (A)': 'current_a', 
    'Applied Potential (V)': 'potential_applied_v',
    'Elapsed Time (s)': 'time_s',
    
    # EIS measurements from .par.csv export
    'Frequency (Hz)': 'frequency_hz',
    'Zre (ohms)': 'impedance_real_ohm',
    'Zim (ohms)': 'impedance_imag_ohm',
    'Phase of Z (deg)': 'impedance_phase_deg',
    
    # Multi-electrode measurements
    'CE-RE Potential (V)': 'ce_re_potential_v',
    
    # Experimental context
    'ActionID': 'technique_id',
    'Segment': 'segment_number',
    'Point': 'point_number',
}
```

### Technique Mapping (Expand as Needed)
```python
TECHNIQUE_MAPPING = {
    'OCV': ['Rest', 'Energy Open Circuit', 'Impedance Open Circuit', 'OCV', 
            'Corrosion Open Circuit', 'Voltametry Open Circuit'],
    'CC': ['Constant Current', 'CC', 'Voltametry ChronoPotentiometry', 
           'ChronoPotentiometry'],
    'CV': ['Constant Voltage', 'CV', 'Voltametry ChronoAmperometry', 
           'ChronoAmperometry'],
    'GEIS': ['Galvanostatic EIS', 'GEIS'],
    'PEIS': ['Potentiostatic EIS', 'PEIS']
}
```

**Important**: Always classify unknown techniques as 'UNKNOWN' and expand mapping as new technique names are encountered.

## Key Features Implemented

### 1. Refined Universal Schema (21 Columns)
**Status**: ✅ COMPLETED  
**Focus**: Management and analytics rather than instrumentation debugging

**Key Changes**:
- Reduced from 32 to 21 focused columns
- Removed instrumentation-specific debugging columns
- Kept essential measurements and analytics
- Added BioLogic compatibility with `potential_avg_v` and `current_avg_v`

### 2. Temperature as File-Level Metadata
**Status**: ✅ COMPLETED  
**Implementation**: Database schema and UI integration

**Features**:
- Temperature stored in `files` table as `temperature_c` column
- Inherits to `technique_segments` table for future analytics
- Optional UI input during file upload
- Database migration support for existing installations

### 3. Applied Potential Configuration
**Status**: ✅ COMPLETED  
**Default**: 2-electrode WE-CE voltage (standard battery measurement)

**UI Options**:
- 2-electrode WE-CE voltage (default)
- 3-electrode WE-RE voltage  
- 3-electrode CE-RE voltage
- Custom configuration
- Stored as file-level metadata for user interpretation

### 4. VersaStudio .par.csv Calibrated Data Support  
**Status**: ✅ COMPLETED  
**Critical**: Uses calibrated EIS data from manual VersaStudio CSV exports

**Workflow**:
- Dual file processing: .par (technique mapping) + .par.csv (calibrated data)
- Column mapping for exact VersaStudio CSV export format
- Data quality assured through VersaStudio calibration
- Technique sequence preserved from .par file structure

## Immediate Development Priorities

### 1. Qt Desktop Application Development
**Status**: In Progress  
**Priority**: High

**Qt Application Roadmap**:
- **Phase 1**: Core window structure with single-cell workflow
- **Phase 2**: File upload system with native dialogs and drag & drop
- **Phase 3**: Data visualization using pyqtgraph
- **Phase 4**: Group management and analysis integration
- **Architecture**: PySide6 + pyqtgraph + existing BackendAPI

**Directory Structure**: `src/qt_app/` (separate from Panel attempts)

### 2. Extended Technique Classification
**Status**: Ready to Expand  
**Priority**: Medium

Expand technique mapping based on real data:
- Analyze technique names from user files
- Add variants to TECHNIQUE_MAPPING
- Improve classification accuracy
- Handle edge cases and compound techniques

## Application Usage Instructions

### Qt Desktop Application (CURRENT)
```bash
# Start Qt application
python src/qt_app/main.py

# With custom data directory
python src/qt_app/main.py --data-dir /path/to/data
```

### Alternative Access Methods
```bash
# Command line interface
python cli_tools/battery_cli.py list-cells
python cli_tools/battery_cli.py upload 0 file1.par file2.par.csv

# Jupyter notebook (planned)
jupyter lab notebooks/battery_analysis.ipynb
```

## Architecture Transition Notes

### Why Qt Instead of Panel?
**Panel Issues Encountered**:
- FileInput widget crashes causing websocket disconnections
- Unreliable event handling (param watchers failing)
- Browser compatibility issues with file uploads
- Performance problems with large datasets
- Debugging difficulties in web environment

**Qt Advantages**:
- Native desktop performance and reliability
- Proven file handling with drag & drop
- pyqtgraph for high-performance plotting
- Professional native UI/UX
- Better development/debugging experience

### Preserved Backend Architecture
**All core functionality retained**:
- ✅ BackendAPI: Common interface for all UI types
- ✅ Universal schema and parsers
- ✅ SQLite database with technique analytics
- ✅ Fundamental analysis algorithms
- ✅ File processing pipeline

**Multiple Access Patterns**:
- **Qt Desktop**: Primary user interface
- **CLI**: Scripting and automation
- **Jupyter**: Interactive analysis and research
- **API**: Future web integration

### 2-Tab UI Workflow (UPDATED)
1. **Tab 1: Cell & File Management**: 
   - Create battery cells with metadata (name, chemistry, capacity, notes)
   - Single active cell selection (cell row selection fixes applied)
   - **Local File Browser**: Navigate filesystem from `/Users/srinathchakravarthy/` (default)
   - **Dual File Selection**: Select .par and .par.csv file pairs for calibrated data processing
   - **File Validation**: Automatic validation of dual file pairs with detailed status
   - **Local File Association**: Process files directly from local paths (no web upload limits)
   - Set temperature metadata and applied potential interpretation per file
   - Responsive table sizing and proper error handling

2. **Tab 2: Cell Data Processing**: 
   - Technique-centric workflow: Files → Techniques → Groups → Manual Plotting
   - Select files from active cell and view technique segments
   - Create user groups for comparative analysis (OCV, Rate, EIS, GITT, Cycle, Custom)
   - Manual plotting system with 8 templated plot types
   - Group analytics with specialized analysis per group type

### Dual File Processing Workflow (NEW)

#### File Browser & Selection
- **Local filesystem navigation**: Start from `/Users/srinathchakravarthy/` (configurable)
- **File type filtering**: Shows only .par and .par.csv files
- **Directory navigation**: Home, Up, and direct path input
- **Multi-file selection**: Select multiple files with validation

#### Dual File Validation  
```python
# Example validation results
{
    'dual_pairs': [
        {
            'par_file': '/path/to/data.par',
            'csv_file': '/path/to/data.par.csv', 
            'valid': True,
            'recommended': True  # Calibrated data processing
        }
    ],
    'individual_files': [...],  # Single files without pairs
    'has_valid_files': True,
    'has_dual_pairs': True
}
```

#### File Association Process
1. **Select active cell** from cell management table
2. **Browse local filesystem** using integrated file browser  
3. **Select .par + .par.csv pairs** (or individual files)
4. **Validate file compatibility** with detailed status feedback
5. **Configure metadata**: Temperature (°C) and applied potential interpretation
6. **Associate files** with active cell using local file processing (no upload)

#### Key Benefits
- **No file size limits**: Process GB-sized files directly from local storage
- **Calibrated data support**: Dual file processing ensures VersaStudio calibration integrity  
- **Efficient workflow**: Single tab for cell + file management
- **Error resilience**: Comprehensive validation before processing

### Database Features
- **SQLite Backend**: Centralized metadata storage
- **File Tracking**: Processing status and error handling  
- **Cell Organization**: Move files between cells atomically
- **Migration Support**: Automatic schema updates

### 3. BioLogic Parser Implementation  
**Status**: Design Phase  
**Priority**: Medium

**BioLogic → Universal Mapping** (Design):
```python
BIOLOGIC_MAPPING = {
    # Time mappings
    'time/s': 'time_s',
    
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
    
    # Unit conversions
    'I/mA': ('current_a', lambda x: x / 1000),           # mA → A
    '<I>/mA': ('current_avg_a', lambda x: x / 1000),     # mA → A  
    'control/mA': ('current_applied_a', lambda x: x / 1000), # mA → A
    '(Q-Qo)/C': ('charge_capacity_ah', lambda x: x / 3600), # C → Ah
    '(Q-Qo)/mA.h': ('charge_capacity_ah', lambda x: x / 1000), # mAh → Ah
}
```

**Implementation Steps**:
1. Add galvani dependency for .mpr/.mpt parsing
2. Create BioLogicParser class following BaseParser pattern
3. Implement column mapping with unit conversions
4. Add timestamp extraction from BioLogic metadata
5. Test with real BioLogic files

### 4. User Grouping System
**Status**: Design Phase  
**Priority**: Medium

**Per-Cell Grouping Structure**:
```python
# CELL_001/user_groups/aging_rests.json
{
    "group_name": "aging_rests",
    "cell_id": "CELL_001", 
    "description": "Rest phases for aging analysis",
    "segments": [
        "CELL_001_file01_action05",
        "CELL_001_file02_action08", 
        "CELL_001_file03_action11"
    ],
    "filters": {
        "fundamental_technique": "OCV",
        "min_duration_s": 300,
        "min_fit_quality": 0.9
    },
    "group_analytics": {
        "avg_time_constant": 45.2,
        "time_constant_trend": "increasing",
        "fit_quality_avg": 0.94
    }
}
```

**CLI Extensions Needed**:
```bash
# Create group within a cell
battery-analyzer group create CELL_001 "formation_rests" \
  --technique OCV \
  --file-pattern "formation*" \
  --min-duration 300

# Compare same group across cells
battery-analyzer compare group "aging_rests" \
  --cells CELL_001,CELL_002,CELL_003 \
  --metric time_constant \
  --plot
```

## Known Issues to Investigate

### 1. EIS Frequency Range Detection
**Issue**: Some EIS segments show frequency range 0.00e+00 - 0.00e+00 Hz  
**Investigation Needed**:
- Check if EIS data contains actual frequency values
- Verify impedance column parsing
- Review ActionId mapping for EIS segments
- Test with known good EIS files

### 2. Unknown Technique Classification
**Issue**: Many actions classified as 'UNKNOWN'  
**Actions Needed**:
- Log all unique technique names encountered
- Expand TECHNIQUE_MAPPING with variants
- Improve pattern matching for technique classification
- Handle technique name variations

### 3. Memory Usage with Large Files
**Issue**: Not yet tested with multi-GB files  
**Testing Needed**:
- Profile memory usage with 1GB+ files
- Test concurrent file processing
- Optimize Polars operations for memory efficiency

## Future Development Phases

### Phase 5: Web Interface (Future)
- FastAPI backend with file upload
- React frontend with visualization
- Real-time processing status
- Interactive group creation and analysis

### Phase 6: Advanced Analytics (Future)  
- Machine learning for pattern recognition
- Anomaly detection in experimental data
- Predictive modeling for battery performance
- Multi-variate analysis across cells

### Phase 7: Production Deployment (Future)
- Docker containerization
- PostgreSQL database backend
- API authentication and user management
- Cloud deployment (AWS/GCP)

## Development Guidelines

### Code Quality Standards
- All new parsers must output universal 32-column schema
- Analytics must include quality metrics (R², completeness)
- Storage operations must be atomic and error-safe
- CLI commands must handle errors gracefully

### Testing Requirements
- Unit tests for all new parsers
- Integration tests for full pipeline
- Performance tests for large files
- Validation tests against known results

### Documentation Updates
- Update project_status.md for completed features
- Add new techniques to this file's mapping tables
- Update implementation_guide.md for new patterns
- Keep README.md current with latest capabilities

## Emergency Procedures

### Parser Failures
1. Check file format validation
2. Review column mapping compatibility
3. Validate universal schema conversion
4. Fall back to error logging and partial processing

### Storage Corruption
1. Verify raw files are intact
2. Regenerate processed files from raw
3. Validate parquet file integrity
4. Restore from backups if available

### Performance Issues
1. Profile memory and CPU usage
2. Identify bottlenecks in processing pipeline
3. Implement streaming for large files
4. Consider distributed processing

---

**For Implementation Details**: See `implementation_guide.md`  
**For Current Status**: See `project_status.md`  
**For Project Overview**: See `README.md`