# Implementation Guide - Battery Data Analyzer

**Target Audience**: Developers working on the battery data analyzer system  
**Last Updated**: August 17, 2025

## System Overview

The Battery Data Analyzer follows a modular architecture with clear separation between parsing, analytics, storage, and user interfaces. The system now uses SQLite database backend for metadata storage and Panel+Plotly UI for cell preprocessing and data management. Designed for extensibility to support multiple instrument types while maintaining a universal data schema.

## Code Organization

### Core Architecture
```
src/
├── core/                   # Data models and parsing
│   ├── data_models.py     # Universal schema, DataFile class
│   ├── parsers.py         # VersaStudio dual file parser (.par + .par.csv)
│   ├── parser_factory.py # Multi-instrument parser framework
│   └── database.py        # SQLite database schema and operations
├── analysis/              # Analytics engine
│   └── analytics.py       # Fundamental analytics (CC, REST, EIS, etc.)
├── io_utils/              # Storage and file management
│   └── storage.py         # Database-backed storage manager
├── ui/                    # Panel-based user interface
│   ├── backend_api.py     # Clean UI/backend API separation
│   ├── components/        # Panel UI components
│   └── main_app.py        # Main Panel application
├── utils/                 # Shared utilities
└── visualization/         # Plotting and visualization
```

### Key Design Patterns

**1. Dual File Processing Pattern**
- VersaStudio parser handles both .par (technique sequence) and .par.csv (calibrated data)
- .par files provide ActionId mapping and technique identification
- .par.csv files provide calibrated EIS data and measurements
- Combined processing ensures data quality and technique mapping

**2. SQLite Database Backend**
- Centralized metadata storage replacing JSON files
- Referential integrity for file movement between cells
- Schema migration support for future updates
- Clean separation between raw data storage and metadata

**3. Panel UI with Backend API**
- Clean UI/backend separation via backend_api.py
- Panel components for cell management and file association
- Plotly integration for large dataset visualization
- Default directory: /Users/srinathchakravarthy/

**4. Universal Schema Conversion**
- All parsers output to same 32-column universal schema
- Instrument-specific mapping functions handle column translation
- Missing columns filled with appropriate null values

**5. Pipeline Architecture**
- Clear separation: Parse → Analyze → Store → UI
- Each stage is independent and testable
- Error handling at each stage with graceful degradation

## SQLite Database Architecture

### Database Schema
```sql
-- Cells table
CREATE TABLE cells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cell_name TEXT UNIQUE NOT NULL,
    description TEXT,
    chemistry TEXT,
    capacity_ah REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Files table  
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cell_id INTEGER NOT NULL,
    file_id TEXT UNIQUE NOT NULL,
    original_filename TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'par' or 'par_csv'
    file_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,
    processed_path TEXT,
    analysis_path TEXT,
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status TEXT DEFAULT 'uploaded', -- 'uploaded', 'processing', 'completed', 'failed'
    FOREIGN KEY (cell_id) REFERENCES cells (id) ON DELETE CASCADE
);

-- Technique segments table
CREATE TABLE technique_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    segment_number INTEGER NOT NULL,
    action_id INTEGER,
    technique_name TEXT,
    fundamental_technique TEXT,
    start_time_s REAL,
    end_time_s REAL,
    point_count INTEGER,
    FOREIGN KEY (file_id) REFERENCES files (file_id) ON DELETE CASCADE
);

-- User groups table
CREATE TABLE user_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cell_id INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    description TEXT,
    file_ids TEXT, -- JSON array of file_ids
    segments TEXT, -- JSON array of segment specifications
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cell_id) REFERENCES cells (id) ON DELETE CASCADE,
    UNIQUE(cell_id, group_name)
);
```

### Database Operations
```python
# src/core/database.py
class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()
    
    def create_cell(self, cell_name: str, **metadata) -> int:
        """Create new cell and return cell_id"""
        
    def add_file_to_cell(self, cell_id: int, file_info: dict) -> str:
        """Add file to cell and return file_id"""
        
    def move_file_to_cell(self, file_id: str, new_cell_id: int) -> bool:
        """Move file between cells atomically"""
        
    def get_cell_files(self, cell_id: int) -> List[dict]:
        """Get all files for a cell"""
        
    def update_processing_status(self, file_id: str, status: str):
        """Update file processing status"""
```

## Panel UI Implementation

### Backend API Layer
```python
# src/ui/backend_api.py
class BackendAPI:
    """Clean interface between Panel UI and backend systems"""
    
    def __init__(self, db_manager: DatabaseManager, storage_manager: StorageManager):
        self.db = db_manager
        self.storage = storage_manager
    
    def get_all_cells(self) -> List[dict]:
        """Get all cells with file counts"""
        
    def create_cell(self, cell_name: str, **metadata) -> dict:
        """Create new cell, return success/error status"""
        
    def add_files_to_cell(self, cell_id: int, file_paths: List[Path]) -> dict:
        """Add multiple files to cell, return processing results"""
        
    def get_file_data_preview(self, file_id: str, n_rows: int = 1000) -> pl.DataFrame:
        """Get data preview for UI display"""
```

### Panel UI Components
```python
# src/ui/components/cell_manager.py
class CellManagerTab:
    """Cell creation and management interface"""
    
    def __init__(self, backend_api: BackendAPI):
        self.api = backend_api
        self.setup_layout()
    
    def setup_layout(self):
        # Cell list table
        # Create cell form
        # Cell metadata editor

# src/ui/components/file_association.py  
class FileAssociationTab:
    """File upload and cell association interface"""
    
    def __init__(self, backend_api: BackendAPI):
        self.api = backend_api
        self.default_directory = Path("/Users/srinathchakravarthy/")
        self.setup_layout()
    
    def setup_layout(self):
        # File browser (default: /Users/srinathchakravarthy/)
        # Cell selection dropdown
        # Dual file processing (.par + .par.csv)
        # Upload progress indicators

# src/ui/components/data_processing.py
class DataProcessingTab:
    """Data preview and processing interface"""
    
    def __init__(self, backend_api: BackendAPI):
        self.api = backend_api
        self.setup_layout()
    
    def setup_layout(self):
        # File data preview (plotly-resample for large datasets)
        # Processing status monitoring
        # Analysis results display
```

### Main Application
```python
# src/ui/main_app.py
import panel as pn
import plotly.graph_objects as go
from plotly_resampler import FigureResampler

class BatteryAnalyzerApp:
    """Main Panel application for battery data preprocessing"""
    
    def __init__(self):
        pn.extension('plotly')
        self.setup_backend()
        self.setup_ui()
    
    def setup_backend(self):
        db_path = Path("data/battery_analyzer.db")
        self.db_manager = DatabaseManager(db_path)
        self.storage_manager = StorageManager(self.db_manager)
        self.api = BackendAPI(self.db_manager, self.storage_manager)
    
    def setup_ui(self):
        self.cell_manager = CellManagerTab(self.api)
        self.file_association = FileAssociationTab(self.api)
        self.data_processing = DataProcessingTab(self.api)
        
        # Create tabbed interface
        self.tabs = pn.Tabs(
            ("Cell Management", self.cell_manager.layout),
            ("File Association", self.file_association.layout),
            ("Data Processing", self.data_processing.layout)
        )
    
    def serve(self, port: int = 5007):
        return self.tabs.servable()

if __name__ == "__main__":
    app = BatteryAnalyzerApp()
    pn.serve(app.serve(), port=5007, show=True)
```

## Dual File Processing Implementation

### VersaStudio Parser Updates
```python
# src/core/parsers.py - Enhanced for dual file processing
class VersaStudioParser(BaseParser):
    def parse_dual_files(self, par_path: Path, csv_path: Path) -> DataFile:
        """Parse both .par and .par.csv files for complete data"""
        
        # Parse .par for technique sequence and ActionId mapping
        par_data = self.parse_structure_only(par_path)
        
        # Parse .par.csv for calibrated measurement data
        csv_data = self.parse_calibrated_csv(csv_path)
        
        # Combine: technique mapping from .par + calibrated data from .csv
        return self.merge_dual_file_data(par_data, csv_data)
    
    def parse_calibrated_csv(self, csv_path: Path) -> pl.DataFrame:
        """Parse VersaStudio exported .par.csv file (calibrated data)"""
        # Read CSV with proper column detection
        # Apply VersaStudio CSV → Universal schema mapping
        # Validate data quality and calibration markers
        
    def validate_dual_files(self, par_path: Path, csv_path: Path) -> bool:
        """Validate that .par and .par.csv files are compatible"""
        # Check timestamps match
        # Verify segment counts align
        # Validate measurement compatibility
```

## Adding New Instrument Parsers

### Step 1: Create Parser Class
```python
# src/core/parsers.py
class BioLogicParser(BaseParser):
    """Parser for BioLogic .mpr/.mpt files."""
    
    def validate_file(self, file_path: Path) -> bool:
        """Check if file is BioLogic format."""
        return file_path.suffix.lower() in ['.mpr', '.mpt']
    
    def parse(self, file_path: Path) -> DataFile:
        """Parse BioLogic file to DataFile."""
        # Implementation here
        pass
```

### Step 2: Add Column Mapping
```python
# src/core/data_models.py
BIOLOGIC_MAPPING = {
    'time/s': 'time_s',
    'Ewe/V': 'potential_v', 
    'I/mA': ('current_a', lambda x: x / 1000),  # Unit conversion
    # ... other mappings
}
```

### Step 3: Register in Factory
```python
# src/core/parser_factory.py
PARSER_REGISTRY = {
    'versastudio': VersaStudioParser,
    'biologic': BioLogicParser,  # Add new parser
}
```

### Step 4: Update Storage Manager
```python
# src/io_utils/storage.py
def _process_file(self, raw_file_path: Path, cell_id: str):
    # Add new file type detection
    if raw_file_path.suffix.lower() in ['.mpr', '.mpt']:
        if self.biologic_parser.validate_file(raw_file_path):
            data_file = self.biologic_parser.parse(raw_file_path)
```

## Extending Analytics Engine

### Adding New Analysis Types
```python
# src/analysis/analytics.py
class FundamentalAnalytics:
    def _analyze_action(self, data: pl.DataFrame, action_id: int, technique: str):
        # Add new technique analysis
        if technique == 'NEW_TECHNIQUE':
            return self._analyze_new_technique(data, action_id)
    
    def _analyze_new_technique(self, data: pl.DataFrame, action_id: int) -> AnalysisResult:
        """Analyze new technique type."""
        # Implementation:
        # 1. Extract relevant columns
        # 2. Perform calculations  
        # 3. Return AnalysisResult with metrics
        pass
```

### Analysis Result Structure
```python
@dataclass
class AnalysisResult:
    technique: str                    # Fundamental technique (CC, OCV, GEIS, etc.)
    segment_id: int                  # Segment number (hierarchy-based)
    results: Dict[str, Any]          # Numerical results
    quality_metrics: Dict[str, float] # Quality indicators (R², completeness)
    fitted_data: Optional[Dict]       # Curve fitting data for plots
    
    # Note: ActionId values are collected separately in metadata for database building
```

## Storage System Customization

### Directory Structure Template
```python
def create_cell_structure(cell_id: str, custom_dirs: List[str] = None):
    """Create cell directory with custom subdirectories."""
    base_dirs = ["raw", "processed", "analysis_results", "exports/relaxis"]
    all_dirs = base_dirs + (custom_dirs or [])
    
    for subdir in all_dirs:
        (cell_dir / subdir).mkdir(parents=True, exist_ok=True)
```

### Custom Export Formats
```python
def export_custom_format(self, data: pl.DataFrame, format_name: str, output_path: Path):
    """Add custom export formats."""
    if format_name == 'instrument_specific':
        # Custom format implementation
        pass
```

## Testing Procedures

### Unit Testing Structure
```python
# tests/test_parsers.py
class TestVersaStudioParser:
    def test_parse_valid_file(self):
        parser = VersaStudioParser()
        result = parser.parse(sample_file_path)
        assert result.universal_data.shape[1] == 32
    
    def test_universal_schema_conversion(self):
        # Test column mapping accuracy
        pass
```

### Integration Testing
```python
# tests/test_integration.py  
class TestFullPipeline:
    def test_upload_process_export(self):
        storage = StorageManager()
        file_id, status = storage.upload_file(sample_file, "TEST_CELL")
        assert status == "uploaded"
        
        # Verify processed data
        data = storage.load_processed_file("TEST_CELL", file_id)
        assert not data.is_empty()
```

### Performance Testing
```python
def test_large_file_performance():
    """Test with files > 1GB."""
    start_time = time.time()
    result = parser.parse(large_file_path)
    duration = time.time() - start_time
    assert duration < MAX_PROCESSING_TIME
```

## Common Development Tasks

### VersaStudio Technique Mapping Strategy

The system uses a **dual-approach** for technique identification with ActionId priority:

#### **Method 1: ActionId-Based Mapping (Primary)**
Direct lookup for verified ActionIds with immediate technique assignment:

```python
# Verified ActionId database (data-driven expansion)
VERSASTUDIO_ACTIONID_MAPPING = {
    8: 'CC',     # Constant Current (verified from GITT data)
    20: 'GEIS',  # Galvanostatic EIS (verified from GITT data)
    23: 'OCV',   # Energy Open Circuit (verified from GITT data)
    # Add more as real data files are processed
}
```

**Benefits**: Simple, fast, accurate for known ActionIds
**Limitations**: Partial coverage, requires database expansion

#### **Method 2: Structural Parsing + Loop-Aware Mapping (Fallback)**
Complex hierarchical analysis with complete loop expansion:

```python
# Execution sequence building with loop iterations
def _build_execution_sequence():
    # 1. Filter structural actions (Common, Loop #X)
    # 2. Group experimental actions by ParentNode
    # 3. Expand loops based on "Number of Iterations"
    # 4. Create complete segment mapping (0-based continuous)
    
    # Example result:
    # 3 top-level + Loop#1(10×4) + Loop#2(20×4) = 123 total segments
```

**Benefits**: Complete coverage, handles complex hierarchies
**Limitations**: Complex logic, requires structural parsing

#### **Hybrid Implementation**
```python
# Final technique assignment priority:
fundamental_technique_final = (
    ActionId_mapping if ActionId in database
    else hierarchy_mapping
)
```

#### **Loop Expansion Example**
Real data file analysis showing complete segment mapping:
```
GITT_EIS_Charge_cycle1_Channel 2.par:
├── Top-level: Action1, Action2, Action13 → segments 0, 1, 122
├── Loop #1 (10 iterations): Action4-7 → segments 2-41 (40 total)
└── Loop #2 (20 iterations): Action9-12 → segments 42-121 (80 total)
Total: 123 segments (perfect 0-based continuous mapping)
```

#### **Database Expansion Process**
1. **Parse new .par files** with structural parser
2. **Check validation warnings** for inconsistent ActionIds  
3. **Manually verify techniques** from action names
4. **Add verified mappings** to VERSASTUDIO_ACTIONID_MAPPING
5. **Test with multiple files** to ensure consistency

**Current ActionId Coverage**: 3 verified (8, 20, 23) - grows organically with usage

### Adding New Technique Classification
1. Update `TECHNIQUE_MAPPING` in `data_models.py`
2. Add corresponding analysis method in `analytics.py`
3. Update CLI display formatting
4. Add test cases for new technique

### Modifying Universal Schema
1. Update `UNIVERSAL_COLUMNS` and `UNIVERSAL_SCHEMA`
2. Update all instrument mapping dictionaries
3. Modify `create_universal_dataframe()` function
4. Update export functions and CLI
5. Version bump and migration strategy

### Adding New CLI Commands
```python
# cli_tools/battery_analyzer.py
def new_command(args):
    """Handle new command."""
    # Implementation
    pass

# Add to main parser
new_parser = subparsers.add_parser('new_command', help='Description')
new_parser.add_argument('required_arg', help='Required argument')
```

## Debugging Guide

### Common Issues

**1. Parsing Failures**
- Check file format validation
- Verify column mappings
- Review metadata extraction
- Enable debug logging

**2. Analytics Errors**
- Verify data quality (null values, outliers)
- Check curve fitting convergence
- Review quality metric thresholds
- Validate input data ranges

**3. Storage Issues**
- Check file permissions
- Verify directory structure
- Review path handling
- Check disk space

### Debug Tools
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Data validation helpers
def validate_universal_schema(df: pl.DataFrame):
    """Validate DataFrame matches universal schema."""
    assert set(df.columns) == set(UNIVERSAL_COLUMNS)
    assert df.schema == UNIVERSAL_SCHEMA
```

## Performance Optimization

### Memory Management
- Use Polars lazy evaluation for large files
- Stream processing for GB-sized datasets
- Chunked analysis for memory-constrained environments

### Processing Speed
- Parallel analytics for multiple actions
- Cached intermediate results
- Efficient column operations

### Storage Optimization
- Parquet compression settings
- JSON minimization strategies  
- Selective column storage

## Security Considerations

### File Handling
- Validate file paths and extensions
- Sanitize user input for cell IDs
- Limit file sizes and processing time
- Secure temporary file handling

### Data Privacy
- No sensitive data in logs
- Secure storage permissions
- User access controls (future)
- Audit trail for file operations

## Extension Points

### Future Enhancements Ready
1. **Database Backend**: Replace file storage with PostgreSQL
2. **Web API**: REST endpoints for external integration
3. **Real-time Processing**: Stream processing for live data
4. **Machine Learning**: Pattern recognition and anomaly detection
5. **Distributed Processing**: Multi-node processing for large datasets

### Plugin Architecture (Future)
```python
class AnalysisPlugin:
    """Base class for analysis plugins."""
    def analyze(self, data: pl.DataFrame) -> Dict[str, Any]:
        pass
    
    def get_required_columns(self) -> List[str]:
        pass
```

---

*This guide covers the essential patterns and procedures for developing with the Battery Data Analyzer system. For project status and current implementation details, see project_status.md.*