"""
Abstract Parser Interface - Electrochemical Analysis Suite

Universal parser interface for instrument-agnostic data processing.

Key Principles:
- Abstract base class for all instrument parsers
- Standard validation and error handling
- Universal schema output requirement
- Common utilities for all parsers
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

from ..core.data_models import DataFile, FileMetadata
from ..core.exceptions import (
    ParsingError, FileFormatError, MetadataExtractionError,
    DataParsingError, UnsupportedInstrumentError
)

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for all instrument parsers."""
    
    def __init__(self):
        self.instrument_name = self.get_instrument_name()
        self.supported_extensions = self.get_supported_extensions()
        logger.debug(f"Initialized {self.instrument_name} parser")
    
    @abstractmethod
    def get_instrument_name(self) -> str:
        """Return the instrument name (e.g., 'VersaStudio', 'BioLogic')."""
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions (e.g., ['.par', '.mpr'])."""
        pass
    
    @abstractmethod
    def validate_file(self, file_path: Path) -> bool:
        """
        Validate if file can be parsed by this parser.
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            True if file can be parsed, False otherwise
        """
        pass
    
    @abstractmethod
    def parse_metadata(self, file_path: Path) -> FileMetadata:
        """
        Extract metadata from file.
        
        Args:
            file_path: Path to metadata file
            
        Returns:
            FileMetadata object with extracted information
            
        Raises:
            MetadataExtractionError: If metadata cannot be extracted
        """
        pass
    
    @abstractmethod
    def parse_data(self, file_path: Path) -> DataFile:
        """
        Parse data file and return universal schema DataFile.
        
        Args:
            file_path: Path to data file
            
        Returns:
            DataFile with universal schema DataFrame
            
        Raises:
            DataParsingError: If data cannot be parsed
        """
        pass
    
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this parser can handle the given file.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            True if parser can handle file, False otherwise
        """
        try:
            # Check file extension
            if not any(str(file_path).lower().endswith(ext.lower()) 
                      for ext in self.supported_extensions):
                return False
            
            # Check file exists and is readable
            if not file_path.exists() or not file_path.is_file():
                return False
            
            # Instrument-specific validation
            return self.validate_file(file_path)
            
        except Exception as e:
            logger.debug(f"Parser {self.instrument_name} cannot parse {file_path}: {e}")
            return False
    
    def _validate_file_exists(self, file_path: Path) -> None:
        """Validate file exists and is readable."""
        if not file_path.exists():
            raise FileFormatError(
                str(file_path), 
                f"{self.instrument_name} file", 
                "File not found"
            )
        
        if not file_path.is_file():
            raise FileFormatError(
                str(file_path),
                f"{self.instrument_name} file",
                "Path is not a file"
            )
        
        if file_path.stat().st_size == 0:
            raise FileFormatError(
                str(file_path),
                f"{self.instrument_name} file", 
                "File is empty"
            )
    
    def _safe_read_file(self, file_path: Path, encoding: str = 'utf-8') -> str:
        """Safely read file content with error handling and skip large data segments."""
        try:
            self._validate_file_exists(file_path)
            
            with open(file_path, 'r', encoding=encoding) as f:
                # For .par files, skip <Segment>...</Segment> blocks which contain raw data
                if str(file_path).lower().endswith('.par'):
                    return self._read_par_metadata_only(f)
                else:
                    return f.read()
                
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    # Apply same optimization for .par files
                    if str(file_path).lower().endswith('.par'):
                        return self._read_par_metadata_only(f)
                    else:
                        return f.read()
            except Exception as e:
                raise DataParsingError(
                    str(file_path),
                    "file content",
                    f"Cannot decode file: {str(e)}"
                )
        except Exception as e:
            raise DataParsingError(
                str(file_path),
                "file content", 
                f"Cannot read file: {str(e)}"
            )
    
    def _read_par_metadata_only(self, file_obj) -> str:
        """Read .par file but skip <Segment>...</Segment> blocks to avoid loading raw data."""
        content_lines = []
        skip_segment = False
        
        for line in file_obj:
            # Check for segment start/end tags (case insensitive)
            line_upper = line.upper().strip()
            
            if line_upper.startswith('<SEGMENT'):
                skip_segment = True
                continue
            elif line_upper.startswith('</SEGMENT>'):
                skip_segment = False
                continue
            
            # Only include lines that are not inside segment blocks
            if not skip_segment:
                content_lines.append(line)
        
        return ''.join(content_lines)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        import hashlib
        
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Cannot calculate hash for {file_path}: {e}")
            return "unknown"
    
    def get_parser_info(self) -> Dict[str, Any]:
        """Get parser information."""
        return {
            'instrument_name': self.instrument_name,
            'supported_extensions': self.supported_extensions,
            'parser_class': self.__class__.__name__,
            'parser_version': getattr(self, 'PARSER_VERSION', '1.0.0')
        }


class DualFileParser(BaseParser):
    """
    Abstract parser for instruments with dual files (metadata + data).
    
    Examples:
    - VersaStudio: .par (metadata) + .par.csv (data)
    - Future instruments with similar structure
    """
    
    @abstractmethod
    def parse_dual_files(self, metadata_path: Path, data_path: Path) -> DataFile:
        """
        Parse dual files and return universal schema DataFile.
        
        Args:
            metadata_path: Path to metadata file (e.g., .par)
            data_path: Path to data file (e.g., .par.csv)
            
        Returns:
            DataFile with universal schema DataFrame
            
        Raises:
            DataParsingError: If files cannot be parsed
        """
        pass
    
    @abstractmethod
    def get_metadata_extension(self) -> str:
        """Return metadata file extension (e.g., '.par')."""
        pass
    
    @abstractmethod
    def get_data_extension(self) -> str:
        """Return data file extension (e.g., '.par.csv')."""
        pass
    
    def validate_dual_files(self, metadata_path: Path, data_path: Path) -> bool:
        """
        Validate dual file pair.
        
        Args:
            metadata_path: Path to metadata file
            data_path: Path to data file
            
        Returns:
            True if both files are valid, False otherwise
        """
        try:
            # Check both files individually
            if not self.can_parse(metadata_path):
                return False
            
            if not self.can_parse(data_path):
                return False
            
            # Check file pairing (optional override in subclasses)
            return self._validate_file_pairing(metadata_path, data_path)
            
        except Exception as e:
            logger.debug(f"Dual file validation failed: {e}")
            return False
    
    def _validate_file_pairing(self, metadata_path: Path, data_path: Path) -> bool:
        """
        Validate that metadata and data files are properly paired.
        Default implementation checks filename matching.
        """
        # Default: check if data file name starts with metadata file name
        metadata_stem = metadata_path.stem
        data_name = data_path.name
        
        return data_name.startswith(metadata_stem)
    
    def find_paired_file(self, file_path: Path) -> Optional[Path]:
        """
        Find the paired file for a given file.
        
        Args:
            file_path: Path to one file of the pair
            
        Returns:
            Path to paired file if found, None otherwise
        """
        try:
            if str(file_path).endswith(self.get_metadata_extension()):
                # This is metadata file, look for data file
                data_name = file_path.name + self.get_data_extension().replace('.', '')
                data_path = file_path.parent / data_name
                return data_path if data_path.exists() else None
                
            elif str(file_path).endswith(self.get_data_extension()):
                # This is data file, look for metadata file
                metadata_name = file_path.name.replace(self.get_data_extension(), 
                                                     self.get_metadata_extension())
                metadata_path = file_path.parent / metadata_name
                return metadata_path if metadata_path.exists() else None
            
            return None
            
        except Exception as e:
            logger.debug(f"Cannot find paired file for {file_path}: {e}")
            return None


class SingleFileParser(BaseParser):
    """
    Abstract parser for instruments with single files.
    
    Examples:
    - BioLogic: .mpr files contain both metadata and data
    - Future single-file formats
    """
    
    def parse_file(self, file_path: Path) -> DataFile:
        """
        Parse single file and return universal schema DataFile.
        This is an alias for parse_data for consistency.
        
        Args:
            file_path: Path to file to parse
            
        Returns:
            DataFile with universal schema DataFrame
        """
        return self.parse_data(file_path)