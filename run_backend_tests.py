#!/usr/bin/env python3
"""
Backend Integration Test Runner

Quick script to run backend tests with various options and output formatting.

Usage:
    python run_backend_tests.py                    # Run all tests
    python run_backend_tests.py --quick            # Skip slow tests  
    python run_backend_tests.py --verbose          # Verbose output
    python run_backend_tests.py --specific multi   # Run only multi-file tests
    python run_backend_tests.py --help            # Show options
"""

import sys
import subprocess
import argparse
from pathlib import Path
import time

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_colored(text, color):
    """Print colored text."""
    print(f"{color}{text}{Colors.END}")

def run_tests(args):
    """Run the tests with specified arguments."""
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Test file selection
    if args.specific:
        if args.specific == "multi":
            cmd.append("tests/test_backend_integration.py::TestMultiFileProcessing")
        elif args.specific == "core":
            cmd.append("tests/test_backend_integration.py::TestCoreBackendAPI")
        elif args.specific == "pipeline":
            cmd.append("tests/test_backend_integration.py::TestDataPipelineIntegrity")
        elif args.specific == "error":
            cmd.append("tests/test_backend_integration.py::TestErrorHandling")
        else:
            cmd.append(f"tests/test_backend_integration.py -k {args.specific}")
    else:
        cmd.append("tests/test_backend_integration.py")
    
    # Test options
    if args.verbose:
        cmd.extend(["-v", "-s"])
    else:
        cmd.append("-v")
    
    if args.quick:
        cmd.extend(["-m", "not slow"])
    
    if args.stop_on_first_failure:
        cmd.append("-x")
    
    # Output options
    if args.capture == "no":
        cmd.append("--capture=no")
    
    # Add timing
    cmd.append("--durations=10")
    
    return cmd

def main():
    parser = argparse.ArgumentParser(description="Run backend integration tests")
    
    parser.add_argument(
        "--quick", 
        action="store_true", 
        help="Skip slow tests (marked with @pytest.mark.slow)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed logs"
    )
    
    parser.add_argument(
        "--specific", "-s",
        choices=["core", "multi", "pipeline", "error"],
        help="Run only specific test category"
    )
    
    parser.add_argument(
        "--stop-on-first-failure", "-x",
        action="store_true", 
        help="Stop on first test failure"
    )
    
    parser.add_argument(
        "--capture",
        choices=["yes", "no"],
        default="yes",
        help="Capture stdout/stderr (default: yes)"
    )
    
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Run test file directly instead of using pytest"
    )
    
    parser.add_argument(
        "--comprehensive",
        action="store_true", 
        help="Run comprehensive validation tests (includes real data and performance tests)"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run both basic integration and comprehensive validation tests"
    )
    
    args = parser.parse_args()
    
    print_colored("🧪 Backend Integration Test Runner", Colors.BOLD + Colors.CYAN)
    print_colored("=" * 50, Colors.CYAN)
    
    # Check if test files exist
    test_file = Path("tests/test_backend_integration.py")
    if not test_file.exists():
        print_colored(f"❌ Test file not found: {test_file}", Colors.RED)
        return 1
    
    if args.comprehensive or args.all:
        comprehensive_file = Path("tests/test_comprehensive_validation.py")
        if not comprehensive_file.exists():
            print_colored(f"❌ Comprehensive test file not found: {comprehensive_file}", Colors.RED)
            return 1
    
    if args.direct:
        # Run directly
        if args.comprehensive:
            print_colored("🚀 Running comprehensive tests directly...", Colors.BLUE)
            cmd = [sys.executable, str(Path("tests/test_comprehensive_validation.py"))]
        elif args.all:
            print_colored("🚀 Running all tests directly...", Colors.BLUE)
            print_colored("Running basic integration tests first:", Colors.YELLOW)
            basic_result = subprocess.run([sys.executable, str(test_file)], check=False)
            print_colored("Running comprehensive validation tests:", Colors.YELLOW)
            cmd = [sys.executable, str(Path("tests/test_comprehensive_validation.py"))]
        else:
            print_colored("🚀 Running basic tests directly...", Colors.BLUE)
            cmd = [sys.executable, str(test_file)]
    else:
        # Run with pytest
        if args.comprehensive:
            print_colored("🚀 Running comprehensive tests with pytest...", Colors.BLUE)
            cmd = [sys.executable, "-m", "pytest", "tests/test_comprehensive_validation.py", "-v"]
        elif args.all:
            print_colored("🚀 Running all tests with pytest...", Colors.BLUE)
            cmd = [sys.executable, "-m", "pytest", "tests/test_backend_integration.py", "tests/test_comprehensive_validation.py", "-v"]
        else:
            print_colored("🚀 Running basic tests with pytest...", Colors.BLUE)
            cmd = run_tests(args)
    
    print_colored(f"Command: {' '.join(cmd)}", Colors.YELLOW)
    print()
    
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, check=False)
        end_time = time.time()
        duration = end_time - start_time
        
        print()
        print_colored("=" * 50, Colors.CYAN)
        
        if result.returncode == 0:
            print_colored(f"🎉 All tests passed! ({duration:.2f}s)", Colors.GREEN)
            print_colored("Backend is ready for beta testing! 🚀", Colors.GREEN)
        else:
            print_colored(f"⚠️  Tests failed with exit code {result.returncode} ({duration:.2f}s)", Colors.RED)
            print_colored("Please check the output above for details.", Colors.RED)
        
        return result.returncode
        
    except KeyboardInterrupt:
        print_colored("\n🛑 Tests interrupted by user", Colors.YELLOW)
        return 1
    except Exception as e:
        print_colored(f"❌ Error running tests: {e}", Colors.RED)
        return 1

if __name__ == "__main__":
    sys.exit(main())