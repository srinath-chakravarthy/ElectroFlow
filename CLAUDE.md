# Battery Data Analyzer - Active Development Guide

## Current Status

**✅ COMPLETED**: Universal data processing system with VersaStudio support, fundamental analytics, cell-based storage, and CLI interface. See `project_status.md` for full implementation details.

**🎯 CURRENT FOCUS**: System refinement, BioLogic parser, and user grouping system.

## Active Work Instructions

### Universal Schema Reference (For Development)

**32-Column Universal Schema** (Always maintain compatibility):
```python
UNIVERSAL_COLUMNS = [
    # Core Time & Indexing (6 columns)
    'time_s', 'timestamp', 'segment_number', 'point_number', 'loop_number', 'battery_cycle',
    
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
    'ce_potential_v', 'cell_potential_v', 'ac_amplitude_v', 'aux_voltage_v',
    
    # Technique Tracking (2 columns)
    'technique_name', 'fundamental_technique'
]
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

## Immediate Development Priorities

### 1. Diagnostic and Validation Tools
**Status**: In Progress  
**Priority**: High

Create validation plots and diagnostic tools:
- ActionId vs Segment# mapping plots with technique coloring
- Analytics accuracy validation (compare with known results)
- EIS frequency range investigation (currently showing 0 Hz)
- Performance profiling for large files

### 2. Extended Technique Classification
**Status**: Ready to Start  
**Priority**: High

Expand technique mapping based on real data:
- Analyze technique names from user files
- Add variants to TECHNIQUE_MAPPING
- Improve classification accuracy
- Handle edge cases and compound techniques

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