# Implementation Guide - Electrochemical Analysis Suite

## Overview

This guide outlines the clean implementation approach for the Electrochemical Analysis Suite, focusing on modular, testable components with clear separation of concerns.

## Implementation Order

### Phase 1: Core Foundation
1. **Data Models** - Clean schemas and data structures
2. **Database Layer** - Minimal database schema and operations
3. **Parser Factory** - Universal parser interface and VersaStudio implementation
4. **Backend API** - Clean orchestration layer

### Phase 2: Interfaces
5. **CLI Interface** - Command-line access to all operations
6. **Testing Suite** - Comprehensive test coverage
7. **Qt GUI** - Clean desktop interface

### Phase 3: Extensions
8. **BioLogic Parser** - Extend to second instrument
9. **Advanced Analytics** - Segment analysis and grouping
10. **Jupyter Integration** - Notebook-friendly interfaces

## Key Design Decisions

### Parsing Strategy
- **VersaStudio**: .par (metadata only) + .par.csv (data only)
- **Universal Schema**: All instruments convert to same 38-column format with explicit units
- **Units-Aware**: Automatic unit conversion using Pint library (mA→A, mV→V, etc.)
- **Config-Driven**: Instrument mappings in separate config files for maintainability

### Database Design
- **Segment-Centric**: Each experimental segment is independent unit
- **Row Boundaries**: Precise start/end rows for efficient data slicing
- **Atomic Operations**: All-or-nothing database commits
- **Foreign Keys**: Proper relational constraints

### Architecture Principles
- **Single Responsibility**: Each module has one clear purpose
- **Dependency Injection**: Components receive dependencies, don't create them
- **Interface Segregation**: Small, focused interfaces
- **Testability**: All business logic is unit testable

## Module Structure

```
src/
├── core/
│   ├── data_models.py          # Schemas and data structures
│   ├── database.py             # Database operations
│   └── exceptions.py           # Custom exceptions
├── parsers/
│   ├── configs/                # Configuration files
│   │   ├── __init__.py         # Clean config exports
│   │   ├── universal_schema.py # 38-column schema with units
│   │   └── versastudio_mappings.py # VersaStudio column mappings
│   ├── base.py                 # Abstract parser interface
│   ├── factory.py              # Parser factory
│   ├── versastudio.py          # VersaStudio implementation (units-aware)
│   └── biologic.py             # BioLogic implementation (future)
├── backend/
│   └── api.py                  # Clean backend orchestration
├── cli/
│   └── main.py                 # Command-line interface
├── qt_gui/
│   ├── main_window.py          # Qt desktop interface
│   └── dialogs/
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

## Testing Strategy

### Unit Tests
- **Data Models**: Schema validation, conversions
- **Parsers**: File format handling, column mapping, unit conversions
- **Config System**: Universal schema and instrument mappings
- **Database**: CRUD operations, constraints
- **Backend**: Orchestration logic

### Integration Tests
- **End-to-End**: File upload → processing → storage → retrieval
- **Cross-Module**: Parser + Database + Backend interactions
- **Real Data**: Test with actual VersaStudio files

### Test Data
- **Fixtures**: Small, representative data files
- **Mocks**: Controlled test scenarios
- **Real Files**: Subset of actual experimental data

## Error Handling

### Validation Errors
- **File Format**: Clear messages for unsupported formats
- **Schema Validation**: Specific column/type mismatches
- **Data Integrity**: Missing required fields

### Processing Errors
- **Atomic Rollback**: Failed processing leaves no partial state
- **Detailed Logging**: Full error context for debugging
- **User-Friendly**: Non-technical error messages for GUI

### Recovery Strategies
- **Graceful Degradation**: Partial success where possible
- **Retry Logic**: Transient failures with backoff
- **Manual Intervention**: Clear paths for user correction

## Performance Considerations

### Memory Management
- **Streaming**: Process large files without loading everything
- **Lazy Loading**: Load data only when needed
- **Cleanup**: Explicit resource management

### Database Optimization
- **Indices**: Proper indexing for common queries
- **Batch Operations**: Efficient bulk inserts
- **Connection Pooling**: Reuse database connections

### File I/O
- **Parquet Format**: Efficient columnar storage
- **Compression**: Reduce storage requirements
- **Caching**: Cache frequently accessed data

## Development Workflow

### Commit Strategy
- **Atomic Commits**: Each commit represents complete, working feature
- **Clear Messages**: Descriptive commit messages
- **Logical Order**: Commits build incrementally

### Testing Requirements
- **Test First**: Write tests before implementation where possible
- **Coverage**: Aim for >90% test coverage
- **CI/CD**: Automated testing on all commits

### Documentation
- **Code Comments**: Focus on why, not what
- **API Documentation**: Clear interface specifications
- **Examples**: Working examples for all public APIs

## Next Steps

See `project_status.md` for current implementation status and immediate next tasks.