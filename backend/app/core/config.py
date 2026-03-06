"""
Application Configuration
Manages environment variables and settings
"""
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from pydantic import field_validator

# Calculer le chemin du .env en dehors de la classe
_ENV_PATH = Path(__file__).parents[2] / ".env"


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        case_sensitive=True,
        extra="ignore"
    )
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Support Agent"
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            return [i.strip() for i in self.BACKEND_CORS_ORIGINS.split(",") if i.strip()]
        return self.BACKEND_CORS_ORIGINS
    
    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_support_agent"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[str] = None
    USE_SQLITE: bool = False  # PostgreSQL activé par défaut
    
    @property
    def db_url(self) -> str:
        """Build database URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.USE_SQLITE:
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ai_support.db")
            return f"sqlite:///{db_path}"
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?client_encoding=utf8"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Vector Store Configuration
    VECTOR_STORE_TYPE: str = "qdrant"  # qdrant, pinecone, weaviate
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # Neo4j Configuration (Knowledge Graph)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"
    
    # AI/LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "groq"  # openai, anthropic, groq
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_TEMPERATURE: float = 0.2
    GROQ_MAX_TOKENS: int = 4096
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    
    # Language Settings
    DEFAULT_LANGUAGE: str = "fr"
    SUPPORTED_LANGUAGES: str = "fr,en"
    TIMEZONE: str = "Europe/Paris"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Application Settings
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Collector Settings
    GIT_REPO_PATH: Optional[str] = None
    LOG_FILES_PATH: Optional[str] = None
    
    # Jira Configuration
    JIRA_URL: Optional[str] = None
    JIRA_EMAIL: Optional[str] = None
    JIRA_API_TOKEN: Optional[str] = None
    JIRA_PROJECT_KEY: Optional[str] = "BRASIL"
    
    # Worker Settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"


settings = Settings()
