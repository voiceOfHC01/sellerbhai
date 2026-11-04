import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings

def _get_fernet_key() -> bytes:
    # Derive a valid 32-byte URL-safe base64-encoded key from JWT_SECRET or TOKEN_ENCRYPTION_KEY
    raw_secret = getattr(settings, 'TOKEN_ENCRYPTION_KEY', '') or settings.JWT_SECRET
    digest = hashlib.sha256(raw_secret.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)

def encrypt_token(plain_token: str) -> str:
    """Encrypts a sensitive access token using AES-128-CBC / Fernet."""
    if not plain_token:
        return ""
    f = Fernet(_get_fernet_key())
    return f.encrypt(plain_token.encode('utf-8')).decode('utf-8')

def decrypt_token(encrypted_token: str) -> str:
    """Decrypts an access token."""
    if not encrypted_token:
        return ""
    try:
        f = Fernet(_get_fernet_key())
        return f.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')
    except Exception:
        # Fallback if unencrypted in development
        return encrypted_token
