"""
Basic tests for VersaStudio parser.

Run with: pytest tests/test_basic_parser.py
"""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import os

from src.core import (
    parse_file, parse_versastudio_file, ParserError, VersaStudioParseError,
    DataFile, TechniqueType, SignalType, VersaStudioParser
)


class TestVersaStudioParser:
    """Test the VersaStudio parser with synthetic data."""

    def create_test_par_file(self, content: str) -> Path:
        """Create a temporary .par file with given content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.par', delete=False) as f:
            f.write(content)
            return Path(f.name)

    def test_basic_dc_measurement(self):
        """Test parsing a simple DC measurement."""
        par_content = """
<Application>
Version=2.66.2.0
LoggedIn=Security Disabled
</Application>

<Instrument>
Model=PMC-1000
Type=PMC-1000
</Instrument>

<Experiment>
TimeAcquired=10:41:31 AM
DateAcquired=Thursday, June 12, 2025
DataFormat=Binary
</Experiment>

<Action0>
Limits1,Value=4.3
Limits1,Direction=>
Limits1,Limits=Potential(V)
Measured Open Circuit=3.331 V
Name=Common
</Action0>

<Action1>
Duration (s)=10
Current (mA)=-6
Name=Constant Current
</Action1>

<Segment1>
Type=11
Version=3
Definition=Segment #, Point #, E(V), I(A), Elapsed Time(s), ADC Sync Input(V), Current Range, Status, E Applied(V), Frequency(Hz), ActionId
0,0,3.331,-0.006,1,0.0,5,131077,0,0,1
0,1,3.330,-0.006,2,0.0,5,131077,0,0,1
0,2,3.329,-0.006,3,0.0,5,131077,0,0,1
"""

        # Create test file
        test_file = self.create_test_par_file(par_content)

        try:
            # Parse file using automatic detection
            measurement = parse_file(test_file)

            # Verify basic properties
            assert isinstance(measurement, DataFile)
            assert measurement.file_path == test_file
            assert measurement.timestamp == datetime(2025, 6, 12, 10, 41, 31)
            assert measurement.primary_technique == TechniqueType.CC
            assert measurement.signal_type == SignalType.DC
            assert measurement.point_count == 3
            assert measurement.duration_seconds == 3.0

            # Verify data structure
            assert not measurement.full_data.is_empty()
            assert 'E(V)' in measurement.full_data.columns
            assert 'I(A)' in measurement.full_data.columns
            assert 'Elapsed Time(s)' in measurement.full_data.columns

            # Verify actions
            assert len(measurement.actions) == 2
            assert 0 in measurement.actions
            assert 1 in measurement.actions
            assert measurement.actions[1].name == "Constant Current"

            # Verify segments
            assert len(measurement.segments) == 1
            assert 1 in measurement.segments

        finally:
            # Clean up
            os.unlink(test_file)

    def test_eis_measurement(self):
        """Test parsing EIS measurement with AC data."""
        par_content = """
<Application>
Version=2.66.2.0
</Application>

<Instrument>
Model=PMC-1000
</Instrument>

<Experiment>
TimeAcquired=2:30:00 PM
DateAcquired=Friday, June 13, 2025
</Experiment>

<Action0>
Name=Common
</Action0>

<Action1>
Amplitude (uA RMS)=500
Start Frequency (Hz)=100000
End Frequency (Hz)=0.01
Name=Galvanostatic EIS
</Action1>

<Segment1>
Type=11
Version=3
Definition=Segment #, Point #, E(V), I(A), Elapsed Time(s), Frequency(Hz), Z Real, Z Imag, ActionId
0,0,3.3,0.0005,1,100000,50.2,-10.1,1
0,1,3.3,0.0005,2,10000,52.1,-15.3,1
0,2,3.3,0.0005,3,1000,58.4,-25.6,1
"""

        test_file = self.create_test_par_file(par_content)

        try:
            measurement = parse_file(test_file)

            # Verify EIS-specific properties
            assert measurement.primary_technique == TechniqueType.EIS
            assert measurement.signal_type == SignalType.AC

            # Verify AC data extraction
            ac_data = measurement.get_ac_data()
            assert not ac_data.is_empty()
            assert ac_data.height == 3

            # Verify impedance data
            assert 'Z Real' in measurement.full_data.columns
            assert 'Z Imag' in measurement.full_data.columns
            assert 'Frequency(Hz)' in measurement.full_data.columns

        finally:
            os.unlink(test_file)

    def test_empty_file(self):
        """Test error handling for empty file."""
        test_file = self.create_test_par_file("")

        try:
            with pytest.raises(ParserError, match="File is empty"):
                parse_file(test_file)
        finally:
            os.unlink(test_file)

    def test_invalid_file_extension(self):
        """Test error handling for non-.par files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some content")
            test_file = Path(f.name)

        try:
            with pytest.raises(ParserError, match="No parser available"):
                parse_file(test_file)
        finally:
            os.unlink(test_file)

    def test_missing_timestamp(self):
        """Test error handling for missing timestamp."""
        par_content = """
<Application>
Version=2.66.2.0
</Application>

<Experiment>
DataFormat=Binary
</Experiment>
"""

        test_file = self.create_test_par_file(par_content)

        try:
            with pytest.raises(VersaStudioParseError, match="Missing DateAcquired or TimeAcquired"):
                parse_versastudio_file(test_file)  # Use specific parser for this test
        finally:
            os.unlink(test_file)

    def test_column_standardization(self):
        """Test that all measurements have standardized columns."""
        par_content = """
<Application>
Version=2.66.2.0
</Application>

<Instrument>
Model=PMC-1000
</Instrument>

<Experiment>
TimeAcquired=10:00:00 AM
DateAcquired=Monday, June 10, 2025
</Experiment>

<Action0>
Name=Common
</Action0>

<Action1>
Name=Simple Test
</Action1>

<Segment1>
Type=11
Version=3
Definition=Segment #, Point #, E(V), I(A), Elapsed Time(s)
0,0,3.3,-0.001,1
0,1,3.2,-0.001,2
"""

        test_file = self.create_test_par_file(par_content)

        try:
            measurement = parse_file(test_file)

            # Verify all standard columns are present in full_data
            from src.core.data_models import VERSASTUDIO_COLUMNS
            for col in VERSASTUDIO_COLUMNS:
                assert col in measurement.full_data.columns

            # Verify pruned_data only has non-null columns
            assert len(measurement.pruned_data.columns) < len(VERSASTUDIO_COLUMNS)
            assert 'E(V)' in measurement.pruned_data.columns
            assert 'I(A)' in measurement.pruned_data.columns

        finally:
            os.unlink(test_file)


if __name__ == "__main__":
    # Run tests directly
    test_instance = TestVersaStudioParser()

    print("Running basic parser tests...")

    try:
        test_instance.test_basic_dc_measurement()
        print("✓ Basic DC measurement test passed")
    except Exception as e:
        print(f"✗ Basic DC measurement test failed: {e}")

    try:
        test_instance.test_eis_measurement()
        print("✓ EIS measurement test passed")
    except Exception as e:
        print(f"✗ EIS measurement test failed: {e}")

    try:
        test_instance.test_empty_file()
        print("✓ Empty file error handling test passed")
    except Exception as e:
        print(f"✗ Empty file error handling test failed: {e}")

    try:
        test_instance.test_invalid_file_extension()
        print("✓ Invalid file extension test passed")
    except Exception as e:
        print(f"✗ Invalid file extension test failed: {e}")

    try:
        test_instance.test_missing_timestamp()
        print("✓ Missing timestamp test passed")
    except Exception as e:
        print(f"✗ Missing timestamp test failed: {e}")

    try:
        test_instance.test_column_standardization()
        print("✓ Column standardization test passed")
    except Exception as e:
        print(f"✗ Column standardization test failed: {e}")

    print("\nAll tests completed!")