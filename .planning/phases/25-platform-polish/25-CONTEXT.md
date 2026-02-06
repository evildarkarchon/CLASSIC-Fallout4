# Phase 25: Platform Polish - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensure the Slint GUI application runs reliably across Windows configurations and is ready for distribution. This includes GPU/software renderer fallback, HiDPI display scaling, distribution packaging, and launch experience polish. No new features — this is about making what exists production-ready on Windows.

</domain>

<decisions>
## Implementation Decisions

### Renderer fallback
- Silent fallback to software renderer when GPU is unavailable (no user notification)
- Use Skia software (CPU rasterizer) as the fallback — same renderer, just no GPU acceleration, for maximum visual consistency
- Support `SLINT_BACKEND` environment variable override for power users to force software mode
- If both GPU and software rendering fail completely: Claude's discretion on error handling

### HiDPI scaling
- Follow system DPI scaling exactly — respect whatever scaling factor Windows reports
- Per-monitor DPI awareness — re-render when dragged between monitors with different scaling
- Embed a Windows application manifest declaring per-monitor-v2 DPI awareness
- Default window size: 800x600 at 100% scaling (compact, utility app feel)

### Distribution packaging
- Folder-based distribution — folder containing .exe plus any required assets, zipped for distribution
- Static link the Visual C++ runtime into the .exe — zero DLL dependencies, larger binary but no external requirements
- Embed the CLASSIC icon into the .exe via Windows resource file (.rc) — existing icon asset in the repo (researcher should locate it)

### Launch experience
- No console window — pure GUI app using `#![windows_subsystem = "windows"]`
- Log to file always — write a log file in the app data directory, rotated or overwritten each launch
- Self-healing on startup failure — delete corrupted state, recreate defaults, and launch normally
- Restore window position and size across launches — check if Phase 20 state persistence already handles this; if not, add it

### Claude's Discretion
- Total rendering failure error handling approach (when both GPU and software fail)
- Log file rotation strategy and naming
- Exact self-healing recovery logic (what gets reset vs preserved)
- Whether window geometry is already persisted from Phase 20 (verify and extend if needed)

</decisions>

<specifics>
## Specific Ideas

- User mentioned per-tab persistence for window state — Phase 20-02 already implemented state persistence (selected tab, paths). Researcher should verify if window geometry (position/size) is included or needs to be added.
- Static linking means the .exe is fully self-contained — no "missing DLL" errors on fresh Windows installs.
- Skia software fallback chosen specifically for visual consistency with the GPU-accelerated Skia path.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 25-platform-polish*
*Context gathered: 2026-02-05*
