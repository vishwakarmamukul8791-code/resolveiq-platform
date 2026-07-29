import os
import json
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from backend.services.logging_service import log_info, log_error

USERS_PATH = "data/users.json"

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 12

# NIST/OWASP minimum for PBKDF2-HMAC-SHA256.
# Interview answer: "Why not bcrypt?" — bcrypt requires a native C extension.
# This project already hit one VC++ DLL mismatch on Windows (torch/VC++ issue).
# PBKDF2 via hashlib is pure stdlib — zero compiled dependencies, same security
# guarantee at 200k iterations with SHA-256.
PBKDF2_ITERATIONS = 200_000

VALID_ROLES = {"admin", "engineer"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _get_jwt_secret() -> str:

    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set in .env. Auth cannot issue or "
            "verify tokens without it."
        )

    return secret


def _load_users():

    if not os.path.exists(USERS_PATH):
        return []

    try:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError:
        return []


def _save_users(users):

    os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)

    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)


def _hash_password(password: str, salt: str = None):

    if salt is None:
        salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS
    )

    return hashed.hex(), salt


def _verify_password(password: str, stored_hash: str, salt: str) -> bool:

    candidate_hash, _ = _hash_password(password, salt)

    # constant-time comparison — plain == leaks timing info
    return hmac.compare_digest(candidate_hash, stored_hash)


# ─────────────────────────────────────────────
# User management
# ─────────────────────────────────────────────

def create_user(username: str, temp_password: str, role: str = "engineer"):
    """
    Creates a user. Called from:
      - backend/seed_admin.py  (creates the first admin on a fresh setup)
      - POST /admin/create-engineer  (admin creates engineer accounts via API)

    role must be "admin" or "engineer". Default is "engineer" since the only
    admin is typically created once via the seed script.

    Returns the temp_password so the HTTP endpoint can return it to the admin
    (shown once, never stored in plaintext).
    """

    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {VALID_ROLES}")

    users = _load_users()

    if any(u["username"] == username for u in users):
        raise ValueError(f"User '{username}' already exists.")

    password_hash, salt = _hash_password(temp_password)

    users.append({
        "username": username,
        "role": role,
        "is_active": True,
        "password_hash": password_hash,
        "salt": salt,
        "must_reset_password": True,
        "created_at": datetime.now().isoformat(),
        "last_login": None
    })

    _save_users(users)

    return temp_password


def get_user(username: str):
    """Returns the full user record or None."""

    users = _load_users()

    return next((u for u in users if u["username"] == username), None)


def list_engineers():
    """
    Returns all engineers (not admins) with safe public fields only —
    no password hashes or salts. Used by GET /admin/engineers.
    """

    users = _load_users()

    return [
        {
            "username": u["username"],
            "role": u["role"],
            "is_active": u["is_active"],
            "must_reset_password": u["must_reset_password"],
            "created_at": u["created_at"],
            "last_login": u["last_login"]
        }
        for u in users
        if u["role"] == "engineer"
    ]


def set_active_status(username: str, is_active: bool):
    """Enable or disable an engineer account. Admin-only operation."""

    users = _load_users()

    found = False

    for user in users:
        if user["username"] == username:
            if user["role"] == "admin":
                raise ValueError("Cannot deactivate an admin account.")
            user["is_active"] = is_active
            found = True

    if not found:
        raise ValueError(f"User '{username}' not found.")

    _save_users(users)


def authenticate(username: str, password: str):
    """
    Returns the user record on success, None on failure.

    Checks is_active — deactivated engineers are rejected at login.
    Existing tokens for deactivated engineers remain valid until expiry
    (12h max). Acceptable tradeoff for this use case — immediate token
    invalidation would require a token blacklist (Redis or DB), which is
    infrastructure complexity not justified here.
    """

    users = _load_users()

    user = next((u for u in users if u["username"] == username), None)

    if user is None:
        return None

    if not user.get("is_active", True):
        log_info(f"Login rejected — account inactive: {username}")
        return None

    if not _verify_password(password, user["password_hash"], user["salt"]):
        return None

    return user


def update_last_login(username: str):

    users = _load_users()

    for user in users:
        if user["username"] == username:
            user["last_login"] = datetime.now().isoformat()

    _save_users(users)


def set_new_password(username: str, new_password: str):
    """Used by POST /auth/reset-password (self-service, own account only)."""

    users = _load_users()

    found = False

    for user in users:
        if user["username"] == username:
            password_hash, salt = _hash_password(new_password)
            user["password_hash"] = password_hash
            user["salt"] = salt
            user["must_reset_password"] = False
            found = True

    if not found:
        raise ValueError(f"User '{username}' not found.")

    _save_users(users)


def admin_reset_password(target_username: str):
    """
    Admin resets an engineer's password to a new system-generated temp.
    Returns the new temp password (shown once to the admin, never stored).
    Sets must_reset_password=True so the engineer is forced to change it
    on their next login.
    """

    users = _load_users()

    found = False
    new_temp = secrets.token_urlsafe(12)

    for user in users:
        if user["username"] == target_username:
            password_hash, salt = _hash_password(new_temp)
            user["password_hash"] = password_hash
            user["salt"] = salt
            user["must_reset_password"] = True
            found = True

    if not found:
        raise ValueError(f"User '{target_username}' not found.")

    _save_users(users)

    return new_temp


# ─────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────

def create_access_token(username: str, role: str) -> str:
    """
    Role is encoded directly in the JWT payload.

    Interview answer: "Why not look up role from the database on each request?"
    Because JWT is stateless by design — the token is self-contained. Encoding
    role avoids a file I/O lookup on every protected request. The tradeoff is
    that a role change doesn't take effect until the current token expires (12h).
    For this use case that's fine.
    """

    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)

    payload = {
        "sub": username,
        "role": role,
        "exp": expire
    }

    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str):
    """Returns {"username": str, "role": str} or None if invalid/expired."""

    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[JWT_ALGORITHM]
        )

        return {
            "username": payload.get("sub"),
            "role": payload.get("role", "engineer")
        }

    except jwt.ExpiredSignatureError:
        log_info("Auth token expired.")
        return None

    except jwt.InvalidTokenError as e:
        log_error(f"Invalid auth token: {e}")
        return None


# ─────────────────────────────────────────────
# FastAPI dependencies
# ─────────────────────────────────────────────

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Returns {"username": str, "role": str} for the authenticated caller.
    Use as: current_user: dict = Depends(get_current_user)
    """

    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return payload


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency for admin-only routes.
    Use as: current_user: dict = Depends(require_admin)

    Interview answer: "How do you enforce role-based access?"
    FastAPI's dependency injection chains — require_admin calls get_current_user
    internally, so every admin route automatically gets both auth and role check
    in one Depends() call. No middleware needed, no decorator pattern.
    """

    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )

    return current_user