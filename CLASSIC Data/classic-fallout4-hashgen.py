"""Generate SHA256 hash file for CLASSIC Fallout4 database."""

import hashlib
from pathlib import Path

data = Path(f"{Path(__file__).parent}/databases/CLASSIC Fallout4.yaml").read_bytes()
Path(f"{Path(__file__).parent}/databases/CLASSIC Fallout4.yaml.sha256").write_text(hashlib.sha256(data).hexdigest(), encoding="utf-8")
