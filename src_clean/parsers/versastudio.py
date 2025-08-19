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
from ..core.data_models import (
    DataFile, FileMetadata, UNIVERSAL_SCHEMA, 
    VERSASTUDIO_CSV_SCHEMA, VERSASTUDIO_CSV_MAPPING,
    VERSASTUDIO_COMPUTED_COLUMNS, add_missing_universal_columns
)
from ..core.exceptions import (
    FileFormatError, MetadataExtractionError, DataParsingError
)

logger = logging.getLogger(__name__)


class VersaStudioParser(DualFileParser):
    """Parser for VersaStudio (.par + .par.csv) files."""
    
    PARSER_VERSION = "2.0.0"
    
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
            
            # Date and time
            date_match = re.search(r'DATE ACQUIRED\s+(.+)', content, re.IGNORECASE)
            time_match = re.search(r'TIME ACQUIRED\s+(.+)', content, re.IGNORECASE)
            
            if date_match and time_match:
                date_str = date_match.group(1).strip()
                time_str = time_match.group(1).strip()
                try:
                    acquisition_start = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %H:%M:%S")
                except ValueError:
                    # Try alternative format
                    try:
                        acquisition_start = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
                    except ValueError:
                        acquisition_start = datetime.now()
            else:
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
            # Read CSV without forcing full schema to avoid data corruption
            df = pl.read_csv(
                csv_path,
                null_values=["", "NULL", "null"]
            )
            
            if df.is_empty():
                raise DataParsingError(str(csv_path), "CSV data", "No data found in file")
            
            # Map to universal schema
            universal_df = self._map_to_universal_schema(df)
            
            # Add computed columns
            universal_df = self._add_computed_columns(universal_df)
            
            # Add missing universal columns
            universal_df = add_missing_universal_columns(universal_df)
            
            # Add timestamps
            universal_df = self._add_timestamps(universal_df, metadata)
            
            # Update metadata with actual data statistics
            updated_metadata = self._update_metadata_from_data(metadata, universal_df)
            
            return DataFile(
                universal_data=universal_df,
                metadata=updated_metadata,
                processing_timestamp=datetime.now()
            )
            
        except Exception as e:
            raise DataParsingError(str(csv_path), "CSV data", str(e))
    
    def _map_to_universal_schema(self, df: pl.DataFrame) -> pl.DataFrame:
        """Map VersaStudio CSV columns to universal schema."""
        # Create mapping for available columns
        column_mapping = {}
        for vs_col, universal_col in VERSASTUDIO_CSV_MAPPING.items():
            if vs_col in df.columns:
                column_mapping[vs_col] = universal_col
        
        # Rename columns to universal schema
        mapped_df = df.rename(column_mapping)
        
        # Select only successfully mapped columns
        universal_columns = list(column_mapping.values())
        available_columns = [col for col in universal_columns if col in mapped_df.columns]
        
        return mapped_df.select(available_columns)
    
    def _add_computed_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add computed columns specific to VersaStudio."""
        try:
            computed_exprs = []
            
            # Power calculation (P = V * I)
            if 'potential_v' in df.columns and 'current_a' in df.columns:
                computed_exprs.append(
                    (pl.col('potential_v') * pl.col('current_a')).alias('power_w')
                )
            
            # Impedance magnitude
            if 'impedance_real_ohm' in df.columns and 'impedance_imag_ohm' in df.columns:
                computed_exprs.append(
                    (pl.col('impedance_real_ohm').pow(2) + pl.col('impedance_imag_ohm').pow(2)).sqrt().alias('impedance_mag_ohm')
                )
                
                # Impedance phase (in degrees)
                computed_exprs.append(
                    (pl.arctan2(pl.col('impedance_imag_ohm'), pl.col('impedance_real_ohm')) * 180 / 3.14159265359).alias('impedance_phase_deg')
                )
            
            if computed_exprs:
                df = df.with_columns(computed_exprs)
            
            return df
            
        except Exception as e:
            logger.warning(f"Failed to add computed columns: {e}")
            return df
    
    def _add_timestamps(self, df: pl.DataFrame, metadata: FileMetadata) -> pl.DataFrame:
        """Add absolute timestamps to data."""
        try:
            if 'time_s' in df.columns:
                # Create timestamps from acquisition start + elapsed time
                start_timestamp = metadata.acquisition_start
                
                df = df.with_columns([
                    (pl.lit(start_timestamp) + pl.duration(seconds=pl.col('time_s'))).alias('timestamp')
                ])
            else:
                # No time data available, use acquisition start for all points
                df = df.with_columns([
                    pl.lit(metadata.acquisition_start).alias('timestamp')
                ])
            
            return df
            
        except Exception as e:
            logger.warning(f"Failed to add timestamps: {e}")
            # Add null timestamp column
            return df.with_columns([
                pl.lit(None).cast(pl.Datetime).alias('timestamp')
            ])
    
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