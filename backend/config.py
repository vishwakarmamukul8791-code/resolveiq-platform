TOP_K = 5

CHUNK_SIZE = 500

CHUNK_OVERLAP = 100

# NOTE: embedding model/dimension are NOT configured here. They come
# from environment variables (EMBEDDING_PROVIDER, EMBEDDING_MODEL,
# EMBEDDING_DIMENSION) read directly in backend/services/embedding_service.py.
# This file used to also define EMBEDDING_MODEL / EMBEDDING_DIMENSION
# constants, but nothing ever imported them — the real values always
# came from embedding_service.py's env-var reads. Changing those two
# constants here silently did nothing, which was confusing enough to
# flag as a bug in its own right. Removed rather than left as dead,
# misleading config; see embedding_service.py for the actual settings.
