"""
Core Module - Electrochemical Analysis Suite

Essential data structures, database operations, and exceptions.
"""

from .data_models import (
    DataFile, FileMetadata, validate_universal_schema, 
    create_empty_universal_dataframe, add_missing_universal_columns,
    FUNDAMENTAL_TECHNIQUES, DEFAULT_ACTIONID_MAPPINGS
)

# Import configs separately - use late imports to avoid circular imports
def get_universal_schema():
    """Get universal schema - lazy import to avoid circular imports."""
    from ..parsers.configs.universal_schema import UNIVERSAL_SCHEMA
    return UNIVERSAL_SCHEMA

def get_versastudio_mappings():
    """Get VersaStudio mappings - lazy import to avoid circular imports."""
    from ..parsers.configs.versastudio_mappings import VERSASTUDIO_CSV_MAPPING, VERSASTUDIO_CSV_SCHEMA
    return VERSASTUDIO_CSV_MAPPING, VERSASTUDIO_CSV_SCHEMA

# Keep these for backward compatibility
UNIVERSAL_SCHEMA = None  # Will be populated on first access
VERSASTUDIO_CSV_MAPPING = None
VERSASTUDIO_CSV_SCHEMA = None
from .database import DatabaseManager
from .exceptions import (
    ElectrochemicalAnalysisError, ValidationError, ParsingError,
    DatabaseError, ProcessingError, StorageError, UIError,
    format_error_for_user, format_error_for_log, is_user_error, is_recoverable_error
)

__all__ = [
    # Data models
    'DataFile',
    'FileMetadata',
    'validate_universal_schema',
    'create_empty_universal_dataframe',
    'add_missing_universal_columns',
    'FUNDAMENTAL_TECHNIQUES',
    'DEFAULT_ACTIONID_MAPPINGS',
    
    # Config access functions
    'get_universal_schema',
    'get_versastudio_mappings',
    
    # Backward compatibility (deprecated)
    'UNIVERSAL_SCHEMA',
    'VERSASTUDIO_CSV_SCHEMA', 
    'VERSASTUDIO_CSV_MAPPING',
    
    # Database
    'DatabaseManager',
    
    # Exceptions
    'ElectrochemicalAnalysisError',
    'ValidationError',
    'ParsingError', 
    'DatabaseError',
    'ProcessingError',
    'StorageError',
    'UIError',
    'format_error_for_user',
    'format_error_for_log',
    'is_user_error',
    'is_recoverable_error'
]