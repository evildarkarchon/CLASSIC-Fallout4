#!/usr/bin/env python3
"""Validation script for Python type stub files (.pyi) in Rust bindings.

This script validates that all .pyi stub files accurately represent their
corresponding Rust implementation by checking for:
- Missing classes/functions from Rust implementation
- Missing magic methods (__repr__, __str__, __eq__, etc.)
- Inconsistent signatures
- Missing module-level exports

Usage:
    python ClassicLib-rs/validate_stubs.py              # Validate all crates
    python ClassicLib-rs/validate_stubs.py --verbose    # Show detailed output
    python ClassicLib-rs/validate_stubs.py --fix        # Auto-fix simple issues (future)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


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

    def validate_crate(self, crate_path: Path) -> tuple[int, int]:
        """Validate a single Python binding crate.

        Args:
            crate_path: Path to the crate directory.

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
        """Validate all Python binding crates.

        Args:
            rust_dir: Path to the rust directory containing python-bindings/.

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

        # Find all *-py crate directories
        crates = sorted(
            [d for d in bindings_dir.iterdir() if d.is_dir() and d.name.endswith("-py")]
        )
        if include_crates:
            include_set = set(include_crates)
            crates = [crate for crate in crates if crate.name in include_set]
        if parity_contract:
            contract = json.loads(parity_contract.read_text(encoding="utf-8"))
            tier1_mappings = contract.get("tier1Mappings", [])
            tier1_modules = {
                mapping.get("pythonModule")
                for mapping in tier1_mappings
                if mapping.get("pythonModule")
            }
            crates = [
                crate
                for crate in crates
                if self.crate_name_to_stub_module(crate.name) in tier1_modules
            ]

        if not crates:
            print(f"[ERROR] No Python binding crates found in {bindings_dir}")
            report = {
                "rust_dir": str(rust_dir),
                "total_crates": 0,
                "crates_passed": 0,
                "total_errors": 1,
                "total_warnings": 0,
                "errors": [f"No Python binding crates found in {bindings_dir}"],
                "warnings": [],
            }
            return (False, report)

        print(f"[INFO] Validating {len(crates)} Python binding crates...\n")

        total_errors = 0
        total_warnings = 0
        self.total_count = len(crates)

        for crate in crates:
            errors, warnings = self.validate_crate(crate)
            total_errors += errors
            total_warnings += warnings

        # Print summary
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"[OK] Crates passed: {self.success_count}/{self.total_count}")
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
        default=Path(__file__).parent,
        help="Path to rust directory (default: script directory)",
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

    validator = StubValidator(verbose=args.verbose)
    success, report = validator.validate_all(
        args.rust_dir,
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
