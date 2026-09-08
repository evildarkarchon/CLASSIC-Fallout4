//! Input-only public DDS byte parser and validation observations.

use super::{RunnerResult, invalid};
use classic_file_io_core::dds::DDSHeader;
use serde_json::{Value, json};

/// Parses raw input bytes and projects the native fields and validation methods.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let bytes = fixture["bytes"]
        .as_array()
        .ok_or_else(|| invalid("DDS bytes must be an array"))?
        .iter()
        .map(|value| {
            value
                .as_u64()
                .and_then(|value| u8::try_from(value).ok())
                .ok_or_else(|| invalid("DDS input byte is invalid"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    if matches!(fixture["operation"].as_str(), Some("files" | "validate")) {
        let temporary = tempfile::tempdir()?;
        let path = temporary.path().join("texture.dds");
        let missing = temporary.path().join("missing.dds");
        std::fs::write(&path, &bytes)?;
        if fixture["operation"] == "files" {
            use classic_file_io_core::{FileIOCore, FileIOError};
            let io = FileIOCore::default();
            let runtime = classic_shared_core::get_runtime();
            let dimensions = runtime
                .block_on(io.read_dds_header(&path))?
                .map(|header| [header.width, header.height]);
            let batch = io
                .read_dds_headers_batch(vec![path.clone(), missing.clone()])
                .into_iter()
                .map(|(path, header)| {
                    json!([
                        path.file_name().unwrap().to_string_lossy(),
                        header.map(|header| [header.width, header.height])
                    ])
                })
                .collect::<Vec<_>>();
            let missing_error = match runtime.block_on(io.read_dds_header(&missing)) {
                Err(FileIOError::IoError(_)) => Some("io_error"),
                Err(error) => return Err(error.into()),
                Ok(_) => None,
            };
            return Ok(
                json!({"dimensions":dimensions,"batch":batch,"missingError":missing_error,"bytes":std::fs::read(path)?}),
            );
        }
        use classic_file_io_core::dds::{DDSAnalyzer, GameTarget};
        let analyzer = DDSAnalyzer::new(GameTarget::Fallout4);
        let issues = analyzer
            .validate_file(&path)
            .into_iter()
            .map(|issue| issue.message)
            .collect::<Vec<_>>();
        let batch = analyzer
            .validate_batch(&[path.clone(), missing])
            .into_iter()
            .map(|(path, issues)| {
                json!([
                    path.file_name().unwrap().to_string_lossy(),
                    issues
                        .into_iter()
                        .map(|issue| issue.message)
                        .collect::<Vec<_>>()
                ])
            })
            .collect::<Vec<_>>();
        let dimensions = fixture["dimensions"]
            .as_array()
            .ok_or_else(|| invalid("DDS dimensions must be an array"))?;
        let width = u32::try_from(
            dimensions[0]
                .as_u64()
                .ok_or_else(|| invalid("invalid width"))?,
        )?;
        let height = u32::try_from(
            dimensions[1]
                .as_u64()
                .ok_or_else(|| invalid("invalid height"))?,
        )?;
        return Ok(
            json!({"issues":issues,"batch":batch,"dimensionIssues":DDSAnalyzer::validate_dimensions(width,height).into_iter().map(|issue|issue.message).collect::<Vec<_>>(),"bytes":std::fs::read(path)?}),
        );
    }
    let header = DDSHeader::from_bytes(&bytes).map_err(|error| invalid(&error.to_string()))?;
    Ok(json!({"bytes":bytes, "header":header.map(|header| json!({
        "width":header.width,"height":header.height,"depth":header.depth,
        "mipmaps":header.mipmap_count,"format":header.format,
        "powerOfTwo":header.has_power_of_2_dimensions(),
        "validBcDimensions":header.has_valid_bc_dimensions(),
        "reasonableSize":header.is_reasonable_size(),
        "hasMipmaps":header.has_mipmaps(),"bcCompressed":header.is_bc_compressed()
    }))}))
}
