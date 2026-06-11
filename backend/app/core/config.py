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
    GROQ_MAX_TOKENS: int = 1024  # R5-FIX: augmenté pour éviter troncature des procédures N3
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    
    # Language Settings
    DEFAULT_LANGUAGE: str = "fr"
    SUPPORTED_LANGUAGES: str = "fr,en"
    TIMEZONE: str = "Europe/Paris"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ANONYMIZE_LLM_CALLS: bool = True  # Masquer les données sensibles avant appel LLM (actif par défaut)
    
    # Application Settings
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Collector Settings
    GIT_REPO_PATH: Optional[str] = None
    LOG_FILES_PATH: Optional[str] = None

    # ── Live Diagnostics — accès DB via SSH → psql ────────────────────────
    # L'accès à la base BRASIL se fait uniquement via SSH → psql sur le serveur DB.
    # Pas de connexion TCP directe (port 5432) — seul le port SSH (22) est requis.
    # Le nom de la DB et le user psql sont passés à SshPsqlDbService :
    BRASIL_PSQL_DB_NAME: str = "brasil"
    BRASIL_PSQL_DB_USER: str = "postgres"
    BRASIL_PSQL_DB_HOST: str = "localhost"   # PostgreSQL écoute sur localhost:5432 du serveur DB
    BRASIL_PSQL_DB_PORT: int = 5432
    BRASIL_PSQL_BIN:     str = "/opt/pgsql/na/9.4.4/bin/psql"
    BRASIL_PSQL_LIB:     str = "/opt/pgsql/na/9.4.4/lib"

    # ── SSH Operational Access ─────────────────────────────────────────────
    # Convention de nommage des serveurs BRASIL :
    #   Prod : op49m{type}{instance}  ex: op49mdb11 (DB prod), op49mwb11 (WA prod)
    #   Dev  : dv49m{type}{instance}  ex: dv49mdb31 (DB dev),  dv49mwb31 (WA dev)
    #
    # 3 types de serveurs :
    #   DB = base de données PostgreSQL  (op49mdb* / dv49mdb*)
    #   DE = Data Extractor              (op49mde* / dv49mde*)
    #   WA = serveur applicatif Tomcat   (op49mwb* / dv49mwb*)
    #
    # Renseigner SSH_BRASIL_ENV pour savoir quel env est connecté (info only)

    SSH_BRASIL_ENV: str = "prod"           # "prod" | "dev" | "test"

    # Server DB — Brasil PostgreSQL + accès psql
    # prod: op49mdb11  |  dev: dv49mdb31
    SSH_BRASIL_HOST: str = ""
    SSH_BRASIL_PORT: int = 22
    SSH_BRASIL_USER: str = ""              # prod: op49mbdd  |  dev: dv49mbdd
    SSH_BRASIL_PASSWORD: str = ""
    SSH_BRASIL_PRIVATE_KEY: str = ""
    SSH_BRASIL_PRIVATE_KEY_PASS: str = ""

    # Server DE — Data Extractor
    # prod: op49mde11  |  dev: dv49mde31
    SSH_DE_HOST: str = ""
    SSH_DE_PORT: int = 22
    SSH_DE_USER: str = ""
    SSH_DE_PASSWORD: str = ""
    SSH_DE_PRIVATE_KEY: str = ""
    SSH_DE_PRIVATE_KEY_PASS: str = ""

    # Server WA — Serveur applicatif (WAR IHM + WS, Tomcat)
    # prod: op49mwb11  |  dev: dv49mwb31
    SSH_WA_HOST: str = ""
    SSH_WA_PORT: int = 22
    SSH_WA_USER: str = ""
    SSH_WA_PASSWORD: str = ""
    SSH_WA_PRIVATE_KEY: str = ""
    SSH_WA_PRIVATE_KEY_PASS: str = ""

    # SSH global options
    SSH_ENABLED: bool = False
    SSH_CONNECT_TIMEOUT_S: int = 15
    SSH_COMMAND_TIMEOUT_S: int = 30
    SSH_AUTO_ADD_HOST_KEY: bool = False    # True uniquement en dev
    SSH_KNOWN_HOSTS_PATH: str = ""

    # ── Code Intelligence (Phase 2) ────────────────────────────────────────
    CODE_INTELLIGENCE_ENABLED: bool = False
    BRASIL_SOURCE_ROOT: str = ""           # chemin vers le code source Java BRASIL
    
    # Jira Configuration
    JIRA_URL: Optional[str] = None
    JIRA_EMAIL: Optional[str] = None
    JIRA_API_TOKEN: Optional[str] = None
    JIRA_PROJECT_KEY: Optional[str] = "BRASIL"
    
    # Worker Settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"


settings = Settings()
