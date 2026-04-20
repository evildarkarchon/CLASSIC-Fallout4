"""Generate SHA256 hash file for CLASSIC Fallout4 database."""

import hashlib
from pathlib import Path

fo4 = Path(f"{Path(__file__).parent}/databases/CLASSIC Fallout4.yaml").read_bytes()
Path(f"{Path(__file__).parent}/databases/CLASSIC Fallout4.yaml.sha256").write_text(
    hashlib.sha256(fo4).hexdigest(), encoding="utf-8"
)
mainyaml = Path(f"{Path(__file__).parent}/databases/CLASSIC Main.yaml").read_bytes()
Path(f"{Path(__file__).parent}/databases/CLASSIC Main.yaml.sha256").write_text(
    hashlib.sha256(mainyaml).hexdigest(), encoding="utf-8"
)
