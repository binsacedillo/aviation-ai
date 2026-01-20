"""
Test runner script - Run all automated tests

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --unit       # Run only unit tests
    python run_tests.py --integration # Run only integration tests
    python run_tests.py --coverage   # Run with coverage report
"""

import subprocess
import sys


def run_command(cmd):
    """Run a command and return exit code"""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)
    result = subprocess.run(cmd, cwd=".", capture_output=False)
    return result.returncode


def main():
    args = sys.argv[1:]
    
    if "--unit" in args:
        # Run only unit tests
        exit_code = run_command([
            sys.executable, "-m", "pytest",
            "tests/test_guardrails_unit.py",
            "-v", "--tb=short"
        ])
    elif "--integration" in args:
        # Run only integration tests
        exit_code = run_command([
            sys.executable, "-m", "pytest",
            "tests/test_agent_integration.py",
            "-v", "--tb=short"
        ])
    elif "--coverage" in args:
        # Run with coverage
        exit_code = run_command([
            sys.executable, "-m", "pytest",
            "tests/",
            "-v", "--tb=short",
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term"
        ])
        if exit_code == 0:
            print("\n✅ Coverage report generated in htmlcov/index.html")
    else:
        # Run all tests
        exit_code = run_command([
            sys.executable, "-m", "pytest",
            "tests/",
            "-v", "--tb=short"
        ])
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
