from typing import Any, ClassVar


class SingletonMeta(type):
    _instances: ClassVar[dict[type, Any]] = {}

    def __call__(cls, *args, **kwargs):  # noqa: ANN002, ANN003, ANN204
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
