# Battery Data Analyzer - AI Assistant Technical Guide

**Version:** 6.1.0 Production System  
**Last Updated:** August 25, 2025  
**Status:** Registry-driven analysis platform with cross-file experiment tracking

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
- **Cross-File Experiment Tracking**: Database-level accumulation across multiple files
- **ElectrochemicalInsights 2.0**: Auto-discovery with expert intelligence algorithms
- **Group Management**: Templated groups with CASCADE operations
- **Multi-Interface Access**: Panel web app, CLI, Python API, Jupyter

### Latest Completions (August 2025)
- Tab 1 Redesign: Unified cell & file management with modals + integrated DataViewer
- Registry Settings + UI Automation: Schema-to-widget generation complete
- Cross-File Experiment Accumulation: 5 experiment columns with automatic maintenance
- ElectrochemicalInsights 2.0: JSONFieldExtractor + expert algorithms
- Tab 3 Backend Analytics: LazyDataService + 8 API methods
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
insights = api.get_equilibrium_analysis(["group_001"])
kinetics = api.get_kinetics_analysis(["group_001"])
resistance = api.get_resistance_analysis(["group_001"])
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

### Current Focus
- **Tab 3 UI Integration**: Connect backend analytics to web interface plotting
- **Multi-File Testing**: Validate cross-file experiment accumulation with real data
- **Registry Expansion**: Continue 30-minute development workflow for new analysis types

### Architecture Status
- **Production Ready**: Core system with registry-driven development platform
- **Clean Modular Design**: Clear separation of concerns with comprehensive error handling
- **Multi-Interface Support**: Consistent functionality across web, CLI, API, Jupyter
- **Performance Optimized**: 1GB+ file processing with efficient memory usage

### Known Issues
- **Pre-Analysis Filtering**: Temporarily disabled in registry settings (needs debugging)
- **Tab 3 UI**: Backend complete, frontend plotting integration in progress

---

**The system provides a complete registry-driven analysis platform with auto-discovery capabilities, expert intelligence algorithms, and cross-file experiment tracking - enabling researchers to focus on electrochemical science rather than software engineering.**