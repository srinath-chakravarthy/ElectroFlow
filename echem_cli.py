#!/usr/bin/env python3
"""
Electrochemical Analysis Suite CLI Entry Point

Usage:
    python echem_cli.py --help
    python echem_cli.py create-cell CELL_001 --chemistry Li_metal
    python echem_cli.py process-files data.par data.par.csv CELL_001
    python echem_cli.py list-cells --format json
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src_clean.cli.main import main

if __name__ == '__main__':
    main()