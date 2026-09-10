# Path Operations fixtures

Each JSON file supplies directories, UTF-8 file contents and a required-file
validation request. Participants materialize those inputs in a fresh temporary
directory and call the public `is_valid_path` and `validate_required_files`
operations. They preserve existence, success/failure and exact domain error text,
replacing only the scenario-owned absolute root and native path separators.

The scenarios cover present files, a missing required file, a missing directory,
a file used as a directory, and an empty required-file list. They do not consult
host installations, registry entries, user directories or permission settings.
Expectations live separately in `tests/conformance/packs/path_operations/v1.json`.
