import pytest

from ClassicLib.scanning.logs.parser import detect_vr_log


class TestVRDetection:
    """Test VR mode auto-detection from crash log content."""

    def test_detect_vr_exe_lowercase(self):
        """Test detection of Fallout4VR.exe lowercase."""
        content = "Unhandled exception at 0x7FF6 fallout4vr.exe+0DB9300"
        assert detect_vr_log(content) is True

    def test_detect_vr_exe_uppercase(self):
        """Test detection of Fallout4VR.exe uppercase."""
        content = "Unhandled exception at 0x7FF6 FALLOUT4VR.EXE+0DB9300"
        assert detect_vr_log(content) is True

    def test_detect_vr_esm_in_plugins(self):
        """Test detection of Fallout4VR.esm in PLUGINS section."""
        content = "[00] Fallout4VR.esm\n[01] DLCRobot.esm"
        assert detect_vr_log(content) is True

    def test_no_vr_standard_fallout4(self):
        """Test non-VR log is not detected as VR."""
        content = "Unhandled exception at 0x7FF6 Fallout4.exe+0DB9300"
        assert detect_vr_log(content) is False

    def test_no_vr_standard_esm(self):
        """Test standard ESM is not detected as VR."""
        content = "[00] Fallout4.esm\n[01] DLCRobot.esm"
        assert detect_vr_log(content) is False

    def test_list_input(self):
        """Test detection works with list of lines."""
        lines = ["Fallout 4 VR v1.2.72", "Buffout 4 VR", "[00] Fallout4VR.esm"]
        assert detect_vr_log(lines) is True

    def test_empty_input(self):
        """Test empty input returns False."""
        assert detect_vr_log("") is False
        assert detect_vr_log([]) is False
