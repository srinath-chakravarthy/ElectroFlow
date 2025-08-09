"""
VersaStudio .par file parser.

This module handles parsing of VersaStudio .par files into standardized
DataFile objects with consistent data schemas.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import polars as pl

from .data_models import (
    DataFile, ActionDefinition, SegmentData,
    create_standardized_dataframe, VERSASTUDIO_COLUMNS
)


class ParserError(Exception):
    """Base exception for all parser errors."""
    pass


class VersaStudioParseError(ParserError):
    """Raised when VersaStudio .par file parsing fails."""
    pass


class BaseParser:
    """
    Abstract base class for all instrument parsers.

    Defines the common interface that all parsers must implement.
    Currently designed around VersaStudio requirements, but provides
    structure for future instrument support.
    """

    def parse(self, file_path: Path) -> DataFile:
        """
        Parse an instrument data file into a DataFile object.

        Args:
            file_path: Path to the instrument data file

        Returns:
            DataFile object with standardized data

        Raises:
            ParserError: If parsing fails
        """
        raise NotImplementedError("Subclasses must implement parse method")

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate that the file can be parsed by this parser.

        Args:
            file_path: Path to the file

        Returns:
            True if file can be parsed, False otherwise
        """
        raise NotImplementedError("Subclasses must implement validate_file method")


class VersaStudioParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.sections = {}
        self.actions = {}
        self.segments = {}

    def validate_file(self, file_path: Path) -> bool:
        """Validate that this is a VersaStudio .par file."""
        if not file_path.exists() or file_path.suffix.lower() != '.par':
            return False

        # Quick check for VersaStudio format markers
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_chunk = f.read(1000)
                return '<Application>' in first_chunk or '<Experiment>' in first_chunk
        except:
            return False

    def parse(self, file_path: Path) -> DataFile:
        """
        Parse a .par file into a DataFile object.

        Args:
            file_path: Path to the .par file

        Returns:
            DataFile object with standardized data

        Raises:
            VersaStudioParseError: If parsing fails
        """
        try:
            # Read file content
            content = self._read_file(file_path)

            # Two-pass parsing
            self._parse_sections(content)
            self._parse_data_segments(content)

            # Create measurement object
            measurement = self._create_measurement(file_path)

            return measurement

        except Exception as e:
            raise VersaStudioParseError(f"Failed to parse {file_path}: {str(e)}") from e

    def _read_file(self, file_path: Path) -> str:
        """Read and validate .par file."""
        if not file_path.exists():
            raise VersaStudioParseError(f"File not found: {file_path}")

        if file_path.suffix.lower() != '.par':
            raise VersaStudioParseError(f"Not a .par file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding as backup
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()

        if not content.strip():
            raise VersaStudioParseError("File is empty")

        return content

    def _parse_sections(self, content: str) -> None:
        """Parse metadata sections (Application, Instrument, Experiment, Actions)."""
        self.sections = {}
        self.actions = {}

        # Find all sections using regex
        section_pattern = r'<(\w+)>(.*?)(?=<\w+>|$)'
        matches = re.findall(section_pattern, content, re.DOTALL)

        for section_name, section_content in matches:
            if section_name.startswith('Action'):
                # Parse action
                action = self._parse_action(section_name, section_content)
                if action:
                    self.actions[action.action_id] = action
            elif section_name.startswith('Segment'):
                # Skip segments here - handled in _parse_data_segments
                continue
            else:
                # Parse regular section
                self.sections[section_name] = self._parse_section_content(section_content)

    def _parse_action(self, section_name: str, content: str) -> Optional[ActionDefinition]:
        """Parse an action section."""
        # Extract action ID
        action_match = re.match(r'Action(\d+)', section_name)
        if not action_match:
            return None

        action_id = int(action_match.group(1))

        # Parse action parameters
        parameters = self._parse_section_content(content)

        # Extract action name
        name = parameters.get('Name', f'Action{action_id}')

        # Extract parent action if specified
        parent_id = None
        if 'ParentNode' in parameters:
            parent_match = re.search(r'Action(\d+)', parameters['ParentNode'])
            if parent_match:
                parent_id = int(parent_match.group(1))

        return ActionDefinition(
            action_id=action_id,
            name=name,
            parameters=parameters,
            parent_action_id=parent_id
        )

    def _parse_section_content(self, content: str) -> Dict[str, str]:
        """Parse key=value pairs from section content."""
        parameters = {}

        for line in content.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                parameters[key.strip()] = value.strip()

        return parameters

    def _parse_data_segments(self, content: str) -> None:
        """Parse data segments."""
        self.segments = {}

        # Find segment sections
        segment_pattern = r'<(Segment\d+)>(.*?)(?=<\w+>|$)'
        matches = re.findall(segment_pattern, content, re.DOTALL)

        for segment_name, segment_content in matches:
            segment = self._parse_segment(segment_name, segment_content)
            if segment:
                self.segments[segment.segment_id] = segment

    def _parse_segment(self, segment_name: str, content: str) -> Optional[SegmentData]:
        """Parse a single data segment."""
        # Extract segment ID
        segment_match = re.match(r'Segment(\d+)', segment_name)
        if not segment_match:
            return None

        segment_id = int(segment_match.group(1))

        lines = content.strip().split('\n')
        if len(lines) < 3:  # Need Type, Version, Definition at minimum
            return None

        # Parse segment metadata
        segment_type = None
        version = None
        definition = None
        data_start_idx = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('Type='):
                segment_type = int(line.split('=')[1])
            elif line.startswith('Version='):
                version = int(line.split('=')[1])
            elif line.startswith('Definition='):
                definition = line.split('=', 1)[1]
                data_start_idx = i + 1
                break

        if segment_type is None or version is None or definition is None:
            raise VersaStudioParseError(f"Invalid segment header in {segment_name}")

        # Parse data rows
        data_rows = []
        for line in lines[data_start_idx:]:
            line = line.strip()
            if line and not line.startswith('#'):
                # Split by comma and convert to appropriate types
                values = [self._convert_value(v.strip()) for v in line.split(',')]
                data_rows.append(values)

        if not data_rows:
            # Empty segment - create empty dataframe with correct schema
            df = create_standardized_dataframe({}, [])
        else:
            # Create dataframe from parsed data
            df = self._create_segment_dataframe(data_rows, definition)

        return SegmentData(
            segment_id=segment_id,
            segment_type=segment_type,
            version=version,
            column_definition=definition,
            data=df
        )

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        if not value or value.lower() in ('', 'nan', 'null'):
            return None

        # Try scientific notation first
        try:
            if 'E' in value.upper() or 'e' in value:
                return float(value)
        except ValueError:
            pass

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def _create_segment_dataframe(self, data_rows: List[List], definition: str) -> pl.DataFrame:
        """Create standardized dataframe from segment data."""
        # Parse column definition
        available_columns = self._parse_column_definition(definition)

        if not available_columns:
            raise VersaStudioParseError("Could not parse column definition")

        # Ensure data consistency
        expected_cols = len(available_columns)
        for i, row in enumerate(data_rows):
            if len(row) != expected_cols:
                raise VersaStudioParseError(
                    f"Row {i} has {len(row)} columns, expected {expected_cols}"
                )

        # Create data dictionary
        data_dict = {}
        for col_idx, col_name in enumerate(available_columns):
            data_dict[col_name] = [row[col_idx] for row in data_rows]

        # Create standardized dataframe
        return create_standardized_dataframe(data_dict, available_columns)

    def _parse_column_definition(self, definition: str) -> List[str]:
        """
        Parse column definition string.

        Example: "Segment #, Point #, E(V), I(A), Elapsed Time(s), ..."
        """
        if not definition:
            return []

        # Split by comma and clean up column names
        columns = []
        for col in definition.split(','):
            col = col.strip()
            if col and col != '0':  # Skip empty and trailing '0'
                columns.append(col)

        return columns

    def _create_measurement(self, file_path: Path) -> DataFile:
        """Create DataFile object from parsed data."""
        # Extract timestamp
        timestamp = self._extract_timestamp()

        # Combine all segment data
        combined_data = self._combine_segments()

        # Add absolute timestamps
        full_data = self._add_absolute_timestamps(combined_data, timestamp)

        # Create pruned version for storage
        from .data_models import prune_empty_columns
        pruned_data = prune_empty_columns(full_data)

        # Extract metadata
        metadata = self._extract_metadata()

        return DataFile(
            file_path=file_path,
            timestamp=timestamp,
            full_data=full_data,
            pruned_data=pruned_data,
            actions=self.actions,
            segments=self.segments,
            metadata=metadata
        )

    def _extract_timestamp(self) -> datetime:
        """Extract experiment timestamp from metadata."""
        if 'Experiment' not in self.sections:
            raise VersaStudioParseError("No Experiment section found")

        exp_section = self.sections['Experiment']

        # Get date and time
        date_str = exp_section.get('DateAcquired', '')
        time_str = exp_section.get('TimeAcquired', '')

        if not date_str or not time_str:
            raise VersaStudioParseError("Missing DateAcquired or TimeAcquired")

        # Parse timestamp
        try:
            # Example: "Thursday, June 12, 2025" + "10:41:31 AM"
            datetime_str = f"{date_str} {time_str}"

            # Try different formats
            formats = [
                "%A, %B %d, %Y %I:%M:%S %p",  # "Thursday, June 12, 2025 10:41:31 AM"
                "%A, %B %d, %Y %H:%M:%S",  # "Thursday, June 12, 2025 10:41:31"
                "%m/%d/%Y %I:%M:%S %p",  # "6/12/2025 10:41:31 AM"
                "%m/%d/%Y %H:%M:%S",  # "6/12/2025 10:41:31"
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue

            raise ValueError(f"Could not parse timestamp: {datetime_str}")

        except Exception as e:
            raise VersaStudioParseError(f"Invalid timestamp format: {e}")

    def _combine_segments(self) -> pl.DataFrame:
        """Combine all segments into single dataframe."""
        if not self.segments:
            return create_standardized_dataframe({}, [])

        # Collect all segment dataframes
        segment_dfs = []
        for segment in self.segments.values():
            if not segment.data.is_empty():
                segment_dfs.append(segment.data)

        if not segment_dfs:
            return create_standardized_dataframe({}, [])

        # Combine segments
        combined = pl.concat(segment_dfs, how="vertical_relaxed")

        return combined

    def _add_absolute_timestamps(self, df: pl.DataFrame, start_time: datetime) -> pl.DataFrame:
        """Add absolute timestamp column based on elapsed time."""
        if df.is_empty():
            return df

        return df.with_columns([
            (pl.lit(start_time).cast(pl.Datetime) +
             pl.duration(seconds=pl.col('Elapsed Time(s)'))).alias('absolute_timestamp')
        ])

    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract relevant metadata from all sections."""
        metadata = {}

        # Copy all sections
        for section_name, section_data in self.sections.items():
            metadata[section_name] = section_data.copy()

        # Add action summary
        metadata['actions_summary'] = {
            'total_actions': len(self.actions),
            'action_names': [action.name for action in self.actions.values()],
            'techniques': list(set(action.technique.value for action in self.actions.values()))
        }

        # Add segment summary
        metadata['segments_summary'] = {
            'total_segments': len(self.segments),
            'total_points': sum(segment.row_count for segment in self.segments.values())
        }

        return metadata


# Convenience function for easy importing
def parse_par_file(file_path: Path) -> DataFile:
    """
    Parse a VersaStudio .par file.

    Args:
        file_path: Path to the .par file

    Returns:
        DataFile object

    Raises:
        VersaStudioParseError: If parsing fails
    """
    parser = VersaStudioParser()
    return parser.parse(file_path)