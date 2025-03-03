from pathlib import Path

from CLASSIC_ScanGame import calculate_file_hash

data_dir = Path(__file__).parent

Path(f"{data_dir}/databases/CLASSIC Fallout4.yaml.sha256").write_text(calculate_file_hash(Path(f"{data_dir}/databases/CLASSIC Fallout4.yaml")))
"""with Path(f"{Path(__file__).parent}/databases/CLASSIC Fallout4.yaml").open("rb") as f:
    data = f.read()
    Path(f"{Path(__file__).parent}/databases/CLASSIC Fallout4.yaml.sha256").write_text(hashlib.sha256(data).hexdigest())"""