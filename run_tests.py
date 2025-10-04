#!/usr/bin/env python3
"""
Test runner script for TodoList backend tests.

This script provides convenient commands to run different types of tests
with appropriate configurations and options.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return its exit code."""
    if description:
        print(f"\n{'='*60}")
        print(f"🚀 {description}")
        print(f"{'='*60}")

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def setup_test_environment():
    """Set up test environment variables."""
    os.environ.setdefault("TESTING", "true")

    # Use SQLite for local testing, PostgreSQL for CI
    default_test_url = (
        "sqlite+aiosqlite:///./test.db"
        if os.getenv("CI") != "true"
        else "postgresql+asyncpg://test:test@localhost:5432/test_ai_todo"
    )
    os.environ.setdefault("TEST_DATABASE_URL", default_test_url)

    # Disable AI service in tests by default
    os.environ.setdefault("GEMINI_API_KEY", "")
    os.environ.setdefault("AI_ENABLED", "false")

    os.environ.setdefault("DATABASE_URL", os.environ.get("TEST_DATABASE_URL", default_test_url))

    print("✅ Test environment configured")


def run_unit_tests(verbose=False, coverage=True):
    """Run unit tests."""
    cmd = ["python", "-m", "pytest", "tests/unit/"]

    if verbose:
        cmd.extend(["-v", "-s"])

    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing"])

    return run_command(cmd, "Running Unit Tests")


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = ["python", "-m", "pytest", "tests/integration/"]

    if verbose:
        cmd.extend(["-v", "-s"])

    cmd.extend(["--tb=short"])

    return run_command(cmd, "Running Integration Tests")


def run_api_tests(verbose=False):
    """Run API tests."""
    cmd = ["python", "-m", "pytest", "tests/api/"]

    if verbose:
        cmd.extend(["-v", "-s"])

    cmd.extend(["--tb=short"])

    return run_command(cmd, "Running API Tests")


def run_e2e_tests(verbose=False):
    """Run end-to-end functional tests."""
    cmd = ["python", "-m", "pytest", "tests/e2e/"]

    if verbose:
        cmd.extend(["-v", "-s"])

    cmd.extend(["--tb=short", "-x"])  # Stop on first failure for E2E

    return run_command(cmd, "Running End-to-End Functional Tests")


def run_all_tests(verbose=False, coverage=True):
    """Run all tests in sequence."""
    total_failures = 0

    # Run tests in logical order
    test_suites = [
        ("Unit Tests", lambda: run_unit_tests(verbose, coverage)),
        ("Integration Tests", lambda: run_integration_tests(verbose)),
        ("API Tests", lambda: run_api_tests(verbose)),
        ("End-to-End Tests", lambda: run_e2e_tests(verbose)),
    ]

    results = []

    for suite_name, test_func in test_suites:
        exit_code = test_func()
        results.append((suite_name, exit_code))
        if exit_code != 0:
            total_failures += 1

    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST RESULTS SUMMARY")
    print(f"{'='*60}")

    for suite_name, exit_code in results:
        status = "✅ PASSED" if exit_code == 0 else "❌ FAILED"
        print(f"{suite_name:25} {status}")

    print(f"\nTotal test suites failed: {total_failures}")

    return total_failures


def run_specific_test(test_path, verbose=False):
    """Run a specific test file or test function."""
    cmd = ["python", "-m", "pytest", test_path]

    if verbose:
        cmd.extend(["-v", "-s"])

    cmd.extend(["--tb=short"])

    return run_command(cmd, f"Running Specific Test: {test_path}")


def run_tests_by_marker(marker, verbose=False):
    """Run tests filtered by marker."""
    cmd = ["python", "-m", "pytest", "-m", marker]

    if verbose:
        cmd.extend(["-v", "-s"])

    cmd.extend(["--tb=short"])

    return run_command(cmd, f"Running Tests with Marker: {marker}")


def check_test_dependencies():
    """Check if test dependencies are available."""
    try:
        import factory
        import faker
        import httpx
        import pytest

        print("✅ Core test dependencies available")
        return True
    except ImportError as e:
        print(f"❌ Missing test dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="TodoList Backend Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --all                    # Run all tests
  python run_tests.py --unit                   # Run unit tests only
  python run_tests.py --integration            # Run integration tests only
  python run_tests.py --api                    # Run API tests only
  python run_tests.py --e2e                    # Run E2E tests only
  python run_tests.py --specific tests/unit/test_user_service.py
  python run_tests.py --marker slow            # Run tests marked as 'slow'
  python run_tests.py --unit --no-coverage     # Unit tests without coverage
        """,
    )

    # Test type options
    parser.add_argument("--all", action="store_true", help="Run all test suites")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--api", action="store_true", help="Run API tests")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    parser.add_argument("--specific", type=str, help="Run specific test file or function")
    parser.add_argument("--marker", type=str, help="Run tests with specific marker")

    # Options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--check-deps", action="store_true", help="Check test dependencies")

    args = parser.parse_args()

    # Check dependencies if requested
    if args.check_deps:
        if not check_test_dependencies():
            return 1
        return 0

    # Set up test environment
    setup_test_environment()

    # Check basic dependencies
    if not check_test_dependencies():
        return 1

    # Determine what to run
    exit_code = 0

    if args.all:
        exit_code = run_all_tests(args.verbose, not args.no_coverage)
    elif args.unit:
        exit_code = run_unit_tests(args.verbose, not args.no_coverage)
    elif args.integration:
        exit_code = run_integration_tests(args.verbose)
    elif args.api:
        exit_code = run_api_tests(args.verbose)
    elif args.e2e:
        exit_code = run_e2e_tests(args.verbose)
    elif args.specific:
        exit_code = run_specific_test(args.specific, args.verbose)
    elif args.marker:
        exit_code = run_tests_by_marker(args.marker, args.verbose)
    else:
        print("❌ No test type specified. Use --help for options.")
        parser.print_help()
        return 1

    # Final summary
    if exit_code == 0:
        print("\n🎉 All tests completed successfully!")
    else:
        print(f"\n💥 Tests failed with exit code: {exit_code}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

































