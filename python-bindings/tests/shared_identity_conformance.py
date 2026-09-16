"""Stable tokens observed from the public Python GameId wrapper."""

from collections.abc import Mapping
from typing import Any


def observe_shared_identity(family: str, fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Read public game identity/metadata and shared-runtime diagnostics through native APIs."""
    if fixture != {"request": {}} and not (
            family == "game-identity"
            and fixture
            in (
                    {"request": {"operation": "metadata"}},
                    {"request": {"operation": "details"}},
            )
    ):
        raise ValueError("unsupported shared identity request")
    if family == "runtime-access":
        from classic_shared import get_runtime_stats, is_runtime_healthy

        available, diagnostics = [], []
        for _ in range(2):
            available.append(is_runtime_healthy())
            stats = get_runtime_stats()
            diagnostics.append(stats.is_healthy and stats.worker_threads > 0)
        return {"available": available, "diagnosticsAvailable": diagnostics}
    if family != "game-identity":
        raise ValueError("unsupported shared identity family")
    from classic_shared import GameId

    games = (GameId.Fallout4, GameId.Fallout4VR, GameId.Skyrim, GameId.Starfield)
    if fixture["request"].get("operation") == "metadata":
        return {"labels": [game.display_name() for game in games]}
    if fixture["request"].get("operation") == "details":
        return {
            "games": [
                {
                    "exeName": game.exe_name(),
                    "vr": game.is_vr(),
                    "text": str(game),
                    "repr": repr(game),
                    "equalCopy": game == getattr(GameId, game.as_str()),
                    "equalOther": game == games[(index + 1) % len(games)],
                    "hashCopy": hash(game) == hash(getattr(GameId, game.as_str())),
                }
                for index, game in enumerate(games)
            ]
        }

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
