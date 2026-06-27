#!/usr/bin/env python3
"""Lanceur odev — permet `python3 odev_main.py` ou `./odev_main.py` sans installation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from odev.cli import main

if __name__ == "__main__":
    main()
