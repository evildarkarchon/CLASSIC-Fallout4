# CLASSIC Python CLI Report

Profile: `python-ci`

## Scenarios
- `bindings-list`: passed (exit 0) - 17/17 bindings importable
- `version-parse`: passed (exit 0) - 1.10.163.0 -> v1.10.163
- `config-main-version`: passed (exit 0) - CLASSIC main YAML version: v9.1.0
- `path-validate-fixture`: passed (exit 0) - Path is valid: D:\repos\CLASSIC-Fallout4\python-bindings\tests\fixtures
- `file-hash`: passed (exit 0) - Cargo.toml dd57655e445fb52d36020d918a593be0f0a58ce2c9f7ba27c6adca5f2abd9596
- `scanlog-addictol-newer-than-floor`: passed (exit 0) - completed - 1 log scanned

## Delegated Gates
- `D:\repos\CLASSIC-Fallout4\python-bindings\.venv\Scripts\python.exe tools/python_api_parity/check_parity_gate.py --repo-root .`: exit 0
- `D:\repos\CLASSIC-Fallout4\python-bindings\.venv\Scripts\python.exe tools/binding_compliance/check_compliance.py --repo-root . --profile python-ci`: exit 0
