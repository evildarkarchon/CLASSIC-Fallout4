# Rust owns Crash Log Scan Run behavior

Crash Log Scan Run behavior lives behind a Rust `scan_run` module so CLI, GUI, TUI, Node, Python, and C++ adapters do not preserve the prepare-orchestrator-process-write-move sequence themselves. The module owns execution for selected Crash Logs after Crash Log Scan Intake, including analysis, Autoscan Report writing, progress and cancellation semantics, failed-log accounting, and Unsolved Logs decisions; adapters remain responsible for log selection, presentation, and user messaging. This concentrates locality for product behavior in Rust, while preserving `OrchestratorCore` as internal analysis implementation behind the seam.

Targeted Crash Log Scan Runs keep the current rule that failed Crash Logs and Autoscan Reports are not moved to Unsolved Logs. The first migration slice should be Rust core plus the C++ bridge and GUI, with Rust core tests owning behavior and GUI tests reduced to adapter wiring.
