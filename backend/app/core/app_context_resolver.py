"""
ApplicationContextResolver
Résout le profil d'une application et route vers le bon pipeline.
"""
import json
from pathlib import Path
from typing import Optional, Dict
from functools import lru_cache

from sqlalchemy.orm import Session

from app.models.app_context import ApplicationContext, AppMode
from app.core.logging import get_logger

logger = get_logger(__name__)

# Chemin vers les profils JSON par défaut (fallback si pas en DB)
_PROFILES_DIR = Path(__file__).parents[2] / "apps"


class ApplicationContextResolver:
    """
    Résoud le profil d'une application selon son ID.
    Ordre de résolution :
      1. Base de données (PostgreSQL) — profil dynamique
      2. Fichier JSON dans apps/<app_id>/context.json — profil statique
      3. Profil par défaut générique (mode FR_WEAK)
    """

    def __init__(self):
        self._cache: Dict[str, ApplicationContext] = {}

    def resolve(self, app_id: str, db: Optional[Session] = None) -> ApplicationContext:
        """
        Résout le contexte d'une application.
        Utilise le cache en mémoire pour éviter des allers-retours DB répétés.
        """
        app_id = app_id.upper().strip()

        if app_id in self._cache:
            return self._cache[app_id]

        # 1. Chercher en base
        if db is not None:
            ctx = db.query(ApplicationContext).filter(
                ApplicationContext.id == app_id,
                ApplicationContext.is_active == True
            ).first()
            if ctx:
                self._cache[app_id] = ctx
                logger.info(f"[ContextResolver] App '{app_id}' chargée depuis DB (mode={ctx.mode})")
                return ctx

        # 2. Chercher dans les fichiers JSON
        profile_path = _PROFILES_DIR / app_id.lower() / "context.json"
        if profile_path.exists():
            ctx = self._load_from_json(app_id, profile_path)
            if ctx:
                self._cache[app_id] = ctx
                logger.info(f"[ContextResolver] App '{app_id}' chargée depuis JSON (mode={ctx.mode})")
                return ctx

        # 3. Fallback : profil générique FR_WEAK
        ctx = self._default_context(app_id)
        self._cache[app_id] = ctx
        logger.warning(f"[ContextResolver] App '{app_id}' introuvable — profil FR_WEAK par défaut")
        return ctx

    def get_pipeline_mode(self, app_id: str, db: Optional[Session] = None) -> AppMode:
        """Retourne uniquement le mode de pipeline de l'app"""
        return self.resolve(app_id, db).mode

    def invalidate_cache(self, app_id: Optional[str] = None):
        """Invalide le cache (à appeler après mise à jour d'un profil)"""
        if app_id:
            self._cache.pop(app_id.upper(), None)
        else:
            self._cache.clear()

    # ─────────────────────────────────────────────
    # Privé
    # ─────────────────────────────────────────────

    def _load_from_json(self, app_id: str, path: Path) -> Optional[ApplicationContext]:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            ctx = ApplicationContext()
            ctx.id = app_id
            ctx.display_name = data.get("display_name", app_id)
            ctx.description = data.get("description")
            ctx.mode = AppMode(data.get("mode", "FR_WEAK"))
            ctx.has_canonical_procedures = data.get("has_canonical_procedures", False)
            ctx.has_ticket_history = data.get("has_ticket_history", False)
            ctx.has_logs = data.get("has_logs", False)
            ctx.has_stack_traces = data.get("has_stack_traces", False)
            ctx.has_codebase = data.get("has_codebase", False)
            ctx.trust_threshold_strong = data.get("trust_threshold_strong", 70)
            ctx.trust_threshold_medium = data.get("trust_threshold_medium", 40)
            ctx.min_cluster_frequency = data.get("min_cluster_frequency", 5)
            ctx.max_canonical_procedures = data.get("max_canonical_procedures", 50)
            ctx.qdrant_collection_prefix = data.get("qdrant_collection_prefix", f"{app_id.lower()}_")
            ctx.log_parser_strategy = data.get("log_parser_strategy", "custom")
            ctx.extra_config = data.get("extra_config")
            ctx.is_active = True
            return ctx

        except Exception as e:
            logger.error(f"[ContextResolver] Erreur lecture JSON pour '{app_id}': {e}")
            return None

    def _default_context(self, app_id: str) -> ApplicationContext:
        ctx = ApplicationContext()
        ctx.id = app_id
        ctx.display_name = app_id
        ctx.description = f"Application {app_id} — profil auto-généré"
        ctx.mode = AppMode.FR_WEAK
        ctx.has_canonical_procedures = False
        ctx.has_ticket_history = False
        ctx.has_logs = False
        ctx.has_stack_traces = False
        ctx.has_codebase = False
        ctx.trust_threshold_strong = 70
        ctx.trust_threshold_medium = 40
        ctx.min_cluster_frequency = 5
        ctx.max_canonical_procedures = 50
        ctx.qdrant_collection_prefix = f"{app_id.lower()}_"
        ctx.is_active = True
        return ctx


# Singleton global
app_context_resolver = ApplicationContextResolver()
