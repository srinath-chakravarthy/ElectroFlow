#!/usr/bin/env python3
"""
Simple BioLogic Parser Debug Script for PyCharm

Minimal script to test parser operation and inspect DataFrames.
Set breakpoints and use PyCharm's DataFrame viewer.

Usage:
1. Update MPR_FILE_PATH with your actual .mpr file
2. Run in PyCharm with debugger
3. Set breakpoint at line marked "BREAKPOINT HERE"
4. Inspect raw_df and universal_df variables
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# =============================================================================
# CONFIGURATION - UPDATE THIS PATH
# =============================================================================

# 🔥 UPDATE THIS PATH TO YOUR ACTUAL MPR FILE
MPR_FILE_PATH = Path(r"/Users/srinathchakravarthy/Desktop/AR3677_3Electrode_GITT_EIS_1st_charge_interlayer_05_GCPL_C05.mpr")


def test_direct_parser():
    """Test BioLogic parser directly."""
    print("🧪 Testing Direct Parser")
    print("-" * 30)
    
    try:
        from src_clean.parsers.biologic import BiologicParser
        
        parser = BiologicParser()
        print(f"✅ Direct parser created: {parser.get_instrument_name()}")
        
        result = parser.parse_data(MPR_FILE_PATH)
        universal_df = result.universal_data
        metadata = result.metadata
        
        print(f"✅ Direct parsing successful: {universal_df.shape}")
        return result, "direct"
        
    except Exception as e:
        print(f"❌ Direct parser failed: {e}")
        return None, "direct"


def test_factory_auto_parse():
    """Test factory auto_parse_file integration."""
    print("\n🧪 Testing Factory Auto Parse")
    print("-" * 30)
    
    try:
        from src_clean.parsers import auto_parse_file
        
        print("🔄 Testing auto_parse_file with .mpr...")
        result = auto_parse_file(MPR_FILE_PATH)
        
        if result:
            universal_df = result.universal_data
            metadata = result.metadata
            print(f"✅ Factory parsing successful: {universal_df.shape}")
            print(f"📋 Parser used: {metadata.instrument_model}")
            return result, "factory"
        else:
            print("❌ Factory returned None - no parser found")
            return None, "factory"
            
    except Exception as e:
        print(f"❌ Factory parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return None, "factory"


def test_parser_registration():
    """Test parser registration and auto-detection."""
    print("\n🧪 Testing Parser Registration & Auto-Detection")
    print("-" * 50)
    
    try:
        from src_clean.parsers import get_parser_factory
        
        factory = get_parser_factory()
        print(f"✅ Factory obtained: {type(factory).__name__}")
        
        # Check registered parsers manually
        print(f"📋 Checking registered parsers...")
        if hasattr(factory, 'registry') and hasattr(factory.registry, '_parsers'):
            registered = factory.registry._parsers
            print(f"   Total registered: {len(registered)}")
            for instrument_name, parser_cls in registered.items():
                extensions = parser_cls().get_supported_extensions()
                print(f"   • {instrument_name} ({parser_cls.__name__}): {extensions}")
        
        # Test instrument detection directly
        print(f"\n🔍 Testing instrument detection for .mpr...")
        if hasattr(factory.registry, 'detect_instrument'):
            detected = factory.registry.detect_instrument(MPR_FILE_PATH)
            print(f"   Detected instrument: {detected}")
            
            if detected:
                print(f"✅ Auto-detection working: {detected}")
                return detected, "registration"
            else:
                print("❌ Auto-detection failed - no instrument detected")
        
        # Test individual parser can_parse
        print(f"\n🔍 Testing individual parser can_parse...")
        from src_clean.parsers.biologic import BiologicParser
        parser = BiologicParser()
        can_parse = parser.can_parse(MPR_FILE_PATH)
        print(f"   BiologicParser.can_parse(.mpr): {can_parse}")
        
        return can_parse, "registration"
            
    except Exception as e:
        print(f"❌ Registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, "registration"


def main():
    """Enhanced parser test with factory integration."""
    print("🚀 BioLogic Parser Factory Integration Test")
    print("=" * 60)
    
    # Check file exists
    if not MPR_FILE_PATH.exists():
        print(f"❌ File not found: {MPR_FILE_PATH}")
        print("Update MPR_FILE_PATH in script with your actual file")
        return
    
    print(f"📁 Using file: {MPR_FILE_PATH.name}")
    print(f"📏 File size: {MPR_FILE_PATH.stat().st_size:,} bytes")
    
    # Test results storage
    test_results = {}
    
    # Test 1: Direct parser
    result_direct, _ = test_direct_parser()
    test_results['direct'] = result_direct
    
    # Test 2: Factory auto parse
    result_factory, _ = test_factory_auto_parse()
    test_results['factory'] = result_factory
    
    # Test 3: Parser registration
    parser_registered, _ = test_parser_registration()
    test_results['registration'] = parser_registered
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 TEST SUMMARY")
    print("=" * 60)
    
    success_count = 0
    for test_name, result in test_results.items():
        if result is not None:
            print(f"✅ {test_name.upper()}: SUCCESS")
            success_count += 1
        else:
            print(f"❌ {test_name.upper()}: FAILED")
    
    print(f"\n📊 Overall: {success_count}/3 tests passed")
    
    # Return best result for inspection
    if test_results['factory']:
        print("🔍 Using factory result for inspection")
        result = test_results['factory']
    elif test_results['direct']:
        print("🔍 Using direct result for inspection")
        result = test_results['direct']
    else:
        print("🔍 No successful result for inspection")
        return None
    
    # Extract DataFrames for inspection
    universal_df = result.universal_data
    metadata = result.metadata
    raw_df = None  # Factory doesn't expose raw_df
    
    # 🔥 BREAKPOINT HERE - Inspect variables
    print(f"\n📊 Final result: {universal_df.shape}")
    print("🔍 Ready for PyCharm inspection!")
    
    return {
        'universal_df': universal_df,
        'metadata': metadata,
        'raw_df': raw_df,
        'result': result,
        'test_results': test_results
    }


if __name__ == "__main__":
    # Run and keep results in scope for debugging
    debug_data = main()
    
    # Variables available for PyCharm inspection:
    if debug_data:
        raw_df = debug_data['raw_df']
        universal_df = debug_data['universal_df'] 
        metadata = debug_data['metadata']
        result = debug_data['result']
        
        # 🔥 FINAL BREAKPOINT - All variables ready for inspection
        print("🎯 Debug complete - set breakpoint here!")