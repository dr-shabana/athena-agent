"""Resolve CORTEX_HOME for standalone skill scripts.

Skill scripts may run outside the Athena process (e.g. system Python,
nix env, CI) where ``cortex_constants`` is not importable.  This module
provides the same ``get_cortex_home()`` and ``display_cortex_home()``
contracts as ``cortex_constants`` without requiring it on ``sys.path``.

When ``cortex_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``cortex_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``CORTEX_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from cortex_constants import display_cortex_home as display_cortex_home
    from cortex_constants import get_cortex_home as get_cortex_home
except (ModuleNotFoundError, ImportError):

    def get_cortex_home() -> Path:
        """Return the Athena home directory (default: ~/.cortex).

        Mirrors ``cortex_constants.get_cortex_home()``."""
        val = os.environ.get("CORTEX_HOME", "").strip()
        return Path(val) if val else Path.home() / ".hermes"

    def display_cortex_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``cortex_constants.display_cortex_home()``."""
        home = get_cortex_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
