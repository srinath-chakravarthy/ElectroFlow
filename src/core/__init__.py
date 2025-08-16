"""
Core module for battery data analyzer.

This module provides the fundamental data structures and parsing capabilities
for electrochemical data analysis.
"""

# Core data models
from .data_models import (
    DataFile,
    DataFileGroup,
    ActionDefinition,
    SegmentData,
    SignalType,
    TechniqueType,
    VERSASTUDIO_COLUMNS,
    create_standardized_dataframe,
    prune_empty_columns
)

# Parser classes and exceptions
from .parsers import (
    BaseParser,
    VersaStudioParser,
    ParserError,
    VersaStudioParseError
)

# Parser factory and convenience functions
from .parser_factory import (
    parse_file,
    parse_versastudio_file,
    parse_par_file,  # backwards compatibility
    register_parser,
    get_supported_extensions
)

# Version info
__version__ = "0.1.0"

# Public API
__all__ = [
    # Data models
    "DataFile",
    "DataFileGroup",
    "ActionDefinition",
    "SegmentData",
    "SignalType",
    "TechniqueType",
    "VERSASTUDIO_COLUMNS",
    "create_standardized_dataframe",
    "prune_empty_columns",

    # Parsers
    "BaseParser",
    "VersaStudioParser",
    "ParserError",
    "VersaStudioParseError",

    # Factory functions
    "parse_file",
    "parse_versastudio_file",
    "parse_par_file",
    "register_parser",
    "get_supported_extensions",

    # Version
    "__version__"
]