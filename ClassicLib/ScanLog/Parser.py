"""
Crash log parser module for CLASSIC.

This module is responsible for parsing crash logs and extracting segments.
It handles the parsing of crash log files into structured segments,
extraction of game version, crash generator version, and main error information.
"""

import regex as re


def parse_crash_header(crash_data: list[str], crashgen_name: str, game_root_name: str) -> tuple[str, str, str]:
    """
    Extract metadata from crash data including game version, crash generator version, and main error.

    Args:
        crash_data: List of strings representing lines of the crash data
        crashgen_name: Name of the crash generator to be identified
        game_root_name: Root name of the game to identify game version

    Returns:
        Tuple containing:
        - Game version string (or "UNKNOWN")
        - Crash generator version string (or "UNKNOWN")
        - Main error message (or "UNKNOWN")
    """
    game_version = "UNKNOWN"
    crashgen_version = "UNKNOWN"
    main_error = "UNKNOWN"

    for line in crash_data:
        if game_root_name and line.startswith(game_root_name):
            game_version: str = line.strip()
        if line.startswith(crashgen_name):
            crashgen_version: str = line.strip()
        if line.startswith("Unhandled exception"):
            main_error: str = line.replace("|", "\n", 1)

    return game_version or "UNKNOWN", crashgen_version or "UNKNOWN", main_error or "UNKNOWN"


def extract_segments(crash_data: list[str], segment_boundaries: list[tuple[str, str]], eof_marker: str) -> list[list[str]]:
    """
    Extract segments from crash data based on defined boundaries.

    Args:
        crash_data: The raw crash report data
        segment_boundaries: List of tuples with (start_marker, end_marker) for each segment
        eof_marker: The marker used to indicate end of file

    Returns:
        A list of segments where each segment is a list of lines
    """
    segments: list[list[str]] = []
    total_lines: int = len(crash_data)
    current_index = 0
    segment_index = 0
    collecting = False
    segment_start_index = 0
    current_boundary: str = segment_boundaries[0][0]  # Start with first boundary

    while current_index < total_lines:
        line: str = crash_data[current_index]

        # Check if we've hit a boundary
        if line.startswith(current_boundary):
            if collecting:
                # End of current segment
                segment_end_index: int = current_index - 1 if current_index > 0 else current_index
                segments.append(crash_data[segment_start_index:segment_end_index])
                segment_index += 1

                # Check if we've processed all segments
                if segment_index == len(segment_boundaries):
                    break
            else:
                # Start of a new segment
                segment_start_index = current_index + 1 if total_lines > current_index else current_index

            # Toggle collection state and update boundary
            collecting: bool = not collecting
            current_boundary = segment_boundaries[segment_index][int(collecting)]

            # Handle special cases
            if collecting and current_boundary == eof_marker:
                # Add all remaining lines
                segments.append(crash_data[segment_start_index:])
                break

            if not collecting:
                # Don't increment index in case the current line is also the next start boundary
                current_index -= 1

        # Check if we've reached the end while still collecting
        if collecting and current_index == total_lines - 1:
            segments.append(crash_data[segment_start_index:])

        current_index += 1

    return segments


def find_segments(
    crash_data: list[str], crashgen_name: str, xse_acronym: str, game_root_name: str
) -> tuple[str, str, str, list[list[str]]]:
    """
    Find and extract segments from crash data and extract metadata.

    Args:
        crash_data: List of strings representing lines of the crash data
        crashgen_name: Name of the crash generator to be identified
        xse_acronym: Script extender acronym (e.g., "F4SE")
        game_root_name: Root name of the game

    Returns:
        Tuple containing:
        - Game version
        - Crash generator version
        - Main error message
        - Processed segments
    """
    # Define segment boundaries
    segment_boundaries: list[tuple[str, str]] = [
        ("\t[Compatibility]", "SYSTEM SPECS:"),  # segment_crashgen
        ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),  # segment_system
        ("PROBABLE CALL STACK:", "MODULES:"),  # segment_callstack
        ("MODULES:", f"{xse_acronym.upper()} PLUGINS:"),  # segment_allmodules
        (f"{xse_acronym.upper()} PLUGINS:", "PLUGINS:"),  # segment_xsemodules
        ("PLUGINS:", "EOF"),  # segment_plugins
    ]

    # Extract metadata
    game_version, crashgen_version, main_error = parse_crash_header(crash_data, crashgen_name, game_root_name)

    # Parse segments
    segments: list[list[str]] = extract_segments(crash_data, segment_boundaries, "EOF")

    # Process segments to strip whitespace
    processed_segments: list[list[str]] = [[line.strip() for line in segment] for segment in segments] if segments else segments

    # Ensure all expected segments exist (add empty lists for missing segments)
    missing_segments_count: int = len(segment_boundaries) - len(processed_segments)
    if missing_segments_count > 0:
        processed_segments.extend([[]] * missing_segments_count)

    return game_version, crashgen_version, main_error, processed_segments


def extract_module_names(module_texts: set[str]) -> set[str]:
    """
    Extract module names from a set of module text entries.

    Some DLLs have version information that needs to be stripped.

    Args:
        module_texts: Set of module text entries

    Returns:
        Set of cleaned module names
    """
    if not module_texts:
        return set()

    # Pattern matches module name potentially followed by version
    pattern: re.Pattern[str] = re.compile(r"(.*?\.dll)\s*v?.*", re.IGNORECASE)

    result: set[str] = set()
    for text in module_texts:
        text: str = text.strip()
        match: re.Match[str] | None = pattern.match(text)
        if match:
            result.add(match.group(1))
        else:
            result.add(text)
            
    return result