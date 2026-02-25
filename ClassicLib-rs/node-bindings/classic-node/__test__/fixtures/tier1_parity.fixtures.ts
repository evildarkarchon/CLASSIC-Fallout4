export const PARITY_MAIN_YAML = `
CLASSIC_Info:
  version: "9.0.0"
  version_date: "2026-02-25"
catch_log_records:
  - "LAND"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
`;

export const PARITY_GAME_YAML = `
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "1.37.0"
  CRASHGEN_LogName: "Buffout 4"
  Main_Root_Name: "Fallout4"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found"
  Warn_Outdated: "Outdated"
Crashlog_Plugins_Exclude: []
Crashlog_Records_Exclude: []
Crashlog_Error_Check: {}
Crashlog_Stack_Check: {}
Mods_CONF: {}
Mods_CORE: {}
Mods_CORE_FOLON: {}
Mods_FREQ: {}
Mods_OPC2: {}
Mods_SOLU: {}
`;

export const PARITY_IGNORE_YAML = `
CLASSIC_Ignore_Fallout4:
  - "IgnoreItem1"
`;

export const INVALID_PARITY_MAIN_YAML = "{ invalid: yaml: content: }}}";

export const scanlogConfigCases = [
  {
    id: "fallout4-non-vr-defaults",
    game: "Fallout4",
    vrMode: false,
    expected: {
      crashgenName: "",
      xseAcronym: "",
      classicVersion: "CLASSIC",
      fcxMode: false,
      simplifyLogs: false,
    },
  },
  {
    id: "fallout4-vr-defaults",
    game: "Fallout4",
    vrMode: true,
    expected: {
      crashgenName: "",
      xseAcronym: "",
      classicVersion: "CLASSIC",
      fcxMode: false,
      simplifyLogs: false,
    },
  },
] as const;

export const scanlogYamlOptionsCases = [
  {
    id: "omitted-options",
    options: undefined,
    expected: {
      crashgenName: "Buffout 4",
      xseAcronym: "F4SE",
      classicVersion: "9.0.0",
      fcxMode: false,
      simplifyLogs: false,
    },
  },
  {
    id: "explicit-options",
    options: {
      showFormidValues: true,
      fcxMode: true,
      simplifyLogs: true,
      removeList: ["NVIDIA", "AMD"],
    },
    expected: {
      crashgenName: "Buffout 4",
      xseAcronym: "F4SE",
      classicVersion: "9.0.0",
      fcxMode: true,
      simplifyLogs: true,
    },
  },
] as const;

export const scanlogErrorCase = {
  missingLogPath: "Z:\\nonexistent\\tier1-parity.log",
} as const;

export const configSourceCases = [
  {
    id: "main-source",
    source: "Main",
    game: "",
    expectedPathToken: "CLASSIC Main.yaml",
    expectedDisplayName: "Main Database",
  },
  {
    id: "game-source",
    source: "Game",
    game: "Fallout4",
    expectedPathToken: "CLASSIC Fallout4.yaml",
    expectedDisplayName: "Fallout4 Database",
  },
  {
    id: "ignore-source",
    source: "Ignore",
    game: "",
    expectedPathToken: "CLASSIC Ignore.yaml",
    expectedDisplayName: "Ignore List",
  },
] as const;

export const versionRegistryCases = [
  {
    id: "fo4-og",
    versionId: "FO4_OG",
    expectedShortName: "OG",
    expectedIsVr: false,
    expectedVersion: "1.10.163.0",
  },
  {
    id: "fo4-ng",
    versionId: "FO4_NG",
    expectedShortName: "NG",
    expectedIsVr: false,
    expectedVersion: "1.10.984.0",
  },
  {
    id: "fo4-vr",
    versionId: "FO4_VR",
    expectedShortName: "VR",
    expectedIsVr: true,
    expectedVersion: "1.2.72.0",
  },
] as const;
