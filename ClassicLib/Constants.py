from enum import Enum, auto
from pathlib import Path
from typing import Literal

from packaging.version import Version

from ClassicLib import GlobalRegistry

NULL_VERSION: Version = Version("0.0.0.0")
OG_VERSION: Version = Version("1.10.163.0")
NG_VERSION: Version = Version("1.10.984.0")
VR_VERSION: Version = Version("1.2.72.0")
OG_F4SE_VERSION: Version = Version("0.6.23")
NG_F4SE_VERSION: Version = Version("0.7.2")
FO4_VERSIONS: tuple[Version, Version] = (OG_VERSION, NG_VERSION)
F4SE_VERSIONS: tuple[Version, Version] = (OG_F4SE_VERSION, NG_F4SE_VERSION)
type GameID = (
    Literal["Fallout4", "Fallout4VR", "Skyrim", "Starfield"] | str
)  # Entries must correspond to the game's Main ESM or EXE file name.


class YAML(Enum):
    Main = auto()
    """CLASSIC Data/databases/CLASSIC Main.yaml"""
    Settings = auto()
    """CLASSIC Settings.yaml"""
    Ignore = auto()
    """CLASSIC Ignore.yaml"""
    Game = auto()
    """CLASSIC Data/databases/CLASSIC Fallout4.yaml"""
    Game_Local = auto()
    """CLASSIC Data/CLASSIC Fallout4 Local.yaml"""
    TEST = auto()
    """tests/test_settings.yaml"""


"""class GameVars(TypedDict):
    game: GameID
    vr: Literal["VR", ""] | str"""


"""gamevars: GameVars = {
    "game": "Fallout4",
    "vr": "",
}"""

SETTINGS_IGNORE_NONE = {
    "SCAN Custom Path",
    "MODS Folder Path",
    "Root_Folder_Game",
    "Root_Folder_Docs",
}

# Define paths for both Main and Local databases
DB_PATHS = (
    Path(f"CLASSIC Data/databases/{GlobalRegistry.get_game()} FormIDs Main.db"),
    Path(f"CLASSIC Data/databases/{GlobalRegistry.get_game()} FormIDs Local.db"),
)
