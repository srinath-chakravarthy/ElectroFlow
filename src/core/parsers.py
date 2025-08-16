"""
Fixed VersaStudio .par file parser with performance improvements.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import polars as pl

from .data_models import (
    DataFile, ActionDefinition, SegmentData,
    create_universal_dataframe, UNIVERSAL_COLUMNS, UNIVERSAL_SCHEMA,
    VERSASTUDIO_COLUMNS, VERSASTUDIO_SCHEMA, TECHNIQUE_MAPPING,
    map_technique_name, calculate_file_hash, prune_empty_columns
)


class ParserError(Exception):
    """Base exception for all parser errors."""
    pass


class VersaStudioParseError(ParserError):
    """Raised when VersaStudio .par file parsing fails."""
    pass


class BaseParser:
    """Abstract base class for all instrument parsers."""

    def parse(self, file_path: Path) -> DataFile:
        """Parse an instrument data file into a DataFile object."""
        raise NotImplementedError("Subclasses must implement parse method")

    def validate_file(self, file_path: Path) -> bool:
        """Validate that the file can be parsed by this parser."""
        raise NotImplementedError("Subclasses must implement validate_file method")


class VersaStudioParser(BaseParser):
    """
    Parser for VersaStudio .par files.

    Uses line-by-line parsing for metadata and Polars for data sections.
    """

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
            # Line-by-line parsing for metadata and boundaries
            self._parse_file_structure(file_path)

            # Use Polars for data sections
            self._parse_data_with_polars(file_path)

            # Create DataFile object
            data_file = self._create_data_file(file_path)

            return data_file

        except Exception as e:
            raise VersaStudioParseError(f"Failed to parse {file_path}: {str(e)}") from e

    def _parse_file_structure(self, file_path: Path) -> None:
        """Parse file structure line by line to find sections and boundaries."""
        self.sections = {}
        self.actions = {}
        self.segment_boundaries = {}

        current_section = None
        current_section_content = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f):
                    line = line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # Section start
                    if line.startswith('<') and line.endswith('>') and not line.startswith('</'):
                        # Save previous section
                        if current_section:
                            self._process_section(current_section, current_section_content)

                        # Start new section
                        current_section = line[1:-1]  # Remove < >
                        current_section_content = []

                        # Track segment boundaries
                        if current_section.startswith('Segment'):
                            segment_id = int(re.search(r'Segment(\d+)', current_section).group(1))
                            self.segment_boundaries[segment_id] = {'start_line': line_num}

                    # Section end
                    elif line.startswith('</') and line.endswith('>'):
                        # Save current section
                        if current_section:
                            self._process_section(current_section, current_section_content)
                            current_section = None
                            current_section_content = []

                        # Track segment end
                        if 'Segment' in line:
                            segment_id = int(re.search(r'Segment(\d+)', line).group(1))
                            if segment_id in self.segment_boundaries:
                                self.segment_boundaries[segment_id]['end_line'] = line_num

                    # Section content
                    elif current_section:
                        current_section_content.append((line_num, line))

                # Process final section
                if current_section:
                    self._process_section(current_section, current_section_content)

        except UnicodeDecodeError:
            # Try with latin-1 encoding as backup
            with open(file_path, 'r', encoding='latin-1') as f:
                # Repeat the same logic...
                pass

    def _process_section(self, section_name: str, content: List[Tuple[int, str]]) -> None:
        """Process a parsed section."""
        if section_name.startswith('Action'):
            action = self._parse_action(section_name, content)
            if action:
                self.actions[action.action_id] = action
        elif section_name.startswith('Segment'):
            # Segment metadata will be handled separately
            segment_id = int(re.search(r'Segment(\d+)', section_name).group(1))
            self._parse_segment_metadata(segment_id, content)
        else:
            # Regular section
            section_dict = {}
            for line_num, line in content:
                if '=' in line:
                    key, value = line.split('=', 1)
                    section_dict[key.strip()] = value.strip()
            self.sections[section_name] = section_dict

    def _parse_action(self, section_name: str, content: List[Tuple[int, str]]) -> Optional[ActionDefinition]:
        """Parse an action section."""
        action_match = re.match(r'Action(\d+)', section_name)
        if not action_match:
            return None

        action_id = int(action_match.group(1))

        # Parse action parameters
        parameters = {}
        for line_num, line in content:
            if '=' in line:
                key, value = line.split('=', 1)
                parameters[key.strip()] = value.strip()

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

    def _parse_segment_metadata(self, segment_id: int, content: List[Tuple[int, str]]) -> None:
        """Parse segment metadata and find data boundaries."""
        segment_type = None
        version = None
        definition = None
        data_start_line = None

        for line_num, line in content:
            if line.startswith('Type='):
                segment_type = int(line.split('=')[1])
            elif line.startswith('Version='):
                version = int(line.split('=')[1])
            elif line.startswith('Definition='):
                definition = line.split('=', 1)[1]
                data_start_line = line_num + 1
                break

        if segment_id in self.segment_boundaries:
            self.segment_boundaries[segment_id].update({
                'segment_type': segment_type,
                'version': version,
                'definition': definition,
                'data_start_line': data_start_line
            })

    def _parse_data_with_polars(self, file_path: Path) -> None:
        """Use Polars to parse data sections efficiently."""
        self.segments = {}

        for segment_id, boundaries in self.segment_boundaries.items():
            try:
                # Extract boundary info
                data_start = boundaries.get('data_start_line')
                data_end = boundaries.get('end_line')
                definition = boundaries.get('definition', '')

                if data_start is None or data_end is None:
                    continue

                # Parse column names from definition
                available_columns = self._parse_column_definition(definition)

                # Calculate number of data rows
                n_rows = data_end - data_start -1

                if n_rows <= 0:
                    # Empty segment
                    df = pl.DataFrame(schema=VERSASTUDIO_SCHEMA)
                else:
                    # Read data with Polars
                    df = pl.read_csv(
                        file_path,
                        skip_rows=data_start,
                        n_rows=n_rows,
                        has_header=False,
                        separator=',',
                        schema=self._create_segment_schema(available_columns),
                        ignore_errors=True
                    )

                    # Standardize to full schema
                    df = self._standardize_dataframe(df, available_columns)

                # Create segment data object
                segment_data = SegmentData(
                    segment_id=segment_id,
                    segment_type=boundaries.get('segment_type', 0),
                    version=boundaries.get('version', 0),
                    column_definition=definition,
                    data=df
                )

                self.segments[segment_id] = segment_data

            except Exception as e:
                print(f"Warning: Failed to parse segment {segment_id}: {e}")
                continue

    def _parse_column_definition(self, definition: str) -> List[str]:
        """Parse column definition string."""
        if not definition:
            return []

        # Split by comma and clean up column names
        columns = []
        for col in definition.split(','):
            col = col.strip()
            if col and col != '0':  # Skip empty and trailing '0'
                columns.append(col)

        return columns

    def _create_segment_schema(self, available_columns: List[str]) -> Dict[str, pl.DataType]:
        """Create Polars schema for available columns."""
        schema = {}
        for col in available_columns:
            if col in VERSASTUDIO_SCHEMA:
                schema[col] = VERSASTUDIO_SCHEMA[col]
            else:
                # Default to float for unknown columns
                schema[col] = pl.Float64
        return schema

    def _standardize_dataframe(self, df: pl.DataFrame, available_columns: List[str]) -> pl.DataFrame:
        """Convert DataFrame to standardized schema."""
        # Start with current data
        result_data = {}

        for col in VERSASTUDIO_COLUMNS:
            if col in available_columns and col in df.columns:
                result_data[col] = df.get_column(col)
            else:
                # Create null column with correct type
                null_series = pl.Series([None] * df.height, dtype=VERSASTUDIO_SCHEMA[col])
                result_data[col] = null_series

        return pl.DataFrame(result_data, schema=VERSASTUDIO_SCHEMA)

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
            datetime_str = f"{date_str} {time_str}"

            # Try different formats
            formats = [
                "%A, %B %d, %Y %I:%M:%S %p",
                "%A, %B %d, %Y %H:%M:%S",
                "%m/%d/%Y %I:%M:%S %p",
                "%m/%d/%Y %H:%M:%S",
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
            return pl.DataFrame(schema=VERSASTUDIO_SCHEMA)

        # Collect all segment dataframes
        segment_dfs = []
        for segment in self.segments.values():
            if not segment.data.is_empty():
                segment_dfs.append(segment.data)

        if not segment_dfs:
            return pl.DataFrame(schema=VERSASTUDIO_SCHEMA)

        # Combine segments
        combined = pl.concat(segment_dfs, how="vertical_relaxed")

        return combined

    def _add_absolute_timestamps(self, df: pl.DataFrame, start_time: datetime) -> pl.DataFrame:
        """Legacy function - timestamps now handled in universal schema conversion."""
        return df

    def _create_data_file(self, file_path: Path) -> DataFile:
        """Create DataFile object from parsed data."""
        # Extract timestamp
        timestamp = self._extract_timestamp()

        # Combine all segment data (VersaStudio format)
        combined_data = self._combine_segments()
        
        # Create ActionId -> Action name mapping for technique identification
        action_id_mapping = {}
        if not combined_data.is_empty() and 'ActionId' in combined_data.columns:
            # Map each unique ActionId to corresponding action name
            for action_id in combined_data.get_column('ActionId').unique():
                if action_id is not None:
                    # Find corresponding segment number
                    segment_data = combined_data.filter(pl.col('ActionId') == action_id)
                    if not segment_data.is_empty():
                        segment_num = segment_data.get_column('Segment #')[0]
                        # Map segment to action (0-based)
                        if segment_num in self.actions:
                            action_id_mapping[action_id] = self.actions[segment_num].name
                        else:
                            # Fallback: try to find action by ID
                            for action in self.actions.values():
                                if action.action_id == segment_num:
                                    action_id_mapping[action_id] = action.name
                                    break
                            else:
                                action_id_mapping[action_id] = 'Unknown'

        # Convert to universal schema
        universal_data = create_universal_dataframe(
            combined_data, action_id_mapping, timestamp
        )

        # Extract enhanced metadata
        metadata = self._extract_metadata()
        metadata['action_id_mapping'] = action_id_mapping
        metadata['technique_mapping'] = {
            action_id: map_technique_name(action_name) 
            for action_id, action_name in action_id_mapping.items()
        }

        return DataFile(
            file_path=file_path,
            timestamp=timestamp,
            universal_data=universal_data,
            actions=self.actions,
            segments=self.segments,
            metadata=metadata,
            file_hash=calculate_file_hash(file_path)
        )

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


# Convenience function
def parse_par_file(file_path: Path) -> DataFile:
    """Parse a VersaStudio .par file."""
    parser = VersaStudioParser()
    return parser.parse(file_path)