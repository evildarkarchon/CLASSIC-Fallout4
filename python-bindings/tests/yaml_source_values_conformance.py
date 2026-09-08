"""Read generic YAML source values through public Python exports."""


def observe_yaml_sources(fixture: dict) -> dict:
    """Preserve the difference between shared game data and per-game local paths."""
    import classic_config

    sources = [getattr(classic_config.YamlSource, name) for name in fixture["sources"]]
    rows = []
    for name, source in zip(fixture["sources"], sources, strict=True):
        if repr(source) != "YamlSource." + name or str(source) != name:
            raise ValueError("source representation lost its variant identity")
        rows.append(
            {
                "id": name,
                "path": source.path(fixture["game"]).replace("\\", "/"),
                "name": source.display_name(),
                "gameName": source.display_name_with_game(fixture["game"]),
            }
        )
    return {
        "sources": rows,
        "equal": sources[0] == classic_config.YamlSource.MAIN,
        "different": sources[0] != sources[1],
        "distinct": len(set(sources)),
    }
