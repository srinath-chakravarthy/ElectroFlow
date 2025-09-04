yes # Battery Data Analyzer - AI Assistant Technical Guide

**Version:** 6.3.1 Enhanced Multi-Plot Explorer with Scientific Data Filtering  
**Last Updated:** August 29, 2025  
**Status:** Complete Tab 3 with responsive range sliders and registry-driven technique filtering

## Interactive Coding Workflow

**CRITICAL RULE**: For all coding and debugging prompts, follow this workflow:

1. **Understand** - Read documentation and source code to understand current system
2. **Report** - Summarize understanding of problem and current implementation 
3. **Plan** - Create detailed implementation plan with specific steps
4. **Get Confirmation** - Wait for user approval before proceeding
5. **Code** - Implement solution with proper testing

### Guidelines:
- **Follow Existing Patterns** - Mimic existing code style, libraries, and architectural patterns
- **User Override Authority** - User can override workflow for specific plan parts
- **Context & Fatigue Reporting** - Report insufficient context or performance limitations
- **Registry-First Approach** - Use registry system for analysis features (30-minute development workflow)

## Documentation Navigation

- **[Complete User Guide → README.md](README.md)** - Installation, quick start, usage
- **[Registry System → docs/registry/REGISTRY_SYSTEM_COMPLETE.md](docs/registry/REGISTRY_SYSTEM_COMPLETE.md)** - Registry implementation details
- **[Architecture → docs/architecture/](docs/architecture/)** - System design decisions
- **[Development History → docs/development/](docs/development/)** - Implementation timeline
- **[All Documentation → docs/README.md](docs/README.md)** - Complete index

## Current System Status

### Production Components
- **Universal Data Processing**: Multi-instrument files to 47-column standardized format (VersaStudio + BioLogic)
- **Registry Analysis System**: Auto-scaling platform with developer tooling
- **Multi-Plot Explorer**: Complete Tab 3 with technique filtering and multi-series analysis
- **Cross-File Experiment Tracking**: Database-level accumulation across multiple files
- **ElectrochemicalInsights 2.0**: Auto-discovery with expert intelligence algorithms
- **Group Management**: Templated groups with CASCADE operations
- **Multi-Interface Access**: Panel web app, CLI, Python API, Jupyter

### Latest Completions (August-September 2025)
- **Universal Schema Column Consistency (Sep 4)**: Fixed BioLogic parser column selection to return proper universal schema names instead of raw instrument columns, ensuring 47-column consistency across all parsers
- **YADG Control Splitting Integration (Sep 4)**: Implemented mode-dependent control column interpretation for BioLogic files, enabling proper current data extraction from galvanostatic vs potentiostatic techniques
- **FileDropper Dictionary Fix (Aug 30)**: Resolved "Error:0" in file upload with proper dictionary pattern implementation
- **Test Config Isolation (Aug 30)**: Complete test suite isolation preventing production database contamination
- **Explorer Backend Testing (Aug 30)**: Comprehensive validation suite (13/14 tests passing) - backend ready for UI debugging
- **Database Schema Migrations (Aug 29)**: Automatic migration system for channel_id, cell_id columns with graceful failure handling
- **Critical Slice Indexing Fix (Aug 29)**: Resolved off-by-one error in analysis engine segment boundary calculations
- **Tab 3 Enhanced Multi-Plot Explorer (Aug 29)**: Complete with responsive range sliders, technique filtering, and clean Panel-native architecture
- **Scientific Data Filtering**: Registry-driven technique filtering eliminates irrelevant data (e.g., resistance analysis shows only galvanostatic data)
- **Responsive Range Sliders**: Data-driven limits with proper 320px panel fit and circular callback prevention
- **Multi-Plot Grid System**: 1→4 plot layouts with GridSpec fix and per-plot state management
- **Performance Optimizations**: Filter-first approach and callback suppression for smooth UI behavior

## Core Architecture

### Data Flow
```
VersaStudio Files (.par + .par.csv) 
    ↓ Universal Schema Mapping
29-Column DataFrame (Polars)
    ↓ Registry Analysis System
Expert Electrochemical Insights
    ↓ Database Storage + Group Management
Panel Web App / CLI / Python API
```

### Universal Schema (47 columns)
- **Time**: `time_s`, `timestamp`
- **Electrochemical**: `potential_v`, `current_a`, `power_w`
- **Technique**: `technique_id`, `segment_number`
- **Impedance**: `impedance_real_ohm`, `impedance_imag_ohm`, `impedance_mag_ohm`, `impedance_phase_deg`
- **Electrode-Specific**: `working_electrode_potential_v`, `we_impedance_*`, `ce_impedance_*`
- **Analytics**: Battery metrics, cumulative tracking, temperature, status flags

### Database Schema
```sql
-- Core data with cross-file experiment tracking
segments: id, file_id, technique_id, start_time_s, duration_s,
          capacity_ah, energy_wh, analysis_results (JSON),
          exp_charge_cap_ah, exp_discharge_cap_ah,
          exp_charge_energy_wh, exp_discharge_energy_wh,
          exp_time_cumulative_s

-- Group management with CASCADE operations
user_groups: group_id, cell_id, group_name, description
user_group_segments: group_id, segment_id (CASCADE cleanup)
```

### Registry System
```python
from src_clean.analysis.registry import get_analysis_registry

registry = get_analysis_registry()

# Auto-discovery capabilities
analysis_config = registry.get_analytics_config('equilibrium_analysis')
plot_configs = registry.get_analysis('kinetics_analysis').plot_config
settings_schema = registry.get_settings_schema('resistance_analysis')

# Developer tooling
issues = registry.validate_all_configs()
report = registry.generate_config_report()
```

## Essential API Methods

### Cell & File Operations
```python
from src_clean.backend import get_backend_api
api = get_backend_api()

# Basic operations
result = api.create_cell("TEST_CELL", chemistry="Li_metal")
result = api.process_dual_files(metadata_path, data_path, "TEST_CELL")
cells = api.get_all_cells()
```

### Group Management
```python
# Complete group system
result = api.create_group("TEST_CELL", "REST_PHASES", "All rest phases")
api.add_segments_to_group(result.group_id, ["seg_001", "seg_003"])
groups = api.get_cell_groups("TEST_CELL")
template_groups = api.get_template_groups("TEST_CELL")  # Auto-generated
```

### Advanced Analytics (Registry-Driven)
```python
# Multi-group analysis with auto-discovery
stats = api.get_group_base_statistics(["group_001", "group_002"])
temporal = api.get_group_temporal_analytics(["group_001"])

# Advanced Research Tab - comprehensive analytics
dataset = api.get_research_dataset_for_perspective(["CELL1", "CELL2"])  # 30K+ segments
# Automated: kinetics, resistance, equilibrium, current_decay analytics
```

## Project Structure

```
src_clean/
├── core/                    # Universal schema, database, config
├── analysis/                # Registry system + analytics engine
├── backend/                 # API orchestration + data migration
├── parsers/                 # VersaStudio + instrument support
├── panel_app/              # 3-tab web interface
│   └── components/         # Tab 1: complete, Tab 2: complete, Tab 3: backend ready
└── cli/                    # 8 advanced analytics commands
```

## Usage Examples

### Web Interface
```bash
python echem_web.py  # http://localhost:5007
# Tab 1: Cell & file management (complete)
# Tab 2: Group management with templated system (complete) 
# Tab 3: Multi-Plot Explorer (complete - clean Panel-native architecture)
# Tab 4: Advanced Research Tab (complete - automated analytics + Perspective)
```

### CLI Analytics
```bash
python -m src_clean.cli.main compare-groups 16 --metrics capacity energy
python -m src_clean.cli.main group-temporal 16 --plot-types cumulative_capacity
python -m src_clean.cli.main group-voltage-correlation 16 --correlation-type pearson
```

### Registry Development (30-minute workflow)
```python
# Add analysis function to registry - system automatically generates:
# - UI controls from settings schema
# - Plot configurations
# - Analytics config integration  
# - Validation framework
# Immediate availability in web interface, CLI, and API
```

## Key Technical Systems

### Multi-Instrument Processing

#### VersaStudio Processing
- **ActionID Mapping**: 23→Rest, 20→EIS, 8→Galvanostatic
- **Loop Expansion**: Complex hierarchical structures with iteration handling
- **Dual File System**: .par (metadata) + .par.csv (calibrated data)

#### BioLogic Processing (NEW)
- **YADG Control Splitting**: Mode-dependent interpretation of control column (galvanostatic vs potentiostatic)
- **Technique Mapping**: Btech→Ftech classification (GCPL→cc, CV→cv, PEIS→eis)
- **Binary MPR Format**: Native parsing with electrode-specific impedance data
- **Column Consistency**: Fixed to return universal schema names (`current_a`, `time_s`) not raw names (`I`, `time`)

### Analytics Engine
- **sqrt(t) + Exponential Fitting**: Automatic best-fit selection with R² comparison
- **JSON Coefficient Storage**: Complete fit parameters for replotting
- **Cross-File Accumulation**: Experiment-level tracking across multiple files

### ElectrochemicalInsights 2.0
- **JSONFieldExtractor**: Auto-discovery field extraction using analytics_config
- **Expert Algorithms**: Physics-based assessment with Cottrell equation calculations
- **Multi-Series Plotting**: Enhanced visualization with registry integration

## Development Context

### Performance Status
**Current Scale:** ✅ Functional up to ~30K segments (tested with 123 segments)
**Performance Bottlenecks:** ❌ Pandas-heavy pipeline, multiple DataFrame copies, comprehensive NaN cleaning
**1M+ Row Readiness:** ❌ Requires Polars-native pipeline + streaming operations

### Next Development Priorities  
1. **Performance Optimization**: Polars-native analytics pipeline for 100K+ segment datasets
2. **Memory Efficiency**: Streaming operations and single-pass data processing
3. **Registry Expansion**: Continue 30-minute development workflow for new analysis types

### Architecture Status
- **Production Ready**: Registry-driven analytics with automated discovery and execution
- **Merge Conflicts Resolved**: Clean `on='id'` merging eliminates column duplication issues  
- **Multi-Interface Support**: Consistent functionality across web, CLI, API, Jupyter
- **Scale-Limited**: Current implementation optimized for moderate datasets (<30K segments)

## Current Session Status & Next Steps

### ✅ **Completed This Session (September 4, 2025)**
- **BioLogic Phase 1 Complete**: File restructuring with clean architectural separation achieved
- **MPRReader Extraction**: Pure binary parser extracted to `src_clean/parsers/mpr_reader.py`
- **BiologicParser Integration**: Clean integration layer using external MPRReader
- **YADG Techniques Integration**: Copied and adapted `biologic_techniques.py` for parameter parsing support
- **Architecture Validation**: BiologicParser imports and instantiates successfully

### 💡 **STRATEGIC DECISION: Combined Phase 2 Implementation**

**Decision**: Combine column mapping fix with Phase 2 technique mapping for maximum efficiency.

**Rationale**: Avoid duplicate work - technique mapping will require column processing changes anyway, so implement both together for cleaner development progression.

### 🎯 **NEXT SESSION PRIORITIES: Enhanced Phase 2 Implementation**

**Expanded Scope**: Combined column mapping fix + technique parameter extraction for architectural coherence.

**Status**: 
- ✅ **Phase 1 Complete** - File restructuring with clean architectural separation achieved
- ⚠️ **Known Issue** - Column mapping produces `unknown_*` columns (will fix in Phase 2)
- 🎯 **Next Priority** - Enhanced Phase 2 with comprehensive BioLogic data processing

**Enhanced Phase 2 Tasks**:
1. **Fix Column Mapping** - Resolve `unknown_*` columns → proper BioLogic names (`time`, `Ewe`, `I`)
2. **Parameter Extraction** - Integrate YADG technique parameter parsing logic
3. **Technique Identification** - Extract technique ID and parameter sequences from settings
4. **Context Integration** - Design column mapping with technique parameter awareness

**Technical Challenge**: Convert BioLogic composite techniques (GCPL→charge/rest cycles, GEIS→galvanostatic/EIS sequences) into fundamental technique segments (1-5) compatible with existing registry-driven analysis system.

**Documentation**: See `docs/BIOLOGIC_TECHNIQUE_MAPPING_ARCHITECTURE.md` for complete implementation plan.
**Previous Roadmap Completed**: Universal schema enhancement and timestamp extraction completed. Now focusing on technique mapping as primary development track.

### 📋 **Current System State**
- **Branch**: prod (clean working tree - column consistency fixes merged)
- **Universal Schema**: v2.1.0 with 47 columns including electrode-specific impedance measurements
- **BioLogic Parser**: ✅ **COMPLETE** - YADG control splitting + universal schema column consistency
- **VersaStudio Parser**: ✅ **VALIDATED** - confirmed proper universal schema column selection
- **Platform Consistency**: Both parsers now return identical 47-column universal schema format
- **Parser Architecture**: Clean MPRReader (binary) + BiologicParser (integration) + YADG technique mode handling

---

**The system provides a complete registry-driven analysis platform with auto-discovery capabilities, expert intelligence algorithms, and cross-file experiment tracking. Next session will focus on raw data plotting integration to enable point-and-click segment inspection.**