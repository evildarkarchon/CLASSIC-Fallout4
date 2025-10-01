"""Test script to verify Rust segment extraction works correctly"""
import sys
sys.path.insert(0, r"C:\Users\evild\PycharmProjects\CLASSIC-Fallout4\.venv\Lib\site-packages")

try:
    import classic_core
    print(f"✓ Rust extension loaded: v{classic_core.__version__}")
except ImportError as e:
    print(f"✗ Failed to import classic_core: {e}")
    sys.exit(1)

# Create test crash log data
test_log = [
    "Fallout 4 v1.10.163",
    "Buffout 4 v1.26.2",
    "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF62D02A2F6",
    "",
    "\t[Compatibility]",
    "F4SE: 0.6.21",
    "",
    "SYSTEM SPECS:",
    "OS: Windows 10 x64",
    "CPU: Intel Core i7",
    "",
    "PROBABLE CALL STACK:",
    "[0] 0x7FF62D02A2F6 SomeModule.dll+0x12A2F6",
    "[1] 0x7FF62D02B456 AnotherModule.dll+0x13B456",
    "FormID: 0x12345678 in MyMod.esp",
    "",
    "MODULES:",
    "SomeModule.dll v1.2.3",
    "AnotherModule.dll v4.5.6",
    "",
    "F4SE PLUGINS:",
    "F4SEPlugin1.dll v1.0",
    "",
    "PLUGINS:",
    "[00] Fallout4.esm",
    "[01] MyMod.esp"
]

parser = classic_core.LogParser()

print("\n" + "="*60)
print("Testing extract_section method")
print("="*60)

# Test extracting compatibility section
print("\n1. Testing Compatibility section:")
compat = parser.extract_section(test_log, "\t[Compatibility]", "SYSTEM SPECS:")
print(f"   Result: {compat}")
print(f"   Lines: {len(compat) if compat else 0}")

# Test extracting system specs
print("\n2. Testing System Specs section:")
system = parser.extract_section(test_log, "SYSTEM SPECS:", "PROBABLE CALL STACK:")
print(f"   Result: {system}")
print(f"   Lines: {len(system) if system else 0}")

# Test extracting call stack
print("\n3. Testing Call Stack section:")
callstack = parser.extract_section(test_log, "PROBABLE CALL STACK:", "MODULES:")
print(f"   Result: {callstack}")
print(f"   Lines: {len(callstack) if callstack else 0}")
if callstack:
    print(f"   Contains FormID line: {'FormID: 0x12345678' in ' '.join(callstack)}")

# Test extracting modules
print("\n4. Testing Modules section:")
modules = parser.extract_section(test_log, "MODULES:", "F4SE PLUGINS:")
print(f"   Result: {modules}")
print(f"   Lines: {len(modules) if modules else 0}")

# Test extracting plugins (to end)
print("\n5. Testing Plugins section:")
plugins = parser.extract_section(test_log, "PLUGINS:", "EOF")
print(f"   Result: {plugins}")
print(f"   Lines: {len(plugins) if plugins else 0}")

print("\n" + "="*60)
print("Testing parse_complete method")
print("="*60)

segment_boundaries = [
    ("\t[Compatibility]", "SYSTEM SPECS:"),
    ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
    ("PROBABLE CALL STACK:", "MODULES:"),
    ("MODULES:", "F4SE PLUGINS:"),
    ("F4SE PLUGINS:", "PLUGINS:"),
    ("PLUGINS:", "EOF"),
]

game_ver, crashgen_ver, main_err, segments = parser.parse_complete(
    test_log, segment_boundaries, "F4SE"
)

print(f"\nGame Version: {game_ver}")
print(f"Crashgen Version: {crashgen_ver}")
print(f"Main Error: {main_err}")
print(f"\nSegments returned: {len(segments)}")
for i, seg in enumerate(segments):
    print(f"  Segment {i}: {len(seg)} lines")
    if seg and len(seg) > 0:
        print(f"    First line: {seg[0][:60] if len(seg[0]) > 60 else seg[0]}")

print("\n" + "="*60)
print("Testing FormID extraction")
print("="*60)

formids = parser.extract_formids(test_log)
print(f"\nFormIDs extracted: {formids}")
print(f"Count: {len(formids)}")

print("\n" + "="*60)
print("✓ All tests completed")
print("="*60)
