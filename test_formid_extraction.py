"""Test FormID extraction for Rust backend migration - Phase 1.2"""

from classic_core import scanlog


def test_formid_extraction():
    """Test that FormID extraction matches Python behavior."""
    print("🔍 Testing FormID extraction (Rust batch function)...\n")

    # Test callstack data (simulating crash log format)
    test_callstack = [
        "    Form ID: 0x00012345",  # Valid FormID
        "    Form ID: 0xABCDEF01",  # Valid FormID
        "    Form ID: 0xFF123456",  # Should be filtered (starts with FF)
        "    Form ID: 0x00000000",  # NULL FormID (should be kept)
        "some other line",
        "    Form ID: 0x12AB34CD",  # Valid FormID
    ]

    print("1️⃣ Testing FormID batch extraction...")
    print(f"   Input: {len(test_callstack)} callstack lines")

    # Extract with Rust using batch function (expects list of callstack segments)
    rust_formids = scanlog.extract_formids_batch([test_callstack])[0]
    print(f"\n   Rust extracted {len(rust_formids)} FormIDs:")
    for formid in rust_formids:
        print(f"     - {formid}")

    # Verify expected results
    expected = [
        "Form ID: 00012345",
        "Form ID: ABCDEF01",
        "Form ID: 00000000",  # NULL kept
        "Form ID: 12AB34CD",
    ]

    print(f"\n2️⃣ Verifying results...")
    if rust_formids == expected:
        print("   ✅ All FormIDs match expected output")
        print(f"   ✅ Correctly filtered FF prefix")
        print(f"   ✅ Correctly kept NULL FormID (00000000)")
    else:
        print(f"   ❌ Mismatch!")
        print(f"   Expected: {expected}")
        print(f"   Got:      {rust_formids}")
        return False

    # Test validation function
    print(f"\n3️⃣ Testing FormID validation...")
    test_formids = ["00012345", "FF123456", "INVALID", "DEADBEEF"]
    valid_results = scanlog.validate_formids_batch(test_formids)
    print(f"   Valid: {[f for f, v in zip(test_formids, valid_results) if v]}")
    print(f"   Invalid: {[f for f, v in zip(test_formids, valid_results) if not v]}")

    # Test is_valid_formid function
    print(f"\n4️⃣ Testing individual FormID validation...")
    test_cases = [
        ("12345678", True),
        ("ABCDEF01", True),
        ("GGGGGGGG", False),
        ("123", False),  # Too short
    ]

    all_passed = True
    for formid_str, expected_valid in test_cases:
        is_valid = scanlog.is_valid_formid(formid_str)
        if is_valid == expected_valid:
            print(f"   ✅ {formid_str} → {'valid' if is_valid else 'invalid'}")
        else:
            print(f"   ❌ {formid_str} → Expected {expected_valid}, got {is_valid}")
            all_passed = False

    if not all_passed:
        return False

    # Test multi-segment batch processing
    print(f"\n5️⃣ Testing multi-segment batch processing...")
    callstack_segments = [
        ["    Form ID: 0x11111111"],
        ["    Form ID: 0x22222222", "    Form ID: 0x33333333"],
        [],  # Empty segment
    ]

    batch_results = scanlog.extract_formids_batch(callstack_segments)
    print(f"   Segment 1: {batch_results[0]}")
    print(f"   Segment 2: {batch_results[1]}")
    print(f"   Segment 3 (empty): {batch_results[2]}")

    if len(batch_results[0]) == 1 and len(batch_results[1]) == 2 and len(batch_results[2]) == 0:
        print("   ✅ Batch processing works correctly")
    else:
        print("   ❌ Batch processing failed")
        return False

    print("\n✅ All FormID extraction tests passed!")
    print("\n📊 Performance note:")
    print("   Expected speedup: 25x (250ms → 10ms per 1000 FormIDs)")
    return True


if __name__ == "__main__":
    success = test_formid_extraction()

    if success:
        print("\n🎉 FormID extraction is working correctly!")
        print("\nNext steps:")
        print("  1. Integrate with FormIDAnalyzerCore Python wrapper")
        print("  2. Add FormID matching (formid_match method)")
        print("  3. Add database lookup support")
        print("  4. Proceed with pattern matching (Section 1.3)")
    else:
        print("\n❌ FormID extraction has issues that need to be resolved")
