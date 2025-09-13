# Session Context - Raw Data Viewer Integration

**Started**: August 31, 2025  
**Branch**: feature/test_isolation_config  
**Goal**: Point-and-click segment inspection in Explorer Tab with Perspective modal

## System State Understanding

**Project**: Battery Data Analyzer v6.3.1 - Registry-driven electrochemical analysis platform
**Architecture**: VersaStudio files → 29-column schema → Registry analytics → Multi-interface access (web/CLI/API)
**Current Status**: Production-ready system with empty database but intact file directories

## Key Infrastructure Available
- **LazyDataService**: Polars lazy loading with query cache and materialization
- **Registry System**: 30-minute development workflow for analytics
- **Explorer Tab**: Complete multi-plot system with technique filtering and responsive UI  
- **Backend API**: Orchestration layer with atomic operations
- **Test Framework**: Complete validation suite (13/14 tests passing)

## Integration Requirements
- **Zero-Copy Performance**: Arrow format for efficient data transfer
- **Scientific Accuracy**: Analytical metadata correctly associated with raw data
- **User Experience**: Intuitive click-to-inspect workflow
- **Fast Response**: <2 seconds for segment data loading

## Implementation Files Ready
- `test_segment_inspector.py`: Complete workflow validation
- `test_segment_inspector_implementation.py`: Structure validation  
- `Raw_data_inspector_for_explorer_tab.md`: Integration plan with code snippets

## Documentation Strategy
- **Context docs**: `docs/` folder with specific implementation context
- **Clean main docs**: CLAUDE.md/README.md remain focused
- **Session tracking**: PROJECT_CONTEXT.md and CURRENT_TASKS.md in root