use super::*;

/// Windows roots must match path values emitted with either separator style.
#[test]
fn portable_removes_windows_root_from_normalized_paths() {
    let root = Path::new(r"C:\Users\runneradmin\temp");
    for value in [
        "C:/Users/runneradmin/temp/game/Fallout4.exe",
        r"C:\Users\runneradmin\temp\game\Fallout4.exe",
    ] {
        assert_eq!(portable(value, root), "game/Fallout4.exe");
    }
}

/// Canonicalized Windows roots and values may independently carry device prefixes.
#[test]
fn portable_removes_extended_windows_roots() {
    for root in [
        r"C:\Users\runneradmin\temp",
        r"\\?\C:\Users\runneradmin\temp",
    ] {
        for value in [
            r"\\?\C:\Users\runneradmin\temp\game\Fallout4.exe",
            "//?/C:/Users/runneradmin/temp/game/Fallout4.exe",
            "C:/Users/runneradmin/temp/game/Fallout4.exe",
        ] {
            assert_eq!(portable(value, Path::new(root)), "game/Fallout4.exe");
        }
    }
}

/// Errors embed paths inside prose, so root removal cannot be prefix-only.
#[test]
fn portable_removes_root_inside_errors() {
    assert_eq!(
        portable(
            r"Missing file: \\?\C:\Users\runneradmin\temp\game\Fallout4.exe",
            Path::new(r"\\?\C:\Users\runneradmin\temp"),
        ),
        "Missing file: game/Fallout4.exe"
    );
}

/// Similar sibling directories and relative paths must retain their path content.
#[test]
fn portable_preserves_paths_outside_root() {
    let root = Path::new(r"C:\Users\runneradmin\temp");
    for value in [
        "C:/Users/runneradmin/temp-other/game/Fallout4.exe",
        "D:/elsewhere/game/Fallout4.exe",
        "game/Fallout4.exe",
    ] {
        assert_eq!(portable(value, root), value);
    }
}
