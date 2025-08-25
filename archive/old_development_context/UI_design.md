# User Groups UI Design - Complete Summary

## **Architecture Decisions ✅**

### **Data Structure (Existing)**
- **Hierarchy**: Cell → Files → Segments (existing DB design)
- **Segment Storage**: Database with links to parquet files
- **User Groups**: JSON lists of `segment_ids` stored per cell
- **Base Grouping**: Auto-generated technique groups (`all_rest_segments`, `all_cc_segments`, etc.)
- **Custom Groups**: User-defined arbitrary segment collections
- **Duplicate Prevention**: Database-level unique constraints

### **Segment Data Schema ✅**
Each segment stores:
- `segment_id`, `technique`, `start/end_timestamps`, `start/end_voltages`, `start/end_currents`
- `file_link`, `row_indices`, `duration`, `technique_metrics_json`

## **Tab Infrastructure Design ✅**

### **3-Tab Application Architecture**
- **Tab 1**: Cell & File Management (existing working code)
- **Tab 2**: Group Management (new - two-tabulator interface)
- **Tab 3**: Data Analysis & Visualization (enhanced to handle groups)

### **Tab Independence Benefits**
- ✅ **No shared state complexity** - each tab is self-contained
- ✅ **Independent debugging** - issues in one tab don't affect others  
- ✅ **Parallel development** - can work on tabs separately
- ✅ **Clear ownership** - each tab owns its components completely
- ✅ **Database-only communication** - tabs interact only through backend API

### **Code Replication Strategy**
- **Acceptable**: Component duplication between tabs for simplicity
- **Preferred**: Independent components over complex state sharing
- **Maintenance**: Easier to maintain separate, clear components

## **Professional UI Components ✅**

### **Tab 2: Group Management Layout**
```
┌─────────────────────────────────────────────────────────────────┐
│ 🔗 Group Management [Professional Gradient Header]              │
├─────────────────────────┬───────────────────────────────────────┤
│ Panel 1: All Segments   │ Panel 2: Group Contents              │
│ ┌─────────────────────┐ │ ┌───────────────────────────────────┐ │
│ │ Tabulator:          │ │ │ Group Selector: [Dropdown]        │ │
│ │ - All segments      │ │ │ Group Info: [Name, Count, Desc]   │ │
│ │ - Multi-select      │ │ ├───────────────────────────────────┤ │
│ │ - Sortable          │ │ │ Tabulator:                        │ │
│ │ - Filterable        │ │ │ - Group segments only             │ │
│ │ - Highlighting      │ │ │ - Remove capability               │ │
│ │ └─────────────────────┘ │ └───────────────────────────────────┘ │
│ [Show Group] [Add →]    │ [New Group] [Remove] [Delete Group]   │
└─────────────────────────┴───────────────────────────────────────┘
```

### **Professional Styling Consistency**
- **Headers**: Same gradient design as existing tabs (`#2E4057` to `#1976D2`)
- **Cards**: White background with shadows (`box-shadow: 0 2px 8px rgba(0,0,0,0.1)`)
- **Colors**: Consistent with existing scientific color scheme
- **Typography**: Same font hierarchy and spacing
- **Buttons**: Match existing button styling and hover effects

### **Component Structure**
```python
class GroupManagementTab(param.Parameterized):
    """Professional group management with two-tabulator design"""
    
    current_cell = param.String(default="")
    selected_group = param.String(default="")
    status_message = param.String(default="")
    
    # Two main tabulators
    segments_tabulator = None      # Panel 1: All segments
    group_contents_tabulator = None # Panel 2: Group contents
    
    # Professional styling methods
    @property
    def panel(self) -> pn.Column
    def _create_professional_layout(self) -> pn.Column
    def _apply_consistent_styling(self) -> dict
```

## **Backend API Interface ✅**

### **Assumed Backend Methods (To Be Implemented)**
```python
# Segment queries
self.api.get_cell_segments(cell_id) → List[dict]  # All segments for Panel 1

# Group CRUD operations  
self.api.get_groups(cell_id) → List[dict]         # Populate dropdown
self.api.create_group(cell_id, name, desc) → Result
self.api.delete_group(group_id) → Result

# Group membership operations
self.api.get_group_segments(group_id) → List[dict]  # Panel 2 contents
self.api.add_segments_to_group(group_id, segment_ids) → Result
self.api.remove_segments_from_group(group_id, segment_ids) → Result

# Group membership queries (for highlighting)
self.api.is_segment_in_group(segment_id, group_id) → bool
self.api.get_segment_groups(segment_id) → List[dict]
```

### **Development Strategy**
- **UI First**: Build interface assuming API exists
- **Backend Parallel**: Implement database operations separately  
- **Integration**: Connect when both components ready
- **Testing**: Mock API for UI development, separate backend testing

## **UI Components (Panel + Tabulator) ✅**

### **Panel 1: All Segments Table**
- **Widget**: Tabulator showing all segments from all files in current cell
- **Columns**: Segment ID, Technique, Start Time, Duration, Start/End V/I, File, Quality (R²)
- **Features**: Multi-column sorting, header filters, multi-row selection
- **Default Sort**: Chronological (respects experimental timeline)
- **Filter Examples**: By technique, by file, by quality metrics
- **Highlighting**: Visual indication when segments belong to selected group

### **Panel 2: Group Management**
- **Group Selector**: Dropdown to select existing groups or create new
- **Group Contents**: Tabulator showing segments currently in selected group
- **Actions**: Add selected segments from Panel 1, remove segments from group
- **Group Info**: Show group metadata (name, description, creation date, segment count)

### **Key UI Actions**
- **"Show Group"**: Highlight group segments in Panel 1 (database lookup)
- **"Add Selected to Group"**: Move checked segments to current group (database insert)
- **"Remove from Group"**: Remove selected segments from Panel 2 (database delete)
- **"Create New Group"**: Add new group and populate Panel 2 (database insert)

### **User Workflow ✅**
1. Select segments in Panel 1 (multi-row selection)
2. Choose existing group or create new group in Panel 2
3. Add to group → Database prevents duplicates automatically
4. View/manage group contents in Panel 2 tabulator
5. Remove segments from groups as needed

### **Visual Highlighting System**
```python
# Row styling for group membership
highlighting_styles = {
    'in_selected_group': {
        'background': '#E8F5E8',     # Green - in currently selected group
        'border-left': '4px solid #2E7D32'
    },
    'in_other_groups': {
        'background': '#F5F5F5',     # Gray - in other groups
        'border-left': '2px solid #999'
    },
    'not_in_groups': {
        'background': 'white',       # Default - not in any groups
    }
}
```

## **Database Architecture (Groups) ✅**

### **Final Schema Design**

#### **user_groups**
```sql
CREATE TABLE user_groups (
    group_id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_template BOOLEAN DEFAULT FALSE,  -- Auto-generated vs user-created
    template_type VARCHAR(100) NULL,    -- 'all_rest', 'all_cc', 'all_eis' for templates
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cell_id) REFERENCES cells(cell_id),
    UNIQUE(cell_id, group_name)  -- Unique group names per cell
);
```

#### **user_group_segments** (Many-to-Many Junction Table)
```sql
CREATE TABLE user_group_segments (
    group_id INTEGER NOT NULL,
    segment_id VARCHAR(255) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (group_id, segment_id),  -- Prevents duplicates
    FOREIGN KEY (group_id) REFERENCES user_groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES segments(segment_id) ON DELETE CASCADE
);
```

### **Key Design Decisions**
- **Many-to-Many**: Segments can belong to multiple groups
- **CASCADE Deletion**: Deleting a group automatically removes all segment memberships
- **Template Integration**: Templates are just special user groups (is_template=true)
- **No Separate Template Table**: Reduces complexity and maintenance overhead

## **Data Flow Architecture ✅**

### **Option 1: Database-Driven (CHOSEN)**

**Initial Load:**
- Query segments table → populate Panel 1 with all segments
- Query user_groups table → populate group dropdown
- Optionally show default group (e.g., "all_rest_segments") highlighted in Panel 1
- Query user_group_segments for default group → populate Panel 2

**"Add Selected to Group" Action:**
- INSERT INTO user_group_segments (group_id, segment_id) for each selected segment
- Re-query user_group_segments for current group → refresh Panel 2
- Re-query membership for Panel 1 highlighting → refresh visual state

**"Show Group in Table" Action:**
- Simple SELECT segment_id FROM user_group_segments WHERE group_id = ? 
- Apply highlighting to Panel 1 (no database writes)
- Query group contents → populate Panel 2

**"Remove from Group" Action:**
- DELETE FROM user_group_segments WHERE group_id = ? AND segment_id = ?
- Refresh both panels (re-query)

### **Performance Characteristics:**
- **Writes**: Database INSERT/DELETE + UI refresh
- **Reads**: Fast SELECT lookups for highlighting/filtering
- **Consistency**: Always reflects current database state
- **Simplicity**: Straightforward data flow, no state synchronization issues

## **Decisions Made ✅**

### **1. Nested Groups - DECIDED: NOT NEEDED FOR NOW**
**Decision:** Start with flat group structure
**Reasoning:**
- Good naming conventions solve hierarchy needs (e.g., `aging_study_rests`, `formation_pulses`)
- Search/filter capabilities replace need for nesting
- Simpler UI and database design
- Can add nesting later for group-to-group analytics if needed

### **2. Auto-Generated Template Groups - DECIDED: INTEGRATED WITH USER GROUPS**
**Decision:** Templates are special user groups (is_template=true), not separate table
**Reasoning:**
- Reduces database complexity (one table instead of two)
- Same CRUD operations for templates and user groups
- No maintenance overhead for separate template system
- Templates can be modified like regular groups

### **3. Database Design - DECIDED: MANY-TO-MANY WITH CASCADE**
**Decision:** Junction table with CASCADE deletion
**Reasoning:**
- Segments can belong to multiple groups (essential flexibility)
- Automatic cleanup when groups are deleted
- Referential integrity maintained
- Clean deletion without orphaned records

### **4. Tab Architecture - DECIDED: 3 INDEPENDENT TABS**
**Decision:** Cell & File | Group Management | Data Analysis
**Reasoning:**
- Clean separation of concerns (ingest → organize → analyze)
- Independent performance and debugging
- Simple mental model for users
- Database-only communication between tabs

### **5. UI Framework - DECIDED: PANEL + TABULATOR**
**Decision:** Panel interface with Tabulator widgets for data display
**Reasoning:**
- Handles large datasets well
- Professional appearance matches existing interface
- Multi-row selection and filtering capabilities
- Consistent with existing application architecture

## **Implementation Priority 📋**

### **Phase 1: Basic Groups (NEXT)**
1. **Tab Infrastructure**: Implement 3-tab Panel application structure
2. **Database Schema**: Implement `user_groups` and `user_group_segments` tables
3. **Panel 1**: Segments tabulator with sorting/filtering (mock backend calls)
4. **Panel 2**: Basic group creation and segment addition (mock backend calls)
5. **Professional Styling**: Apply consistent design from existing tabs

### **Phase 2: Backend Integration**
1. **Backend API**: Implement all group-related database operations
2. **UI Integration**: Connect Panel components to real backend
3. **Testing**: Verify end-to-end group management workflow
4. **Error Handling**: Robust error states and user feedback

### **Phase 3: Enhanced Features**
1. **Auto-Generated Templates**: Create technique-based groups automatically
2. **Group Analytics**: Compute group-level statistics
3. **Tab 3 Enhancement**: Extend Data Analysis to work with groups
4. **Export/Import**: Save/load group definitions

### **Phase 4: Advanced Features (If Needed)**
1. **Nested Groups**: Hierarchical group organization
2. **Group Comparison**: Compare analytics across groups
3. **Workflow Integration**: Connect groups to analysis pipelines
4. **Visualization**: Group-based plotting and analysis

## **Key Technical Decisions ✅**

- **UI Framework**: Panel + Tabulator (handles large datasets well)
- **Data Storage**: Database with JSON metadata (flexible + queryable)
- **Duplicate Prevention**: Database constraints (robust + simple)
- **Group Scope**: Cell-level (matches existing architecture)
- **Selection Method**: Multi-row tabulator selection (user-friendly)
- **Tab Communication**: Database-only (simple and reliable)
- **Styling Consistency**: Match existing professional interface design

## **Open Questions (For Future Development) 🚧**

1. **Template Generation Timing**: When to auto-create technique-based templates (on file processing vs on-demand)?
2. **Group Analytics**: What group-level computations are most valuable for battery research?
3. **Naming Conventions**: Should we suggest/enforce naming patterns for groups?
4. **Group Sharing**: Future consideration for sharing groups across cells/users?
5. **Group Export/Import**: Need for saving/loading group definitions?
6. **Tab 3 Integration**: How should Data Analysis tab switch between file and group analysis modes?

## **Ready for Implementation ✅**

This design is ready for Phase 1 implementation:
- Tab infrastructure architecture finalized
- Database schema finalized
- UI components specified with professional styling
- User workflow defined
- Technical decisions made
- Backend API interface defined

**Next Step**: Implement Tab infrastructure and Panel 1 (Segments Tabulator) with mock backend calls, maintaining professional styling consistency.