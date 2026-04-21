---
phase: 08-wrapper-and-parity-rewire
plan: "03"
requirements-completed: [INTG-02]
---

# 08-03 Summary

- Cut Python stub/parity tooling defaults to repo-root `python-bindings/` and `foundation/` paths.
- Changed `validate_stubs.py` to fail fast on legacy `ClassicLib-rs` inputs with migration guidance.
- Added regression tests for repo-root inventories and legacy-path rejection.
