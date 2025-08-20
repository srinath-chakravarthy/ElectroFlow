# Electrochemical Analysis Suite

A comprehensive web-based application for electrochemical battery data analysis and management. Designed for small-scale battery research (30-60 cells) with professional-grade data processing, visualization, and universal instrument support.

## 🚀 Features

- **🌐 Modern Web Interface**: Professional Panel web application with responsive design
- **🔋 Complete Cell Management**: Rich metadata tracking (chemistry, capacity, electrode details)
- **📊 Interactive Visualization**: HoloViews plots with dynamic decimation and segment coloring
- **🔍 Intelligent Analysis**: Automatic technique detection and Nyquist plot generation
- **📁 Universal File Processing**: VersaStudio (.par + .par.csv) with BioLogic support planned
- **💾 Clean Data Organization**: Standardized cell-based directory structure
- **🖥️ Multi-Interface Support**: Web UI, CLI, Python API, and Jupyter integration

## ✅ Current Implementation Status

### Professional Web Application
- **Modern Panel Interface**: 3-column responsive layout with card-based design
- **Professional Styling**: Scientific color scheme with gradients and hover effects
- **Interactive Components**: Cell management, file upload, data visualization, status feedback
- **Real-time Updates**: Dynamic status messages with timestamps
- **Responsive Design**: Works on desktop and tablet devices

### Universal Data Processing
- **29-Column Universal Schema**: Instrument-agnostic data structure
- **VersaStudio Support**: Complete .par + .par.csv processing with impedance data
- **Automatic Timestamping**: Absolute timestamps computed from acquisition metadata
- **Segment Detection**: Automatic experimental technique boundaries
- **Data Migration**: Standardized cell-based raw file organization

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
# Create a cell
python -m src_clean.cli.main create-cell CELL_001 --chemistry Li_ion

# Process files
python -m src_clean.cli.main process-files metadata.par data.par.csv CELL_001

# List cells and files
python -m src_clean.cli.main list-cells
python -m src_clean.cli.main list-files CELL_001

# Get database statistics
python -m src_clean.cli.main stats
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
-- Cell-level metadata with rich material information
cells: id, name, chemistry, description, capacity_ah, 
       cathode_material, cathode_mass_mg, anode_material, anode_mass_mg

-- File-level processing results
files: id, cell_id, file_id, original_filename, paired_filename,
       parquet_file_path, acquisition_start, processing_status

-- Segment-level technique boundaries  
segments: id, file_id, segment_index, technique_id, technique_name,
          start_row, end_row, start_time_s, end_time_s, point_count

-- ActionID technique mappings
actionid_mappings: action_id, technique_name, fundamental_technique
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

**Status**: ✅ Production-ready web application with professional interface  
**Version**: 3.0 - Modern Panel web interface with universal data processing  
**Last Updated**: August 20, 2025

**Quick Access**:
- **Web Interface**: `python echem_web.py` → `http://localhost:5007`
- **Documentation**: `docs/panel_ui_components.md`
- **API Reference**: `src_clean/backend/api.py`