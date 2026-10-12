# Cached document fixtures

The Rust participant loads these authored YAML bytes into a disposable file,
retrieves the public cached document payload, replaces the file, retrieves
again, and invalidates the key. Observations distinguish an absent entry from a cached
empty document list and prove the cache does not reread modified source bytes.
Each scenario clears the process cache before and after execution. CXX has no
public cached-document accessor and is outside this pack's applicability.
