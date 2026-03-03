"""
Database Models
SQLAlchemy models pour PostgreSQL
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Conversation(Base):
    """Table des conversations chatbot"""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    meta_data = Column(JSON, nullable=True)
    
    # Relations
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Table des messages"""
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    confidence = Column(Float, nullable=True)
    sources = Column(JSON, nullable=True)  # Liste des sources citées
    meta_data = Column(JSON, nullable=True)
    
    # Relations
    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("MessageFeedback", back_populates="message", uselist=False)


class MessageFeedback(Base):
    """Table des feedbacks sur les messages"""
    __tablename__ = "message_feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, ForeignKey("messages.id"), nullable=False, unique=True, index=True)
    rating = Column(Integer, nullable=True)  # 1-5 ou thumbs up/down
    is_helpful = Column(Boolean, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relations
    message = relationship("Message", back_populates="feedback")


class CollectionJob(Base):
    """Table des jobs de collecte"""
    __tablename__ = "collection_jobs"
    
    id = Column(String, primary_key=True)
    job_type = Column(String, nullable=False, index=True)  # code, logs, database, documentation
    status = Column(String, nullable=False, index=True)  # pending, running, completed, failed
    source = Column(JSON, nullable=False)  # Config de la source
    progress = Column(Float, default=0.0, nullable=False)
    items_collected = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relations
    artifacts = relationship("CollectionArtifact", back_populates="job", cascade="all, delete-orphan")


class CollectionArtifact(Base):
    """Table des artefacts collectés"""
    __tablename__ = "collection_artifacts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("collection_jobs.id"), nullable=False, index=True)
    artifact_type = Column(String, nullable=False, index=True)  # function, class, endpoint, table, log_entry
    name = Column(String, nullable=False)
    path = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)
    neo4j_node_id = Column(String, nullable=True, index=True)  # ID du node dans Neo4j
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relations
    job = relationship("CollectionJob", back_populates="artifacts")


class ValidationTask(Base):
    """Table des tâches de validation humaine"""
    __tablename__ = "validation_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String, nullable=False, index=True)  # response_validation, rule_extraction, pattern_confirmation
    status = Column(String, nullable=False, index=True, default="pending")  # pending, validated, rejected, skipped
    priority = Column(Integer, default=5, nullable=False, index=True)  # 1-10
    
    # Données à valider
    original_data = Column(JSON, nullable=False)
    ai_suggestion = Column(JSON, nullable=True)
    
    # Résultat de validation
    validated_data = Column(JSON, nullable=True)
    validator_id = Column(String, nullable=True, index=True)
    validation_comment = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    validated_at = Column(DateTime, nullable=True)


class Correction(Base):
    """Table des corrections ML (pour apprentissage)"""
    __tablename__ = "corrections"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    correction_type = Column(String, nullable=False, index=True)  # response, classification, extraction
    entity_type = Column(String, nullable=True)  # message, artifact, rule
    entity_id = Column(String, nullable=True, index=True)
    
    # Données de correction
    original_value = Column(JSON, nullable=False)
    corrected_value = Column(JSON, nullable=False)
    confidence_before = Column(Float, nullable=True)
    
    # Métadonnées
    corrector_id = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    applied = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    applied_at = Column(DateTime, nullable=True)


class KnowledgeNode(Base):
    """Table de cache/métadonnées des nodes Neo4j"""
    __tablename__ = "knowledge_nodes"
    
    id = Column(String, primary_key=True)  # ID du node Neo4j
    node_type = Column(String, nullable=False, index=True)  # Function, Class, Table, Endpoint, etc.
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    properties = Column(JSON, nullable=True)
    embedding_indexed = Column(Boolean, default=False, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SystemConfig(Base):
    """Table de configuration système (clé-valeur)"""
    __tablename__ = "system_config"
    
    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    category = Column(String, nullable=False, index=True)  # llm, database, integrations, ui_preferences
    is_sensitive = Column(Boolean, default=False, nullable=False)  # Si true, sera chiffré
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DiagnosticReport(Base):
    """Table des rapports de diagnostic"""
    __tablename__ = "diagnostic_reports"
    
    id = Column(String, primary_key=True)
    issue_description = Column(Text, nullable=False)
    affected_component = Column(String, nullable=True, index=True)
    severity = Column(String, nullable=False, index=True)  # low, medium, high, critical
    status = Column(String, nullable=False, index=True, default="open")  # open, in_progress, resolved, closed
    
    # Analyse IA
    root_cause = Column(Text, nullable=True)
    analysis = Column(JSON, nullable=True)  # Analyse détaillée
    confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    
    # Contexte
    error_logs = Column(JSON, nullable=True)  # Liste des logs d'erreur
    related_code = Column(JSON, nullable=True)  # Code sections pertinentes
    context = Column(JSON, nullable=True)  # Contexte additionnel
    
    # Suggestions et résolution
    suggested_fixes = Column(JSON, nullable=True)  # Liste des solutions suggérées
    applied_fix = Column(JSON, nullable=True)  # Solution appliquée
    resolution_notes = Column(Text, nullable=True)
    
    # Métadonnées
    requester_id = Column(String, nullable=True, index=True)
    assigned_to = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relations
    similar_issues = relationship("SimilarIssue", back_populates="diagnostic", cascade="all, delete-orphan")


class SimilarIssue(Base):
    """Table des issues similaires (pour pattern matching)"""
    __tablename__ = "similar_issues"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    diagnostic_id = Column(String, ForeignKey("diagnostic_reports.id"), nullable=False, index=True)
    reference_issue_id = Column(String, nullable=True)  # ID d'une autre issue ou ticket Jira
    similarity_score = Column(Float, nullable=False)  # 0.0 - 1.0
    description = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relations
    diagnostic = relationship("DiagnosticReport", back_populates="similar_issues")
