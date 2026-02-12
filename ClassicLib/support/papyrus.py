"""Papyrus log file processor and analyzer.

Thin wrapper that delegates to the Rust ``classic_scanlog.papyrus_logging``
function for high-performance log analysis with automatic encoding detection.

The module resolves the Papyrus log path from YAML settings and passes it
to Rust for analysis.  The Rust implementation handles streaming I/O,
encoding detection, and statistics collection (15-30x faster than Python).
"""

from pathlib import Path

from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import GlobalRegistry


def papyrus_logging() -> tuple[str, int]:
    """Analyze Papyrus log files via the Rust ``classic_scanlog`` backend.

    Resolves the Papyrus log path from YAML settings, then delegates all
    analysis work to the Rust ``papyrus_logging`` function which handles
    streaming I/O, encoding detection, and statistics collection.

    Returns:
        tuple[str, int]: A tuple containing a formatted string with log analysis
        details and the total count of dumps extracted from the log.

    """
    from ClassicLib.io.yaml import yaml_settings

    papyrus_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Docs_File_PapyrusLog")

    if papyrus_path and papyrus_path.exists():
        from classic_scanlog import papyrus_logging as rust_papyrus_logging

        logger.debug("Papyrus log analysis delegated to Rust (Streaming I/O)")
        return rust_papyrus_logging(papyrus_path)

    # Log not found -- return guidance message (no Rust call needed)
    message_output = (
        "[!] ERROR : UNABLE TO FIND *Papyrus.0.log* (LOGGING IS DISABLED OR YOU DIDN'T RUN THE GAME)\n"
        "ENABLE PAPYRUS LOGGING MANUALLY OR WITH BETHINI AND START THE GAME TO GENERATE THE LOG FILE\n"
        "BethINI Link | Use Manual Download : https://www.nexusmods.com/site/mods/631?tab=files\n"
    )
    return message_output, 0
