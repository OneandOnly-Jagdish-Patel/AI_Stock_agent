#!/usr/bin/env python3
"""Start the trading agent dashboard API server."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.server import main

if __name__ == "__main__":
    main()
