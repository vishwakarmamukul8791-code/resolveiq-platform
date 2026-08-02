from functools import wraps
from threading import RLock


_document_storage_lock = RLock()


def synchronized_document_storage(function):
    """Serialize index/metadata/registry mutations within one API process."""

    @wraps(function)
    def wrapped(*args, **kwargs):
        with _document_storage_lock:
            return function(*args, **kwargs)

    return wrapped
