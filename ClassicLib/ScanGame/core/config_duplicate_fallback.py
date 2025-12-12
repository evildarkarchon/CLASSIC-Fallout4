"""Pure Python fallback implementation of ConfigDuplicateDetector.

This module provides a Python-only implementation of configuration file
duplicate detection that matches the Rust interface.
"""

from collections import defaultdict
from pathlib import Path

from ClassicLib.Utils.file_utils import calculate_file_hash


class DuplicateGroup:
    """Container for a group of duplicate configuration files.

    Attributes:
        original: Path to the original (canonical) file.
        duplicates: List of duplicate file paths.

    """

    def __init__(self, original: Path, duplicates: list[Path] | None = None) -> None:
        """Initialize DuplicateGroup.

        Args:
            original: Path to the original file.
            duplicates: List of duplicate file paths.

        """
        self.original = original
        self.duplicates = duplicates or []


class ConfigDuplicateDetector:
    """Detect duplicate configuration files in a directory tree.

    This is a Python fallback implementation that matches the Rust interface.
    It finds configuration files with identical content based on file hashes.

    Example:
        >>> detector = ConfigDuplicateDetector()
        >>> duplicates = detector.detect_duplicates(Path("/game/Data"))
        >>> for group in duplicates:
        ...     print(f"Original: {group.original}")
        ...     for dup in group.duplicates:
        ...         print(f"  Duplicate: {dup}")

    """

    @staticmethod
    def detect_duplicates(root_path: Path) -> list[DuplicateGroup]:
        """Detect duplicate configuration files in the specified directory.

        Scans the directory tree for configuration files (.ini, .conf) and
        groups files with identical content based on file hashes.

        Args:
            root_path: Root directory path to scan.

        Returns:
            List of DuplicateGroup objects containing original and duplicate paths.

        Example:
            >>> detector = ConfigDuplicateDetector()
            >>> groups = detector.detect_duplicates(Path("/mods"))
            >>> total_dupes = sum(len(g.duplicates) for g in groups)
            >>> print(f"Found {total_dupes} duplicate files")

        """
        if not root_path.exists():
            return []

        # Map of hash -> list of file paths
        hash_map: dict[str, list[Path]] = defaultdict(list)

        # Scan for configuration files
        for config_file in root_path.rglob("*"):
            if not config_file.is_file():
                continue

            file_lower = config_file.name.lower()
            # Check for config file extensions
            if not (file_lower.endswith((".ini", ".conf")) or file_lower == "dxvk.conf"):
                continue

            try:
                file_hash = calculate_file_hash(config_file)
                hash_map[file_hash].append(config_file)
            except (OSError, PermissionError):
                # Skip inaccessible files
                continue

        # Build duplicate groups
        duplicate_groups: list[DuplicateGroup] = []
        for file_list in hash_map.values():
            if len(file_list) > 1:
                # First file is canonical, rest are duplicates
                canonical = file_list[0]
                duplicates = file_list[1:]
                duplicate_groups.append(DuplicateGroup(canonical, duplicates))

        return duplicate_groups

    @staticmethod
    def get_duplicate_map(root_path: Path) -> dict[str, list[Path]]:
        """Get dictionary mapping of lowercase filenames to lists of paths.

        Args:
            root_path: Root directory path to scan.

        Returns:
            Dictionary where keys are lowercase filenames and values are lists
            of paths with identical content (all files in group, including canonical).

        Example:
            >>> detector = ConfigDuplicateDetector()
            >>> dup_map = detector.get_duplicate_map(Path("/mods"))
            >>> for filename, paths in dup_map.items():
            ...     print(f"{filename}: {len(paths)} copies")

        """
        groups = ConfigDuplicateDetector.detect_duplicates(root_path)

        # Build map of filename -> all paths (canonical + duplicates)
        result: dict[str, list[Path]] = {}
        for group in groups:
            filename_lower = group.original.name.lower()
            all_paths = [group.original, *group.duplicates]
            result[filename_lower] = all_paths

        return result
