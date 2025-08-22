"""
Parser Configuration Module

Centralized configuration for instrument-agnostic electrochemical data parsing.
Contains schema definitions, unit specifications, and instrument mappings.
"""

from .universal_schema import UNIVERSAL_SCHEMA, get_polars_schema, get_column_units
from .versastudio_mappings import VERSASTUDIO_CSV_MAPPING, VERSASTUDIO_CSV_SCHEMA

__all__ = [
    'UNIVERSAL_SCHEMA',
    'get_polars_schema',
    'get_column_units',
    'VERSASTUDIO_CSV_MAPPING', 
    'VERSASTUDIO_CSV_SCHEMA'
]