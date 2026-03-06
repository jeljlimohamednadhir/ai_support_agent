"""
ApplicationContext Model
Modèle SQLAlchemy pour le profil d'une application (multi-tenant)
"""
from sqlalchemy import Column, String, Boolean, Integer, JSON, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base_class import Base


class AppMode(str, enum.Enum):
    """Mode de traitement selon la qualité des sources disponibles"""
    FR_RICH = "FR_RICH"       # Mode 1 : FR existantes et de qualité
    FR_WEAK = "FR_WEAK"       # Mode 2 : FR de mauvaise qualité ou incomplètes
    LOG_BASED = "LOG_BASED"   # Mode 3 : Pas de FR, on s'appuie sur logs + tickets + stack traces


class LogParserStrategy(str, enum.Enum):
    """Stratégie de parsing des logs selon la techno de l'app"""
    JAVA_SPRING = "java_spring"
    ORACLE = "oracle"
    NETWORK = "network"
    PYTHON = "python"
    CUSTOM = "custom"


class ApplicationContext(Base):
    """
    Profil d'une application dans le système multi-tenant.
    Définit les sources disponibles, le mode de traitement et la stratégie de trust.
    """
    __tablename__ = "application_contexts"

    id = Column(String, primary_key=True)                         # Ex: "BRASIL"
    display_name = Column(String, nullable=False)                 # Ex: "Application Brasil"
    description = Column(String, nullable=True)

    # Mode d'intelligence (détermine quel pipeline utiliser)
    mode = Column(
        Enum(AppMode, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AppMode.FR_WEAK
    )

    # Sources disponibles pour cette application
    has_canonical_procedures = Column(Boolean, default=False)
    has_ticket_history = Column(Boolean, default=False)
    has_logs = Column(Boolean, default=False)
    has_stack_traces = Column(Boolean, default=False)
    has_codebase = Column(Boolean, default=False)

    # Stratégie de parsing des logs (Mode 3)
    log_parser_strategy = Column(
        Enum(LogParserStrategy, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        default=LogParserStrategy.CUSTOM
    )

    # Seuils de confiance (0-100)
    trust_threshold_strong = Column(Integer, default=70)   # Au-dessus : diagnostic fort
    trust_threshold_medium = Column(Integer, default=40)   # Entre : diagnostic prudent
    # En-dessous du seuil medium : refus ou réponse vague

    # Paramètres de clustering (Mode 2 & 3)
    min_cluster_frequency = Column(Integer, default=5)     # Nb min de tickets pour créer un cluster
    max_canonical_procedures = Column(Integer, default=50) # Nb max de procédures canoniques

    # Isolation tenant : préfixe pour les collections Qdrant
    qdrant_collection_prefix = Column(String, nullable=True)  # Ex: "brasil_"

    # Metadata
    is_active = Column(Boolean, default=True)
    extra_config = Column(JSON, nullable=True)    # Config spécifique à l'app (libre)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
