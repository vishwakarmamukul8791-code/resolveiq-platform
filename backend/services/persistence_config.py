import os


LOCAL_BACKEND = "local"
SUPABASE_BACKEND = "supabase"
VALID_PERSISTENCE_BACKENDS = {LOCAL_BACKEND, SUPABASE_BACKEND}


def get_persistence_backend() -> str:
    configured = os.getenv("PERSISTENCE_BACKEND", "").strip()

    if not configured:
        environment = os.getenv(
            "ENVIRONMENT",
            "development",
        ).strip().lower()

        if environment == "production":
            raise RuntimeError(
                "PERSISTENCE_BACKEND must be explicitly configured in "
                "production; refusing temporary filesystem storage."
            )

        return LOCAL_BACKEND

    backend = configured.lower()

    if backend not in VALID_PERSISTENCE_BACKENDS:
        raise RuntimeError(
            "PERSISTENCE_BACKEND must be 'local' or 'supabase'."
        )

    return backend


def is_supabase_backend() -> bool:
    return get_persistence_backend() == SUPABASE_BACKEND


def validate_persistence_configuration() -> None:
    if not is_supabase_backend():
        return

    required = {
        "SUPABASE_DATABASE_URL": os.getenv("SUPABASE_DATABASE_URL", ""),
        "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
        "SUPABASE_SERVICE_ROLE_KEY": os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY",
            "",
        ),
    }

    missing = [name for name, value in required.items() if not value.strip()]

    if missing:
        raise RuntimeError(
            "Supabase persistence is enabled but required configuration "
            f"is missing: {', '.join(missing)}"
        )

    supabase_url = required["SUPABASE_URL"].rstrip("/")

    if not supabase_url.startswith("https://"):
        raise RuntimeError("SUPABASE_URL must be an HTTPS URL.")


def get_vector_database_name() -> str:
    if is_supabase_backend():
        return "Supabase PostgreSQL + pgvector"

    return "FAISS"
