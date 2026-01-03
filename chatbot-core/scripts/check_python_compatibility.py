#!/usr/bin/env python3
"""
Python Version Compatibility Checker

This script checks if the current Python version is compatible with the
Jenkins AI Chatbot Plugin dependencies.
"""

import sys
import platform

SUPPORTED_VERSIONS = [(3, 11), (3, 12), (3, 13)]
MIN_VERSION = (3, 11)
MAX_VERSION = (3, 13)

def check_python_version():
    """Check if the current Python version is supported."""
    current_version = sys.version_info[:2]
    python_version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    print("=" * 70)
    print("Python Version Compatibility Check")
    print("=" * 70)
    print(f"\nPython Version: {python_version_str}")
    print(f"Platform: {platform.platform()}")
    print(f"Implementation: {platform.python_implementation()}")
    print(f"Architecture: {platform.machine()}")
    
    print(f"\n{'=' * 70}")
    print("Compatibility Status")
    print("=" * 70)
    
    if current_version in SUPPORTED_VERSIONS:
        print(f"✅ Python {current_version[0]}.{current_version[1]} is SUPPORTED")
        print("\nYou can proceed with installation:")
        print("  pip install -r requirements.txt")
        print("  # or for CPU-only:")
        print("  pip install -r requirements-cpu.txt")
        return 0
    
    elif current_version < MIN_VERSION:
        print(f"❌ Python {current_version[0]}.{current_version[1]} is TOO OLD")
        print(f"\nMinimum required version: Python {MIN_VERSION[0]}.{MIN_VERSION[1]}")
        print("\nPlease upgrade your Python installation:")
        print("  # Ubuntu/Debian/WSL")
        print("  sudo apt install python3.12 python3.12-venv python3.12-dev")
        print("\n  # macOS")
        print("  brew install python@3.12")
        return 1
    
    elif current_version > MAX_VERSION:
        print(f"⚠️  Python {current_version[0]}.{current_version[1]} is TOO NEW (not yet supported)")
        print(f"\nMaximum supported version: Python {MAX_VERSION[0]}.{MAX_VERSION[1]}")
        print("\nCritical dependencies (PyTorch, NumPy, Numba) have not yet released")
        print("wheels compatible with this Python version.")
        print("\nOptions:")
        print("  1. Use a supported Python version (recommended):")
        print("     - Python 3.11, 3.12, or 3.13")
        print("\n  2. Wait for dependency updates (check quarterly):")
        print("     - See docs/PYTHON_3_14_ASSESSMENT.md for details")
        print("     - Track: https://github.com/pytorch/pytorch/releases")
        print("\n  3. Build dependencies from source (not recommended):")
        print("     - Very time-consuming (1-4 hours)")
        print("     - May fail on some platforms")
        return 1
    
    else:
        print(f"⚠️  Python {current_version[0]}.{current_version[1]} status is UNKNOWN")
        print("\nThis version has not been tested. Supported versions:")
        for ver in SUPPORTED_VERSIONS:
            print(f"  - Python {ver[0]}.{ver[1]}")
        return 1

def main():
    """Main entry point."""
    try:
        exit_code = check_python_version()
        print("\n" + "=" * 70)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Error during compatibility check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
