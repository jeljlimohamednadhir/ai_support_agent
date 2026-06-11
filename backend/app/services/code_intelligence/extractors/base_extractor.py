"""
code_intelligence/extractors/base_extractor.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Base class for all code intelligence extractors (Phase 2).

All extractors are DISABLED by default.
When enabled, they parse Java source files and extract structured knowledge.
NEVER expose raw source code to the LLM.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.code_intelligence import CODE_INTELLIGENCE_ENABLED
from app.services.live_diagnostics.models.evidence import CodeEvidence

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Abstract base for all source code extractors."""

    def __init__(self, source_root: str | None = None):
        self._source_root = Path(source_root) if source_root else None
        self._enabled     = CODE_INTELLIGENCE_ENABLED

    @property
    def enabled(self) -> bool:
        return self._enabled and self._source_root is not None

    def extract(self, *args, **kwargs) -> CodeEvidence:
        if not self.enabled:
            logger.debug(f"[{self.__class__.__name__}] Disabled (Phase 2).")
            return CodeEvidence(enabled=False)
        return self._extract(*args, **kwargs)

    @abstractmethod
    def _extract(self, *args, **kwargs) -> CodeEvidence:
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Exception Extractor (Phase 2 stub)
# ─────────────────────────────────────────────────────────────────────────────

class ExceptionExtractor(BaseExtractor):
    """
    Extract business exceptions and error code mappings from Java source.

    Output example:
    {
      "error_code": "1300",
      "exception":  "ConstraintViolationException",
      "condition":  "eqpt_status == 'F'",
      "throw_site": "EquipmentDeletionService.java:142"
    }
    """

    def _extract(self, operation: str) -> CodeEvidence:
        # Phase 2: scan Java files for throw statements + error codes
        logger.info(f"[ExceptionExtractor] Scanning for operation: {operation}")
        return CodeEvidence(
            enabled=True,
            operation=operation,
            exceptions=[],
            validations=[],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Validation Extractor (Phase 2 stub)
# ─────────────────────────────────────────────────────────────────────────────

class ValidationExtractor(BaseExtractor):
    """
    Extract validation rules and hard constraints from Java source.

    Output example:
    {
      "condition":  "eqpt_status == 'F'",
      "error_code": "1300",
      "message":    "Equipment closed to production",
      "type":       "hard_constraint"
    }
    """

    def _extract(self, operation: str) -> CodeEvidence:
        logger.info(f"[ValidationExtractor] Scanning for operation: {operation}")
        return CodeEvidence(
            enabled=True,
            operation=operation,
            validations=[],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Flow Extractor (Phase 2 stub)
# ─────────────────────────────────────────────────────────────────────────────

class FlowExtractor(BaseExtractor):
    """
    Detect service flows and operation chains in Java source.
    """

    def _extract(self, operation: str) -> CodeEvidence:
        return CodeEvidence(enabled=True, operation=operation)


# ─────────────────────────────────────────────────────────────────────────────
# SQL Extractor (Phase 2 stub)
# ─────────────────────────────────────────────────────────────────────────────

class SqlExtractor(BaseExtractor):
    """
    Extract SQL queries and table dependencies from Java/MyBatis/Hibernate source.
    """

    def _extract(self, operation: str) -> CodeEvidence:
        return CodeEvidence(enabled=True, operation=operation, queries=[])


# ─────────────────────────────────────────────────────────────────────────────
# Dependency Extractor (Phase 2 stub)
# ─────────────────────────────────────────────────────────────────────────────

class DependencyExtractor(BaseExtractor):
    """
    Extract service/repository/entity dependencies from Java source.
    """

    def _extract(self, operation: str) -> CodeEvidence:
        return CodeEvidence(enabled=True, operation=operation, dependencies=[])


# ─────────────────────────────────────────────────────────────────────────────
# Facade: CodeIntelligenceService
# ─────────────────────────────────────────────────────────────────────────────

class CodeIntelligenceService:
    """
    Phase 2 facade — orchestrates all extractors for a given operation.

    Usage (Phase 2):
        svc = CodeIntelligenceService(source_root="/path/to/brasil/src")
        evidence = svc.analyze("delete_equipment", "EquipmentDeletionService.java")

    Usage (Phase 1 — stub, always returns empty CodeEvidence):
        svc = CodeIntelligenceService()
        evidence = svc.analyze("delete_equipment")  # → CodeEvidence(enabled=False)
    """

    def __init__(self, source_root: str | None = None):
        self._source_root = source_root
        self._exc   = ExceptionExtractor(source_root)
        self._val   = ValidationExtractor(source_root)
        self._flow  = FlowExtractor(source_root)
        self._sql   = SqlExtractor(source_root)
        self._dep   = DependencyExtractor(source_root)

    @property
    def enabled(self) -> bool:
        return CODE_INTELLIGENCE_ENABLED and self._source_root is not None

    def analyze(
        self,
        operation:   str,
        source_file: Optional[str] = None,
    ) -> CodeEvidence:
        """
        Full code analysis for an operation.
        Returns empty CodeEvidence if disabled.
        """
        if not self.enabled:
            return CodeEvidence(enabled=False)

        # Phase 2: merge all extractor results
        exc_ev  = self._exc.extract(operation)
        val_ev  = self._val.extract(operation)
        sql_ev  = self._sql.extract(operation)
        dep_ev  = self._dep.extract(operation)

        return CodeEvidence(
            enabled=True,
            operation=operation,
            source_file=source_file,
            validations=val_ev.validations,
            exceptions=exc_ev.exceptions,
            queries=sql_ev.queries,
            dependencies=dep_ev.dependencies,
            confidence=0.85 if (val_ev.validations or dep_ev.dependencies) else 0.3,
        )
