#!/usr/bin/env python3
"""Validation script for Python type stub files (.pyi) in Rust bindings.

This script validates that all .pyi stub files accurately represent their
corresponding Rust implementation by checking for:
- Missing classes/functions from Rust implementation
- Missing class methods from legacy direct PyO3 crates
- Missing or extra maintained names against the checked-in Python API surface
- Missing or extra exports in a checked-in direct-import facade's literal __all__

Usage:
    python validate_stubs.py                            # Validate all crates from repo root
    python validate_stubs.py --rust-dir .               # Explicit repo-root input
    python validate_stubs.py --rust-dir ClassicLib-rs   # Unsupported legacy input; use --rust-dir .
    python validate_stubs.py --verbose                  # Show detailed output
    python validate_stubs.py --fix                      # Auto-fix simple issues (future)
"""

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
LEGACY_WORKSPACE_DIR = SCRIPT_DIR / "ClassicLib-rs"


def normalize_rust_dir(rust_dir: Path) -> Path:
    """Resolve the repo root, rejecting legacy ClassicLib-rs inputs."""

    resolved = rust_dir.resolve()
    if resolved == LEGACY_WORKSPACE_DIR or resolved.name == "ClassicLib-rs":
        raise FileNotFoundError(
            "Legacy rust-dir 'ClassicLib-rs' is no longer supported. "
            "Use the repository root as --rust-dir (for example, '--rust-dir .') "
            "so the validator reads '<repo>/python-bindings'."
        )

    if (resolved / "python-bindings").exists():
        return resolved

    raise FileNotFoundError(
        "python-bindings directory not found at "
        f"'{resolved / 'python-bindings'}'. Use the repository root as --rust-dir."
    )


class StubValidator:
    """Validates Python stub files against Rust implementations."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize the validator.

        Args:
            verbose: Whether to print detailed validation output.

        """
        self.verbose = verbose
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.success_count = 0
        self.total_count = 0

    @staticmethod
    def crate_name_to_stub_module(crate_name: str) -> str:
        """Convert crate directory name to Python module stub basename."""
        if crate_name.endswith("-py"):
            return crate_name[:-3].replace("-", "_")
        return crate_name.replace("-", "_")

    @staticmethod
    def public_stub_names(stub_content: str) -> set[str]:
        """Return maintained top-level class, callable, and constant names."""
        module = ast.parse(stub_content)
        names: set[str] = set()
        for node in module.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(node.name)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            elif isinstance(node, ast.Assign):
                names.update(
                    target.id for target in node.targets if isinstance(target, ast.Name)
                )
        return names

    @staticmethod
    def public_stub_export_paths(stub_content: str) -> set[str]:
        """Return top-level names plus class methods and property getters.

        Setter and deleter declarations reuse their getter's public path and
        do not create a second maintained name.
        """
        module = ast.parse(stub_content)
        names = StubValidator.public_stub_names(stub_content)
        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for member in node.body:
                if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if any(
                    isinstance(decorator, ast.Attribute)
                    and decorator.attr in {"setter", "deleter"}
                    for decorator in member.decorator_list
                ):
                    continue
                names.add(f"{node.name}.{member.name}")
        return names

    @staticmethod
    def typing_only_stub_names(stub_content: str) -> set[str]:
        """Find classes that describe Python typing records, not runtime exports."""
        module = ast.parse(stub_content)
        names: set[str] = set()
        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for base in node.bases:
                base_name = base.id if isinstance(base, ast.Name) else (
                    base.attr if isinstance(base, ast.Attribute) else None
                )
                if base_name in {"TypedDict", "Protocol"}:
                    names.add(node.name)
                    break
        return names

    @staticmethod
    def check_stub_name_inventory(
        module_name: str, stub_content: str, expected_names: set[str]
    ) -> list[str]:
        """Report missing and extra maintained export paths against the surface."""
        actual_names = StubValidator.public_stub_export_paths(stub_content)
        missing = expected_names - actual_names
        extra = actual_names - expected_names
        errors: list[str] = []
        if missing:
            errors.append(
                f"[ERROR] {module_name}: Missing maintained stub names: {sorted(missing)}"
            )
        if extra:
            errors.append(
                f"[ERROR] {module_name}: Extra maintained stub names: {sorted(extra)}"
            )
        return errors

    @staticmethod
    def check_facade_export_inventory(
        module_name: str, facade_content: str, expected_names: set[str]
    ) -> list[str]:
        """Compare literal ``__all__`` to expected names and their bindings.

        Returns diagnostics for missing, extra, wildcard, duplicate, or unbound
        public facade names; an empty list means the source names agree.
        """
        module = ast.parse(facade_content)
        declarations = [
            node.value
            for node in module.body
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            and (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "__all__"
                or isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "__all__"
                    for target in node.targets
                )
            )
        ]
        if len(declarations) != 1:
            return [
                f"[ERROR] {module_name}: Source facade must declare one literal __all__."
            ]
        literal_names = declarations[0]
        try:
            names = ast.literal_eval(literal_names) if literal_names is not None else None
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            names = None
        if not isinstance(names, (list, tuple)) or not all(
            isinstance(name, str) for name in names
        ):
            return [
                f"[ERROR] {module_name}: Source facade __all__ must be a literal list of names."
            ]

        errors: list[str] = []
        if len(names) != len(set(names)):
            errors.append(f"[ERROR] {module_name}: Source facade __all__ has duplicate names.")
        # PyO3 may include internal module metadata in __all__; it is not part
        # of the contributor-facing public name inventory.
        actual_names = set(names) - {"__doc__", "__debug_registered__"}
        missing = expected_names - actual_names
        extra = actual_names - expected_names
        if missing:
            errors.append(
                f"[ERROR] {module_name}: Missing source facade exports: {sorted(missing)}"
            )
        if extra:
            errors.append(
                f"[ERROR] {module_name}: Extra source facade exports: {sorted(extra)}"
            )
        bound_names: set[str] = set()
        for node in module.body:
            if isinstance(node, ast.ImportFrom):
                if any(alias.name == "*" for alias in node.names):
                    errors.append(
                        f"[ERROR] {module_name}: Wildcard facade import cannot prove public names."
                    )
                bound_names.update(
                    alias.asname or alias.name for alias in node.names if alias.name != "*"
                )
            elif isinstance(node, ast.Import):
                bound_names.update(
                    alias.asname or alias.name.split(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.Assign):
                bound_names.update(
                    target.id for target in node.targets if isinstance(target, ast.Name)
                )
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.value is not None
            ):
                bound_names.add(node.target.id)
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                bound_names.add(node.name)
        unbound = actual_names - bound_names
        if unbound:
            errors.append(
                f"[ERROR] {module_name}: Unbound source facade exports: {sorted(unbound)}"
            )
        return errors

    @staticmethod
    def find_source_facades(repo_root: Path, module_names: set[str]) -> dict[str, list[Path]]:
        """Locate checked-in Python facade files while skipping built wheel contents."""
        facades: dict[str, list[Path]] = {name: [] for name in module_names}
        for layer in ("python-bindings", "foundation"):
            layer_root = repo_root / layer
            if not layer_root.is_dir():
                continue
            for current, directories, files in os.walk(layer_root):
                directories[:] = [
                    name
                    for name in directories
                    if name not in {".venv", "target", "tests", "__pycache__"}
                ]
                current_path = Path(current)
                if current_path.name in module_names and "__init__.py" in files:
                    facades[current_path.name].append(current_path / "__init__.py")
                for name in files:
                    if name.endswith(".py") and name[:-3] in module_names:
                        facades[name[:-3]].append(current_path / name)
        return facades

    @staticmethod
    def extract_rust_classes(rust_content: str) -> set[str]:
        """Extract class names from Rust PyClass declarations.

        Args:
            rust_content: Content of the Rust lib.rs file.

        Returns:
            Set of Python class names exported from Rust.

        """
        classes: set[Any] = set()
        # Match #[pyclass(..., name = "ClassName")]
        classes.update(
            match.group(1)
            for match in re.finditer(
                r'#\[pyclass\([^)]*name\s*=\s*"([^"]+)"', rust_content
            )
        )

        # Match struct names when no explicit name is given
        classes.update(
            match.group(1)
            for match in re.finditer(
                r"#\[pyclass[^\]]*\]\s+(?:pub\s+)?struct\s+Py(\w+)", rust_content
            )
        )

        return classes

    @staticmethod
    def extract_rust_functions(rust_content: str) -> set[str]:
        """Extract function names from Rust PyFunction declarations.

        Args:
            rust_content: Content of the Rust lib.rs file.

        Returns:
            Set of Python function names exported from Rust.

        """
        functions: set[Any] = set()
        # Match #[pyfunction] followed by fn name
        functions.update(
            match.group(1)
            for match in re.finditer(
                r"#\[pyfunction\].*?fn\s+(\w+)", rust_content, re.DOTALL
            )
        )

        return functions

    @staticmethod
    def extract_rust_methods(rust_content: str, class_name: str) -> set[str]:
        """Extract method names for a specific Rust class.

        Args:
            rust_content: Content of the Rust lib.rs file.
            class_name: Name of the class to extract methods for.

        Returns:
            Set of method names for the class.

        """
        methods: set[Any] = set()

        # Find the impl block for this class (look for PyClassName)
        py_class_name = f"Py{class_name}"
        impl_pattern = rf"impl\s+{py_class_name}\s*\{{(.*?)\n\}}"
        impl_match = re.search(impl_pattern, rust_content, re.DOTALL)

        if impl_match:
            impl_body = impl_match.group(1)
            # Find callable methods while excluding property/classattr accessors.
            for match in re.finditer(
                r"(?P<attrs>(?:\s*#\[[^\]]+\]\s*)*)(?:pub\s+)?fn\s+(\w+)",
                impl_body,
                re.DOTALL,
            ):
                attrs = match.group("attrs") or ""
                method_name = match.group(2)
                if any(
                    marker in attrs
                    for marker in ("#[getter", "#[setter", "#[classattr")
                ):
                    continue
                if method_name == "new":
                    continue
                if method_name.startswith("py_"):
                    method_name = method_name.removeprefix("py_")
                # Include magic methods
                if method_name.startswith("__") or not method_name.startswith("_"):
                    methods.add(method_name)

        return methods

    @staticmethod
    def extract_stub_classes(stub_content: str) -> set[str]:
        """Extract class names from stub file.

        Args:
            stub_content: Content of the .pyi stub file.

        Returns:
            Set of class names defined in the stub.

        """
        classes: set[Any] = set()
        classes.update(
            match.group(1)
            for match in re.finditer(r"^class\s+(\w+)[:\(]", stub_content, re.MULTILINE)
        )
        return classes

    @staticmethod
    def extract_stub_functions(stub_content: str) -> set[str]:
        """Extract top-level function names from stub file.

        Args:
            stub_content: Content of the .pyi stub file.

        Returns:
            Set of function names defined in the stub.

        """
        functions: set[Any] = set()
        # Match both regular functions and async functions at module level
        functions.update(
            match.group(1)
            for match in re.finditer(
                r"^(?:async\s+)?def\s+(\w+)\s*\(", stub_content, re.MULTILINE
            )
        )
        return functions

    @staticmethod
    def extract_stub_methods(stub_content: str, class_name: str) -> set[str]:
        """Extract method names for a specific class from stub file.

        Args:
            stub_content: Content of the .pyi stub file.
            class_name: Name of the class to extract methods for.

        Returns:
            Set of method names for the class.

        """
        methods: set[Any] = set()

        # Find the class definition
        class_pattern = rf"class\s+{class_name}[:\(].*?(?=^class\s|\Z)"
        class_match = re.search(class_pattern, stub_content, re.DOTALL | re.MULTILINE)

        if class_match:
            class_body = class_match.group(0)
            # Find all method definitions (indented)
            methods.update(
                match.group(1)
                for match in re.finditer(
                    r"^\s{4}def\s+(\w+)\s*\(", class_body, re.MULTILINE
                )
            )

        return methods

    def validate_public_surface(
        self,
        module_name: str,
        stub_content: str,
        expected_names: set[str],
        facade_source: Path | None,
    ) -> int:
        """Check maintained stub paths and an optional source facade ``__all__``.

        ``expected_names`` includes dotted class methods and properties;
        ``facade_source`` may be absent for a direct native module. Returns the
        number of errors appended to this validator.
        """
        name_errors = self.check_stub_name_inventory(
            module_name, stub_content, expected_names
        )
        self.errors.extend(name_errors)
        errors = len(name_errors)

        if facade_source is not None:
            # TypedDicts and protocols are maintained typing contracts,
            # but no native class is exported for them at runtime.
            public_facade_names = {
                name for name in expected_names if "." not in name
            } - self.typing_only_stub_names(stub_content) - {"__debug_registered__"}
            facade_errors = self.check_facade_export_inventory(
                module_name,
                facade_source.read_text(encoding="utf-8"),
                public_facade_names,
            )
            self.errors.extend(facade_errors)
            errors += len(facade_errors)
        return errors

    def validate_crate(
        self,
        crate_path: Path,
        expected_names: set[str] | None = None,
        facade_source: Path | None = None,
    ) -> tuple[int, int]:
        """Validate a single Python binding crate.

        Args:
            crate_path: Path to the crate directory.
            expected_names: Checked-in public stub paths, including class members.
            facade_source: Optional checked-in facade exposing these names.

        Returns:
            Tuple of (error_count, warning_count).

        """
        crate_name = crate_path.name
        lib_rs = crate_path / "src" / "lib.rs"
        # Convert crate name to stub filename: classic-pybridge-py -> classic_pybridge.pyi
        # Remove the -py suffix (must be at the end), then replace remaining hyphens
        stub_name = self.crate_name_to_stub_module(crate_name)
        stub_file = crate_path / f"{stub_name}.pyi"

        if not lib_rs.exists():
            self.errors.append(f"[ERROR] {crate_name}: lib.rs not found at {lib_rs}")
            return (1, 0)

        if not stub_file.exists():
            self.errors.append(
                f"[ERROR] {crate_name}: Stub file not found at {stub_file}"
            )
            return (1, 0)

        rust_content = lib_rs.read_text(encoding="utf-8")
        stub_content = stub_file.read_text(encoding="utf-8")

        errors = 0
        warnings = 0

        if expected_names is not None:
            errors += self.validate_public_surface(
                stub_name, stub_content, expected_names, facade_source
            )

        # Validate classes
        rust_classes = self.extract_rust_classes(rust_content)
        stub_classes = self.extract_stub_classes(stub_content)

        missing_classes = rust_classes - stub_classes
        if missing_classes:
            self.errors.append(
                f"[ERROR] {crate_name}: Missing classes in stub: {missing_classes}"
            )
            errors += len(missing_classes)

        # Validate functions
        rust_functions = self.extract_rust_functions(rust_content)
        stub_functions = self.extract_stub_functions(stub_content)

        missing_functions = rust_functions - stub_functions
        if missing_functions:
            self.errors.append(
                f"[ERROR] {crate_name}: Missing functions in stub: {missing_functions}"
            )
            errors += len(missing_functions)

        # Validate methods for each class
        for class_name in rust_classes & stub_classes:
            rust_methods = self.extract_rust_methods(rust_content, class_name)
            stub_methods = self.extract_stub_methods(stub_content, class_name)

            missing_methods = rust_methods - stub_methods
            if missing_methods:
                self.warnings.append(
                    f"[WARN] {crate_name}: Class '{class_name}' missing methods: {missing_methods}"
                )
                warnings += len(missing_methods)

        # If no issues, mark as success
        if errors == 0 and warnings == 0:
            self.success_count += 1
            if self.verbose:
                print(f"[OK] {crate_name}: All checks passed")

        return (errors, warnings)

    def build_report(
        self, total_errors: int, total_warnings: int, rust_dir: Path
    ) -> dict[str, Any]:
        """Build a structured validation report payload."""
        return {
            "rust_dir": str(rust_dir),
            "total_crates": self.total_count,
            "crates_passed": self.success_count,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def validate_all(
        self,
        rust_dir: Path,
        fail_on_warnings: bool = False,
        include_crates: list[str] | None = None,
        parity_contract: Path | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Validate all maintained Python stub modules and direct binding crates.

        Args:
            rust_dir: Path to the rust directory containing python-bindings/.
            fail_on_warnings: Treat the legacy Rust method warnings as errors.
            include_crates: Limit validation to stub paths beneath these crate names.
            parity_contract: Limit validation to modules in its Tier-1 mappings.

        Returns:
            Tuple of (success, structured_report).

        """
        bindings_dir = rust_dir / "python-bindings"

        if not bindings_dir.exists():
            print(f"[ERROR] python-bindings directory not found at {bindings_dir}")
            report = {
                "rust_dir": str(rust_dir),
                "total_crates": 0,
                "crates_passed": 0,
                "total_errors": 1,
                "total_warnings": 0,
                "errors": [f"python-bindings directory not found at {bindings_dir}"],
                "warnings": [],
            }
            return (False, report)

        surface_path = (
            rust_dir
            / "docs"
            / "implementation"
            / "python_api_parity"
            / "baseline"
            / "python_api_surface.json"
        )
        if not surface_path.is_file():
            error = f"[ERROR] Checked-in Python API surface not found at {surface_path}"
            self.errors.append(error)
            return (False, self.build_report(1, 0, rust_dir))
        surface = json.loads(surface_path.read_text(encoding="utf-8"))
        expected_by_module: dict[str, set[str]] = {}
        for entry in surface["exports"]:
            export_path = entry.get("export_path", entry["export"])
            expected_by_module.setdefault(entry["module"], set()).add(export_path)

        scope = surface["scope"]
        modules = scope["target_modules"]
        source_files = scope["source_files"]
        if len(modules) != len(source_files) or len(modules) != len(set(modules)):
            self.errors.append(
                "[ERROR] Checked-in Python API surface has invalid module/source paths."
            )
            return (False, self.build_report(1, 0, rust_dir))
        targets = list(zip(modules, source_files, strict=True))
        if include_crates:
            include_set = set(include_crates)
            targets = [
                (module, source)
                for module, source in targets
                if include_set.intersection(Path(source).parts)
            ]
        if parity_contract:
            contract = json.loads(parity_contract.read_text(encoding="utf-8"))
            tier1_mappings = contract.get("tier1Mappings", [])
            tier1_modules = {
                mapping.get("pythonModule")
                for mapping in tier1_mappings
                if mapping.get("pythonModule")
            }
            targets = [
                (module, source)
                for module, source in targets
                if module in tier1_modules
            ]

        if not targets:
            print("[ERROR] No maintained Python stub modules selected")
            report = {
                "rust_dir": str(rust_dir),
                "total_crates": 0,
                "crates_passed": 0,
                "total_errors": 1,
                "total_warnings": 0,
                "errors": ["No maintained Python stub modules selected"],
                "warnings": [],
            }
            return (False, report)

        print(f"[INFO] Validating {len(targets)} Python stub modules...\n")

        total_errors = 0
        total_warnings = 0
        self.total_count = len(targets)

        facades = self.find_source_facades(
            rust_dir, {module for module, _source in targets}
        )

        for module_name, source in targets:
            expected_names = expected_by_module.get(module_name)
            if expected_names is None:
                self.errors.append(
                    f"[ERROR] {module_name}: No checked-in Python API surface inventory."
                )
                total_errors += 1
                continue
            stub_path = rust_dir / source
            if not stub_path.is_file():
                self.errors.append(
                    f"[ERROR] {module_name}: Maintained stub not found at {stub_path}"
                )
                total_errors += 1
                continue
            source_paths = facades[module_name]
            if len(source_paths) > 1:
                self.errors.append(
                    f"[ERROR] {module_name}: Multiple source facades: {source_paths}"
                )
                total_errors += 1
                continue
            facade_source = source_paths[0] if source_paths else None
            crate = stub_path.parent
            if self.crate_name_to_stub_module(crate.name) == module_name:
                errors, warnings = self.validate_crate(
                    crate,
                    expected_names=expected_names,
                    facade_source=facade_source,
                )
            else:
                # Once one adapter owns several stubs, its module-level PyO3
                # source is checked by parity resolution, while this gate
                # checks each direct-import facade's exact public names.
                if facade_source is None:
                    self.errors.append(
                        f"[ERROR] {module_name}: No checked-in source facade found."
                    )
                    total_errors += 1
                    continue
                errors = self.validate_public_surface(
                    module_name,
                    stub_path.read_text(encoding="utf-8"),
                    expected_names,
                    facade_source,
                )
                warnings = 0
                if errors == 0:
                    self.success_count += 1
            total_errors += errors
            total_warnings += warnings

        # Print summary
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"[OK] Stub modules passed: {self.success_count}/{self.total_count}")
        print(f"[ERROR] Total errors: {total_errors}")
        print(f"[WARN] Total warnings: {total_warnings}")

        # Print all errors
        if self.errors:
            print("\n[ERROR] ERRORS:")
            for error in self.errors:
                print(f"  {error}")

        # Print all warnings
        if self.warnings:
            print("\n[WARN] WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")

        print("=" * 70)

        report = self.build_report(total_errors, total_warnings, rust_dir)
        success = total_errors == 0 and (not fail_on_warnings or total_warnings == 0)
        if fail_on_warnings and total_warnings > 0 and total_errors == 0:
            print("\n[ERROR] Failing due to --fail-on-warnings.")
        return (success, report)


def main() -> None:
    """Serve as main entry point for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate Python type stub files against Rust implementations"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed validation output"
    )
    parser.add_argument(
        "--rust-dir",
        type=Path,
        default=SCRIPT_DIR,
        help=(
            "Workspace root to validate. Defaults to the repo root. Legacy "
            "ClassicLib-rs inputs are rejected; use the repository root instead."
        ),
    )
    parser.add_argument(
        "--json-out", type=Path, help="Optional path to write JSON validation report"
    )
    parser.add_argument(
        "--fail-on-warnings", action="store_true", help="Treat warnings as failures"
    )
    parser.add_argument(
        "--include-crates",
        nargs="+",
        help="Optional explicit list of binding crate directory names to validate (e.g., classic-config-py)",
    )
    parser.add_argument(
        "--parity-contract",
        type=Path,
        help="Optional parity contract JSON; validates crates discovered from tier1Mappings.pythonModule",
    )

    args = parser.parse_args()

    try:
        normalized_rust_dir = normalize_rust_dir(args.rust_dir)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)

    validator = StubValidator(verbose=args.verbose)
    success, report = validator.validate_all(
        normalized_rust_dir,
        fail_on_warnings=args.fail_on_warnings,
        include_crates=args.include_crates,
        parity_contract=args.parity_contract,
    )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"JSON report written: {args.json_out}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
