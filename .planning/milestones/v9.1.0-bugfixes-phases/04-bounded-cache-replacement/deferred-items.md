# Deferred Items

- `python tools/python_api_parity/check_parity_gate.py --repo-root .` still reports one newly uncovered surface, `binding:rust:FcxResetError`, caused by unrelated in-flight scanlog workspace changes outside Plan 04-05. Left untouched per execution scope rules.
