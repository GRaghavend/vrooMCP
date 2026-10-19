"""
pytest reads this file automatically, before any test file in this
folder -- it's the standard place for setup every test needs.

Here that's just one thing: making `backend/` and `mcp_server/` importable
as plain top-level modules (e.g. `import main`, `import shared`), the same
way backend/main.py sets up its own sys.path to reach mcp_server/. Without
this, every single test file would need to repeat those two lines itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

for _dir in (REPO_ROOT / "backend", REPO_ROOT / "mcp_server"):
    path_str = str(_dir)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
