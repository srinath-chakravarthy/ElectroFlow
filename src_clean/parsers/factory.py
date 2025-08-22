"""
Parser Factory - Electrochemical Analysis Suite

Auto-detection and creation of appropriate parsers for different instruments.

Key Principles:
- Automatic instrument detection
- Clean parser registration system
- Graceful fallback for unknown formats
- Extensible for future instruments
"""

from pathlib import Path
from typing import Dict, List, Type, Optional
import logging

from .base import BaseParser, DualFileParser, SingleFileParser
from ..core.exceptions import UnsupportedInstrumentError, ParsingError

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registry for all available parsers."""
    
    def __init__(self):
        self._parsers: Dict[str, Type[BaseParser]] = {}
        self._dual_file_parsers: Dict[str, Type[DualFileParser]] = {}
        self._single_file_parsers: Dict[str, Type[SingleFileParser]] = {}
    
    def register_parser(self, parser_class: Type[BaseParser]) -> None:
        """Register a parser class."""
        # Create instance to get info
        parser_instance = parser_class()
        instrument_name = parser_instance.get_instrument_name()
        
        self._parsers[instrument_name] = parser_class
        
        # Register by type for specific workflows
        if isinstance(parser_instance, DualFileParser):
            self._dual_file_parsers[instrument_name] = parser_class
        elif isinstance(parser_instance, SingleFileParser):
            self._single_file_parsers[instrument_name] = parser_class
        
        logger.info(f"Registered parser: {instrument_name} ({parser_class.__name__})")
    
    def get_parser(self, instrument_name: str) -> Optional[Type[BaseParser]]:
        """Get parser class by instrument name."""
        return self._parsers.get(instrument_name)
    
    def get_dual_file_parser(self, instrument_name: str) -> Optional[Type[DualFileParser]]:
        """Get dual file parser by instrument name."""
        return self._dual_file_parsers.get(instrument_name)
    
    def get_single_file_parser(self, instrument_name: str) -> Optional[Type[SingleFileParser]]:
        """Get single file parser by instrument name."""
        return self._single_file_parsers.get(instrument_name)
    
    def get_all_parsers(self) -> Dict[str, Type[BaseParser]]:
        """Get all registered parsers."""
        return self._parsers.copy()
    
    def get_supported_instruments(self) -> List[str]:
        """Get list of supported instrument names."""
        return list(self._parsers.keys())
    
    def detect_instrument(self, file_path: Path) -> Optional[str]:
        """
        Auto-detect instrument type from file.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            Instrument name if detected, None otherwise
        """
        for instrument_name, parser_class in self._parsers.items():
            try:
                parser_instance = parser_class()
                if parser_instance.can_parse(file_path):
                    logger.debug(f"Detected instrument: {instrument_name} for {file_path}")
                    return instrument_name
            except Exception as e:
                logger.debug(f"Parser {instrument_name} failed detection for {file_path}: {e}")
                continue
        
        logger.debug(f"No parser found for {file_path}")
        return None


# Global parser registry
_parser_registry = ParserRegistry()


class ParserFactory:
    """Factory for creating parsers and detecting file formats."""
    
    def __init__(self, registry: ParserRegistry = None):
        self.registry = registry or _parser_registry
    
    def create_parser(self, instrument_name: str) -> BaseParser:
        """
        Create parser instance for specific instrument.
        
        Args:
            instrument_name: Name of instrument (e.g., 'VersaStudio')
            
        Returns:
            Parser instance
            
        Raises:
            UnsupportedInstrumentError: If instrument not supported
        """
        parser_class = self.registry.get_parser(instrument_name)
        if not parser_class:
            supported = self.registry.get_supported_instruments()
            raise UnsupportedInstrumentError(instrument_name, supported)
        
        return parser_class()
    
    def auto_detect_parser(self, file_path: Path) -> BaseParser:
        """
        Auto-detect and create appropriate parser for file.
        
        Args:
            file_path: Path to file to parse
            
        Returns:
            Parser instance that can handle the file
            
        Raises:
            UnsupportedInstrumentError: If no parser can handle file
        """
        instrument_name = self.registry.detect_instrument(file_path)
        if not instrument_name:
            supported = self.registry.get_supported_instruments()
            raise UnsupportedInstrumentError("Unknown", supported)
        
        return self.create_parser(instrument_name)
    
    def get_dual_file_parser(self, instrument_name: str) -> DualFileParser:
        """
        Create dual file parser for specific instrument.
        
        Args:
            instrument_name: Name of instrument
            
        Returns:
            DualFileParser instance
            
        Raises:
            UnsupportedInstrumentError: If instrument doesn't support dual files
        """
        parser_class = self.registry.get_dual_file_parser(instrument_name)
        if not parser_class:
            raise UnsupportedInstrumentError(
                f"{instrument_name} (dual file mode)", 
                list(self.registry._dual_file_parsers.keys())
            )
        
        return parser_class()
    
    def get_single_file_parser(self, instrument_name: str) -> SingleFileParser:
        """
        Create single file parser for specific instrument.
        
        Args:
            instrument_name: Name of instrument
            
        Returns:
            SingleFileParser instance
            
        Raises:
            UnsupportedInstrumentError: If instrument doesn't support single files
        """
        parser_class = self.registry.get_single_file_parser(instrument_name)
        if not parser_class:
            raise UnsupportedInstrumentError(
                f"{instrument_name} (single file mode)",
                list(self.registry._single_file_parsers.keys())
            )
        
        return parser_class()
    
    def find_paired_files(self, file_path: Path) -> Optional[Dict[str, Path]]:
        """
        Find paired files for dual file instruments.
        
        Args:
            file_path: Path to one file of the pair
            
        Returns:
            Dict with 'metadata' and 'data' paths if found, None otherwise
        """
        for instrument_name in self.registry._dual_file_parsers.keys():
            try:
                parser = self.get_dual_file_parser(instrument_name)
                
                if parser.can_parse(file_path):
                    paired_file = parser.find_paired_file(file_path)
                    if paired_file and paired_file.exists():
                        # Determine which is metadata and which is data
                        if str(file_path).endswith(parser.get_metadata_extension()):
                            return {
                                'metadata': file_path,
                                'data': paired_file
                            }
                        else:
                            return {
                                'metadata': paired_file,
                                'data': file_path
                            }
            except Exception as e:
                logger.debug(f"Error finding paired files with {instrument_name}: {e}")
                continue
        
        return None
    
    def get_supported_extensions(self) -> Dict[str, List[str]]:
        """
        Get supported file extensions by instrument.
        
        Returns:
            Dict mapping instrument names to their supported extensions
        """
        extensions = {}
        for instrument_name, parser_class in self.registry.get_all_parsers().items():
            parser_instance = parser_class()
            extensions[instrument_name] = parser_instance.get_supported_extensions()
        
        return extensions
    
    def get_parser_info(self) -> Dict[str, Dict[str, any]]:
        """
        Get information about all registered parsers.
        
        Returns:
            Dict with parser information
        """
        info = {}
        for instrument_name, parser_class in self.registry.get_all_parsers().items():
            parser_instance = parser_class()
            info[instrument_name] = parser_instance.get_parser_info()
        
        return info


def register_parser(parser_class: Type[BaseParser]) -> None:
    """Register a parser class globally."""
    _parser_registry.register_parser(parser_class)


def get_parser_factory() -> ParserFactory:
    """Get the global parser factory instance."""
    return ParserFactory(_parser_registry)


def auto_parse_file(file_path: Path):
    """
    Convenience function to auto-detect and parse a file.
    
    Args:
        file_path: Path to file to parse
        
    Returns:
        DataFile with universal schema
        
    Raises:
        UnsupportedInstrumentError: If no parser can handle file
        ParsingError: If parsing fails
    """
    factory = get_parser_factory()
    parser = factory.auto_detect_parser(file_path)
    return parser.parse_data(file_path)


def auto_parse_dual_files(metadata_path: Path, data_path: Path):
    """
    Convenience function to auto-detect and parse dual files.
    
    Args:
        metadata_path: Path to metadata file
        data_path: Path to data file
        
    Returns:
        DataFile with universal schema
        
    Raises:
        UnsupportedInstrumentError: If no dual file parser can handle files
        ParsingError: If parsing fails
    """
    factory = get_parser_factory()
    
    # Try to detect instrument from either file
    instrument_name = _parser_registry.detect_instrument(metadata_path)
    if not instrument_name:
        instrument_name = _parser_registry.detect_instrument(data_path)
    
    if not instrument_name:
        supported = list(_parser_registry._dual_file_parsers.keys())
        raise UnsupportedInstrumentError("Unknown", supported)
    
    parser = factory.get_dual_file_parser(instrument_name)
    return parser.parse_dual_files(metadata_path, data_path)