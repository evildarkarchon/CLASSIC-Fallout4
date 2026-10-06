"""Type declarations need source-corroborated absence of a custom constructor."""

import shutil
from pathlib import Path


def _example_facade(root: Path) -> tuple[Path, Path]:
    """Create the ``classic_example`` facade in the one Python adapter layout.

    Returns ``(stub, rust_dir)``: the facade's ``python/classic_example/__init__.pyi``
    path and its ``src/classic_example/`` Rust directory (both parents created).
    """
    adapter = root / "python-bindings/classic-python-bindings"
    stub = adapter / "python/classic_example/__init__.pyi"
    rust_dir = adapter / "src/classic_example"
    stub.parent.mkdir(parents=True, exist_ok=True)
    rust_dir.mkdir(parents=True, exist_ok=True)
    return stub, rust_dir


def test_typed_dict_is_a_type_only_contract_not_a_phantom_native_class(
        tmp_path: Path,
) -> None:
    """Typing-only dictionary declarations retain stub shape without runtime credit."""
    from conformance.source_declarations import python_declaration_exports

    stub, _ = _example_facade(tmp_path)
    stub.write_text(
        "from typing import TypedDict\nclass Stats(TypedDict):\n    count: int\nclass MissingNative: ...\n"
    )
    assert python_declaration_exports(tmp_path) == {("classic_example", "Stats")}
    stub.write_text(
        "from typing import TypedDict\nTypedDict = object\nclass Stats(TypedDict):\n    count: int\n"
    )
    assert python_declaration_exports(tmp_path) == set()


def test_python_type_declaration_checks_both_stub_and_rust_constructor(
        tmp_path: Path,
) -> None:
    """An omitted stub constructor must never hide a real PyO3 #[new] function."""
    from conformance.source_declarations import python_declaration_exports

    stub, rust_dir = _example_facade(tmp_path)
    stub.write_text(
        "class Result:\n    value: str\n\nclass Request:\n    def __init__(self, value: str) -> None: ...\n"
    )
    rust = rust_dir / "mod.rs"
    rust.write_text(
        "#[pyclass]\npub struct Result { value: String }\n#[pyclass]\npub struct Request { value: String }\n#[pymethods]\nimpl Request { #[new] pub fn new(value: String) -> Self { Self { value } } }\nfn register(m: Module) { m.add_class::<Result>(); m.add_class::<Request>(); }\n"
    )
    assert python_declaration_exports(tmp_path) == {("classic_example", "Result")}
    rust.write_text(
        rust.read_text()
        + "\n#[pymethods]\nimpl Result { #[new] pub fn new(value: String) -> Self { Self { value } } }\n"
    )
    assert python_declaration_exports(tmp_path) == set()


def test_constructor_in_another_source_file_prevents_structural_credit(
        tmp_path: Path,
) -> None:
    """Split pymethods implementations must not hide callable construction."""
    from conformance.source_declarations import python_declaration_exports

    stub, rust_dir = _example_facade(tmp_path)
    stub.write_text("class Result:\n    value: str\n")
    (rust_dir / "mod.rs").write_text(
        "#[pyclass]\npub struct Result { value: String }\nfn register(m: Module) { m.add_class::<Result>(); }\n"
    )
    (rust_dir / "constructor.rs").write_text(
        "#[pymethods]\nimpl Result { #[new] pub fn new(value: String) -> Self { Self { value } } }\n"
    )
    assert python_declaration_exports(tmp_path) == set()
    (rust_dir / "constructor.rs").rename(rust_dir / "constructors_tests.rs")
    (rust_dir / "mod.rs").write_text(
        (rust_dir / "mod.rs").read_text() + "mod constructors_tests;\n"
    )
    assert python_declaration_exports(tmp_path) == set()


def test_comments_strings_and_unregistered_types_cannot_claim_declaration_evidence(
        tmp_path: Path,
) -> None:
    """Only real registered declarations may own structural source evidence."""
    from conformance.source_declarations import python_declaration_exports

    stub, rust_dir = _example_facade(tmp_path)
    stub.write_text("class Result: ...\n")
    source = "#[pyclass]\npub struct Result {}\nfn register(m: Module) { m.add_class::<Result>(); }\n"
    rust = rust_dir / "mod.rs"
    for fake in (
            "/* " + source + " */",
            'const FAKE: &str = r###"' + source + '"###;',
            "#[pyclass]\npub struct Result {}\n// m.add_class::<Result>();\n",
    ):
        rust.write_text(fake)
        assert python_declaration_exports(tmp_path) == set()


def test_shared_exception_macro_requires_real_import_registration_and_unmodified_definition(
        tmp_path: Path,
) -> None:
    """The standard macro owns type declarations only while its expansion stays standard."""
    from conformance.source_declarations import python_declaration_exports

    root = Path(__file__).resolve().parents[3]
    macro = Path("python-bindings/classic-python-bindings/src/support/exceptions.rs")
    (tmp_path / macro).parent.mkdir(parents=True)
    shutil.copy2(root / macro, tmp_path / macro)
    stub, rust_dir = _example_facade(tmp_path)
    stub.write_text(
        "class Error(Exception): ...\nclass IOError(Error): ...\nclass ParseError(Error): ...\n"
    )
    source = "use crate::support::{define_exceptions, register_exceptions};\ndefine_exceptions!(module: classic_example, base: Error, io: IOError, parse: ParseError);\nfn init(m: Module) { register_exceptions!(m, Error, IOError, ParseError); }\n"
    rust = rust_dir / "mod.rs"
    rust.write_text(source)
    assert python_declaration_exports(tmp_path) == {
        ("classic_example", name) for name in ("Error", "IOError", "ParseError")
    }
    rust.write_text(
        source.replace("register_exceptions!(m, Error, IOError, ParseError);", "")
    )
    assert python_declaration_exports(tmp_path) == set()
    rust.write_text(source)
    (tmp_path / macro).write_text(
        (tmp_path / macro)
        .read_text()
        .replace("pyo3::exceptions::PyException", "pyo3::exceptions::PyValueError")
    )
    assert python_declaration_exports(tmp_path) == set()


def test_exception_declaration_requires_pyo3_provenance_and_registration(
        tmp_path: Path,
) -> None:
    """A similarly named local macro cannot disguise a custom callable Python class."""
    from conformance.source_declarations import python_declaration_exports

    stub, rust_dir = _example_facade(tmp_path)
    stub.write_text("class Error(Exception): ...\n")
    source = 'use pyo3::create_exception;\ncreate_exception!(classic_example, Error, pyo3::exceptions::PyException);\nfn register(m: Module) { m.add("Error", m.py().get_type::<Error>()); }\n'
    rust = rust_dir / "mod.rs"
    rust.write_text(source)
    assert python_declaration_exports(tmp_path) == {("classic_example", "Error")}
    for changed in (
            source.replace('m.add("Error", m.py().get_type::<Error>());', ""),
            source.replace(
                "use pyo3::create_exception;",
                "macro_rules! create_exception { ($($t:tt)*) => {}; }",
            ),
            source.replace("use pyo3::create_exception;", ""),
    ):
        rust.write_text(changed)
        assert python_declaration_exports(tmp_path) == set()


def test_retired_shared_py_macro_location_cannot_own_exception_declarations(
        tmp_path: Path,
) -> None:
    """Only the adapter's `support` module may own the standard exception macros.

    #259 folded `foundation/classic-shared-py` into the one Python adapter, so
    an unmodified macro left (or restored) at the retired crate path must not
    earn declaration credit for a facade that imports it.
    """
    from conformance.source_declarations import python_declaration_exports

    root = Path(__file__).resolve().parents[3]
    live_macro = root / "python-bindings/classic-python-bindings/src/support/exceptions.rs"
    retired_macro = tmp_path / "foundation/classic-shared-py/src/exceptions.rs"
    retired_macro.parent.mkdir(parents=True)
    shutil.copy2(live_macro, retired_macro)
    adapter = tmp_path / "python-bindings/classic-python-bindings"
    stub = adapter / "python/classic_alpha/__init__.pyi"
    stub.parent.mkdir(parents=True)
    stub.write_text(
        "class Error(Exception): ...\nclass IOError(Error): ...\nclass ParseError(Error): ...\n"
    )
    (adapter / "src/classic_alpha").mkdir(parents=True)
    (adapter / "src/classic_alpha/mod.rs").write_text(
        "use crate::support::{define_exceptions, register_exceptions};\n"
        "define_exceptions!(module: classic_alpha, base: Error, io: IOError, parse: ParseError);\n"
        "fn register_facade(m: Module) { register_exceptions!(m, Error, IOError, ParseError); }\n"
    )

    assert python_declaration_exports(tmp_path) == set()


def test_retired_per_module_binding_crate_stub_cannot_claim_declarations(
        tmp_path: Path,
) -> None:
    """A stub in a retired `classic-*-py` crate layout is not a maintained Python surface."""
    from conformance.source_declarations import python_declaration_exports

    for layer in ("python-bindings", "foundation"):
        legacy = tmp_path / layer / "classic-example-py"
        (legacy / "src").mkdir(parents=True)
        (legacy / "classic_example.pyi").write_text("class Result: ...\n")
        (legacy / "src" / "lib.rs").write_text(
            "#[pyclass]\npub struct Result {}\nfn register(m: Module) { m.add_class::<Result>(); }\n"
        )

    assert python_declaration_exports(tmp_path) == set()


def test_one_adapter_facade_stub_reads_only_its_own_module_sources(
        tmp_path: Path,
) -> None:
    """In the merged adapter, each facade stub pairs with `src/<facade>/` only."""
    from conformance.source_declarations import python_declaration_exports

    root = Path(__file__).resolve().parents[3]
    macro = Path("python-bindings/classic-python-bindings/src/support/exceptions.rs")
    (tmp_path / macro).parent.mkdir(parents=True)
    shutil.copy2(root / macro, tmp_path / macro)
    adapter = tmp_path / "python-bindings/classic-python-bindings"
    for facade in ("classic_alpha", "classic_beta"):
        stub = adapter / "python" / facade / "__init__.pyi"
        stub.parent.mkdir(parents=True)
        stub.write_text(
            "class Result: ...\nclass Error(Exception): ...\n"
            "class IOError(Error): ...\nclass ParseError(Error): ...\n"
        )
        (adapter / "src" / facade).mkdir(parents=True)
    # Only classic_alpha declares and registers these types.
    (adapter / "src" / "classic_alpha" / "mod.rs").write_text(
        "use crate::support::{define_exceptions, register_exceptions};\n"
        "define_exceptions!(module: classic_alpha, base: Error, io: IOError, parse: ParseError);\n"
        "#[pyclass]\npub struct Result {}\n"
        "fn register_facade(m: Module) { m.add_class::<Result>(); "
        "register_exceptions!(m, Error, IOError, ParseError); }\n"
    )

    assert python_declaration_exports(tmp_path) == {
        ("classic_alpha", name) for name in ("Result", "Error", "IOError", "ParseError")
    }
