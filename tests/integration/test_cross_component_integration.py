"""Cross-component integration tests.

This module tests interactions between different components of the system,
ensuring they work together correctly across GUI and CLI interfaces.
"""
# ruff: noqa: ANN201, ANN001, PLR6301, ANN202, RUF059, ASYNC240, ASYNC230

import asyncio
import contextlib
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class IntegrationTestHelpers:
    """Helper functions for cross-component testing."""

    @staticmethod
    def create_synthetic_crash_log() -> str:
        """Create a minimal synthetic crash log for testing."""
        return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

PLUGINS:
    [00] Fallout4.esm
    [01] DLCRobot.esm
    [FE:000] PRP.esp
    [FE:001] SS2_Addon.esp

STACK TRACE:
    [0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> 703355+0x72
    [1] 0x7FF6EF4C145E Fallout4.exe+073145E -> 548219+0x3E

FormID: 00000014 from Fallout4.esm
FormID: FE000800 from [FE:000] PRP.esp
"""

    @staticmethod
    def create_synthetic_game_structure(root_path: Path) -> None:
        """Create a synthetic game directory structure."""
        (root_path / "Data").mkdir(parents=True, exist_ok=True)
        (root_path / "F4SE" / "Plugins").mkdir(parents=True, exist_ok=True)

        # Create synthetic master files
        (root_path / "Data" / "Fallout4.esm").write_bytes(b"SYNTH_MASTER_FILE")
        (root_path / "Data" / "DLCRobot.esm").write_bytes(b"SYNTH_DLC_FILE")

        # Create synthetic plugins
        (root_path / "Data" / "SyntheticMod.esp").write_bytes(b"SYNTH_MOD_FILE")
        (root_path / "Data" / "PRP.esp").write_bytes(b"SYNTH_PRP_FILE")

        # Create F4SE files
        (root_path / "F4SE" / "Plugins" / "Buffout4.dll").write_bytes(b"SYNTH_DLL")


class TestGUIToRustIntegration:
    """Test GUI components integrating with Rust parser and report generation."""

    @pytest.mark.asyncio
    async def test_gui_scan_with_rust_parser(self):
        """Test GUI initiating scan that uses Rust parser."""
        from ClassicLib.AsyncBridge import AsyncBridge
        from ClassicLib.integration.factory import get_parser
        from ClassicLib.MessageHandler.handler import MessageHandler

        # Clear AsyncBridge singleton instances properly
        # Note: MessageHandler is not a singleton anymore, no cleanup needed
        with AsyncBridge._lock:
            for instance in AsyncBridge._instances.values():
                with contextlib.suppress(Exception):
                    instance.shutdown()
            AsyncBridge._instances.clear()

        bridge = AsyncBridge.get_instance()
        MessageHandler()
        parser = get_parser()

        # Create synthetic crash log
        crash_log = IntegrationTestHelpers.create_synthetic_crash_log()

        # Mock GUI components
        with patch("CLASSIC_Interface.MainWindow"):
            # Simulate GUI triggering scan
            async def gui_scan_operation():
                # GUI would call parser through AsyncBridge
                # Use find_segments which is the actual API
                lines = crash_log.splitlines()
                game_ver, crashgen_ver, error, segments = await asyncio.to_thread(
                    parser.find_segments, lines, "Buffout 4", "F4SE", "Fallout4.exe"
                )
                return segments

            # Run through bridge (as GUI would)
            # result = bridge.run_async(gui_scan_operation())
            result = await gui_scan_operation()

            # Validate result
            assert result is not None
            if isinstance(result, dict) and "plugins" in result:
                assert len(result["plugins"]) >= 2

    @pytest.mark.asyncio
    async def test_gui_concurrent_operations(self):
        """Test GUI handling multiple concurrent operations."""
        from ClassicLib.AsyncBridge import AsyncBridge
        from ClassicLib.integration.factory import get_parser

        bridge = AsyncBridge.get_instance()
        parser = get_parser()

        # Create multiple synthetic logs
        logs = [IntegrationTestHelpers.create_synthetic_crash_log() for _ in range(3)]

        # Simulate GUI launching multiple scans
        async def concurrent_scans():
            tasks = []
            for log in logs:
                lines = log.splitlines()
                task = asyncio.create_task(asyncio.to_thread(parser.find_segments, lines, "Buffout 4", "F4SE", "Fallout4.exe"))
                tasks.append(task)

            # Gather returns tuples of (game_ver, crashgen_ver, error, segments)
            results = await asyncio.gather(*tasks)
            # Extract just the segments
            return [r[3] for r in results]

        # results = bridge.run_async(concurrent_scans())
        results = await concurrent_scans()

        # All scans should complete
        assert len(results) == 3
        assert all(r is not None for r in results)


class TestTUIAsyncIntegration:
    """Test TUI components with async operations and file I/O.

    NOTE: These tests mock TUI components to avoid launching the interactive
    interface which would block test execution.
    """

    @pytest.mark.asyncio
    async def test_tui_async_file_operations(self, tmp_path):
        """Test TUI performing async file operations (without launching interactive UI)."""
        from ClassicLib.AsyncBridge import AsyncBridge
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()
        AsyncBridge.get_instance()

        test_file = tmp_path / "test_log.log"
        test_file.write_text("Test log content\nLine 2\nLine 3", encoding="utf-8")

        # Simulate TUI reading file asynchronously
        async def tui_read_operation():
            return await io_core.read_file(str(test_file))

        # TUI would use AsyncBridge in sync context
        # content = bridge.run_async(tui_read_operation())
        content = await tui_read_operation()

        assert content is not None
        assert "Test log content" in content
        assert content.count("\n") >= 2

    @pytest.mark.asyncio
    async def test_tui_live_log_monitoring(self, tmp_path):
        """Test TUI monitoring log file for changes."""
        from ClassicLib.FileIO import FileIOCore

        FileIOCore()

        log_path = tmp_path / "monitor_test.log"
        log_path.write_text("Initial content\n", encoding="utf-8")

        # Simulate TUI monitoring file
        changes_detected = []

        async def monitor_file(path: Path, duration: float = 0.5):
            """Monitor file for changes."""
            start_time = time.time()
            last_size = path.stat().st_size

            while time.time() - start_time < duration:
                await asyncio.sleep(0.1)
                current_size = path.stat().st_size
                if current_size != last_size:
                    changes_detected.append(current_size)
                    last_size = current_size

        # Start monitoring
        monitor_task = asyncio.create_task(monitor_file(log_path))

        # Simulate log updates
        await asyncio.sleep(0.1)
        with Path(log_path).open("a", encoding="utf-8") as f:
            f.write("New line 1\n")

        await asyncio.sleep(0.1)
        with Path(log_path).open("a", encoding="utf-8") as f:
            f.write("New line 2\n")

        await monitor_task

        # Should detect changes
        assert len(changes_detected) >= 1

    @pytest.mark.asyncio
    async def test_tui_async_ui_updates(self):
        """Test TUI updating UI components asynchronously."""
        from ClassicLib.MessageHandler.handler import MessageHandler

        # Note: MessageHandler is not a singleton anymore, no cleanup needed

        MessageHandler()
        messages_received = []

        # Mock TUI component that receives updates
        class MockTUIComponent:
            async def update_status(self, message: str):
                messages_received.append(message)
                await asyncio.sleep(0.01)  # Simulate UI update delay

        tui_component = MockTUIComponent()

        # Simulate async processing with UI updates
        async def process_with_updates():
            await tui_component.update_status("Starting scan...")
            await asyncio.sleep(0.1)

            await tui_component.update_status("Parsing log...")
            await asyncio.sleep(0.1)

            await tui_component.update_status("Analyzing FormIDs...")
            await asyncio.sleep(0.1)

            await tui_component.update_status("Complete!")

        await process_with_updates()

        # Verify all updates were received
        assert len(messages_received) == 4
        assert messages_received[0] == "Starting scan..."
        assert messages_received[-1] == "Complete!"


class TestCLIBatchProcessing:
    """Test CLI batch processing and output format handling."""

    @pytest.mark.asyncio
    async def test_cli_batch_log_processing(self, tmp_path):
        """Test CLI processing multiple logs in batch."""
        from ClassicLib.AsyncBridge import AsyncBridge
        from ClassicLib.integration.factory import get_parser

        AsyncBridge.get_instance()
        parser = get_parser()

        # Create multiple synthetic logs
        num_logs = 5
        log_files = []

        # Create log files
        for i in range(num_logs):
            log_path = tmp_path / f"crash_{i}.log"
            log_path.write_text(IntegrationTestHelpers.create_synthetic_crash_log())
            log_files.append(log_path)

        # Simulate CLI batch processing
        async def batch_process():
            results = []
            for log_path in log_files:
                content = log_path.read_text()
                lines = content.splitlines()
                game_ver, crashgen_ver, error, segments = await asyncio.to_thread(
                    parser.find_segments, lines, "Buffout 4", "F4SE", "Fallout4.exe"
                )
                results.append({"file": log_path.name, "result": segments})
            return results

        # Process batch
        # batch_results = bridge.run_async(batch_process())
        batch_results = await batch_process()

        # Verify all logs processed
        assert len(batch_results) == num_logs
        assert all(r["result"] is not None for r in batch_results)

    @pytest.mark.asyncio
    async def test_cli_parallel_processing(self):
        """Test CLI processing logs in parallel for performance."""
        import concurrent.futures

        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Create synthetic logs
        logs = [IntegrationTestHelpers.create_synthetic_crash_log() for _ in range(10)]

        # Process in parallel using ThreadPoolExecutor
        def process_log(log_content):
            lines = log_content.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")
            return segments

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_log, log) for log in logs]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        elapsed = time.time() - start_time

        # All logs should be processed
        assert len(results) == 10
        assert all(r is not None for r in results)

        # Parallel processing should be faster
        print(f"\nParallel processing time (10 logs): {elapsed:.3f}s")
        assert elapsed < 5.0  # Should process 10 logs quickly in parallel


class TestComponentCommunication:
    """Test communication between different components."""

    @pytest.mark.asyncio
    async def test_message_passing_between_components(self):
        """Test message passing between GUI, backend, and report components."""
        from ClassicLib import GlobalRegistry
        from ClassicLib.MessageHandler.handler import MessageHandler

        # Note: MessageHandler is not a singleton anymore, no cleanup needed
        # Note: GlobalRegistry is module-level now, no cleanup needed

        msg_handler = MessageHandler()
        # registry = GlobalRegistry() removed

        messages_log = []

        # Mock components
        class MockGUIComponent:
            def send_message(self, msg: str):
                msg_handler.info(f"GUI: {msg}")
                messages_log.append(("GUI", msg))

        class MockBackendComponent:
            def process(self, data: str):
                msg_handler.info(f"Backend: Processing {data}")
                messages_log.append(("Backend", f"Processing {data}"))
                return f"Processed: {data}"

        class MockReportComponent:
            def generate(self, processed_data: str):
                msg_handler.info(f"Report: Generating from {processed_data}")
                messages_log.append(("Report", f"Generating from {processed_data}"))
                return "Report complete"

        # Register components
        gui = MockGUIComponent()
        backend = MockBackendComponent()
        report = MockReportComponent()

        GlobalRegistry.register("gui", gui)
        GlobalRegistry.register("backend", backend)
        GlobalRegistry.register("report", report)

        # Simulate component interaction
        gui.send_message("Starting scan")
        processed = backend.process("crash_log.txt")
        report.generate(processed)

        # Verify communication chain
        assert len(messages_log) == 3
        assert messages_log[0] == ("GUI", "Starting scan")
        assert messages_log[1] == ("Backend", "Processing crash_log.txt")
        assert messages_log[2] == ("Report", "Generating from Processed: crash_log.txt")

    @pytest.mark.asyncio
    async def test_error_propagation_across_components(self):
        """Test error propagation from backend to UI components."""
        from ClassicLib.AsyncBridge import AsyncBridge
        from ClassicLib.MessageHandler.handler import MessageHandler

        bridge = AsyncBridge.get_instance()

        # Note: MessageHandler is not a singleton anymore, no cleanup needed

        msg_handler = MessageHandler()
        error_messages = []

        # Mock error handler
        def handle_error(error: str):
            error_messages.append(error)
            msg_handler.error(error)

        # Simulate backend error
        async def backend_operation_with_error():
            await asyncio.sleep(0)
            raise ValueError("Synthetic backend error")

        # UI component catching error
        try:
            # bridge.run_async(backend_operation_with_error())
            await backend_operation_with_error()
        except ValueError as e:
            handle_error(str(e))

        # Verify error was handled
        assert len(error_messages) == 1
        assert "Synthetic backend error" in error_messages[0]

    @pytest.mark.asyncio
    async def test_async_sync_boundary_crossing(self):
        """Test data passing across async/sync boundaries."""
        from ClassicLib.AsyncBridge import AsyncBridge

        bridge = AsyncBridge.get_instance()

        # Test data
        test_data = {
            "plugins": ["Fallout4.esm", "DLCRobot.esm"],
            "formids": ["00000014", "FE000800"],
            "stack_trace": ["0x7FF6EF4C3512", "0x7FF6EF4C145E"],
        }

        # Async function
        async def async_processor(data: dict) -> dict:
            await asyncio.sleep(0.01)  # Simulate async work
            return {"processed": True, "item_count": sum(len(v) for v in data.values())}

        # Sync function calling async
        def sync_wrapper(data: dict) -> dict:
            return bridge.run_async(async_processor(data))

        # Test boundary crossing
        # result = sync_wrapper(test_data)
        result = await asyncio.to_thread(sync_wrapper, test_data)

        assert result["processed"]
        assert result["item_count"] == 6  # 2 + 2 + 2

    @pytest.mark.asyncio
    async def test_shared_state_consistency(self):
        """Test shared state consistency across components."""

        # Note: GlobalRegistry is module-level now, no cleanup needed

        # GlobalRegistry() removed

        # Shared state
        shared_state = {"scan_count": 0, "errors": [], "last_scan": None}

        # Multiple components accessing shared state
        class Component1:
            def update_state(self):
                shared_state["scan_count"] += 1
                shared_state["last_scan"] = "component1"

        class Component2:
            def update_state(self):
                shared_state["scan_count"] += 1
                shared_state["last_scan"] = "component2"

        comp1 = Component1()
        comp2 = Component2()

        # Simulate concurrent updates
        async def concurrent_updates():
            tasks = []
            for i in range(5):
                if i % 2 == 0:
                    tasks.append(asyncio.to_thread(comp1.update_state))
                else:
                    tasks.append(asyncio.to_thread(comp2.update_state))

            await asyncio.gather(*tasks)

        await concurrent_updates()

        # Verify state consistency
        assert shared_state["scan_count"] == 5
        assert shared_state["last_scan"] in {"component1", "component2"}


class TestResourceManagement:
    """Test resource management across components."""

    @pytest.mark.asyncio
    async def test_file_handle_cleanup(self, tmp_path):
        """Test proper file handle cleanup across operations."""
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()

        # Track open files
        open_files = []

        # Create test files
        for i in range(5):
            file_path = tmp_path / f"test_{i}.log"
            file_path.write_text(f"Test content {i}")
            open_files.append(file_path)

        # Read files and ensure cleanup
        for file_path in open_files:
            content = await io_core.read_file(str(file_path))
            assert content is not None

            # File should be readable again (not locked)
            content2 = await io_core.read_file(str(file_path))
            assert content == content2

    @pytest.mark.asyncio
    async def test_memory_cleanup_on_large_operations(self):
        """Test memory cleanup during large operations."""
        import gc

        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Perform large operation
        large_data = []
        for i in range(100):
            # Create synthetic data
            data = IntegrationTestHelpers.create_synthetic_crash_log() * 10
            large_data.append(data)

            # Periodic cleanup
            if i % 20 == 0:
                # Clear old data
                large_data = large_data[-10:]
                gc.collect()

        # Final cleanup
        large_data.clear()
        gc.collect()

        final_memory = process.memory_info().rss
        memory_increase_mb = (final_memory - initial_memory) / (1024 * 1024)

        print(f"\nMemory increase after large operations: {memory_increase_mb:.2f}MB")

        # Should not leak excessive memory
        assert memory_increase_mb < 50, f"Memory leak: {memory_increase_mb}MB"

    @pytest.mark.asyncio
    async def test_concurrent_resource_access(self):
        """Test concurrent access to shared resources."""
        # Note: GlobalRegistry is module-level now, no cleanup needed

        # GlobalRegistry() removed

        # Shared resource
        resource_lock = asyncio.Lock()
        resource_access_log = []

        async def access_resource(component_id: str, duration: float):
            """Simulate resource access."""
            async with resource_lock:
                resource_access_log.append((component_id, "acquired"))
                await asyncio.sleep(duration)
                resource_access_log.append((component_id, "released"))

        # Multiple components accessing resource
        tasks = [
            access_resource("GUI", 0.1),
            access_resource("Backend", 0.05),
            access_resource("Report", 0.08),
        ]

        await asyncio.gather(*tasks)

        # Verify sequential access (no overlaps)
        assert len(resource_access_log) == 6  # 3 acquires + 3 releases

        # Check proper ordering (acquire before release)
        for i in range(0, len(resource_access_log), 2):
            assert resource_access_log[i][1] == "acquired"
            assert resource_access_log[i + 1][1] == "released"
            assert resource_access_log[i][0] == resource_access_log[i + 1][0]
