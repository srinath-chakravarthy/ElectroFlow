"""
Centralized Configuration Management

Loads configuration from .env file and provides typed access to all settings.
Supports environment variable overrides and development/production modes.
"""

import os
from pathlib import Path
from typing import Optional
import logging

# Try to load python-dotenv if available, but don't require it
try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

class Config:
    """
    Centralized configuration class with environment variable support.
    
    Loads settings from .env file if available, with environment variable overrides.
    Provides typed access and validation for all application settings.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize configuration with optional project root path.
        
        Args:
            project_root: Path to project root directory (defaults to auto-detection)
        """
        # Auto-detect project root if not provided
        if project_root is None:
            # Start from this file's directory and search upward for .env
            current_dir = Path(__file__).resolve().parent
            while current_dir.parent != current_dir:
                if (current_dir / '.env').exists():
                    project_root = current_dir
                    break
                current_dir = current_dir.parent
            else:
                # Fallback to src_clean parent directory
                project_root = Path(__file__).resolve().parent.parent.parent
        
        self.project_root = Path(project_root)
        self.env_file = self.project_root / '.env'
        
        # Load .env file if available
        if _DOTENV_AVAILABLE and self.env_file.exists():
            load_dotenv(self.env_file)
            logging.info(f"Loaded configuration from: {self.env_file}")
        elif self.env_file.exists():
            logging.warning("Found .env file but python-dotenv not installed. Using environment variables only.")
        
        # Initialize all configuration values
        self._init_config()
    
    def _init_config(self):
        """Initialize all configuration values with type checking."""
        
        # Data Storage
        self.data_dir = self._get_path('ELECTROCHEMICAL_DATA_DIR', 'data_clean')
        self.db_name = self._get_str('ELECTROCHEMICAL_DB_NAME', 'electrochemical.db')
        
        # Web Interface
        self.web_port = self._get_int('WEB_PORT', 5007)
        self.web_host = self._get_str('WEB_HOST', 'localhost')
        self.web_debug = self._get_bool('WEB_DEBUG', False)
        
        # Logging
        self.log_level = self._get_str('LOG_LEVEL', 'INFO').upper()
        self.log_file = self._get_str('LOG_FILE', 'electrochemical.log')
        self.log_dir = self._get_path('LOG_DIR', 'logs')
        
        # Processing
        self.default_temperature_c = self._get_float('DEFAULT_TEMPERATURE_C', 25.0)
        self.max_file_size_mb = self._get_int('MAX_FILE_SIZE_MB', 1000)
        self.processing_timeout_seconds = self._get_int('PROCESSING_TIMEOUT_SECONDS', 300)
        
        # Analysis
        self.decimation_threshold = self._get_int('DECIMATION_THRESHOLD', 10000)
        self.default_decimation_samples = self._get_int('DEFAULT_DECIMATION_SAMPLES', 1000)
        
        # Development
        self.dev_mode = self._get_bool('DEV_MODE', False)
        self.auto_reload = self._get_bool('AUTO_RELOAD', False)
        
        # Computed paths
        self.db_path = self.data_dir / self.db_name
        self.full_log_path = self.log_dir / self.log_file
    
    def _get_str(self, key: str, default: str) -> str:
        """Get string environment variable with default."""
        return os.getenv(key, default)
    
    def _get_int(self, key: str, default: int) -> int:
        """Get integer environment variable with default and validation."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            logging.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def _get_float(self, key: str, default: float) -> float:
        """Get float environment variable with default and validation."""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            logging.warning(f"Invalid float value for {key}, using default: {default}")
            return default
    
    def _get_bool(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with default and validation."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_path(self, key: str, default: str) -> Path:
        """Get Path environment variable with default, resolved relative to project root."""
        path_str = os.getenv(key, default)
        path = Path(path_str)
        
        # If relative path, make it relative to project root
        if not path.is_absolute():
            path = self.project_root / path
        
        return path.resolve()
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.data_dir,
            self.data_dir / 'cells',
            self.log_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logging.debug(f"Ensured directory exists: {directory}")
    
    def get_cell_directory(self, cell_name: str) -> Path:
        """Get the directory path for a specific cell."""
        cell_dir = self.data_dir / 'cells' / cell_name
        return cell_dir
    
    def get_cell_raw_directory(self, cell_name: str) -> Path:
        """Get the raw data directory for a specific cell."""
        return self.get_cell_directory(cell_name) / 'raw'
    
    def get_cell_processed_directory(self, cell_name: str) -> Path:
        """Get the processed data directory for a specific cell."""
        return self.get_cell_directory(cell_name) / 'processed'
    
    def get_cell_analytics_directory(self, cell_name: str) -> Path:
        """Get the analytics directory for a specific cell."""
        return self.get_cell_directory(cell_name) / 'analytics'
    
    def get_cell_groups_directory(self, cell_name: str) -> Path:
        """Get the groups directory for a specific cell."""
        return self.get_cell_directory(cell_name) / 'groups'
    
    def get_cell_images_directory(self, cell_name: str) -> Path:
        """Get the images directory for a specific cell."""
        return self.get_cell_directory(cell_name) / 'images'
    
    def __str__(self) -> str:
        """String representation showing key configuration values."""
        return f"""Electrochemical Analysis Configuration:
  Data Directory: {self.data_dir}
  Database: {self.db_path}
  Web Server: {self.web_host}:{self.web_port}
  Log Level: {self.log_level}
  Log File: {self.full_log_path}
  Development Mode: {self.dev_mode}"""


# Global configuration instance
_config_instance: Optional[Config] = None

def get_config(project_root: Optional[Path] = None) -> Config:
    """
    Get the global configuration instance (singleton pattern).
    
    Args:
        project_root: Optional project root path for initial configuration
        
    Returns:
        Config instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config(project_root)
    
    return _config_instance

def reload_config(project_root: Optional[Path] = None) -> Config:
    """
    Force reload of configuration (useful for testing or config changes).
    
    Args:
        project_root: Optional project root path
        
    Returns:
        New Config instance
    """
    global _config_instance
    _config_instance = Config(project_root)
    return _config_instance


# Convenience functions for common configuration access
def get_data_dir() -> Path:
    """Get the data directory path."""
    return get_config().data_dir

def get_db_path() -> Path:
    """Get the database file path."""
    return get_config().db_path

def is_dev_mode() -> bool:
    """Check if development mode is enabled."""
    return get_config().dev_mode

def get_web_config() -> tuple[str, int, bool]:
    """Get web server configuration as (host, port, debug) tuple."""
    config = get_config()
    return config.web_host, config.web_port, config.web_debug