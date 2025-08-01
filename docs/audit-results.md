 ### Critical Issues Found:

  1. Thread Reuse Bug - The Pastebin fetch functionality reuses the same QThread instance, which violates Qt threading rules and can cause crashes.
  2. Improper asyncio.run() Usage - Using asyncio.run() in a Qt application can block the GUI thread and conflict with Qt's event loop.
  3. Missing Resource Cleanup - No proper cleanup when the application closes, potentially leaving threads running.
  4. Race Conditions - Potential race conditions in button state management when multiple scan operations run concurrently.
  5. Papyrus Monitor Thread Safety - The Papyrus monitoring thread lacks proper synchronization for start/stop operations.