# VersaStudio File Format - Structural Parsing & Technique Mapping

## Overview
VersaStudio .par files contain complex hierarchical structures with loops, structural actions, and data segments. This document describes the dual mapping approach implemented for technique identification.

## File Structure Understanding

### Action Hierarchy
- **Structural Actions**: `Common`, `Loop #X` - organizational elements that don't generate data
- **Experimental Actions**: Actual measurements that generate data segments
- **ParentNode Relationships**: Define execution order and loop membership

### Loop Execution Model
- **Loop Definition**: Structural action (e.g., `Action3: Loop #1`) with `Number of Iterations`
- **Loop Children**: Experimental actions with `ParentNode=Loop #1` 
- **Execution Expansion**: Loop with 10 iterations × 4 actions = 40 data segments

## Dual Technique Mapping System

### Method 1: ActionId-Based Mapping (Primary)
**Simple, Direct, Partial Coverage**

```python
VERSASTUDIO_ACTIONID_MAPPING = {
    8: 'CC',     # Constant Current (verified)
    20: 'GEIS',  # Galvanostatic EIS (verified)  
    23: 'OCV',   # Energy Open Circuit (verified)
}
```

**Benefits:**
- Immediate technique identification
- High accuracy for known ActionIds
- Simple dictionary lookup
- Easy to expand with new data files

**Limitations:**
- Partial coverage (only verified ActionIds)
- Requires building database over time
- Unknown ActionIds fall back to hierarchy mapping

### Method 2: Hierarchy-Based Mapping (Fallback)
**Complex, Complete, Full Coverage**

**Process:**
1. **Structural Parsing**: Filter out `Common` and `Loop #X` actions
2. **Execution Sequence**: Build from ParentNode relationships
3. **Loop Expansion**: Repeat loop actions based on `Number of Iterations`
4. **Segment Mapping**: Create complete 0-based continuous mapping

**Example Execution Sequence:**
```
Top-level Actions:
  Action1 (Energy Open Circuit) → segment 0
  Action2 (Galvanostatic EIS) → segment 1

Loop #1 (10 iterations):
  Action4 (Constant Current) → segments 2, 6, 10, 14, 18, 22, 26, 30, 34, 38
  Action5 (Energy Open Circuit) → segments 3, 7, 11, 15, 19, 23, 27, 31, 35, 39
  Action6 (Galvanostatic EIS) → segments 4, 8, 12, 16, 20, 24, 28, 32, 36, 40
  Action7 (Energy Open Circuit) → segments 5, 9, 13, 17, 21, 25, 29, 33, 37, 41

Loop #2 (20 iterations):
  Action9 (Constant Current) → segments 42-121 (20 iterations)
  Action10-12 → continuing sequence...

Final: Action13 → segment 122
```

## Implementation Results

### Real Data Example
**File**: `GITT_EIS_Charge_cycle1_Channel 2.par`
- **Total Segments**: 123 (0-122)
- **Loop #1**: 10 iterations × 4 actions = 40 segments
- **Loop #2**: 20 iterations × 4 actions = 80 segments  
- **ActionIds Found**: 8 (CC), 20 (GEIS), 23 (OCV)

### Mapping Strategy
1. **ActionId mapping applied first** → Direct technique assignment for known ActionIds
2. **Hierarchy mapping as fallback** → Complete coverage for unknown ActionIds
3. **Final result**: `fundamental_technique_final` column with best available mapping

## Expanding the Database

### Requirements for New ActionIds
1. **Parse real .par files** with the structural parser
2. **Identify unmapped ActionIds** in validation warnings
3. **Manually verify technique types** from action names
4. **Add to VERSASTUDIO_ACTIONID_MAPPING** with verification comment
5. **Test with multiple files** to ensure consistency

### Current Coverage
- **ActionId 8**: Constant Current (CC) - verified from GITT data
- **ActionId 20**: Galvanostatic EIS (GEIS) - verified from GITT data  
- **ActionId 23**: Energy Open Circuit (OCV) - verified from GITT data

**Note**: Only verified ActionIds from real data files are included. The database grows organically as more files are processed and validated.