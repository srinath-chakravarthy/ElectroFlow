"""
Parser factory and registry for automatic parser selection.

This module provides automatic detection and selection of the appropriate
parser based on file format and content.
"""

from pathlib import Path
from typing import List, Type, Optional
import logging

from .parsers import BaseParser, VersaStudioParser, ParserError
from .data_models import DataFile

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registry for all available parsers."""

    def __init__(self):
        self._parsers: List[Type[BaseParser]] = []
        self._register_default_parsers()

    def _register_default_parsers(self):
        """Register all built-in parsers."""
        self.register_parser(VersaStudioParser)
        # Future parsers will be added here:
        # self.register_parser(BiologicParser)


        # self.register_parser(GamryParser)

    def register_parser(self, parser_class: Type[BaseParser]):
        """
        Register a new parser class.

        Args:
            parser_class: Parser class that inherits from BaseParser
        """
        if not issubclass(parser_class, BaseParser):
            raise ValueError(f"Parser {parser_class} must inherit from BaseParser")

        self._parsers.append(parser_class)
        logger.info(f"Registered parser: {parser_class.__name__}")

    def get_parser_for_file(self, file_path: Path) -> Optional[BaseParser]:
        """
        Find the appropriate parser for a given file.

        Args:
            file_path: Path to the data file

        Returns:
            Parser instance that can handle the file, or None if no parser found
        """
        for parser_class in self._parsers:
            parser = parser_class()
            if parser.validate_file(file_path):
                logger.info(f"Selected parser {parser_class.__name__} for {file_path}")
                return parser

        logger.warning(f"No parser found for file: {file_path}")
        return None

    def list_supported_extensions(self) -> List[str]:
        """Get list of all supported file extensions."""
        extensions = set()

        # This is a simple heuristic - in the future we might want
        # parsers to explicitly declare their supported extensions
        for parser_class in self._parsers:
            if parser_class.__name__ == "VersaStudioParser":
                extensions.add(".par")
            # Add other known extensions here

        return sorted(list(extensions))


# Global registry instance
_parser_registry = ParserRegistry()


def parse_file(file_path: Path) -> DataFile:
    """
    Automatically detect file format and parse with appropriate parser.

    Args:
        file_path: Path to the instrument data file

    Returns:
        DataFile object with standardized data

    Raises:
        ParserError: If no suitable parser found or parsing fails
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Find appropriate parser
    parser = _parser_registry.get_parser_for_file(file_path)

    if parser is None:
        supported_extensions = _parser_registry.list_supported_extensions()
        raise ParserError(
            f"No parser available for file: {file_path}. "
            f"Supported extensions: {supported_extensions}"
        )

    # Parse the file
    try:
        return parser.parse(file_path)
    except Exception as e:
        raise ParserError(f"Failed to parse {file_path} with {parser.__class__.__name__}: {e}") from e


def register_parser(parser_class: Type[BaseParser]):
    """
    Register a custom parser class.

    Args:
        parser_class: Parser class that inherits from BaseParser
    """
    _parser_registry.register_parser(parser_class)


def get_supported_extensions() -> List[str]:
    """Get list of all supported file extensions."""
    return _parser_registry.list_supported_extensions()


# Convenience functions for specific parsers
def parse_versastudio_file(file_path: Path) -> DataFile:
    """
    Parse a VersaStudio .par file specifically.

    Args:
        file_path: Path to the .par file

    Returns:
        DataFile object

    Raises:
        ParserError: If parsing fails
    """
    parser = VersaStudioParser()
    return parser.parse(file_path)


# For backwards compatibility
parse_par_file = parse_versastudio_file