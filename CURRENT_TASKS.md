# Current Tasks - Raw Data Viewer Integration

**Session**: August 31, 2025  
**Status**: Phase 1 - Backend API Implementation  

## Backend API Implementation ✅ COMPLETE
**Goal**: Add `get_segment_raw_data_for_perspective()` method to Backend API with Arrow format support

### Implementation Tasks:
1. ✅ **Documentation Setup**: Context and task tracking files
2. ✅ **API Method Addition**: `get_segment_raw_data_for_perspective()` in `src_clean/backend/api.py`  
3. ✅ **Helper Methods**: `_add_segment_metadata()`, `_clean_data_for_perspective()`, `_create_empty_arrow_table()`
4. ✅ **Database Integration**: `get_segment_file_info()`, `get_segment_by_id()` methods added
5. ✅ **LazyDataService**: `get_segment_raw_data()` method with row-range filtering
6. ✅ **Testing**: 5/6 validation tests passing - structure complete

### Phase 2: LazyDataService Integration ⚡
**Goal**: Add segment-specific data querying with existing infrastructure

### Phase 3: Analytics Integration 🧠
**Goal**: Registry system integration for metadata and fit curves

### Phase 4: Explorer UI Click Handling 🖱️
**Goal**: Point-and-click segment identification in multi-plot system

### Phase 5: Perspective Modal 📊
**Goal**: Zero-copy Arrow data display with interactive controls

### Phase 6: Testing and Polish ✨
**Goal**: Real data testing, error cases, performance validation

## Success Criteria
- **Fast Response**: <2 seconds segment data loading
- **Zero-Copy**: Arrow format efficiency  
- **Rich Data**: Raw electrochemical + analytical metadata
- **Intuitive UX**: Click-to-inspect workflow

## Files to Modify
- `src_clean/backend/api.py` (Phase 1)
- `src_clean/backend/lazy_data_service.py` (Phase 2)
- `src_clean/panel_app/components/electrochemical_explorer_tab.py` (Phase 4)
- Test files for validation