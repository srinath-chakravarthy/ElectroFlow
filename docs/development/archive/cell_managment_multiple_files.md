# Cross-File Cumulative Quantities Implementation Plan

## Problem Statement

Battery experiments often span multiple files due to VersaStudio's experimental design (separate GITT files, cycling batches, temperature changes, etc.). Each file has internal cumulative values that reset to zero, but researchers need **experiment-level accumulation** to track:

- **Cycle progression** (capacity processed = proxy for cycle count)
- **Total experimental time** (aging/degradation timeline)  
- **Total electrochemical activity** (cumulative work done on battery)

## The Challenge: Cross-File Accumulation

### Current State (File-Level Only)
```
Cell_A experiment timeline:
├── GITT_initial.par → segments have capacity_cumulative_ah: 0→1.2 Ah
├── cycling_batch.par → segments have capacity_cumulative_ah: 0→4.5 Ah  ← RESETS!
└── GITT_final.par → segments have capacity_cumulative_ah: 0→1.1 Ah    ← RESETS!

Problem: No way to know "this segment is after 6 Ah total experimental activity"
```

### Required State (Experiment-Level)  
```
Cell_A experiment timeline with cross-file accumulation:
├── GITT_initial.par → segments: experiment_cumulative_ah: 0→1.2 Ah
├── cycling_batch.par → segments: experiment_cumulative_ah: 1.2→5.7 Ah ← CONTINUES!
└── GITT_final.par → segments: experiment_cumulative_ah: 5.7→6.8 Ah   ← CONTINUES!

Solution: Every segment knows its position in the entire experiment
```

## Architecture Decision: Database-Level Storage

After evaluating multiple approaches, we decided on **database-level pre-computation** for performance and maintenance benefits.

### Why Database Storage vs. Application Computation

**Database Approach (CHOSEN)**:
✅ **Zero maintenance overhead** - always in sync  
✅ **Fast queries** - direct column filtering, no JOINs  
✅ **Simple analytics code** - just use the data  
✅ **Consistent results** - single source of truth  

**Application Approach (Rejected)**:
❌ **Maintenance complexity** - manual synchronization needed  
❌ **Performance overhead** - computation + JOINs on every query  
❌ **Drift potential** - calculations might get out of sync  
❌ **Complex update logic** - error-prone state management  

## Implementation Strategy

### Step 1: Database Schema Extension

Add cross-file accumulation columns to existing `segments` table:

```sql
-- Add columns to segments table
ALTER TABLE segments ADD COLUMN experiment_capacity_cumulative_ah REAL;
ALTER TABLE segments ADD COLUMN experiment_energy_cumulative_wh REAL; 
ALTER TABLE segments ADD COLUMN experiment_time_cumulative_s REAL;

-- Optional: Add file-level metadata for reference
ALTER TABLE files ADD COLUMN capacity_start_ah REAL;
ALTER TABLE files ADD COLUMN capacity_end_ah REAL;
ALTER TABLE files ADD COLUMN energy_start_wh REAL;
ALTER TABLE files ADD COLUMN energy_end_wh REAL;
ALTER TABLE files ADD COLUMN time_start_s REAL;
ALTER TABLE files ADD COLUMN time_end_s REAL;
```

### Step 2: Automatic Population During File Processing

#### File Addition Workflow
```python
def add_file_to_cell(cell_id, file_path):
    """
    Enhanced file addition with automatic accumulation updates.
    """
    try:
        # 1. Normal file processing (existing logic)
        file_id = process_and_parse_file(file_path, cell_id)
        
        # 2. NEW: Update file metadata with start/end values
        update_file_accumulation_metadata(file_id)
        
        # 3. NEW: Update ALL segments in cell with experiment positions
        update_experiment_positions_for_entire_cell(cell_id)
        
        return ProcessingResult(success=True, file_id=file_id)
        
    except Exception as e:
        return ProcessingResult(success=False, error=str(e))

def update_file_accumulation_metadata(file_id):
    """
    Helper: Update file table with first/last segment values.
    """
    # Get first and last segments for this file
    first_segment = db.execute("""
        SELECT capacity_cumulative_ah, energy_cumulative_wh, start_time_s
        FROM segments 
        WHERE file_id = ? 
        ORDER BY start_time_s ASC 
        LIMIT 1
    """, [file_id])[0]
    
    last_segment = db.execute("""
        SELECT capacity_cumulative_ah, energy_cumulative_wh, end_time_s
        FROM segments 
        WHERE file_id = ? 
        ORDER BY end_time_s DESC 
        LIMIT 1
    """, [file_id])[0]
    
    # Update file metadata
    db.execute("""
        UPDATE files SET 
            capacity_start_ah = ?,
            capacity_end_ah = ?,
            energy_start_wh = ?,
            energy_end_wh = ?,
            time_start_s = ?,
            time_end_s = ?
        WHERE file_id = ?
    """, [
        first_segment['capacity_cumulative_ah'],
        last_segment['capacity_cumulative_ah'],
        first_segment['energy_cumulative_wh'], 
        last_segment['energy_cumulative_wh'],
        first_segment['start_time_s'],
        last_segment['end_time_s'],
        file_id
    ])

def update_experiment_positions_for_entire_cell(cell_id):
    """
    Helper: Update ALL segments in cell with experiment positions.
    This is the key function that maintains cross-file accumulation.
    """
    # Get all files for cell, ordered by timestamp (determines experimental sequence)
    files = db.execute("""
        SELECT file_id, capacity_start_ah, capacity_end_ah, 
               energy_start_wh, energy_end_wh,
               time_start_s, time_end_s, acquisition_start_date
        FROM files 
        WHERE cell_id = ? 
        ORDER BY acquisition_start_date ASC
    """, [cell_id])
    
    # Calculate running totals and update each file's segments
    experiment_capacity_offset = 0.0
    experiment_energy_offset = 0.0  
    experiment_time_offset = 0.0
    
    for file_info in files:
        file_capacity_contribution = file_info['capacity_end_ah'] - file_info['capacity_start_ah']
        file_energy_contribution = file_info['energy_end_wh'] - file_info['energy_start_wh']
        file_time_contribution = file_info['time_end_s'] - file_info['time_start_s']
        
        # Update ALL segments in this file with experiment position
        db.execute("""
            UPDATE segments 
            SET experiment_capacity_cumulative_ah = capacity_cumulative_ah + ?,
                experiment_energy_cumulative_wh = energy_cumulative_wh + ?,
                experiment_time_cumulative_s = start_time_s + ?
            WHERE file_id = ?
        """, [
            experiment_capacity_offset,
            experiment_energy_offset, 
            experiment_time_offset,
            file_info['file_id']
        ])
        
        # Update offsets for next file
        experiment_capacity_offset += file_capacity_contribution
        experiment_energy_offset += file_energy_contribution
        experiment_time_offset += file_time_contribution
```

#### File Removal Workflow
```python
def remove_file_from_cell(file_id):
    """
    Enhanced file removal with automatic accumulation updates.
    """
    try:
        # 1. Calculate impact BEFORE deletion
        file_info = db.execute("""
            SELECT cell_id, capacity_start_ah, capacity_end_ah,
                   energy_start_wh, energy_end_wh,
                   time_start_s, time_end_s, acquisition_start_date
            FROM files WHERE file_id = ?
        """, [file_id])[0]
        
        file_capacity_contribution = file_info['capacity_end_ah'] - file_info['capacity_start_ah']
        file_energy_contribution = file_info['energy_end_wh'] - file_info['energy_start_wh'] 
        file_time_contribution = file_info['time_end_s'] - file_info['time_start_s']
        cell_id = file_info['cell_id']
        file_timestamp = file_info['acquisition_start_date']
        
        # 2. Delete file and segments (existing CASCADE logic)
        db.execute("DELETE FROM segments WHERE file_id = ?", [file_id])
        db.execute("DELETE FROM files WHERE file_id = ?", [file_id])
        
        # 3. Update subsequent segments (SUBTRACT removed file's contribution)
        db.execute("""
            UPDATE segments 
            SET experiment_capacity_cumulative_ah = experiment_capacity_cumulative_ah - ?,
                experiment_energy_cumulative_wh = experiment_energy_cumulative_wh - ?,
                experiment_time_cumulative_s = experiment_time_cumulative_s - ?
            WHERE file_id IN (
                SELECT file_id FROM files 
                WHERE cell_id = ? AND acquisition_start_date > ?
            )
        """, [
            file_capacity_contribution,
            file_energy_contribution,
            file_time_contribution, 
            cell_id, 
            file_timestamp
        ])
        
        return ProcessingResult(success=True)
        
    except Exception as e:
        return ProcessingResult(success=False, error=str(e))
```

### Step 3: Analytics Config Auto-Discovery

Add new columns to analytics configuration for auto-discovery:

```python
# Add to analytics_config.py segment fields:
'experiment_capacity_cumulative_ah': {
    'type': 'float',
    'unit': 'Ah', 
    'description': 'Cumulative capacity across entire cell experiment'
},
'experiment_energy_cumulative_wh': {
    'type': 'float',
    'unit': 'Wh',
    'description': 'Cumulative energy across entire cell experiment' 
},
'experiment_time_cumulative_s': {
    'type': 'float',
    'unit': 's',
    'description': 'Cumulative time across entire cell experiment'
}
```

## Usage Examples

### Research Query Power
With experiment-level accumulation, researchers can now ask:

```sql
-- "Show me resistance evolution after 5 cycles (≈5 Ah)"
SELECT segment_id, start_potential_v, 
       JSON_EXTRACT(analysis_results, '$.ir_immediate_ohm') as resistance
FROM segments 
WHERE cell_id = 'Cell_A'
  AND experiment_capacity_cumulative_ah >= 5.0
  AND start_potential_v BETWEEN 3.9 AND 4.1
  AND fundamental_technique = 'Rest';

-- "Compare kinetics at different experimental stages" 
SELECT 
    CASE 
        WHEN experiment_capacity_cumulative_ah < 2.0 THEN 'Early'
        WHEN experiment_capacity_cumulative_ah < 8.0 THEN 'Middle' 
        ELSE 'Late'
    END as experimental_stage,
    AVG(JSON_EXTRACT(analysis_results, '$.time_constant_s')) as avg_kinetics
FROM segments
WHERE fundamental_technique = 'Rest'
  AND JSON_EXTRACT(analysis_results, '$.r_squared') > 0.95
GROUP BY experimental_stage;
```

### LazyDataService Integration  
```python
# Your existing filter system works immediately:
filters = {
    'experiment_capacity_range': (5.0, 6.0),  # "After ~5 cycles"
    'voltage_range': (3.9, 4.1),             # "Around 4V"
    'techniques': ['Rest']                     # "REST segments"
}

# LazyDataService applies filters directly - no computation needed!
filtered_data = api.materialize_data_for_visualization(query_id, filters)
```

## Timeline Insertion Example

### Scenario: Adding Earlier File
```
Current experimental sequence:
├── file_002.par (acquired: 10:00 AM) → 2.5 Ah 
└── file_003.par (acquired: 2:00 PM) → 1.8 Ah

User adds: file_001.par (acquired: 8:00 AM) → 1.2 Ah

Result after auto-update:
├── file_001.par (08:00) → experiment_cumulative: 0.0→1.2 Ah    ← New first  
├── file_002.par (10:00) → experiment_cumulative: 1.2→3.7 Ah   ← Shifted up
└── file_003.par (14:00) → experiment_cumulative: 3.7→5.5 Ah   ← Shifted up

All segments automatically updated based on acquisition timestamps!
```

### Update Efficiency
```python
# Adding file_001.par triggers:
# 1. Update file_001 segments: +0.0 offset (it's first)
# 2. Update file_002 segments: +1.2 offset (single UPDATE query)  
# 3. Update file_003 segments: +1.2 offset (single UPDATE query)

# Total: 3 UPDATE queries, not thousands of individual segment updates
# Database handles bulk updates efficiently
```

## Benefits Achieved

### For Researchers
✅ **"After 5 cycles" queries** work instantly  
✅ **Cross-file comparisons** are natural  
✅ **Aging studies** use experiment timeline  
✅ **Temperature effects** over experimental progression  

### For Developers  
✅ **Zero maintenance** - accumulation always in sync  
✅ **Fast queries** - direct column filtering  
✅ **Simple code** - no complex aggregations needed  
✅ **Robust** - handles file reordering automatically  

### For System Performance
✅ **Database optimization** - indexes on accumulation columns  
✅ **Query efficiency** - no JOINs needed for filtering  
✅ **Lazy loading** - works with existing LazyDataService  
✅ **Arrow integration** - zero-copy to Perspective  

## Risk Mitigation

### File Reprocessing Impact
- **Concern**: Reprocessing file affects entire cell's accumulation
- **Mitigation**: Atomic transactions ensure consistency
- **Recovery**: Full cell recalculation available as backup

### Performance with Large Cells  
- **Concern**: Updating 10K+ segments when adding file
- **Reality**: Single UPDATE query per file, database handles efficiently
- **Monitoring**: Track update times, optimize if needed

### Data Consistency
- **Validation**: Add integrity checks in file processing
- **Backup**: Store file-level totals for verification  
- **Recovery**: Recalculation function available

## Future Enhancements

### Additional Accumulation Types
```python
# Could add specialized accumulations:
'experiment_charge_cumulative_ah'    # Only positive capacity
'experiment_discharge_cumulative_ah' # Only negative capacity  
'experiment_activity_cumulative_ah'  # |charge| + |discharge| total
'experiment_cycle_count'             # Estimated cycle number
```

### Cell-Specific Cycle Proxies
```python
# Cell metadata for cycle interpretation:
cell_configs = {
    'Cell_A': {'capacity_per_cycle': 0.95},  # 25°C performance
    'Cell_B': {'capacity_per_cycle': 0.78},  # 45°C performance  
    'Cell_C': {'capacity_per_cycle': 1.12}   # 5°C performance
}

# UI can show: "5 cycles ≈ 4.75 Ah for Cell_A @ 25°C"
```

## Implementation Priority

### Phase 1: Core Implementation ⚡ HIGH PRIORITY
- [ ] Add database columns  
- [ ] Implement file addition/removal helpers
- [ ] Test with multi-file cell data
- [ ] Validate accumulation accuracy

### Phase 2: Integration ✅ MEDIUM PRIORITY  
- [ ] Update analytics_config auto-discovery
- [ ] Test LazyDataService filtering  
- [ ] Verify Perspective integration
- [ ] Performance benchmarking

### Phase 3: Enhancement 🔮 LOW PRIORITY
- [ ] Add specialized accumulation types
- [ ] Implement cell-specific cycle proxies  
- [ ] Create validation and recovery tools
- [ ] Advanced query examples

## Success Criteria

### Technical Success
- [ ] Files can be added in any order, accumulation stays correct
- [ ] File removal properly adjusts subsequent segments  
- [ ] Query performance remains fast with accumulation columns
- [ ] LazyDataService filtering works seamlessly

### Research Success  
- [ ] "After 5 cycles" queries return expected data
- [ ] Cross-file aging analysis works correctly
- [ ] Temperature effects visible across experimental timeline
- [ ] Publication-quality cycle progression analysis possible

## Conclusion

This implementation provides the **missing link** for comprehensive battery research: **experiment-level accumulation tracking** that enables researchers to analyze data across the entire experimental timeline, not just individual files.

**Key Innovation**: Database-level storage with automatic maintenance ensures accumulation data is always available, always correct, and requires zero ongoing maintenance overhead.

**Impact**: Transforms fragmented file-based data into coherent experimental timelines, enabling research questions like "How does performance change after X cycles of aging?" across any combination of techniques, voltages, and conditions.

---

*This solution completes the foundation for advanced battery research analytics by providing experiment-level context to every measurement point.*