"""
CanonicalProcedure Model - SQLAlchemy
Procédure canonique validée N3 (Mode 1 & 2)
"""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Boolean, JSON, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base_class import Base


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactScope(str, enum.Enum):
    SINGLE_CUSTOMER = "single_customer"
    MULTIPLE_CUSTOMERS = "multiple_customers"
    INFRASTRUCTURE = "infrastructure"
    PLATFORM = "platform"


class TrustLevel(str, enum.Enum):
    HIGH = "high"       # Validée N3 humainement
    MEDIUM = "medium"   # Issue du clustering, non encore validée
    LOW = "low"         # Ticket brut, non structuré


class CanonicalProcedure(Base):
    """
    Procédure canonique structurée.
    Représente un cas résolu de manière propre, validé, exploitable par le moteur.
    """
    __tablename__ = "canonical_procedures"

    id = Column(String, primary_key=True)              # Ex: "brasil_err1300_nd_delete"
    app_id = Column(String, nullable=False, index=True) # FK vers ApplicationContext.id (logique)
    title = Column(String, nullable=False)
    category = Column(String, nullable=True, index=True)  # Ex: "Data_Inconsistency"

    # Codes d'erreur associés (liste JSON: ["1300", "9903"])
    error_codes = Column(JSON, nullable=True)

    # Symptômes observés
    symptoms = Column(JSON, nullable=True)            # ["Suppression ND impossible", ...]

    # Causes racines identifiées
    root_causes = Column(JSON, nullable=True)         # ["Entrée résiduelle en base", ...]

    # Checks de diagnostic à effectuer
    diagnostic_checks = Column(JSON, nullable=True)  # ["Vérifier table X", ...]

    # Étapes de résolution
    resolution_steps = Column(JSON, nullable=True)   # ["Supprimer entrée BDD", ...]

    # Niveaux
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.MEDIUM, nullable=False)
    impact_scope = Column(Enum(ImpactScope), default=ImpactScope.SINGLE_CUSTOMER, nullable=False)
    trust_level = Column(Enum(TrustLevel), default=TrustLevel.MEDIUM, nullable=False)

    # Validation humaine
    validated_by = Column(String, nullable=True)      # Ex: "N3", "user_id"
    validated_at = Column(DateTime, nullable=True)

    # Traçabilité
    source_fr_numbers = Column(JSON, nullable=True)   # FR sources: ["FR 130", "FR 136"]
    source_cluster_id = Column(String, nullable=True) # Si généré par clustering
    source_ticket_count = Column(Integer, default=0)  # Nb de tickets ayant généré cette procédure

    # Métriques d'usage
    usage_count = Column(Integer, default=0)          # Nb fois utilisée par l'assistant
    success_count = Column(Integer, default=0)        # Nb fois marquée "utile"

    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_validated_at = Column(DateTime, nullable=True)
