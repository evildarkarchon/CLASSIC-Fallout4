# XSE conformance fixtures

Each scenario writes zero-byte files into its own temporary root. Missing loader, loader without version DLL, and exactly one valid version DLL avoid directory enumeration ambiguity. No installed game, registry, executable resource parsing, or user settings are required. Detection absence maps to null because Node and CXX expose an absence sentinel rather than distinct errors; no error-category coverage is claimed. Exact byte inventory verifies observation did not add, remove, or modify fixture files.

The optional `kind` selects F4SE, F4SEVR, SKSE, SKSE64, SKSEVR, or SFSE; omitted `kind` preserves the original F4SE fixtures. Every variant has missing, loader-only, and detected scenarios with a variant-owned loader and `1_10_163.dll` filename. The synthetic DLL filename tests parsing and is not a claim about released game versions. Each Python constructor earns evidence only from its own variant observations.
