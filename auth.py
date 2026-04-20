import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. Add it to .env before starting the app."
    )

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
HASH_NAME = "sha256"
PBKDF2_ITERATIONS = 390000
SALT_BYTES = 16


class AuthError(ValueError):
    """Raised when a token is invalid or expired."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        HASH_NAME,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return (
        f"pbkdf2_{HASH_NAME}${PBKDF2_ITERATIONS}$"
        f"{_b64url_encode(salt)}${_b64url_encode(derived_key)}"
    )


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False

    try:
        algorithm, iterations, salt, stored_key = stored_hash.split("$", maxsplit=3)
        if algorithm != f"pbkdf2_{HASH_NAME}":
            return False
        derived_key = hashlib.pbkdf2_hmac(
            HASH_NAME,
            password.encode("utf-8"),
            _b64url_decode(salt),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(_b64url_encode(derived_key), stored_key)


def create_access_token(
    subject: str,
    email: str,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(subject),
        "email": email,
        "exp": int(time.time()) + (expires_minutes * 60),
    }

    encoded_header = _b64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    encoded_payload = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        JWT_SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", maxsplit=2)
    except ValueError as exc:
        raise AuthError("Invalid token format") from exc

    try:
        header = json.loads(_b64url_decode(encoded_header).decode("utf-8"))
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise AuthError("Invalid token data") from exc

    if header.get("alg") != "HS256":
        raise AuthError("Unsupported token algorithm")

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = _b64url_encode(
        hmac.new(
            JWT_SECRET_KEY.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    )
    if not hmac.compare_digest(expected_signature, encoded_signature):
        raise AuthError("Invalid token signature")

    if payload.get("exp", 0) < int(time.time()):
        raise AuthError("Token has expired")

    return payload
