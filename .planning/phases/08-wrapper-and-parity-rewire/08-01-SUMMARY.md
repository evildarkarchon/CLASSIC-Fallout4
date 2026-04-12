# 08-01 Summary

- Rewired `rebuild_rust.ps1` Python/Node defaults to repo-root binding paths.
- Replaced `rebuild_node.ps1` with a thin alias over `rebuild_rust.ps1 -Target node`.
- Added wrapper regression coverage for root-only paths, stale guidance rejection, and alias delegation.
