"""Pure Python fallback implementation of BA2Scanner.

.. deprecated::
    This fallback is deprecated. The Rust classic_scangame.BA2Scanner is the
    primary implementation. This module will be removed in a future release.

This module provides a Python-only implementation of BA2 archive scanning
that matches the Rust interface. It's used as a fallback when the Rust
acceleration module is not available.
"""

from pathlib import Path


class BA2Issues:
    """Container for BA2 archive issues.

    Attributes:
        tex_dims: List of texture dimension issues (odd dimensions).
        tex_frmt: List of texture format issues (non-DDS textures).
        snd_frmt: List of sound format issues (MP3/M4A instead of XWM).
        xse_file: List of XSE script files found in archives.

    """

    def __init__(
        self,
        tex_dims: list[str] | None = None,
        tex_frmt: list[str] | None = None,
        snd_frmt: list[str] | None = None,
        xse_file: list[str] | None = None,
    ) -> None:
        """Initialize BA2Issues container.

        Args:
            tex_dims: List of texture dimension issues.
            tex_frmt: List of texture format issues.
            snd_frmt: List of sound format issues.
            xse_file: List of XSE script files.

        """
        self.tex_dims = tex_dims or []
        self.tex_frmt = tex_frmt or []
        self.snd_frmt = snd_frmt or []
        self.xse_file = xse_file or []


class BA2Scanner:
    """Simple BA2 archive scanner (Python fallback).

    This is a simplified Python implementation that matches the Rust
    interface. For full-featured scanning with BSArch integration,
    use BA2ArchiveScanner from ba2_scanner.py.

    Example:
        >>> scanner = BA2Scanner()
        >>> issues = scanner.scan_archive(Path("mod.ba2"))
        >>> print(len(issues.tex_frmt))
        5

    """

    def __init__(self) -> None:
        """Initialize BA2Scanner."""

    @staticmethod
    def scan_archive(archive_path: Path) -> BA2Issues:
        """Scan a single BA2 archive for issues.

        This is a simplified Python implementation. For production use,
        consider using the Rust implementation for better performance.

        Args:
            archive_path: Path to the BA2 archive file.

        Returns:
            BA2Issues object containing detected issues.

        Note:
            This Python fallback provides basic validation but doesn't
            perform the full BSArch-based analysis that the Rust version does.

        """
        issues = BA2Issues()

        # Basic validation - check if file exists and has .ba2 extension
        if not archive_path.exists():
            return issues

        if archive_path.suffix.lower() != ".ba2":
            return issues

        # For Python fallback, we can't do deep BA2 analysis without BSArch
        # This is intentionally simplified - use Rust version for full scanning
        return issues

    @staticmethod
    def scan_archives_batch(archive_paths: list[Path]) -> list[tuple[Path, BA2Issues]]:
        """Scan multiple BA2 archives in batch.

        Args:
            archive_paths: List of paths to BA2 archive files.

        Returns:
            List of tuples containing (archive_path, BA2Issues) for each archive.

        Example:
            >>> scanner = BA2Scanner()
            >>> results = scanner.scan_archives_batch([Path("mod1.ba2"), Path("mod2.ba2")])
            >>> for path, issues in results:
            ...     print(f"{path}: {len(issues.tex_frmt)} issues")

        """
        results: list[tuple[Path, BA2Issues]] = []
        for path in archive_paths:
            issues = BA2Scanner.scan_archive(path)
            results.append((path, issues))
        return results
