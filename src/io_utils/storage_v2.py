"""
Database-backed storage system for battery data files.

Replaces JSON-based metadata storage with SQLite database while maintaining
cell-based directory structure for raw data and processed files.
"""

import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import polars as pl
import sys

# Add src directory to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from core.data_models import DataFile, calculate_file_hash
from core.parsers import VersaStudioParser
from core.database import DatabaseManager, get_or_create_cell
from analysis.analytics import FundamentalAnalytics

logger = logging.getLogger(__name__)


class DatabaseStorageManager:
    """
    Database-backed storage manager for battery data files.
    
    Combines SQLite database for metadata with filesystem storage for data files.
    Supports both single .par files and dual file processing (.par + .par.csv).
    
    Storage structure:
    data/cells/CELL_NAME/
    ├── raw/                    # Original uploaded files (.par, .par.csv)
    ├── processed/              # Universal schema parquet files
    ├── analysis_results/       # Analysis JSON files  
    ├── exports/relaxis/        # EIS CSV exports
    └── user_groups/           # User-defined groupings (future)
    
    Database tables:
    - cells: Cell metadata and properties
    - files: File tracking and processing status
    - technique_segments: Segment-level technique mapping
    - user_groups: User-defined file groupings
    """

    def __init__(self, base_data_dir: Path = None, db_path: Path = None):
        """
        Initialize database-backed storage manager.
        
        Args:
            base_data_dir: Base directory for data storage (default: data/)
            db_path: Path to SQLite database (default: data/battery_analyzer.db)
        """
        self.base_data_dir = base_data_dir or Path("data")
        self.cells_dir = self.base_data_dir / "cells"
        self.cells_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = db_path or (self.base_data_dir / "battery_analyzer.db")
        self.db = DatabaseManager(self.db_path)
        
        # Initialize analytics engine
        self.analytics = FundamentalAnalytics()
        
        # Initialize parsers
        self.versastudio_parser = VersaStudioParser()
        
        logger.info(f"DatabaseStorageManager initialized with database: {self.db_path}")

    def create_cell(self, cell_name: str, description: str = "", chemistry: str = "", 
                   capacity_ah: Optional[float] = None, notes: str = "") -> int:
        """
        Create a new cell with database tracking.
        
        Args:
            cell_name: Unique cell identifier
            description: Cell description
            chemistry: Battery chemistry (e.g., 'Li-ion', 'LFP')
            capacity_ah: Nominal capacity in Ah
            notes: Additional notes
            
        Returns:
            cell_id: Database primary key for the cell
        """
        # Create cell in database
        cell_id = self.db.create_cell(cell_name, description, chemistry, capacity_ah, notes)
        
        # Create directory structure
        cell_dir = self.cells_dir / cell_name
        (cell_dir / "raw").mkdir(parents=True, exist_ok=True)
        (cell_dir / "processed").mkdir(parents=True, exist_ok=True)
        (cell_dir / "analysis_results").mkdir(parents=True, exist_ok=True)
        (cell_dir / "exports" / "relaxis").mkdir(parents=True, exist_ok=True)
        (cell_dir / "user_groups").mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created cell: {cell_name} (id={cell_id}) with directory structure")
        return cell_id

    def upload_file(self, source_file_path: Path, cell_name: str, 
                   file_type: str = "par", user_choice: str = "ask") -> Tuple[str, str]:
        """
        Upload a file to cell's raw directory with database tracking.
        
        Args:
            source_file_path: Path to source file
            cell_name: Target cell name
            file_type: File type ('par' or 'par_csv')
            user_choice: Duplicate handling ("replace", "keep_both", "skip", "ask")
            
        Returns:
            Tuple of (file_id, status) where status is "uploaded", "replaced", "skipped"
        """
        if not source_file_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file_path}")
        
        # Get or create cell
        cell_id, cell_created = get_or_create_cell(self.db, cell_name)
        if cell_created:
            # Create directory structure for new cell
            cell_dir = self.cells_dir / cell_name
            self._create_cell_directories(cell_dir)
        
        cell_dir = self.cells_dir / cell_name
        target_filename = source_file_path.name
        target_path = cell_dir / "raw" / target_filename
        
        # Check for duplicates
        if target_path.exists():
            if user_choice == "ask":
                print(f"File '{target_filename}' already exists in {cell_name}.")
                print("Options: (r)eplace, (k)eep both, (s)kip")
                choice = input("Choice [r/k/s]: ").lower()
                user_choice = {"r": "replace", "k": "keep_both", "s": "skip"}.get(choice, "skip")
            
            if user_choice == "replace":
                # Remove existing file from database and filesystem
                existing_file_id = f"{cell_name}_{target_path.stem}"
                self.db.delete_file(existing_file_id)
                target_path.unlink(missing_ok=True)
                status = "replaced"
            elif user_choice == "keep_both":
                # Add timestamp to new file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = target_path.stem
                suffix = target_path.suffix
                target_filename = f"{stem}_{timestamp}{suffix}"
                target_path = cell_dir / "raw" / target_filename
                status = "uploaded"
            else:  # skip
                return "", "skipped"
        else:
            status = "uploaded"
        
        # Copy file to target location
        shutil.copy2(source_file_path, target_path)
        
        # Calculate file hash and create file_id
        file_hash = calculate_file_hash(target_path)
        file_id = f"{cell_name}_{target_path.stem}"
        
        # Add file to database
        file_info = {
            'file_id': file_id,
            'original_filename': target_filename,
            'file_type': file_type,
            'file_hash': file_hash,
            'file_path': str(target_path),
            'metadata': {
                'upload_source': str(source_file_path),
                'upload_timestamp': datetime.now().isoformat()
            }
        }
        
        self.db.add_file_to_cell(cell_id, file_info)
        
        # Process file immediately
        try:
            self._process_file(file_id, cell_id, cell_name, target_path, file_type)
        except Exception as e:
            logger.error(f"Failed to process file {file_id}: {e}")
            self.db.update_processing_status(file_id, "failed", str(e))
        
        logger.info(f"Uploaded file: {file_id} → {cell_name} ({status})")
        return file_id, status

    def upload_dual_files(self, par_path: Path, csv_path: Path, cell_name: str,
                          user_choice: str = "ask") -> Tuple[List[str], str]:
        """
        Upload both .par and .par.csv files for dual processing.
        
        Args:
            par_path: Path to .par file
            csv_path: Path to .par.csv file  
            cell_name: Target cell name
            user_choice: Duplicate handling
            
        Returns:
            Tuple of (file_ids, status)
        """
        # Validate dual files
        if not self.versastudio_parser.validate_dual_files(par_path, csv_path):
            raise ValueError(f"Invalid dual file pair: {par_path.name} and {csv_path.name}")
        
        # Upload both files
        par_file_id, par_status = self.upload_file(par_path, cell_name, "par", user_choice)
        csv_file_id, csv_status = self.upload_file(csv_path, cell_name, "par_csv", user_choice)
        
        if par_status == "skipped" or csv_status == "skipped":
            return [], "skipped"
        
        # Process dual files together
        try:
            self._process_dual_files(par_file_id, csv_file_id, cell_name)
            return [par_file_id, csv_file_id], "uploaded"
        except Exception as e:
            logger.error(f"Failed to process dual files {par_file_id}, {csv_file_id}: {e}")
            return [par_file_id, csv_file_id], "failed"

    def _process_file(self, file_id: str, cell_id: int, cell_name: str, 
                     file_path: Path, file_type: str):
        """Process uploaded file with analytics."""
        self.db.update_processing_status(file_id, "processing")
        
        try:
            # Parse file
            if file_type == "par":
                data_file = self.versastudio_parser.parse(file_path)
            elif file_type == "par_csv":
                # For standalone CSV files, parse as calibrated data only
                calibrated_data = self.versastudio_parser.parse_calibrated_csv(file_path)
                # Create minimal DataFile for CSV-only processing
                data_file = DataFile(
                    file_path=file_path,
                    timestamp=datetime.now(),
                    universal_data=calibrated_data,
                    actions={},
                    segments={},
                    metadata={'processing_type': 'csv_only', 'data_quality': 'calibrated'}
                )
            else:
                raise ValueError(f"Unknown file type: {file_type}")
            
            # Save processed data
            processed_path = self.cells_dir / cell_name / "processed" / f"{file_id}.parquet"
            data_file.universal_data.write_parquet(processed_path)
            
            # Run analytics
            analysis_results = self.analytics.analyze_datafile(data_file.universal_data)
            
            # Save analysis results
            analysis_path = self.cells_dir / cell_name / "analysis_results" / f"{file_id}.json"
            with open(analysis_path, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            
            # Update database with processing results
            self.db.update_processing_status(
                file_id, "completed",
                processed_path=str(processed_path),
                analysis_path=str(analysis_path)
            )
            
            # Add technique segments to database
            if analysis_results:
                segments = self._extract_segments_from_analysis(data_file, analysis_results)
                if segments:
                    self.db.add_technique_segments(file_id, segments)
            
            # Export EIS data if present
            self._export_eis_data(data_file, cell_name, file_id)
            
            logger.info(f"Successfully processed file: {file_id}")
            
        except Exception as e:
            self.db.update_processing_status(file_id, "failed", str(e))
            raise

    def _process_dual_files(self, par_file_id: str, csv_file_id: str, cell_name: str):
        """Process dual .par and .par.csv files together."""
        # Get file paths
        par_file = self.db.get_file_by_id(par_file_id)
        csv_file = self.db.get_file_by_id(csv_file_id)
        
        if not par_file or not csv_file:
            raise ValueError("One or both files not found in database")
        
        par_path = Path(par_file['file_path'])
        csv_path = Path(csv_file['file_path'])
        
        # Update processing status for both files
        self.db.update_processing_status(par_file_id, "processing")
        self.db.update_processing_status(csv_file_id, "processing")
        
        try:
            # Parse dual files
            data_file = self.versastudio_parser.parse_dual_files(par_path, csv_path)
            
            # Use par_file_id as primary identifier for processed data
            primary_file_id = par_file_id
            
            # Save processed data
            processed_path = self.cells_dir / cell_name / "processed" / f"{primary_file_id}_dual.parquet"
            data_file.universal_data.write_parquet(processed_path)
            
            # Run analytics
            analysis_results = self.analytics.analyze_datafile(data_file.universal_data)
            
            # Save analysis results
            analysis_path = self.cells_dir / cell_name / "analysis_results" / f"{primary_file_id}_dual.json"
            with open(analysis_path, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            
            # Update database for both files
            self.db.update_processing_status(
                par_file_id, "completed",
                processed_path=str(processed_path),
                analysis_path=str(analysis_path)
            )
            self.db.update_processing_status(
                csv_file_id, "completed",
                processed_path=str(processed_path),  # Same processed file
                analysis_path=str(analysis_path)     # Same analysis file
            )
            
            # Add technique segments (from .par structure)
            if analysis_results:
                segments = self._extract_segments_from_analysis(data_file, analysis_results)
                if segments:
                    self.db.add_technique_segments(par_file_id, segments)
            
            # Export EIS data (from calibrated .csv data)
            self._export_eis_data(data_file, cell_name, primary_file_id)
            
            logger.info(f"Successfully processed dual files: {par_file_id}, {csv_file_id}")
            
        except Exception as e:
            self.db.update_processing_status(par_file_id, "failed", str(e))
            self.db.update_processing_status(csv_file_id, "failed", str(e))
            raise

    def _extract_segments_from_analysis(self, data_file: DataFile, 
                                      analysis_results: Dict) -> List[Dict[str, Any]]:
        """Extract segment information for database storage."""
        segments = []
        
        # Get unique segments from data
        if not data_file.universal_data.is_empty():
            segment_info = (
                data_file.universal_data
                .group_by(['segment_number', 'technique_id', 'technique_name', 'fundamental_technique'])
                .agg([
                    pl.col('time_s').min().alias('start_time_s'),
                    pl.col('time_s').max().alias('end_time_s'),
                    pl.len().alias('point_count')
                ])
                .sort('segment_number')
            )
            
            for row in segment_info.iter_rows(named=True):
                segment = {
                    'segment_number': row['segment_number'],
                    'action_id': row['technique_id'],
                    'technique_name': row['technique_name'],
                    'fundamental_technique': row['fundamental_technique'],
                    'start_time_s': row['start_time_s'],
                    'end_time_s': row['end_time_s'],
                    'point_count': row['point_count'],
                    'analysis_results': analysis_results.get(row['technique_id'], {})
                }
                segments.append(segment)
        
        return segments

    def _export_eis_data(self, data_file: DataFile, cell_name: str, file_id: str):
        """Export EIS data for external analysis tools."""
        # Check if data contains EIS measurements
        eis_data = data_file.universal_data.filter(
            (pl.col('frequency_hz').is_not_null()) & 
            (pl.col('frequency_hz') > 0)
        )
        
        if not eis_data.is_empty():
            # Export EIS data for Relaxis
            export_dir = self.cells_dir / cell_name / "exports" / "relaxis"
            export_path = export_dir / f"{file_id}_eis.csv"
            
            # Select relevant columns for EIS analysis
            eis_export = eis_data.select([
                'frequency_hz', 'impedance_real_ohm', 'impedance_imag_ohm',
                'impedance_mag_ohm', 'impedance_phase_deg', 'time_s'
            ])
            
            eis_export.write_csv(export_path)
            logger.info(f"Exported EIS data: {export_path}")

    def _create_cell_directories(self, cell_dir: Path):
        """Create standard cell directory structure."""
        (cell_dir / "raw").mkdir(parents=True, exist_ok=True)
        (cell_dir / "processed").mkdir(parents=True, exist_ok=True)
        (cell_dir / "analysis_results").mkdir(parents=True, exist_ok=True)
        (cell_dir / "exports" / "relaxis").mkdir(parents=True, exist_ok=True)
        (cell_dir / "user_groups").mkdir(parents=True, exist_ok=True)

    # Database query methods
    def get_all_cells(self) -> List[Dict[str, Any]]:
        """Get all cells with file counts."""
        return self.db.get_all_cells()

    def get_cell_by_name(self, cell_name: str) -> Optional[Dict[str, Any]]:
        """Get cell by name."""
        return self.db.get_cell_by_name(cell_name)

    def get_cell_files(self, cell_name: str) -> List[Dict[str, Any]]:
        """Get all files for a cell."""
        cell = self.db.get_cell_by_name(cell_name)
        if not cell:
            return []
        return self.db.get_cell_files(cell['id'])

    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata by file_id."""
        return self.db.get_file_by_id(file_id)

    def load_processed_file(self, file_id: str) -> Optional[pl.DataFrame]:
        """Load processed parquet file."""
        file_info = self.db.get_file_by_id(file_id)
        if not file_info or not file_info.get('processed_path'):
            return None
        
        try:
            return pl.read_parquet(file_info['processed_path'])
        except Exception as e:
            logger.error(f"Failed to load processed file {file_id}: {e}")
            return None

    def load_analysis_results(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Load analysis results JSON."""
        file_info = self.db.get_file_by_id(file_id)
        if not file_info or not file_info.get('analysis_path'):
            return None
        
        try:
            with open(file_info['analysis_path'], 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load analysis results {file_id}: {e}")
            return None

    def move_file_to_cell(self, file_id: str, target_cell_name: str) -> bool:
        """Move file between cells atomically."""
        # Get target cell
        target_cell = self.db.get_cell_by_name(target_cell_name)
        if not target_cell:
            logger.error(f"Target cell not found: {target_cell_name}")
            return False
        
        # Move in database
        success = self.db.move_file_to_cell(file_id, target_cell['id'])
        
        # TODO: Move physical files between cell directories
        # This would require updating file paths in database
        
        return success

    def delete_file(self, file_id: str) -> bool:
        """Delete file and all associated data."""
        file_info = self.db.get_file_by_id(file_id)
        if not file_info:
            return False
        
        try:
            # Delete physical files
            if file_info.get('file_path'):
                Path(file_info['file_path']).unlink(missing_ok=True)
            if file_info.get('processed_path'):
                Path(file_info['processed_path']).unlink(missing_ok=True)
            if file_info.get('analysis_path'):
                Path(file_info['analysis_path']).unlink(missing_ok=True)
            
            # Delete from database
            return self.db.delete_file(file_id)
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.db.get_database_stats()

    def backup_database(self, backup_path: Path):
        """Create database backup."""
        self.db.backup_database(backup_path)

    # Legacy compatibility methods
    def list_cells(self) -> List[str]:
        """List all cell names (legacy compatibility)."""
        cells = self.db.get_all_cells()
        return [cell['cell_name'] for cell in cells]

    def get_cell_summary(self, cell_name: str) -> Optional[Dict[str, Any]]:
        """Get cell summary with computed statistics."""
        cell = self.db.get_cell_by_name(cell_name)
        if not cell:
            return None
        
        files = self.db.get_cell_files(cell['id'])
        
        # Compute summary statistics
        total_points = 0
        total_duration = 0
        techniques = set()
        timestamps = []
        
        for file_info in files:
            # Load processed data for statistics
            try:
                data = self.load_processed_file(file_info['file_id'])
                if data and not data.is_empty():
                    total_points += data.height
                    total_duration += data.get_column('time_s').max() or 0
                    file_techniques = data.get_column('fundamental_technique').unique().to_list()
                    techniques.update(t for t in file_techniques if t is not None)
                    if 'timestamp' in data.columns:
                        timestamps.extend(data.get_column('timestamp').to_list())
            except:
                pass
        
        summary = {
            **cell,
            'files': files,
            'summary': {
                'total_files': len(files),
                'total_points': total_points,
                'total_duration_hours': total_duration / 3600,
                'techniques_used': list(techniques),
                'date_range': {
                    'earliest': min(timestamps) if timestamps else None,
                    'latest': max(timestamps) if timestamps else None
                }
            }
        }
        
        return summary


# Convenience function for backward compatibility
def create_storage_manager(data_dir: Path = None) -> DatabaseStorageManager:
    """Create a new database storage manager."""
    return DatabaseStorageManager(data_dir)