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

# NIST/OWASP-acceptable minimum for PBKDF2-HMAC-SHA256 as of 2023+ guidance.
PBKDF2_ITERATIONS = 200_000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _get_jwt_secret() -> str:

    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set in .env. Auth cannot issue or "
            "verify tokens without it — generate one and add it to .env "
            "before using any /auth endpoint."
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
    """
    PBKDF2-HMAC-SHA256, not bcrypt/argon2 — deliberate choice. This project
    already hit one native-extension DLL mismatch on Windows (see
    PROJECT_MASTER_CONTEXT Section 3, the torch/VC++ Redistributable
    issue). PBKDF2 via hashlib is pure standard library — zero new
    compiled dependencies, zero risk of repeating that class of problem.
    Still an accepted, secure choice for password storage at this
    iteration count.
    """

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

    # constant-time comparison — a plain == here would leak timing info
    return hmac.compare_digest(candidate_hash, stored_hash)


def create_user(username: str, temp_password: str):
    """
    Creates a user with must_reset_password=True.

    Deliberately NOT exposed as an HTTP endpoint. This is a single-owner
    local tool, not a multi-tenant app with public registration — there's
    no legitimate case for a "create user" API surface here, and building
    one just to secure it afterward would be over-investing exactly where
    the roadmap says not to. Called only from backend/seed_admin.py.
    """

    users = _load_users()

    if any(u["username"] == username for u in users):
        raise ValueError(f"User '{username}' already exists.")

    password_hash, salt = _hash_password(temp_password)

    users.append({
        "username": username,
        "password_hash": password_hash,
        "salt": salt,
        "must_reset_password": True,
        "created_at": datetime.now().isoformat(),
        "last_login": None
    })

    _save_users(users)


def authenticate(username: str, password: str):
    """Returns the user record dict on success, None on failure."""

    users = _load_users()

    user = next((u for u in users if u["username"] == username), None)

    if user is None:
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


def create_access_token(username: str) -> str:

    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)

    payload = {
        "sub": username,
        "exp": expire
    }

    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str):
    """Returns the username from a valid token, or None if invalid/expired."""

    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        return payload.get("sub")

    except jwt.ExpiredSignatureError:
        log_info("Auth token expired.")
        return None

    except jwt.InvalidTokenError as e:
        log_error(f"Invalid auth token: {e}")
        return None


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Reusable dependency for gating routes: add `Depends(get_current_user)`
    to any route's signature and it returns the authenticated username, or
    raises 401 automatically.

    Built now as infrastructure. Deliberately NOT applied to the existing
    upload/process/ask/etc. routes in this pass — wiring auth into 11
    existing route files is a separate, higher-risk change, and bundling
    it with login/reset raises the odds of breaking something that
    currently works. It's a one-line addition per route whenever you want
    it done as its own dedicated pass.
    """

    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    username = decode_access_token(token)

    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return username