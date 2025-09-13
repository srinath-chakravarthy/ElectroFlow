# Parser Architecture - Universal Schema Processing

**Status:** Production Ready | **Updated:** September 12, 2025

## Overview

The parser architecture converts instrument-specific file formats into a standardized 47-column universal schema, enabling instrument-agnostic electrochemical analysis.

## Universal Schema Design

### Philosophy
- **Instrument Agnostic**: Same columns regardless of source instrument
- **Explicit Units**: Every column has defined units (V, A, Ah, Wh, etc.)
- **Type Safety**: Polars DataFrame validation with strict typing
- **Physics Integration**: Units enable automatic physics calculations

### Schema Structure (47 Columns)

#### Time & Indexing (6 columns)
- `time_s`: Relative time from experiment start
- `timestamp`: Absolute timestamp (ISO8601)
- `segment_number`: Experimental segment index
- `point_number`: Point within segment
- `loop_number`: Loop iteration
- `battery_cycle`: Battery cycle number

#### Electrochemical Core (6 columns)
- `potential_v`: Working electrode potential (cell potential)
- `current_a`: Measured current
- `potential_applied_v`: Applied potential setpoint
- `current_applied_a`: Applied current setpoint
- `potential_avg_v`: Average potential
- `current_avg_a`: Average current

#### Battery Analytics (4 columns)
- `capacity_ah`: Segment capacity integration
- `energy_wh`: Segment energy integration
- `power_w`: Instantaneous power
- `temperature_c`: Temperature

#### Cumulative Tracking (8 columns)
Cross-file experiment tracking:
- `capacity_cumulative_ah`: File-level cumulative capacity
- `energy_cumulative_wh`: File-level cumulative energy
- `charge_cumulative_ah`: Positive capacity cumulative
- `discharge_cumulative_ah`: Negative capacity cumulative
- Plus energy equivalents and absolute tracking

#### EIS Support (5 columns)
- `frequency_hz`: Frequency
- `impedance_real_ohm`: Real impedance
- `impedance_imag_ohm`: Imaginary impedance
- `impedance_mag_ohm`: Magnitude impedance
- `impedance_phase_deg`: Phase

#### Electrode-Specific (9 columns)
Enhanced BioLogic support:
- `working_electrode_potential_v`: WE potential vs reference
- `we_impedance_*`: Working electrode impedance components
- `ce_impedance_*`: Counter electrode impedance components

#### Status & Advanced (8 columns)
- `current_range`: Current range setting
- `potential_range`: Potential range setting
- `mode`: Measurement mode
- `technique_id`: ActionID/Technique identifier
- `status_flags`: Status flags
- Plus auxiliary measurements

## Parser Implementations

### BioLogic Parser (.mpr files)

#### Architecture
```python
MPRReader (Binary Parser) → BiologicParser (Integration) → Universal Schema
     ↓                           ↓                              ↓
YADG-compatible              Enhanced segmentation        47-column output
Binary decoding              Mode-aware mapping           Type validation
```

#### Key Features

**Mixed-Mode Segmentation:**
- **Enhanced Logic**: Splits on Ns changes OR mode transitions
- **Pure Segments**: CC-CV techniques split into separate segments
- **Example**: Segment with modes [1,2] → Galvanostatic segment + Potentiostatic segment

**Mode-Aware Current Mapping:**
```python
# Priority system with technique awareness
current_a = (
    I * 1e-3                    if I_available           # MB: measured current
    else control_I * 1e-3       if control_I_available   # GCPL: applied current  
    else <I> * 1e-3             if <I>_available         # EIS: AC current
    else 0.0                                             # OCV: no current
)
```

**Rest Phase Logic:**
- Uses `control_I` (0.0) instead of measured drift
- Eliminates instrumentation artifacts (µA noise)
- Electrochemically meaningful data

**Technique Support:**
- **MB (Modulo Bat)**: Full mixed-mode support
- **GCPL**: Pure galvanostatic cycling
- **PEIS/GEIS**: EIS with AC current mapping
- **OCV**: Open circuit voltage (no current)

#### Implementation Details

**Segmentation Logic:**
```python
# Enhanced segmentation: Ns + Mode transitions
segment_change = ns_change | mode_change
segment_number = segment_change.cumsum()
```

**Current Mapping:**
```python
# Mode-aware fallback system
if mode == 3:  # Rest
    current_a = control_I * 1e-3  # Use enforced control (0.0)
else:  # Galvanostatic/Potentiostatic
    current_a = I * 1e-3 if available else control_I * 1e-3
```

### VersaStudio Parser (.par + .par.csv files)

#### Architecture  
```python
DualFileParser → ActionID Mapping → Universal Schema
      ↓               ↓                    ↓
.par metadata    Technique classification  47-column output
.par.csv data    Loop expansion           Type validation
```

#### Key Features

**Dual File System:**
- `.par`: Experimental metadata and parameters
- `.par.csv`: Calibrated measurement data
- **Validation**: Ensures file pair consistency

**ActionID Mapping:**
- `23 → rest`: Rest/equilibration phases
- `20 → eis`: Electrochemical impedance spectroscopy
- `8 → cc`: Galvanostatic (constant current)
- Plus comprehensive technique coverage

**Loop Expansion:**
- Handles hierarchical experimental structures
- Automatic iteration tracking
- Maintains temporal sequence

## Universal Processing Pipeline

### Processing Flow
```
1. File Detection → 2. Parser Selection → 3. Raw Processing → 4. Universal Conversion
      ↓                    ↓                   ↓                    ↓
File extension     BioLogic/VersaStudio   Instrument-specific   47-column schema
validation         parser routing         data extraction       type validation
```

### Quality Assurance
- **Type Validation**: Polars schema enforcement
- **Unit Conversion**: Automatic mA→A, etc.
- **Null Handling**: Mode-aware fallbacks eliminate NaN values
- **Cross-Validation**: Consistency checks across columns

### Performance Characteristics
- **Processing Speed**: Real-time for moderate files
- **Memory Usage**: Polars-optimized DataFrames
- **Scalability**: Linear scaling to 30K+ segments
- **Error Handling**: Graceful degradation with informative messages

## Integration Points

### Database Integration
- **Automatic Storage**: Processed data flows to SQLite
- **Cross-File Tracking**: Cumulative metrics across experiments
- **Metadata Preservation**: Original file information maintained

### Analytics Integration
- **Registry System**: Universal schema enables auto-discovery
- **Physics Calculations**: Units enable automatic computation
- **Expert Algorithms**: Standardized data for intelligent analysis

### Multi-Interface Support
- **Web Interface**: Direct DataFrame visualization
- **CLI Access**: Processed data for command-line analytics
- **Python API**: Universal schema for programmatic access
- **Jupyter**: Native DataFrame integration

---
**The parser architecture provides robust, scalable conversion from instrument formats to universal schema, enabling comprehensive electrochemical analysis across multiple platforms.**