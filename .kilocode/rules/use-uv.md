# use-uv.md

Use uv to run python commands so that they all go through its virtual environment.

## Description

This rule ensures that all Python commands are executed through `uv`, which provides a consistent and isolated virtual environment for Python projects. This helps prevent dependency conflicts and ensures that the project's dependencies are managed correctly.

## Examples

### Bad

```bash
python -m pip install -r requirements.txt
```

### Good

```bash
uv pip install -r requirements.txt
```

```bash
uv run pytest
```

## Rationale

Using `uv` to manage Python environments ensures that all dependencies are installed in a consistent and isolated manner. This helps prevent conflicts between different projects and ensures that the project's dependencies are managed correctly.

## Further Reading

- [uv Documentation](https://github.com/astral-sh/uv)