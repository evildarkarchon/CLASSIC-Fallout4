"""Python module initialization
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_database import (
    BATCH_CACHE_TTL,
    DEFAULT_CACHE_CLEANUP_INTERVAL,
    DEFAULT_CACHE_CLEANUP_THRESHOLD,
    DEFAULT_CACHE_TTL,
    DEFAULT_QUERY_CACHE_CAPACITY,
    DatabasePool,
    FormIdValueLookup,
    FormIdValueLookupEntry,
    FormIdValueLookupError,
    FormIdValueLookupOutcome,
    MAX_CACHE_TTL,
    RustDatabaseError,
    RustDatabaseIOError,
    RustDatabaseQueryError,
    __version__,
    get_batch_cache_ttl,
    get_default_cache_cleanup_interval,
    get_default_cache_cleanup_threshold,
    get_default_cache_ttl,
    get_default_query_cache_capacity,
    get_max_cache_ttl,
)

__all__ = [
    "BATCH_CACHE_TTL",
    "DEFAULT_CACHE_CLEANUP_INTERVAL",
    "DEFAULT_CACHE_CLEANUP_THRESHOLD",
    "DEFAULT_CACHE_TTL",
    "DEFAULT_QUERY_CACHE_CAPACITY",
    "DatabasePool",
    "FormIdValueLookup",
    "FormIdValueLookupEntry",
    "FormIdValueLookupError",
    "FormIdValueLookupOutcome",
    "MAX_CACHE_TTL",
    "RustDatabaseError",
    "RustDatabaseIOError",
    "RustDatabaseQueryError",
    "__version__",
    "get_batch_cache_ttl",
    "get_default_cache_cleanup_interval",
    "get_default_cache_cleanup_threshold",
    "get_default_cache_ttl",
    "get_default_query_cache_capacity",
    "get_max_cache_ttl",
]
