"""
Report builder component for CLASSIC_ScanGame.

This module provides report generation functionality for mod scanning operations,
formatting detected issues into human-readable reports for both unpacked and
archived mod scans.
"""

from io import StringIO

from ClassicLib.ScanGame.core.validators import ScanValidators


class ScanReportBuilder:
    """
    Builds formatted scan reports from issue collections.

    This class provides report generation functionality for mod scanning operations.
    It takes collections of detected issues and formats them into human-readable
    reports with appropriate headers and messages for different issue types.

    Attributes:
        validators (ScanValidators): Component for retrieving issue messages.
    """

    def __init__(self, validators: ScanValidators) -> None:
        """
        Initialize the ScanReportBuilder.

        Args:
            validators: Component for retrieving issue-specific messages.
        """
        self.validators = validators

    def build_unpacked_report(self, issue_lists: dict[str, set[str]], xse_acronym: str) -> str:
        """
        Build report for unpacked (loose) mod file scan.

        Generates a formatted report for unpacked mod file scanning results,
        including headers and categorized issues such as cleanup items,
        texture problems, sound format issues, etc.

        Args:
            issue_lists: Dictionary of issue sets by category.
            xse_acronym: XSE acronym (e.g., "F4SE", "SKSE") for issue messages.

        Returns:
            Formatted scan report as string.

        Example:
            >>> builder = ScanReportBuilder(validators)
            >>> issues = {"tex_frmt": {"texture1.tga", "texture2.png"}}
            >>> report = builder.build_unpacked_report(issues, "F4SE")
            >>> "RESULTS FROM UNPACKED" in report
            True
        """
        message_list: list[str] = [
            "=================== MOD FILES SCAN ====================\n",
            "========= RESULTS FROM UNPACKED / LOOSE FILES =========\n",
        ]

        # Build the report using StringIO for efficiency
        output = StringIO()
        issue_messages = self.validators.get_issue_messages(xse_acronym, "unpacked")

        # Write initial messages
        for msg in message_list:
            output.write(msg)

        # Add found issues
        for issue_type, items in issue_lists.items():
            if items and issue_type in issue_messages:
                for msg in issue_messages[issue_type]:
                    output.write(msg)
                for item in sorted(items):
                    output.write(item)

        return output.getvalue()

    def build_archived_report(self, issue_lists: dict[str, set[str]], xse_acronym: str) -> str:
        """
        Build report for archived (BA2) mod file scan.

        Generates a formatted report for BA2 archive scanning results,
        including headers and categorized issues such as format problems,
        texture dimension issues, sound format problems, etc.

        Args:
            issue_lists: Dictionary of issue sets by category.
            xse_acronym: XSE acronym (e.g., "F4SE", "SKSE") for issue messages.

        Returns:
            Formatted scan report as string.

        Example:
            >>> builder = ScanReportBuilder(validators)
            >>> issues = {"ba2_frmt": {"invalid.ba2"}}
            >>> report = builder.build_archived_report(issues, "F4SE")
            >>> "RESULTS FROM ARCHIVED" in report
            True
        """
        message_list: list[str] = ["\n========== RESULTS FROM ARCHIVED / BA2 FILES ==========\n"]

        # Build the report using StringIO for efficiency
        output = StringIO()

        # Write initial messages
        for msg in message_list:
            output.write(msg)

        issue_messages = self.validators.get_issue_messages(xse_acronym, "archived")

        # Add found issues
        for issue_type, items in issue_lists.items():
            if items and issue_type in issue_messages:
                for msg in issue_messages[issue_type]:
                    output.write(msg)
                for item in sorted(items):
                    output.write(item)

        return output.getvalue()

    def build_combined_report(
        self,
        unpacked_issues: dict[str, set[str]],
        archived_issues: dict[str, set[str]],
        xse_acronym: str,
    ) -> str:
        """
        Build combined report for both unpacked and archived scans.

        Generates a comprehensive report combining results from both unpacked
        (loose) file scanning and archived (BA2) file scanning. This is useful
        when both scan types are run together.

        Args:
            unpacked_issues: Dictionary of issue sets from unpacked scan.
            archived_issues: Dictionary of issue sets from archived scan.
            xse_acronym: XSE acronym (e.g., "F4SE", "SKSE") for issue messages.

        Returns:
            Combined formatted scan report as string.

        Example:
            >>> builder = ScanReportBuilder(validators)
            >>> unpacked = {"tex_frmt": {"texture.tga"}}
            >>> archived = {"ba2_frmt": {"invalid.ba2"}}
            >>> report = builder.build_combined_report(unpacked, archived, "F4SE")
            >>> "UNPACKED" in report and "ARCHIVED" in report
            True
        """
        unpacked_report = self.build_unpacked_report(unpacked_issues, xse_acronym)
        archived_report = self.build_archived_report(archived_issues, xse_acronym)
        return unpacked_report + archived_report
