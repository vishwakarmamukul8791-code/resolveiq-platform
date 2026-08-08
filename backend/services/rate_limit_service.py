"""
Minimal in-memory rate limiting for /auth/login (brute-force protection)
and /ask (LLM cost/abuse protection).

Deliberately not a new pip dependency (slowapi, etc.). This project's
persisted state already resets on every restart on Render's free tier —
see README — so an in-memory limiter that also resets on restart isn't
introducing any new inconsistency, and it keeps the dependency surface
small. If this app later moves to persistent, possibly multi-instance
hosting (e.g. the planned Supabase migration), swap this for a
shared-storage limiter (Redis, or a Postgres table) so multiple
instances agree on counts — a single process's in-memory dict only
protects that one process.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

_lock = Lock()
_buckets = defaultdict(list)  # key -> sorted list of request timestamps


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")

    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


def _enforce(key: str, limit: int, window_seconds: int):
    now = time.monotonic()

    with _lock:
        bucket = _buckets[key]
        cutoff = now - window_seconds

        while bucket and bucket[0] < cutoff:
            bucket.pop(0)

        if len(bucket) >= limit:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many requests. Please wait a moment and try "
                    "again."
                ),
                headers={"Retry-After": str(window_seconds)},
            )

        bucket.append(now)


def rate_limit_login(request: Request):
    """
    Per-IP limit on POST /auth/login. Keyed by IP rather than the
    attempted username so a single attacker can't dodge the limit by
    trying many different usernames from the same source.
    """

    _enforce(
        f"login:{_client_ip(request)}",
        limit=10,
        window_seconds=60,
    )


def rate_limit_ask(username: str):
    """
    Per-user limit on POST /ask. Each call runs retrieval plus one
    Gemini request, so this bounds both cost and how hard one account
    can hammer the pipeline.
    """

    _enforce(
        f"ask:{username}",
        limit=20,
        window_seconds=60,
    )


def rate_limit_guest_ask(request: Request):
    """
    Per-IP limit on POST /guest/ask. Much stricter than the logged-in
    /ask limit, and keyed by IP rather than any account, since this
    endpoint has no login at all — anyone on the internet can call it.
    A generous-enough allowance for someone genuinely trying the demo,
    tight enough to bound Gemini API cost from automated abuse.
    """

    _enforce(
        f"guest_ask:{_client_ip(request)}",
        limit=5,
        window_seconds=600,
    )
