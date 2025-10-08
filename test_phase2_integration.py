"""Quick integration test for Phase 2 Rust components."""
import classic_scanlog
import time
import tempfile
import os

print("=== Testing RustOrchestrator with Phase 2 Integration ===\n")

# Create configuration
config = classic_scanlog.AnalysisConfig("Fallout4", False)
config.crashgen_name = "Buffout 4"
config.crashgen_latest = "1.10.0"
config.game_version = "1.10.163"
config.xse_acronym = "F4SE"

print(f"Configuration: {config}")
print(f"  Game: {config.game}")
print(f"  VR Mode: {config.vr_mode}")
print(f"  Crashgen: {config.crashgen_name}")

# Create orchestrator with Phase 2 enabled
print("\n--- Creating RustOrchestrator with Phase 2 ---")
orchestrator = classic_scanlog.RustOrchestrator(config, enable_phase2=True)
print(f"✓ RustOrchestrator created: {orchestrator}")

# Test with a simple crash log
print("\n--- Creating test crash log ---")
test_log_content = """Fallout 4 v1.10.163

EXCEPTION_ACCESS_VIOLATION reading 0x0

SYSTEM:
\tGPU #1: AMD Radeon RX 6800 XT
\tRAM: 32 GB

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm

PROBABLE CALL STACK:
\tBSScript::Object::dtor+0x123
\tF4SE::ModuleA::Function+0x456
\tFallout4.exe+0xABC
"""

# Write test log
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
    f.write(test_log_content)
    test_log_path = f.name

try:
    # Process the log
    print(f"\n--- Processing log: {test_log_path} ---")
    start = time.perf_counter()
    result = orchestrator.process_log(test_log_path)
    elapsed = time.perf_counter() - start

    print(f"\n✅ Analysis Complete!")
    print(f"  Success: {result.success}")
    print(f"  Processing time: {result.processing_time_ms}ms")
    print(f"  Suspects found: {result.suspect_count}")
    print(f"  Plugin count: {result.plugin_count}")
    print(f"  FormID count: {result.formid_count}")

    print(f"\n--- Report Preview (first 30 lines) ---")
    for i, line in enumerate(result.report_lines[:30], 1):
        print(f"{i:2d}: {line}")

    if len(result.report_lines) > 30:
        print(f"... ({len(result.report_lines) - 30} more lines)")

finally:
    # Cleanup
    os.unlink(test_log_path)

print("\n✨ Phase 2 Integration Test Complete!")
