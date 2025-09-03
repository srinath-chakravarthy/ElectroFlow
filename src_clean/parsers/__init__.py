"""
Parsers Module - Electrochemical Analysis Suite

Universal parser framework for multiple instrument support.
"""

from .base import BaseParser, DualFileParser, SingleFileParser
from .factory import (
    ParserFactory, ParserRegistry, register_parser, 
    get_parser_factory, auto_parse_file, auto_parse_dual_files
)
from .versastudio import VersaStudioParser
from .biologic import BiologicParser

# Register all available parsers
register_parser(VersaStudioParser)
register_parser(BiologicParser)

__all__ = [
    'BaseParser',
    'DualFileParser', 
    'SingleFileParser',
    'ParserFactory',
    'ParserRegistry',
    'VersaStudioParser',
    'register_parser',
    'get_parser_factory',
    'auto_parse_file',
    'auto_parse_dual_files'
]