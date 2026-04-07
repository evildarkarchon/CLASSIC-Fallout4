# Phase 3: FCX State Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 03-fcx-state-hardening
**Areas discussed:** Node API names, Reset timing, Reset failures, Issue access model

---

## Node API names

| Option | Description | Selected |
|--------|-------------|----------|
| GlobalState + ConfigIssues | Use `resetFcxGlobalState()` and `getFcxConfigIssues()`. Most explicit, matches roadmap wording, and makes the getter clearly about structured issue objects. | ✓ |
| State + Issues | Use `resetFcxState()` and `getFcxIssues()`. Shorter names and closer to the REQUIREMENTS shorthand. | |
| Mixed pair | Use `resetFcxGlobalState()` with a shorter getter like `getFcxIssues()`. | |

**User's choice:** `resetFcxGlobalState()` + `getFcxConfigIssues()`
**Notes:** Keep the Node surface flat and explicit; no extra wrapper type for FCX state.

---

## Reset timing

| Option | Description | Selected |
|--------|-------------|----------|
| Auto every session | Reset automatically at the start of every single-log and batch scan session, while still exposing explicit reset APIs. | ✓ |
| Auto when FCX on | Only auto-reset when `fcx_mode` is enabled for that scan. | |
| Manual only | Expose reset APIs but require callers to invoke them before scans. | |

**User's choice:** Auto every session
**Notes:** Session isolation should be the default behavior in C++ and Node; manual reset remains available but should not be required for correctness.

---

## Reset failures

| Option | Description | Selected |
|--------|-------------|----------|
| Abort scan | Treat a real reset failure as a scan-start error. `unnecessary` stays non-fatal. | ✓ |
| Warn and continue | Report the reset problem but continue scanning anyway. | |
| Return status only | Surface reset status separately and let callers decide whether to stop. | |

**User's choice:** Abort scan
**Notes:** The stale-state bug is a correctness problem, so a real reset failure should block scan start rather than degrade silently.

---

## Issue access model

| Option | Description | Selected |
|--------|-------------|----------|
| Node getter only | Add `getFcxConfigIssues()` for Node as a structured standalone getter, keep scan results unchanged, and keep C++ limited to reset in this phase. | ✓ |
| Node + C++ getters | Expose structured FCX issue inspection in both Node and the C++ bridge, while still keeping scan result payloads unchanged. | |
| Embed in results too | Attach FCX issues onto scan results as well as or instead of standalone getters. | |

**User's choice:** Node getter only
**Notes:** Keep Phase 3 narrow: add the missing Node issue surface without broadening the C++ bridge contract or reshaping existing result DTOs.

---

## the agent's Discretion

- Exact `FcxResetError` variant naming and error-to-binding mapping
- Exact Node DTO reuse for structured FCX issue objects
- Exact helper placement for the new automatic pre-scan reset calls

## Deferred Ideas

- C++ FCX issue inspection - future phase or follow-up parity work
- Embedding FCX diagnostics into existing scan result payloads - future contract discussion
