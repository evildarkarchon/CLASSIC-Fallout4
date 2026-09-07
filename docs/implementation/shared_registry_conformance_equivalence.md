# Shared utility and registry conformance

These packs retain independently authored expectations outside the input-only
run plans. Each receipt records actual public API results; central comparison
and invocation validation determine whether the observations earn runtime credit.

| Family | Rust owner | Public observations | Current adapters |
|---|---|---|---|
| `string-operations` | `classic-shared-core` | Content-preserving interning, scalar normalization, ordered batch normalization | Rust, Node/Bun, Python |
| `registry-operations` | `classic-registry-core` | Initial absence, typed values, overwrite, removal effect, clear effect | Rust, CXX, Node/Bun, Python |
| `game-identity` | `classic-shared-core` | All four stable game tokens in canonical order | Rust, CXX, Node/Bun, Python |
| `runtime-access` | `classic-shared-core` | Initial and repeated shared runtime availability | Rust, CXX, Node/Bun |

String fixtures preserve Unicode, whitespace, duplicates and empty input. The
authored normalization expectation deliberately retains the uppercase accented
`É`: the core performs ASCII lowercase conversion, not Unicode case folding.
The Python adapter calls `StringProcessor.intern`, `normalize` and
`process_batch(..., "normalize")`; it does not credit unrelated class methods.
No string-pool size or address is compared because Node owns a process-wide pool.

Registry scenarios execute in a dedicated receipt process with global cleanup
before and after each scenario, including failure cleanup. The values include
empty strings, false and -1, preserving successful reads that happen to equal
CXX's missing-value sentinels. Explicit presence checks establish absence in
Rust/CXX/Python. Node has no public presence query, so its public null-returning
`registryGet` establishes absence for these exclusively non-null values. The
pack does not claim cross-language object identity, arbitrary object transport,
convenience getters or application-directory ownership.

Game token coverage uses exact source row selectors. It exercises the shared
CXX `GameId` and `game_id_as_str`, Node `getAllGameIds`, and Python `GameId.as_str`.
The existing config, scanner and web CXX enum carriers retain their existing
evidence; they are not executed by reading the shared enum. Node `getGameName`
and Python equality, hashing, representation, executable-name and VR methods
also retain their prior runtime tests. Those methods have no equivalent public
operation across every adapter in this token contract. These are explicit
retained runtime obligations, not structural reclassifications. Unknown future
methods and row IDs receive no such disposition and fail closed.

Runtime observations access the existing shared Tokio runtime. Rust and CXX
prove availability by executing a trivial task on that runtime; Node exposes
availability/diagnostic access only. Diagnostic projection records availability
and positive worker capacity where exposed, never host-dependent worker counts.
This contract does not claim scheduling, cancellation, runtime shutdown or
runtime object identity. Python's diagnostics are currently inventoried under
the separate `classic-shared-py` owner and retain their existing tests.

Retained Node aux mappings receive explicit source-backed `rustCrate` metadata
for registry, performance, file fingerprint and runtime operations where their
old `aux` label otherwise concealed the actual core owner. Existing mapping IDs
and symbols remain stable; applicability still comes from source parity rows.
