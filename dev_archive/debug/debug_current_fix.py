#!/usr/bin/env python3
"""Debug the current_a fix implementation."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import polars as pl

# Test the Polars logic directly
def test_polars_logic():
    """Test the when/then/otherwise logic with our data pattern."""
    
    # Create test data matching our boundary rows
    test_data = pl.DataFrame({
        'control_I': [None, None, None, 14.518, 14.518, 14.518],  # None = nan for Rest phases
        'I': [0.0, 0.0, 0.0, 14.433, 14.520, 14.521],
    })
    
    print("=== TEST DATA ===")
    print(test_data)
    
    print("\n=== POLARS LOGIC TEST ===")
    
    # Test our exact logic
    control_conversion_factor = 1e-3  # mA to A
    i_conversion_factor = 1e-3        # mA to A
    
    result = test_data.with_columns([
        pl.when(pl.col("control_I").is_not_null())
        .then(pl.col("control_I") * control_conversion_factor)
        .otherwise(pl.col("I") * i_conversion_factor)
        .alias("current_a")
    ])
    
    print("Result with fix:")
    print(result.select(['control_I', 'I', 'current_a']))
    
    print("\n=== CHECK is_not_null() behavior ===")
    null_check = test_data.with_columns([
        pl.col("control_I").is_not_null().alias("control_I_not_null"),
        pl.col("control_I").is_null().alias("control_I_is_null")
    ])
    print(null_check)

if __name__ == "__main__":
    test_polars_logic()