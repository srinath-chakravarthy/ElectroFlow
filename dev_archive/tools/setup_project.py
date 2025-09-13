#!/usr/bin/env python3
"""
Battery Data Analyzer - Project Setup Script

Run this script in your project root to create the complete directory structure.
"""

import os
from pathlib import Path


def create_directory_structure():
    """Create the complete project directory structure."""

    # Define the directory structure
    directories = [
        # Source code
        "src",
        "src/core",
        "src/analysis",
        "src/io_utils",
        "src/visualization",
        "src/utils",

        # Notebooks
        "notebooks",
        "notebooks/templates",
        "notebooks/examples",
        "notebooks/development",

        # CLI tools
        "cli_tools",

        # Tests
        "tests",
        "tests/sample_data",
        "tests/sample_data/sample_fragmented_gitt",
        "tests/sample_data/expected_outputs",

        # Data storage (will be gitignored)
        "data",
        "data/cells",
        "data/measurement_groups",
        "data/experiments",
        "data/experiments/completed_experiments",
        "data/exports",
        "data/exports/doe_datasets",
        "data/exports/relaxis_exports",
        "data/exports/reports",
        "data/exports/plots",
        "data/exports/plots/publication_figures",
        "data/exports/plots/analysis_snapshots",

        # Configuration
        "config",
        "config/instrument_configs",

        # Documentation
        "docs",
        "docs/tutorial",
        "docs/examples",
        "docs/development",

        # Scripts
        "scripts",
        "scripts/maintenance",

        # Environments
        "environments",
        "environments/docker"
    ]

    # Create directories
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created: {directory}/")

    # Create __init__.py files for Python packages
    init_files = [
        "src/__init__.py",
        "src/core/__init__.py",
        "src/analysis/__init__.py",
        "src/io_utils/__init__.py",
        "src/visualization/__init__.py",
        "src/utils/__init__.py",
        "cli_tools/__init__.py",
        "tests/__init__.py"
    ]

    for init_file in init_files:
        Path(init_file).touch()
        print(f"Created: {init_file}")


def create_config_files():
    """Create basic configuration files."""

    # .gitignore
    gitignore_content = """
# Data files
data/
*.par
*.parquet

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Jupyter
.ipynb_checkpoints/

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Temporary files
tmp/
temp/
"""

    with open(".gitignore", "w") as f:
        f.write(gitignore_content.strip())
    print("Created: .gitignore")

    # requirements.txt
    requirements_content = """
polars>=0.20.0
pandas>=2.0.0
numpy>=1.24.0
panel>=1.3.0
param>=2.0.0
bokeh>=3.0.0
matplotlib>=3.7.0
seaborn>=0.12.0
scipy>=1.10.0
scikit-learn>=1.3.0
pytest>=7.0.0
jupyter>=1.0.0
ipykernel>=6.0.0
"""

    with open("requirements.txt", "w") as f:
        f.write(requirements_content.strip())
    print("Created: requirements.txt")

    # pyproject.toml
    pyproject_content = """
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "battery-data-analyzer"
version = "0.1.0"
description = "Comprehensive battery electrochemical data analysis toolkit"
authors = [{name = "Battery Research Lab"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "polars>=0.20.0",
    "pandas>=2.0.0", 
    "numpy>=1.24.0",
    "panel>=1.3.0",
    "param>=2.0.0",
    "bokeh>=3.0.0",
    "matplotlib>=3.7.0",
    "seaborn>=0.12.0",
    "scipy>=1.10.0",
    "scikit-learn>=1.3.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "jupyter>=1.0.0", 
    "ipykernel>=6.0.0",
    "black>=23.0.0",
    "flake8>=6.0.0"
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-dir]
"" = "src"
"""

    with open("pyproject.toml", "w") as f:
        f.write(pyproject_content.strip())
    print("Created: pyproject.toml")

    # Basic README
    readme_content = """
# Battery Data Analyzer

Comprehensive toolkit for analyzing electrochemical battery data from VersaStudio and other instruments.

## Quick Start

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
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
"""

    with open("README.md", "w") as f:
        f.write(readme_content.strip())
    print("Created: README.md")


if __name__ == "__main__":
    print("Setting up Battery Data Analyzer project structure...")
    print("=" * 50)

    create_directory_structure()
    print()
    create_config_files()

    print()
    print("=" * 50)
    print("Project setup complete!")
    print()
    print("Next steps:")
    print("1. Create virtual environment: python -m venv venv")
    print("2. Activate environment: source venv/bin/activate")
    print("3. Install dependencies: pip install -r requirements.txt")
    print("4. Install package: pip install -e .")
    print("5. Start development in notebooks/development/")