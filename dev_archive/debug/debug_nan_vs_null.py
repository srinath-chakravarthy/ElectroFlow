#!/usr/bin/env python3
"""Debug whether control_I uses float('nan') vs None/null."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import polars as pl
import math

# Test both float('nan') and None patterns
def test_nan_patterns():
    """Test how Polars handles float('nan') vs None."""
    
    # Create test data with both patterns
    test_data = pl.DataFrame({
        'control_I_none': [None, None, None, 14.518, 14.518, 14.518],
        'control_I_nan': [float('nan'), float('nan'), float('nan'), 14.518, 14.518, 14.518],
        'I': [0.0, 0.0, 0.0, 14.433, 14.520, 14.521],
    })
    
    print("=== TEST DATA ===")
    print(test_data)
    
    print("\n=== POLARS NULL CHECK BEHAVIOR ===")
    
    # Test is_not_null() with both types
    null_check = test_data.with_columns([
        pl.col("control_I_none").is_not_null().alias("none_not_null"),
        pl.col("control_I_nan").is_not_null().alias("nan_not_null"),
    ])
    print(null_check.select(['control_I_none', 'control_I_nan', 'none_not_null', 'nan_not_null']))
    
    print("\n=== TESTING OUR FIX WITH NAN VALUES ===")
    
    conversion_factor = 1e-3
    
    # Test with float('nan') values (what BioLogic likely produces)
    result_nan = test_data.with_columns([
        pl.when(pl.col("control_I_nan").is_not_null())
        .then(pl.col("control_I_nan") * conversion_factor)
        .otherwise(pl.col("I") * conversion_factor)
        .alias("current_a_nan_fix")
    ])
    
    print("Result with float('nan') values:")
    print(result_nan.select(['control_I_nan', 'I', 'current_a_nan_fix']))
    
    print("\n=== ALTERNATIVE FIX: is_not_nan() ===")
    
    # Test is_not_nan() instead of is_not_null()
    result_nan_fix = test_data.with_columns([
        pl.when(pl.col("control_I_nan").is_not_nan())
        .then(pl.col("control_I_nan") * conversion_factor)
        .otherwise(pl.col("I") * conversion_factor)
        .alias("current_a_nan_aware")
    ])
    
    print("Result with is_not_nan():")
    print(result_nan_fix.select(['control_I_nan', 'I', 'current_a_nan_aware']))

if __name__ == "__main__":
    test_nan_patterns()