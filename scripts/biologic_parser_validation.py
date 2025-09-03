#!/usr/bin/env python3
"""
PyCharm-Friendly BioLogic Parser Debug Script

Interactive debugging with real MPR files in PyCharm debugger.
Set breakpoints and inspect DataFrames interactively.

Usage:
1. Update MPR_FILE_PATH with your actual file
2. Run in PyCharm
3. Set breakpoints to inspect results
4. Use PyCharm's DataFrame viewer
"""

import sys
from pathlib import Path
import polars as pl

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent  # Adjust based on your project structure
sys.path.insert(0, str(project_root))

# =============================================================================
# CONFIGURATION - UPDATE THESE PATHS
# =============================================================================

# 🔥 UPDATE THIS PATH TO YOUR ACTUAL MPR FILE
MPR_FILE_PATH = Path(r"/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr")

# Alternative paths to try (add your common locations)
ALTERNATIVE_PATHS = [
    Path(r"C:\Users\YourName\Desktop\sample.mpr"),
    Path(r"D:\data\biologic\sample.mpr"),
    Path("sample.mpr"),
    Path("../data/sample.mpr"),
    # Add more paths where your MPR files might be
]

# Debug settings
DEBUG_MODE = True
SHOW_SAMPLE_DATA = True
SAMPLE_ROWS = 5


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def find_mpr_file() -> Path:
    """Find a valid MPR file for debugging."""
    print("🔍 Looking for MPR file...")

    # Try main path first
    if MPR_FILE_PATH.exists():
        print(f"✅ Found: {MPR_FILE_PATH}")
        return MPR_FILE_PATH

    # Try alternatives
    for alt_path in ALTERNATIVE_PATHS:
        if alt_path.exists():
            print(f"✅ Found: {alt_path}")
            return alt_path

    # Not found
    print("❌ No MPR file found!")
    print("📝 Paths tried:")
    print(f"   Primary: {MPR_FILE_PATH}")
    for alt_path in ALTERNATIVE_PATHS:
        print(f"   Alternative: {alt_path}")

    raise FileNotFoundError("Update MPR_FILE_PATH in script with your actual file")


def check_imports():
    """Check that all imports work correctly."""
    print("🧪 Checking imports...")

    try:
        # Check column mappings import
        from src_clean.parsers.configs.biologic_mappings import (
            data_columns,
            conflict_columns,
            flag_columns
        )
        print(f"✅ Biologic mappings: {len(data_columns)} data columns")

        # Check parser import
        from src_clean.parsers.biologic import BiologicParser, MPRReader
        print("✅ BiologicParser and MPRReader imported")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("\n🔧 Fix suggestions:")
        print("1. Check that you created biologic.py in src_clean/parsers/")
        print("2. Check that biologic_mappings.py is in src_clean/parsers/configs/")
        print("3. Make sure __init__.py files exist")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_column_definitions():
    """Validate column definitions in detail."""
    print("\n🧪 Validating column definitions...")

    try:
        from src_clean.parsers.configs.biologic_mappings import data_columns

        # Check specific important columns
        important_columns = [
            (4, "time"),
            (6, "Ewe"),
            (8, "I"),
            (13, "(Q-Qo)"),
            (74, "|Energy|"),
            (206, "Temperature")
        ]

        print("✅ Key columns found:")
        for col_id, expected_name in important_columns:
            if col_id in data_columns:
                dtype, name, unit = data_columns[col_id]
                print(f"   {col_id}: {name} ({dtype}) [{unit}]")
                assert name == expected_name, f"Expected {expected_name}, got {name}"
            else:
                print(f"   ⚠️  Missing column {col_id}: {expected_name}")

        print(f"✅ Total columns defined: {len(data_columns)}")
        return True

    except Exception as e:
        print(f"❌ Column validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_mpr_reader(file_path: Path):
    """Run MPRReader binary parsing."""
    print(f"\n🧪 Running MPRReader with: {file_path.name}")

    try:
        from src_clean.parsers.biologic import MPRReader

        # Create reader with debug mode
        reader = MPRReader(debug=DEBUG_MODE)

        # Parse the file
        print("🔄 Parsing MPR file...")
        df = reader.parse_mpr_file(file_path)

        # 🔥 PYCHARM BREAKPOINT HERE - Inspect 'df' in debugger
        print(f"✅ Parsing successful!")
        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📋 Columns: {list(df.columns)}")

        # Show sample data if requested
        if SHOW_SAMPLE_DATA and len(df) > 0:
            print(f"\n📝 Sample data (first {SAMPLE_ROWS} rows):")
            print(df.head(SAMPLE_ROWS))

        # Check data types
        print(f"\n🔢 Column types:")
        for col in df.columns[:10]:  # First 10 columns
            print(f"   {col}: {df[col].dtype}")

        if len(df.columns) > 10:
            print(f"   ... and {len(df.columns) - 10} more columns")

        return df

    except Exception as e:
        print(f"❌ MPR reader failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_biologic_parser(file_path: Path):
    """Run full BiologicParser integration."""
    print(f"\n🧪 Running BiologicParser with: {file_path.name}")

    try:
        from src_clean.parsers.biologic import BiologicParser

        # Create parser
        parser = BiologicParser()
        print(f"✅ Parser created: {parser.get_instrument_name()}")
        print(f"✅ Supported extensions: {parser.get_supported_extensions()}")

        # Validate file
        can_parse = parser.validate_file(file_path)
        print(f"✅ File validation: {can_parse}")

        if not can_parse:
            print("❌ Parser cannot handle this file")
            return None

        # Parse metadata
        print("🔄 Extracting metadata...")
        metadata = parser.parse_metadata(file_path)
        print("✅ Metadata extracted")

        # Parse data
        print("🔄 Parsing data with universal schema...")
        result = parser.parse_data(file_path)

        # Extract DataFrame
        if hasattr(result, 'universal_data'):
            universal_df = result.universal_data
            metadata_obj = result.metadata
        else:
            universal_df = result['universal_data']
            metadata_obj = result['metadata']

        # 🔥 PYCHARM BREAKPOINT HERE - Inspect 'universal_df' and 'metadata_obj'
        print("✅ Full parsing successful!")
        print(f"📊 Universal DataFrame shape: {universal_df.shape}")
        print(f"📋 Universal columns: {list(universal_df.columns)}")

        # Show sample universal data
        if SHOW_SAMPLE_DATA and len(universal_df) > 0:
            print(f"\n📝 Universal schema sample (first {SAMPLE_ROWS} rows):")
            print(universal_df.head(SAMPLE_ROWS))

        return result

    except Exception as e:
        print(f"❌ BiologicParser failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_raw_vs_universal(raw_df: pl.DataFrame, universal_df: pl.DataFrame):
    """Compare raw biologic DataFrame vs universal schema DataFrame."""
    print("\n🔍 Comparing raw vs universal DataFrames...")

    print(f"📊 Raw DataFrame: {raw_df.shape}")
    print(f"📊 Universal DataFrame: {universal_df.shape}")

    print(f"\n📋 Raw columns: {list(raw_df.columns[:10])}")
    print(f"📋 Universal columns: {list(universal_df.columns)}")

    # Check for common time/potential/current columns
    mappings_found = []
    if "time" in raw_df.columns and "time_s" in universal_df.columns:
        mappings_found.append("time → time_s")
    if "Ewe" in raw_df.columns and "potential_v" in universal_df.columns:
        mappings_found.append("Ewe → potential_v")
    if "I" in raw_df.columns and "current_a" in universal_df.columns:
        mappings_found.append("I → current_a")

    if mappings_found:
        print(f"✅ Schema mappings found: {mappings_found}")
    else:
        print("⚠️  No obvious schema mappings detected")


def run_parser_info():
    """Display parser information and capabilities."""
    print("\n🧪 Checking parser information...")

    try:
        from src_clean.parsers.biologic import BiologicParser

        parser = BiologicParser()
        info = parser.get_parser_info()

        print("✅ Parser Information:")
        for key, value in info.items():
            print(f"   {key}: {value}")

        return True

    except Exception as e:
        print(f"❌ Parser info check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def debug_file_validation(file_path: Path):
    """Debug file validation process."""
    print(f"\n🧪 Debugging file validation for: {file_path.name}")

    try:
        from src_clean.parsers.biologic import BiologicParser

        parser = BiologicParser()

        # Check file existence
        print(f"📁 File exists: {file_path.exists()}")
        if file_path.exists():
            print(f"📏 File size: {file_path.stat().st_size:,} bytes")

        # Check extension
        extension_check = any(str(file_path).lower().endswith(ext) for ext in parser.get_supported_extensions())
        print(f"📝 Extension check: {extension_check}")

        # Check file magic for MPR files
        if str(file_path).lower().endswith('.mpr') and file_path.exists():
            with open(file_path, 'rb') as f:
                magic = f.read(23)
                magic_check = magic.startswith(b"BIO-LOGIC MODULAR FILE")
                print(f"🔮 Magic bytes check: {magic_check}")
                print(f"🔮 Magic bytes: {magic[:23]}")

        # Full validation
        can_parse = parser.validate_file(file_path)
        print(f"✅ Full validation result: {can_parse}")

        return can_parse

    except Exception as e:
        print(f"❌ File validation debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution with PyCharm-friendly breakpoints."""
    print("🚀 BioLogic Parser - PyCharm Debug Session")
    print("=" * 60)

    # Variables for inspection
    mpr_file = None
    raw_df = None
    parser_result = None
    universal_df = None

    try:
        # Step 1: Find MPR file
        mpr_file = find_mpr_file()
        print(f"📁 Using file: {mpr_file}")

        # Step 2: Check imports
        if not check_imports():
            print("❌ Fix imports first before continuing")
            return

        # Step 3: Validate columns
        if not validate_column_definitions():
            print("❌ Fix column definitions before continuing")
            return

        # Step 4: Parser information
        print("\n" + "=" * 60)
        run_parser_info()

        # Step 5: Debug file validation
        print("\n" + "=" * 60)
        debug_file_validation(mpr_file)

        # Step 6: Run MPRReader
        print("\n" + "=" * 60)
        raw_df = run_mpr_reader(mpr_file)

        # Step 7: Run BiologicParser
        if raw_df is not None:
            print("\n" + "=" * 60)
            parser_result = run_biologic_parser(mpr_file)

            # Step 8: Compare results
            if parser_result is not None:
                if hasattr(parser_result, 'universal_data'):
                    universal_df = parser_result.universal_data
                else:
                    universal_df = parser_result['universal_data']

                compare_raw_vs_universal(raw_df, universal_df)

        # 🔥 FINAL PYCHARM BREAKPOINT HERE
        # Inspect: mpr_file, raw_df, parser_result, universal_df
        print("\n" + "=" * 60)
        print("🎉 All debugging completed successfully!")
        print("🔍 Set breakpoints and use PyCharm's DataFrame viewer")
        print("📊 Variables available for inspection:")
        print("   - mpr_file: Path to MPR file")
        print("   - raw_df: Raw biologic DataFrame")
        print("   - parser_result: Full parsing result")
        print("   - universal_df: Universal schema DataFrame")

        # Keep variables in scope for PyCharm inspection
        locals_for_inspection = {
            'mpr_file': mpr_file,
            'raw_df': raw_df,
            'parser_result': parser_result,
            'universal_df': universal_df
        }

        print(f"\n🔍 Final variable summary:")
        for var_name, var_value in locals_for_inspection.items():
            if var_value is not None:
                if hasattr(var_value, 'shape'):
                    print(f"   {var_name}: DataFrame {var_value.shape}")
                else:
                    print(f"   {var_name}: {type(var_value).__name__}")
            else:
                print(f"   {var_name}: None")

        return locals_for_inspection

    except Exception as e:
        print(f"\n❌ Main execution failed: {e}")
        import traceback
        traceback.print_exc()

        # Still return what we have for inspection
        return {
            'mpr_file': mpr_file,
            'raw_df': raw_df,
            'parser_result': parser_result,
            'universal_df': universal_df
        }


if __name__ == "__main__":
    debug_results = main()

    # 🔥 FINAL BREAKPOINT - All results available in debug_results dictionary
    print(f"\n🔍 Debug session complete. Results stored in 'debug_results'")
    print("Set breakpoint here to inspect all variables!")