# Group Management Tab - UI Design Summary

**Status**: ✅ COMPLETED - Core functionality fully operational with advanced analytics integration

## Final UI Layout Decision

### Modern 3-Column Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Cell Selector (Top Bar)                                         │
│ [Dropdown: CELL_001 (Li_ion) - 247 segments, 5 groups]        │
├─────────────────────────────────────────────────────────────────┤
│ Left Column (40%)    │ Middle Column (25%) │ Right Column (35%) │
│ ──────────────────── │ ─────────────────── │ ──────────────────│
│ SEGMENTS TABLE       │ GROUPS TREE         │ REAL-TIME PREVIEW  │
│                      │                     │                    │
│ [✓] seg_001 REST     │ 📁 Template Groups  │ ┌──Voltage vs Time─┐│
│ [ ] seg_002 CC       │   └─ All REST (12)  │ │    ●●●●          ││
│ [✓] seg_003 REST     │   └─ All EIS (5)    │ │      ●●●        ││
│ [ ] seg_004 EIS      │ 📁 User Groups       │ │        ●●●      ││
│ [✓] seg_005 REST     │   └─ Formation (8)   │ │          ●●●    ││
│                      │   └─ GITT Exp (15)   │ │            ●●●  ││
│ Voltage│Time│Tech    │                     │ └─────────────────┘│
│ 3.75V  │300s│REST    │ [Create Group]      │ 3 REST segments    │
│ 4.2V   │600s│CC      │ [Delete Group]      │ Time: 300-320s     │
│ 3.80V  │295s│REST    │ [Add Selected]      │ Voltage: 3.75-3.82V│
│        │    │        │ [Remove Selected]   │                    │
└────────────────────────────────────────────────────────────────┘
```

## Key UI Components

### 1. Cell Selector (Top Bar)
- **Component**: Single dropdown with cell summary
- **Data**: Cell name, chemistry, total segments, total groups
- **Purpose**: Context setting for entire workflow

### 2. Left Column - Segments Table (40% width)
- **Component**: Panel Tabulator with database-driven columns
- **Data Source**: `segments` table via `api.get_cell_segments()`
- **Schema**: Dynamic from `api.get_segments_display_schema()`
- **Features**: 
  - Multi-select checkboxes
  - Sortable by any column (time, voltage, technique, duration)
  - Rich data display (voltage, timing, technique, capacity)
- **Purpose**: Detailed segment selection with full metadata

### 3. Middle Column - Groups Management (25% width)
- **Component**: Tree view for groups + action buttons
- **Data Source**: `user_groups` table via `api.get_cell_groups_with_counts()`
- **Tree Structure**:
  ```
  📁 Template Groups
    └─ All REST Phases (12 segments)
    └─ All EIS Measurements (5 segments)
  📁 User Groups  
    └─ Formation Protocol (8 segments)
    └─ GITT Experiment (15 segments)
  ```
- **Actions**: Create Group, Delete Group, Add Selected, Remove Selected
- **Purpose**: Compact group navigation and management

### 4. Right Column - Real-Time Preview (35% width)
- **Component**: Small HoloViews plot with dropdown selector and enhanced summary stats
- **Data**: Currently selected segments from left panel (segment-level metadata only)
- **Default Plot**: Segment Boundary Plot (Option 1)
  - X-axis: `start_time_s` (experimental timeline)
  - Y-axis: `start_potential_v` and `end_potential_v` (voltage boundaries)
  - Visual: Connected points/bars showing voltage change per segment
  - Color/Legend: By `fundamental_technique` (REST=blue, EIS=green, CC=red, etc.)
- **Plot Options Dropdown**:
  - "Voltage Boundaries vs Time" (default)
  - "Voltage Range Bars"
  - "Time vs Duration Scatter"
  - "Capacity vs Time" (for analytical segments)
- **Enhanced Summary Stats**:
  ```
  Current Selection: 5 segments
  ├─ REST: 3 segments (blue ●)
  ├─ EIS: 2 segments (green ●)
  ├─ Voltage Range: 3.0V - 4.2V
  ├─ Time Span: 0s - 3600s
  └─ Total Duration: 1200s
  ```
- **Updates**: Real-time as selection changes
- **Purpose**: Immediate visual validation of group composition without raw data joins

## Data Flow & API Requirements

### Database Schema Integration
```python
# Dynamic column generation from actual database schema
segments_schema = api.get_segments_display_schema()  # PRAGMA table_info(segments)
groups_schema = api.get_groups_display_schema()      # PRAGMA table_info(user_groups)
```

### API Methods Required
```python
# Cell context
api.get_cells() → List[Dict]                        # For dropdown

# Segments (left panel)  
api.get_cell_segments(cell_name) → List[Dict]       # All segments for cell
api.get_segments_display_schema() → Dict[str, Dict] # Column definitions

# Groups (middle panel)
api.get_cell_groups_with_counts(cell_name) → List[Dict]  # Groups with segment counts
api.get_groups_display_schema() → Dict[str, Dict]        # Column definitions

# Group operations
api.create_group(cell_name, name, description) → ProcessingResult
api.delete_group(group_id) → ProcessingResult  
api.add_segments_to_group(group_id, segment_ids) → ProcessingResult
api.remove_segments_from_group(group_id, segment_ids) → ProcessingResult
```

### Key SQL Joins
```sql
-- Groups with segment counts (middle panel)
SELECT ug.*, COUNT(ugs.segment_id) as segment_count
FROM user_groups ug 
LEFT JOIN user_group_segments ugs ON ug.group_id = ugs.group_id
WHERE ug.cell_id = ?
GROUP BY ug.group_id

-- Group contents for preview
SELECT s.* FROM segments s
JOIN user_group_segments ugs ON s.id = ugs.segment_id  
WHERE ugs.group_id = ?
```

## User Workflow

### Primary Use Case: Creating Analytical Groups
1. **Select Cell** → Shows all segments and existing groups
2. **Browse Segments** → Sort by time/voltage/technique to find relevant ones
3. **Multi-select Segments** → Real-time preview shows selection validity
4. **Create/Select Group** → Tree view for group navigation
5. **Add to Group** → Immediate feedback and group count update

### Error Prevention via Real-Time Preview
- **Mixed Techniques**: Colors show if accidentally mixing REST + EIS
- **Wrong Time Range**: Plot shows temporal outliers immediately  
- **Voltage Inconsistency**: Scatter shows voltage range issues
- **Visual Confidence**: "Yes, these all look like similar measurements"

## Implementation Status

### ✅ Core Functionality Complete
- **Segments Table**: Full 19-column electrochemical data display with sorting and filtering
- **Group Operations**: Create/delete groups, add/remove segments, group contents display
- **Three-Column Layout**: Professional responsive design with real-time preview
- **Database Integration**: All operations use real backend API with atomic transactions
- **Template Groups**: Automatic template generation with smart copy functionality

### ✅ Advanced Analytics Integration
- **Group-Level Statistics**: Multi-group comparative analysis ready for Tab 3 integration
- **Temporal Analytics**: Cross-file cumulative calculations with boundary data optimization
- **Fit Quality Analysis**: R² distributions and success rates for curve fitting validation
- **Voltage Correlations**: Pearson/Spearman correlation analysis between metrics and voltages
- **Cumulative Calculations**: Cross-file capacity/energy tracking with file boundary readers

### ✅ Backend Infrastructure Complete
- **Analytics Config Registry**: Auto-generated field definitions with 20 base + 6 cumulative metrics
- **Comprehensive CLI**: 8 advanced analytics commands with matplotlib plotting integration
- **API Methods**: Complete group analytics backend with temporal, fit quality, and correlation analysis
- **Real Data Validation**: Tested with GITT experimental data (123 segments, voltage correlations r=0.766)

## Design Principles Followed

### 1. Database-Driven UI
- Column names and types come from actual database schema
- No hardcoded display logic
- Automatic adaptation to schema changes

### 2. Natural Ordering Only
- No artificial sequencing within groups
- Sort by meaningful data: time, voltage, technique, duration
- Groups are sets, not sequences

### 3. Separation of Concerns
- **Group Management Tab**: Organizing segments into groups (COMPLETE)
- **Data Analysis Tab**: Statistical analysis and advanced visualization (backend ready)
- **File Management Tab**: Data processing and basic plotting (COMPLETE)

### 4. Performance Considerations
- Real-time plotting: 200-300 segments = trivial performance
- Database joins: Efficient with proper indexing
- Dynamic schema: One-time query, then cached
- Cumulative calculations: File boundary optimization with in-memory caching

### 5. Modern UX Patterns
- 3-column layout maximizes information density
- Tree view for hierarchical data (groups)
- Tabulator for rich data display (segments)  
- Real-time feedback for user confidence
- Advanced analytics integration ready for Tab 3