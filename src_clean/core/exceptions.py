"""
Custom Exceptions - Electrochemical Analysis Suite

Clean exception hierarchy for precise error handling and user-friendly messages.

Key Principles:
- Specific exception types for different error categories
- User-friendly error messages
- Preservation of technical details for debugging
- Clear error recovery suggestions
"""

from typing import Optional, List, Dict, Any


class ElectrochemicalAnalysisError(Exception):
    """Base exception for all electrochemical analysis errors."""
    
    def __init__(self, message: str, technical_details: Optional[str] = None, 
                 suggestion: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.technical_details = technical_details
        self.suggestion = suggestion
    
    def __str__(self):
        return self.message


# =============================================================================
# VALIDATION EXCEPTIONS
# =============================================================================

class ValidationError(ElectrochemicalAnalysisError):
    """Base class for validation errors."""
    pass


class FileFormatError(ValidationError):
    """File format is not supported or invalid."""
    
    def __init__(self, file_path: str, expected_format: str, 
                 detected_format: Optional[str] = None):
        self.file_path = file_path
        self.expected_format = expected_format
        self.detected_format = detected_format
        
        if detected_format:
            message = f"Invalid file format: expected {expected_format}, got {detected_format}"
        else:
            message = f"Invalid file format: expected {expected_format}"
        
        suggestion = f"Please ensure the file is a valid {expected_format} file"
        
        super().__init__(
            message=message,
            technical_details=f"File: {file_path}",
            suggestion=suggestion
        )


class SchemaValidationError(ValidationError):
    """Data schema validation failed."""
    
    def __init__(self, missing_columns: List[str] = None, 
                 invalid_types: Dict[str, str] = None,
                 extra_info: Optional[str] = None):
        self.missing_columns = missing_columns or []
        self.invalid_types = invalid_types or {}
        
        error_parts = []
        
        if self.missing_columns:
            error_parts.append(f"Missing columns: {', '.join(self.missing_columns)}")
        
        if self.invalid_types:
            type_errors = [f"{col}: expected {expected}, got {actual}" 
                          for col, (expected, actual) in self.invalid_types.items()]
            error_parts.append(f"Type mismatches: {'; '.join(type_errors)}")
        
        message = "Schema validation failed: " + "; ".join(error_parts)
        
        if extra_info:
            message += f" ({extra_info})"
        
        suggestion = "Check that the file contains the expected columns and data types"
        
        super().__init__(
            message=message,
            technical_details=f"Missing: {self.missing_columns}, Types: {self.invalid_types}",
            suggestion=suggestion
        )


class DataIntegrityError(ValidationError):
    """Data integrity check failed."""
    
    def __init__(self, issue: str, affected_rows: Optional[int] = None):
        self.issue = issue
        self.affected_rows = affected_rows
        
        message = f"Data integrity error: {issue}"
        if affected_rows is not None:
            message += f" ({affected_rows} rows affected)"
        
        suggestion = "Check data quality and consider data cleaning"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


# =============================================================================
# PARSING EXCEPTIONS
# =============================================================================

class ParsingError(ElectrochemicalAnalysisError):
    """Base class for parsing errors."""
    pass


class FileReadError(ParsingError):
    """Cannot read file."""
    
    def __init__(self, file_path: str, reason: str):
        self.file_path = file_path
        self.reason = reason
        
        message = f"Cannot read file: {reason}"
        suggestion = "Check file permissions and that the file is not corrupted"
        
        super().__init__(
            message=message,
            technical_details=f"File: {file_path}",
            suggestion=suggestion
        )


class MetadataExtractionError(ParsingError):
    """Cannot extract metadata from file."""
    
    def __init__(self, file_path: str, missing_metadata: List[str]):
        self.file_path = file_path
        self.missing_metadata = missing_metadata
        
        message = f"Cannot extract required metadata: {', '.join(missing_metadata)}"
        suggestion = "Verify this is a valid instrument file with complete metadata"
        
        super().__init__(
            message=message,
            technical_details=f"File: {file_path}",
            suggestion=suggestion
        )


class DataParsingError(ParsingError):
    """Cannot parse data section of file."""
    
    def __init__(self, file_path: str, section: str, reason: str):
        self.file_path = file_path
        self.section = section
        self.reason = reason
        
        message = f"Cannot parse {section} data: {reason}"
        suggestion = "Check that the data section is properly formatted"
        
        super().__init__(
            message=message,
            technical_details=f"File: {file_path}, Section: {section}",
            suggestion=suggestion
        )


class UnsupportedInstrumentError(ParsingError):
    """Instrument not supported."""
    
    def __init__(self, instrument_name: str, supported_instruments: List[str]):
        self.instrument_name = instrument_name
        self.supported_instruments = supported_instruments
        
        message = f"Instrument '{instrument_name}' is not supported"
        suggestion = f"Supported instruments: {', '.join(supported_instruments)}"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


# =============================================================================
# DATABASE EXCEPTIONS
# =============================================================================

class DatabaseError(ElectrochemicalAnalysisError):
    """Base class for database errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Cannot connect to database."""
    
    def __init__(self, db_path: str, reason: str):
        self.db_path = db_path
        self.reason = reason
        
        message = f"Database connection failed: {reason}"
        suggestion = "Check database file permissions and disk space"
        
        super().__init__(
            message=message,
            technical_details=f"Database: {db_path}",
            suggestion=suggestion
        )


class DatabaseIntegrityError(DatabaseError):
    """Database integrity constraint violation."""
    
    def __init__(self, constraint: str, operation: str):
        self.constraint = constraint
        self.operation = operation
        
        message = f"Database integrity error during {operation}: {constraint}"
        suggestion = "Check for duplicate data or missing references"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


class TransactionError(DatabaseError):
    """Database transaction failed."""
    
    def __init__(self, operation: str, reason: str):
        self.operation = operation
        self.reason = reason
        
        message = f"Transaction failed during {operation}: {reason}"
        suggestion = "Operation was rolled back. Check data and retry"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


class RecordNotFoundError(DatabaseError):
    """Requested record not found in database."""
    
    def __init__(self, record_type: str, identifier: str):
        self.record_type = record_type
        self.identifier = identifier
        
        message = f"{record_type} '{identifier}' not found"
        suggestion = f"Check that the {record_type.lower()} exists and try again"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


# =============================================================================
# PROCESSING EXCEPTIONS
# =============================================================================

class ProcessingError(ElectrochemicalAnalysisError):
    """Base class for data processing errors."""
    pass


class SegmentationError(ProcessingError):
    """Cannot identify experimental segments."""
    
    def __init__(self, reason: str, data_points: Optional[int] = None):
        self.reason = reason
        self.data_points = data_points
        
        message = f"Segment detection failed: {reason}"
        if data_points is not None:
            message += f" ({data_points} data points)"
        
        suggestion = "Check ActionID/technique mappings and data quality"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


class MappingError(ProcessingError):
    """ActionID/technique mapping error."""
    
    def __init__(self, unknown_actionids: List[int]):
        self.unknown_actionids = unknown_actionids
        
        message = f"Unknown ActionIDs found: {', '.join(map(str, unknown_actionids))}"
        suggestion = "Add ActionID mappings in the database or UI"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


class DataConversionError(ProcessingError):
    """Cannot convert data to universal schema."""
    
    def __init__(self, source_format: str, reason: str):
        self.source_format = source_format
        self.reason = reason
        
        message = f"Cannot convert {source_format} data to universal schema: {reason}"
        suggestion = "Check column mappings and data types"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


# =============================================================================
# STORAGE EXCEPTIONS
# =============================================================================

class StorageError(ElectrochemicalAnalysisError):
    """Base class for storage errors."""
    pass


class FileNotFoundError(StorageError):
    """File not found in storage."""
    
    def __init__(self, file_id: str, storage_path: str):
        self.file_id = file_id
        self.storage_path = storage_path
        
        message = f"File '{file_id}' not found in storage"
        suggestion = "Check that the file was processed successfully"
        
        super().__init__(
            message=message,
            technical_details=f"Expected path: {storage_path}",
            suggestion=suggestion
        )


class StorageSpaceError(StorageError):
    """Insufficient storage space."""
    
    def __init__(self, required_space: str, available_space: str):
        self.required_space = required_space
        self.available_space = available_space
        
        message = f"Insufficient storage space: need {required_space}, have {available_space}"
        suggestion = "Free up disk space and try again"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


# =============================================================================
# USER INTERFACE EXCEPTIONS
# =============================================================================

class UIError(ElectrochemicalAnalysisError):
    """Base class for user interface errors."""
    pass


class InvalidUserInputError(UIError):
    """User provided invalid input."""
    
    def __init__(self, field: str, value: str, expected: str):
        self.field = field
        self.value = value
        self.expected = expected
        
        message = f"Invalid {field}: got '{value}', expected {expected}"
        suggestion = f"Please enter a valid {field}"
        
        super().__init__(
            message=message,
            suggestion=suggestion
        )


class OperationCancelledError(UIError):
    """User cancelled the operation."""
    
    def __init__(self, operation: str):
        self.operation = operation
        
        message = f"Operation cancelled: {operation}"
        
        super().__init__(message=message)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_error_for_user(error: Exception) -> Dict[str, str]:
    """Format error for user display with suggestion."""
    if isinstance(error, ElectrochemicalAnalysisError):
        return {
            'message': error.message,
            'suggestion': error.suggestion or "Please try again or contact support",
            'technical_details': error.technical_details or str(error)
        }
    else:
        return {
            'message': f"Unexpected error: {str(error)}",
            'suggestion': "Please try again or contact support",
            'technical_details': str(error)
        }


def format_error_for_log(error: Exception) -> str:
    """Format error for detailed logging."""
    if isinstance(error, ElectrochemicalAnalysisError):
        parts = [
            f"Error: {error.message}",
            f"Type: {type(error).__name__}"
        ]
        
        if error.technical_details:
            parts.append(f"Details: {error.technical_details}")
        
        if error.suggestion:
            parts.append(f"Suggestion: {error.suggestion}")
        
        return " | ".join(parts)
    else:
        return f"Unexpected error ({type(error).__name__}): {str(error)}"


def is_user_error(error: Exception) -> bool:
    """Check if error is due to user input (vs system error)."""
    user_error_types = (
        FileFormatError,
        SchemaValidationError,
        InvalidUserInputError,
        UnsupportedInstrumentError,
        OperationCancelledError
    )
    
    return isinstance(error, user_error_types)


def is_recoverable_error(error: Exception) -> bool:
    """Check if error is recoverable (user can retry)."""
    unrecoverable_types = (
        DatabaseConnectionError,
        StorageSpaceError,
        FileReadError
    )
    
    return not isinstance(error, unrecoverable_types)