#!/usr/bin/env python3
"""Launcher for Life Calendar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import main

if __name__ == "__main__":
    main()
