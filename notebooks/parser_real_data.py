from pathlib import Path
from src.core.parser_factory import parse_file

file_path = Path("../data/measurement_groups/GITT_EIS_Charge_cycle1_Channel 2.par")
print(f"Current working directory: {Path.cwd()}")
data_file = parse_file(file_path)

# Check the results
print(f"✓ Parsed: {data_file.file_path.name}")
print(f"Technique: {data_file.primary_technique.value}")
print(f"Signal type: {data_file.signal_type.value}")
print(f"Duration: {data_file.duration_seconds:.1f} seconds")
print(f"Data points: {data_file.point_count:,}")