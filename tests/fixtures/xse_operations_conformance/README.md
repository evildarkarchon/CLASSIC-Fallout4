# XSE conformance fixtures

Each scenario writes zero-byte files into its own temporary root. Missing loader, loader without version DLL, and exactly one valid version DLL avoid directory enumeration ambiguity. No installed game, registry, executable resource parsing, or user settings are required. Detection absence maps to null because Node and CXX expose an absence sentinel rather than distinct errors; no error-category coverage is claimed. Exact byte inventory verifies observation did not add, remove, or modify fixture files.
