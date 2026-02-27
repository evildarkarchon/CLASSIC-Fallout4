# Logging Redaction Policy (Phase 1)

This policy defines redaction behavior for parity-scoped startup and dependency diagnostics.

## Goals

- Prevent secret leakage in diagnostics.
- Reduce local machine fingerprinting from file path context.
- Keep emitted events useful for triage.

## Rule Set

### 1) Secret-Like Keys

If a context field key contains any of the following tokens (case-insensitive), the value is replaced with `[REDACTED]`:

- `password`
- `passwd`
- `secret`
- `token`
- `api_key`
- `apikey`
- `authorization`
- `cookie`
- `session`
- `credential`
- `private_key`

### 2) Path-Like Keys

If a context field key appears path-oriented (`path`, `file`, `filename`, `filepath`, `directory`, `dir`, `location`), the value is masked as `<path-redacted>`.

### 3) In-Value Secret Markers

If a value contains explicit secret markers (`token=`, `password=`, `secret=`, `api_key=`, `apikey=`), the value is replaced with `[REDACTED]` even when the key is not secret-like.

### 4) Empty and Non-sensitive Values

Values not matching redaction rules pass through unchanged.

## Examples

- `api_key=abc123` -> `[REDACTED]`
- `db_password=supersecret` -> `[REDACTED]`
- `game_path=C:\Users\Alice\Documents\My Games\Fallout4` -> `<path-redacted>`
- `contract=startup_all` -> `startup_all`

## Enforcement

- Rust contract helper redacts all context fields before formatting.
- Python/Rust parity tests verify secret and path masking behavior.
- CI phase-1 checks run contract + redaction tests to prevent regression.
