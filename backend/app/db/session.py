"""
Database Session Management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency pour obtenir une session DB
    À utiliser avec FastAPI Depends
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    try:
        from app.models.database import Base
        Base.metadata.create_all(bind=engine)
        logger.info("[OK] Tables de base de donnees creees")
    except UnicodeDecodeError as e:
        logger.error(f"[ERREUR] Encodage UTF-8: {e}")
        logger.warning("[INFO] Database init skipped due to encoding issue")
    except Exception as e:
        logger.error(f"[ERREUR] Creation tables: {e}")
        logger.warning("[INFO] Application will continue without database")
