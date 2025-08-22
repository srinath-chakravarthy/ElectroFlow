"""
Backend Module - Electrochemical Analysis Suite

Clean backend orchestration layer.
"""

from .api import BackendAPI, ProcessingResult, get_backend_api

__all__ = [
    'BackendAPI',
    'ProcessingResult', 
    'get_backend_api'
]