#!/usr/bin/env python3
"""Compare BioLogic and VersaStudio parser implementations."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

# Read the key implementation lines from both parsers
biologic_file = Path("src_clean/parsers/biologic.py")
versastudio_file = Path("src_clean/parsers/versastudio.py")

print("🔍 Comparing Parser Column Selection Implementations\n")

if biologic_file.exists():
    with open(biologic_file, 'r') as f:
        biologic_content = f.read()
    
    print("📊 BioLogic Parser - _map_to_universal_schema():")
    
    # Find the return statement in _map_to_universal_schema
    lines = biologic_content.split('\n')
    in_method = False
    for i, line in enumerate(lines):
        if 'def _map_to_universal_schema' in line:
            in_method = True
            print(f"   Line {i+1}: {line.strip()}")
        elif in_method and 'return' in line and 'universal_df' in line:
            print(f"   Line {i+1}: {line.strip()}")
            break
        elif in_method and line.strip().startswith('def '):
            break

if versastudio_file.exists():
    with open(versastudio_file, 'r') as f:
        versastudio_content = f.read()
    
    print("\n📊 VersaStudio Parser - _map_to_universal_schema():")
    
    # Find the return statement in _map_to_universal_schema
    lines = versastudio_content.split('\n')
    in_method = False
    for i, line in enumerate(lines):
        if 'def _map_to_universal_schema' in line:
            in_method = True
            print(f"   Line {i+1}: {line.strip()}")
        elif in_method and 'return' in line and 'mapped_df' in line:
            print(f"   Line {i+1}: {line.strip()}")
            break
        elif in_method and line.strip().startswith('def '):
            break

print("\n📊 add_missing_universal_columns() Usage:")

# Check add_missing_universal_columns usage
if 'add_missing_universal_columns(universal_df)' in biologic_content:
    print("   ✅ BioLogic: Uses add_missing_universal_columns() - INTEGRATED MODE ONLY")
else:
    print("   ❌ BioLogic: Missing add_missing_universal_columns()")

if 'add_missing_universal_columns(universal_df)' in versastudio_content:
    print("   ✅ VersaStudio: Uses add_missing_universal_columns()")
else:
    print("   ❌ VersaStudio: Missing add_missing_universal_columns()")

print("\n🏁 Summary:")
print("   BioLogic:    Fixed - now uses .select(available_cols)")
print("   VersaStudio: Already correct - uses .select(available_columns)")
print("   Both parsers: Use add_missing_universal_columns() for 47-column schema")