# Golden File Log Selection

Selected crash logs for parity testing. These logs capture diverse scenarios
to ensure Rust implementation matches Python output exactly.

## Selection Criteria

Per Phase 6 CONTEXT.md decisions:
- Common cases (typical crashes with plugins, FormIDs)
- Edge cases (unusual patterns, special characters, minimal content)
- Large logs (stress testing parser performance)
- Varied content (different crash types, mod counts, usernames)

## Selected Logs (18 total)

### Common Cases (10)

Standard crash logs with typical plugin lists, FormIDs, and segments.

| Log File | Size | Description |
|----------|------|-------------|
| crash-2022-06-05-12-52-17.log | 45KB | Standard crash, typical plugin list |
| crash-2022-06-12-07-11-38.log | 83KB | Larger mod list, ~50+ plugins |
| crash-2022-06-24-07-23-35.log | 51KB | Standard crash, various segments |
| crash-2022-10-07-01-50-25 Lancer_Vance.log | 34KB | Named user log, username in filename |
| crash-2022-10-10-02-12-34 Bones.log | 32KB | Another user log, different naming |
| crash-2022-06-17-07-04-05.log | 33KB | Mid-size standard crash |
| crash-2022-08-04-05-02-16.log | 24KB | Summer 2022 crash |
| crash-2022-09-22-04-55-18.log | 35KB | Fall 2022 crash |
| crash-2022-10-16-22-55-26 Arcanist.log | 34KB | Mixed content with user |
| crash-2022-06-09-04-44-04.log | 46KB | Early June baseline |

### Edge Cases (5)

Logs with unusual filenames, special characters, or minimal content.

| Log File | Size | Edge Case Type |
|----------|------|----------------|
| crash-$123 1.log | 50KB | Special char ($) in filename |
| crash-0akensh1eld 1.log | 52KB | Alphanumeric mix in name |
| crash-0DB9300.log | 15KB | Hex-like short name |
| crash-12624.log | 38KB | Numeric only filename |
| crash-1D1777B.log | 20KB | Hex FormID-style name |

### Large/Stress (3)

Largest logs for performance comparison and edge case handling.

| Log File | Size | Description |
|----------|------|-------------|
| crash-2024-05-12-15-43-32 BonBon.log | 2.0MB | Largest log, many mods |
| crash-2023-10-03-13-47-03 yaan.log | 1.8MB | Large with unicode username |
| crash-BLCKLSTD 2.log | 1.5MB | Heavy mod load |

Note: Unicode characters in filenames simplified for cross-platform compatibility.

## Minimal Content Logs (included for edge case testing)

| Log File | Size | Description |
|----------|------|-------------|
| crash-2023-08-05-09-06-21.log | 61B | Minimal header only |

Note: This log contains only game version headers, useful for testing parser handling of minimal input.

## Capture Strategy

1. Parse each log using Python implementation
2. Capture intermediate outputs:
   - Parsed segments (JSON) - segment boundaries and content
   - Analysis summary (JSON) - file metadata and parse statistics
3. Store in tests/golden/captured/ with naming:
   - `{safe_stem}_segments.json`
   - `{safe_stem}_analysis.json`

Safe stem: Filename with spaces replaced by underscores, special chars removed.

## Notes

- Timestamps and paths will be masked before storage using {{TIMESTAMP}} and {{PATH}} placeholders
- Use `--update-golden` flag to regenerate after Python implementation changes
- Phase 10 will compare Rust output against these golden files to verify parity
- At least 10 logs must be captured per VAL-01 requirement
