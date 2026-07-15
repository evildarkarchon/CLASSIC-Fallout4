# CLASSIC Python CLI Report

Profile: `python-ci`

## Scenarios
- `bindings-list`: passed (exit 0) - 17/17 bindings importable
- `version-parse`: passed (exit 0) - 1.10.163.0 -> v1.10.163
- `config-main-version`: passed (exit 0) - CLASSIC main YAML version: v9.1.0
- `path-validate-fixture`: passed (exit 0) - Path is valid: D:\repos\CLASSIC-Fallout4\python-bindings\tests\fixtures
- `file-hash`: passed (exit 0) - Cargo.toml 9b1c3c3eebad280ece432e35b6a85ac78d721282b9b6175fa9f89180176bd606
- `scanlog-addictol-newer-than-floor`: passed (exit 0) - Scanlog binding completed: 1 succeeded, 0 failed

## Delegated Gates
- `D:\repos\CLASSIC-Fallout4\python-bindings\.venv\Scripts\python.exe tools/python_api_parity/check_parity_gate.py --repo-root .`: exit 0
- `D:\repos\CLASSIC-Fallout4\python-bindings\.venv\Scripts\python.exe tools/binding_compliance/check_compliance.py --repo-root . --profile python-ci`: exit 0
