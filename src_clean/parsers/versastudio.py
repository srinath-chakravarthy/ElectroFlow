"""
VersaStudio Parser - Electrochemical Analysis Suite

Clean VersaStudio implementation with dual file processing (.par + .par.csv).

Key Principles:
- .par files: metadata only (skip all segment data)
- .par.csv files: calibrated data with VERSASTUDIO_CSV_SCHEMA
- Universal schema output
- Robust error handling
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import polars as pl


from .base import DualFileParser
from .configs.universal_schema import get_column_units
from .configs.versastudio_mappings import VERSASTUDIO_CSV_SCHEMA, VERSASTUDIO_CSV_MAPPING
from ..core.data_models import DataFile, FileMetadata, add_missing_universal_columns
from ..core.universal_processor import UniversalProcessor
from ..core.exceptions import (
    MetadataExtractionError, DataParsingError
)

logger = logging.getLogger(__name__)


class VersaStudioParser(DualFileParser):
    """Parser for VersaStudio (.par + .par.csv) files."""
    
    PARSER_VERSION = "2.0.0"
    
    def __init__(self):
        super().__init__()
        self.universal_processor = UniversalProcessor()
    
    def get_instrument_name(self) -> str:
        return "VersaStudio"
    
    def get_supported_extensions(self) -> List[str]:
        return ['.par', '.par.csv']
    
    def get_metadata_extension(self) -> str:
        return '.par'
    
    def get_data_extension(self) -> str:
        return '.par.csv'
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate VersaStudio file format."""
        try:
            self._validate_file_exists(file_path)
            
            if str(file_path).lower().endswith('.par'):
                return self._validate_par_file(file_path)
            elif str(file_path).lower().endswith('.par.csv'):
                return self._validate_csv_file(file_path)
            
            return False
            
        except Exception as e:
            logger.debug(f"VersaStudio validation failed for {file_path}: {e}")
            return False
    
    def _validate_par_file(self, file_path: Path) -> bool:
        """Validate .par file format."""
        try:
            content = self._safe_read_file(file_path)
            
            # Check for VersaStudio-specific headers
            required_patterns = [
                r'VERSION',
                r'DATE ACQUIRED',
                r'TIME ACQUIRED',
                r'NOTES'
            ]
            
            for pattern in required_patterns:
                if not re.search(pattern, content, re.IGNORECASE):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_csv_file(self, file_path: Path) -> bool:
        """Validate .par.csv file format."""
        try:
            # Read first few lines to check headers
            with open(file_path, 'r') as f:
                header = f.readline().strip()
            
            # Check for key VersaStudio CSV columns
            required_columns = ['Potential (V)', 'Current (A)', 'Elapsed Time (s)']
            return all(col in header for col in required_columns)
            
        except Exception:
            return False
    
    def parse_metadata(self, file_path: Path) -> FileMetadata:
        """Extract metadata from .par file."""
        try:
            content = self._safe_read_file(file_path)
            
            # Extract basic metadata
            metadata = {}
            
            # Version information
            version_match = re.search(r'VERSION\s+(.+)', content, re.IGNORECASE)
            software_version = version_match.group(1).strip() if version_match else "Unknown"
            
            # Date and time - handle both old and new VersaStudio formats
            date_match = re.search(r'DateAcquired=(.+)', content) or re.search(r'DATE ACQUIRED\s+(.+)', content, re.IGNORECASE)
            time_match = re.search(r'TimeAcquired=(.+)', content) or re.search(r'TIME ACQUIRED\s+(.+)', content, re.IGNORECASE)
            
            if date_match and time_match:
                date_str = date_match.group(1).strip()
                time_str = time_match.group(1).strip()
                
                # Try multiple datetime formats
                datetime_formats = [
                    "%A, %B %d, %Y %I:%M:%S %p",    # Monday, April 7, 2025 12:41:57 PM
                    "%m/%d/%Y %H:%M:%S",             # 04/07/2025 12:41:57
                    "%d/%m/%Y %H:%M:%S",             # 07/04/2025 12:41:57
                    "%Y-%m-%d %H:%M:%S",             # 2025-04-07 12:41:57
                    "%m/%d/%Y %I:%M:%S %p",          # 04/07/2025 12:41:57 PM
                    "%d/%m/%Y %I:%M:%S %p"           # 07/04/2025 12:41:57 PM
                ]
                
                acquisition_start = None
                for fmt in datetime_formats:
                    try:
                        acquisition_start = datetime.strptime(f"{date_str} {time_str}", fmt)
                        logger.debug(f"Parsed timestamp with format: {fmt}")
                        break
                    except ValueError:
                        continue
                
                if acquisition_start is None:
                    logger.warning(f"Could not parse timestamp: '{date_str} {time_str}' - using current time")
                    acquisition_start = datetime.now()
            else:
                logger.warning(f"Date/time not found in file - using current time")
                acquisition_start = datetime.now()
            
            # Notes
            notes_match = re.search(r'NOTES\s+(.+?)(?=\n[A-Z]|\Z)', content, re.IGNORECASE | re.DOTALL)
            notes = notes_match.group(1).strip() if notes_match else ""
            
            # Extract ActionID mappings
            actionid_mappings = self._extract_actionid_mappings(content)
            
            # Calculate technique count
            technique_count = len(actionid_mappings)
            
            return FileMetadata(
                original_filename=file_path.name,
                file_hash=self._calculate_file_hash(file_path),
                file_size_bytes=file_path.stat().st_size,
                parser_version=self.PARSER_VERSION,
                acquisition_start=acquisition_start,
                acquisition_duration_s=0.0,  # Will be calculated from data
                instrument_model="VersaStudio",
                software_version=software_version,
                total_points=0,  # Will be calculated from data
                technique_count=technique_count,
                actionid_mappings=actionid_mappings,
                notes=notes,
                user_metadata=metadata
            )
            
        except Exception as e:
            raise MetadataExtractionError(str(file_path), ["acquisition_start", "actionid_mappings"])
    
    def _safe_read_file(self, file_path: Path, encoding: str = 'utf-8') -> str:
        """Override base method with VersaStudio-specific optimization."""
        try:
            self._validate_file_exists(file_path)
            
            with open(file_path, 'r', encoding=encoding) as f:
                # For .par files, skip <Segment>...</Segment> blocks which contain raw data
                if str(file_path).lower().endswith('.par'):
                    return self._read_versastudio_metadata_only(f)
                else:
                    return f.read()
                    
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    if str(file_path).lower().endswith('.par'):
                        return self._read_versastudio_metadata_only(f)
                    else:
                        return f.read()
            except Exception as e:
                raise DataParsingError(
                    str(file_path),
                    "file content", 
                    f"Cannot read file: {str(e)}"
                )
        except Exception as e:
            raise DataParsingError(
                str(file_path),
                "file content", 
                f"Cannot read file: {str(e)}"
            )
    
    def _read_versastudio_metadata_only(self, file_obj) -> str:
        """Read VersaStudio .par file but skip <Segment>...</Segment> blocks to avoid loading raw data."""
        content_lines = []
        skip_segment = False
        
        for line in file_obj:
            # Check for VersaStudio segment start/end tags (case insensitive)
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

    def _extract_actionid_mappings(self, content: str) -> Dict[int, str]:
        """Extract ActionID mappings from .par file content."""
        mappings = {}
        
        # Look for action definitions (various formats in VersaStudio)
        action_patterns = [
            r'ACTION\s+(\d+)\s+(.+)',
            r'STEP\s+(\d+)\s+(.+)',
            r'(\d+)\s+(\w+(?:\s+\w+)*)'  # Generic number + technique name
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    action_id = int(match[0])
                    technique_name = match[1].strip()
                    
                    # Clean up technique name
                    technique_name = re.sub(r'\s+', ' ', technique_name)
                    technique_name = technique_name.replace('\t', ' ')
                    
                    if technique_name and len(technique_name) > 1:
                        mappings[action_id] = technique_name
                        
                except (ValueError, IndexError):
                    continue
        
        return mappings
    
    def parse_data(self, file_path: Path) -> DataFile:
        """Parse .par.csv data file."""
        if not str(file_path).lower().endswith('.par.csv'):
            raise DataParsingError(str(file_path), "CSV data", "Expected .par.csv file")
        
        # For single data file, we need to create minimal metadata
        minimal_metadata = FileMetadata(
            original_filename=file_path.name,
            file_hash=self._calculate_file_hash(file_path),
            file_size_bytes=file_path.stat().st_size,
            parser_version=self.PARSER_VERSION,
            acquisition_start=datetime.now(),
            acquisition_duration_s=0.0,
            instrument_model="VersaStudio",
            software_version="Unknown",
            total_points=0,
            technique_count=0,
            actionid_mappings={}
        )
        
        return self._parse_csv_data(file_path, minimal_metadata)
    
    def parse_dual_files(self, metadata_path: Path, data_path: Path) -> DataFile:
        """Parse VersaStudio dual files (.par + .par.csv)."""
        try:
            # Extract metadata from .par file
            metadata = self.parse_metadata(metadata_path)
            
            # Parse data from .par.csv file with metadata context
            return self._parse_csv_data(data_path, metadata)
            
        except Exception as e:
            raise DataParsingError(
                f"{metadata_path} + {data_path}",
                "dual file processing",
                str(e)
            )
    
    def _parse_csv_data(self, csv_path: Path, metadata: FileMetadata) -> DataFile:
        """Parse CSV data with schema validation and universal conversion."""
        try:
            # Handle BOM and encoding issues by preprocessing the file
            clean_csv_path = self._clean_csv_file(csv_path)
            
            # Read CSV with explicit schema to ensure proper types
            df = pl.read_csv(
                clean_csv_path,
                schema=VERSASTUDIO_CSV_SCHEMA,
                null_values=["", "NULL", "null"]
            )
            
            if df.is_empty():
                raise DataParsingError(str(csv_path), "CSV data", "No data found in file")
            
            # Map to universal schema
            universal_df = self._map_to_universal_schema(df)
            
            # Convert units to universal standard
            universal_df = self._convert_units(universal_df)
            
            # Add computed columns using UniversalProcessor
            universal_df = self.universal_processor.add_computed_columns(universal_df)
            
            # Add physics integration using UniversalProcessor
            universal_df = self.universal_processor.add_physics_integration(universal_df)
            
            # Add missing universal columns
            universal_df = add_missing_universal_columns(universal_df)
            
            # VersaStudio enhancement: populate electrode-specific columns from available data
            universal_df = self._enhance_versastudio_electrode_columns(universal_df)
            
            # Add timestamps using UniversalProcessor
            universal_df = self.universal_processor.add_timestamps(universal_df, metadata.acquisition_start)
            
            # Update metadata with actual data statistics
            updated_metadata = self._update_metadata_from_data(metadata, universal_df)
            
            return DataFile(
                universal_data=universal_df,
                metadata=updated_metadata,
                processing_timestamp=datetime.now()
            )
            
        except Exception as e:
            raise DataParsingError(str(csv_path), "CSV data", str(e))
    
    def _clean_csv_file(self, csv_path: Path) -> Path:
        """Clean CSV file by removing BOM and other encoding artifacts."""
        import tempfile
        import codecs
        
        # Create temporary cleaned file
        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / f"cleaned_{csv_path.name}"
        
        try:
            # Read file with potential BOM handling
            with open(csv_path, 'r', encoding='utf-8-sig') as input_file:
                content = input_file.read()
            
            # Write clean content
            with open(temp_file, 'w', encoding='utf-8') as output_file:
                output_file.write(content)
            
            return temp_file
            
        except UnicodeDecodeError:
            # Fallback for other encoding issues
            try:
                with open(csv_path, 'r', encoding='utf-8') as input_file:
                    content = input_file.read()
                # Remove BOM manually if present
                if content.startswith('\ufeff'):
                    content = content[1:]
                
                with open(temp_file, 'w', encoding='utf-8') as output_file:
                    output_file.write(content)
                
                return temp_file
            except Exception:
                # If all else fails, return original file
                return csv_path
    
    def _map_to_universal_schema(self, df: pl.DataFrame) -> pl.DataFrame:
        """Map VersaStudio CSV columns to universal schema."""
        # Create mapping for available columns, avoiding duplicates
        column_mapping = {}
        used_universal_cols = set()
        
        for vs_col, config in VERSASTUDIO_CSV_MAPPING.items():
            if isinstance(config, dict) and 'universal' in config:
                universal_col = config['universal']
                if vs_col in df.columns and universal_col not in used_universal_cols:
                    column_mapping[vs_col] = universal_col
                    used_universal_cols.add(universal_col)
            elif isinstance(config, str):  # Backward compatibility
                if vs_col in df.columns and config not in used_universal_cols:
                    column_mapping[vs_col] = config
                    used_universal_cols.add(config)
        
        logger.debug(f"Column mapping: {column_mapping}")
        
        # Rename columns to universal schema
        mapped_df = df.rename(column_mapping)
        
        # Select only successfully mapped columns
        universal_columns = list(column_mapping.values())
        available_columns = [col for col in universal_columns if col in mapped_df.columns]
        
        return mapped_df.select(available_columns)
    
    def _convert_units(self, df: pl.DataFrame) -> pl.DataFrame:
        """Convert units from instrument units to universal schema units."""
        try:
            # Only import pint when needed to avoid startup overhead
            import pint
            ureg = pint.UnitRegistry()
            
            # Process each mapped column for unit conversion
            for vs_col, config in VERSASTUDIO_CSV_MAPPING.items():
                if not isinstance(config, dict) or 'universal' not in config or 'units' not in config:
                    continue
                    
                universal_col = config['universal']
                instrument_units = config['units']
                
                # Skip non-physical units
                if instrument_units in ['categorical', 'dimensionless']:
                    continue
                    
                # Check if this column exists in the DataFrame
                if universal_col not in df.columns:
                    continue
                
                # Get target units from universal schema
                try:
                    target_units = get_column_units(universal_col)
                except ValueError:
                    logger.warning(f"Universal column '{universal_col}' not found in schema")
                    continue
                
                # Skip if units are already the same
                if instrument_units == target_units:
                    continue
                
                # Perform unit conversion
                try:
                    conversion_factor = ureg(instrument_units).to(target_units).magnitude
                    df = df.with_columns([
                        (pl.col(universal_col) * conversion_factor).alias(universal_col)
                    ])
                    logger.debug(f"Converted {universal_col}: {instrument_units} → {target_units} (factor: {conversion_factor})")
                    
                except pint.errors.UndefinedUnitError:
                    logger.warning(f"Undefined unit '{instrument_units}' for column {universal_col}")
                    continue
                except pint.errors.DimensionalityError:
                    logger.warning(f"Incompatible units: cannot convert '{instrument_units}' to '{target_units}' for column {universal_col}")
                    continue
                    
            return df
            
        except ImportError:
            logger.warning("Pint library not available - skipping unit conversions")
            return df
        except Exception as e:
            logger.warning(f"Unit conversion failed: {e}")
            return df
    
    def _enhance_versastudio_electrode_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Enhance VersaStudio data with electrode-specific columns.
        
        VersaStudio provides cell-level measurements (2-electrode), so we populate:
        - working_electrode_potential_v from potential_v (cell voltage)  
        - WE impedance columns from cell impedance columns
        - CE impedance columns remain null (no separate CE data available)
        """
        expressions = []
        
        # Column 1: WE voltage from cell voltage
        if 'potential_v' in df.columns:
            expressions.append(
                pl.col('potential_v').alias('working_electrode_potential_v')
            )
        
        # Columns 2-5: WE impedance from cell impedance  
        impedance_mappings = {
            'impedance_real_ohm': 'we_impedance_real_ohm',
            'impedance_imag_ohm': 'we_impedance_imag_ohm', 
            'impedance_mag_ohm': 'we_impedance_mag_ohm',
            'impedance_phase_deg': 'we_impedance_phase_deg'
        }
        
        for source_col, target_col in impedance_mappings.items():
            if source_col in df.columns:
                expressions.append(
                    pl.col(source_col).alias(target_col)
                )
        
        # Apply all enhancements at once
        if expressions:
            df = df.with_columns(expressions)
        
        # CE impedance columns remain null (already handled by add_missing_universal_columns)
        return df

    def _update_metadata_from_data(self, metadata: FileMetadata, df: pl.DataFrame) -> FileMetadata:
        """Update metadata with statistics from actual data."""
        try:
            # Calculate duration from data
            if 'time_s' in df.columns:
                time_col = df.get_column('time_s')
                duration_s = float(time_col.max() - time_col.min()) if time_col.len() > 0 else 0.0
            else:
                duration_s = 0.0
            
            # Count unique techniques
            if 'technique_id' in df.columns:
                unique_techniques = df.get_column('technique_id').n_unique()
            else:
                unique_techniques = 1
            
            # Create updated metadata
            updated_metadata = FileMetadata(
                original_filename=metadata.original_filename,
                file_hash=metadata.file_hash,
                file_size_bytes=metadata.file_size_bytes,
                parser_version=metadata.parser_version,
                acquisition_start=metadata.acquisition_start,
                acquisition_duration_s=duration_s,
                instrument_model=metadata.instrument_model,
                software_version=metadata.software_version,
                total_points=df.height,
                technique_count=unique_techniques,
                actionid_mappings=metadata.actionid_mappings,
                notes=metadata.notes,
                temperature_c=metadata.temperature_c,
                user_metadata=metadata.user_metadata
            )
            
            return updated_metadata
            
        except Exception as e:
            logger.warning(f"Failed to update metadata from data: {e}")
            return metadata