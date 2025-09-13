# BioLogic Technique Mapping Architecture Documentation

**Document Status**: Implementation Planning  
**Date**: September 4, 2025  
**Implementation**: BioLogic Sequence-to-Segment Conversion System  
**Priority**: Next Session Development Focus

## Overview

Architectural design for implementing BioLogic technique mapping that converts composite BioLogic techniques (GCPL, GEIS, etc.) into fundamental electrochemical segments compatible with our registry-driven analysis system. Addresses the core challenge of mapping BioLogic's complex parameter sequences to our database's 5 fundamental techniques.

## Problem Statement

### **The BioLogic Challenge**
BioLogic instruments use "composite techniques" that contain multiple fundamental operations:

```python
# BioLogic Composite Techniques
GCPL (0x04): Galvanostatic charge + Rest + Galvanostatic discharge + Rest
GEIS (0x1E): Galvanostatic stabilization + EIS measurement (repeated)
PEIS (0x1D): Potentiostatic stabilization + EIS measurement (repeated)
BCD (0x88):  Multiple charge/discharge cycles with various conditions

# Our Database Expects
Fundamental_Techniques = {
    1: "Galvanostatic",
    2: "Potentiostatic", 
    3: "EIS",
    4: "CV", 
    5: "Rest"
}
```

### **Current Status**
- ✅ **Binary parsing implemented** - MPRReader extracts raw data
- ✅ **Universal schema mapping** - Basic column conversion working
- ✅ **Timestamp extraction** - OLE timestamps and absolute time calculation
- ❌ **Technique mapping missing** - No sequence-to-segment conversion

## Architectural Design

### **File Organization Strategy**

#### **New File Structure**
```
src_clean/parsers/configs/
├── biologic_techniques.py      # Parameter parsing definitions (from YADG)
├── biologic_mappings.py        # Column mappings (existing)
└── universal_schema.py         # Universal schema (existing)

src_clean/parsers/
├── mpr_reader.py              # Pure binary parser (extracted from biologic.py)
├── biologic.py                # Integration layer + technique interpretation
└── base.py                    # Parser base classes (existing)
```

#### **Responsibility Distribution**

**`mpr_reader.py` - Pure Binary Parser**:
```python
class MPRReader:
    def parse_mpr_file(self, file_path) -> tuple[pl.DataFrame, dict, list]:
        # Binary module processing (VMP Set, VMP data, VMP LOG)
        # Technique ID extraction from settings module
        # Parameter sequence parsing using biologic_techniques.py
        # Raw data extraction and timestamp processing
        return raw_data, technique_metadata, parameter_sequences
```

**`biologic.py` - Integration & Interpretation Layer**:
```python
class BiologicParser:
    def _convert_sequences_to_segments(self, technique, params, raw_data):
        # Technique-specific interpretation logic
        # Parameter analysis → fundamental operation classification
        # Segment boundary generation from loop module data
        # Mapping to database technique_id (1-5)
        return segments_with_fundamental_techniques
```

### **Parameter Extraction Workflow**

Based on YADG's proven approach in `mpr.py`:

#### **Step 1: Technique Identification**
```python
# Extract from settings module byte 0x0000
technique_id = data[0x0000]  # e.g., 0x04 = GCPL
technique, params_dtypes = technique_params_dtypes[technique_id]
```

#### **Step 2: Parameter Location Discovery**
```python
# Try multiple possible offsets for parameter storage
offsets = (0x0572, 0x1845, 0x1846, 0x1847)
for offset in offsets:
    n_params = np.frombuffer(data, offset=offset + 0x0002, dtype="<u2", count=1)[0]
    # Match with technique's expected parameter structure
    if len(technique_dtype) == n_params:
        params_offset = offset
        break
```

#### **Step 3: Sequence Extraction**
```python
# Get number of parameter sequences (ns)
ns = np.frombuffer(data, offset=params_offset, dtype="<u2", count=1)[0]

# Extract all sequences using technique-specific data types
rawparams = np.frombuffer(
    data, offset=params_offset + 0x0004, 
    dtype=params_dtype, count=ns
)
```

#### **Step 4: Parameter Dictionary Creation**
```python
# Convert to structured parameter data
params = {
    "Is": [2.0, 0.0, -2.0, 0.0],           # Current values for each sequence
    "t1 (h:m:s)": [1800, 1800, 1800, 1800], # Duration for each sequence  
    "EM (V)": [4.2, 0, 2.5, 0],            # Voltage limits
    # ... all other technique-specific parameters
}
```

## Technique Interpretation Logic

### **GCPL Example: Battery Cycling**
```python
def interpret_gcpl_sequences(params) -> list[dict]:
    segments = []
    ns = len(params["Is"])  # Number of sequences
    
    for i in range(ns):
        current = params["Is"][i]
        duration = params["t1 (h:m:s)"][i] * 3600  # Convert to seconds
        
        if current != 0:
            # Active galvanostatic step
            segments.append({
                'sequence_index': i,
                'technique_id': 1,  # Galvanostatic
                'current_a': current,
                'duration_s': duration,
                'voltage_limit': params["EM (V)"][i],
                'biologic_source': 'GCPL_charge_discharge'
            })
        else:
            # Rest period
            segments.append({
                'sequence_index': i,
                'technique_id': 5,  # Rest
                'duration_s': duration,
                'biologic_source': 'GCPL_rest'
            })
    
    return segments

# Result: GCPL → [Galvanostatic, Rest, Galvanostatic, Rest] segments
```

### **GEIS Example: Galvanostatic EIS**
```python
def interpret_geis_sequences(params) -> list[dict]:
    segments = []
    
    # Galvanostatic stabilization step
    if params["tIs (h:m:s)"][0] > 0:
        segments.append({
            'technique_id': 1,  # Galvanostatic
            'current_a': params["Is"][0],
            'duration_s': params["tIs (h:m:s)"][0] * 3600,
            'biologic_source': 'GEIS_stabilization'
        })
    
    # EIS measurement step
    segments.append({
        'technique_id': 3,  # EIS
        'freq_start': params["fi"][0],
        'freq_end': params["ff"][0],
        'points': params["Nd"][0],
        'biologic_source': 'GEIS_measurement'
    })
    
    return segments

# Result: GEIS → [Galvanostatic, EIS] segments (repeated for each measurement point)
```

## Implementation Phases

### **Phase 1: File Restructuring**
**Objective**: Clean architectural separation

**Tasks**:
1. Copy `yadg/techniques.py` → `src_clean/parsers/configs/biologic_techniques.py`
2. Extract `MPRReader` class → `src_clean/parsers/mpr_reader.py`
3. Update imports and dependencies in `biologic.py`
4. Verify existing functionality still works

**Expected Outcome**: Clean separation between binary parsing and interpretation logic.

### **Phase 2: Parameter Extraction Enhancement**
**Objective**: Extract structured technique parameters

**Tasks**:
1. Integrate YADG parameter parsing logic into MPRReader
2. Add technique identification from settings module
3. Implement parameter sequence extraction (ns sequences)
4. Return structured parameter data alongside raw measurements

**Expected Outcome**: MPRReader provides technique metadata and parameter sequences.

### **Phase 3: Technique Interpretation Implementation**
**Objective**: Convert parameter sequences to fundamental segments

**Tasks**:
1. Build technique-specific interpretation functions (GCPL, GEIS, PEIS, etc.)
2. Analyze parameter sequences to classify fundamental operations
3. Generate segment boundaries with proper technique_id mapping
4. Integrate with loop module data for cycle detection

**Expected Outcome**: BioLogic composite techniques converted to database-compatible segments.

### **Phase 4: System Integration**
**Objective**: Full compatibility with existing analysis framework

**Tasks**:
1. Update universal schema mapping to handle segmented data
2. Validate database storage of segmented BioLogic data
3. Test registry system compatibility with new segment structure
4. Performance validation with real BioLogic files

**Expected Outcome**: Complete BioLogic technique support with registry-driven analysis capabilities.

## Database Integration Strategy

### **Segment Storage Enhancement**
```sql
-- Enhanced segments table to support BioLogic source tracking
ALTER TABLE segments ADD COLUMN biologic_source VARCHAR(50);
ALTER TABLE segments ADD COLUMN sequence_index INTEGER;
ALTER TABLE segments ADD COLUMN parent_technique VARCHAR(10);

-- Example data
INSERT INTO segments (technique_id, biologic_source, sequence_index, parent_technique)
VALUES 
    (1, 'GCPL_charge', 0, 'GCPL'),
    (5, 'GCPL_rest', 1, 'GCPL'),
    (1, 'GCPL_discharge', 2, 'GCPL'),
    (5, 'GCPL_rest', 3, 'GCPL');
```

### **Registry Compatibility**
```python
# Registry system will work seamlessly
registry.get_analysis('kinetics_analysis').get_compatible_segments()
# Returns: [segments with technique_id=1] (galvanostatic segments only)

registry.get_analysis('equilibrium_analysis').get_compatible_segments()  
# Returns: [segments with technique_id=5] (rest segments only)

registry.get_analysis('impedance_analysis').get_compatible_segments()
# Returns: [segments with technique_id=3] (EIS segments only)
```

## Validation Strategy

### **Parameter Extraction Validation**
- Compare extracted parameters with EC-Lab original technique settings
- Validate sequence count (ns) matches expected experiment design
- Verify parameter units and value ranges

### **Segment Classification Validation**
- Manual review of technique interpretation for known BioLogic experiments
- Cross-reference with original EC-Lab technique sequences
- Validate fundamental technique assignment accuracy

### **System Integration Validation**
- End-to-end testing with real BioLogic MPR files
- Database storage and retrieval validation
- Registry-driven analysis compatibility testing
- Performance benchmarking with large BioLogic datasets

## Current Status and Next Steps

### **✅ Completed Foundation**
- Binary MPR parsing with YADG integration
- Universal schema with 9-column electrode enhancement
- OLE timestamp extraction and absolute time calculation
- Basic BioLogic column mapping

### **✅ COMPLETED: Phase 1 - File Restructuring** 
**Status**: Complete with architectural clean separation achieved

**Completed Tasks**:
1. ✅ Copy and adapt `biologic_techniques.py` from YADG → `src_clean/parsers/configs/biologic_techniques.py`
2. ✅ Extract MPRReader to separate module → `src_clean/parsers/mpr_reader.py` (pure binary parser)
3. ✅ Update BiologicParser to use external MPRReader → `src_clean/parsers/biologic.py` (integration layer)
4. ✅ Validate basic functionality preservation → BiologicParser imports and instantiates successfully

**Architecture Benefits Achieved**:
- Clean separation between binary parsing (MPRReader) and domain logic (BiologicParser)
- Maintainable design with technique interpretation logic ready for extension
- Testable components with each layer independently unit testable
- YADG integration preserved with proven parameter parsing logic available

### **💡 STRATEGIC DECISION: Combined Phase 2 Implementation**
**Decision**: Combine column mapping fix with Phase 2 technique mapping for more efficient development.

**Rationale**:
- **Efficiency**: Avoid duplicate work - fixing column mapping now then changing again for technique mapping
- **Architecture**: Technique mapping will require changes to column processing anyway
- **Cohesion**: Column mapping can be designed with technique parameter context from the start
- **Development Flow**: Cleaner progression from architectural separation to full implementation

### **⚠️ KNOWN ISSUE: Column Mapping Logic** 
**Current State**: MPRReader produces `unknown_*` columns instead of proper BioLogic names (`time`, `Ewe`, `I`)

**Technical Root Cause**: Column ID mapping from YADG `biologic_mappings` not properly integrated in restructured architecture.

**Resolution Strategy**: Will be addressed comprehensively in Phase 2 alongside technique mapping implementation.

### **🎯 ENHANCED PHASE 2: Column Mapping + Technique Mapping**
**Expanded Scope**: Combined implementation for maximum efficiency and architectural coherence

**Enhanced Phase 2 Tasks**:
1. **Fix Column Mapping**: Resolve `unknown_*` columns → proper BioLogic column names
2. **Parameter Extraction**: Integrate YADG technique parameter parsing logic  
3. **Technique Identification**: Extract technique ID and parameter sequences from settings module
4. **Column Context Integration**: Design column mapping with technique parameter awareness

**Expected Outcome**: Fully functional BioLogic parser with proper column names AND technique parameter extraction ready for Phase 3 sequence-to-segment conversion.

### **🚀 Future Development Path**
- Phase 2: Parameter extraction and technique identification
- Phase 3: Sequence-to-segment interpretation logic
- Phase 4: Full system integration and validation

## Benefits and Impact

### **Enhanced Analysis Capabilities**
- **Technique-Aware Analysis**: Registry system can filter BioLogic data by fundamental technique type
- **Precise Segmentation**: Individual charge/discharge/rest phases properly isolated
- **Cross-Instrument Compatibility**: BioLogic data works with VersaStudio-designed analysis functions
- **Battery Cycling Support**: Proper cycle detection and phase classification

### **System Architecture Improvements**
- **Clean Separation**: Binary parsing vs. domain logic separation
- **Maintainable Design**: Technique interpretation logic easily extensible
- **Testable Components**: Each layer can be unit tested independently
- **Performance Scalable**: Efficient parameter extraction for large BioLogic datasets

## Conclusion

**Implementation Status**: Architecture designed, ready for Phase 1 implementation in next session.

**Critical Success Factors**:
1. Proper separation between binary parsing and technique interpretation
2. Accurate parameter extraction using YADG-proven methods
3. Intelligent sequence classification based on parameter analysis
4. Seamless integration with existing registry-driven analysis system

**The proposed architecture provides a robust foundation for converting BioLogic's complex composite techniques into our database's fundamental technique classification, enabling full compatibility with the existing analysis registry while preserving the rich experimental detail from BioLogic instruments.**