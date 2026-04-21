---
phase: 09-clean-validation-and-ci-refresh
plan: "03"
requirements-completed: [INTG-03]
---

# 09-03 Summary

- Refreshed `ci-python-bindings.yml` to use repo-root `validate_stubs.py`, `python-bindings/.venv`, `target`, and `python-bindings/parity-artifacts/` paths.
- Refreshed `ci-typescript.yml` to use repo-root `target`, `node-bindings/classic-node`, and `node-bindings/classic-node/parity-artifacts/` paths.
- Extended the Phase 9 validation audit to assert the live Python and Node workflow contract plus scoped artifact ownership.
