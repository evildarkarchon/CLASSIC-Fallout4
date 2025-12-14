# Change: Remove ClassicLib.Util Backward Compatibility Shim

## Why
`ClassicLib.Util` is a backward compatibility shim that re-exports functions from the new `ClassicLib.Utils` submodules. This is the last remaining backward compatibility shim after previous refactoring efforts. Keeping it increases maintenance burden and violates the project's commitment to clean import paths without legacy aliases.

## What Changes
- **BREAKING**: Remove `ClassicLib/Util.py` (the backward compatibility shim)
- Update all imports in ClassicLib modules to use new `ClassicLib.Utils.*` paths
- Update all imports in test files to use new `ClassicLib.Utils.*` paths  
- Update test mock/patch paths to use canonical module paths
- Add requirement to code-organization spec prohibiting `ClassicLib.Util` imports

## Impact
- Affected specs: `code-organization`
- Affected code:
  - `ClassicLib/__init__.py` - Re-exports from Util.py
  - `ClassicLib/BackupManager.py` - Uses normalize_list, open_file_with_encoding, validate_path
  - `ClassicLib/DocsPath.py` - Uses remove_readonly, validate_path
  - `ClassicLib/GameIntegrity.py` - Uses calculate_file_hash
  - `ClassicLib/GamePath.py` - Uses get_game_version, open_file_with_encoding, validate_path
  - `ClassicLib/SetupCoordinator.py` - Uses configure_logging
  - `ClassicLib/Interface/Pastebin.py` - Uses pastebin_fetch_async
  - `ClassicLib/ScanGame/CheckXsePlugins.py` - Uses get_game_version
  - `ClassicLib/ScanGame/Config.py` - Uses calculate_file_hash, calculate_similarity
  - `ClassicLib/ScanGame/core/config_duplicate_fallback.py` - Uses calculate_file_hash
  - `ClassicLib/ScanGame/core/log_processor.py` - Uses normalize_list, open_file_with_encoding
  - `ClassicLib/ScanLog/OrchestratorCore.py` - Uses crashgen_version_gen
  - `CLASSIC_Interface_QML.py` - Uses pastebin_fetch_async
  - `tests/utils/test_string_utils.py` - Tests string utilities
  - `tests/utils/test_path_utils.py` - Tests path utilities
  - `tests/utils/test_network_operations.py` - Tests network utilities
  - `tests/utils/test_logging_utils.py` - Tests logging utilities
  - `tests/utils/test_file_operations.py` - Tests file utilities

## Migration Guide

### Import Mappings

| Old Import                                            | New Import                                                        |
| ----------------------------------------------------- | ----------------------------------------------------------------- |
| `from ClassicLib.Util import normalize_list`          | `from ClassicLib.Utils.string_utils import normalize_list`        |
| `from ClassicLib.Util import append_or_extend`        | `from ClassicLib.Utils.string_utils import append_or_extend`      |
| `from ClassicLib.Util import validate_path`           | `from ClassicLib.Utils.path_utils import validate_path`           |
| `from ClassicLib.Util import remove_readonly`         | `from ClassicLib.Utils.path_utils import remove_readonly`         |
| `from ClassicLib.Util import calculate_file_hash`     | `from ClassicLib.Utils.file_utils import calculate_file_hash`     |
| `from ClassicLib.Util import calculate_similarity`    | `from ClassicLib.Utils.file_utils import calculate_similarity`    |
| `from ClassicLib.Util import open_file_with_encoding` | `from ClassicLib.Utils.file_utils import open_file_with_encoding` |
| `from ClassicLib.Util import get_game_version`        | `from ClassicLib.Utils.version_utils import get_game_version`     |
| `from ClassicLib.Util import crashgen_version_gen`    | `from ClassicLib.Utils.version_utils import crashgen_version_gen` |
| `from ClassicLib.Util import configure_logging`       | `from ClassicLib.Utils.logging_utils import configure_logging`    |
| `from ClassicLib.Util import pastebin_fetch`          | `from ClassicLib.Utils.web_utils import pastebin_fetch`           |
| `from ClassicLib.Util import async_pastebin_fetch`    | `from ClassicLib.Utils.web_utils import async_pastebin_fetch`     |
| `from ClassicLib.Util import pastebin_fetch_async`    | `from ClassicLib.Utils.web_utils import async_pastebin_fetch`     |

### Alternative: Use the Utils Package
For convenience, all functions remain available via `ClassicLib.Utils`:
```python
from ClassicLib.Utils import normalize_list, validate_path, calculate_file_hash