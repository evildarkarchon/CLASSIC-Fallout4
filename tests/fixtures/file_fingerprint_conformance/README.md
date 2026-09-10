# File fingerprint inputs

These files contain only byte inputs (or null for an absent file). Independent
SHA-256 expectations are in the pack; `abc` and empty input use standard known
vectors, and the Windows-1252 bytes were hashed independently with Python's
standard hashlib. Adapters never receive those expectations. Temporary-file
inventories prove hashing and encoding do not mutate or create files.
