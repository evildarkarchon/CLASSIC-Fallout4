# Version Registry conformance fixtures

Issue #213 adds enumeration, extender metadata, and crash-generator list/selection scenarios. The shared seed includes real XSE and crash-generator metadata, while absent entries and missing selected versions test explicit absence. All fixtures retain identical YAML for isolated singleton initialization; exact post-call file inventories forbid unintended writes.

These input-only fixtures stage identical `CLASSIC Main.yaml` bytes in an owned
temporary directory before the first public Version Registry call. Each family
participant runs serially in a fresh process: the public Rust `OnceLock` therefore
retains the same fixture registry across every scenario. Custom IDs and metadata
make accidental embedded-default or installed-data fallback observable.

The pack covers metadata lookup, missing IDs, three-component exact matching,
VR selection, mode filtering, unsupported games, and malformed version strings.
Each adapter records the exact post-operation file inventory. There are no live
machine registry, installed-game, network, or executable dependencies.

CXX executes both promoted and legacy public namespaces and requires their
observations to agree. DTO presence flags and native parse-error sentinels map to
the same explicit null/error envelope used by Rust, Node, and Python. Match
confidence uses lowercase spelling; authored match messages remain exact.
