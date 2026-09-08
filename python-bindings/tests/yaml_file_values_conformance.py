"""Read canonical YAML file values through the real Python extension."""


def observe_yaml_file_values(fixture):
    """Observe both text views while exercising native equality/hash/display methods."""
    from classic_settings import YamlFile

    if fixture != {"request": {}}:
        raise ValueError("unsupported YAML file value request")
    names = ("Main", "Ignore", "Game", "GameLocal", "Test", "Cache")
    kinds = []
    for name in names:
        value = getattr(YamlFile, name)
        token = value.as_str()
        if str(value) != token or repr(value) != "YamlFile." + token:
            raise ValueError("YAML file display disagrees with native token")
        for other in names:
            peer = getattr(YamlFile, other)
            if value.__eq__(peer) is not (name == other):
                raise ValueError("YAML file equality changed enum identity")
            if name == other and hash(value) != hash(peer):
                raise ValueError("equal YAML file kinds have different hashes")
        kinds.append({"token": token, "description": value.description()})
    if hasattr(YamlFile, "Settings"):
        raise ValueError(
            "retired untyped User Settings enum leaked into public YAML kinds"
        )
    return {"kinds": kinds}
