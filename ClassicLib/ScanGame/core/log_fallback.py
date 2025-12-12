"""Pure Python fallback implementation of LogProcessor.

This module provides a Python-only implementation of log processing
that matches the Rust interface.
"""

from pathlib import Path


class LogProcessor:
    """Process log files and detects errors based on patterns.

    This is a simplified Python fallback implementation that matches
    the Rust interface. For full-featured async processing, use the
    LogProcessor from log_processor.py.

    Attributes:
        catch_errors: List of error patterns to catch.
        ignore_files: List of file patterns to ignore.
        ignore_errors: List of error patterns to ignore.

    Example:
        >>> processor = LogProcessor(
        ...     catch_errors=["error", "exception"],
        ...     ignore_files=["debug.log"],
        ...     ignore_errors=["benign"]
        ... )
        >>> report = processor.process_logs(Path("/logs"))
        >>> print(report)

    """

    def __init__(
        self,
        catch_errors: list[str],
        ignore_files: list[str],
        ignore_errors: list[str],
    ) -> None:
        """Initialize LogProcessor with error detection patterns.

        Args:
            catch_errors: List of error patterns to catch in log lines.
            ignore_files: List of file patterns to ignore during scanning.
            ignore_errors: List of error patterns to ignore (exclude from results).

        """
        self.catch_errors = [pattern.lower() for pattern in catch_errors]
        self.ignore_files = [pattern.lower() for pattern in ignore_files]
        self.ignore_errors = [pattern.lower() for pattern in ignore_errors]

    def process_logs(self, log_dir: Path) -> str:
        """Process all log files in the specified directory.

        Scans log files for error patterns and generates a formatted report.

        Args:
            log_dir: Path to directory containing log files.

        Returns:
            Formatted error report string with detected issues.

        Example:
            >>> processor = LogProcessor(["error"], [], [])
            >>> report = processor.process_logs(Path("/logs"))
            >>> if report:
            ...     print("Errors found in logs")

        """
        if not log_dir.exists() or not log_dir.is_dir():
            return ""

        report_lines: list[str] = []

        try:
            # Find all .log files (excluding crash logs)
            for log_file in log_dir.glob("*.log"):
                filename_lower = log_file.name.lower()

                # Skip crash logs and ignored files
                if "crash-" in filename_lower:
                    continue
                if any(pattern in filename_lower for pattern in self.ignore_files):
                    continue

                # Process this log file
                errors = self._process_single_log(log_file)
                if errors:
                    report_lines.extend(self._format_error_report(log_file, errors))

        except (OSError, PermissionError):
            # Return partial results if scan fails
            pass

        return "".join(report_lines)

    def _process_single_log(self, log_file: Path) -> list[str]:
        """Process a single log file and extract errors.

        Args:
            log_file: Path to the log file to process.

        Returns:
            List of error lines found in the log file.

        """
        errors: list[str] = []

        try:
            with log_file.open("r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

                for line in lines:
                    line_lower = line.lower()

                    # Check if line contains any catch patterns
                    has_catch_pattern = any(pattern in line_lower for pattern in self.catch_errors)
                    if not has_catch_pattern:
                        continue

                    # Check if line contains any ignore patterns
                    has_ignore_pattern = any(pattern in line_lower for pattern in self.ignore_errors)
                    if has_ignore_pattern:
                        continue

                    # This is a valid error line
                    errors.append(line.strip())

                # Limit to last 50 errors (tail -50)
                if len(errors) > 50:
                    errors = errors[-50:]

        except (OSError, UnicodeDecodeError):
            # Return empty list if file can't be read
            pass

        return errors

    @staticmethod
    def _format_error_report(log_file: Path, errors: list[str]) -> list[str]:
        """Format error report for a log file.

        Args:
            log_file: Path to the log file.
            errors: List of error lines.

        Returns:
            Formatted report lines.

        """
        report = [
            "[!] CAUTION : THE FOLLOWING LOG FILE REPORTS ONE OR MORE ERRORS!\n",
            "[ Errors do not necessarily mean that the mod is not working. ]\n",
            f"\nLOG PATH > {log_file}\n\n",
        ]

        report.extend(f"ERROR > {error}\n" for error in errors)

        report.append(f"\n* TOTAL NUMBER OF DETECTED LOG ERRORS * : {len(errors)}\n\n")

        return report
