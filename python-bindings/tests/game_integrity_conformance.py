"""Public integrity checks over isolated executable and Steam marker fixtures."""

import tempfile
from pathlib import Path


def observe_integrity(fixture: dict) -> dict:
    """Observe individual, grouped, and rendered checks from the same native checker."""
    import classic_scangame

    with tempfile.TemporaryDirectory(
            prefix="classic-integrity-conformance-"
    ) as temporary:
        root = Path(temporary)
        for name, content in fixture["files"].items():
            if (
                    "\\" in name
                    or any(part in {"", ".", ".."} for part in name.split("/"))
                    or Path(name).is_absolute()
            ):
                raise ValueError("integrity fixture escaped its root")
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode())
        config = classic_scangame.IntegrityConfig(
            root / fixture["exe"], fixture["hashes"], fixture["rootName"]
        )
        if fixture["steamIni"] is not None:
            config.with_steam_ini(root / fixture["steamIni"])
        if fixture["rootWarn"] is not None:
            config.with_root_warn(fixture["rootWarn"])
        if (
                config.game_exe_path != root / fixture["exe"]
                or config.valid_exe_hashes != fixture["hashes"]
                or config.root_name != fixture["rootName"]
        ):
            raise ValueError("integrity configuration lost constructor inputs")
        if (
                config.steam_ini_path
                != (None if fixture["steamIni"] is None else root / fixture["steamIni"])
                or config.root_warn != fixture["rootWarn"]
        ):
            raise ValueError("integrity configuration lost optional inputs")
        executable = classic_scangame.CheckType.executable_version()
        location = classic_scangame.CheckType.installation_location()
        if (
                not executable.is_executable_version()
                or executable.is_installation_location()
                or not location.is_installation_location()
                or location.is_executable_version()
        ):
            raise ValueError("integrity check type identity was lost")
        checker = classic_scangame.GameIntegrityChecker(config)

        def project(value):
            """Read a public result's validity, message, and typed check identity."""
            kind = value.check_type
            return {
                "isValid": value.is_valid,
                "message": value.message,
                "checkType": "ExecutableVersion"
                if kind.is_executable_version()
                else "InstallationLocation"
                if kind.is_installation_location()
                else "unknown",
            }

        checks = [project(value) for value in checker.run_all_checks()]
        if checks != [
            project(checker.check_executable_version()),
            project(checker.check_installation_location()),
        ]:
            raise ValueError("grouped checks differ from individual public checks")
        report = checker.run_full_check()
        return {
            "checks": checks,
            "report": report,
            "files": [
                {
                    "path": path.relative_to(root).as_posix(),
                    "content": path.read_bytes().decode(),
                }
                for path in sorted(root.rglob("*"))
                if path.is_file()
            ],
        }
