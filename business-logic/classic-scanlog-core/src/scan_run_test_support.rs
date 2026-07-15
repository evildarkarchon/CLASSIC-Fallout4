use std::path::{Path, PathBuf};

pub(crate) const FIXTURE_LOG_SMALL: &str = include_str!("../benches/fixtures/crash-0DB9300.log");

pub(crate) fn write_fixture_log(temp: &tempfile::TempDir, filename: &str) -> PathBuf {
    let log_path = temp.path().join(filename);
    std::fs::write(&log_path, FIXTURE_LOG_SMALL).expect("fixture log should be written");
    log_path
}

pub(crate) fn write_minimal_yaml_tree(root: &Path, data: &Path) {
    std::fs::create_dir_all(data.join("databases")).expect("database dir should be created");
    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        concat!(
            "CLASSIC_Info:\n",
            "  version: \"v9.1.0\"\n",
            "  version_date: \"2026-06-30\"\n",
            "CLASSIC_Interface:\n",
            "  autoscan_text_Fallout4: \"Autoscan Fallout 4\"\n",
            "catch_log_records:\n",
            "  - TESObjectREFR\n",
            "exclude_log_records:\n",
            "  - '(void*)'\n",
        ),
    )
    .expect("main YAML should be written");
    std::fs::write(
        data.join("databases").join("CLASSIC Fallout4.yaml"),
        concat!(
            "Game_Info:\n",
            "  XSE_Acronym: \"F4SE\"\n",
            "  GameVersion: \"1.10.163\"\n",
            "  CRASHGEN_LatestVer: \"1.28.6\"\n",
            "  CRASHGEN_LogName: \"Buffout 4\"\n",
            "  Main_Root_Name: \"Fallout4\"\n",
            "Crashlog_Plugins_Exclude: []\n",
            "Crashlog_Records_Exclude: []\n",
            "Crashgen_Registry:\n",
            "  default:\n",
            "    display_section: \"\"\n",
            "    ignore_keys: []\n",
            "    checks: []\n",
        ),
    )
    .expect("game YAML should be written");
    std::fs::write(
        root.join("CLASSIC Ignore.yaml"),
        "CLASSIC_Ignore_Fallout4:\n  - IgnoreThis.dll\n",
    )
    .expect("ignore YAML should be written");
}
