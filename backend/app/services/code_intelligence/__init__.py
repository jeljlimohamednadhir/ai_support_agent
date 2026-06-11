"""
code_intelligence/__init__.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Code Intelligence Layer — ENABLED when BRASIL source is available.

Provides deterministic knowledge extracted from Java source code:
- Exception hierarchy (400+ classes)
- Deletion constraints (blocking conditions)
- Business rules (RF/FSC codes)
- Workflow state machines
- Throw-site context (method + line + label key)

Enable via:
    CODE_INTELLIGENCE_ENABLED=true (env var)
    or auto-enabled if BRASIL_SOURCE_ROOT exists
"""

import os
from pathlib import Path

_SOURCE_ROOT = os.getenv(
    "BRASIL_SOURCE_ROOT",
    str(Path(__file__).resolve().parents[4] / "brasil-default" / "brasil-default")
)

# Auto-enable if source root exists
CODE_INTELLIGENCE_ENABLED = (
    os.getenv("CODE_INTELLIGENCE_ENABLED", "").lower() == "true"
    or Path(_SOURCE_ROOT).exists()
)

__all__ = ["CODE_INTELLIGENCE_ENABLED"]
