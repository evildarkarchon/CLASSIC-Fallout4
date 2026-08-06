# Spike Finding: A Non-Blocking Qt Recovery Prompt Path

Answers gate condition 4 of the Local Ignore Recovery Phase in
`docs/implementation/scan_run_presentation_consolidation.md`. Issue #173, under #170.

## Finding

**A non-blocking path exists, it is demonstrated, and it is the path the Qt GUI already ships.**
The recovery phase is not blocked on threading. Gate condition 4 is satisfied.

The GUI thread never stops servicing its event queue while the recovery prompt is open. The thread
that blocks is the scan worker thread, which is the thread that should block: it is holding the
one-shot continuation, and the bridge call it will make next
(`scan_run_continuation_resume`, `cpp-bindings/classic-cpp-bridge/src/scanner/contract.rs:226-254`)
is a `block_on` that must not run on the GUI thread under any design.

This was worth checking rather than assuming, because the two facts that make it work are easy to
read the wrong way round. `Qt::BlockingQueuedConnection` blocks the **caller**, not the receiver, and
`QMessageBox::exec()` starts a **nested** event loop rather than suspending the current one. Both
appear in the path as "blocking", and neither blocks the GUI thread.

## The Path

```
ScanWorker::doScan                              [worker thread]  scanworker.cpp:158
  takes the continuation off the execution                       scanworker.cpp:192
  calls the injected ScanRunLocalIgnoreRecoveryPrompt            scanworker.cpp:193-194
    -> QMetaObject::invokeMethod(Qt::BlockingQueuedConnection)   scancontroller.cpp:51-58
       ...worker thread parks here, GUI thread keeps running...
         ScanController::requestLocalIgnoreRecoveryChoice        [GUI thread] scancontroller.cpp:29-36
           MainWindow's installed lambda                         mainwindow.cpp:296-298
             promptLocalIgnoreRecoveryChoice                     localignorerecoveryprompt.cpp:12
               QMessageBox::exec()  <- nested event loop         localignorerecoveryprompt.cpp:46
    <- typed choice returns by value through the captured reference
  maps the choice to a ScanRunLocalIgnoreRecoveryDecision        scanworker.cpp:195-206
  scan_run_continuation_resume                  [worker thread]  scanworker.cpp:208-209
```

The seam itself is unremarkable and that is the point:

```cpp
// classic-gui/src/workers/scanrunpresentation.h:37-38
using ScanRunLocalIgnoreRecoveryPrompt =
    std::function<ScanRunLocalIgnoreRecoveryChoice(const QString& message, bool resetAvailable)>;
```

## What Was Demonstrated

`classic-gui/tests/test_recoverypromptnonblocking.cpp`, target
`classic-gui-test-recovery-prompt-nonblocking`, run through `classic-gui/build_gui.ps1 -Test`.

The two tests that already existed each cover one half of the seam and so neither could answer this
question. `test_localignorerecoveryprompt.cpp` drives the real modal but calls it directly on the
GUI thread with no worker involved. `test_scancontroller_recovery.cpp` drives the real worker-thread
marshalling but answers with a stub lambda that never opens a dialog, and it pumps the GUI thread by
hand with `QCoreApplication::processEvents`, which would mask exactly the freeze being looked for.

The spike joins them. In every case the GUI thread sits in an ordinary `QEventLoop::exec()`
throughout, with nothing pumping it by hand, so each probe below is evidence the loop kept turning
on its own while `QMessageBox::exec()` was on that thread's stack.

| Probe | Measured while the modal was up | Asserted |
| --- | --- | --- |
| `QTimer` heartbeat on the GUI thread | ~5 ticks per 5 ms poll | at least 25 ticks before answering |
| Repaints of a sibling top-level window | rises every poll tick | at least one |
| A call queued from inside the nested loop | delivered | delivered before the answer |
| Synthesized clicks on the sibling window | delivered every poll tick | at least one |

Four cases isolate the controller seam, with a bare `QThread` standing in for the worker:

- `choosing_a_decision_keeps_the_event_loop_running` — clicks Continue Without Ignore, the worker
  thread receives `ProceedWithoutIgnore`.
- `abandoning_the_prompt_keeps_the_event_loop_running` — Escape and window-close both reach the
  worker thread as `Cancel`.
- `withheld_reset_keeps_the_event_loop_running` — with `resetAvailable == false` the reset button is
  absent and the remaining decision still answers responsively.
- `input_dispatch_continues_while_the_prompt_is_up` — input events keep being dispatched.

Two more cover the shipped path end to end: a real `ScanWorker` on a real `QThread`, running a real
scan against a `QTemporaryDir` install root whose Local Ignore is genuinely unparseable, answered by
the real dialog. These matter because they execute the two legs the seam cases only reason about —
`doScan` taking the one-shot continuation off the execution *before* the prompt, and
`scan_run_continuation_resume` (a `block_on` across the bridge) *after* it.

- `real_scan_worker_recovery_keeps_the_event_loop_running` — Continue Without Ignore; the run then
  resumes and completes (`finished` once, no `error`, no `cancelled`), which is what shows the
  post-prompt resume ran to completion on the worker thread rather than deadlocking against the GUI
  thread that had just been holding the modal. The run also reports Reset To Default as available,
  so the withheld case above is withholding something that would otherwise have worked.
- `real_scan_worker_abandonment_keeps_the_event_loop_running` — Escape; the run ends `cancelled`
  once, with no `error` and nothing scanned.

Every case also asserts that the prompt was requested from a thread other than the GUI thread and
executed on the GUI thread, so a future refactor that quietly ran the dialog on the worker thread
fails here rather than deadlocking a user's window.

A 15-second failsafe closes the dialog and lets the harness report a failure, because the regression
this test guards against is a hang, and a hang would otherwise sit until CTest's 600-second timeout.
For the same reason the harness keeps a flushed breadcrumb file, written to the test's CTest working
directory as `classic-gui/build/tests/recovery-prompt-nonblocking-trace.log`: CTest in this repo does
not surface a test binary's captured stdout, so an abort inside a Qt assertion and a deadlocked loop
are otherwise indistinguishable from the outside.

The issue called for throwaway code. This landed as a registered CTest target instead, deliberately:
the finding is only worth as much as its continued truth, the failure it guards against is a frozen
window rather than a wrong value, and nothing else in the tree would catch a regression here.

## Constraints This Imposes On The Shared Prompt Shape

The brief proposes crossing the bridge as
`ScanRunRecoveryPrompt { lines, decisions }` with
`ScanRunRecoveryDecisionDescription { decision, label, description, available }`. That shape is
compatible with this path, subject to five constraints. Four it already satisfies; the fifth is a
rule for the migration.

1. **The prompt call stays synchronous and value-returning.** The GUI's ability to keep its loop
   alive comes from the *caller* blocking, so a callback- or future-shaped prompt buys nothing and
   costs a great deal: `ScanWorker::doScan` is straight-line code holding the continuation on its
   stack, and the CLI's seam blocks in `std::getline`
   (`classic-cli/src/scan_run_cli.cpp:612`). Making the prompt asynchronous would force `doScan`
   into a state machine for no benefit to any frontend.

2. **Everything the prompt needs must be a copyable value.** The request is captured *by value* into
   the queued lambda and crosses a thread boundary. Today that is a `QString` and a `bool`. A
   `ScanRunRecoveryPrompt` of Qt containers over flat segment structs is fine. What must never
   appear in it is the continuation, a `rust::Box`, a pointer into the worker's stack, or anything
   whose lifetime is tied to the run.

3. **Rendering happens on the worker thread, before the hop.** This falls out of ADR-0007 already —
   display lines are produced while the Rust value is live — and this path makes it load-bearing
   rather than incidental. The GUI thread must never need to touch a Rust value to draw the prompt,
   because by then the worker owns it and is parked.

4. **The answer stays a plain enum.** No handle back into Rust travels in the return direction.

5. **The same-thread short-circuit must survive.** `makeLocalIgnoreRecoveryPrompt` checks
   `QThread::currentThread() == controller->thread()` before using `BlockingQueuedConnection`
   (`scancontroller.cpp:45-47`). `Qt::BlockingQueuedConnection` self-deadlocks when the caller and
   receiver are the same thread, and this is not hypothetical:
   `test_scanworker_cancellation.cpp` calls `worker.doScan(...)` directly on the test thread.
   Whatever the prompt's payload becomes, that branch stays.

Two existing safety properties also have to be carried across rather than rewritten. A prompt that
cannot reach a live controller resolves to `Cancel` — the `QPointer` goes null with the controller,
and a failed `invokeMethod` returns `Cancel` — and `Cancel` is the one outcome that mutates nothing.
And the continuation is taken off the execution *before* the prompt is called, so a prompt that
throws drops the continuation instead of leaving it claimable.

## What This Means For The Frontends Not At Risk

Nothing changes for them, which was the expectation going in; the spike confirms there is no shared
constraint flowing back from the GUI.

- **Native CLI.** Blocks on `std::getline` on its only thread
  (`classic-cli/src/scan_run_cli.cpp:612`). There is no event loop to starve. Constraint 1 above is
  what keeps the shared prompt usable here: a synchronous value-returning call is the only shape a
  `std::getline` loop can implement without inversion of control. The CLI's existing behaviours —
  the three-attempt limit, EOF handling, and installing the prompt only when stdin is a TTY
  (`classic-cli/src/scanner.cpp:223-241`) — are unaffected.
- **TUI.** Owns its render loop, holds the continuation in `PendingLocalIgnoreRecovery`, and answers
  from its key map with the overlay drawn as an ordinary frame. It never blocks on a prompt at all,
  so it is the least constrained of the three and stays that way.

Both keep their own affordances. Bracketed letters, key hints, and buttons are Display Layout; only
the descriptions beside them become shared.

## Limits Of The Demonstration

Stated so the gate is not read as covering more than it does.

- **Headless.** These tests run under the `minimal` QPA plugin. Timer, paint, queued-call, and input
  dispatch are all real, but there is no compositor and no real window manager.
- **Modality is not measured, and is not claimed.** `QTest::mouseClick` synthesizes at the platform
  layer and reaches the sibling window here, where a real user's click on an application-modal
  parent would be refused. Whether the main window *accepts* input while the prompt is open is a
  modality question and a Display Layout choice. Whether the GUI thread is still dispatching at all
  is the non-blocking question, and that is what is demonstrated. A user's window during the prompt
  is responsive in the sense that matters — it repaints, it does not go white, the OS does not mark
  it Not Responding — and modal in the sense the dialog intends.
- **The prompt payload is today's payload.** A `QString` and a `bool`. The constraints above are
  what the richer payload must satisfy; they are reasoned from the mechanism, not measured against a
  `ScanRunRecoveryPrompt` that does not exist yet.
- **One run, one log, one decision each way.** The end-to-end cases scan a single crash log and
  answer once. Nothing here says anything about a long run, many logs, or a second recovery request
  after a resume — that last one `ScanWorker` already treats as an invariant failure.
- **Cancelling from the main window during the prompt was not exercised.** Reading the code, it
  should work and work immediately: `ScanController::cancelScan` calls `ScanWorker::requestCancel`
  as a direct call rather than a queued slot invocation (`scancontroller.cpp:119-124`), so it runs
  on the GUI thread and sets the Rust cancellation token while the worker is parked, and `resume`
  checks cancellation after claiming the continuation and yields the ordinary post-discovery
  cancelled result (`business-logic/classic-scanlog-core/src/scan_run/contract.rs:808-813`). That is
  a reading, not a measurement. Worth a test when the recovery phase lands.
