# Python bindings adapter (`classic-python-bindings`)

All 18 `classic_*` Python modules ship from **one** PyO3 adapter crate, one
native extension, and one wheel. The crate is
[`python-bindings/classic-python-bindings`](../../python-bindings/classic-python-bindings/);
it replaced the 17 `python-bindings/classic-*-py` crates and
`foundation/classic-shared-py` in issue #259. It is an adapter only: business
rules and authoritative state stay in the Rust core crates.

## Layout

| Part | Path | Role |
|---|---|---|
| Native extension | `_classic_native._native` (`src/lib.rs`) | One `cdylib`. Its initializer attaches the shared Tokio runtime, configures Python stdio, and registers one submodule per facade. |
| Facade adapter modules | `src/classic_<name>/` | Each former crate's adapter code, unchanged in behavior, with a `register_facade` function. |
| Shared helpers | `src/support/` | Former `classic-shared-py` helper library: error conversion, the `define_exceptions!` / `register_exceptions!` macros, GIL helpers, `PathLike`, Python entry-directory resolution, runtime attachment. No Python surface. |
| Facade packages | `python/classic_<name>/__init__.py` | Pure-Python direct-import packages. Each imports its names from `_classic_native._native.classic_<name>` and declares a literal `__all__`. |
| Maintained stubs | `python/classic_<name>/__init__.pyi` + `py.typed` | The typed contract for each import. |
| Wheel metadata | `pyproject.toml` | maturin mixed layout: `module-name = "_classic_native._native"`, `python-source = "python"`, and the 18 facades in `python-packages`. |

The 18 direct imports are `classic_config`, `classic_database`,
`classic_file_io`, `classic_message`, `classic_path`, `classic_perf`,
`classic_registry`, `classic_resource`, `classic_scangame`, `classic_scanlog`,
`classic_settings`, `classic_shared`, `classic_update`,
`classic_user_settings`, `classic_version`, `classic_version_registry`,
`classic_web`, and `classic_xse`.

## Compatibility contract

Preserved for every facade:

- public names (`__all__` and `dir()`), signatures, docstrings, typed
  exceptions, and `__version__` (the adapter crate version, `9.1.0`);
- canonical identity: every exported class, function, and exception is the
  one native object registered on that facade's submodule, so a value created
  through one facade is the same Python type another accepts (for example
  `classic_shared.GameId` passed to `classic_scanlog.ScanRunConfiguration`);
- defining module: classes keep their `#[pyclass(module = ...)]` value
  (`builtins` where none was ever set) and exceptions keep their
  `create_exception!` module, so every type that was picklable by reference
  still pickles to the same object, and exception instances round-trip.

Deliberate packaging changes (decided in #229 and #231): the installed
distribution is now `classic-python-bindings` instead of 18 `classic-*-py`
distributions; the native filename is `_classic_native/_native.pyd`; facade
`__file__`, `__spec__`, and loader are those of a pure-Python package; and a
native function's `__module__` is now the facade name (`classic_xse`) rather
than the old private native path (`classic_xse.classic_xse`).

Two facades export a class of the same name (`ConfigIssue` in
`classic_scangame` and `classic_scanlog`; `GameVersion` in `classic_scangame`
and `classic_version_registry`; `RustConfigError` in `classic_config` and
`classic_scanlog`; `get_application_dir` / `set_application_dir` in
`classic_config` and `classic_registry`). They stay distinct objects because
each facade has its own native submodule.

## State scopes

Separate extension images used to give every facade its own copy of each
Rust static. The adapter keeps the observable separation by selecting an
opaque core-owned scope at facade entry or object construction; core crates
own the scope types and rules.

| State | Owner page | Python scopes |
|---|---|---|
| Typed registry and application directory | [`classic-registry-core`](classic-registry-core.md#registry-scopes) | `classic_registry`, `classic_config`, `classic_scanlog` each hold an isolated `RegistryScope`. |
| Logical-key and YAML-file caches | [`classic-shared-core`](classic-shared-core.md#cache-scopes) | `classic_settings` holds isolated scopes for both caches; `classic_config.clear_yaml_cache()` clears the default YAML-file scope shared by the config, Version Registry, and scanlog loaders. |
| File-hash cache and statistics | [`classic-file-io-core`](classic-file-io-core.md#file-hash-scopes) | `classic_file_io.FileHasher`, `classic_scangame` Game Setup Intake, and `classic_scanlog` FCX setup (`scan_run::contract::execute_in_scopes`) each hold an isolated `FileHashScope`. |
| Version Registry snapshots | [`classic-version-registry-core`](classic-version-registry-core.md#version-registry-scopes) | `classic_version_registry`, `classic_version`, `classic_config`, `classic_scangame`, `classic_scanlog` each hold a lazy isolated `VersionRegistryScope`. |
| Timing metrics | [`classic-shared-core`](classic-shared-core.md#default-store) | Intentionally shared: `classic_perf` and `classic_shared.RustPerformanceMonitor` read and clear this image's one default store (#231). |

Object-owned caches (`PathHandler`, `FileIOCore`, `DatabasePool`) and
operation-local cancellation stay owned by their objects and operations.

One process-global facility is not scoped: the `log` crate's logger.
`classic_message.init_logging()` installs it for the whole native image, so
once a caller initializes logging, log records from every facade's Rust code
reach it (previously only `classic_message`'s own image could log).

## Runtime

`support::initialize_async_runtime()` runs before any facade is registered and
attaches `pyo3-async-runtimes` to `classic_shared_core::get_runtime()`, so every
native coroutine (`classic_database`, `classic_file_io`, `classic_settings`,
`classic_update`, ...) runs on CLASSIC's one shared Tokio runtime. Before the
merge only `classic_database` did this; the other async facades used a runtime
`pyo3-async-runtimes` built lazily. The private
`_classic_native._native._shares_classic_runtime()` reports the structural
identity for probes.

## Build, install, upgrade

`./rebuild_rust.ps1 -Target python` builds the wheel, then:

1. runs `tools/python_wheel/one_wheel.py remove-obsolete` against
   `python-bindings/.venv`, deleting every legacy `classic_*_py` distribution's
   recorded files, its `.dist-info`, and any leftover `classic_*.pyd` (legacy
   wheels used the same package directories, so a stale `.pyd` or a later
   legacy uninstall could otherwise mask or break the new install);
2. installs the wheel with `--reinstall`;
3. runs `one_wheel.py verify` (18 imports, versions, facade origins, canonical
   objects, no legacy artifacts) in the venv;
4. installs the same wheel into a fresh temporary environment and verifies it
   there too.

Positional module filters no longer apply to the Python target: the 18
modules always build together.

## Parity and stub tooling

- `tools/python_api_parity/generate_baseline.py` reads the stubs from
  `python/<facade>/__init__.pyi`. The adapter is not a core owner, so it is
  not a Rust target crate; rows that inventoried `classic-shared-py` helpers
  retired, and the re-exported `ClassicError` / `ClassicResult` and
  `RuntimeStats` rows name `classic-shared-core`.
- `tools/python_api_parity/resolve_python_rust_symbols.py` keys native
  declarations by facade module (from the `src/classic_<name>/` path) and
  routes each facade import `from _classic_native._native.<facade> import X`
  to that facade's own declaration. A flat import of a name two facades
  declare is reported as ambiguous instead of borrowing an owner.
- `validate_stubs.py` checks each facade's literal `__all__` against the
  checked-in surface (missing, extra, unbound, or wildcard names fail).
- `tools/binding_compliance/conformance/source_declarations.py` pairs each
  facade stub with `src/<facade>/` sources.

Probes: `python-bindings/tests/test_one_wheel_facades.py` (identity, pickle,
both import orders, runtime, metrics, install hygiene) and the scope probes
`test_registry_scopes.py`, `test_yaml_cache_scopes.py`,
`test_hash_cache_scopes.py`, and `test_version_registry_scopes.py`.
