from __future__ import annotations

from pathlib import Path

import runpy
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

runpy.run_path(str(Path(__file__).with_name("sentinel_dashboard.py")), run_name="__main__")
