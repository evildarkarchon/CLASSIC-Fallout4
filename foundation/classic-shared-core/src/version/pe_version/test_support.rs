//! Test-only PE synthesis for exercising [`extract_pe_version`](super::extract_pe_version).
//!
//! Compiled for this crate's own tests and, behind the `test-support` feature, for
//! other crates' tests. Production builds never enable the feature.
//!
//! Real binaries are not committed as fixtures, and a zero-byte stand-in has no
//! version resource. So tests that need a version-stamped `.exe` or `.dll` write
//! the bytes built here instead.

/// Section RVA of the single `.rsrc` section.
const SECTION_RVA: u32 = 0x1000;
/// File alignment, and the file offset of the `.rsrc` section's raw data.
const FILE_ALIGNMENT: usize = 0x200;
/// File offset of the NT headers (`e_lfanew`).
const PE_OFFSET: usize = 0x40;
/// Offset of the `VS_VERSIONINFO` blob inside the `.rsrc` section, just past the
/// three resource directories and the data entry.
const VERSION_INFO_OFFSET: usize = 0x58;

/// Build a minimal PE32+ image whose only content is a `VS_VERSIONINFO` resource
/// stamped with `file_version` as `(major, minor, patch, build)`.
///
/// The image has no code and cannot be loaded. It carries just enough header
/// structure for PE parsers to reach `RT_VERSION/1/0x0409`, and the same version
/// is written as both the file version and the product version.
#[must_use]
pub fn versioned_pe_bytes(file_version: (u16, u16, u16, u16)) -> Vec<u8> {
    let rsrc = resource_section(file_version);
    let rsrc_len = u32::try_from(rsrc.len()).expect("resource section fits in u32");
    let raw_size = rsrc.len().next_multiple_of(FILE_ALIGNMENT);
    let raw_size_u32 = u32::try_from(raw_size).expect("raw size fits in u32");
    let file_alignment = u32::try_from(FILE_ALIGNMENT).expect("alignment fits in u32");

    let mut image = vec![0u8; FILE_ALIGNMENT + raw_size];

    // DOS header: PE parsers only read the magic and `e_lfanew`.
    image[0..2].copy_from_slice(b"MZ");
    put_u32(
        &mut image,
        0x3C,
        u32::try_from(PE_OFFSET).expect("offset fits"),
    );

    let mut at = PE_OFFSET;
    image[at..at + 4].copy_from_slice(b"PE\0\0");
    at += 4;

    // COFF file header.
    put_u16(&mut image, at, 0x8664); // Machine: AMD64
    put_u16(&mut image, at + 2, 1); // NumberOfSections
    put_u16(&mut image, at + 16, 240); // SizeOfOptionalHeader (PE32+)
    put_u16(&mut image, at + 18, 0x0022); // EXECUTABLE_IMAGE | LARGE_ADDRESS_AWARE
    at += 20;

    // PE32+ optional header; unlisted fields stay zero.
    let opt = at;
    put_u16(&mut image, opt, 0x020B); // Magic: PE32+
    put_u32(&mut image, opt + 8, raw_size_u32); // SizeOfInitializedData
    put_u64(&mut image, opt + 24, 0x1_4000_0000); // ImageBase
    put_u32(&mut image, opt + 32, SECTION_RVA); // SectionAlignment
    put_u32(&mut image, opt + 36, file_alignment); // FileAlignment
    put_u16(&mut image, opt + 40, 6); // MajorOperatingSystemVersion
    put_u16(&mut image, opt + 48, 6); // MajorSubsystemVersion
    put_u32(
        &mut image,
        opt + 56,
        SECTION_RVA + rsrc_len.next_multiple_of(SECTION_RVA),
    ); // SizeOfImage
    put_u32(&mut image, opt + 60, file_alignment); // SizeOfHeaders
    put_u16(&mut image, opt + 68, 3); // Subsystem: Windows console
    put_u32(&mut image, opt + 108, 16); // NumberOfRvaAndSizes
    // Data directory 2: the resource table.
    put_u32(&mut image, opt + 112 + 2 * 8, SECTION_RVA);
    put_u32(&mut image, opt + 112 + 2 * 8 + 4, rsrc_len);
    at = opt + 240;

    // The single `.rsrc` section header.
    image[at..at + 8].copy_from_slice(b".rsrc\0\0\0");
    put_u32(&mut image, at + 8, rsrc_len); // VirtualSize
    put_u32(&mut image, at + 12, SECTION_RVA); // VirtualAddress
    put_u32(&mut image, at + 16, raw_size_u32); // SizeOfRawData
    put_u32(&mut image, at + 20, file_alignment); // PointerToRawData
    put_u32(&mut image, at + 36, 0x4000_0040); // INITIALIZED_DATA | MEM_READ

    image[FILE_ALIGNMENT..FILE_ALIGNMENT + rsrc.len()].copy_from_slice(&rsrc);
    image
}

/// Build the `.rsrc` section: `RT_VERSION` -> ID 1 -> language 0x0409 -> data entry
/// -> `VS_VERSIONINFO`, each directory holding exactly one ID entry.
fn resource_section(file_version: (u16, u16, u16, u16)) -> Vec<u8> {
    const RT_VERSION: u32 = 16;
    // High bit of OffsetToData marks a subdirectory rather than a data entry.
    const SUBDIRECTORY: u32 = 0x8000_0000;

    let version_info = version_info_resource(file_version);
    let mut rsrc = vec![0u8; VERSION_INFO_OFFSET];
    write_single_entry_directory(&mut rsrc, 0x00, RT_VERSION, SUBDIRECTORY | 0x18);
    write_single_entry_directory(&mut rsrc, 0x18, 1, SUBDIRECTORY | 0x30);
    write_single_entry_directory(&mut rsrc, 0x30, 0x0409, 0x48);
    // IMAGE_RESOURCE_DATA_ENTRY: OffsetToData is an RVA, not a section offset.
    let blob_offset = u32::try_from(VERSION_INFO_OFFSET).expect("offset fits");
    put_u32(&mut rsrc, 0x48, SECTION_RVA + blob_offset);
    put_u32(
        &mut rsrc,
        0x4C,
        u32::try_from(version_info.len()).expect("blob fits"),
    );
    rsrc.extend_from_slice(&version_info);
    rsrc
}

/// Write an `IMAGE_RESOURCE_DIRECTORY` with one ID entry pointing at `target`.
fn write_single_entry_directory(buf: &mut [u8], at: usize, id: u32, target: u32) {
    // Characteristics, TimeDateStamp, versions and NumberOfNamedEntries stay zero.
    put_u16(buf, at + 14, 1); // NumberOfIdEntries
    put_u32(buf, at + 16, id);
    put_u32(buf, at + 20, target);
}

/// Build a `VS_VERSIONINFO` blob holding only the `VS_FIXEDFILEINFO` value.
fn version_info_resource((major, minor, patch, build): (u16, u16, u16, u16)) -> Vec<u8> {
    let most_significant = (u32::from(major) << 16) | u32::from(minor);
    let least_significant = (u32::from(patch) << 16) | u32::from(build);

    let mut blob = Vec::with_capacity(92);
    blob.extend_from_slice(&0u16.to_le_bytes()); // wLength, patched below
    blob.extend_from_slice(&52u16.to_le_bytes()); // wValueLength: sizeof(VS_FIXEDFILEINFO)
    blob.extend_from_slice(&0u16.to_le_bytes()); // wType: binary
    for unit in "VS_VERSION_INFO\0".encode_utf16() {
        blob.extend_from_slice(&unit.to_le_bytes());
    }
    blob.extend_from_slice(&[0u8; 2]); // pad the Value to a 32-bit boundary
    for field in [
        0xFEEF_04BD,       // dwSignature
        0x0001_0000,       // dwStrucVersion
        most_significant,  // dwFileVersionMS
        least_significant, // dwFileVersionLS
        most_significant,  // dwProductVersionMS
        least_significant, // dwProductVersionLS
        0x3F,              // dwFileFlagsMask
        0,                 // dwFileFlags
        0x0004_0004,       // dwFileOS: VOS_NT_WINDOWS32
        1,                 // dwFileType: VFT_APP
        0,                 // dwFileSubtype
        0,                 // dwFileDateMS
        0,                 // dwFileDateLS
    ] {
        blob.extend_from_slice(&u32::to_le_bytes(field));
    }
    let length = u16::try_from(blob.len()).expect("blob fits in u16");
    blob[0..2].copy_from_slice(&length.to_le_bytes());
    blob
}

fn put_u16(buf: &mut [u8], at: usize, value: u16) {
    buf[at..at + 2].copy_from_slice(&value.to_le_bytes());
}

fn put_u32(buf: &mut [u8], at: usize, value: u32) {
    buf[at..at + 4].copy_from_slice(&value.to_le_bytes());
}

fn put_u64(buf: &mut [u8], at: usize, value: u64) {
    buf[at..at + 8].copy_from_slice(&value.to_le_bytes());
}
