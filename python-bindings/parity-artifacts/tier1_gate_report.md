# Tier-1 Python Parity Gate Report

- Tier-1 contract rows: **1221**
- Tier-1 matched: **1220**
- Tier-1 missing Rust: **0**
- Tier-1 missing Python: **0**
- Tier-1 signature mismatch: **0**

## Result

Tier-1 drift detected. Review failing contract rows below.

| ID | Owner Module | Rust Symbol | Python Export | Status | Reason |
|---|---|---|---|---|---|
| `settings.lib.SettingsCacheStats` | `settings` | `None` | `classic_settings.SettingsCacheStats` | `unmapped` | No verified core Rust counterpart. Previous value 'validators' named a Rust module, which verifies nothing about this Python export. |
