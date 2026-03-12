"""
Schemas Pydantic pour ApplicationContext
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AppMode(str, Enum):
    FR_RICH = "FR_RICH"
    FR_WEAK = "FR_WEAK"
    LOG_BASED = "LOG_BASED"


class LogParserStrategy(str, Enum):
    JAVA_SPRING = "java_spring"
    ORACLE = "oracle"
    NETWORK = "network"
    PYTHON = "python"
    CUSTOM = "custom"


class ApplicationContextCreate(BaseModel):
    id: str = Field(..., description="Identifiant unique de l'application (ex: BRASIL)")
    display_name: str
    description: Optional[str] = None
    mode: AppMode = AppMode.FR_WEAK

    # Sources disponibles
    has_canonical_procedures: bool = False
    has_ticket_history: bool = False
    has_logs: bool = False
    has_stack_traces: bool = False
    has_codebase: bool = False

    # Stratégie de parsing logs
    log_parser_strategy: LogParserStrategy = LogParserStrategy.CUSTOM

    # Seuils de confiance
    trust_threshold_strong: int = Field(default=70, ge=0, le=100)
    trust_threshold_medium: int = Field(default=40, ge=0, le=100)

    # Paramètres clustering
    min_cluster_frequency: int = Field(default=5, ge=1)
    max_canonical_procedures: int = Field(default=50, ge=1)

    # Isolation Qdrant
    qdrant_collection_prefix: Optional[str] = None

    extra_config: Optional[Dict[str, Any]] = None


class ApplicationContextUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[AppMode] = None
    has_canonical_procedures: Optional[bool] = None
    has_ticket_history: Optional[bool] = None
    has_logs: Optional[bool] = None
    has_stack_traces: Optional[bool] = None
    has_codebase: Optional[bool] = None
    log_parser_strategy: Optional[LogParserStrategy] = None
    trust_threshold_strong: Optional[int] = Field(default=None, ge=0, le=100)
    trust_threshold_medium: Optional[int] = Field(default=None, ge=0, le=100)
    min_cluster_frequency: Optional[int] = None
    max_canonical_procedures: Optional[int] = None
    qdrant_collection_prefix: Optional[str] = None
    is_active: Optional[bool] = None
    extra_config: Optional[Dict[str, Any]] = None


class ApplicationContextRead(BaseModel):
    id: str
    display_name: str
    description: Optional[str]
    mode: AppMode
    has_canonical_procedures: bool
    has_ticket_history: bool
    has_logs: bool
    has_stack_traces: bool
    has_codebase: bool
    log_parser_strategy: Optional[LogParserStrategy]
    trust_threshold_strong: int
    trust_threshold_medium: int
    min_cluster_frequency: int
    max_canonical_procedures: int
    qdrant_collection_prefix: Optional[str]
    is_active: bool
    extra_config: Optional[Dict[str, Any]]
    created_at: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationContextSummary(BaseModel):
    """Vue résumée pour les listes"""
    id: str
    display_name: str
    mode: AppMode
    is_active: bool
    has_canonical_procedures: bool
    has_ticket_history: bool
    has_logs: bool

    model_config = {"from_attributes": True}
