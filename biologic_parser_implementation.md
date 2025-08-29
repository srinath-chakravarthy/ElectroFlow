# BioLogic EC-Lab Parser Implementation Plan for Claude Code

## **Project Overview**
Add BioLogic EC-Lab (.mpr, .mpt, .mps) parser support to existing electrochemical data analysis suite, maintaining all existing code patterns and architecture principles.

## **Pre-Implementation Research Tasks**

### **Task 1: Analyze Inspiration Sources**
**Objective**: Study yadg and eclabfiles implementations to understand BioLogic file structure
**Focus Areas**:
- Binary .mpr module structure (settings, data, log, loop modules)
- Column ID mapping systems from yadg.extractors.eclab.mpr_columns
- Technique parameter extraction patterns
- OLE timestamp conversion methods
- Error handling for missing log modules

**Key Files to Study**:
- `yadg/extractors/eclab/mpr.py` - Binary parsing logic
- `yadg/extractors/eclab/mpt.py` - Text parsing logic  
- `yadg/extractors/eclab/techniques.py` - Technique parameter definitions
- `yadg/extractors/eclab/mpr_columns.py` - Column ID definitions

### **Task 2: Map Universal Schema Compatibility**
**Objective**: Determine how BioLogic columns map to existing 29-column universal schema
**Deliverable**: Create mapping dictionary similar to existing `VERSASTUDIO_CSV_MAPPING`

**Key BioLogic Columns to Map**:
- `time/s` → `time_s`
- `Ewe/V` → `potential_v`
- `I/mA` → `current_a` (with unit conversion)
- `<Ewe>/V` → `potential_avg_v`
- `<I>/mA` → `current_avg_a`
- `cycle number` → `battery_cycle`

## **Implementation Phases**

### **Phase 1: Core Infrastructure Setup**

#### **Task 1.1: Create BioLogic Parser Module Structure**
**Pattern**: Follow existing `src_clean/parsers/versastudio.py` structure

**Files to Create**:
```
src_clean/parsers/biologic/
├── __init__.py
├── base.py                    # BioLogic-specific base classes
├── mpr_parser.py             # Binary .mpr file parser  
├── mpt_parser.py             # Text .mpt file parser
├── timestamp_resolver.py     # Timestamp resolution logic
└── configs/
    ├── __init__.py
    ├── biologic_mappings.py    # Universal schema mappings
    ├── technique_dtypes.py     # Binary parsing data types
    └── column_definitions.py   # Column ID definitions
```

**Code Patterns to Follow**:
- Inherit from existing base classes (`BaseParser`, `DualFileParser`, `SingleFileParser`)
- Use same method signatures as `VersaStudioParser`
- Follow same validation patterns with `_validate_file_exists()`, `_safe_read_file()`
- Use same error handling with `DataParsingError`, `MetadataExtractionError`

#### **Task 1.2: Implement Timestamp Resolution System**
**Pattern**: Follow existing error handling and logging patterns

**Key Components**:
```python
class TimestampResolutionResult:
    timestamp: datetime
    source: Literal['ole_log', 'mpt_header', 'file_mtime', 'current_time']  
    confidence: Literal['high', 'medium', 'low', 'fallback']
    warnings: List[str]

def resolve_timestamp(self, file_path: Path, log_data: Optional[dict], 
                     mpt_header: Optional[dict]) -> TimestampResolutionResult:
    # Implement 4-tier fallback system with user warnings
```

**Integration Points**:
- Extend existing `FileMetadata` dataclass with timestamp fields
- Add logging using existing `logger` pattern
- Store warnings for API surface

#### **Task 1.3: Create Column Mapping Configuration**
**Pattern**: Mirror `versastudio_mappings.py` structure

**Implementation**:
```python
# biologic_mappings.py
BIOLOGIC_COLUMN_MAPPING = {
    'time/s': ('time_s', 's', pl.Float64),
    'Ewe/V': ('potential_v', 'V', pl.Float64),
    'I/mA': ('current_a', 'A', pl.Float64, lambda x: x / 1000),  # Unit conversion
    # ... complete mapping
}

BIOLOGIC_TO_UNIVERSAL_SCHEMA = {
    # Direct column mappings with unit conversions
}
```

### **Phase 2: Binary .mpr Parser Implementation**

#### **Task 2.1: Module-Based Binary Parser**
**Pattern**: Follow existing file reading and validation patterns from `VersaStudioParser`

**Core Parser Structure**:
```python
class MPRParser:
    def parse_mpr_file(self, file_path: Path) -> DataFile:
        # 1. Validate file format
        # 2. Read binary content
        # 3. Split into modules
        # 4. Process each module type
        # 5. Convert to universal schema
        
    def split_modules(self, binary_data: bytes) -> Dict[str, bytes]:
        # Split on 'MODULE' keyword, parse headers
        
    def process_settings_module(self, data: bytes) -> dict:
        # Extract technique_id, comments, cell characteristics
        # Parse technique parameters at variable offsets
        
    def process_data_module(self, data: bytes) -> pl.DataFrame:
        # Parse column_ids, convert binary data to DataFrame
        
    def process_log_module(self, data: bytes) -> dict:
        # Extract OLE timestamp, device info, software versions
        
    def process_loop_module(self, data: bytes) -> dict:
        # Extract loop indexes and iteration counts
```

#### **Task 2.2: Column ID System Implementation**
**Pattern**: Use existing lookup table patterns

**Implementation Strategy**:
- Study yadg's column ID definitions extensively
- Create lookup tables for column names, data types, units
- Handle flag columns (multiple values packed in single byte)
- Implement dtype arrays for binary data parsing

#### **Task 2.3: Technique Parameter Extraction**
**Pattern**: Follow existing ActionID mapping approach from VersaStudio

**Implementation**:
```python
TECHNIQUE_DTYPES = {
    'OCV': np.dtype([('param1', '<f4'), ('param2', '<u2')]),
    'CV': np.dtype([...]),
    'GCPL': [np.dtype([...]), np.dtype([...])],  # Variable parameters
    # Based on yadg technique definitions
}

def extract_technique_params(self, settings_data: bytes, technique_id: int):
    # Parse parameters at variable offsets (0x1845, 0x1846, 0x0572)
    # Use technique-specific dtypes for binary parsing
```

### **Phase 3: Text .mpt Parser Implementation**

#### **Task 3.1: Header-Based Text Parser**  
**Pattern**: Follow existing CSV parsing patterns from VersaStudio

**Core Structure**:
```python
class MPTParser:
    def parse_mpt_file(self, file_path: Path) -> DataFile:
        # 1. Read and split header/data sections
        # 2. Process header for metadata and technique params
        # 3. Parse data section as CSV-like format
        # 4. Extract timestamp information
        # 5. Convert to universal schema
        
    def process_header(self, header_lines: List[str]) -> dict:
        # Extract settings, technique parameters, loop info
        # Parse acquisition timestamps (with export date warning)
        
    def parse_data_section(self, data_lines: List[str]) -> pl.DataFrame:
        # CSV parsing with locale-aware number parsing
        # Handle technique-specific columns
```

#### **Task 3.2: .mpt Timestamp Extraction**
**Pattern**: Follow existing regex-based metadata extraction

**Implementation**:
- Multiple timestamp format patterns
- Export date vs acquisition date detection
- Integration with timestamp resolution system
- Appropriate user warnings

### **Phase 4: Universal Schema Integration**

#### **Task 4.1: Schema Conversion Implementation**
**Pattern**: Mirror existing `_parse_csv_data()` conversion logic

**Implementation**:
```python
def convert_to_universal_schema(self, biologic_df: pl.DataFrame, 
                              metadata: FileMetadata) -> DataFile:
    # 1. Apply column mappings with unit conversions
    # 2. Calculate missing universal columns
    # 3. Process loops/segments for battery cycling
    # 4. Add technique-specific calculations
    # 5. Use existing add_missing_universal_columns()
```

#### **Task 4.2: Loop/Segment Processing**
**Pattern**: Follow existing segment processing logic

**Focus Areas**:
- Convert BioLogic loop structures to segment_number system
- Handle nested loops and technique sequences  
- Generate battery_cycle numbers for cycling techniques
- Maintain compatibility with existing analytics

#### **Task 4.3: Battery-Specific Calculations**
**Pattern**: Use existing integration patterns from VersaStudio

**Implementation**:
- Capacity/energy integration for cycling techniques
- Power calculations
- Cumulative tracking across segments
- Temperature handling

### **Phase 5: Parser Factory Integration**

#### **Task 5.1: Multi-Format Parser Registration**
**Pattern**: Follow existing `VersaStudioParser` registration

**Implementation**:
```python
class BiologicParser(BaseParser):  # Choose appropriate base class
    def get_instrument_name(self) -> str:
        return "BioLogic"
    
    def get_supported_extensions(self) -> List[str]:
        return ['.mpr', '.mpt', '.mps']
    
    def validate_file(self, file_path: Path) -> bool:
        # Check file signatures:
        # .mpr: "BIO-LOGIC MODULAR FILE"
        # .mpt: Header structure validation
        
    def parse_data(self, file_path: Path) -> DataFile:
        # Route to appropriate parser based on extension
        # Priority: .mpr > .mpt > .mps
```

#### **Task 5.2: Auto-Detection Enhancement**
**Pattern**: Extend existing factory detection logic

**Integration**:
- Add BioLogic signature detection to `detect_instrument()`
- Handle companion file discovery (.mpr/.mpt pairs)
- Maintain existing parser priority system

#### **Task 5.3: Registration and Testing**
**Pattern**: Follow existing parser registration

**Implementation**:
```python
# In parsers/__init__.py
from .biologic import BiologicParser
register_parser(BiologicParser)

# Test with existing convenience functions
auto_parse_file(Path("test.mpr"))
auto_parse_dual_files(Path("test.mpt"), Path("test.mpr"))
```

### **Phase 6: Error Handling and Validation**

#### **Task 6.1: Comprehensive Error Handling**
**Pattern**: Use existing exception hierarchy

**Error Types**:
- Missing log module warnings (ExtDev files)
- Unknown technique parameter handling
- Binary parsing failures
- Timestamp resolution warnings

#### **Task 6.2: File Validation Enhancement**
**Pattern**: Follow existing validation patterns

**Validations**:
- File format signatures
- Module structure integrity  
- Column ID validity
- Data consistency checks

#### **Task 6.3: User Warning System Integration**
**Pattern**: Extend existing API response structure

**Integration Points**:
- Surface timestamp warnings in API responses
- Add batch upload validation
- Provide chronology guidance
- Enhance frontend warning display

## **Implementation Guidelines**

### **Code Patterns to Follow**
1. **Class Structure**: Mirror `VersaStudioParser` hierarchy and method signatures
2. **Error Handling**: Use existing exception types and logging patterns  
3. **Configuration**: Follow existing mapping file structures
4. **Testing**: Use existing test patterns with synthetic data creation
5. **API Integration**: Maintain compatibility with existing endpoints

### **Key Architectural Principles**
1. **Parser Factory Pattern**: Seamless integration with existing auto-detection
2. **Universal Schema**: All output must conform to 29-column schema
3. **Metadata Consistency**: Use existing `FileMetadata` structure with extensions
4. **Database Compatibility**: Maintain existing storage patterns
5. **API Backwards Compatibility**: No breaking changes to existing endpoints

### **Quality Assurance**
1. **Incremental Testing**: Test each phase independently
2. **VersaStudio Compatibility**: Ensure no regression in existing functionality
3. **Real Data Validation**: Test with actual BioLogic files from multiple techniques
4. **Performance Monitoring**: Binary parsing should be efficient for large files
5. **User Experience**: Clear warnings and guidance for timestamp issues

## **Success Criteria**
- [ ] Parse .mpr binary files with all major techniques (OCV, CV, GCPL, GEIS, PEIS)
- [ ] Parse .mpt text files as fallback
- [ ] Convert all data to universal 29-column schema  
- [ ] Maintain absolute timestamps when available with appropriate warnings
- [ ] Integrate seamlessly with existing parser factory and API
- [ ] Handle missing log modules gracefully
- [ ] Provide clear user guidance for chronology issues
- [ ] No performance regression on existing VersaStudio functionality

## **Risk Mitigation**
1. **Complex Binary Format**: Extensive study of yadg implementation first
2. **Multiple File Types**: Implement incrementally starting with .mpr
3. **Timestamp Issues**: Clear user communication and fallback strategies  
4. **Performance**: Profile binary parsing on large files
5. **Compatibility**: Thorough testing with existing codebase integration

This implementation plan provides Claude Code with specific, actionable tasks while maintaining the existing codebase patterns and architecture principles.