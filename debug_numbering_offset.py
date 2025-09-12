#!/usr/bin/env python3
"""Debug why segment numbering starts from 2 instead of 1."""

import polars as pl

# Simulate the exact logic with fill_value=-1
test_df = pl.DataFrame({
    'Ns': [0, 0, 0, 1, 1, 1, 2, 2]
})

print("=== DEBUGGING SEGMENT NUMBERING OFFSET ===")
print("\nOriginal data:")
print(test_df)

print("\nStep-by-step logic:")
result = test_df.with_columns([
    pl.col('Ns').shift(1, fill_value=-1).alias('Ns_shifted'),
    (pl.col('Ns') != pl.col('Ns').shift(1, fill_value=-1)).alias('ns_change'),
    pl.col('Ns').shift(1, fill_value=-1).cast(pl.Int32).alias('shifted_int')
])

print("After shift with fill_value=-1:")
print(result.select(['Ns', 'Ns_shifted', 'ns_change']))

result = result.with_columns([
    pl.col('ns_change').cast(pl.Int32).alias('change_int'),
    pl.col('ns_change').cast(pl.Int32).cum_sum().alias('cum_sum'),
    (pl.col('ns_change').cast(pl.Int32).cum_sum() + 1).alias('segment_with_plus1')
])

print("\nAfter cumsum and +1:")
print(result.select(['Ns', 'ns_change', 'change_int', 'cum_sum', 'segment_with_plus1']))

print("\nPROBLEM IDENTIFIED:")
print("- First row: Ns=0 vs fill_value=-1 → ns_change=True → cum_sum=1 → +1 = segment 2")
print("- We want: First row should be segment 1")
print()

print("SOLUTION OPTIONS:")
print("Option 1: Don't add +1 (segments 0,1,2 instead of 1,2,3)")
result_no_plus1 = test_df.with_columns([
    (pl.col('Ns') != pl.col('Ns').shift(1, fill_value=-1)).cast(pl.Int32).cum_sum().alias('segments_no_plus1')
])
print(result_no_plus1.select(['Ns', 'segments_no_plus1']))

print("\nOption 2: Start cum_sum from 0 instead of 1")
result_start_0 = test_df.with_columns([
    ((pl.col('Ns') != pl.col('Ns').shift(1, fill_value=-1)).cast(pl.Int32).cum_sum() - 1 + 1).alias('segments_minus1_plus1')
])
print(result_start_0.select(['Ns', 'segments_minus1_plus1']))

print("\nOption 3: Use different fill_value approach")
# The real issue: cum_sum starts counting from the first True, which gives us 1,2,3...
# But we want the first segment to be 1, so we should get 1,1,1,2,2,2,3,3
print("Current: cum_sum gives segment boundaries")
print("Want: Each Ns occurrence gets same segment number")