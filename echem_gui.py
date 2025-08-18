#!/usr/bin/env python3
"""
Electrochemical Analysis Suite Qt GUI Entry Point

Usage:
    python echem_gui.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src_clean.qt_gui.main_window import main

if __name__ == '__main__':
    sys.exit(main())