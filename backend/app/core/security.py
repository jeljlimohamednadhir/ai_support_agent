"""
Security utilities for authentication and authorization.

This module centralizes password hashing, JWT creation/decoding and
lightweight value encryption. It uses application `settings` so secrets
and expiration values come from the configured environment.
"""

from datetime import datetime, timedelta
from typing import Optional, Any
import logging
import secrets
import uuid

from jose import jwt, JWTError
import bcrypt as _bcrypt
from cryptography.fernet import Fernet
import base64
import hashlib

from app.core.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES  # From .env (default 10080 = 7 days)
REFRESH_TOKEN_EXPIRE_DAYS = 7    # Longer-lived refresh tokens


def _get_fernet_key() -> bytes:
    """Génère une clé Fernet déterministe depuis `settings.SECRET_KEY`."""
    secret_key = settings.SECRET_KEY
    key = hashlib.sha256(secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_value(value: str) -> str:
    """Chiffre une valeur sensible (API key, password, ...).

    Returns the encrypted string (base64) or the original value if empty.
    Errors are logged and the original value is returned to avoid breaking
    existing callers, but a warning is emitted so operators can correct
    configuration.
    """
    if not value:
        return value
    try:
        fernet = Fernet(_get_fernet_key())
        encrypted = fernet.encrypt(value.encode())
        return encrypted.decode()
    except Exception as e:
        logger.warning("Failed to encrypt value: %s", e)
        return value


def decrypt_value(encrypted_value: str) -> str:
    """Déchiffre une valeur sensible.

    If decryption fails we assume the value was stored in cleartext and
    return it unchanged; a warning is logged.
    """
    if not encrypted_value:
        return encrypted_value
    try:
        fernet = Fernet(_get_fernet_key())
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except Exception as e:
        logger.warning("Failed to decrypt value (assuming cleartext): %s", e)
        return encrypted_value


def _truncate_bcrypt_input(s: Optional[str]) -> str:
    """Bcrypt limite la longueur des mots de passe à 72 octets; tronquer.

    Passlib/bcrypt can raise on long inputs; truncation keeps behaviour
    deterministic and avoids runtime exceptions.
    """
    if s is None:
        return ""
    return s[:72]


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token from a dictionary payload.

    The function adds `exp` (expiry), `iat` (issued at), and `jti` (JWT ID) claims.
    Signs the token with `settings.SECRET_KEY`.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add standard claims
    jti = str(uuid.uuid4())  # Unique token identifier for revocation
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    """Create refresh token with expiration time.
    
    Returns:
        tuple: (token_string, expiration_datetime)
    """
    now = datetime.utcnow()
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire
    }
    
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict:
    """Decode JWT token using configured secret and algorithm.
    
    Raises:
        JWTError: If token is invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash (Python 3.13 compatible)."""
    try:
        pwd_bytes = _truncate_bcrypt_input(plain_password).encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
        return _bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash password with bcrypt (Python 3.13 compatible)."""
    pwd_bytes = _truncate_bcrypt_input(password).encode('utf-8')
    return _bcrypt.hashpw(pwd_bytes, _bcrypt.gensalt()).decode('utf-8')


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)
