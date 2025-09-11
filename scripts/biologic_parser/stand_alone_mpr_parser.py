#!/usr/bin/env python3
"""
Final MPR Parser using YADG's proven logic with Polars output
Clean implementation with complete YADG column mappings
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import struct

try:
    import polars as pl
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install polars")
    sys.exit(1)

logger = logging.getLogger(__name__)

# ===== COMPLETE YADG Column Definitions =====
# Module header formats to try
module_header_dtypes = [
    np.dtype([
        ("short_name", "|S10"),
        ("long_name", "|S25"),
        ("max_length", "<u4"),
        ("length", "<u4"),
        ("oldver", "<u4"),
        ("newver", "<u4"),
        ("date", "|S8"),
    ]),
    np.dtype([
        ("short_name", "|S10"),
        ("long_name", "|S25"),
        ("length", "<u4"),
        ("oldver", "<u4"),
        ("date", "|S8"),
    ]),
]

# Flag columns with bitmasks
flag_columns = {
    1: (0b00000011, "mode"),
    2: (0b00000100, "ox or red"),
    3: (0b00001000, "error"),
    21: (0b00010000, "control changes"),
    31: (0b00100000, "Ns changes"),
    65: (0b10000000, "counter inc."),
}

# Complete data column mappings from YADG
data_columns = {
    4: ("<f8", "time", "s"),
    5: ("<f4", "control", "V/mA"),
    6: ("<f4", "Ewe", "V"),
    7: ("<f8", "dq", "mA·h"),
    8: ("<f4", "I", "mA"),
    9: ("<f4", "Ece", "V"),
    11: ("<f8", "<I>", "mA"),
    13: ("<f8", "(Q-Qo)", "mA·h"),
    15: ("<f4", "Phase(Z1)", "deg"),
    16: ("<f4", "Analog IN 1", "V"),
    17: ("<f4", "Analog IN 2", "V"),
    19: ("<f4", "control_V", "V"),
    20: ("<f4", "control_I", "mA"),
    23: ("<f8", "dQ", "mA·h"),
    24: ("<f8", "cycle number", None),
    32: ("<f4", "freq", "Hz"),
    33: ("<f4", "|Ewe|", "V"),
    34: ("<f4", "|I|", "A"),
    35: ("<f4", "Phase(Z)", "deg"),
    36: ("<f4", "|Z|", "Ω"),
    37: ("<f4", "Re(Z)", "Ω"),
    38: ("<f4", "-Im(Z)", "Ω"),
    39: ("<u2", "I Range", None),
    45: ("<f4", "|Z1|", "Ω"),
    46: ("<f4", "|Z2|", "Ω"),
    69: ("<f4", "Rwe", "Ω"),
    70: ("<f4", "Pwe", "W"),
    74: ("<f8", "|Energy|", "W·h"),
    75: ("<f4", "Analog OUT", "V"),
    76: ("<f4", "<I>", "mA"),
    77: ("<f4", "<Ewe>", "V"),
    78: ("<f4", "Cs⁻²", "µF⁻²"),
    96: ("<f4", "|Ece|", "V"),
    98: ("<f4", "Phase(Zce)", "deg"),
    99: ("<f4", "|Zce|", "Ω"),
    100: ("<f4", "Re(Zce)", "Ω"),
    101: ("<f4", "-Im(Zce)", "Ω"),
    105: ("<f4", "-Im(Z1)", "Ω"),
    106: ("<f4", "-Im(Z2)", "Ω"),
    110: ("<f8", "Energy ce", "W·h"),
    112: ("<f8", "Energy we", "W·h"),
    115: ("<f8", "Energy ce charge", "W·h"),  # Your Column ID 115!
    116: ("<f8", "Energy ce discharge", "W·h"),
    123: ("<f8", "Energy we charge", "W·h"),
    124: ("<f8", "Energy we discharge", "W·h"),
    125: ("<f8", "Capacitance charge", "µF"),
    126: ("<f8", "Capacitance discharge", "µF"),
    131: ("<u2", "Ns", None),
    135: ("<f4", "<E1>", "V"),
    136: ("<f4", "<E2>", "V"),
    163: ("<f4", "|Estack|", "V"),
    166: ("<f4", "Phase(Zstack)", "deg"),
    167: ("<f4", "|Zstack|", "Ω"),
    168: ("<f4", "Rcmp", "Ω"),
    169: ("<f4", "Cs", "µF"),
    172: ("<f4", "Cp", "µF"),
    173: ("<f4", "Cp⁻²", "µF⁻²"),
    174: ("<f4", "<Ewe>", "V"),
    175: ("<f4", "|Zwe-ce|", "Ω"),
    176: ("<f4", "Re(Zwe-ce)", "Ω"),
    177: ("<f4", "-Im(Zwe-ce)", "Ω"),
    178: ("<f4", "(Q-Qo)", "C"),
    179: ("<f4", "dQ", "C"),
    182: ("<f8", "step time", "s"),
    185: ("<f4", "<Ece>", "V"),
    206: ("<f4", "Temperature", "°C"),
    211: ("<f8", "Q charge or discharge", "C"),
    212: ("<u4", "half cycle", None),
    213: ("<u4", "z cycle", None),
    215: ("<f4", "<Ece>", "V"),
    217: ("<f4", "THD Ewe", "%"),
    218: ("<f4", "THD I", "%"),
    219: ("<f4", "THD Ece", "%"),
    220: ("<f4", "NSD Ewe", "%"),
    221: ("<f4", "NSD I", "%"),
    222: ("<f4", "NSD Ece", "%"),
    223: ("<f4", "NSR Ewe", "%"),
    224: ("<f4", "NSR I", "%"),
    225: ("<f4", "NSR Ece", "%"),
    230: ("<f4", "|Ewe h2|", "V"),
    231: ("<f4", "|Ewe h3|", "V"),
    232: ("<f4", "|Ewe h4|", "V"),
    233: ("<f4", "|Ewe h5|", "V"),
    234: ("<f4", "|Ewe h6|", "V"),
    235: ("<f4", "|Ewe h7|", "V"),
    236: ("<f4", "|I h2|", "A"),
    237: ("<f4", "|I h3|", "A"),
    238: ("<f4", "|I h4|", "A"),
    239: ("<f4", "|I h5|", "A"),
    240: ("<f4", "|I h6|", "A"),
    241: ("<f4", "|I h7|", "A"),
    242: ("<f4", "|Ece h2|", "V"),
    243: ("<f4", "|Ece h3|", "V"),
    244: ("<f4", "|Ece h4|", "V"),
    245: ("<f4", "|Ece h5|", "V"),
    246: ("<f4", "|Ece h6|", "V"),
    247: ("<f4", "|Ece h7|", "V"),
}

# Conflict resolution for ambiguous column IDs
conflict_columns = {
    174: {
        6: ("<f4", "Phase(Zwe-ce)", "deg"),
        77: ("<f4", "Phase(Zwe-ce)", "deg"),
    },
}

# Technique-dependent column names
technique_dependent_ids = {
    6: {
        "BCD": "Ecell",
    }
}


class FinalMPRParser:
    """Final MPR parser using YADG's complete logic with Polars output"""

    def __init__(self):
        self.debug = False

    def read_header(self, data: bytes, offset: int, dtype: np.dtype) -> Optional[Dict[str, Any]]:
        """Read module header and return as dictionary"""
        try:
            if len(data) < offset + dtype.itemsize:
                return None

            value = np.frombuffer(data, offset=offset, dtype=dtype, count=1)[0]

            header_dict = {}
            for field_name in dtype.names:
                field_value = value[field_name]
                if hasattr(field_value, 'decode'):
                    header_dict[field_name] = field_value.decode('ascii', errors='ignore').strip()
                else:
                    header_dict[field_name] = field_value.item() if hasattr(field_value, 'item') else field_value

            return header_dict

        except Exception as e:
            if self.debug:
                print(f"Error reading header with dtype {dtype}: {e}")
            return None

    def parse_columns(self, column_ids: List[int], technique: str = "") -> Tuple[List, List, List, Dict]:
        """Parse column IDs using YADG's complete logic"""
        names = []
        dtypes = []
        units = []
        flags = {}

        for id in column_ids:
            idd = id % 256

            # Check flag columns first
            if id in flag_columns:
                bitmask, name = flag_columns[id]
                flags[name] = bitmask
                if "flags" not in names:
                    names.append("flags")
                    dtypes.append("|u1")
                    units.append(None)

            # Check regular data columns
            elif idd in data_columns:
                dtype, name, unit = data_columns[idd]

                # Handle technique-dependent naming
                if idd in technique_dependent_ids:
                    name = technique_dependent_ids[idd].get(technique, name)

                # Handle duplicates
                if name in names:
                    if self.debug:
                        print(f"Column ID {id} ({idd}) is duplicate of '{name}' with unit '{unit}'")
                    name = f"duplicate_{name}"

                names.append(name)
                dtypes.append(dtype)
                units.append(unit)

            # Check conflict columns
            elif idd in conflict_columns:
                resolved = False
                for cid, cvals in conflict_columns[idd].items():
                    if cid in column_ids:
                        dtype, name, unit = cvals
                        names.append(name)
                        dtypes.append(dtype)
                        units.append(unit)
                        if self.debug:
                            print(f"Resolved conflict for column ID {id} ({idd}) as '{name}'")
                        resolved = True
                        break

                if not resolved:
                    # Fallback to unknown
                    name = f"unknown_{len(names)}"
                    if self.debug:
                        print(f"Unresolved conflict column ID {id} assigned to '{name}'")
                    names.append(name)
                    dtypes.append("<f4")
                    units.append(None)

            else:
                # Completely unknown columns - handle gracefully
                name = f"unknown_{len(names)}"
                if self.debug:
                    print(f"Unknown column ID {id} assigned to '{name}'")
                names.append(name)
                dtypes.append("<f4")  # Default to float32
                units.append(None)

        return names, dtypes, units, flags

    def process_data(self, data: bytes, version: int, technique: str = "") -> Optional[pl.DataFrame]:
        """Process data module using YADG's version-specific logic"""
        try:
            print(f"DEBUG: Using YADG-based parser, NOT galvani!")

            if len(data) < 5:
                print("Data module too small")
                return None

            # Read data header
            n_datapoints = np.frombuffer(data, offset=0x0000, dtype="<u4", count=1)[0]
            n_columns = np.frombuffer(data, offset=0x0004, dtype="|u1", count=1)[0]

            if self.debug:
                print(f"Data points: {n_datapoints}, Columns: {n_columns}")

            if n_datapoints == 0 or n_columns == 0:
                print("No data points or columns")
                return None

            # YADG's version-specific endianness handling
            if version in {10, 11}:
                column_ids = np.frombuffer(data, offset=0x005, dtype=">u2", count=n_columns)
            elif version in {2, 3}:
                column_ids = np.frombuffer(data, offset=0x005, dtype="<u2", count=n_columns)
            else:
                column_ids = np.frombuffer(data, offset=0x005, dtype="<u2", count=n_columns)

            if self.debug:
                print(f"Column IDs: {list(column_ids)}")

            # Parse columns with YADG's complete logic
            namelist, dtypelist, unitlist, flaglist = self.parse_columns(list(column_ids), technique)

            # Create numpy dtype for structured array
            data_dtype = np.dtype(list(zip(namelist, dtypelist)))

            # YADG's version-specific data offset
            if version in {10, 11}:
                offset = 0x3EF
            elif version == 2:
                offset = 0x195
            elif version == 3:
                offset = 0x196
            else:
                offset = 0x195

            if self.debug:
                print(f"Using data offset: 0x{offset:X} for version {version}")
                print(f"Expected dtype: {data_dtype}")

            # Validate data size
            expected_size = offset + (data_dtype.itemsize * n_datapoints)
            if len(data) < expected_size:
                available_points = max(0, (len(data) - offset) // data_dtype.itemsize)
                if available_points > 0:
                    n_datapoints = available_points
                    if self.debug:
                        print(f"Reading {n_datapoints} available points (truncated)")
                else:
                    print("No data available at calculated offset")
                    return None

            # Read structured data
            values = np.frombuffer(data, offset=offset, dtype=data_dtype, count=n_datapoints)

            # Convert to list of dictionaries
            data_dicts = []
            for value in values:
                row_dict = dict(zip(value.dtype.names, value.item()))

                # Handle flag columns
                if flaglist and "flags" in row_dict:
                    flag_bits = row_dict.pop("flags")
                    for name, bitmask in flaglist.items():
                        shift = (bitmask & -bitmask).bit_length() - 1
                        row_dict[name] = bool((flag_bits & bitmask) >> shift)

                data_dicts.append(row_dict)

            # Convert to polars DataFrame
            df = pl.DataFrame(data_dicts)

            if self.debug:
                print(f"SUCCESS: Created DataFrame with shape {df.shape}")
                print(f"Columns: {df.columns}")

            return df

        except Exception as e:
            print(f"Error processing data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def process_modules(self, contents: bytes) -> Tuple[Optional[pl.DataFrame], Dict, Dict]:
        """Process modules using YADG's robust header detection"""
        modules = contents.split(b"MODULE")[1:]
        settings = {}
        data_df = None
        log = {}
        technique = ""

        if self.debug:
            print(f"Found {len(modules)} modules")

        for i, module in enumerate(modules):
            if len(module) == 0:
                continue

            # Try different header formats
            header = None
            mhd = None

            for mhd_try in module_header_dtypes:
                header = self.read_header(module, 0x0000, mhd_try)

                if header is None:
                    continue

                # Handle 0xFFFFFFFF length issue
                if header["length"] == 0xFFFFFFFF:
                    header["length"] = len(module) - mhd_try.itemsize
                    if self.debug:
                        print(f"Fixed invalid length 0xFFFFFFFF to {header['length']}")

                # Validate length
                if len(module) >= mhd_try.itemsize + header["length"]:
                    mhd = mhd_try
                    if self.debug:
                        print(
                            f"Module {i}: '{header['short_name']}' version: {header.get('newver', 0) + header['oldver']}")
                    break

            if header is None or mhd is None:
                if self.debug:
                    print(f"Could not parse module {i} header")
                continue

            # Process module data
            name = header["short_name"]
            version = header.get("newver", 0) + header["oldver"]
            module_data = module[mhd.itemsize:]

            if name == "VMP Set":
                settings["technique"] = "Unknown"
                settings["version"] = version
                technique = "Unknown"

            elif name == "VMP data":
                data_df = self.process_data(module_data, version, technique)

            elif name == "VMP LOG":
                log["version"] = version

        return data_df, settings, log

    def parse_file(self, mpr_path: str) -> Optional[pl.DataFrame]:
        """Main parsing function"""
        try:
            with open(mpr_path, 'rb') as f:
                contents = f.read()

            # Handle magic variants
            magic_variants = [
                b"BIO-LOGIC MODULAR FILE\x1a\x00\x00\x00\x00",
                b"BIO-LOGIC MODULAR FILE\x1a    ",
                b"BIO-LOGIC MODULAR FILE\x1a"
            ]

            magic_found = False
            skip_bytes = 0

            for magic in magic_variants:
                if contents.startswith(magic):
                    skip_bytes = len(magic)
                    magic_found = True
                    if self.debug:
                        print(f"Found magic: {magic}")
                    break

            if not magic_found:
                print("Invalid MPR file magic")
                return None

            # Process modules
            data_df, settings, log = self.process_modules(contents[skip_bytes:])

            return data_df

        except Exception as e:
            print(f"Error parsing file: {e}")
            import traceback
            traceback.print_exc()
            return None


def parse_mpr_file_test(mpr_path: str, debug: bool = False) -> Optional[pl.DataFrame]:
    """Test function for PyCharm"""
    print(f"Final MPR Parser Test: {mpr_path}")
    print("-" * 60)

    parser = FinalMPRParser()
    parser.debug = debug

    df = parser.parse_file(mpr_path)

    if df is not None:
        print("SUCCESS! MPR file parsed with YADG logic")
        print(f"Shape: {df.shape}")
        print(f"Columns: {df.columns}")

        # Show first few rows
        print(f"\nFirst 3 rows:")
        print(df.head(3))

        # Show column types
        print(f"\nColumn types:")
        for col in df.columns[:10]:  # First 10 columns
            dtype = df[col].dtype
            print(f"  {col}: {dtype}")

        if len(df.columns) > 10:
            print(f"  ... and {len(df.columns) - 10} more columns")

        return df
    else:
        print("FAILED to parse MPR file")
        return None


def map_to_universal_schema(df: pl.DataFrame) -> pl.DataFrame:
    """Map to your universal schema"""
    column_mapping = {
        "time": "time_s",
        "Ewe": "potential_v",
        "I": "current_a",
        "(Q-Qo)": "capacity_ah",
        "dQ": "capacity_delta_ah",
        "|Energy|": "energy_wh",
        "Energy ce charge": "energy_charge_wh",
        "Energy ce discharge": "energy_discharge_wh",
        "Temperature": "temperature_c",
        "cycle number": "cycle_number",
        # Add more mappings as needed
    }

    rename_dict = {}
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            rename_dict[old_name] = new_name

    if rename_dict:
        df = df.rename(rename_dict)
        print(f"Mapped {len(rename_dict)} columns to universal schema")

    return df


if __name__ == "__main__":
    # Update this path to your MPR file
    mpr_path = r"/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr"

    if not Path(mpr_path).exists():
        print(f"File not found: {mpr_path}")
        print("Please update the mpr_path variable")
        sys.exit(1)

    # Parse with complete YADG logic
    df = parse_mpr_file_test(mpr_path, debug=True)

    if df is not None:
        print("\n" + "=" * 60)
        print("SUCCESS: MPR parsed with complete YADG logic!")

        # Map to universal schema
        universal_df = map_to_universal_schema(df)
        print(f"\nUniversal schema shape: {universal_df.shape}")

        # PyCharm debugging - set breakpoint here
        print(f"\nBreakpoint here to inspect 'df' and 'universal_df'")

    else:
        print("\n" + "=" * 60)
        print("FAILED: Could not parse MPR file")