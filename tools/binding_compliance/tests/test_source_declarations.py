"""Type declarations need source-corroborated absence of a custom constructor."""

import shutil
from pathlib import Path


def test_typed_dict_is_a_type_only_contract_not_a_phantom_native_class(
        tmp_path: Path,
) -> None:
    """Typing-only dictionary declarations retain stub shape without runtime credit."""
    from conformance.source_declarations import python_declaration_exports

    crate = tmp_path / "python-bindings/classic-example-py"
    crate.mkdir(parents=True)
    (crate / "classic_example.pyi").write_text(
        "from typing import TypedDict\nclass Stats(TypedDict):\n    count: int\nclass MissingNative: ...\n"
    )
    assert python_declaration_exports(tmp_path) == {("classic_example", "Stats")}
    (crate / "classic_example.pyi").write_text(
        "from typing import TypedDict\nTypedDict = object\nclass Stats(TypedDict):\n    count: int\n"
    )
    assert python_declaration_exports(tmp_path) == set()


def test_python_type_declaration_checks_both_stub_and_rust_constructor(
        tmp_path: Path,
) -> None:
    """An omitted stub constructor must never hide a real PyO3 #[new] function."""
    from conformance.source_declarations import python_declaration_exports

    crate = tmp_path / "python-bindings/classic-example-py"
    (crate / "src").mkdir(parents=True)
    (crate / "classic_example.pyi").write_text(
        "class Result:\n    value: str\n\nclass Request:\n    def __init__(self, value: str) -> None: ...\n"
    )
    rust = crate / "src/lib.rs"
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

    crate = tmp_path / "python-bindings/classic-example-py"
    (crate / "src").mkdir(parents=True)
    (crate / "classic_example.pyi").write_text("class Result:\n    value: str\n")
    (crate / "src/lib.rs").write_text(
        "#[pyclass]\npub struct Result { value: String }\nfn register(m: Module) { m.add_class::<Result>(); }\n"
    )
    (crate / "src/constructor.rs").write_text(
        "#[pymethods]\nimpl Result { #[new] pub fn new(value: String) -> Self { Self { value } } }\n"
    )
    assert python_declaration_exports(tmp_path) == set()
    (crate / "src/constructor.rs").rename(crate / "src/constructors_tests.rs")
    (crate / "src/lib.rs").write_text(
        (crate / "src/lib.rs").read_text() + "mod constructors_tests;\n"
    )
    assert python_declaration_exports(tmp_path) == set()


def test_comments_strings_and_unregistered_types_cannot_claim_declaration_evidence(
        tmp_path: Path,
) -> None:
    """Only real registered declarations may own structural source evidence."""
    from conformance.source_declarations import python_declaration_exports

    crate = tmp_path / "python-bindings/classic-example-py"
    (crate / "src").mkdir(parents=True)
    (crate / "classic_example.pyi").write_text("class Result: ...\n")
    source = "#[pyclass]\npub struct Result {}\nfn register(m: Module) { m.add_class::<Result>(); }\n"
    rust = crate / "src/lib.rs"
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
    macro = Path("foundation/classic-shared-py/src/exceptions.rs")
    (tmp_path / macro).parent.mkdir(parents=True)
    shutil.copy2(root / macro, tmp_path / macro)
    crate = tmp_path / "python-bindings/classic-example-py"
    (crate / "src").mkdir(parents=True)
    (crate / "classic_example.pyi").write_text(
        "class Error(Exception): ...\nclass IOError(Error): ...\nclass ParseError(Error): ...\n"
    )
    source = "use classic_shared::{define_exceptions, register_exceptions};\ndefine_exceptions!(module: classic_example, base: Error, io: IOError, parse: ParseError);\nfn init(m: Module) { register_exceptions!(m, Error, IOError, ParseError); }\n"
    rust = crate / "src/lib.rs"
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

    crate = tmp_path / "python-bindings/classic-example-py"
    (crate / "src").mkdir(parents=True)
    (crate / "classic_example.pyi").write_text("class Error(Exception): ...\n")
    source = 'use pyo3::create_exception;\ncreate_exception!(classic_example, Error, pyo3::exceptions::PyException);\nfn register(m: Module) { m.add("Error", m.py().get_type::<Error>()); }\n'
    rust = crate / "src/lib.rs"
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
