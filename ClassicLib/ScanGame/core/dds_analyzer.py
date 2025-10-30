"""Enhanced DDS texture file analyzer with optional library support.

This module provides advanced DDS analysis capabilities beyond basic validation,
with support for optional third-party libraries for deeper inspection.
Falls back to basic validation if libraries are unavailable.
"""

from __future__ import annotations

import asyncio
import struct
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

# Fix for Python 3.8+ compatibility with pyffi
# time.clock() was removed in Python 3.8, replace with time.perf_counter()
if not hasattr(time, 'clock'):
    time.clock = time.perf_counter

# Try to import optional DDS libraries
try:
    from pyffi.formats.dds import DdsFormat
    HAS_PYFFI = True
except ImportError:
    HAS_PYFFI = False

try:
    from PIL import Image
    # Check if DDS plugin is available
    Image.init()
    HAS_PIL_DDS = "DDS" in Image.registered_extensions().values()
except ImportError:
    HAS_PIL_DDS = False


class DDSFlags(IntEnum):
    """DDS header flags constants."""
    CAPS = 0x1
    HEIGHT = 0x2
    WIDTH = 0x4
    PITCH = 0x8
    PIXELFORMAT = 0x1000
    MIPMAPCOUNT = 0x20000
    LINEARSIZE = 0x80000
    DEPTH = 0x800000


class DDSPixelFlags(IntEnum):
    """DDS pixel format flags."""
    ALPHAPIXELS = 0x1
    ALPHA = 0x2
    FOURCC = 0x4
    RGB = 0x40
    YUV = 0x200
    LUMINANCE = 0x20000


@dataclass
class DDSInfo:
    """Comprehensive DDS file information."""
    width: int
    height: int
    depth: int = 1
    mipmap_count: int = 1
    format_fourcc: str | None = None
    is_compressed: bool = False
    has_alpha: bool = False
    is_dx10: bool = False
    is_cubemap: bool = False
    is_volume: bool = False
    pixel_format: str = "Unknown"
    file_size: int = 0

    @property
    def is_power_of_2(self) -> bool:
        """
        Checks if both the width and height are powers of 2.

        This property evaluates whether the `width` and `height` attributes of the
        instance are powers of 2. The determination is made using a helper function.

        Returns:
            bool: True if both `width` and `height` are powers of 2, otherwise False.
        """
        def is_pow2(n: int) -> bool:
            return n > 0 and (n & (n - 1)) == 0
        return is_pow2(self.width) and is_pow2(self.height)

    @property
    def is_bc_compatible(self) -> bool:
        """
        Checks if the dimensions are block compression (BC) compatible.

        Block compression compatibility is determined by verifying whether both
        the width and height are divisible by 4.

        Returns:
            bool: True if both the width and height are divisible by 4, indicating
            BC compatibility; otherwise, False.
        """
        return self.width % 4 == 0 and self.height % 4 == 0

    @property
    def aspect_ratio(self) -> float:
        """
        Gets the aspect ratio of an object based on its width and height.

        Calculates the ratio of the width to the height of the object. If the height
        is zero, the aspect ratio will default to 0 to avoid division by zero error.

        Returns:
            float: The computed aspect ratio, or 0 if height is zero.
        """
        return self.width / self.height if self.height > 0 else 0

    @property
    def total_pixels(self) -> int:
        """
        Calculates the total number of pixels considering width, height, mipmap
        levels, and depth.

        This property computes the total number of pixels for an object
        accounting for different mipmap levels and the specified depth of the
        data. The method iteratively calculates the contribution of each mipmap
        level to the total pixel count.

        Returns:
            int: The calculated total number of pixels, considering all
            mipmap levels and depth.
        """
        pixels = 0
        w, h = self.width, self.height
        for _ in range(self.mipmap_count):
            pixels += w * h
            w = max(1, w // 2)
            h = max(1, h // 2)
        return pixels * self.depth


class EnhancedDDSAnalyzer:
    """Advanced DDS texture analyzer with multiple backend support."""

    # Common BC/DXT format FourCC codes
    BC_FORMATS = {
        b"DXT1": "BC1/DXT1 (4bpp, 1-bit alpha)",
        b"DXT2": "BC2/DXT2 (8bpp, premult alpha)",
        b"DXT3": "BC2/DXT3 (8bpp, explicit alpha)",
        b"DXT4": "BC3/DXT4 (8bpp, premult alpha)",
        b"DXT5": "BC3/DXT5 (8bpp, interpolated alpha)",
        b"BC4U": "BC4 Unsigned (4bpp, single channel)",
        b"BC4S": "BC4 Signed (4bpp, single channel)",
        b"BC5U": "BC5 Unsigned (8bpp, two channels)",
        b"BC5S": "BC5 Signed (8bpp, two channels)",
        b"DX10": "DX10 Extended Header",
    }

    def __init__(self, use_libraries: bool = True) -> None:
        """
        Initializes an instance of the class with optional library usage.

        Args:
            use_libraries: Determines whether to use the libraries. Defaults to True.
        """
        self.use_libraries = use_libraries
        self._has_warned_libraries = False

    def analyze_file(self, file_path: Path) -> DDSInfo | None:
        """
        Analyzes a file to extract DDS (DirectDraw Surface) file information. The method attempts to parse
        and retrieve data from the specified file using different approaches: library-based analysis
        (PyFFI or PIL DDS plugin) if available, falling back to manual parsing if necessary.

        Args:
            file_path (Path): Path object representing the location of the file to analyze.

        Returns:
            DDSInfo | None: Returns an instance of DDSInfo containing the extracted file information
            if successful, or None if the file could not be analyzed or if it does not exist
            or is smaller than 128 bytes.
        """
        if not file_path.exists() or file_path.stat().st_size < 128:
            return None

        # Try library-based analysis first if available
        if self.use_libraries:
            if HAS_PYFFI:
                result = self._analyze_with_pyffi(file_path)
                if result:
                    return result
            elif HAS_PIL_DDS:
                result = self._analyze_with_pil(file_path)
                if result:
                    return result

        # Fall back to manual parsing
        return self._analyze_manual(file_path)

    def _analyze_manual(self, file_path: Path) -> DDSInfo | None:
        """
        Analyzes a DDS (DirectDraw Surface) file for various properties such as dimensions, format, and capabilities.
        This function reads the DDS file header to extract this information and determines flags like whether the
        file is compressed, has alpha channels, is a cubemap, or uses extended DX10 formats.

        Args:
            file_path (Path): Path to the DDS file.

        Returns:
            DDSInfo | None: A DDSInfo object containing details about the DDS file or None if the file is not valid
            or fails to parse.
        """
        try:
            with Path(file_path).open("rb") as f:
                # Check magic number
                magic = f.read(4)
                if magic != b"DDS ":
                    return None

                # Read DDS header (124 bytes after magic)
                header = f.read(124)
                if len(header) < 124:
                    return None

                # Parse header fields
                dwSize = struct.unpack("<I", header[0:4])[0]
                if dwSize != 124:
                    return None

                dwFlags = struct.unpack("<I", header[4:8])[0]
                dwHeight = struct.unpack("<I", header[8:12])[0]
                dwWidth = struct.unpack("<I", header[12:16])[0]
                dwPitchOrLinearSize = struct.unpack("<I", header[16:20])[0]
                dwDepth = struct.unpack("<I", header[20:24])[0] if dwFlags & DDSFlags.DEPTH else 1
                dwMipMapCount = struct.unpack("<I", header[24:28])[0] if dwFlags & DDSFlags.MIPMAPCOUNT else 1

                # Parse pixel format (32 bytes at offset 76)
                pf_offset = 72  # 76 - 4 (we already read magic)
                pf_size = struct.unpack("<I", header[pf_offset:pf_offset + 4])[0]
                if pf_size != 32:
                    return None

                pf_flags = struct.unpack("<I", header[pf_offset + 4:pf_offset + 8])[0]
                fourcc = header[pf_offset + 8:pf_offset + 12] if pf_flags & DDSPixelFlags.FOURCC else None

                # Parse caps to detect cubemap/volume
                caps1 = struct.unpack("<I", header[104:108])[0]
                caps2 = struct.unpack("<I", header[108:112])[0]

                is_cubemap = bool(caps2 & 0x200)  # DDSCAPS2_CUBEMAP
                is_volume = bool(caps2 & 0x200000)  # DDSCAPS2_VOLUME

                # Determine format
                pixel_format = "Unknown"
                is_compressed = False
                has_alpha = bool(pf_flags & DDSPixelFlags.ALPHAPIXELS)
                is_dx10 = False

                if fourcc:
                    is_compressed = True
                    if fourcc == b"DX10":
                        is_dx10 = True
                        pixel_format = "DX10 Extended Format"
                    elif fourcc in self.BC_FORMATS:
                        pixel_format = self.BC_FORMATS[fourcc]
                    else:
                        pixel_format = f"FourCC: {fourcc.decode('ascii', errors='replace')}"
                elif pf_flags & DDSPixelFlags.RGB:
                    rgb_bit_count = struct.unpack("<I", header[pf_offset + 12:pf_offset + 16])[0]
                    pixel_format = f"RGB{rgb_bit_count}"
                    if has_alpha:
                        pixel_format = f"RGBA{rgb_bit_count}"
                elif pf_flags & DDSPixelFlags.LUMINANCE:
                    pixel_format = "Luminance"

                return DDSInfo(
                    width=dwWidth,
                    height=dwHeight,
                    depth=dwDepth,
                    mipmap_count=dwMipMapCount,
                    format_fourcc=fourcc.decode("ascii", errors="replace") if fourcc else None,
                    is_compressed=is_compressed,
                    has_alpha=has_alpha,
                    is_dx10=is_dx10,
                    is_cubemap=is_cubemap,
                    is_volume=is_volume,
                    pixel_format=pixel_format,
                    file_size=file_path.stat().st_size
                )

        except (OSError, struct.error):
            return None

    def _analyze_with_pyffi(self, file_path: Path) -> DDSInfo | None:
        """
        Analyzes a DDS file using PyFFI to extract detailed information if available.

        This function uses the PyFFI library to read the contents of a DDS (DirectDraw
        Surface) file and extracts detailed information such as its dimensions, format,
        compression, and other metadata. If PyFFI is not available, or an error occurs
        during analysis, the function returns None.

        Args:
            file_path (Path): The path to the DDS file to be analyzed.

        Returns:
            DDSInfo | None: An instance of DDSInfo containing the extracted metadata,
            or None if the analysis fails or PyFFI is unavailable.
        """
        if not HAS_PYFFI:
            return None

        try:
            dds = DdsFormat.Data()
            with Path(file_path).open("rb") as stream:
                dds.read(stream)

            # Extract detailed information from PyFFI
            header = dds.header
            return DDSInfo(
                width=header.width,
                height=header.height,
                depth=header.depth if header.depth > 0 else 1,
                mipmap_count=header.mipmap_count if header.mipmap_count > 0 else 1,
                format_fourcc=header.pixel_format.four_cc.decode("ascii", errors="replace") if header.pixel_format.four_cc else None,
                is_compressed=bool(header.pixel_format.flags & 0x4),  # DDPF_FOURCC
                has_alpha=bool(header.pixel_format.flags & 0x1),  # DDPF_ALPHAPIXELS
                is_dx10=header.pixel_format.four_cc == b"DX10" if header.pixel_format.four_cc else False,
                is_cubemap=bool(header.caps_2 & 0x200),  # DDSCAPS2_CUBEMAP
                is_volume=bool(header.caps_2 & 0x200000),  # DDSCAPS2_VOLUME
                pixel_format=self._get_pyffi_format_name(header),
                file_size=file_path.stat().st_size
            )
        except Exception:
            return None

    def _get_pyffi_format_name(self, header) -> str:
        """
        Determines the PyFFI format name based on the given pixel format header.

        This function analyzes the provided header's pixel format information and
        returns a string representing the corresponding PyFFI format name. It
        accounts for FourCC codes, RGB bit counts, and flags to determine the
        appropriate format. If the format is not recognized, the function returns
        "Unknown".

        Args:
            header: The header containing pixel format information. This must
                include pixel format data, including the FourCC code, RGB bit count,
                and format flags.

        Returns:
            str: The PyFFI format name derived from the input header.

        """
        pf = header.pixel_format
        if pf.four_cc:
            fourcc = pf.four_cc
            if fourcc in self.BC_FORMATS:
                return self.BC_FORMATS[fourcc]
            return f"FourCC: {fourcc.decode('ascii', errors='replace')}"
        if pf.flags & 0x40:  # RGB
            return f"RGB{pf.rgb_bit_count}"
        return "Unknown"

    def _analyze_with_pil(self, file_path: Path) -> DDSInfo | None:
        """
        Analyzes a DDS (DirectDraw Surface) file using the PIL library to extract metadata.

        This method attempts to open and analyze the given DDS file using the Pillow (PIL) library to
        extract additional information such as alpha channel presence and pixel format. If the library
        is unavailable or the file cannot be opened/analyzed, it gracefully handles the issue.

        Args:
            file_path (Path): The path to the DDS file to analyze.

        Returns:
            DDSInfo | None: A DDSInfo object containing metadata about the DDS file if the analysis is
            successful, or None if the analysis fails or Pillow (PIL) is not available.
        """
        if not HAS_PIL_DDS:
            return None

        try:
            with Image.open(file_path) as img:
                # Pillow provides basic info, we need to read header for more
                info = self._analyze_manual(file_path)
                if info:
                    # Enhance with PIL data
                    info.has_alpha = img.mode in ("RGBA", "LA")
                    # PIL can sometimes provide format info
                    if hasattr(img, "format_description"):
                        info.pixel_format = img.format_description
                return info
        except Exception:
            return None

    async def analyze_file_async(self, file_path: Path) -> DDSInfo | None:
        """
        Asynchronously analyzes a file and returns detailed diagnostic information about it.

        This method offloads the file analysis process to a dedicated thread,
        ensuring non-blocking behavior for the main application logic.

        Args:
            file_path (Path): The path to the file that needs to be analyzed.

        Returns:
            DDSInfo | None: An object containing diagnostic details about the file
            if analysis is successful, or None if the file cannot be analyzed.

        Raises:
            FileNotFoundError: If the file specified by the path does not exist.
            Exception: For any other errors that occur during the analysis process.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.analyze_file, file_path)

    def validate_for_game(self, info: DDSInfo, game: str = "Fallout4") -> list[str]:
        """
        Validates the given DDS texture information against common requirements and game-specific
        criteria. This function ensures that the provided DDS texture meets the compatibility
        and performance expectations for general use and the specified game.

        Args:
            info (DDSInfo): The DDS texture information to be validated.
            game (str): The name of the target game for validation. Defaults to "Fallout4".

        Returns:
            list[str]: A list of issues found during validation. Each issue is a string describing
            the specific problem.
        """
        issues = []

        # Common validations
        if not info.is_power_of_2 and info.mipmap_count > 1:
            issues.append("Non-power-of-2 dimensions with mipmaps")

        if info.is_compressed and not info.is_bc_compatible:
            issues.append(f"BC compressed format requires dimensions multiple of 4 (got {info.width}x{info.height})")

        if info.width > 8192 or info.height > 8192:
            issues.append("Exceeds recommended maximum dimensions (8192x8192)")

        # Game-specific checks
        if game == "Fallout4":
            # Fallout 4 specific texture requirements
            if info.width > 4096 or info.height > 4096:
                issues.append("Fallout 4 performs better with textures ≤4096x4096")

            if info.format_fourcc == "DXT1" and info.has_alpha:
                issues.append("DXT1 with alpha may cause transparency issues")

            if not info.is_compressed and info.width * info.height > 1024 * 1024:
                issues.append("Large uncompressed texture may cause performance issues")

        return issues


def get_analyzer() -> EnhancedDDSAnalyzer:
    """
    Initializes and returns an instance of EnhancedDDSAnalyzer while logging the available
    backends for DDS analysis. The function checks for the availability of specific backends
    and logs them if they are present.

    Returns:
        EnhancedDDSAnalyzer: An instance of the EnhancedDDSAnalyzer class.

    Raises:
        None
    """
    analyzer = EnhancedDDSAnalyzer()

    # Log available backends once
    available_backends = []
    if HAS_PYFFI:
        available_backends.append("PyFFI")
    if HAS_PIL_DDS:
        available_backends.append("Pillow-DDS")

    if available_backends:
        import logging
        logging.debug(f"DDS Analyzer using: {', '.join(available_backends)}")

    return analyzer


# Convenience function for backward compatibility
def analyze_dds(file_path: Path) -> DDSInfo | None:
    """
    Analyzes a DDS (DirectDraw Surface) file for relevant information.

    The function uses an analyzer to examine the contents of the provided DDS file
    and extract relevant information if the file is valid. If the analysis is
    unsuccessful or the file is not a valid DDS, the function will return None.

    Args:
        file_path (Path): Path to the DDS file to be analyzed.

    Returns:
        DDSInfo | None: An object containing extracted information about the DDS
        file if the analysis is successful; otherwise, None.
    """
    analyzer = get_analyzer()
    return analyzer.analyze_file(file_path)