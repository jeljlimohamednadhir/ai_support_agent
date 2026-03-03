"""
ErrorSignature Model - SQLAlchemy
Signature d'erreur extraite de logs/stack traces (Mode 3)
"""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Boolean, JSON, Enum
from datetime import datetime
import enum

from app.db.base_class import Base


class SignatureStatus(str, enum.Enum):
    RAW = "raw"             # Extrait automatiquement, non vérifié
    CLUSTERED = "clustered" # Regroupé avec d'autres signatures similaires
    VALIDATED = "validated" # Validé humainement


class ErrorSignature(Base):
    """
    Signature d'erreur structurée extraite depuis logs, stack traces et tickets.
    Utilisée en Mode 3 (LOG_BASED) quand aucune FR n'est disponible.
    """
    __tablename__ = "error_signatures"

    id = Column(String, primary_key=True)              # Ex: "brasil_OrderService.create.NPE"
    app_id = Column(String, nullable=False, index=True)

    # Signature technique
    signature_hash = Column(String, nullable=False, index=True)  # Hash de la signature pour dedup
    error_type = Column(String, nullable=True, index=True)   # Ex: "NullPointerException"
    module = Column(String, nullable=True, index=True)       # Ex: "OrderService"
    method = Column(String, nullable=True)                   # Ex: "create"
    error_message_pattern = Column(Text, nullable=True)      # Pattern regex ou texte partiel

    # Keywords extraits des logs
    log_keywords = Column(JSON, nullable=True)               # ["customer_id null", "ERROR OrderService"]

    # Contexte stack trace
    stack_trace_pattern = Column(Text, nullable=True)        # Début de la stack trace normalisée
    affected_classes = Column(JSON, nullable=True)           # Classes présentes dans la stack

    # Métriques historiques
    frequency = Column(Integer, default=1)                   # Nb d'occurrences
    first_seen_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)

    # Clustering
    cluster_id = Column(String, nullable=True, index=True)   # ID du cluster auquel appartient cette signature
    cluster_confidence = Column(Float, nullable=True)        # Score de confiance dans le cluster (0-1)

    # Trust
    confidence_score = Column(Float, default=0.0)            # Score calculé par TrustEngine (0-1)
    status = Column(Enum(SignatureStatus), default=SignatureStatus.RAW, nullable=False)

    # Résolution connue (si identifiée via historique)
    known_resolution = Column(Text, nullable=True)
    resolution_confidence = Column(Float, nullable=True)

    # Diagnostics probabilistes (JSON liste)
    # Ex: [{"cause": "customer_id null", "probability": 0.78}, ...]
    probable_causes = Column(JSON, nullable=True)

    # Validation
    validated_by = Column(String, nullable=True)
    validated_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
