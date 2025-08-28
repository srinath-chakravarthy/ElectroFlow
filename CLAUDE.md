# Battery Data Analyzer - AI Assistant Technical Guide

**Version:** 6.2.1 Optimized Multi-Plot Platform  
**Last Updated:** August 28, 2025  
**Status:** Complete multi-plot Explorer with optimized codebase (13% size reduction)

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
- **Universal Data Processing**: VersaStudio files to 29-column standardized format
- **Registry Analysis System**: Auto-scaling platform with developer tooling
- **Multi-Plot Explorer**: Complete Tab 3 with technique filtering and multi-series analysis
- **Cross-File Experiment Tracking**: Database-level accumulation across multiple files
- **ElectrochemicalInsights 2.0**: Auto-discovery with expert intelligence algorithms
- **Group Management**: Templated groups with CASCADE operations
- **Multi-Interface Access**: Panel web app, CLI, Python API, Jupyter

### Latest Completions (August 2025)
- **Multi-Plot Explorer (Tab 3 Complete)**: Grid layouts (1→4 plots), technique-based filtering, multi-series plotting with saved per-plot state
- **Data Filtering System**: Registry-driven technique filtering eliminates 0.0 value clutter (kinetics: CV/EIS only, resistance: EIS/Galvanostatic only)
- **Multi-Series Analysis**: Y-axis MultiSelect widget enables overlaid metrics with automatic legends and color coding
- **Advanced Research Tab (Tab 4)**: Complete automated analytics pipeline with Perspective integration
- **Registry **kwargs System**: Dynamic parameter passing for all analysis functions  
- **Performance Assessment**: Current scale functional, 30K+ row optimization identified
- Cross-File Experiment Accumulation: 5 experiment columns with automatic maintenance
- ElectrochemicalInsights 2.0: JSONFieldExtractor + expert algorithms
- Templated Groups System: Single dropdown UI with automatic template creation

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

### Universal Schema (29 columns)
- **Time**: `time_s`, `timestamp`
- **Electrochemical**: `potential_v`, `current_a`, `power_w`
- **Technique**: `technique_id`, `segment_number`
- **Impedance**: `impedance_real_ohm`, `impedance_imag_ohm`, `impedance_mag_ohm`, `impedance_phase_deg`
- **Analysis**: 20+ additional columns

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
# Tab 3: Multi-group analytics (backend complete, UI in progress)
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

### VersaStudio Processing
- **ActionID Mapping**: 23→Rest, 20→EIS, 8→Galvanostatic
- **Loop Expansion**: Complex hierarchical structures with iteration handling
- **Dual File System**: .par (metadata) + .par.csv (calibrated data)

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

---

**The system provides a complete registry-driven analysis platform with auto-discovery capabilities, expert intelligence algorithms, and cross-file experiment tracking - enabling researchers to focus on electrochemical science rather than software engineering.**