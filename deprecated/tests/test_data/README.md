# Test Data Directory

This directory contains mock data and sample files used by the CLASSIC-Fallout4 test suite.

## Directory Structure

```
tests/test_data/
├── sample_crash_logs/          # Sample crash log files for testing
│   ├── sample_crash_1.log      # Basic crash log with standard format
│   └── complex_crash.log       # Complex crash log with multiple issues
├── mock_registry/              # Mock Windows registry data
│   └── game_paths.json         # Game installation paths for different platforms
├── sample_yaml/                # Sample YAML configuration files
│   └── test_settings.yaml      # Test YAML settings configuration
└── README.md                   # This documentation file
```

## Usage

These test data files are used by various fixtures in `conftest.py` to provide consistent test data across the test suite:

- **Sample Crash Logs**: Used by crash log processing tests to validate parsing and analysis functionality
- **Mock Registry**: Used by game path detection tests to simulate Windows registry entries
- **Sample YAML**: Used by configuration and settings tests to validate YAML processing

## Adding New Test Data

When adding new test data files:

1. Place them in the appropriate subdirectory
2. Use descriptive filenames that indicate their purpose
3. Update any relevant fixtures in `conftest.py` to use the new data
4. Document the purpose and structure of complex test data files

## File Formats

- **Crash Logs**: Plain text files following Buffout 4 crash log format
- **Registry Data**: JSON files with nested structure matching Windows registry layout
- **YAML Files**: Standard YAML configuration files matching the application's schema 