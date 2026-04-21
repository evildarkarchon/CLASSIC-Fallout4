# Inter (bundled font)

The CLASSIC Qt GUI embeds the [Inter](https://rsms.me/inter/) typeface so text
rendering stays consistent across Windows 10 and Windows 11 hosts regardless of
the installed system font.

## Version

- Upstream repository: https://github.com/rsms/inter
- Release tag: [`v4.1`](https://github.com/rsms/inter/releases/tag/v4.1)
- Source archive: `Inter-4.1.zip` (33,707,794 bytes)
- Archive SHA-256: `9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e`

## Bundled files

The four static TrueType faces were extracted from `extras/ttf/` inside the
upstream archive. `OFL.txt` is the upstream `LICENSE.txt` renamed to match the
Qt resource prefix used by the GUI (`:/fonts/Inter/OFL.txt`).

| File                   | Size (bytes) | SHA-256                                                            |
| ---------------------- | ------------ | ------------------------------------------------------------------ |
| `Inter-Regular.ttf`    | 411,640      | `40d692fce188e4471e2b3cba937be967878f631ad3ebbbdcd587687c7ebe0c82` |
| `Inter-Italic.ttf`     | 417,388      | `bbc051dd204b5019a1aa0bc0ae2aa8a05ab13e7a3f979fa357631dc7feb6833a` |
| `Inter-Bold.ttf`       | 420,428      | `288316099b1e0a47a4716d159098005eef7c0066921f34e3200393dbdb01947f` |
| `Inter-BoldItalic.ttf` | 425,296      | `948405a16cdc62701da5f4005ed068ca5f4d27061d98f7974ccfc37831d9581d` |
| `OFL.txt`              | 4,380        | `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a` |

## License

Inter is licensed under the [SIL Open Font License, Version 1.1](OFL.txt).
The unmodified upstream license text ships alongside these font files as
`OFL.txt` and is also embedded in the Qt resource system at
`:/fonts/Inter/OFL.txt` so distributed builds satisfy the OFL's
license-propagation requirement. The CLASSIC About dialog contains a short
attribution line that names Inter and references this license.

## Refresh procedure

1. Download the desired Inter release from https://github.com/rsms/inter/releases.
2. Verify the downloaded archive's SHA-256 against the value published by the
   release page or recompute it locally and compare to a trusted source.
3. Extract `extras/ttf/Inter-Regular.ttf`, `extras/ttf/Inter-Italic.ttf`,
   `extras/ttf/Inter-Bold.ttf`, and `extras/ttf/Inter-BoldItalic.ttf` into this
   directory, overwriting the existing files.
4. Copy the archive's `LICENSE.txt` into this directory as `OFL.txt`,
   overwriting the existing file.
5. Update the "Version" and "Bundled files" sections above with the new tag,
   archive SHA-256, file sizes, and per-file SHA-256 digests.
6. Rebuild with `classic-gui/build_gui.ps1 -Test` and verify the GUI still
   starts with Inter as its default family.
