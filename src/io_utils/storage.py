"""
Cell-based storage system for battery data files.
Handles file upload, duplicate management, and individual file processing.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import polars as pl
import sys

# Add src directory to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from core.data_models import DataFile, calculate_file_hash
from core.parsers import VersaStudioParser
from analysis.analytics import FundamentalAnalytics


class StorageManager:
    """
    Manages cell-based storage structure and file operations.
    
    Storage structure:
    data/cells/CELL_ID/
    ├── raw/                    # Original uploaded files
    ├── processed/              # Universal schema parquet files
    ├── analysis_results/       # Analysis JSON files
    ├── exports/relaxis/        # EIS CSV exports
    └── metadata.json          # Cell-level metadata
    """

    def __init__(self, base_data_dir: Path = None):
        self.base_data_dir = base_data_dir or Path("data")
        self.cells_dir = self.base_data_dir / "cells"
        self.cells_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize analytics engine
        self.analytics = FundamentalAnalytics()
        
        # Initialize parsers
        self.versastudio_parser = VersaStudioParser()

    def create_cell(self, cell_id: str, metadata: Dict[str, Any] = None) -> Path:
        """
        Create a new cell directory structure.
        
        Args:
            cell_id: Unique cell identifier
            metadata: Optional cell metadata
            
        Returns:
            Path to created cell directory
        """
        cell_dir = self.cells_dir / cell_id
        
        # Create directory structure
        (cell_dir / "raw").mkdir(parents=True, exist_ok=True)
        (cell_dir / "processed").mkdir(parents=True, exist_ok=True)
        (cell_dir / "analysis_results").mkdir(parents=True, exist_ok=True)
        (cell_dir / "exports" / "relaxis").mkdir(parents=True, exist_ok=True)
        (cell_dir / "user_groups").mkdir(parents=True, exist_ok=True)
        
        # Create cell metadata
        cell_metadata = {
            "cell_id": cell_id,
            "created_timestamp": datetime.now().isoformat(),
            "files": [],
            "total_experiments": 0,
            "user_metadata": metadata or {}
        }
        
        metadata_path = cell_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(cell_metadata, f, indent=2)
        
        return cell_dir

    def upload_file(self, source_file_path: Path, cell_id: str, 
                   user_choice: str = "ask") -> Tuple[str, str]:
        """
        Upload a file to cell's raw directory with duplicate handling.
        
        Args:
            source_file_path: Path to source file
            cell_id: Target cell ID
            user_choice: Duplicate handling ("replace", "keep_both", "skip", "ask")
            
        Returns:
            Tuple of (file_id, status) where status is "uploaded", "replaced", "skipped"
        """
        if not source_file_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file_path}")
        
        # Ensure cell exists
        cell_dir = self.cells_dir / cell_id
        if not cell_dir.exists():
            self.create_cell(cell_id)
        
        # Target paths
        raw_dir = cell_dir / "raw"
        target_filename = source_file_path.name
        target_path = raw_dir / target_filename
        
        # Handle duplicates
        if target_path.exists():
            if user_choice == "ask":
                print(f"File '{target_filename}' already exists. Choose action:")
                print("1. Replace existing file (overwrites analysis)")
                print("2. Keep both (timestamp added to new file)")
                print("3. Skip this upload")
                choice = input("Enter choice (1/2/3): ").strip()
                user_choice = {"1": "replace", "2": "keep_both", "3": "skip"}.get(choice, "skip")
            
            if user_choice == "replace":
                shutil.copy2(source_file_path, target_path)
                file_id = self._process_file(target_path, cell_id, replace_existing=True)
                return file_id, "replaced"
            elif user_choice == "keep_both":
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"{target_path.stem}_{timestamp}{target_path.suffix}"
                new_path = raw_dir / new_filename
                shutil.copy2(source_file_path, new_path)
                file_id = self._process_file(new_path, cell_id, replace_existing=False)
                return file_id, "uploaded"
            else:  # skip
                return "", "skipped"
        else:
            # New file
            shutil.copy2(source_file_path, target_path)
            file_id = self._process_file(target_path, cell_id, replace_existing=False)
            return file_id, "uploaded"

    def _process_file(self, raw_file_path: Path, cell_id: str, 
                     replace_existing: bool = False) -> str:
        """
        Process uploaded file: parse → analyze → store.
        
        Args:
            raw_file_path: Path to raw file in cell directory
            cell_id: Cell ID
            replace_existing: Whether this replaces an existing file
            
        Returns:
            Generated file_id
        """
        # Generate file_id
        file_id = f"{cell_id}_{raw_file_path.stem}"
        
        try:
            # Parse file based on type
            if raw_file_path.suffix.lower() == '.par':
                if self.versastudio_parser.validate_file(raw_file_path):
                    data_file = self.versastudio_parser.parse(raw_file_path)
                else:
                    raise ValueError("File validation failed")
            else:
                raise ValueError(f"Unsupported file type: {raw_file_path.suffix}")
            
            # Perform analytics
            analysis_results = self.analytics.analyze_datafile(data_file.universal_data)
            data_file.analysis_results = {
                action_id: {
                    'technique': result.technique,
                    'results': result.results,
                    'quality_metrics': result.quality_metrics,
                    'fitted_data': result.fitted_data
                }
                for action_id, result in analysis_results.items()
            }
            
            # Store processed data
            cell_dir = self.cells_dir / cell_id
            processed_path = cell_dir / "processed" / f"{file_id}.parquet"
            analysis_path = cell_dir / "analysis_results" / f"{file_id}.json"
            
            # Save parquet file
            data_file.universal_data.write_parquet(processed_path)
            
            # Save analysis results
            analysis_data = {
                "file_metadata": {
                    "file_id": file_id,
                    "original_file": raw_file_path.name,
                    "cell_id": cell_id,
                    "file_hash": data_file.file_hash,
                    "timestamp": data_file.timestamp.isoformat(),
                    "parser_version": "2.0.0",
                    "processing_timestamp": datetime.now().isoformat()
                },
                "data_summary": {
                    "total_points": data_file.point_count,
                    "duration_seconds": data_file.duration_seconds,
                    "techniques": list(set(data_file.universal_data.get_column('fundamental_technique').to_list())),
                    "action_count": len(data_file.actions)
                },
                "analysis_results": data_file.analysis_results,
                "metadata": data_file.metadata
            }
            
            with open(analysis_path, 'w') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            
            # Export EIS data if present
            self._export_eis_data(data_file, cell_dir, file_id)
            
            # Update cell metadata
            self._update_cell_metadata(cell_id, file_id, data_file, replace_existing)
            
            return file_id
            
        except Exception as e:
            print(f"Error processing file {raw_file_path}: {e}")
            # Create minimal error record
            error_analysis = {
                "file_metadata": {
                    "file_id": file_id,
                    "original_file": raw_file_path.name,
                    "cell_id": cell_id,
                    "processing_timestamp": datetime.now().isoformat(),
                    "error": str(e)
                },
                "analysis_results": {},
                "metadata": {}
            }
            
            error_path = self.cells_dir / cell_id / "analysis_results" / f"{file_id}_error.json"
            with open(error_path, 'w') as f:
                json.dump(error_analysis, f, indent=2)
            
            return file_id

    def _export_eis_data(self, data_file: DataFile, cell_dir: Path, file_id: str):
        """Export EIS segments to Relaxis-compatible CSV files."""
        eis_segments = data_file.get_eis_segments()
        
        if not eis_segments:
            return
        
        relaxis_dir = cell_dir / "exports" / "relaxis"
        
        for i, segment in enumerate(eis_segments):
            # Get action ID for this segment
            action_id = segment.get_column('technique_id')[0] if not segment.is_empty() else i
            
            # Extract EIS data
            frequency = segment.get_column('frequency_hz')
            z_real = segment.get_column('impedance_real_ohm')
            z_imag = segment.get_column('impedance_imag_ohm')
            
            # Create Relaxis-compatible DataFrame
            eis_export = pl.DataFrame({
                'Frequency(Hz)': frequency,
                'Z_Real(Ohm)': z_real,
                'Z_Imag(Ohm)': z_imag
            })
            
            # Remove rows with null impedance values
            eis_export = eis_export.filter(
                pl.col('Z_Real(Ohm)').is_not_null() & 
                pl.col('Z_Imag(Ohm)').is_not_null()
            )
            
            if not eis_export.is_empty():
                export_path = relaxis_dir / f"{file_id}_action{action_id}_eis.csv"
                eis_export.write_csv(export_path)

    def _update_cell_metadata(self, cell_id: str, file_id: str, 
                            data_file: DataFile, replace_existing: bool):
        """Update cell metadata with new file information."""
        metadata_path = self.cells_dir / cell_id / "metadata.json"
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        except FileNotFoundError:
            metadata = {"cell_id": cell_id, "files": [], "total_experiments": 0}
        
        # Update file list
        file_info = {
            "file_id": file_id,
            "original_filename": data_file.file_path.name,
            "timestamp": data_file.timestamp.isoformat(),
            "techniques": list(set(data_file.universal_data.get_column('fundamental_technique').to_list())),
            "duration_seconds": data_file.duration_seconds,
            "point_count": data_file.point_count
        }
        
        if replace_existing:
            # Replace existing file info
            metadata["files"] = [f for f in metadata["files"] if f["file_id"] != file_id]
            metadata["files"].append(file_info)
        else:
            # Add new file info
            metadata["files"].append(file_info)
            metadata["total_experiments"] = len(metadata["files"])
        
        metadata["last_updated"] = datetime.now().isoformat()
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

    def get_cell_files(self, cell_id: str) -> List[Dict[str, Any]]:
        """Get list of all files for a cell."""
        metadata_path = self.cells_dir / cell_id / "metadata.json"
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return metadata.get("files", [])
        except FileNotFoundError:
            return []

    def load_processed_file(self, cell_id: str, file_id: str) -> Optional[pl.DataFrame]:
        """Load processed parquet file."""
        parquet_path = self.cells_dir / cell_id / "processed" / f"{file_id}.parquet"
        
        try:
            return pl.read_parquet(parquet_path)
        except FileNotFoundError:
            return None

    def load_analysis_results(self, cell_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        """Load analysis results JSON."""
        analysis_path = self.cells_dir / cell_id / "analysis_results" / f"{file_id}.json"
        
        try:
            with open(analysis_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def list_cells(self) -> List[str]:
        """List all available cell IDs."""
        if not self.cells_dir.exists():
            return []
        
        return [d.name for d in self.cells_dir.iterdir() if d.is_dir()]

    def get_cell_summary(self, cell_id: str) -> Optional[Dict[str, Any]]:
        """Get summary information for a cell."""
        metadata_path = self.cells_dir / cell_id / "metadata.json"
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Add computed summaries
            files = metadata.get("files", [])
            metadata["summary"] = {
                "total_files": len(files),
                "total_points": sum(f.get("point_count", 0) for f in files),
                "total_duration_hours": sum(f.get("duration_seconds", 0) for f in files) / 3600,
                "techniques_used": list(set(
                    tech for f in files for tech in f.get("techniques", [])
                )),
                "date_range": {
                    "earliest": min((f.get("timestamp") for f in files), default=None),
                    "latest": max((f.get("timestamp") for f in files), default=None)
                } if files else None
            }
            
            return metadata
        except FileNotFoundError:
            return None