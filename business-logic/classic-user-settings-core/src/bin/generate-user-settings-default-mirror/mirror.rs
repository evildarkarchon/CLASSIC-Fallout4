//! Pure renderer, semantic checker, and literal-block replacement for the developer command.

use super::default_settings::{
    ARTICLES_TAB_DEFAULT, BACKUPS_TAB_DEFAULT, MAIN_TAB_DEFAULT, MIRROR_SETTINGS, PublishedDefault,
    RESULTS_TAB_DEFAULT, USER_SETTINGS_SCHEMA_MAJOR, USER_SETTINGS_SCHEMA_MINOR, registry_is_valid,
};
use classic_settings_core::{Yaml, parse_yaml_content};

/// Byte offsets and newline convention for the embedded literal scalar.
struct MirrorBlock {
    start: usize,
    end: usize,
    newline: &'static str,
}

/// Renders the complete compatibility document with stable ordering and guidance.
fn render_compatibility_mirror() -> String {
    debug_assert!(
        registry_is_valid(),
        "User Settings metadata registry is invalid"
    );
    debug_assert_eq!(MAIN_TAB_DEFAULT, geometry_default("main_tab"));
    debug_assert_eq!(BACKUPS_TAB_DEFAULT, geometry_default("backups_tab"));
    debug_assert_eq!(ARTICLES_TAB_DEFAULT, geometry_default("articles_tab"));
    debug_assert_eq!(RESULTS_TAB_DEFAULT, geometry_default("results_tab"));
    let mut output =
        format!("schema_version: \"{USER_SETTINGS_SCHEMA_MAJOR}.{USER_SETTINGS_SCHEMA_MINOR}\"\n");
    output.push_str(
        "# Generated from classic-user-settings-core; do not edit this mirror by hand.\n",
    );
    let mut previous_groups: &[&str] = &[];
    for setting in MIRROR_SETTINGS {
        let path = setting.path();
        let groups = &path[..path.len() - 1];
        let common = previous_groups
            .iter()
            .zip(groups)
            .take_while(|(left, right)| left == right)
            .count();
        for (index, group) in groups.iter().enumerate().skip(common) {
            output.push('\n');
            output.push_str(&"  ".repeat(index));
            output.push_str(group);
            output.push_str(":\n");
        }
        output.push('\n');
        let indent = "  ".repeat(groups.len());
        for guidance in setting.guidance {
            output.push_str(&indent);
            output.push_str("# ");
            output.push_str(guidance);
            output.push('\n');
        }
        output.push_str(&indent);
        output.push_str(setting.label());
        output.push_str(": ");
        output.push_str(&render_default(setting.default()));
        output.push('\n');
        previous_groups = groups;
    }
    output
}

/// Reads one window's width and height from the same ordered metadata used for rendering.
fn geometry_default(tab: &str) -> (u32, u32) {
    let dimension = |label| {
        let setting = MIRROR_SETTINGS
            .iter()
            .find(|setting| setting.path == ["UI", "window_geometry", tab, label].as_slice())
            .expect("every published window geometry has width and height metadata");
        u32::try_from(setting.default().as_integer())
            .expect("published window geometry dimensions fit in u32")
    };
    (dimension("width"), dimension("height"))
}

/// Renders one const-friendly registry value as deterministic YAML.
fn render_default(default: PublishedDefault) -> String {
    match default {
        PublishedDefault::Bool(_) => default.as_bool().to_string(),
        PublishedDefault::Integer(_) => default.as_integer().to_string(),
        PublishedDefault::String(_) => default.as_str().to_string(),
        PublishedDefault::Null => {
            debug_assert_eq!(default.as_optional_str(), None);
            "null".to_string()
        }
        PublishedDefault::EmptyMapping => {
            default.assert_empty_mapping();
            "{}".to_string()
        }
    }
}

/// Locates the one structured compatibility scalar without re-emitting outer YAML Data.
fn locate_compatibility_mirror(source: &str) -> Result<MirrorBlock, String> {
    let mut documents = parse_yaml_content("CLASSIC Main.yaml", source)
        .map_err(|error| format!("CLASSIC Main.yaml is invalid: {error}"))?;
    if documents.len() != 1
        || documents.remove(0)["CLASSIC_Info"]["default_settings"]
            .as_str()
            .is_none()
    {
        return Err(
            "CLASSIC Main.yaml must contain CLASSIC_Info.default_settings as a literal scalar"
                .into(),
        );
    }

    let newline = detected_newline(source);
    let marker = format!("  default_settings: |{newline}");
    if source.matches(&marker).count() != 1 {
        return Err(
            "CLASSIC Main.yaml must contain exactly one CLASSIC_Info.default_settings block".into(),
        );
    }
    let start = source.find(&marker).expect("unique marker exists") + marker.len();
    let boundary = format!("{newline}  default_localyaml: |");
    let relative_end = source[start..].find(&boundary).ok_or_else(|| {
        "CLASSIC_Info.default_settings must precede default_localyaml".to_string()
    })?;
    Ok(MirrorBlock {
        start,
        end: start + relative_end,
        newline,
    })
}

/// Extracts and de-indents the compatibility scalar without rewriting outer YAML Data.
fn extract_compatibility_mirror(source: &str) -> Result<String, String> {
    let location = locate_compatibility_mirror(source)?;
    let block = &source[location.start..location.end];
    let mut extracted = String::new();
    for line in block.split_inclusive(location.newline) {
        let (body, ending) = line
            .strip_suffix(location.newline)
            .map_or((line, ""), |body| (body, location.newline));
        let body = if body.is_empty() {
            body
        } else {
            body.strip_prefix("    ").ok_or_else(|| {
                "every non-blank default_settings content line must be indented four spaces"
                    .to_string()
            })?
        };
        extracted.push_str(body);
        extracted.push_str(ending);
    }
    Ok(extracted.replace("\r\n", "\n"))
}

/// Replaces only the embedded scalar, preserving line endings and every surrounding byte.
pub(super) fn replace_compatibility_mirror(source: &str) -> Result<String, String> {
    let location = locate_compatibility_mirror(source)?;
    let rendered = render_compatibility_mirror().replace('\n', location.newline);
    let indented = rendered
        .split_inclusive(location.newline)
        .map(|line| {
            if line == location.newline {
                location.newline.to_string()
            } else {
                format!("    {line}")
            }
        })
        .collect::<String>();
    Ok(format!(
        "{}{}{}",
        &source[..location.start],
        indented,
        &source[location.end..]
    ))
}

/// Verifies exact generated freshness and every canonical path's YAML type and value.
pub(super) fn check_compatibility_mirror(source: &str) -> Result<(), String> {
    let actual = extract_compatibility_mirror(source)?;
    let expected = render_compatibility_mirror();
    validate_canonical_semantics(&actual)?;
    if actual != expected {
        return Err(
            "CLASSIC_Info.default_settings is stale; regenerate the compatibility mirror".into(),
        );
    }
    Ok(())
}

/// Walks every canonical registry path and compares its parsed YAML value without coercion.
fn validate_canonical_semantics(mirror: &str) -> Result<(), String> {
    let mut documents = parse_yaml_content("generated User Settings compatibility mirror", mirror)
        .map_err(|error| error.to_string())?;
    if documents.len() != 1 {
        return Err(format!(
            "default_settings must contain one YAML document, found {}",
            documents.len()
        ));
    }
    let document = documents.remove(0);
    for setting in MIRROR_SETTINGS.iter().filter(|setting| setting.canonical) {
        let actual = setting
            .path()
            .iter()
            .fold(&document, |node, label| &node[*label]);
        if !semantically_matches(setting.default(), actual) {
            return Err(format!(
                "default_settings semantic drift at {}",
                setting.dotted_path
            ));
        }
    }
    Ok(())
}

/// Compares one parsed YAML node with a registry default without scalar coercion.
fn semantically_matches(default: PublishedDefault, actual: &Yaml) -> bool {
    match default {
        PublishedDefault::Bool(_) => {
            matches!(actual, Yaml::Boolean(actual) if *actual == default.as_bool())
        }
        PublishedDefault::Integer(_) => {
            matches!(actual, Yaml::Integer(actual) if *actual == default.as_integer())
        }
        PublishedDefault::String(_) => actual.as_str() == Some(default.as_str()),
        PublishedDefault::Null => {
            default.as_optional_str().is_none() && matches!(actual, Yaml::Null)
        }
        PublishedDefault::EmptyMapping => {
            default.assert_empty_mapping();
            matches!(actual, Yaml::Hash(mapping) if mapping.is_empty())
        }
    }
}

/// Detects the file's existing newline convention so regeneration avoids whole-file churn.
fn detected_newline(source: &str) -> &'static str {
    if source.contains("\r\n") {
        "\r\n"
    } else {
        "\n"
    }
}
