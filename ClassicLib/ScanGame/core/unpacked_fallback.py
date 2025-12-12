"""Pure Python fallback implementation of UnpackedScanner.

This module provides a Python-only implementation of unpacked file scanning
that matches the Rust interface.
"""

from pathlib import Path


class UnpackedIssues:
    """Container for unpacked file issues.

    Attributes:
        animdata: List of animation data directories detected.
        tex_frmt: List of texture format issues (TGA/PNG instead of DDS).
        snd_frmt: List of sound format issues (MP3/M4A instead of XWM).
        xse_file: List of XSE script files detected.
        previs: List of previs/precombine files detected.
        dds_files: List of DDS files found (for batch dimension checking).

    """

    def __init__(
        self,
        animdata: list[str] | None = None,
        tex_frmt: list[str] | None = None,
        snd_frmt: list[str] | None = None,
        xse_file: list[str] | None = None,
        previs: list[str] | None = None,
        dds_files: list[Path] | None = None,
    ) -> None:
        """Initialize UnpackedIssues container.

        Args:
            animdata: Animation data directories.
            tex_frmt: Texture format issues.
            snd_frmt: Sound format issues.
            xse_file: XSE script files.
            previs: Previs/precombine files.
            dds_files: DDS files for batch checking.

        """
        self.animdata = animdata or []
        self.tex_frmt = tex_frmt or []
        self.snd_frmt = snd_frmt or []
        self.xse_file = xse_file or []
        self.previs = previs or []
        self.dds_files = dds_files or []

    def has_issues(self) -> bool:
        """Check if any issues were found.

        Returns:
            True if any issues detected, False otherwise.

        """
        return bool(self.animdata or self.tex_frmt or self.snd_frmt or self.xse_file or self.previs)

    def total_count(self) -> int:
        """Get total count of all issues.

        Returns:
            Total number of detected issues.

        """
        return len(self.animdata) + len(self.tex_frmt) + len(self.snd_frmt) + len(self.xse_file) + len(self.previs)


class UnpackedScanner:
    """Scan directories for unpacked files that should be in BA2 archives.

    This is a Python fallback implementation that matches the Rust interface.

    Example:
        >>> scanner = UnpackedScanner()
        >>> issues = scanner.scan_directory(Path("/game/Data"), ["f4se.dll"])
        >>> if issues.has_issues():
        ...     print(f"Found {issues.total_count()} issues")

    """

    def __init__(self) -> None:
        """Initialize UnpackedScanner."""

    @staticmethod
    def scan_directory(root_path: Path, xse_scriptfiles: list[str]) -> UnpackedIssues:
        """Scan a directory for unpacked file issues.

        Args:
            root_path: Root directory to scan (typically game Data folder).
            xse_scriptfiles: List of XSE script filenames to detect (e.g., ["f4se.dll"]).

        Returns:
            UnpackedIssues object containing lists of problematic files.

        Example:
            >>> scanner = UnpackedScanner()
            >>> issues = scanner.scan_directory(
            ...     Path("/mods/Data"),
            ...     ["f4se.dll", "skse64.dll"]
            ... )
            >>> for file in issues.tex_frmt:
            ...     print(f"Non-DDS texture: {file}")

        """
        issues = UnpackedIssues()

        if not root_path.exists():
            return issues

        # Convert xse_scriptfiles to lowercase set for faster lookup
        xse_scriptfiles_lower = {f.lower() for f in xse_scriptfiles}

        try:
            for file_path in root_path.rglob("*"):
                if not file_path.is_file():
                    # Check for animation data directory
                    if file_path.is_dir() and file_path.name.lower() == "animationfiledata":
                        relative = str(file_path.relative_to(root_path))
                        issues.animdata.append(relative)
                    continue

                file_ext = file_path.suffix.lower()
                filename_lower = file_path.name.lower()
                relative_str = str(file_path.relative_to(root_path))

                # Check texture formats
                if file_ext in {".tga", ".png"} and "BodySlide" not in file_path.parts:
                    issues.tex_frmt.append(relative_str)
                # Check sound formats
                elif file_ext in {".mp3", ".m4a"}:
                    issues.snd_frmt.append(relative_str)
                # Check for XSE script files
                elif filename_lower in xse_scriptfiles_lower and "Scripts" in file_path.parts:
                    issues.xse_file.append(relative_str)
                # Check for previs files
                elif filename_lower.endswith((".uvd", "_oc.nif")):
                    issues.previs.append(relative_str)
                # Collect DDS files for batch dimension checking
                elif file_ext == ".dds":
                    issues.dds_files.append(file_path)

        except (OSError, PermissionError):
            # Return partial results if scan fails
            pass

        return issues
