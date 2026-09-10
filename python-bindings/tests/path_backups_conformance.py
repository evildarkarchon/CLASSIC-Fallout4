"""Byte-exact versioned backup observations through the Python public API."""

from pathlib import Path
from tempfile import TemporaryDirectory


def observe_path_backups(fixture):
    """Copy arbitrary bytes twice into an owned version directory and read them back."""
    from classic_path import BackupManager, XseVersion

    with TemporaryDirectory(prefix="classic-backup-") as directory:
        root = Path(directory)
        source = root / "settings.ini"
        log = root / "xse.log"
        log.write_bytes(fixture["log"].encode())
        source.write_bytes(bytes.fromhex(fixture["firstHex"]))
        manager = BackupManager(str(root / "backups"))
        initial = manager.list_versions()
        version = manager.extract_version_from_xse_log(str(log))
        explicit = XseVersion(fixture["version"])
        if (version.full_version(), version.sanitized()) != (
            explicit.full_version(),
            explicit.sanitized(),
        ):
            raise ValueError("extracted and explicit versions disagree")
        if (
            repr(explicit) != f"XseVersion('{fixture['version']}')"
            or str(explicit) != fixture["version"]
        ):
            raise ValueError("version representation lost its native value")
        created = Path(manager.create_backup(str(source), version))
        first = created.read_bytes().hex()
        source.write_bytes(bytes.fromhex(fixture["replacementHex"]))
        if Path(manager.create_backup(str(source), explicit)) != created:
            raise ValueError("same-version backup did not replace original path")
        return {
            "version": version.full_version(),
            "sanitized": version.sanitized(),
            "initial": initial,
            "versions": manager.list_versions(),
            "root": Path(manager.backup_root).relative_to(root).as_posix(),
            "directory": Path(manager.get_version_path(explicit))
            .relative_to(root)
            .as_posix(),
            "created": created.relative_to(root).as_posix(),
            "firstHex": first,
            "replacementHex": created.read_bytes().hex(),
            "files": {
                p.relative_to(root).as_posix(): p.read_bytes().hex()
                for p in root.rglob("*")
                if p.is_file()
            },
        }
