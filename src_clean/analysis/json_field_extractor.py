"""
JSON Field Extractor - Auto-Discovery Field Extraction

ElectrochemicalInsights 2.0 foundation component that uses analytics_config 
to dynamically extract JSON fields without hard-coding field names.

This replaces hard-coded field extraction throughout the registry analysis functions.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
import json
from datetime import datetime

from .analytics_config import get_config as get_analytics_config

logger = logging.getLogger(__name__)


class JSONFieldExtractor:
    """
    Auto-discovery JSON field extraction using analytics_config schemas.
    
    Eliminates hard-coding of field names in registry analysis functions by
    dynamically extracting fields based on analytics_config definitions.
    """
    
    def __init__(self):
        """Initialize with current analytics configuration."""
        self.config = get_analytics_config()
        self.logger = logger
        
        # Cache schema information for performance
        self._schema_cache = {}
        self._field_metadata_cache = {}
        self._load_schema_cache()
    
    def _load_schema_cache(self):
        """Pre-load schema information for fast lookup."""
        try:
            schemas = self.config.get('analysis_result_schemas', {})
            for schema_name, schema_info in schemas.items():
                self._schema_cache[schema_name] = schema_info
                self._field_metadata_cache[schema_name] = schema_info.get('fields', {})
        except Exception as e:
            self.logger.error(f"Failed to load schema cache: {e}")
    
    def extract_all_fields(self, analysis_results: dict, schema_name: str) -> dict:
        """
        Extract all fields from analytics_config schema dynamically.
        
        Args:
            analysis_results: JSON analysis results from database
            schema_name: Schema name from analytics_config (e.g., 'current_pulse')
            
        Returns:
            Dictionary with all available fields from the schema
        """
        try:
            if not analysis_results or not isinstance(analysis_results, dict):
                return {}
            
            # Handle string JSON that needs parsing
            if isinstance(analysis_results, str):
                try:
                    analysis_results = json.loads(analysis_results)
                except json.JSONDecodeError:
                    return {}
            
            # Get field definitions for this schema
            field_metadata = self._field_metadata_cache.get(schema_name, {})
            if not field_metadata:
                self.logger.warning(f"No field metadata found for schema: {schema_name}")
                return {}
            
            extracted = {}
            
            # Extract each field defined in the schema
            for field_name, field_info in field_metadata.items():
                value = self.extract_with_fallbacks(analysis_results, [f"{schema_name}.{field_name}", field_name])
                if value is not None:
                    # Type validation based on schema
                    field_type = field_info.get('type', 'string')
                    validated_value = self._validate_field_type(value, field_type, field_name)
                    if validated_value is not None:
                        extracted[field_name] = validated_value
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"Error extracting fields from schema {schema_name}: {e}")
            return {}
    
    def get_available_fields(self, schema_name: str) -> dict:
        """
        Get metadata for all fields in a schema.
        
        Args:
            schema_name: Schema name from analytics_config
            
        Returns:
            Dictionary of field metadata with types, units, descriptions
        """
        return self._field_metadata_cache.get(schema_name, {})
    
    def extract_with_quality(self, analysis_results: dict, schema_name: str) -> Tuple[dict, float]:
        """
        Extract fields with quality assessment.
        
        Args:
            analysis_results: JSON analysis results
            schema_name: Schema name from analytics_config
            
        Returns:
            Tuple of (extracted_fields, quality_score)
            Quality score: 0.0 (no data) to 1.0 (all fields present)
        """
        extracted = self.extract_all_fields(analysis_results, schema_name)
        available_fields = self.get_available_fields(schema_name)
        
        if not available_fields:
            return extracted, 0.0
        
        # Calculate quality as percentage of available fields that were extracted
        quality_score = len(extracted) / len(available_fields)
        
        return extracted, quality_score
    
    def get_schema_names(self) -> List[str]:
        """Get list of all available schema names."""
        return list(self._schema_cache.keys())
    
    def extract_with_fallbacks(self, analysis_results: dict, field_paths: List[str]) -> Any:
        """
        Extract field with graceful fallbacks for nested structures.
        
        Args:
            analysis_results: JSON analysis results
            field_paths: List of field paths to try (e.g., ['voltage_infinity', 'end_voltage_v'])
            
        Returns:
            First available value or None
        """
        if not analysis_results or not isinstance(analysis_results, dict):
            return None
        
        for field_path in field_paths:
            # Handle nested field paths (e.g., 'exponential_fit.voltage_infinity')
            if '.' in field_path:
                parts = field_path.split('.')
                current = analysis_results
                try:
                    for part in parts:
                        current = current[part]
                    if current is not None:
                        return current
                except (KeyError, TypeError):
                    continue
            else:
                # Simple field access
                value = analysis_results.get(field_path)
                if value is not None:
                    return value
        
        return None
    
    def _validate_field_type(self, value: Any, expected_type: str, field_name: str) -> Optional[Any]:
        """
        Validate and convert field value to expected type.
        
        Args:
            value: Raw value from JSON
            expected_type: Expected type from schema
            field_name: Field name for error reporting
            
        Returns:
            Validated value or None if validation fails
        """
        try:
            if expected_type == 'float':
                return float(value) if value is not None else None
            elif expected_type == 'int':
                return int(value) if value is not None else None
            elif expected_type == 'bool':
                return bool(value) if value is not None else None
            elif expected_type == 'string' or expected_type == 'str':
                return str(value) if value is not None else None
            elif expected_type == 'json':
                # JSON fields can be dict or string
                if isinstance(value, dict):
                    return value
                elif isinstance(value, str):
                    return json.loads(value)
                else:
                    return value
            else:
                # Unknown type, return as-is
                return value
                
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            self.logger.warning(f"Type validation failed for field {field_name}: {e}")
            return None
    
    def extract_multiple_schemas(self, analysis_results: dict, schema_names: List[str]) -> dict:
        """
        Extract fields from multiple schemas at once.
        
        Args:
            analysis_results: JSON analysis results
            schema_names: List of schema names to extract from
            
        Returns:
            Dictionary with schema_name -> extracted_fields mapping
        """
        results = {}
        for schema_name in schema_names:
            results[schema_name] = self.extract_all_fields(analysis_results, schema_name)
        return results
    
    def get_field_units(self, schema_name: str, field_name: str) -> Optional[str]:
        """
        Get units for a specific field.
        
        Args:
            schema_name: Schema name
            field_name: Field name
            
        Returns:
            Units string or None
        """
        field_metadata = self._field_metadata_cache.get(schema_name, {})
        field_info = field_metadata.get(field_name, {})
        return field_info.get('unit')
    
    def get_field_description(self, schema_name: str, field_name: str) -> Optional[str]:
        """
        Get description for a specific field.
        
        Args:
            schema_name: Schema name
            field_name: Field name
            
        Returns:
            Description string or None
        """
        field_metadata = self._field_metadata_cache.get(schema_name, {})
        field_info = field_metadata.get(field_name, {})
        return field_info.get('description')
    
    def diagnose_extraction(self, analysis_results: dict, schema_name: str) -> dict:
        """
        Diagnostic information about field extraction for debugging.
        
        Args:
            analysis_results: JSON analysis results
            schema_name: Schema name to diagnose
            
        Returns:
            Dictionary with diagnostic information
        """
        available_fields = self.get_available_fields(schema_name)
        extracted_fields = self.extract_all_fields(analysis_results, schema_name)
        
        # Find what's available in the data vs schema
        data_fields = set(analysis_results.keys()) if analysis_results else set()
        schema_fields = set(available_fields.keys())
        
        return {
            'schema_name': schema_name,
            'schema_fields_available': list(schema_fields),
            'data_fields_present': list(data_fields),
            'successfully_extracted': list(extracted_fields.keys()),
            'schema_fields_missing_from_data': list(schema_fields - data_fields),
            'data_fields_not_in_schema': list(data_fields - schema_fields),
            'extraction_coverage': len(extracted_fields) / len(schema_fields) if schema_fields else 0.0
        }


# Global instance for convenient access
_json_field_extractor = None

def get_json_field_extractor() -> JSONFieldExtractor:
    """Get global JSON field extractor instance."""
    global _json_field_extractor
    if _json_field_extractor is None:
        _json_field_extractor = JSONFieldExtractor()
    return _json_field_extractor