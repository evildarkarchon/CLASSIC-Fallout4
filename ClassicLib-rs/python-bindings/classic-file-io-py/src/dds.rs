//! Python bindings for DDS header parsing (thin PyO3 adapter)
//!
//! This module provides PyO3 bindings for the DDS header parsing functionality
//! from classic-file-io-core. It exposes a PyDDSHeader class with all validation
//! methods and properties from the Rust implementation.

use classic_file_io_core::dds::DDSHeader;
use pyo3::prelude::*;

/// Python wrapper for DDSHeader - DDS texture file header information
///
/// This class provides access to DDS texture metadata and validation methods.
/// Use this for detailed texture analysis and validation.
///
/// # Example
///
/// ```python
/// from classic_file_io import FileIOCore, DDSHeader
///
/// # Parse DDS header from bytes
/// with open("texture.dds", "rb") as f:
///     data = f.read()
///
/// header = DDSHeader.from_bytes(data)
/// if header:
///     print(f"Size: {header.width}x{header.height}")
///     print(f"Format: {header.format}")
///     print(f"Mipmaps: {header.mipmap_count}")
///
///     # Validation
///     if not header.has_power_of_2_dimensions():
///         print("Warning: Non-power-of-2 dimensions")
///     if header.is_bc_compressed() and not header.has_valid_bc_dimensions():
///         print("Error: Invalid BC compression dimensions")
/// ```
#[pyclass(name = "DDSHeader")]
#[derive(Clone)]
pub struct PyDDSHeader {
    inner: DDSHeader,
}

#[pymethods]
impl PyDDSHeader {
    /// Parse DDS header from bytes
    ///
    /// Args:
    ///     data: Raw bytes of the DDS file (at least first 128 bytes)
    ///
    /// Returns:
    ///     DDSHeader object if valid DDS file, None otherwise
    ///
    /// Example:
    ///     ```python
    ///     with open("texture.dds", "rb") as f:
    ///         header = DDSHeader.from_bytes(f.read())
    ///     ```
    #[staticmethod]
    fn from_bytes(data: &[u8]) -> PyResult<Option<Self>> {
        match DDSHeader::from_bytes(data) {
            Ok(Some(header)) => Ok(Some(PyDDSHeader { inner: header })),
            Ok(None) => Ok(None),
            Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
                "DDS parsing error: {}",
                e
            ))),
        }
    }

    /// Texture width in pixels
    #[getter]
    fn width(&self) -> u32 {
        self.inner.width
    }

    /// Texture height in pixels
    #[getter]
    fn height(&self) -> u32 {
        self.inner.height
    }

    /// Texture depth (for 3D textures, 1 for 2D textures)
    #[getter]
    fn depth(&self) -> u32 {
        self.inner.depth
    }

    /// Number of mipmap levels
    #[getter]
    fn mipmap_count(&self) -> u32 {
        self.inner.mipmap_count
    }

    /// Texture compression format (e.g., "BC7", "DXT5")
    #[getter]
    fn format(&self) -> String {
        self.inner.format.clone()
    }

    /// Check if dimensions are power of 2 (optimal for mipmaps)
    ///
    /// Returns:
    ///     True if both width and height are powers of 2
    ///
    /// Example:
    ///     ```python
    ///     if header.has_power_of_2_dimensions():
    ///         print("Optimal for mipmaps")
    ///     ```
    fn has_power_of_2_dimensions(&self) -> bool {
        self.inner.has_power_of_2_dimensions()
    }

    /// Check if dimensions are valid for BC compression (multiple of 4)
    ///
    /// Returns:
    ///     True if both width and height are multiples of 4
    ///
    /// Note:
    ///     BC-compressed textures (BC1-BC7/DXT) require dimensions that are
    ///     multiples of 4 for proper compression block alignment.
    ///
    /// Example:
    ///     ```python
    ///     if header.is_bc_compressed() and not header.has_valid_bc_dimensions():
    ///         print("ERROR: BC texture with invalid dimensions")
    ///     ```
    fn has_valid_bc_dimensions(&self) -> bool {
        self.inner.has_valid_bc_dimensions()
    }

    /// Check if dimensions are within reasonable bounds (1-16384 pixels)
    ///
    /// Returns:
    ///     True if dimensions are reasonable for game textures
    ///
    /// Example:
    ///     ```python
    ///     if not header.is_reasonable_size():
    ///         print(f"WARNING: Unusual texture size {header.width}x{header.height}")
    ///     ```
    fn is_reasonable_size(&self) -> bool {
        self.inner.is_reasonable_size()
    }

    /// Check if texture has mipmaps (mipmap_count > 1)
    ///
    /// Returns:
    ///     True if texture has mipmap levels
    ///
    /// Example:
    ///     ```python
    ///     if not header.has_mipmaps():
    ///         print("No mipmaps - may cause performance issues")
    ///     ```
    fn has_mipmaps(&self) -> bool {
        self.inner.has_mipmaps()
    }

    /// Check if format is a BC compressed format
    ///
    /// Returns:
    ///     True if format is BC1-BC7 or DXT1-DXT5
    ///
    /// Example:
    ///     ```python
    ///     if header.is_bc_compressed():
    ///         print(f"BC-compressed: {header.format}")
    ///     ```
    fn is_bc_compressed(&self) -> bool {
        self.inner.is_bc_compressed()
    }

    /// String representation showing key properties
    fn __repr__(&self) -> String {
        format!(
            "DDSHeader(width={}, height={}, depth={}, mipmaps={}, format={})",
            self.inner.width,
            self.inner.height,
            self.inner.depth,
            self.inner.mipmap_count,
            self.inner.format
        )
    }

    /// String representation for display
    fn __str__(&self) -> String {
        format!(
            "{}x{} {} (mipmaps: {})",
            self.inner.width, self.inner.height, self.inner.format, self.inner.mipmap_count
        )
    }
}
