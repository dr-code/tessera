"""Feature flags and environment configuration for Tessera.

Feature flags are read once at import time. Disabled modules produce no
import or runtime failures — they exit cleanly with a user-facing error.
"""

from __future__ import annotations

import os


def _flag(env_var: str, default: bool = True) -> bool:
    """Read a boolean feature flag from an environment variable."""
    val = os.environ.get(env_var, "").strip().lower()
    if val in ("0", "false", "no", "off"):
        return False
    if val in ("1", "true", "yes", "on", ""):
        return default
    return default


# Feature flags — checked at module import time
ENABLE_DASHBOARD: bool = _flag("TESSERA_ENABLE_DASHBOARD", default=True)
ENABLE_DEBATE: bool = _flag("TESSERA_ENABLE_DEBATE", default=True)
ENABLE_COMPLIANCE: bool = _flag("TESSERA_ENABLE_COMPLIANCE", default=True)

# Core settings
DB_FILENAME: str = os.environ.get("TESSERA_DB_FILENAME", "tessera.db")
TESSERA_DIR: str = os.environ.get("TESSERA_DIR", ".tessera")
PROJECT_ROOT: str = os.environ.get("TESSERA_PROJECT_ROOT", "")

# Retrieval cache
CACHE_TTL_SECONDS: int = int(os.environ.get("TESSERA_CACHE_TTL", "900"))
CACHE_MAX_ENTRIES: int = int(os.environ.get("TESSERA_CACHE_MAX", "50"))

# Turn budget
READ_BUDGET_CHARS: int = int(os.environ.get("TESSERA_READ_BUDGET", "18000"))

# Retention caps
MAX_ACTIONS_PER_SESSION: int = 300
MAX_DECISIONS: int = 20
MAX_RETRIEVAL_CACHE: int = 50
MAX_DEBATE_TRANSCRIPT_BYTES: int = 50 * 1024  # 50 KB
MAX_TOKEN_SAVINGS_ROWS: int = 1000

# Dashboard
DASHBOARD_HOST: str = os.environ.get("TESSERA_DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT: int = int(os.environ.get("TESSERA_DASHBOARD_PORT", "5050"))

# Debate
DEBATE_MAX_ROUNDS: int = int(os.environ.get("TESSERA_DEBATE_MAX_ROUNDS", "3"))
DEBATE_CLAUDE_MODEL: str = os.environ.get(
    "TESSERA_DEBATE_MODEL", "claude-opus-4-6"
)
