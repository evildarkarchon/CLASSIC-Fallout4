"""Stable tokens observed from the public Python GameId wrapper."""

from collections.abc import Mapping
from typing import Any


def observe_shared_identity(family: str, fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Read all public game tokens; Python runtime has a different owner contract."""
    if family != "game-identity" or fixture != {"request": {}}:
        raise ValueError("unsupported shared identity request")
    from classic_shared import GameId

    return {
        "tokens": [
            game.as_str()
            for game in (
                GameId.Fallout4,
                GameId.Fallout4VR,
                GameId.Skyrim,
                GameId.Starfield,
            )
        ]
    }
