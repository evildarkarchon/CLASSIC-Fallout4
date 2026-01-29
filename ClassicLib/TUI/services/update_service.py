"""Update Service for CLASSIC TUI.

Async update checking using existing backend.
"""

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.update import UpdateCheckError, is_latest_version


class UpdateService:
    """Service for checking application updates.

    Wraps existing update checking functionality for TUI use.
    Provides async methods compatible with Textual's Worker API.
    """

    @staticmethod
    async def check_for_updates(explicit: bool = False) -> tuple[bool, str | None]:
        """Check if the application is up to date.

        Args:
            explicit: If True, this is a user-triggered check that should
                always show results. If False, results may be suppressed
                for up-to-date status.

        Returns:
            Tuple of (is_latest, error_message).
            - is_latest: True if current version is the latest.
            - error_message: Error description if check failed, None otherwise.

        """
        # Check if pre-release
        if GlobalRegistry.get(GlobalRegistry.Keys.IS_PRERELEASE):
            return True, "Pre-release version, update check skipped."

        try:
            is_latest = await is_latest_version(quiet=True, gui_request=explicit)
        except UpdateCheckError as e:
            return False, str(e)
        except (RuntimeError, OSError, ValueError) as e:
            return False, f"Unexpected error during update check: {e}"
        else:
            return is_latest, None
