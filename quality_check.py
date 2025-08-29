#!/usr/bin/env python3
"""
Modern code quality checker for TodoList backend.

This script uses the modern Python toolchain:
1. Ruff (fast import sorting + linting) - replaces isort, flake8, etc.
2. Black (code formatting)
3. Pylint (deep code analysis)

For CI/CD integration, run: python quality_check.py
For legacy toolchain: python quality_check_traditional.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str, is_pylint: bool = False) -> bool:
    """Run a command and return True if successful."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Special handling for pylint - check score instead of exit code
        if is_pylint and result.stdout:
            import re

            score_match = re.search(r"rated at ([\d.]+)/10", result.stdout)
            if score_match:
                score = float(score_match.group(1))
                print(f"Pylint Score: {score}/10")
                if score >= 9.5:
                    print(f"✅ {description} - PASSED (Score: {score}/10)")
                    return True
                else:
                    print(f"⚠️ {description} - LOW SCORE (Score: {score}/10, minimum: 9.5)")
                    return False

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False

    except Exception as e:
        print(f"💥 Error running {description}: {e}")
        return False


def main():
    """Run all quality checks using modern toolchain."""
    print("🚀 Running TodoList Backend Quality Checks (Modern Toolchain)")
    print("⚡ Using Ruff for fast import sorting and linting")

    # Change to project directory
    project_root = Path(__file__).parent
    print(f"Project root: {project_root}")

    checks = [
        (
            ["ruff", "check", "app/", "tests/", "--fix"],
            "Ruff - Import sorting and linting (with auto-fix)",
            False,
        ),
        (["python", "-m", "black", ".", "--check"], "Black - Code formatting check", False),
        (
            ["python", "-m", "pylint", "app/", "--score=y"],
            "Pylint - Code analysis and scoring",
            True,
        ),
    ]

    # Modern toolchain: Ruff replaces isort + flake8 for better performance

    results = []

    for cmd, description, is_pylint in checks:
        success = run_command(cmd, description, is_pylint)
        results.append((description, success))

    # Summary
    print(f"\n{'='*60}")
    print("📊 QUALITY CHECK SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{description}: {status}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All quality checks passed!")
        sys.exit(0)
    else:
        print("⚠️  Some quality checks failed. Please review and fix.")
        sys.exit(1)


if __name__ == "__main__":
    main()
