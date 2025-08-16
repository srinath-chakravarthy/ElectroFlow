# Implementation Guide - Battery Data Analyzer

**Target Audience**: Developers working on the battery data analyzer system  
**Last Updated**: August 16, 2025

## System Overview

The Battery Data Analyzer follows a modular architecture with clear separation between parsing, analytics, storage, and user interfaces. The system is designed for extensibility to support multiple instrument types while maintaining a universal data schema.

## Code Organization

### Core Architecture
```
src/
├── core/                   # Data models and parsing
│   ├── data_models.py     # Universal schema, DataFile class
│   ├── parsers.py         # VersaStudio parser implementation  
│   └── parser_factory.py # Multi-instrument parser framework
├── analysis/              # Analytics engine
│   └── analytics.py       # Fundamental analytics (CC, REST, EIS, etc.)
├── io_utils/              # Storage and file management
│   └── storage.py         # Cell-based storage manager
├── utils/                 # Shared utilities
└── visualization/         # Plotting and visualization
```

### Key Design Patterns

**1. Parser Strategy Pattern**
- `BaseParser` abstract class defines common interface
- Instrument-specific parsers (`VersaStudioParser`) implement `parse()` method
- `ParserFactory` handles automatic parser selection

**2. Universal Schema Conversion**
- All parsers output to same 32-column universal schema
- Instrument-specific mapping functions handle column translation
- Missing columns filled with appropriate null values

**3. Pipeline Architecture**
- Clear separation: Parse → Analyze → Store
- Each stage is independent and testable
- Error handling at each stage with graceful degradation

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
    technique: str                    # Technique name
    action_id: int                   # ActionId from data
    results: Dict[str, Any]          # Numerical results
    quality_metrics: Dict[str, float] # Quality indicators (R², completeness)
    fitted_data: Optional[Dict]       # Curve fitting data for plots
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