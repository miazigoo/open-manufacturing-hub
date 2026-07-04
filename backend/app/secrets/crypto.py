from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_DEV_KEY_SEED = "open-manufacturing-hub-development-secret-key"


class SecretCryptoError(RuntimeError):
    pass


class SecretDecryptError(SecretCryptoError):
    pass


def _fernet_key() -> bytes:
    settings = get_settings()
    raw = (settings.secret_key or "").strip()
    if not raw:
        if settings.app_env.lower() in {"production", "prod"}:
            raise SecretCryptoError("OMH_SECRET_KEY is required in production")
        logger.warning("OMH_SECRET_KEY is not set; using deterministic development key. Do not use this in production.")
        raw = _DEV_KEY_SEED
    candidate = raw.encode("utf-8")
    try:
        Fernet(candidate)
        return candidate
    except Exception:
        digest = hashlib.sha256(candidate).digest()
        return base64.urlsafe_b64encode(digest)


def encrypt_value(value: str) -> str:
    return Fernet(_fernet_key()).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(encrypted_value: str) -> str:
    try:
        return Fernet(_fernet_key()).decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise SecretDecryptError("SECRET_DECRYPT_FAILED") from exc
    except Exception as exc:
        raise SecretDecryptError("SECRET_DECRYPT_FAILED") from exc
