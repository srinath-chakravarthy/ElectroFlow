# Battery Data Analyzer - Qt Desktop Application

A comprehensive Qt desktop application for electrochemical battery data analysis and management. Designed for small-scale battery research (30-60 cells) with professional-grade data processing and visualization.

## 🚀 Features

- **🔋 Cell Management**: Complete material metadata tracking (cathode/anode masses, chemistry)
- **📊 Interactive Visualization**: pyqtgraph plots with zoom, pan, crosshair, and real-time data loading
- **🔍 Segment Analysis**: Row-mapped database for efficient technique-specific analysis
- **📁 File Processing**: Dual-file support (.par + .par.csv) with timestamp computation
- **👥 Group Management**: Multi-selection segment grouping for comparative studies
- **💾 Database Storage**: Clean SQLite architecture with segment-based row mapping
- **🖥️ Desktop Native**: Qt application with resizable panels and modal workflows

## ✅ Current Implementation Status

### Fully Functional Qt Application
- **3-Panel Resizable Interface**: Cell/experiment tree, data viewer, actions/segments management
- **Modal Upload/Review Dialog**: 4-panel plotting interface for comprehensive file validation
- **Complete Cell CRUD**: Create, read, update cells with material metadata
- **Real-time Data Loading**: Direct parquet data access with interactive plotting
- **Segment-Level Analysis**: Color-coded analysis status with database storage

### Clean Database Architecture
```sql
-- Cell-level material metadata
cells: id, cell_name, chemistry, cathode_material, cathode_mass_mg, anode_material, anode_mass_mg

-- File-level (files ARE experiments)  
files: id, cell_id, file_id, original_filename, acquisition_start, parquet_file_path

-- Segment-level with efficient row mapping
segments: id, file_id, segment_index, start_row, end_row, analysis_status, analysis_results_json

-- User-defined groups
user_groups: id, cell_id, group_name, segment_ids (JSON array)
```

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Required packages:
pip install PySide6 polars pyqtgraph pandas numpy scipy
```

### Running the Application

```bash
# Start the Qt application
python -m src.qt_app.main

# Optional: Specify data directory
python -m src.qt_app.main --data-dir /path/to/your/data

# Debug mode
python -m src.qt_app.main --debug
```

## 📚 Usage Guide

### 1. Creating Cells

1. **New Cell**: Click "New Cell" button or File → New Cell
2. **Enter Details**:
   - **Cell Name**: Unique identifier (e.g., `CELL_001`)
   - **Chemistry**: Battery type (Li_metal, Li-ion, LFP, NMC, etc.)
   - **Capacity**: Nominal capacity in Ah
   - **Cathode**: Material type and active mass in mg
   - **Anode**: Material type and active mass in mg
   - **Notes**: Assembly conditions, references

### 2. File Upload Workflow

1. **Select Cell**: Click on cell in left panel
2. **Upload Files**: Click "Upload Files" or Ctrl+U
3. **Modal Review Dialog**:
   - Select .par file (technique structure)
   - Select matching .par.csv file (calibrated data)
   - Review 4-panel plots:
     - Applied Potential vs Time
     - Current vs Time
     - Nyquist Plot (colored by segment)
     - Applied Potential vs Current
   - Confirm processing

### 3. Data Analysis Workflow

**Step 1: Select Experiment**
- Click experiment in cell tree
- Data loads in main viewer

**Step 2: Review Data**
- **File Overview**: Metadata and experiment statistics
- **Data Table**: Raw data preview with sorting
- **Plots**: Interactive visualization with axis selection
- **Analysis**: Segment-level results summary

**Step 3: Segment Management**
- Use bottom-left panel for segment selection
- Ctrl+click for multi-selection
- Create groups for comparative analysis
- Color-coded status: 🟢 Completed, 🔴 Failed, 🟡 Pending

### 4. Interactive Plotting

**Controls:**
- **Zoom**: Mouse wheel or box selection
- **Pan**: Click and drag
- **Crosshair**: Hover for exact values
- **Axis Selection**: X/Y dropdowns
- **Reset**: Clear button

**Optimization:**
- Automatic downsampling for >10k points
- Real-time data loading from parquet files
- Memory-efficient for large datasets

## 🏗️ Application Architecture

### 3-Panel Main Window
```
┌─────────────────────────────────────────────────────────────────┐
│ File | View | Analysis | Help                                   │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌───────────────────────────────────────────┐│
│ │ Cells &         │ │ Data Viewer (Tabbed)                      ││
│ │ Experiments     │ │ • File Overview                           ││
│ │ ├─ CELL_001     │ │ • Data Table                              ││
│ │ │  ├─ exp1.par  │ │ • Interactive Plots                      ││
│ │ │  └─ exp2.par  │ │ • Analysis Results                       ││
│ │ └─ CELL_002     │ │                                          ││
│ └─────────────────┘ └───────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────────────┐│
│ │ Actions &       │ │ Group           │ │ Analysis Tabs         ││
│ │ Segments        │ │ Management      │ │ • Data View           ││
│ │ ✓ OCV Segment 1 │ │ ├─ OCV_Group    │ │ • Analysis            ││
│ │ ✓ OCV Segment 2 │ │ ├─ CC_Group     │ │ • Plotting            ││
│ │   CC Segment 1  │ │ └─ EIS_Group    │ │                      ││
│ └─────────────────┘ └─────────────────┘ └───────────────────────┘│
│ Status: Active: CELL_001 | Ready                               │
└─────────────────────────────────────────────────────────────────┘
```

### Data Processing Pipeline

1. **Upload**: Validate .par/.par.csv file pairs
2. **Parse**: Extract metadata, technique sequences, ActionIDs
3. **Convert**: Transform to universal 29-column schema  
4. **Timestamp**: Compute absolute timestamps from acquisition_start
5. **Store**: Save as parquet with segment row mapping in database
6. **Analyze**: Run fundamental analysis per segment

### Timestamp Computation
```python
# From .par file metadata
acquisition_start = datetime.strptime(DateAcquired + TimeAcquired, format)

# For each data point
absolute_timestamp = acquisition_start + timedelta(seconds=elapsed_time_s)
```

## 🔧 Advanced Features

### Segment-Based Analysis
```python
# Efficient parquet access via row ranges
segment_data = parquet_file.slice(start_row, end_row - start_row)
```

**Benefits:**
- Fast re-analysis of specific techniques
- Memory efficient for large files  
- Enables technique-specific operations
- Direct database queries by row ranges

### Dynamic ActionID Discovery

**Workflow:**
1. Parser encounters unknown ActionID
2. User prompted with technique classification dialog
3. Mapping stored in database for future use
4. No code changes needed for new techniques

**Database Integration:**
```sql
actionid_mappings: action_id, technique_name, fundamental_technique, user_defined
```

### File Mobility
```python
# Atomic operation: move file with all segments
db.move_file_to_cell(file_id, new_cell_id, new_cell_name)
# Automatically updates segments.cell_name for easy reference
```

## 📁 Data Organization

### Directory Structure
```
data/
├── battery_data.db              # SQLite database
└── processed_parquet/           # Processed data files
    ├── CELL_001_exp1.parquet
    ├── CELL_001_exp2.parquet
    └── CELL_002_exp1.parquet
```

### Supported File Types

**VersaStudio (Current):**
- **.par files**: Technique structure, ActionID mapping, metadata
- **.par.csv files**: Calibrated measurement data (required for EIS)

**Future Support (Planned):**
- **BioLogic**: .mpr/.mpt files with galvani integration
- **Gamry**: .DTA file support

## 🔍 Quality Control

### File Validation
- Ensures .par/.par.csv pairs are from same experiment
- Validates file timestamps and compatibility
- Checks for required metadata fields

### Error Handling
- Graceful parsing failure recovery
- Real-time processing status updates
- Comprehensive error logging and user feedback

### Data Integrity
- Foreign key constraints in database
- Atomic operations for file movement
- Analysis result versioning and validation

## 🚨 Troubleshooting

### Application Startup Issues
```bash
# Check dependencies
pip install PySide6 polars pyqtgraph pandas

# Run with debug output
python -m src.qt_app.main --debug

# Reset database (WARNING: deletes all data)
rm data/battery_data.db
```

### File Upload Problems
- **Pairing Issues**: Ensure .par and .par.csv are from same experiment
- **Permissions**: Check file read permissions and disk space
- **Export Settings**: Verify VersaStudio CSV export is calibrated

### Plotting Issues
- Try different X/Y axis combinations
- Check if selected columns exist in data
- Use "Clear" button to reset plot
- Enable downsampling for large datasets

### Performance Optimization
- Use reasonable preview limits (1000-10k rows)
- Close unused experiments to free memory
- For files >1GB, consider data filtering
- Monitor memory usage during large file processing

## 🛠️ Development

### Architecture Benefits

**Research Workflow:**
- Single application for complete workflow
- Native performance without browser limitations
- Offline operation with local processing
- Professional metadata collection

**Data Management:**
- Segment-based querying and analysis
- Row-mapped direct parquet access
- Easy error correction (file movement)
- Analysis persistence with reproducibility

**Extensibility:**
- Database-driven technique mapping
- Universal schema for multi-instrument support
- Plugin-ready backend API
- Cross-platform Qt deployment

### Contributing

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/new-analysis`
3. **Implement** following existing patterns
4. **Test** with real data files
5. **Document** in CLAUDE.md and commit messages
6. **Submit** pull request with detailed description

### Development Setup
```bash
# Clone repository
git clone [repository-url]
cd Potentiostat_Data_analyser

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-qt  # For testing

# Run tests
pytest tests/

# Start application in debug mode
python -m src.qt_app.main --debug
```

## 📊 Performance Metrics

### Validated Capabilities
- **✅ Large Files**: >1GB .par files with 948k+ data points
- **✅ Processing Speed**: <10 seconds for typical experiments
- **✅ Memory Efficiency**: Streaming processing for large datasets
- **✅ Analysis Accuracy**: Curve fitting R² >0.9 for quality segments
- **✅ Real-time UI**: Responsive interface during processing

## 📄 Documentation

| Document | Purpose |
|----------|---------|
| **README.md** | User guide and quick start (this file) |
| **CLAUDE.md** | Technical architecture and development guide |
| **project_status.md** | Implementation status and validation results |
| **src/core/README.md** | Core processing pipeline documentation |

## 📜 License

MIT License - See LICENSE file for details.

---

**Status**: ✅ Fully functional Qt desktop application  
**Latest Version**: Complete 3-panel interface with database integration  
**Last Updated**: August 18, 2025