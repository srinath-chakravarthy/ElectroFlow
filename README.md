# Electrochemical Analysis Suite

A comprehensive web-based application for electrochemical battery data analysis and management. Designed for small-scale battery research (30-60 cells) with professional-grade data processing, visualization, and universal instrument support.

## 🚀 Features

- **🌐 Modern Web Interface**: Professional Panel web application with responsive design
- **🔋 Complete Cell Management**: Rich metadata tracking with automatic directory creation
- **📊 Interactive Visualization**: HoloViews plots with dynamic decimation and technique-specific coloring
- **🧠 Universal Technique Mapping**: 5 fundamental techniques with instrument-specific ActionID translation
- **⚡ Automatic Analytics**: Real-time computation of core metrics and technique-specific analysis
- **🏷️ Group Management**: Visual segment organization with real-time preview plots
- **🔧 Units-Aware Processing**: Automatic unit conversion (mA→A, mV→V) with Pint library
- **📁 Perfect Data Organization**: Per-cell structure (raw/, processed/, analysis_results/, user_groups/)
- **🔧 CASCADE Operations**: Complete file system and database cleanup with atomic transactions
- **🖥️ Multi-Interface Support**: Web UI, CLI, Python API, and Jupyter integration

## ✅ Current Implementation Status (v4.4.0)

### Advanced Analytics System (COMPLETE ✅)
- **sqrt(t) + Exponential Fitting**: Dual curve fitting with automatic best-fit selection based on R²
- **Coefficient Storage**: Complete fit parameters (V∞, A, τ, R²) stored in JSON for replotting
- **Group Temporal Analytics**: Time-series analysis with cumulative capacity/energy across file boundaries
- **Fit Quality Statistics**: R² distributions and success rates aggregated across all techniques
- **Voltage Correlation Analysis**: Pearson/Spearman correlations between metrics and start/end voltages
- **Analytics Config Registry**: Auto-generated interpretability system with 20 base + 6 cumulative fields
- **8 Advanced CLI Commands**: Complete analytics interface with JSON export and matplotlib plotting

### Templated Groups System (COMPLETE ✅)
- **Automatic Template Creation**: Template groups auto-generated for all fundamental techniques
- **Smart Copy System**: Template_All_Rest → User_Rest with conflict resolution
- **Single Dropdown UI**: Visual distinction with 🔧 templates and 📁 user groups, eliminates selection conflicts
- **Integrated Refresh**: Manual + automatic refresh on file processing + tab switching
- **Case-Insensitive Matching**: Robust database JOINs handle technique name differences

### Universal Data Processing (COMPLETE ✅)
- **38-Column Universal Schema**: Explicit units for every column (A, V, Ah, Wh, Hz, Ω)
- **Automatic Unit Conversion**: Pint library integration for robust unit handling
- **5 Fundamental Techniques**: Rest, Galvanostatic, Potentiostatic, EIS, CV with VersaStudio mapping
- **Perfect Data Organization**: Automatic per-cell structure with CASCADE deletion system

### Universal Technique System
- **5 Fundamental Techniques**: Rest, Galvanostatic, Potentiostatic, EIS, Cyclic Voltammetry
- **VersaStudio ActionID Mapping**: 23→Rest, 20→EIS, 8→Galvanostatic (instrument-specific translation)
- **Database-Driven**: Universal technique table with foreign key constraints
- **Automatic Detection**: Real-time technique classification during file processing

### Automatic Analytics Engine
- **Core Metrics**: Capacity (Ah), Energy (Wh), Duration (s) for all techniques
- **Technique-Specific Analysis**: Context-aware rest phase and pulse analysis
- **Advanced Curve Fitting**: Exponential decay with R² quality metrics
- **Database Storage**: All analytics stored in segments table with JSON details
- **Reanalysis System**: Update existing data with improved algorithms

### Perfect Data Organization (ENHANCED)
- **Automatic Directory Creation**: Complete per-cell structure on cell creation
- **CASCADE Deletion**: Proper file system and database cleanup
- **ProcessingResult API**: Standardized return types across all operations
- **Atomic Transactions**: Database integrity with foreign key constraints

### Clean Architecture
```
data_clean/cells/{cell_name}/
├── raw/                    # Original source files
├── processed/              # Parsed parquet files
├── analytics/              # Analysis results
├── groups/                 # User-defined groupings
└── images/                 # Generated plots
```

## 🌐 Quick Start - Web Interface

### Launch the Web Application
```bash
# Install dependencies
pip install -r requirements.txt

# Start web server (default port 5007)
python echem_web.py

# Custom port
python echem_web.py --port 5008

# Development mode with auto-reload
python echem_web.py --dev
```

**Access Interface**: Open browser to `http://localhost:5007`

### Web Interface Workflow
1. **Create Cell**: Enter cell details (chemistry, capacity, electrode materials)
2. **Upload Files**: Select paired .par + .par.csv files with temperature setting
3. **View Data**: Automatic plot type detection (Voltage/Current vs Time, Nyquist plots)
4. **Analyze Results**: Interactive visualization with data preview tables

## 🔧 Alternative Interfaces

### Command Line Interface
```bash
# Cell and file operations
python -m src_clean.cli.main create-cell CELL_001 --chemistry Li_ion
python -m src_clean.cli.main process-files metadata.par data.par.csv CELL_001
python -m src_clean.cli.main list-cells --format json

# Group management
python -m src_clean.cli.main create-group CELL_001 "GITT Rest" --description "All rest phases"
python -m src_clean.cli.main add-to-group group_001 seg_001 seg_003 seg_005

# Advanced analytics (NEW)
python -m src_clean.cli.main --format json compare-groups 16 --metrics capacity energy fit_quality
python -m src_clean.cli.main group-temporal 16 --plot-types cumulative_capacity voltage_evolution
python -m src_clean.cli.main group-fit-quality 16 --technique-filter Rest
python -m src_clean.cli.main group-voltage-correlation 16 --correlation-type pearson
python -m src_clean.cli.main generate-analytics-config --output-path custom_config.py
python -m src_clean.cli.main list-cumulative-fields

# System information
python -m src_clean.cli.main stats --format json
```

### Python API
```python
from src_clean.backend import get_backend_api
from pathlib import Path

# Initialize API
api = get_backend_api()

# Create cell with metadata
result = api.create_cell(
    name="CELL_001",
    chemistry="Li_ion",
    capacity_ah=2.5,
    cathode_material="NMC811",
    cathode_mass_mg=15.2
)

# Process dual files
result = api.process_dual_files(
    metadata_path=Path("experiment.par"),
    data_path=Path("experiment.par.csv"), 
    cell_name="CELL_001",
    temperature_c=25.0
)

# Access processed data
data = api.get_file_data(result.file_id)  # Returns Polars DataFrame

# Group management
result = api.create_group("CELL_001", "Rest Phases", "All rest measurements")
api.add_segments_to_group(result.group_id, ["seg_001", "seg_003"])
groups = api.get_cell_groups("CELL_001")

# Advanced analytics (NEW)
temporal_data = api.get_group_temporal_analytics([group_id])
fit_stats = api.get_group_fit_quality_statistics([group_id])
correlations = api.get_group_voltage_correlation_analytics([group_id])
```

### Jupyter Notebook Integration
```bash
# Launch Jupyter with example notebook
jupyter notebook examples/jupyter_example.ipynb
```

## 📊 Universal Data Schema

### 29-Column Universal Schema
**Core Time & Indexing (6 columns)**:
- `time_s`: Relative time from experiment start (seconds)
- `timestamp`: Absolute timestamp (ISO format) for traceability
- `segment_number`, `point_number`, `loop_number`, `battery_cycle`

**Electrochemical Core (6 columns)**:
- `potential_v`, `current_a`: Working electrode measurements
- `potential_applied_v`, `current_applied_a`: Applied control values
- `potential_avg_v`, `current_avg_a`: Averaged measurements

**Battery Analytics (4 columns)**:
- `charge_capacity_ah`, `energy_wh`, `power_w`, `temperature_c`

**EIS Support (5 columns)**:
- `frequency_hz`, `impedance_real_ohm`, `impedance_imag_ohm`
- `impedance_mag_ohm`, `impedance_phase_deg`

**Advanced Metadata (8 columns)**:
- `current_range`, `potential_range`, `mode`, `technique_id`
- `status_flags`, `ce_potential_v`, `cell_potential_v`, `ac_amplitude_v`, `aux_voltage_v`

## 🎯 Advanced Features

### Intelligent Visualization
- **Automatic Plot Detection**: Voltage/Current time series, Nyquist plots for AC data
- **Dynamic Decimation**: Handles large datasets (>10k points) efficiently
- **Segment Coloring**: Different colors for multiple EIS measurements
- **Interactive Tools**: Pan, zoom, box selection, data export

### Fundamental Analytics Engine
- **Universal Core Metrics**: Automatic capacity (Ah), energy (Wh), and duration for all techniques
- **Context-Aware Analysis**: Intelligent rest phase analysis based on previous segment context
- **Advanced Curve Fitting**: Exponential decay fitting with R² quality metrics
- **Current Pulse Analysis**: Multi-point resistance calculations (immediate, 10s, 30s)
- **Technique Classification**: Automatic detection and appropriate analysis methods
- **Reanalysis System**: Update existing data with improved analytics algorithms

### Data Management
- **Atomic Processing**: Database transactions ensure data consistency
- **File Migration**: Automatic organization into standardized structure
- **Reprocessing**: Update files with schema improvements
- **Cell-Based Organization**: Portable directory structure for backup/sharing

### Professional Interface Components

#### Cell Manager
- Rich metadata collection (chemistry, electrodes, capacity)
- Visual cell list with file counts and chemistry types
- Professional form validation and error handling

#### File Uploader  
- Step-by-step workflow with visual guidance
- Paired file validation (.par + .par.csv)
- Temperature metadata and processing status
- File management with delete/refresh operations

#### Data Viewer
- Automatic AC data detection for impedance plots
- Professional plot styling with scientific color schemes
- Data preview tables (first 1000 rows)
- Export capabilities for further analysis

#### Status System
- Real-time updates with professional styling
- Color-coded status types (success, warning, error, processing)
- Integrated system information display

## 🔧 Configuration

### Environment Variables (.env)
```env
# Data storage
ELECTROCHEMICAL_DATA_DIR=data_clean
ELECTROCHEMICAL_DB_NAME=electrochemical.db

# Web interface
WEB_PORT=5007
WEB_HOST=localhost
WEB_DEBUG=False

# Processing
DEFAULT_TEMPERATURE_C=25.0
MAX_FILE_SIZE_MB=1000
DECIMATION_THRESHOLD=10000

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
```

## 🏗️ Architecture

### Clean Modular Design
```
src_clean/
├── core/
│   ├── config.py           # Environment configuration
│   ├── data_models.py      # Universal schema and validation
│   ├── database.py         # SQLite operations
│   └── exceptions.py       # Error handling
├── backend/
│   ├── api.py             # Backend orchestration
│   └── data_migration.py  # Directory structure management
├── parsers/
│   ├── factory.py         # Auto-detection system
│   ├── base.py           # Abstract interfaces
│   └── versastudio.py    # VersaStudio implementation
├── panel_app/
│   ├── main_app.py       # Web application
│   └── components/       # UI components
└── cli/
    └── main.py           # Command-line interface
```

### Database Schema
```sql
-- Universal technique system (NEW)
fundamental_techniques: technique_id, technique_name, description
instrument_actionid_mappings: action_id, action_name, technique_id, description

-- Cell-level metadata with rich material information
cells: id, name, chemistry, capacity_ah, cathode_material, cathode_mass_mg,
       anode_material, anode_mass_mg, notes, created_at

-- File-level processing results
files: file_id, cell_id, original_filename, paired_filename,
       parquet_file_path, acquisition_start, processing_status, metadata

-- Segment-level with automatic analytics (ENHANCED)
segments: id, file_id, segment_number, technique_id, start_row, end_row,
          start_time_s, end_time_s, duration_s, capacity_ah, energy_wh,
          start_potential_v, end_potential_v, start_current_a, end_current_a,
          point_count, analysis_status, analysis_results
```

## 🧪 Testing and Validation

### Run Test Suite
```bash
# Complete system test
python test_clean_implementation.py

# Web interface test
python -c "from src_clean.panel_app.main_app import ElectrochemicalApp; app = ElectrochemicalApp(); print('✅ Web interface ready')"
```

### Validated Capabilities
- **✅ Large Files**: >1GB .par files with 948k+ data points processed
- **✅ Multi-Interface**: Web, CLI, Python API, Jupyter all functional
- **✅ Data Migration**: Raw files organized in standardized structure
- **✅ Impedance Processing**: Complex EIS data with proper Nyquist visualization
- **✅ Professional UI**: Responsive web interface with modern styling

## 📈 Performance Metrics

- **Processing Speed**: <10 seconds for typical experiments (948k points)
- **Memory Efficiency**: Streaming processing for large datasets
- **Visualization**: Dynamic decimation handles >10k points smoothly
- **Database**: SQLite WAL mode for concurrent operations
- **Response Time**: <2 seconds for data loading and plot generation

## 🔍 Troubleshooting

### Common Issues

**Installation Problems**:
```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Check Python version (3.9+ required)
python --version
```

**Web Interface Issues**:
```bash
# Check port availability
netstat -an | grep 5007

# Try different port
python echem_web.py --port 5008

# Enable debug mode
python echem_web.py --dev
```

**File Processing Problems**:
- Ensure .par and .par.csv files are from the same experiment
- Check file permissions and disk space
- Verify VersaStudio CSV export settings (calibrated data required)

**Performance Issues**:
- Files >1GB may take longer to process
- Use data decimation for visualization (automatic above 10k points)
- Monitor system memory during large file processing

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **README.md** | User guide and quick start (this file) |
| **CLAUDE.md** | Technical architecture and development guide |
| **docs/panel_ui_components.md** | Web interface component documentation |
| **docs/fundamental_analytics.md** | Analytics engine technical documentation |
| **cleanup_summary.md** | Legacy code removal and modernization |

## 🛠️ Development

### Contributing
1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/new-analysis`
3. **Follow** existing code patterns in `src_clean/`
4. **Test** with real data files using web interface
5. **Document** changes in relevant markdown files
6. **Submit** pull request with detailed description

### Development Setup
```bash
# Clone and setup
git clone [repository-url]
cd Potentiostat_Data_analyser

# Install development dependencies  
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Edit as needed

# Start development server
python echem_web.py --dev

# Run tests
python test_clean_implementation.py
```

## 🚀 Future Roadmap

### Planned Features
- **BioLogic Support**: .mpr/.mpt file parsing with galvani integration
- **Advanced Analytics**: Machine learning for pattern recognition
- **Group Analysis**: Cross-cell comparative studies
- **Export Tools**: Publication-ready plots and data export
- **API Integration**: REST API for laboratory information systems

### Technology Stack
- **Backend**: Python 3.9+, Polars, SQLite, Panel
- **Frontend**: Panel web framework with Bokeh plotting
- **Visualization**: HoloViews with professional styling
- **Data**: Universal 29-column schema with instrument mappings
- **Architecture**: Clean modular design with configuration management

## 📜 License

MIT License - See LICENSE file for details.

---

**Status**: ✅ Production-ready with advanced analytics and universal technique mapping  
**Version**: 4.0 - Universal technique system with automatic analytics engine  
**Last Updated**: August 20, 2025

**Quick Access**:
- **Web Interface**: `python echem_web.py` → `http://localhost:5007`
- **Documentation**: `docs/panel_ui_components.md`
- **API Reference**: `src_clean/backend/api.py`