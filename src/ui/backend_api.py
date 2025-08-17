"""
Backend API layer for Panel UI.

Provides clean interface between Panel UI components and backend systems
(database, storage, parsing, analytics). Ensures proper error handling
and status reporting for UI consumption.
"""

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

from core.database import DatabaseManager
from io_utils.storage_v2 import DatabaseStorageManager
from core.parsers import VersaStudioParser

logger = logging.getLogger(__name__)


class BackendAPI:
    """
    Clean interface between Panel UI and backend systems.
    
    Provides standardized methods for UI operations with consistent
    error handling and status reporting. All methods return dictionaries
    with 'success' status and appropriate data or error messages.
    """

    def __init__(self, data_dir: Path = None, db_path: Path = None):
        """
        Initialize backend API.
        
        Args:
            data_dir: Base directory for data storage
            db_path: Path to SQLite database
        """
        self.data_dir = data_dir or Path("data")
        self.db_path = db_path or (self.data_dir / "battery_analyzer.db")
        
        # Initialize backend components
        self.db = DatabaseManager(self.db_path)
        self.storage = DatabaseStorageManager(self.data_dir, self.db_path)
        self.parser = VersaStudioParser()
        
        logger.info(f"BackendAPI initialized with data_dir: {self.data_dir}")

    # Cell management operations
    def get_all_cells(self) -> Dict[str, Any]:
        """
        Get all cells with metadata and file counts.
        
        Returns:
            Dict with success status and cells data
        """
        try:
            cells = self.storage.get_all_cells()
            return {
                'success': True,
                'cells': cells,
                'total_cells': len(cells)
            }
        except Exception as e:
            logger.error(f"Failed to get all cells: {e}")
            return {
                'success': False,
                'error': str(e),
                'cells': []
            }

    def create_cell(self, cell_name: str, description: str = "", chemistry: str = "",
                   capacity_ah: Optional[float] = None, notes: str = "") -> Dict[str, Any]:
        """
        Create new cell with validation.
        
        Args:
            cell_name: Unique cell identifier
            description: Cell description
            chemistry: Battery chemistry
            capacity_ah: Nominal capacity
            notes: Additional notes
            
        Returns:
            Dict with success status and cell_id or error message
        """
        try:
            # Validate cell name
            if not cell_name or not cell_name.strip():
                return {
                    'success': False,
                    'error': "Cell name cannot be empty"
                }
            
            cell_name = cell_name.strip()
            
            # Check if cell already exists
            existing_cell = self.storage.get_cell_by_name(cell_name)
            if existing_cell:
                return {
                    'success': False,
                    'error': f"Cell '{cell_name}' already exists"
                }
            
            # Create cell
            cell_id = self.storage.create_cell(
                cell_name, description, chemistry, capacity_ah, notes
            )
            
            return {
                'success': True,
                'cell_id': cell_id,
                'cell_name': cell_name,
                'message': f"Cell '{cell_name}' created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create cell {cell_name}: {e}")
            return {
                'success': False,
                'error': f"Failed to create cell: {str(e)}"
            }

    def get_cell_details(self, cell_name: str) -> Dict[str, Any]:
        """
        Get detailed cell information including files and summary.
        
        Args:
            cell_name: Cell name
            
        Returns:
            Dict with success status and cell details
        """
        try:
            cell_summary = self.storage.get_cell_summary(cell_name)
            if not cell_summary:
                return {
                    'success': False,
                    'error': f"Cell '{cell_name}' not found"
                }
            
            return {
                'success': True,
                'cell': cell_summary
            }
            
        except Exception as e:
            logger.error(f"Failed to get cell details {cell_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def update_cell_metadata(self, cell_name: str, **updates) -> Dict[str, Any]:
        """
        Update cell metadata.
        
        Args:
            cell_name: Cell name
            **updates: Fields to update
            
        Returns:
            Dict with success status
        """
        try:
            cell = self.storage.get_cell_by_name(cell_name)
            if not cell:
                return {
                    'success': False,
                    'error': f"Cell '{cell_name}' not found"
                }
            
            success = self.db.update_cell(cell['id'], **updates)
            
            if success:
                return {
                    'success': True,
                    'message': f"Cell '{cell_name}' updated successfully"
                }
            else:
                return {
                    'success': False,
                    'error': "Failed to update cell"
                }
                
        except Exception as e:
            logger.error(f"Failed to update cell {cell_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # File management operations
    def add_files_to_cell(self, cell_name: str, file_paths: List[Path],
                         upload_options: Union[str, Dict[str, Any]] = "ask") -> Dict[str, Any]:
        """
        Add multiple files to cell with processing.
        
        Args:
            cell_name: Target cell name
            file_paths: List of file paths to upload
            upload_options: Duplicate handling strategy (str) or full options dict
                           with keys: duplicate_handling, temperature_c, applied_potential_interpretation
            
        Returns:
            Dict with success status and processing results
        """
        # Handle backward compatibility - if string passed, convert to dict
        if isinstance(upload_options, str):
            upload_options = {'duplicate_handling': upload_options}
        
        user_choice = upload_options.get('duplicate_handling', 'ask')
        temperature_c = upload_options.get('temperature_c')
        applied_potential_config = upload_options.get('applied_potential_interpretation', '2-electrode WE-CE voltage')
        try:
            results = []
            successful_uploads = 0
            failed_uploads = 0
            
            for file_path in file_paths:
                try:
                    if not file_path.exists():
                        results.append({
                            'file': str(file_path),
                            'success': False,
                            'error': f"File not found: {file_path}"
                        })
                        failed_uploads += 1
                        continue
                    
                    # Determine file type
                    if file_path.suffix.lower() == '.par':
                        file_type = "par"
                    elif str(file_path).lower().endswith('.par.csv'):
                        file_type = "par_csv"
                    else:
                        results.append({
                            'file': str(file_path),
                            'success': False,
                            'error': f"Unsupported file type: {file_path.suffix}"
                        })
                        failed_uploads += 1
                        continue
                    
                    # Prepare file metadata
                    file_metadata = {
                        'temperature_c': temperature_c,
                        'applied_potential_interpretation': applied_potential_config
                    }
                    
                    # Upload file with metadata
                    file_id, status = self.storage.upload_file(
                        file_path, cell_name, file_type, user_choice, file_metadata
                    )
                    
                    if status != "skipped":
                        results.append({
                            'file': str(file_path),
                            'success': True,
                            'file_id': file_id,
                            'status': status
                        })
                        successful_uploads += 1
                    else:
                        results.append({
                            'file': str(file_path),
                            'success': False,
                            'status': 'skipped'
                        })
                        
                except Exception as e:
                    results.append({
                        'file': str(file_path),
                        'success': False,
                        'error': str(e)
                    })
                    failed_uploads += 1
            
            return {
                'success': True,
                'results': results,
                'summary': {
                    'total_files': len(file_paths),
                    'successful_uploads': successful_uploads,
                    'failed_uploads': failed_uploads
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to add files to cell {cell_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_dual_files_to_cell(self, cell_name: str, par_path: Path, csv_path: Path,
                              upload_options: Union[str, Dict[str, Any]] = "ask") -> Dict[str, Any]:
        """
        Add dual .par and .par.csv files for calibrated processing.
        
        Args:
            cell_name: Target cell name
            par_path: Path to .par file
            csv_path: Path to .par.csv file
            upload_options: Duplicate handling strategy (str) or full options dict
                           with keys: duplicate_handling, temperature_c, applied_potential_interpretation
            
        Returns:
            Dict with success status and processing results
        """
        # Handle backward compatibility - if string passed, convert to dict
        if isinstance(upload_options, str):
            upload_options = {'duplicate_handling': upload_options}
        
        user_choice = upload_options.get('duplicate_handling', 'ask')
        temperature_c = upload_options.get('temperature_c')
        applied_potential_config = upload_options.get('applied_potential_interpretation', '2-electrode WE-CE voltage')
        
        try:
            # Validate dual files
            if not self.parser.validate_dual_files(par_path, csv_path):
                return {
                    'success': False,
                    'error': f"Invalid dual file pair: {par_path.name} and {csv_path.name}"
                }
            
            # Prepare file metadata
            file_metadata = {
                'temperature_c': temperature_c,
                'applied_potential_interpretation': applied_potential_config
            }
            
            # Upload dual files with metadata
            file_ids, status = self.storage.upload_dual_files(
                par_path, csv_path, cell_name, user_choice, file_metadata
            )
            
            if status == "skipped":
                return {
                    'success': False,
                    'status': 'skipped',
                    'message': "File upload was skipped"
                }
            elif status == "failed":
                return {
                    'success': False,
                    'error': "Dual file processing failed"
                }
            else:
                return {
                    'success': True,
                    'file_ids': file_ids,
                    'status': status,
                    'message': f"Dual files processed successfully: {len(file_ids)} files"
                }
                
        except Exception as e:
            logger.error(f"Failed to add dual files to cell {cell_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_file_data_preview(self, file_id: str, n_rows: int = 1000) -> Dict[str, Any]:
        """
        Get preview of processed file data for UI display.
        
        Args:
            file_id: File identifier
            n_rows: Number of rows to preview
            
        Returns:
            Dict with success status and data preview
        """
        try:
            data = self.storage.load_processed_file(file_id)
            if data is None:
                return {
                    'success': False,
                    'error': f"Processed data not found for file: {file_id}"
                }
            
            # Get preview data
            preview_data = data.head(n_rows) if data.height > n_rows else data
            
            # Convert to pandas for UI consumption
            preview_df = preview_data.to_pandas()
            
            # Get basic statistics
            stats = {
                'total_rows': data.height,
                'total_columns': data.width,
                'preview_rows': preview_df.shape[0],
                'columns': list(data.columns),
                'data_types': {col: str(dtype) for col, dtype in data.schema.items()},
                'time_range': {
                    'min': float(data.get_column('time_s').min()) if 'time_s' in data.columns else None,
                    'max': float(data.get_column('time_s').max()) if 'time_s' in data.columns else None
                },
                'techniques': data.get_column('fundamental_technique').unique().to_list() if 'fundamental_technique' in data.columns else []
            }
            
            return {
                'success': True,
                'preview_data': preview_df,
                'stats': stats,
                'file_id': file_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get file preview {file_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_file_analysis_results(self, file_id: str) -> Dict[str, Any]:
        """
        Get analysis results for a file.
        
        Args:
            file_id: File identifier
            
        Returns:
            Dict with success status and analysis results
        """
        try:
            analysis_results = self.storage.load_analysis_results(file_id)
            if analysis_results is None:
                return {
                    'success': False,
                    'error': f"Analysis results not found for file: {file_id}"
                }
            
            return {
                'success': True,
                'analysis_results': analysis_results,
                'file_id': file_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis results {file_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_processing_status(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        Get processing status for multiple files.
        
        Args:
            file_ids: List of file identifiers
            
        Returns:
            Dict with success status and processing information
        """
        try:
            status_info = []
            
            for file_id in file_ids:
                file_info = self.storage.get_file_by_id(file_id)
                if file_info:
                    status_info.append({
                        'file_id': file_id,
                        'filename': file_info['original_filename'],
                        'status': file_info['processing_status'],
                        'upload_time': file_info['upload_timestamp'],
                        'error_message': file_info.get('error_message')
                    })
                else:
                    status_info.append({
                        'file_id': file_id,
                        'status': 'not_found',
                        'error_message': 'File not found in database'
                    })
            
            return {
                'success': True,
                'status_info': status_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get processing status: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # File browser operations
    def list_directory_contents(self, directory_path: Path) -> Dict[str, Any]:
        """
        List contents of a directory for file browser.
        
        Args:
            directory_path: Directory to list
            
        Returns:
            Dict with success status and directory contents
        """
        try:
            if not directory_path.exists():
                return {
                    'success': False,
                    'error': f"Directory not found: {directory_path}"
                }
            
            if not directory_path.is_dir():
                return {
                    'success': False,
                    'error': f"Path is not a directory: {directory_path}"
                }
            
            contents = []
            
            # Add parent directory link
            if directory_path.parent != directory_path:  # Not root
                contents.append({
                    'name': '..',
                    'path': str(directory_path.parent),
                    'type': 'directory',
                    'size': None,
                    'modified': None
                })
            
            # List directory contents
            for item in sorted(directory_path.iterdir()):
                try:
                    stat = item.stat()
                    contents.append({
                        'name': item.name,
                        'path': str(item),
                        'type': 'directory' if item.is_dir() else 'file',
                        'size': stat.st_size if item.is_file() else None,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'is_par_file': item.suffix.lower() == '.par',
                        'is_par_csv_file': str(item).lower().endswith('.par.csv'),
                        'is_supported': item.suffix.lower() == '.par' or str(item).lower().endswith('.par.csv')
                    })
                except (PermissionError, OSError):
                    # Skip files we can't access
                    continue
            
            return {
                'success': True,
                'path': str(directory_path),
                'contents': contents
            }
            
        except Exception as e:
            logger.error(f"Failed to list directory {directory_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def validate_file_compatibility(self, file_paths: List[Path]) -> Dict[str, Any]:
        """
        Validate file compatibility for processing.
        
        Args:
            file_paths: List of file paths to validate
            
        Returns:
            Dict with validation results
        """
        try:
            validation_results = []
            
            # Check for dual file pairs
            par_files = [f for f in file_paths if f.suffix.lower() == '.par']
            csv_files = [f for f in file_paths if str(f).lower().endswith('.par.csv')]
            
            # Validate individual files
            for file_path in file_paths:
                if file_path.suffix.lower() == '.par':
                    is_valid = self.parser.validate_file(file_path)
                    validation_results.append({
                        'file': str(file_path),
                        'type': 'par',
                        'valid': is_valid,
                        'error': None if is_valid else "Invalid .par file format"
                    })
                elif str(file_path).lower().endswith('.par.csv'):
                    # Basic CSV validation
                    try:
                        import polars as pl
                        test_df = pl.read_csv(file_path, has_header=True, n_rows=5)
                        is_valid = self.parser._validate_versastudio_csv(test_df)
                        validation_results.append({
                            'file': str(file_path),
                            'type': 'par_csv',
                            'valid': is_valid,
                            'error': None if is_valid else "Invalid VersaStudio CSV format"
                        })
                    except Exception as e:
                        validation_results.append({
                            'file': str(file_path),
                            'type': 'par_csv',
                            'valid': False,
                            'error': f"CSV validation failed: {str(e)}"
                        })
                else:
                    validation_results.append({
                        'file': str(file_path),
                        'type': 'unknown',
                        'valid': False,
                        'error': "Unsupported file type"
                    })
            
            # Check for dual file pairs
            dual_pairs = []
            for par_file in par_files:
                # Look for matching CSV file
                csv_name = par_file.name + '.csv'
                matching_csv = None
                for csv_file in csv_files:
                    if csv_file.name == csv_name:
                        matching_csv = csv_file
                        break
                
                if matching_csv:
                    pair_valid = self.parser.validate_dual_files(par_file, matching_csv)
                    dual_pairs.append({
                        'par_file': str(par_file),
                        'csv_file': str(matching_csv),
                        'valid': pair_valid,
                        'recommended': True  # Dual processing recommended for calibrated data
                    })
            
            return {
                'success': True,
                'individual_files': validation_results,
                'dual_pairs': dual_pairs,
                'has_valid_files': any(r['valid'] for r in validation_results),
                'has_dual_pairs': len(dual_pairs) > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to validate file compatibility: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # Database operations
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = self.storage.get_database_stats()
            return {
                'success': True,
                'stats': stats
            }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def backup_database(self, backup_path: Path) -> Dict[str, Any]:
        """Create database backup."""
        try:
            self.storage.backup_database(backup_path)
            return {
                'success': True,
                'backup_path': str(backup_path),
                'message': f"Database backed up to {backup_path}"
            }
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance for global access
_backend_api_instance = None

def get_backend_api(data_dir: Path = None, db_path: Path = None) -> BackendAPI:
    """Get singleton backend API instance."""
    global _backend_api_instance
    if _backend_api_instance is None:
        _backend_api_instance = BackendAPI(data_dir, db_path)
    return _backend_api_instance