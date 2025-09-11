"""
Data Migration Utility - Standardize Directory Structure

Migrates existing raw files to the standardized cell-based directory structure.
Creates proper cell directories and copies raw files to correct locations.
"""

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from src_clean.core.config import get_config
from src_clean.core.database import DatabaseManager

logger = logging.getLogger(__name__)

class DataMigrationManager:
    """
    Manages migration of raw data files to standardized directory structure.
    
    Ensures all raw files are properly stored in:
    data_clean/cells/{cell_name}/raw/
    """
    
    def __init__(self):
        self.config = get_config()
        self.db = DatabaseManager(self.config.db_path)
    
    def migrate_raw_files(self, dry_run: bool = True) -> Dict[str, any]:
        """
        Migrate all raw files to standardized cell directory structure.
        
        Args:
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            Dictionary with migration summary
        """
        logger.info(f"Starting data migration {'(DRY RUN)' if dry_run else ''}")
        
        # Get all files from database
        all_files = self._get_all_database_files()
        
        migration_plan = []
        errors = []
        
        for file_info in all_files:
            try:
                plan_item = self._plan_file_migration(file_info)
                if plan_item:
                    migration_plan.append(plan_item)
            except Exception as e:
                errors.append(f"Error planning migration for {file_info.get('file_id', 'unknown')}: {e}")
                logger.error(f"Migration planning error: {e}")
        
        # Execute migration if not dry run
        executed_count = 0
        if not dry_run:
            for plan_item in migration_plan:
                try:
                    self._execute_migration_item(plan_item)
                    executed_count += 1
                    logger.info(f"Migrated: {plan_item['description']}")
                except Exception as e:
                    errors.append(f"Migration execution error: {e}")
                    logger.error(f"Failed to execute migration: {e}")
        
        # Generate summary
        summary = {
            'total_files_checked': len(all_files),
            'migration_items_planned': len(migration_plan),
            'migration_items_executed': executed_count if not dry_run else 0,
            'errors': errors,
            'dry_run': dry_run,
            'migration_plan': migration_plan if dry_run else [],
        }
        
        logger.info(f"Migration complete: {executed_count}/{len(migration_plan)} items processed")
        return summary
    
    def _get_all_database_files(self) -> List[Dict[str, any]]:
        """Get all files from database with cell information."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT f.*, c.name as cell_name
                FROM files f
                JOIN cells c ON f.cell_id = c.id
                ORDER BY c.name, f.file_id
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def _plan_file_migration(self, file_info: Dict[str, any]) -> Optional[Dict[str, any]]:
        """
        Plan migration for a single file.
        
        Args:
            file_info: Database file information
            
        Returns:
            Migration plan item or None if no migration needed
        """
        cell_name = file_info['cell_name']
        original_filename = file_info['original_filename']
        paired_filename = file_info.get('paired_filename')
        
        # Target directories
        target_raw_dir = self.config.get_cell_raw_directory(cell_name)
        
        # Look for source files in known locations
        source_locations = self._find_source_files(original_filename, paired_filename)
        
        if not source_locations:
            logger.warning(f"No source files found for {original_filename}")
            return None
        
        # Check if files already in correct location
        target_metadata_path = target_raw_dir / original_filename
        target_data_path = target_raw_dir / paired_filename if paired_filename else None
        
        migration_needed = False
        copy_operations = []
        
        # Check metadata file
        if 'metadata' in source_locations:
            if not target_metadata_path.exists() or source_locations['metadata'] != target_metadata_path:
                copy_operations.append({
                    'source': source_locations['metadata'],
                    'target': target_metadata_path,
                    'type': 'metadata'
                })
                migration_needed = True
        
        # Check data file  
        if 'data' in source_locations and target_data_path:
            if not target_data_path.exists() or source_locations['data'] != target_data_path:
                copy_operations.append({
                    'source': source_locations['data'],
                    'target': target_data_path,
                    'type': 'data'
                })
                migration_needed = True
        
        if not migration_needed:
            return None
        
        return {
            'file_id': file_info['file_id'],
            'cell_name': cell_name,
            'target_raw_dir': target_raw_dir,
            'copy_operations': copy_operations,
            'description': f"{cell_name}: {original_filename} + {paired_filename or 'N/A'}"
        }
    
    def _find_source_files(self, metadata_filename: str, data_filename: Optional[str]) -> Dict[str, Path]:
        """
        Find source files in various possible locations.
        
        Args:
            metadata_filename: .par filename
            data_filename: .par.csv filename (optional)
            
        Returns:
            Dictionary with 'metadata' and optionally 'data' paths
        """
        found_files = {}
        
        # Search locations
        search_paths = [
            # Legacy data directory
            Path("data"),
            # Current data_clean
            self.config.data_dir,
            # Project root
            self.config.project_root,
        ]
        
        # Search for metadata file (.par)
        for search_root in search_paths:
            if not search_root.exists():
                continue
                
            for metadata_path in search_root.rglob(metadata_filename):
                if metadata_path.is_file():
                    found_files['metadata'] = metadata_path
                    logger.debug(f"Found metadata file: {metadata_path}")
                    break
            
            if 'metadata' in found_files:
                break
        
        # Search for data file (.par.csv) 
        if data_filename:
            for search_root in search_paths:
                if not search_root.exists():
                    continue
                    
                for data_path in search_root.rglob(data_filename):
                    if data_path.is_file():
                        found_files['data'] = data_path
                        logger.debug(f"Found data file: {data_path}")
                        break
                
                if 'data' in found_files:
                    break
        
        return found_files
    
    def _execute_migration_item(self, plan_item: Dict[str, any]):
        """
        Execute a single migration item.
        
        Args:
            plan_item: Migration plan item to execute
        """
        # Ensure target directory exists
        target_raw_dir = plan_item['target_raw_dir']
        target_raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Execute copy operations
        for operation in plan_item['copy_operations']:
            source = operation['source']
            target = operation['target']
            op_type = operation['type']
            
            if source.exists():
                # Copy file with verification
                shutil.copy2(source, target)
                logger.debug(f"Copied {op_type} file: {source} -> {target}")
                
                # Verify copy
                if not target.exists():
                    raise RuntimeError(f"Failed to copy {op_type} file to {target}")
                    
                if target.stat().st_size != source.stat().st_size:
                    raise RuntimeError(f"Size mismatch after copying {op_type} file")
            else:
                raise FileNotFoundError(f"Source {op_type} file not found: {source}")
    
    def ensure_cell_directory_structure(self, cell_name: str):
        """
        Ensure complete directory structure exists for a cell.
        
        Args:
            cell_name: Name of the cell
        """
        directories = [
            self.config.get_cell_raw_directory(cell_name),
            self.config.get_cell_processed_directory(cell_name),
            self.config.get_cell_analytics_directory(cell_name),
            self.config.get_cell_groups_directory(cell_name),
            self.config.get_cell_images_directory(cell_name),
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def copy_raw_files_to_cell(self, cell_name: str, metadata_path: Path, 
                              data_path: Path) -> Tuple[Path, Path]:
        """
        Copy raw files to the correct cell directory structure.
        
        Args:
            cell_name: Target cell name
            metadata_path: Source .par file path
            data_path: Source .par.csv file path
            
        Returns:
            Tuple of (target_metadata_path, target_data_path)
        """
        # Ensure cell directory structure exists
        self.ensure_cell_directory_structure(cell_name)
        
        raw_dir = self.config.get_cell_raw_directory(cell_name)
        
        # Target paths
        target_metadata_path = raw_dir / metadata_path.name
        target_data_path = raw_dir / data_path.name
        
        # Copy files if they don't already exist
        if not target_metadata_path.exists():
            shutil.copy2(metadata_path, target_metadata_path)
            logger.info(f"Copied metadata file: {metadata_path.name} -> {target_metadata_path}")
        
        if not target_data_path.exists():
            shutil.copy2(data_path, target_data_path)
            logger.info(f"Copied data file: {data_path.name} -> {target_data_path}")
        
        return target_metadata_path, target_data_path

    def copy_single_file_to_cell(self, cell_name: str, file_path: Path) -> Path:
        """
        Copy single file to the correct cell directory structure.
        
        Args:
            cell_name: Target cell name
            file_path: Source file path (e.g., .mpr)
            
        Returns:
            Path to target file location
        """
        # Ensure cell directory structure exists
        self.ensure_cell_directory_structure(cell_name)
        
        raw_dir = self.config.get_cell_raw_directory(cell_name)
        
        # Target path
        target_file_path = raw_dir / file_path.name
        
        # Copy file if it doesn't already exist
        if not target_file_path.exists():
            shutil.copy2(file_path, target_file_path)
            logger.info(f"Copied single file: {file_path.name} -> {target_file_path}")
        
        return target_file_path