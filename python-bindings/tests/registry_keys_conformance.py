"""Observe public registry key constants without reading authored expectations."""


def observe_registry_keys(fixture):
    """Read each public Python class attribute with its stable common key name."""
    import classic_registry as registry

    if fixture != {"request": {}}:
        raise ValueError("registry keys fixture must contain only an empty request")
    names = (
        "YAML_CACHE",
        "MANUAL_DOCS_GUI",
        "GAME_PATH_GUI",
        "GAME_PATH",
        "DOCS_PATH",
        "IS_GUI_MODE",
        "OPEN_FILE_FUNC",
        "GAME",
        "GAME_VERSION",
        "VERSION_AUTO_DETECTED",
        "LOCAL_DIR",
        "IS_PRERELEASE",
        "XSE_VALID",
        "XSE_VERSION",
        "ENB_PRESENT",
        "GAME_VERSION_DETECTED",
    )
    return {"keys": {name: getattr(registry.Keys, name) for name in names}}
