#!/usr/bin/env python3
"""Test Polars shift() fill_value parameter."""

import polars as pl

# Test data similar to our BioLogic case
test_df = pl.DataFrame({
    'Ns': [0, 0, 0, 1, 1, 1, 2, 2]
})

print("Original data:")
print(test_df)

print("\nshift(1) without fill_value:")
result1 = test_df.with_columns([
    pl.col('Ns').shift(1).alias('Ns_shifted_null'),
    (pl.col('Ns') != pl.col('Ns').shift(1)).alias('change_null')
])
print(result1)

print("\nshift(1) with fill_value:")
# Try different fill values
result2 = test_df.with_columns([
    pl.col('Ns').shift(1, fill_value=-1).alias('Ns_shifted_fill'),
    (pl.col('Ns') != pl.col('Ns').shift(1, fill_value=-1)).alias('change_fill')
])
print(result2)

print("\nWith cumsum logic:")
result3 = result2.with_columns([
    pl.col('change_fill').cast(pl.Int32).cum_sum().alias('cum_sum'),
    (pl.col('change_fill').cast(pl.Int32).cum_sum() + 1).alias('segment_number')
])
print(result3)

print("\nTesting with different fill values:")
for fill_val in [-1, 999, None]:
    print(f"\nfill_value={fill_val}:")
    test_result = test_df.with_columns([
        (pl.col('Ns') != pl.col('Ns').shift(1, fill_value=fill_val)).alias('change'),
        (pl.col('Ns') != pl.col('Ns').shift(1, fill_value=fill_val)).cast(pl.Int32).cum_sum().alias('segments')
    ])
    print(test_result)