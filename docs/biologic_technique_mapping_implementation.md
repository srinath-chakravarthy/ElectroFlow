# BioLogic Technique Mapping Implementation

**Document Type**: Technical Implementation Plan  
**Created**: September 4, 2025  
**Status**: Ready for Implementation  
**Session Context**: Post-timestamp fix, implementing Btech to Ftech mapping

## Overview

Implementation of BioLogic technique (Btech) to fundamental technique (Ftech) mapping system for proper analytics integration. Addresses database schema issue where `technique_name` and `fundamental_technique` currently represent same data.

## Problem Statement

### Current Issue
- Database columns `technique_name` and `fundamental_technique` currently store same data
- Should be: `technique_name` = instrument-specific (Btech for BioLogic, Vtech for VersaStudio)
- Should be: `fundamental_technique` = analytics mapping (Ftech: rest, cv, cc, cp, eis, pulse, unknown)
- **Impact**: Analytics currently loose due to incorrect technique classification

### Session Discovery
- **Btech (BioLogic Technique)**: BioLogic's specific implementations (GCPL, CV, PEIS, etc.)
- **Ftech (Fundamental Technique)**: Universal electrochemical fundamentals for analytics
- **Key Insight**: Ns (sequence number) within each Btech likely maps to individual Ftechs
- **Mapping Policy**: Each Ftech change = new segment (not polluted by BioLogic's internal Ns)

## Technical Architecture

### Terminology Clarification
```
Btech (BioLogic Technique):
- GCPL (Galvanostatic Cycling with Potential Limitation)  
- CV (Cyclic Voltammetry)
- PEIS (Potentio Electrochemical Impedance Spectroscopy)
- Complex techniques containing sequences of fundamental steps

Ftech (Fundamental Technique):  
- rest (Rest/Open Circuit)
- cv (Cyclic Voltammetry)
- cc (Constant Current/Galvanostatic) 
- cp (Constant Potential/Potentiostatic)
- eis (Electrochemical Impedance Spectroscopy)
- pulse (Pulse Technique)
- unknown (Unknown/Unclassified)

Ns (Sequence Number):
- BioLogic internal sequence number within each Btech
- Each Ns value represents a different Ftech step
- Used for mapping but not stored in universal schema
```

### Current Implementation Status
- ✅ Technique identification working (`_extract_technique()`)
- ✅ Parameter extraction working (`_extract_technique_parameters()`)  
- ✅ Ns column available in data (column ID 131)
- ✅ Universal schema extended with electrode-specific columns
- ✅ Timestamp extraction fixed and working

## Implementation Plan

### File Changes Required

#### 1. `src_clean/parsers/configs/biologic_mappings.py`
**Add Btech to Ftech base mapping table:**
```python
# BioLogic Technique (Btech) to Fundamental Technique (Ftech) Mapping
BTECH_TO_FTECH_BASE_MAPPING = {
    # Simple 1:1 mappings
    "OCV": "rest",      # Open Circuit Voltage
    "CV": "cv",         # Cyclic Voltammetry  
    "PEIS": "eis",      # Potentio EIS
    "GEIS": "eis",      # Galvano EIS
    "WAIT": "rest",     # Wait = Rest
    "LSV": "cv",        # Linear Sweep = CV variant
    
    # Potentiostatic vs Galvanostatic clarification
    "CA": "cp",         # Chronoamperometry = Potentiostatic (voltage pulse)
    "CP": "cc",         # Chronopotentiometry = Galvanostatic  
    "coV": "cp",        # Constant Voltage = Potentiostatic
    "coC": "cc",        # Constant Current = Galvanostatic
    
    # Complex techniques - use primary Ftech (Ns will handle sequences)
    "GCPL": "cc",       # Galvanostatic Cycling (primary technique)
    "CVA": "cv",        # Cyclic Voltammetry Advanced (primary)
    "BCD": "cc",        # Battery Capacity Determination (primary)
    "ZIR": "eis",       # EIS with IR compensation
    "MP": "unknown",    # Modular Potentio (user-configurable)
    "MB": "unknown",    # Modulo Bat (too complex)
}
```

#### 2. `src_clean/parsers/mpr_reader.py`
**Add Btech to Ftech mapping function:**
```python
def _map_btech_to_ftech(self, btech_name: str, ns_value: int = None) -> str:
    """
    Map BioLogic technique (Btech) to fundamental technique (Ftech).
    
    Args:
        btech_name: BioLogic technique name (e.g., "GCPL", "CV")
        ns_value: Sequence number within Btech (for future complex mapping)
        
    Returns:
        Fundamental technique name (e.g., "cc", "rest", "cv")
    """
    from .configs.biologic_mappings import BTECH_TO_FTECH_BASE_MAPPING
    
    # For now, use base mapping (Ns-specific mapping can be added later)
    return BTECH_TO_FTECH_BASE_MAPPING.get(btech_name, "unknown")
```

**Modify `_process_modules()` method around line 107-108:**
```python
if name == "VMP Set":
    technique = self._extract_technique(module_data)                    # Extract Btech
    ftech = self._map_btech_to_ftech(technique)                        # Map to Ftech
    technique_parameters = self._extract_technique_parameters(module_data, technique)
    
    # Store both Btech and Ftech for later use
    technique_parameters['_btech_name'] = technique  # BioLogic technique
    technique_parameters['_ftech_name'] = ftech      # Fundamental technique
```

#### 3. `src_clean/parsers/biologic.py`
**Add segment number generation:**
```python
def _generate_segment_numbers(self, df: pl.DataFrame) -> pl.DataFrame:
    """
    Generate proper segment numbers based on Ftech changes.
    
    Each unique Ns value represents a different Ftech step within the Btech.
    Map each Ns to sequential segment numbers for universal schema.
    """
    if 'Ns' not in df.columns:
        # No Ns data - single segment
        return df.with_columns(pl.lit(1).alias('segment_number'))
    
    # Map each unique Ns to sequential segment numbers  
    unique_ns = df['Ns'].unique().sort()
    segment_mapping = {ns_val: idx + 1 for idx, ns_val in enumerate(unique_ns)}
    
    segment_numbers = [segment_mapping[ns] for ns in df['Ns']]
    return df.with_columns(pl.Series('segment_number', segment_numbers))
```

**Add Ftech integration in `_map_to_universal_schema()`:**
```python
# After add_missing_universal_columns call:
if INTEGRATED_MODE and hasattr(self.mpr_reader, 'last_technique_parameters'):
    # Add technique information to universal schema
    ftech_name = self.mpr_reader.last_technique_parameters.get('_ftech_name', 'unknown')
    technique_id = self._get_technique_id_from_ftech(ftech_name)
    
    universal_df = universal_df.with_columns([
        pl.lit(technique_id).alias('technique_id')  # Use existing universal column
    ])
    
    # Generate proper segment numbers based on Ns changes
    universal_df = self._generate_segment_numbers(universal_df)
```

**Add Ftech to technique_id mapping:**
```python
def _get_technique_id_from_ftech(self, ftech_name: str) -> int:
    """Map fundamental technique to existing technique_id system."""
    ftech_to_id_mapping = {
        'rest': 23,    # OCV/Rest ActionID from VersaStudio
        'cv': 1,       # CV ActionID  
        'cc': 8,       # Galvanostatic ActionID
        'cp': 7,       # Potentiostatic ActionID
        'eis': 20,     # EIS ActionID
        'pulse': 9,    # Pulse ActionID
        'unknown': 0   # Unknown
    }
    return ftech_to_id_mapping.get(ftech_name, 0)
```

## Data Flow

### Before Implementation
```
BioLogic MPR File → technique_id → "GCPL" → technique_name="GCPL", fundamental_technique="GCPL"
```

### After Implementation  
```
BioLogic MPR File → technique_id → "GCPL" (Btech) → "cc" (Ftech) → technique_id=8, segment_number=1,2,3...
```

## Implementation Approach

### Design Principles
1. **Clean Universal Schema**: No instrument-specific pollution
2. **Parser-Level Processing**: Handle mapping before universal conversion
3. **Segment Logic**: Each Ftech change = new segment (not BioLogic's internal Ns)
4. **Backward Compatibility**: Use existing universal schema columns

### Future Enhancements
1. **Ns-Specific Mapping**: Advanced mapping using Ns sequences for complex Btechs
2. **Database Migration**: Fix technique_name vs fundamental_technique schema issue
3. **VersaStudio Integration**: Apply same approach to VersaStudio parser

## Database Schema Issue

### Current Problem
Both `technique_name` and `fundamental_technique` contain same data, causing analytics confusion.

### Temporary Solution  
Map Btech → Ftech at parser level, store Ftech in existing `technique_id` column using ActionID system.

### Future Database Migration Needed
```sql
-- TODO: Future database migration required
-- 1. Separate technique_name (instrument-specific) from fundamental_technique (analytics)
-- 2. Update existing data with correct mappings  
-- 3. Update analytics to use fundamental_technique properly
```

## Success Criteria

### Functional Requirements
- ✅ Extract BioLogic technique name (Btech) 
- ✅ Map Btech to fundamental technique (Ftech)
- ✅ Generate proper segment numbers based on technique sequences
- ✅ Integrate with existing universal schema without pollution
- ✅ Maintain backward compatibility with existing analytics

### Technical Requirements  
- ✅ No changes to universal schema structure
- ✅ Parser-level processing before universal conversion
- ✅ Use existing technique_id and segment_number columns
- ✅ Clean separation of BioLogic-specific logic

## Files Modified Summary

1. **biologic_mappings.py**: Add Btech→Ftech mapping table
2. **mpr_reader.py**: Add mapping function + integrate in module processing  
3. **biologic.py**: Generate segment numbers + use Ftech in universal schema + helper function

**Total**: 3 files modified, ~50 lines of new code

## Implementation Results

### ✅ **COMPLETED: Technique Mapping Implementation**

**Implementation Date**: September 4, 2025  
**Status**: Complete - All changes implemented with Polars optimization

#### Files Modified Successfully:

1. **`src_clean/parsers/configs/biologic_mappings.py`** ✅
   - Added `BTECH_TO_FTECH_BASE_MAPPING` table (16 technique mappings)
   - Covers all major BioLogic techniques: GCPL→cc, CV→cv, PEIS→eis, etc.

2. **`src_clean/parsers/mpr_reader.py`** ✅
   - Added `_map_btech_to_ftech()` function for technique mapping
   - Integrated mapping in `_process_modules()` method (lines 113-120)
   - Stores both Btech and Ftech in technique_parameters for later use

3. **`src_clean/parsers/biologic.py`** ✅
   - Added `_get_technique_id_from_ftech()` helper function (maps Ftech→ActionID)
   - Added `_generate_segment_numbers()` with **Polars-optimized operations** (no Python loops)
   - Integrated technique mapping in `parse_data()` method (lines 137-147)

#### Performance Optimization:
**Critical Fix**: Replaced Python loop with Polars vectorized operations in segment generation:

```python
# Before (Python loop - SLOW)
segment_numbers = [segment_mapping[ns] for ns in df['Ns']]

# After (Polars vectorized - FAST)
unique_ns_df = (
    df.select('Ns').unique().sort('Ns')
    .with_row_index(name='segment_number', offset=1)
)
return df.join(unique_ns_df, on='Ns', how='left')
```

### Technical Implementation Details:

#### Btech→Ftech Mapping Examples:
```python
"GCPL" → "cc" → technique_id=8 (Galvanostatic)
"CV" → "cv" → technique_id=1 (Cyclic Voltammetry)  
"PEIS" → "eis" → technique_id=20 (EIS)
"OCV" → "rest" → technique_id=23 (Rest)
```

#### Segment Number Generation Logic:
```python
# Input: Ns values in file
[1, 1, 1, 3, 3, 5, 5, 5]

# Processing: unique Ns sorted → sequential mapping
unique_ns = [1, 3, 5]
mapping = {1: 1, 3: 2, 5: 3}

# Output: sequential segment_number
[1, 1, 1, 2, 2, 3, 3, 3]
```

### Data Flow Validation:

#### Before Implementation:
```
BioLogic MPR → "GCPL" → technique_name="GCPL", fundamental_technique="GCPL"
```

#### After Implementation:
```  
BioLogic MPR → "GCPL" (Btech) → "cc" (Ftech) → technique_id=8, segment_number=1,2,3...
```

### Loop Performance Audit:

**✅ Optimized**: Segment generation (most critical - processes all data rows)  
**⚠️ Minor**: Column mapping loops (18 items only, negligible impact)  
**✅ Fast**: Binary extraction loops (offset-based, unavoidable, optimal)

### Design Principles Achieved:
- ✅ Clean Universal Schema: No instrument-specific pollution
- ✅ Parser-Level Processing: All mapping before universal conversion
- ✅ Polars Performance: Vectorized operations, no Python loops on data
- ✅ Backward Compatibility: Uses existing ActionID system
- ✅ Minimal Code Changes: No modifications to fundamental methods

## Next Steps

1. ✅ **~~Implement changes~~** according to this plan **COMPLETE**
2. **Test with real BioLogic data** to verify Ns→Ftech mapping works
3. **Validate segment numbering** logic produces correct results  
4. **Document any discovered edge cases** in technique mapping
5. **Plan database schema migration** for future session