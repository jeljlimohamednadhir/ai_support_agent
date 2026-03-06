"""
Database Session Management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create SQLAlchemy engine
_connect_args = {}
if not settings.db_url.startswith("sqlite"):
    _connect_args["connect_timeout"] = 5  # fail fast if postgres is unreachable

engine = create_engine(
    settings.db_url,
    pool_pre_ping=False,        # avoid blocking the asyncio event loop at startup
    echo=settings.DEBUG,
    connect_args=_connect_args,
    pool_timeout=10,            # max wait for a pool connection
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
