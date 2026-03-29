"""Fixtures for Python Tier-1 binding parity smoke tests."""

PARITY_MAIN_YAML = """
CLASSIC_Info:
  version: "9.0.0"
  version_date: "2026-02-25"
catch_log_records:
  - "LAND"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
"""

PARITY_GAME_YAML = """
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
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_CONF: []
Mods_CORE: {}
Mods_CORE_FOLON: {}
Mods_FREQ: {}
Mods_SOLU: []
"""

PARITY_IGNORE_YAML = """
CLASSIC_Ignore_Fallout4:
  - "IgnoreItem1"
"""
