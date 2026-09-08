"""Input-only public DDS header observations from native Python bindings."""

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def observe_dds_header(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Parse fixture bytes and project every public header getter and query."""
    from classic_file_io import DDSHeader

    raw = bytes(fixture["bytes"])
    if fixture.get("operation") == "files":
        import classic_file_io as native

        with tempfile.TemporaryDirectory(prefix="classic-dds-files-") as directory:
            root = Path(directory)
            path = root / "texture.dds"
            missing = root / "missing.dds"
            path.write_bytes(raw)
            io = native.FileIOCore()
            dimensions = io.read_dds_header(path)
            batch = io.read_dds_headers_batch([str(path), str(missing)])
            missing_error = None
            try:
                io.read_dds_header(missing)
            except native.RustFileIOIOError:
                # A malformed header returns None; a missing file is a distinct native I/O error.
                missing_error = "io_error"
            return {
                "dimensions": None if dimensions is None else list(dimensions),
                "batch": [
                    [Path(name).name, None if value is None else list(value)]
                    for name, value in batch.items()
                ],
                "missingError": missing_error,
                "bytes": list(path.read_bytes()),
            }
    header = DDSHeader.from_bytes(raw)
    return {
        "bytes": list(raw),
        "header": None
        if header is None
        else {
            "width": header.width,
            "height": header.height,
            "depth": header.depth,
            "mipmaps": header.mipmap_count,
            "format": header.format,
            "powerOfTwo": header.has_power_of_2_dimensions(),
            "validBcDimensions": header.has_valid_bc_dimensions(),
            "reasonableSize": header.is_reasonable_size(),
            "hasMipmaps": header.has_mipmaps(),
            "bcCompressed": header.is_bc_compressed(),
        },
    }
