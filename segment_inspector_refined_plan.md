# Refined Segment Inspector Plan - Database-Driven Lazy Query Approach

## Key Discovery: Plotting DataFrame Contains Everything Needed

### Current Implementation Analysis:
- **Plotting DataFrame** (from `get_research_dataset_for_perspective()`) contains:
  - `id` (segment_id)
  - `file_id` 
  - `start_row`, `end_row` (raw data boundaries)
  - `cell_name` (for file path construction)
  - All segment metadata

### Refined Approach (Eliminates Code Bloat):

#### Step 1: Use Plotting DataFrame Context
```python
def _handle_plot_click(self, x, y):
    # Find closest segment in self._current_plot_data 
    segment_row = self._find_closest_segment(x, y, self._current_plot_data)
    
    # Extract from plotting DataFrame (no database calls needed):
    segment_id = segment_row['id']
    file_id = segment_row['file_id'] 
    start_row = segment_row['start_row']
    end_row = segment_row['end_row']
    cell_name = segment_row['cell_name']
```

#### Step 2: LazyDataService Enhancement
```python
def get_segment_raw_data_by_context(self, file_id: str, cell_name: str, start_row: int, end_row: int):
    # 1. Check existing query cache for file
    # 2. Create lazy frame if needed: pl.scan_parquet(f"{cell_name}/processed/{file_id}.parquet")
    # 3. Apply row slice: lazy_frame.slice(start_row, count)
    # 4. Materialize and return
```

#### Step 3: Eliminate Database Dependencies
- **Remove:** `get_segment_file_info()` database method
- **Remove:** Database manager from LazyDataService
- **Use:** Direct plotting DataFrame context for all mapping

### Benefits:
1. **Zero Database Overhead** - All data from plotting context
2. **Consistent Patterns** - Uses existing LazyDataService infrastructure
3. **Efficient Caching** - File-level lazy frames reused
4. **No Code Bloat** - Minimal new methods, maximum reuse

### Implementation Changes Needed:
1. **Remove database dependencies** from LazyDataService
2. **Enhance click handler** to extract full context from plotting DataFrame
3. **Simplify API method** to use direct file context instead of database queries

This approach eliminates the separate database layer I implemented and uses the existing data structures more efficiently.