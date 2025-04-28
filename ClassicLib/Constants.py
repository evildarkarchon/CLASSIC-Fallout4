from typing import Literal
from packaging.version import Version

NULL_VERSION = Version("0.0.0.0")
OG_VERSION = Version("1.10.163.0")
NG_VERSION = Version("1.10.984.0")
VR_VERSION = Version("1.2.72.0")
OG_F4SE_VERSION = Version("0.6.23")
NG_F4SE_VERSION = Version("0.7.2")
FO4_VERSIONS = (OG_VERSION, NG_VERSION)
F4SE_VERSIONS = (OG_F4SE_VERSION, NG_F4SE_VERSION)
type YAMLLiteral = str | int | bool
type YAMLSequence = list[str]
type YAMLMapping = dict[str, "YAMLValue"]
type YAMLValue = YAMLMapping | YAMLSequence | YAMLLiteral
type YAMLValueOptional = YAMLValue | None
type GameID = Literal[
    "Fallout4", "Fallout4VR", "Skyrim", "Starfield"]  # Entries must correspond to the game's Main ESM or EXE file name.