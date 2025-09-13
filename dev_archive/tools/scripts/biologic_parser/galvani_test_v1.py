#!/usr/bin/env python3
"""
Basic test script for reading BioLogic MPR files using galvani
"""

import sys
from pathlib import Path

try:
    from galvani import BioLogic
    import pandas as pd
    import polars as pl
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install galvani pandas polars")
    sys.exit(1)


def mpr_file_test(mpr_path):
    """Test reading a single MPR file and show basic info"""

    print(f"Testing MPR file: {mpr_path}")
    print("-" * 50)

    try:
        # Read MPR file using galvani
        mpr_file = BioLogic.MPRfile(mpr_path)

        # Basic file info
        print(f"Start date: {mpr_file.startdate}")
        print(f"End date: {mpr_file.enddate}")
        print(f"Number of modules: {len(mpr_file.modules)}")

        # Show module info
        print("\nModules found:")
        for i, module in enumerate(mpr_file.modules):
            print(f"  {i}: {module}")

        # Data info
        data = mpr_file.data
        print(f"\nData shape: {data.shape}")
        print(f"Data type: {type(data)}")
        print(f"Column names: {data.dtype.names}")

        # Convert to pandas for easy viewing
        df_pandas = pd.DataFrame(data)
        print(f"\nPandas DataFrame shape: {df_pandas.shape}")
        print(f"Columns: {list(df_pandas.columns)}")

        # Show first few rows
        print("\nFirst 3 rows:")
        print(df_pandas.head(3))

        # Convert to polars
        df_polars = pl.from_pandas(df_pandas)
        print(f"\nPolars DataFrame shape: {df_polars.shape}")
        print(f"Polars schema: {df_polars.schema}")

        return df_polars

    except Exception as e:
        print(f"Error reading MPR file: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # TODO: Set your MPR file path here
    mpr_path = r"/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr"
    # Or uncomment this to use file dialog (requires tkinter)
    # from tkinter import filedialog
    # mpr_path = filedialog.askopenfilename(
    #     title="Select MPR file",
    #     filetypes=[("MPR files", "*.mpr"), ("All files", "*.*")]
    # )

    if not Path(mpr_path).exists():
        print(f"File not found: {mpr_path}")
        print("Please update the mpr_path variable in the script")
        sys.exit(1)

    if not mpr_path.endswith('.mpr'):
        print(f"Warning: File doesn't have .mpr extension: {mpr_path}")

    df = mpr_file_test(mpr_path)

    if df is not None:
        print("\n" + "=" * 50)
        print("SUCCESS: MPR file parsed successfully!")
        print("Ready for Step 2: Universal schema transformation")

        # PyCharm-friendly: You can now inspect these variables in the debugger
        # Set a breakpoint here to explore the data
        pandas_df = df.to_pandas()  # For PyCharm's DataFrame viewer
        print(f"\nSet breakpoint here to inspect data in PyCharm debugger")
        print(f"Variables available: df (polars), pandas_df (pandas)")

    else:
        print("\n" + "=" * 50)
        print("FAILED: Could not parse MPR file")