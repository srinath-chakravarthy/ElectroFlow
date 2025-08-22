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
import numpy as np

# Scipy integration - handle deprecation
try:
    from scipy.integrate import trapezoid as integrate_trapz
except ImportError:
    from scipy.integrate import trapz as integrate_trapz

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
        
        for vs_col, universal_col in VERSASTUDIO_CSV_MAPPING.items():
            if vs_col in df.columns and universal_col not in used_universal_cols:
                column_mapping[vs_col] = universal_col
                used_universal_cols.add(universal_col)
        
        logger.debug(f"Column mapping: {column_mapping}")
        
        # Rename columns to universal schema
        mapped_df = df.rename(column_mapping)
        
        # Select only successfully mapped columns
        universal_columns = list(column_mapping.values())
        available_columns = [col for col in universal_columns if col in mapped_df.columns]
        
        return mapped_df.select(available_columns)
    
    def _add_computed_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add computed columns including physics-based capacity and energy integration."""
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
            
            # Apply basic computations first
            if computed_exprs:
                df = df.with_columns(computed_exprs)
            
            # Physics-based integration (requires segment grouping)
            if all(col in df.columns for col in ['time_s', 'current_a', 'segment_number']):
                df = self._add_integration_columns(df)
            
            return df
            
        except Exception as e:
            logger.warning(f"Failed to add computed columns: {e}")
            return df

    def _add_integration_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add segment-based integration using scipy trapezoid."""
        
        def integrate_segment_capacity(segment_df):
            """Integrate capacity for one segment using scipy trapezoidal rule."""
            # Ensure monotonic time before integration
            segment_df_sorted = segment_df.sort('time_s')
            segment_data = segment_df_sorted.to_pandas()  # Convert to pandas for numpy operations
            time_vals = segment_data['time_s'].values
            current_vals = segment_data['current_a'].values
            
            if len(time_vals) < 2:
                segment_data['capacity_ah'] = 0.0
                return pl.from_pandas(segment_data)
            
            # Scipy trapezoidal integration - cumulative within segment
            cumulative_capacity = np.zeros_like(time_vals)
            
            # For cumulative integration, use cumulative trapz
            for i in range(1, len(time_vals)):
                cumulative_capacity[i] = integrate_trapz(
                    current_vals[:i+1], time_vals[:i+1]
                ) / 3600.0
            
            segment_data['capacity_ah'] = cumulative_capacity
            return pl.from_pandas(segment_data)
        
        def integrate_segment_energy(segment_df):
            """Integrate energy for one segment using scipy trapezoidal rule."""
            if 'power_w' not in segment_df.columns:
                return segment_df.with_columns([pl.lit(0.0).alias('energy_wh')])
            
            # Ensure monotonic time before integration
            segment_df_sorted = segment_df.sort('time_s')
            segment_data = segment_df_sorted.to_pandas()
            time_vals = segment_data['time_s'].values
            power_vals = segment_data['power_w'].values
            
            if len(time_vals) < 2:
                segment_data['energy_wh'] = 0.0
                return pl.from_pandas(segment_data)
            
            # Scipy trapezoidal integration - cumulative within segment
            cumulative_energy = np.zeros_like(time_vals)
            for i in range(1, len(time_vals)):
                cumulative_energy[i] = integrate_trapz(
                    power_vals[:i+1], time_vals[:i+1]
                ) / 3600.0  # Convert Ws to Wh
            
            segment_data['energy_wh'] = cumulative_energy
            return pl.from_pandas(segment_data)
        
        # Apply segment-based integration
        df = df.group_by('segment_number', maintain_order=True).map_groups(integrate_segment_capacity)
        
        if 'power_w' in df.columns:
            df = df.group_by('segment_number', maintain_order=True).map_groups(integrate_segment_energy)
        else:
            df = df.with_columns([pl.lit(0.0).alias('energy_wh')])
        
        # Add file-level cumulative tracking
        df = self._add_cumulative_tracking(df)
        
        return df

    def _add_cumulative_tracking(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add file-level cumulative capacity and energy tracking."""
        
        # Get final values from each segment for cumulative tracking
        segment_totals = df.group_by('segment_number').agg([
            pl.col('capacity_ah').sort_by('time_s').last().alias('segment_capacity_final'),
            pl.col('energy_wh').sort_by('time_s').last().alias('segment_energy_final')
        ]).sort('segment_number')
        
        # Calculate cumulative values across segments
        segment_totals = segment_totals.with_columns([
            # Net cumulative
            pl.col('segment_capacity_final').cumsum().alias('capacity_cumulative_segment'),
            pl.col('segment_energy_final').cumsum().alias('energy_cumulative_segment'),
            
            # Charge cumulative (positive only)
            pl.col('segment_capacity_final').clip(lower_bound=0).cumsum().alias('charge_cumulative_segment'),
            pl.col('segment_energy_final').clip(lower_bound=0).cumsum().alias('energy_charge_cumulative_segment'),
            
            # Discharge cumulative (negative only)
            pl.col('segment_capacity_final').clip(upper_bound=0).cumsum().alias('discharge_cumulative_segment'),
            pl.col('segment_energy_final').clip(upper_bound=0).cumsum().alias('energy_discharge_cumulative_segment'),
            
            # Absolute cumulative
            pl.col('segment_capacity_final').abs().cumsum().alias('capacity_absolute_cumulative_segment'),
            pl.col('segment_energy_final').abs().cumsum().alias('energy_absolute_cumulative_segment')
        ])
        
        # Join back to main dataframe
        df = df.join(segment_totals, on='segment_number', how='left')
        
        # Convert to point-level cumulative (interpolate within segments)
        df = df.with_columns([
            # File-level cumulative = previous segments + current segment progress
            (pl.col('capacity_cumulative_segment') - pl.col('segment_capacity_final') + pl.col('capacity_ah')).alias('capacity_cumulative_ah'),
            (pl.col('energy_cumulative_segment') - pl.col('segment_energy_final') + pl.col('energy_wh')).alias('energy_cumulative_wh'),
            
            # Charge/discharge tracking
            (pl.col('charge_cumulative_segment') + pl.col('capacity_ah').clip(lower_bound=0)).alias('charge_cumulative_ah'),
            (pl.col('discharge_cumulative_segment') + pl.col('capacity_ah').clip(upper_bound=0)).alias('discharge_cumulative_ah'),
            
            # Energy equivalents
            (pl.col('energy_charge_cumulative_segment') + pl.col('energy_wh').clip(lower_bound=0)).alias('energy_charge_cumulative_wh'),
            (pl.col('energy_discharge_cumulative_segment') + pl.col('energy_wh').clip(upper_bound=0)).alias('energy_discharge_cumulative_wh'),
            
            # Absolute tracking
            (pl.col('capacity_absolute_cumulative_segment') + pl.col('capacity_ah').abs()).alias('capacity_absolute_cumulative_ah'),
            (pl.col('energy_absolute_cumulative_segment') + pl.col('energy_wh').abs()).alias('energy_absolute_cumulative_wh')
        ])
        
        # Clean up temporary columns
        df = df.drop([col for col in df.columns if col.endswith('_segment')])
        
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