"""Requirement catalog for the canonical binding compliance suite."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TextExpectation:
    """Expected substrings that must appear in a repository text file."""

    path: str
    contains: tuple[str, ...]


@dataclass(frozen=True)
class CommandSpec:
    """Subprocess command that provides executable evidence for a requirement."""

    argv: tuple[str, ...]
    cwd: str | None = None
    env: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    timeout_seconds: int | None = None


@dataclass(frozen=True)
class ComplianceRequirement:
    """A binding policy requirement and the evidence used to evaluate it."""

    id: str
    title: str
    surface: str
    classification: str
    profiles: tuple[str, ...]
    blocking: bool
    summary: str
    command: CommandSpec | None = None
    paths: tuple[str, ...] = field(default_factory=tuple)
    text_expectations: tuple[TextExpectation, ...] = field(default_factory=tuple)
    proves: tuple[str, ...] = field(default_factory=tuple)
    gaps: tuple[str, ...] = field(default_factory=tuple)


STATIC_PROFILES = ("static", "ci", "full", "cxx-ci", "node-ci", "python-ci")


REQUIREMENTS: tuple[ComplianceRequirement, ...] = (
    ComplianceRequirement(
        id="user-settings-exclusive-ownership",
        title="User Settings has one deep Rust owner",
        surface="policy",
        classification="new_check",
        profiles=STATIC_PROFILES,
        blocking=True,
        summary=(
            "Rejects legacy settings models, raw first-party key interpretation, "
            "and runtime compatibility-mirror reads outside classic-user-settings-core."
        ),
        command=CommandSpec(
            argv=(
                "python",
                "tools/user_settings_ownership/check.py",
                "--repo-root",
                ".",
            )
        ),
        paths=("tools/user_settings_ownership/check.py",),
        proves=(
            "ClassicConfig and PathConfig cannot return to maintained production code.",
            "Only classic-user-settings-core interprets first-party User Settings keys.",
            "Maintained runtimes do not bootstrap from CLASSIC_Info.default_settings.",
        ),
    ),
    ComplianceRequirement(
        id="policy-one-tier-contract",
        title="One-tier parity policy is documented",
        surface="policy",
        classification="new_check",
        profiles=STATIC_PROFILES,
        blocking=True,
        summary="The binding policy must remain one-tier with no deferred backlog.",
        paths=("docs/api/binding-parity-policy.md",),
        text_expectations=(
            TextExpectation(
                path="docs/api/binding-parity-policy.md",
                contains=(
                    "One-Tier Policy Statement",
                    "There is no deferred tier",
                    "all three bindings must expose it before CI passes",
                ),
            ),
        ),
        proves=(
            "Contributor policy has not drifted back to a tiered promotion model.",
        ),
    ),
    ComplianceRequirement(
        id="shared-rust-api-inventory-baselines",
        title="Shared Rust API inventories are checked in",
        surface="shared_rust_api_inventory",
        classification="new_check",
        profiles=STATIC_PROFILES,
        blocking=True,
        summary="The generated Rust API inventory baselines for C++, Node, and Python exist.",
        paths=(
            "docs/implementation/cxx_api_parity/baseline/rust_api_surface.json",
            "docs/implementation/node_api_parity/baseline/rust_api_surface.json",
            "docs/implementation/python_api_parity/baseline/rust_api_surface.json",
        ),
        proves=(
            "Every lower-level gate has a checked-in source-owned API inventory to compare against.",
        ),
    ),
    ComplianceRequirement(
        id="cxx-parity-gate",
        title="C++ bridge parity gate",
        surface="cxx",
        classification="existing_gate",
        profiles=("ci", "full", "cxx-ci"),
        blocking=True,
        summary="Runs the source-only CXX bridge drift gate against the committed baseline.",
        command=CommandSpec(
            argv=(
                "python",
                "tools/cxx_api_parity/check_parity_gate.py",
                "--repo-root",
                ".",
            )
        ),
        paths=(
            "tools/cxx_api_parity/check_parity_gate.py",
            "docs/implementation/cxx_api_parity/baseline/parity_contract.json",
        ),
        proves=(
            "The CXX bridge source listed by build.rs matches the committed CXX baseline.",
            "Stale committed CXX parity artifacts fail the gate.",
        ),
    ),
    ComplianceRequirement(
        id="node-parity-gate",
        title="Node parity and runtime coverage gate",
        surface="node",
        classification="existing_gate",
        profiles=("ci", "full", "node-ci"),
        blocking=True,
        summary="Runs the Node parity gate, including runtime coverage registry checks.",
        command=CommandSpec(
            argv=(
                "python",
                "tools/node_api_parity/check_parity_gate.py",
                "--repo-root",
                ".",
            )
        ),
        paths=(
            "tools/node_api_parity/check_parity_gate.py",
            "docs/implementation/node_api_parity/baseline/parity_contract.json",
            "node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json",
        ),
        proves=(
            "Node exports in index.d.ts match the committed parity contract.",
            "Node runtime coverage metadata covers every Tier-1 contract row.",
        ),
    ),
    ComplianceRequirement(
        id="python-parity-gate",
        title="Python parity and runtime coverage gate",
        surface="python",
        classification="existing_gate",
        profiles=("ci", "full", "python-ci"),
        blocking=True,
        summary="Runs the Python parity gate, including runtime coverage registry checks.",
        command=CommandSpec(
            argv=(
                "python",
                "tools/python_api_parity/check_parity_gate.py",
                "--repo-root",
                ".",
                "--output-dir",
                "tools/binding_compliance/artifacts/python_api_parity",
            )
        ),
        paths=(
            "tools/python_api_parity/check_parity_gate.py",
            "docs/implementation/python_api_parity/baseline/parity_contract.json",
            "python-bindings/tests/fixtures/runtime_coverage_registry.json",
        ),
        proves=(
            "Python exports and stubs mapped by the parity contract match the Rust inventory.",
            "Python runtime coverage metadata covers every Tier-1 contract row.",
        ),
    ),
    ComplianceRequirement(
        id="python-stub-validation",
        title="Python stub validation",
        surface="stubs_declarations",
        classification="existing_gate",
        profiles=("ci", "full", "python-ci"),
        blocking=True,
        summary="Validates maintained Python .pyi files against PyO3 wrapper source.",
        command=CommandSpec(
            argv=(
                "python",
                "validate_stubs.py",
                "--rust-dir",
                ".",
                "--parity-contract",
                "docs/implementation/python_api_parity/baseline/parity_contract.json",
                "--json-out",
                "tools/binding_compliance/artifacts/stub_validation_report.json",
                "--fail-on-warnings",
            )
        ),
        paths=("validate_stubs.py",),
        proves=(
            "Maintained Python stubs expose the same public classes/functions as PyO3 wrappers.",
        ),
    ),
    ComplianceRequirement(
        id="generated-artifacts-present",
        title="Generated and maintained contract artifacts are present",
        surface="generated_artifacts",
        classification="new_check",
        profiles=STATIC_PROFILES,
        blocking=True,
        summary="The suite can find every checked-in baseline, declaration, and stub report it depends on.",
        paths=(
            "node-bindings/classic-node/index.d.ts",
            "docs/implementation/cxx_api_parity/baseline/parity_contract.json",
            "docs/implementation/node_api_parity/baseline/parity_contract.json",
            "docs/implementation/python_api_parity/baseline/parity_contract.json",
            "python-bindings/parity-artifacts/stub_validation_report.json",
        ),
        proves=(
            "The top-level suite is anchored to checked-in contract artifacts instead of ad hoc scans only.",
        ),
    ),
    ComplianceRequirement(
        id="runtime-coverage-registries-present",
        title="Runtime coverage registries are present",
        surface="runtime_coverage",
        classification="new_check",
        profiles=STATIC_PROFILES,
        blocking=True,
        summary="Node and Python runtime coverage registries and baseline summaries are checked in.",
        paths=(
            "node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json",
            "python-bindings/tests/fixtures/runtime_coverage_registry.json",
            "docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json",
            "docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json",
        ),
        proves=(
            "Node and Python lower-level gates can classify runtime-verified, mapped-only, and uncovered surfaces.",
        ),
    ),
    ComplianceRequirement(
        id="cxx-runtime-coverage-gap",
        title="C++ runtime coverage registry gap",
        surface="runtime_coverage",
        classification="coverage_gap",
        profiles=STATIC_PROFILES,
        blocking=False,
        summary="The CXX parity gate is source-only and has no dedicated runtime coverage registry.",
        gaps=(
            "C++ bridge runtime behavior is still covered by CLI/GUI wrapper tests rather than a CXX runtime coverage registry equivalent to Node/Python.",
        ),
    ),
    ComplianceRequirement(
        id="node-dts-freshness",
        title="Node index.d.ts freshness",
        surface="stubs_declarations",
        classification="existing_gate",
        profiles=("full", "node-ci"),
        blocking=True,
        summary="Regenerates Node declarations into a temp directory and compares them to index.d.ts.",
        command=CommandSpec(
            argv=("bun", "run", "dts:freshness:check"),
            cwd="node-bindings/classic-node",
        ),
        paths=(
            "tools/node_api_parity/check_dts_freshness.py",
            "node-bindings/classic-node/index.d.ts",
        ),
        proves=(
            "The checked-in TypeScript declaration file is fresh relative to NAPI-RS generation.",
        ),
    ),
    ComplianceRequirement(
        id="node-bun-runtime-tests",
        title="Node Bun runtime tests",
        surface="node",
        classification="existing_gate",
        profiles=("full",),
        blocking=True,
        summary="Runs the Bun runtime test suite for the Node binding package.",
        command=CommandSpec(
            argv=("bun", "run", "test:bun"),
            cwd="node-bindings/classic-node",
        ),
        proves=("Bun consumers can load and exercise the generated NAPI package.",),
    ),
    ComplianceRequirement(
        id="node-node-runtime-tests",
        title="Node.js runtime smoke tests",
        surface="node",
        classification="existing_gate",
        profiles=("full",),
        blocking=True,
        summary="Runs the Node.js runtime smoke tests for the Node binding package.",
        command=CommandSpec(
            argv=("bun", "run", "test:node"),
            cwd="node-bindings/classic-node",
        ),
        proves=("Node.js consumers can load and exercise the generated NAPI package.",),
    ),
    ComplianceRequirement(
        id="python-tooling-sync",
        title="Python binding tooling sync",
        surface="python",
        classification="existing_gate",
        profiles=("full", "python-ci"),
        blocking=True,
        summary="Refreshes the uv-managed Python binding tooling environment.",
        command=CommandSpec(
            argv=(
                "uv",
                "sync",
                "--project",
                "python-bindings",
                "--inexact",
                "--group",
                "drift-guards",
                "--locked",
            )
        ),
        proves=("Python parity, schema drift, and stub validation tools are available.",),
    ),
    ComplianceRequirement(
        id="python-schema-version-drift",
        title="Python schema-version drift guard",
        surface="policy",
        classification="existing_gate",
        profiles=("full", "python-ci"),
        blocking=True,
        summary="Runs the checked-in YAML schema-version drift guard used by Python CI.",
        command=CommandSpec(
            argv=(
                "uv",
                "run",
                "--project",
                "python-bindings",
                "python",
                "tools/schema_version_gate.py",
                "--repo-root",
                ".",
            )
        ),
        paths=("tools/schema_version_gate.py",),
        proves=("Binding validation is not hiding schema contract drift that Python smoke tests import.",),
    ),
    ComplianceRequirement(
        id="python-bindings-rebuild",
        title="Python PyO3 binding rebuild",
        surface="python",
        classification="existing_gate",
        profiles=("full",),
        blocking=True,
        summary="Builds and installs every PyO3 binding crate into python-bindings/.venv.",
        command=CommandSpec(
            argv=("pwsh", "-ExecutionPolicy", "Bypass", "-File", "rebuild_rust.ps1", "-Target", "python"),
            env=(("PYO3_PYTHON", "{repo_root}\\python-bindings\\.venv\\Scripts\\python.exe"),),
        ),
        proves=("Python runtime smoke tests import freshly built PyO3 modules.",),
    ),
    ComplianceRequirement(
        id="python-runtime-smoke-tests",
        title="Python runtime smoke tests",
        surface="python",
        classification="existing_gate",
        profiles=("full",),
        blocking=True,
        summary="Runs the Python binding smoke/runtime test suite through python -m pytest.",
        command=CommandSpec(
            argv=(
                "uv",
                "run",
                "--project",
                "python-bindings",
                "python",
                "-m",
                "pytest",
                "python-bindings/tests",
                "-q",
            )
        ),
        proves=("Python consumers can import and exercise the built PyO3 modules.",),
    ),
    ComplianceRequirement(
        id="error-shape-docs",
        title="Binding error shapes are documented",
        surface="docs",
        classification="new_check",
        profiles=STATIC_PROFILES,
        blocking=True,
        summary="The documented C++, Node, and Python error-shape expectations remain discoverable.",
        paths=("docs/api/error-contract.md",),
        text_expectations=(
            TextExpectation(
                path="docs/api/error-contract.md",
                contains=(
                    "C++ (CXX Bridge)",
                    "Node (NAPI-RS)",
                    "Python (PyO3)",
                    "Notification errors",
                    "CLASSIC Main.yaml",
                ),
            ),
        ),
        proves=("Known per-binding error shape divergence is documented rather than normalized away.",),
    ),
    ComplianceRequirement(
        id="docs-canonical-command",
        title="Canonical binding compliance command is documented",
        surface="docs",
        classification="new_check",
        profiles=STATIC_PROFILES,
        blocking=True,
        summary="Contributor docs name the binding compliance suite as the canonical umbrella gate.",
        paths=("docs/api/binding-compliance-suite.md",),
        text_expectations=(
            TextExpectation(
                path="docs/api/binding-compliance-suite.md",
                contains=(
                    "tools/binding_compliance/check_compliance.py",
                    "canonical binding gate",
                    "--profile ci",
                ),
            ),
        ),
        proves=("Contributors can find the top-level replacement command without reading CI YAML.",),
    ),
    ComplianceRequirement(
        id="ci-canonical-command",
        title="CI invokes the binding compliance command",
        surface="policy",
        classification="new_check",
        profiles=STATIC_PROFILES,
        blocking=True,
        summary="Binding-related CI workflows invoke the canonical compliance command.",
        paths=(
            ".github/workflows/ci-cpp.yml",
            ".github/workflows/ci-typescript.yml",
            ".github/workflows/ci-python-bindings.yml",
        ),
        text_expectations=(
            TextExpectation(
                path=".github/workflows/ci-cpp.yml",
                contains=("tools/binding_compliance/check_compliance.py", "--profile cxx-ci"),
            ),
            TextExpectation(
                path=".github/workflows/ci-typescript.yml",
                contains=("tools/binding_compliance/check_compliance.py", "--profile node-ci"),
            ),
            TextExpectation(
                path=".github/workflows/ci-python-bindings.yml",
                contains=("tools/binding_compliance/check_compliance.py", "--profile python-ci"),
            ),
        ),
        proves=("CI policy now flows through the umbrella suite while old gates remain diagnostic subcommands.",),
    ),
)


def requirements_for_profile(profile: str) -> tuple[ComplianceRequirement, ...]:
    """Return requirements that participate in a named execution profile."""

    selected = tuple(
        requirement for requirement in REQUIREMENTS if profile in requirement.profiles
    )
    if not selected:
        known = sorted({name for req in REQUIREMENTS for name in req.profiles})
        raise ValueError(
            f"Unknown binding compliance profile '{profile}'. Known profiles: {', '.join(known)}"
        )
    return selected
