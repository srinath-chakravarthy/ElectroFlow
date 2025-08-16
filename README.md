# Battery Data Analyzer

Comprehensive toolkit for analyzing electrochemical battery data from VersaStudio and other instruments.

## Quick Start

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install package in development mode:
   ```bash
   pip install -e .
   ```

## Project Structure

- `src/core/` - Core data models and parsing logic
- `src/analysis/` - Technique-specific analysis modules  
- `src/visualization/` - Panel dashboards and plotting
- `notebooks/` - Jupyter analysis templates and examples
- `tests/` - Test suite with sample data
- `data/` - Organized data storage (gitignored)

## Usage

See `notebooks/development/` for development examples and `docs/` for detailed documentation.