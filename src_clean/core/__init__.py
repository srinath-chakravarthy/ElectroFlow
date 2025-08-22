"""
Core Module - Electrochemical Analysis Suite

Essential data structures, database operations, and exceptions.
"""

from .data_models import (
    UNIVERSAL_SCHEMA, VERSASTUDIO_CSV_SCHEMA, VERSASTUDIO_CSV_MAPPING,
    DataFile, FileMetadata, validate_universal_schema, 
    create_empty_universal_dataframe, add_missing_universal_columns,
    FUNDAMENTAL_TECHNIQUES, DEFAULT_ACTIONID_MAPPINGS
)
from .database import DatabaseManager
from .exceptions import (
    ElectrochemicalAnalysisError, ValidationError, ParsingError,
    DatabaseError, ProcessingError, StorageError, UIError,
    format_error_for_user, format_error_for_log, is_user_error, is_recoverable_error
)

__all__ = [
    # Data models
    'UNIVERSAL_SCHEMA',
    'VERSASTUDIO_CSV_SCHEMA', 
    'VERSASTUDIO_CSV_MAPPING',
    'DataFile',
    'FileMetadata',
    'validate_universal_schema',
    'create_empty_universal_dataframe',
    'add_missing_universal_columns',
    'FUNDAMENTAL_TECHNIQUES',
    'DEFAULT_ACTIONID_MAPPINGS',
    
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