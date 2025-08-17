"""
SQLite database layer for battery data analyzer.

Replaces JSON file storage with centralized database for metadata management,
file tracking, and cell organization. Provides atomic operations for file
movement between cells and maintains referential integrity.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite database manager for battery data analyzer."""
    
    def __init__(self, db_path: Path):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create cells table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cells (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cell_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    chemistry TEXT,
                    capacity_ah REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create files table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cell_id INTEGER NOT NULL,
                    file_id TEXT UNIQUE NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_type TEXT NOT NULL CHECK (file_type IN ('par', 'par_csv')),
                    file_hash TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    processed_path TEXT,
                    analysis_path TEXT,
                    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_status TEXT DEFAULT 'uploaded' 
                        CHECK (processing_status IN ('uploaded', 'processing', 'completed', 'failed')),
                    error_message TEXT,
                    metadata_json TEXT, -- Additional file metadata as JSON
                    FOREIGN KEY (cell_id) REFERENCES cells (id) ON DELETE CASCADE
                )
            """)
            
            # Create technique segments table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS technique_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    segment_number INTEGER NOT NULL,
                    action_id INTEGER,
                    technique_name TEXT,
                    fundamental_technique TEXT,
                    start_time_s REAL,
                    end_time_s REAL,
                    point_count INTEGER,
                    analysis_results_json TEXT, -- Segment-specific analysis results
                    FOREIGN KEY (file_id) REFERENCES files (file_id) ON DELETE CASCADE
                )
            """)
            
            # Create user groups table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cell_id INTEGER NOT NULL,
                    group_name TEXT NOT NULL,
                    description TEXT,
                    file_ids TEXT, -- JSON array of file_ids
                    segments TEXT, -- JSON array of segment specifications
                    group_metadata_json TEXT, -- Group-specific metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cell_id) REFERENCES cells (id) ON DELETE CASCADE,
                    UNIQUE(cell_id, group_name)
                )
            """)
            
            # Create indices for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_cell_id ON files (cell_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_file_id ON files (file_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_file_id ON technique_segments (file_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_cell_id ON user_groups (cell_id)")
            
            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")
    
    def migrate_schema(self, target_version: int = 1):
        """Migrate database schema to target version.
        
        Args:
            target_version: Target schema version
        """
        # Future implementation for schema migrations
        # This allows adding new columns or tables without breaking existing data
        pass
    
    # Cell operations
    def create_cell(self, cell_name: str, description: str = "", chemistry: str = "", 
                   capacity_ah: Optional[float] = None, notes: str = "") -> int:
        """Create new cell and return cell_id.
        
        Args:
            cell_name: Unique cell identifier
            description: Cell description
            chemistry: Battery chemistry (e.g., 'Li-ion', 'LFP')
            capacity_ah: Nominal capacity in Ah
            notes: Additional notes
            
        Returns:
            cell_id: Primary key of created cell
            
        Raises:
            sqlite3.IntegrityError: If cell_name already exists
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO cells (cell_name, description, chemistry, capacity_ah, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (cell_name, description, chemistry, capacity_ah, notes))
            conn.commit()
            cell_id = cursor.lastrowid
            logger.info(f"Created cell: {cell_name} (id={cell_id})")
            return cell_id
    
    def get_all_cells(self) -> List[Dict[str, Any]]:
        """Get all cells with file counts.
        
        Returns:
            List of cell dictionaries with file counts
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT c.*, 
                       COUNT(f.id) as file_count,
                       COUNT(CASE WHEN f.processing_status = 'completed' THEN 1 END) as processed_count
                FROM cells c
                LEFT JOIN files f ON c.id = f.cell_id
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_cell_by_id(self, cell_id: int) -> Optional[Dict[str, Any]]:
        """Get cell by ID.
        
        Args:
            cell_id: Cell primary key
            
        Returns:
            Cell dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cells WHERE id = ?", (cell_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_cell_by_name(self, cell_name: str) -> Optional[Dict[str, Any]]:
        """Get cell by name.
        
        Args:
            cell_name: Cell name
            
        Returns:
            Cell dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cells WHERE cell_name = ?", (cell_name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_cell(self, cell_id: int, **updates) -> bool:
        """Update cell metadata.
        
        Args:
            cell_id: Cell primary key
            **updates: Fields to update
            
        Returns:
            True if cell was updated, False if not found
        """
        if not updates:
            return False
            
        # Add updated_at timestamp
        updates['updated_at'] = datetime.now().isoformat()
        
        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [cell_id]
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                UPDATE cells SET {set_clause} WHERE id = ?
            """, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_cell(self, cell_id: int) -> bool:
        """Delete cell and all associated files.
        
        Args:
            cell_id: Cell primary key
            
        Returns:
            True if cell was deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM cells WHERE id = ?", (cell_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted cell: id={cell_id}")
            return deleted
    
    # File operations
    def add_file_to_cell(self, cell_id: int, file_info: Dict[str, Any]) -> str:
        """Add file to cell and return file_id.
        
        Args:
            cell_id: Cell primary key
            file_info: Dictionary with file metadata
                Required: file_id, original_filename, file_type, file_hash, file_path
                Optional: processed_path, analysis_path, metadata
                
        Returns:
            file_id: Unique file identifier
            
        Raises:
            sqlite3.IntegrityError: If file_id already exists
        """
        required_fields = ['file_id', 'original_filename', 'file_type', 'file_hash', 'file_path']
        for field in required_fields:
            if field not in file_info:
                raise ValueError(f"Required field missing: {field}")
        
        metadata_json = json.dumps(file_info.get('metadata', {}))
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO files (
                    cell_id, file_id, original_filename, file_type, file_hash, file_path,
                    processed_path, analysis_path, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cell_id, file_info['file_id'], file_info['original_filename'],
                file_info['file_type'], file_info['file_hash'], file_info['file_path'],
                file_info.get('processed_path'), file_info.get('analysis_path'),
                metadata_json
            ))
            conn.commit()
            logger.info(f"Added file to cell: {file_info['file_id']} → cell_id={cell_id}")
            return file_info['file_id']
    
    def get_cell_files(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get all files for a cell.
        
        Args:
            cell_id: Cell primary key
            
        Returns:
            List of file dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM files 
                WHERE cell_id = ? 
                ORDER BY upload_timestamp DESC
            """, (cell_id,))
            files = []
            for row in cursor.fetchall():
                file_dict = dict(row)
                # Parse JSON metadata
                if file_dict['metadata_json']:
                    file_dict['metadata'] = json.loads(file_dict['metadata_json'])
                else:
                    file_dict['metadata'] = {}
                del file_dict['metadata_json']
                files.append(file_dict)
            return files
    
    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file by file_id.
        
        Args:
            file_id: Unique file identifier
            
        Returns:
            File dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
            if row:
                file_dict = dict(row)
                if file_dict['metadata_json']:
                    file_dict['metadata'] = json.loads(file_dict['metadata_json'])
                else:
                    file_dict['metadata'] = {}
                del file_dict['metadata_json']
                return file_dict
            return None
    
    def update_processing_status(self, file_id: str, status: str, 
                               error_message: str = None, **updates) -> bool:
        """Update file processing status.
        
        Args:
            file_id: Unique file identifier
            status: New processing status
            error_message: Error message if status is 'failed'
            **updates: Additional fields to update
            
        Returns:
            True if file was updated, False if not found
        """
        updates['processing_status'] = status
        if error_message:
            updates['error_message'] = error_message
            
        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [file_id]
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                UPDATE files SET {set_clause} WHERE file_id = ?
            """, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def move_file_to_cell(self, file_id: str, new_cell_id: int) -> bool:
        """Move file between cells atomically.
        
        Args:
            file_id: Unique file identifier
            new_cell_id: Target cell primary key
            
        Returns:
            True if file was moved, False if not found
        """
        with self.get_connection() as conn:
            # Begin transaction
            conn.execute("BEGIN")
            try:
                # Check if target cell exists
                cursor = conn.execute("SELECT id FROM cells WHERE id = ?", (new_cell_id,))
                if not cursor.fetchone():
                    conn.rollback()
                    return False
                
                # Move file
                cursor = conn.execute("""
                    UPDATE files SET cell_id = ? WHERE file_id = ?
                """, (new_cell_id, file_id))
                
                if cursor.rowcount == 0:
                    conn.rollback()
                    return False
                
                conn.commit()
                logger.info(f"Moved file: {file_id} → cell_id={new_cell_id}")
                return True
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to move file {file_id}: {e}")
                return False
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file and all associated segments.
        
        Args:
            file_id: Unique file identifier
            
        Returns:
            True if file was deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted file: {file_id}")
            return deleted
    
    # Technique segments operations
    def add_technique_segments(self, file_id: str, segments: List[Dict[str, Any]]):
        """Add technique segments for a file.
        
        Args:
            file_id: Unique file identifier
            segments: List of segment dictionaries
        """
        with self.get_connection() as conn:
            for segment in segments:
                analysis_json = json.dumps(segment.get('analysis_results', {}))
                conn.execute("""
                    INSERT INTO technique_segments (
                        file_id, segment_number, action_id, technique_name,
                        fundamental_technique, start_time_s, end_time_s,
                        point_count, analysis_results_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id, segment['segment_number'], segment.get('action_id'),
                    segment.get('technique_name'), segment.get('fundamental_technique'),
                    segment.get('start_time_s'), segment.get('end_time_s'),
                    segment.get('point_count', 0), analysis_json
                ))
            conn.commit()
            logger.info(f"Added {len(segments)} segments for file: {file_id}")
    
    def get_file_segments(self, file_id: str) -> List[Dict[str, Any]]:
        """Get technique segments for a file.
        
        Args:
            file_id: Unique file identifier
            
        Returns:
            List of segment dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM technique_segments 
                WHERE file_id = ? 
                ORDER BY segment_number
            """, (file_id,))
            segments = []
            for row in cursor.fetchall():
                segment_dict = dict(row)
                # Parse JSON analysis results
                if segment_dict['analysis_results_json']:
                    segment_dict['analysis_results'] = json.loads(segment_dict['analysis_results_json'])
                else:
                    segment_dict['analysis_results'] = {}
                del segment_dict['analysis_results_json']
                segments.append(segment_dict)
            return segments
    
    # User groups operations  
    def create_user_group(self, cell_id: int, group_name: str, description: str = "",
                         file_ids: List[str] = None, segments: List[Dict] = None,
                         metadata: Dict[str, Any] = None) -> int:
        """Create user group for a cell.
        
        Args:
            cell_id: Cell primary key
            group_name: Group name (unique within cell)
            description: Group description
            file_ids: List of file_ids in group
            segments: List of segment specifications
            metadata: Additional group metadata
            
        Returns:
            group_id: Primary key of created group
        """
        file_ids_json = json.dumps(file_ids or [])
        segments_json = json.dumps(segments or [])
        metadata_json = json.dumps(metadata or {})
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO user_groups (
                    cell_id, group_name, description, file_ids,
                    segments, group_metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (cell_id, group_name, description, file_ids_json,
                  segments_json, metadata_json))
            conn.commit()
            group_id = cursor.lastrowid
            logger.info(f"Created user group: {group_name} (cell_id={cell_id})")
            return group_id
    
    def get_cell_groups(self, cell_id: int) -> List[Dict[str, Any]]:
        """Get all user groups for a cell.
        
        Args:
            cell_id: Cell primary key
            
        Returns:
            List of group dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM user_groups 
                WHERE cell_id = ? 
                ORDER BY created_at DESC
            """, (cell_id,))
            groups = []
            for row in cursor.fetchall():
                group_dict = dict(row)
                # Parse JSON fields
                group_dict['file_ids'] = json.loads(group_dict['file_ids'])
                group_dict['segments'] = json.loads(group_dict['segments'])
                if group_dict['group_metadata_json']:
                    group_dict['metadata'] = json.loads(group_dict['group_metadata_json'])
                else:
                    group_dict['metadata'] = {}
                del group_dict['group_metadata_json']
                groups.append(group_dict)
            return groups
    
    # Database utilities
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        with self.get_connection() as conn:
            stats = {}
            
            # Count records in each table
            for table in ['cells', 'files', 'technique_segments', 'user_groups']:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            # File processing status breakdown
            cursor = conn.execute("""
                SELECT processing_status, COUNT(*) 
                FROM files 
                GROUP BY processing_status
            """)
            stats['processing_status'] = dict(cursor.fetchall())
            
            # Database file size
            stats['db_size_bytes'] = self.db_path.stat().st_size
            
            return stats
    
    def vacuum_database(self):
        """Vacuum database to reclaim space."""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            logger.info("Database vacuumed")
    
    def backup_database(self, backup_path: Path):
        """Create database backup.
        
        Args:
            backup_path: Path for backup file
        """
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        logger.info(f"Database backed up to: {backup_path}")


# Convenience functions for common operations
def get_or_create_cell(db: DatabaseManager, cell_name: str, **metadata) -> Tuple[int, bool]:
    """Get existing cell or create new one.
    
    Args:
        db: DatabaseManager instance
        cell_name: Cell name
        **metadata: Cell metadata for creation
        
    Returns:
        Tuple of (cell_id, created) where created is True if cell was created
    """
    cell = db.get_cell_by_name(cell_name)
    if cell:
        return cell['id'], False
    else:
        cell_id = db.create_cell(cell_name, **metadata)
        return cell_id, True


def migrate_from_json_storage(db: DatabaseManager, data_dir: Path):
    """Migrate existing JSON-based storage to database.
    
    Args:
        db: DatabaseManager instance
        data_dir: Path to existing data/cells/ directory
    """
    cells_dir = data_dir / "cells"
    if not cells_dir.exists():
        logger.info("No existing cells directory found")
        return
    
    migrated_cells = 0
    migrated_files = 0
    
    for cell_dir in cells_dir.iterdir():
        if not cell_dir.is_dir():
            continue
            
        cell_name = cell_dir.name
        logger.info(f"Migrating cell: {cell_name}")
        
        # Create cell in database
        try:
            cell_id = db.create_cell(cell_name, description=f"Migrated from {cell_dir}")
            migrated_cells += 1
        except sqlite3.IntegrityError:
            logger.warning(f"Cell {cell_name} already exists, skipping")
            continue
        
        # Migrate files from metadata.json if it exists
        metadata_file = cell_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    cell_metadata = json.load(f)
                
                for file_info in cell_metadata.get('files', []):
                    # Convert old format to new database format
                    db_file_info = {
                        'file_id': file_info.get('file_id', f"{cell_name}_{file_info['filename']}"),
                        'original_filename': file_info['filename'],
                        'file_type': 'par',  # Assume .par files for migration
                        'file_hash': file_info.get('file_hash', ''),
                        'file_path': str(cell_dir / 'raw' / file_info['filename']),
                        'processed_path': str(cell_dir / 'processed' / f"{file_info.get('file_id', file_info['filename'])}.parquet"),
                        'metadata': file_info
                    }
                    
                    try:
                        db.add_file_to_cell(cell_id, db_file_info)
                        migrated_files += 1
                    except Exception as e:
                        logger.error(f"Failed to migrate file {file_info['filename']}: {e}")
                        
            except Exception as e:
                logger.error(f"Failed to read metadata for cell {cell_name}: {e}")
    
    logger.info(f"Migration complete: {migrated_cells} cells, {migrated_files} files")