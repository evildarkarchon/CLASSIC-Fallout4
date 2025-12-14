## 1. Update Import Statements in Production Code

- [x] 1.1 Update `ClassicLib/FileGeneration.py` line 84: Change `from ClassicLib.AsyncYamlSettings import yaml_settings_async` to `from ClassicLib.YamlSettings import yaml_settings_async`
- [x] 1.2 Update `ClassicLib/FileGeneration.py` line 110: Change `from ClassicLib.AsyncYamlSettings import yaml_settings_async` to `from ClassicLib.YamlSettings import yaml_settings_async`

## 2. Update Import Statements in Tests

- [x] 2.1 Update `tests/mods/test_mod_detection_patterns.py` line 13: Change `from ClassicLib.AsyncYamlSettings import AsyncYamlSettingsCore` to `from ClassicLib.YamlSettings import AsyncYamlSettingsCore`
- [x] 2.2 Update `tests/core/test_message_handler.py`: Replace all `MessageTarget.CLI_ONLY` with `MessageTarget.CONSOLE`
- [x] 2.3 Update `tests/core/test_message_handler.py`: Replace all `MessageTarget.GUI_ONLY` with `MessageTarget.GUI`

## 3. Remove Deprecated Function

- [x] 3.1 Remove `get_rust_module()` function from `ClassicLib/rust_loader.py`

## 4. Remove Deprecated Enum Aliases

- [x] 4.1 Remove `MessageTarget.GUI_ONLY` enum value from `ClassicLib/MessageHandler/core/enums.py`
- [x] 4.2 Remove `MessageTarget.CLI_ONLY` enum value from `ClassicLib/MessageHandler/core/enums.py`
- [x] 4.3 Remove `_deprecated_gui_only()` function from `ClassicLib/MessageHandler/core/enums.py`
- [x] 4.4 Remove `_deprecated_cli_only()` function from `ClassicLib/MessageHandler/core/enums.py`
- [x] 4.5 Update `normalize()` method to remove handling of deprecated values

## 5. Delete Deprecated Module Files

- [x] 5.1 Delete `ClassicLib/FileIOCore.py`
- [x] 5.2 Delete `ClassicLib/AsyncUtil.py`
- [x] 5.3 Delete `ClassicLib/AsyncYamlSettingsCore.py`
- [x] 5.4 Delete `ClassicLib/AsyncYamlSettings/` directory
- [x] 5.5 Delete `ClassicLib/AsyncUtilities.py`
- [x] 5.6 Delete `ClassicLib/AsyncUtilities_Enhanced.py`

## 6. Verification

- [x] 6.1 Run full test suite: `uv run pytest -n auto`
- [x] 6.2 Run unit tests: `uv run pytest -n auto -m "unit and not slow"`
- [x] 6.3 Run linting: `uv run ruff check .`
- [x] 6.4 Verify no DeprecationWarnings from deleted modules in pytest output

## 7. Documentation

- [x] 7.1 Update CLASSIC Changelog.md with removal notice
- [x] 7.2 Verify CLAUDE.md doesn't reference deleted modules