//! Pure auxiliary domain observations through canonical Rust public operations.

use super::{RunnerResult, invalid, text};
use serde_json::{Value, json};
use std::path::Path;

/// Preserve the actual Result value or the domain error's public display text.
fn result<T: std::fmt::Display, E: std::fmt::Display>(value: Result<T, E>) -> Value {
    match value {
        Ok(value) => json!({"value": value.to_string(), "error": null}),
        Err(error) => json!({"value": null, "error": error.to_string()}),
    }
}

/// Execute fixture-selected owner operations without access to authored expectations.
pub(super) fn execute(family: &str, fixture: &Value) -> RunnerResult<Value> {
    let request = &fixture["request"];
    if family.starts_with("version-") && request.get("operation").is_some() {
        return super::version_extended::execute(fixture);
    }
    match family {
        "web-operations" => {
            use classic_web_core as web;
            let url = text(&request["url"])?;
            let path = text(&request["path"])?;
            let pairs = request["params"]
                .as_array()
                .ok_or_else(|| invalid("query pairs missing"))?
                .iter()
                .map(|pair| Ok((text(&pair[0])?, text(&pair[1])?)))
                .collect::<RunnerResult<Vec<_>>>()?;
            let borrowed = pairs
                .iter()
                .map(|(key, value)| (key.as_str(), value.as_str()))
                .collect::<Vec<_>>();
            Ok(
                json!({"valid": web::is_valid_url(&url), "validated": result(web::validate_url(&url)),
                "domain": result(web::extract_domain(&url)), "joined": result(web::join_url(&url, &path)),
                "query": result(web::build_url_with_query(&url, &borrowed))}),
            )
        }
        "resource-operations" => {
            use classic_resource_core as resource;
            let path = text(&request["path"])?;
            let kind: resource::ResourceType = text(&request["type"])?.parse()?;
            let info = resource::ResourceInfo::new(path.clone().into());
            let type_catalog = request["types"]
                .as_array()
                .ok_or_else(|| invalid("resource types missing"))?
                .iter()
                .map(|name| {
                    let kind: resource::ResourceType = text(name)?.parse()?;
                    Ok(kind.as_str())
                })
                .collect::<RunnerResult<Vec<_>>>()?;
            let temporary = tempfile::tempdir()?;
            let root = temporary.path();
            for (relative, content) in fixture["files"]
                .as_object()
                .ok_or_else(|| invalid("resource files missing"))?
            {
                let target = owned(root, relative)?;
                std::fs::create_dir_all(
                    target
                        .parent()
                        .ok_or_else(|| invalid("resource parent missing"))?,
                )?;
                std::fs::write(target, text(content)?)?;
            }
            let mut resources = resource::enumerate_resources(root, None)?.into_iter().map(|item| {
                Ok(json!({"path": item.path.strip_prefix(root)?.to_string_lossy().replace('\\', "/"), "type": item.resource_type.as_str(), "size": item.size}))
            }).collect::<RunnerResult<Vec<_>>>()?;
            resources.sort_by(|left, right| left["path"].as_str().cmp(&right["path"].as_str()));
            let first = resources
                .first()
                .ok_or_else(|| invalid("resource fixture must contain a supported file"))?;
            let sized = resource::ResourceInfo::with_size(
                text(&first["path"])?.into(),
                first["size"]
                    .as_u64()
                    .ok_or_else(|| invalid("resource size missing"))?,
            );
            let mut counts = resource::count_resources_by_type(root)?
                .into_iter()
                .map(|(kind, count)| json!({"type": kind.as_str(), "count": count}))
                .collect::<Vec<_>>();
            counts.sort_by(|left, right| left["type"].as_str().cmp(&right["type"].as_str()));
            let validation = request["validate"]
                .as_array()
                .ok_or_else(|| invalid("resource validation missing"))?
                .iter()
                .map(|relative| {
                    let relative = text(relative)?;
                    let error = match resource::validate_resource(&owned(root, &relative)?) {
                        Ok(()) => None,
                        Err(resource::ResourceError::NotFound(_)) => Some("not_found"),
                        Err(resource::ResourceError::InvalidType(_)) => Some("invalid_type"),
                        Err(error) => return Err(error.into()),
                    };
                    Ok(json!({"path": relative, "error": error}))
                })
                .collect::<RunnerResult<Vec<_>>>()?;
            Ok(
                json!({"detected": resource::detect_resource_type(Path::new(&path)).as_str(),
                "supported": resource::is_supported_resource(Path::new(&path)), "parsed": kind.as_str(), "typeCatalog": type_catalog,
                "extensions": kind.extensions(), "info": {"path": info.path, "type": info.resource_type.as_str(), "size": info.size},
                "resources": resources, "counts": counts, "validation": validation, "files": resource_files(root, root)?,
                "sizedInfo": {"path": sized.path, "type": sized.resource_type.as_str(), "size": sized.size}}),
            )
        }
        "version-operations" => {
            use classic_version_core as version;
            let input = text(&request["version"])?;
            let parsed = version::parse_version(&input);
            let (comparison, formatted) = match &parsed {
                Ok(native) => {
                    let other = version::parse_version(&text(&request["other"])?)?;
                    let order = match version::compare_versions(native, &other) {
                        std::cmp::Ordering::Less => -1,
                        std::cmp::Ordering::Equal => 0,
                        std::cmp::Ordering::Greater => 1,
                    };
                    (Some(order), Some(version::format_version(native, None)))
                }
                Err(_) => (None, None),
            };
            Ok(
                json!({"parsed": result(parsed), "optional": version::try_parse_version(&input).map(|value| value.to_string()),
                "comparison": comparison, "formatted": formatted}),
            )
        }
        _ => Err(invalid("unsupported auxiliary owner domain").into()),
    }
}

/// Refuse path escapes before any resource fixture file is created.
fn owned(root: &Path, relative: &str) -> RunnerResult<std::path::PathBuf> {
    if relative.is_empty()
        || relative.contains(['\\', ':'])
        || relative
            .split('/')
            .any(|part| matches!(part, "" | "." | ".."))
    {
        return Err(invalid("resource fixture path must be contained").into());
    }
    Ok(root.join(relative))
}

/// Read all actual files, including unrecognized resources, after domain calls finish.
fn resource_files(root: &Path, directory: &Path) -> RunnerResult<Vec<Value>> {
    let mut files = Vec::new();
    for entry in std::fs::read_dir(directory)? {
        let entry = entry?;
        let kind = entry.file_type()?;
        if kind.is_dir() {
            files.extend(resource_files(root, &entry.path())?);
        } else if kind.is_file() {
            let bytes = std::fs::read(entry.path())?;
            let hex = bytes
                .iter()
                .map(|byte| format!("{byte:02x}"))
                .collect::<String>();
            files.push(json!({"path": entry.path().strip_prefix(root)?.to_string_lossy().replace('\\', "/"), "hex": hex}));
        } else {
            return Err(invalid("unexpected symlink or special file in resource workspace").into());
        }
    }
    files.sort_by(|left, right| left["path"].as_str().cmp(&right["path"].as_str()));
    Ok(files)
}
