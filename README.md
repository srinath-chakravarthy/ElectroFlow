# Electrochemical Analysis Platform

A comprehensive platform for electrochemical data processing, analysis, and visualization supporting multiple instrument formats with universal schema standardization.

## Features

- **Multi-Instrument Support**: VersaStudio (.par + .par.csv) and BioLogic (.mpr) file formats
- **Universal Data Processing**: 47-column standardized schema for instrument-agnostic analysis
- **Mixed-Mode Analysis**: Advanced CC-CV (Constant Current to Constant Voltage) technique splitting
- **Registry-Driven Analytics**: Auto-discovery analysis system with expert intelligence algorithms
- **Multi-Interface Access**: Web app, CLI, Python API, and Jupyter notebook support
- **Database Integration**: Cross-file experiment tracking with automated capacity/energy integration

## Quick Start

### Installation
```bash
git clone <repository>
cd Potentiostat_Data_analyser
pip install -r requirements.txt
```

### Web Interface
```bash
python echem_web.py  # http://localhost:5007
```

### CLI Usage  
```bash
python -m src_clean.cli.main compare-groups 16 --metrics capacity energy
python -m src_clean.cli.main group-temporal 16 --plot-types cumulative_capacity
```

### Python API
```python
from src_clean.backend import get_backend_api
api = get_backend_api()

# Process files
result = api.create_cell("TEST_CELL", chemistry="Li_metal")
result = api.process_dual_files(metadata_path, data_path, "TEST_CELL")

# Advanced analytics  
stats = api.get_group_base_statistics(["group_001", "group_002"])
temporal = api.get_group_temporal_analytics(["group_001"])
```

## Supported File Formats

### VersaStudio Files
- **Metadata**: `.par` files (experimental parameters)
- **Data**: `.par.csv` files (calibrated measurements)  
- **Features**: Loop expansion, ActionID mapping, dual-file processing

### BioLogic Files
- **Format**: `.mpr` binary files
- **Features**: Mixed-mode segmentation (CC-CV splitting), technique-aware current mapping
- **Advanced**: Pure technique segments, mode-aware fallbacks, instrumentation drift handling

## Architecture

```
Raw Instrument Files → Universal Schema (47 columns) → Registry Analytics → Multi-Interface Access
```

- **Universal Schema**: Instrument-agnostic 47-column format with explicit units
- **Registry System**: Auto-scaling analysis platform with developer tooling
- **Database Layer**: SQLite with cross-file experiment tracking
- **Multi-Interface**: Panel web app, CLI, Python API, Jupyter support

## Documentation

- **[Complete Documentation](docs/)** - Structured technical documentation
- **[System Overview](docs/SYSTEM_OVERVIEW.md)** - Architecture and components
- **[API Reference](docs/API_REFERENCE.md)** - Programming interface guide
- **[Development Guide](docs/DEVELOPMENT_GUIDE.md)** - Contributing and development setup
- **[User Guide](docs/USER_GUIDE.md)** - Comprehensive usage documentation

## Contributing

See [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) for development setup, testing guidelines, and contribution workflow.

## License

See LICENSE file for details.