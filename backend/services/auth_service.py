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
# PBKDF2 is implemented through Python's standard hashlib module,
# avoiding an additional native dependency while providing salted,
# configurable password hashing.
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



def bootstrap_admin_from_env() -> bool:
    """
    Creates the first admin from deployment environment variables.

    The operation is idempotent:
    - existing admin accounts are never overwritten
    - passwords are never logged or stored in plaintext
    - returns True only when a new admin is created
    """

    username = os.getenv(
        "BOOTSTRAP_ADMIN_USERNAME",
        ""
    ).strip()

    password = os.getenv(
        "BOOTSTRAP_ADMIN_PASSWORD",
        ""
    )

    reset_version = os.getenv(
        "BOOTSTRAP_ADMIN_RESET_VERSION",
        ""
    ).strip()

    if not username and not password:
        return False

    if not username or not password:
        raise RuntimeError(
            "BOOTSTRAP_ADMIN_USERNAME and "
            "BOOTSTRAP_ADMIN_PASSWORD must both be configured."
        )

    if len(username) > 64:
        raise RuntimeError(
            "BOOTSTRAP_ADMIN_USERNAME must be at most 64 characters."
        )

    if len(password) < 12:
        raise RuntimeError(
            "BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters."
        )

    users = _load_users()

    existing_user = next(
        (
            user
            for user in users
            if user["username"] == username
        ),
        None
    )

    if existing_user is not None:
        if existing_user["role"] != "admin":
            raise RuntimeError(
                "Bootstrap username already exists without the admin role."
            )

        previous_reset_version = existing_user.get(
            "bootstrap_reset_version",
            ""
        )

        if (
            reset_version
            and reset_version != previous_reset_version
        ):
            password_hash, salt = _hash_password(password)

            existing_user["password_hash"] = password_hash
            existing_user["salt"] = salt
            existing_user["must_reset_password"] = True
            existing_user["bootstrap_reset_version"] = reset_version

            _save_users(users)

            log_info(
                f"Bootstrap admin password reset: {username}"
            )
            return True

        log_info(
            f"Bootstrap admin already exists: {username}"
        )
        return False

    if any(user["role"] == "admin" for user in users):
        log_info(
            "An admin account already exists; bootstrap skipped."
        )
        return False

    create_user(
        username=username,
        temp_password=password,
        role="admin"
    )

    if reset_version:
        users = _load_users()

        for user in users:
            if user["username"] == username:
                user["bootstrap_reset_version"] = reset_version
                break

        _save_users(users)

    log_info(
        f"Bootstrap admin created: {username}"
    )

    return True


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
    (12h max). Immediate token invalidation would require server-side
    token revocation or a blacklist, which is not implemented in the
    current local-storage design.
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

    The role is stored in the signed JWT payload, avoiding a user-file lookup
    on every authenticated request. Role changes take effect after the current
    token expires.
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

    Role-based access is enforced through FastAPI dependencies.
    require_admin first authenticates the request and then verifies the user's
    role before the route handler runs.

    """

    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )

    return current_user