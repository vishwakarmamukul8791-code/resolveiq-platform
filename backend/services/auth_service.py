import os
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from backend.services.logging_service import log_info, log_error
from backend.services.json_storage import (
    load_json_list,
    save_json,
    synchronized_storage,
)
from backend.services.storage_paths import data_path
from backend.services.session_service import is_session_active

USERS_PATH = data_path("users.json")

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 12

# PBKDF2 is implemented through Python's standard hashlib module,
# avoiding an additional native dependency while providing salted,
# configurable password hashing.
#
# OWASP's current guidance (2023+) for PBKDF2-HMAC-SHA256 is 600k
# iterations. Earlier records in users.json may have been hashed at the
# old 200k figure; each user record stores the iteration count it was
# actually hashed with (`pbkdf2_iterations`), so old hashes keep
# verifying correctly and are transparently re-hashed at the new,
# stronger count the next time that user logs in successfully.
PBKDF2_ITERATIONS = 600_000
LEGACY_PBKDF2_ITERATIONS = 200_000

VALID_ROLES = {"admin", "engineer"}
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


MIN_JWT_SECRET_LENGTH = 32

_WEAK_JWT_SECRETS = {
    "secret",
    "changeme",
    "change_me",
    "your-secret-key",
    "your_secret_key",
    "password",
    "jwt_secret",
    "jwt_secret_key",
    "test",
    "testing",
    "development",
}


def _get_jwt_secret() -> str:

    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set in .env. Auth cannot issue or "
            "verify tokens without it."
        )

    if (
        len(secret) < MIN_JWT_SECRET_LENGTH
        or secret.strip().lower() in _WEAK_JWT_SECRETS
    ):
        raise RuntimeError(
            "JWT_SECRET_KEY is too weak. Use a random value at least "
            f"{MIN_JWT_SECRET_LENGTH} characters long (e.g. "
            "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"`) "
            "— a short or guessable secret lets anyone forge valid tokens."
        )

    return secret


def _load_users():
    return load_json_list(USERS_PATH)


def _save_users(users):
    save_json(USERS_PATH, users)


def _hash_password(password: str, salt: str = None, iterations: int = None):

    if salt is None:
        salt = secrets.token_hex(16)

    if iterations is None:
        iterations = PBKDF2_ITERATIONS

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )

    return hashed.hex(), salt, iterations


def _verify_password(
    password: str,
    stored_hash: str,
    salt: str,
    iterations: int = None,
) -> bool:
    """
    Verifies against whatever iteration count the hash was actually
    created with. Older user records predate the `pbkdf2_iterations`
    field entirely — those are always LEGACY_PBKDF2_ITERATIONS (200k),
    the only value this codebase ever hashed with before this field
    existed.
    """

    if iterations is None:
        iterations = LEGACY_PBKDF2_ITERATIONS

    candidate_hash, _, _ = _hash_password(password, salt, iterations)

    # constant-time comparison — plain == leaks timing info
    return hmac.compare_digest(candidate_hash, stored_hash)


# ─────────────────────────────────────────────
# User management
# ─────────────────────────────────────────────

@synchronized_storage(USERS_PATH)
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

    username = username.strip()

    if not 3 <= len(username) <= 64:
        raise ValueError("Username must contain 3 to 64 characters.")

    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Username may contain only letters, numbers, dots, "
            "underscores, and hyphens."
        )

    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {VALID_ROLES}")

    users = _load_users()

    if any(u["username"] == username for u in users):
        raise ValueError(f"User '{username}' already exists.")

    password_hash, salt, iterations = _hash_password(temp_password)

    users.append({
        "username": username,
        "role": role,
        "is_active": True,
        "password_hash": password_hash,
        "salt": salt,
        "pbkdf2_iterations": iterations,
        "must_reset_password": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
        # Bumped on every password change. Tokens carry the value that
        # was current when they were issued (see create_access_token) —
        # a mismatch at request time means "issued under an old
        # password" and the token is rejected even if it hasn't expired
        # yet. This is what makes password changes actually revoke
        # previously issued tokens instead of leaving them valid until
        # their 12h expiry.
        "token_version": 0
    })

    _save_users(users)

    return temp_password



@synchronized_storage(USERS_PATH)
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
            password_hash, salt, iterations = _hash_password(password)

            existing_user["password_hash"] = password_hash
            existing_user["salt"] = salt
            existing_user["pbkdf2_iterations"] = iterations
            existing_user["must_reset_password"] = True
            existing_user["bootstrap_reset_version"] = reset_version
            existing_user["token_version"] = (
                existing_user.get("token_version", 0) + 1
            )

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


@synchronized_storage(USERS_PATH)
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


@synchronized_storage(USERS_PATH)
def _rehash_if_legacy(username: str, password: str, used_iterations: int):
    """
    Transparent upgrade path: a successful login verified against the old
    200k-iteration hash gets silently re-hashed at the current, stronger
    iteration count so accounts naturally migrate to the new standard the
    next time their owner logs in, with no forced reset and no downtime.
    """

    if used_iterations >= PBKDF2_ITERATIONS:
        return

    users = _load_users()

    for user in users:
        if user["username"] == username:
            password_hash, salt, iterations = _hash_password(password)
            user["password_hash"] = password_hash
            user["salt"] = salt
            user["pbkdf2_iterations"] = iterations
            break

    _save_users(users)


def authenticate(username: str, password: str):
    """
    Returns the user record on success, None on failure.

    Checks is_active — deactivated engineers are rejected at login.
    """

    users = _load_users()

    user = next((u for u in users if u["username"] == username), None)

    if user is None:
        return None

    if not user.get("is_active", True):
        log_info(f"Login rejected — account inactive: {username}")
        return None

    used_iterations = user.get("pbkdf2_iterations", LEGACY_PBKDF2_ITERATIONS)

    if not _verify_password(
        password,
        user["password_hash"],
        user["salt"],
        used_iterations,
    ):
        return None

    _rehash_if_legacy(username, password, used_iterations)

    return user


def verify_current_password(username: str, password: str) -> bool:
    """
    Used by POST /auth/reset-password to require proof of the current
    password before accepting a new one — closes the gap where a
    stolen-but-still-valid JWT alone would be enough to lock the real
    owner out.
    """

    user = get_user(username)

    if user is None:
        return False

    used_iterations = user.get("pbkdf2_iterations", LEGACY_PBKDF2_ITERATIONS)

    return _verify_password(
        password,
        user["password_hash"],
        user["salt"],
        used_iterations,
    )


@synchronized_storage(USERS_PATH)
def update_last_login(username: str):

    users = _load_users()

    for user in users:
        if user["username"] == username:
            user["last_login"] = datetime.now(timezone.utc).isoformat()

    _save_users(users)


@synchronized_storage(USERS_PATH)
def set_new_password(username: str, new_password: str):
    """
    Used by POST /auth/reset-password (self-service, own account only).

    Caller must already have verified the current password via
    verify_current_password() — this function only performs the write,
    so the read-verify-write isn't split across two separate storage
    lock acquisitions.

    Bumps token_version so every access token issued before this change
    stops working immediately, even if it hasn't expired yet — the
    person who set this new password is the only one who should be able
    to keep using the account from this point on.
    """

    users = _load_users()

    found = False

    for user in users:
        if user["username"] == username:
            password_hash, salt, iterations = _hash_password(new_password)
            user["password_hash"] = password_hash
            user["salt"] = salt
            user["pbkdf2_iterations"] = iterations
            user["must_reset_password"] = False
            user["token_version"] = user.get("token_version", 0) + 1
            found = True

    if not found:
        raise ValueError(f"User '{username}' not found.")

    _save_users(users)

    return next(
        user for user in users
        if user["username"] == username
    )


@synchronized_storage(USERS_PATH)
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
            if user["role"] != "engineer":
                raise ValueError(
                    "Only engineer passwords can be reset here."
                )

            password_hash, salt, iterations = _hash_password(new_temp)
            user["password_hash"] = password_hash
            user["salt"] = salt
            user["pbkdf2_iterations"] = iterations
            user["must_reset_password"] = True
            # Any token issued to this engineer before the admin's reset
            # stops working immediately, not just at its 12h expiry.
            user["token_version"] = user.get("token_version", 0) + 1
            found = True

    if not found:
        raise ValueError(f"User '{target_username}' not found.")

    _save_users(users)

    return new_temp


# ─────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────

def create_access_token(
    username: str,
    role: str,
    token_version: int = 0,
    session_id: str = None,
) -> str:
    """
    Issue a signed access token. Protected requests also reload the current
    user record, so deactivation, role, and forced-reset changes take effect
    immediately instead of waiting for this token to expire.

    token_version is stamped into the token at issue time and compared
    against the user's *current* token_version on every authenticated
    request (see get_current_user). Password changes bump the stored
    value, so tokens issued before a password change are rejected right
    away instead of remaining valid until their 12h expiry.

    session_id, when provided, is stamped in as the "sid" claim. On every
    authenticated request get_current_user checks whether that session has
    been closed (POST /auth/logout) and rejects the token immediately if
    so — without this, logout only annotated the analytics session record
    and the JWT itself stayed valid for the rest of its 12h lifetime.
    Tokens issued without a session_id (e.g. the replacement token from
    POST /auth/reset-password) skip this check and rely on token_version
    alone, same as before.
    """

    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)

    payload = {
        "sub": username,
        "role": role,
        "tv": token_version,
        "exp": expire,
    }

    if session_id:
        payload["sid"] = session_id

    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str):
    """
    Returns {"username": str, "role": str, "token_version": int} or
    None if invalid/expired.
    """

    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[JWT_ALGORITHM]
        )

        username = payload.get("sub")
        role = payload.get("role")
        token_version = payload.get("tv", 0)
        session_id = payload.get("sid")

        if (
            not isinstance(username, str)
            or not username
            or role not in VALID_ROLES
            or not isinstance(token_version, int)
        ):
            return None

        return {
            "username": username,
            "role": role,
            "token_version": token_version,
            "session_id": session_id if isinstance(session_id, str) else None,
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
    Returns current persisted identity and password-reset state.
    Use as: current_user: dict = Depends(get_current_user)
    """

    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    user = get_user(payload["username"])

    if user is None or not user.get("is_active", True):
        raise HTTPException(
            status_code=401,
            detail="Account is unavailable.",
        )

    if payload.get("token_version", 0) != user.get("token_version", 0):
        raise HTTPException(
            status_code=401,
            detail="This session was signed out by a password change.",
        )

    session_id = payload.get("session_id")

    if session_id and not is_session_active(session_id, user["username"]):
        raise HTTPException(
            status_code=401,
            detail="This session was signed out. Please log in again.",
        )

    return {
        "username": user["username"],
        "role": user["role"],
        "must_reset_password": user.get(
            "must_reset_password",
            False,
        ),
    }


def require_password_reset_complete(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Block application access until a temporary password is changed."""

    if current_user["must_reset_password"]:
        raise HTTPException(
            status_code=403,
            detail="Password reset required.",
        )

    return current_user


def require_admin(
    current_user: dict = Depends(require_password_reset_complete),
) -> dict:
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
