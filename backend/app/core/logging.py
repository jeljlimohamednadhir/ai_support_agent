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
    """StreamHandler UTF-8 safe pour Windows (évite UnicodeEncodeError cp1252)."""
    def __init__(self, stream=None):
        super().__init__(stream)
        # Forcer UTF-8 sur le stream si possible (Python 3.7+)
        if hasattr(self.stream, 'reconfigure'):
            try:
                self.stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

    def emit(self, record):
        try:
            msg = self.format(record)
            # Fallback : remplacer les caractères non-encodables
            try:
                stream = self.stream
                stream.write(msg + self.terminator)
                self.flush()
            except UnicodeEncodeError:
                safe_msg = msg.encode('utf-8', errors='replace').decode(
                    self.stream.encoding or 'utf-8', errors='replace'
                )
                self.stream.write(safe_msg + self.terminator)
                self.flush()
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
