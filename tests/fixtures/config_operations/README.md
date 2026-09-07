# Config operations fixtures

This pack promotes the deterministic Main/Game/Ignore values from the historical
Tier-1 parity fixtures into one shared input-only corpus. The explicit public
loader requires schema markers, which are included here. Ignore uses CRLF to make
unintended text rewriting observable.

All participants load the three exact caller-selected files in a disposable tree.
The successful case observes CLASSIC version, XSE acronym, crash generator name,
selected game version, and the ordered Ignore list. The failure cases observe the
native error code, YAML role, and relative path. Every case independently re-reads
the final file bytes; missing Ignore is never generated or repaired.

This bounded pack covers explicit loading and only the public getters actually
used. It does not replace or claim coverage for installed-data selection, YAML
document helpers, settings caches, or source-path mapping. Historical Tier-1
fixtures remain unchanged.
