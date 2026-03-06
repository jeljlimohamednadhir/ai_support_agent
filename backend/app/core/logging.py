"""
Logging configuration
"""
import logging
import sys
import os
from pathlib import Path

# Éviter l'import circulaire avec settings
try:
    from app.core.config import settings
    LOG_LEVEL = getattr(logging, settings.LOG_LEVEL, logging.INFO)
except Exception:
    LOG_LEVEL = logging.INFO

_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class _SafeStreamHandler(logging.StreamHandler):
    """StreamHandler qui ignore silencieusement les erreurs de flush (Windows/OneDrive)."""
    def emit(self, record):
        try:
            super().emit(record)
        except OSError:
            pass
    def flush(self):
        try:
            super().flush()
        except OSError:
            pass


# Handler console uniquement (stdout) — version safe pour Windows/OneDrive
_handlers: list = [_SafeStreamHandler(sys.stdout)]

# FileHandler dans C:\Temp pour éviter les problèmes OneDrive
try:
    # Priorité: C:\Temp (hors OneDrive), sinon TEMP système, sinon skip
    for _candidate in [Path("C:/Temp/ai-support-agent"), Path(os.environ.get("TEMP", "C:/Temp")) / "ai-support-agent"]:
        try:
            _candidate.mkdir(parents=True, exist_ok=True)
            _log_path = _candidate / "app.log"
            _fh = logging.FileHandler(str(_log_path), encoding="utf-8", delay=True)
            _handlers.append(_fh)
            break
        except Exception:
            continue
except Exception:
    pass  # FileHandler non critique, on continue sans

logging.basicConfig(
    level=LOG_LEVEL,
    format=_fmt,
    handlers=_handlers,
    force=True,
)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)
