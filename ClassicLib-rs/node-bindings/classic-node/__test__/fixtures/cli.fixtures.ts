export const CLI_MAIN_YAML = `
CLASSIC_Info:
  version: "9.0.0"
  version_date: "2026-02-25"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
catch_log_records:
  - "LAND"
`;

export const CLI_GAME_YAML = `
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "1.37.0"
  CRASHGEN_LogName: "Buffout 4"
  Main_Root_Name: "Fallout4"
  Docs_Folder_XSE: "DOCS_XSE_PLACEHOLDER"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found"
  Warn_Outdated: "Outdated"
Crashlog_Plugins_Exclude: []
Crashlog_Records_Exclude: []
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_CONF: []
Mods_CORE: []
Mods_FREQ: {}
Mods_SOLU: {}
`;

export const CLI_IGNORE_YAML = `
CLASSIC_Ignore_Fallout4:
  - "IgnoreItem1"
`;

export const CLI_LOCAL_YAML = `
Game_Info:
  Docs_Folder_XSE: "DOCS_XSE_PLACEHOLDER"
`;

export const CLI_SAMPLE_LOG = `Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]
\tPHYSICAL MEMORY: 32.0 GB

PROBABLE CALL STACK:
\t[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> TESForm::SetReference+0x12
\t[ 1] 0x7FF6EF4C3600 Fallout4.exe+0733600 -> BGSInventoryItem::GetOwner+0x30

MODULES:
\tFallout4.exe v1.10.163.0
\tnvwgf2umx.dll v31.0.15.3713

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[03] Unofficial Fallout 4 Patch.esp
`;
