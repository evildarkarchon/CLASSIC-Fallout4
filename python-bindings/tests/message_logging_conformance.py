"""Capture actual native logger records from an isolated initialized Python process."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _worker(fixture):
    """Invoke only public binding APIs; the parent owns the independent log observation."""
    import classic_message as message

    message.init_logging()
    message.init_logging()
    logger = message.Logger()
    operation = fixture["operation"]
    if operation == "basic":
        for level, content in fixture["messages"].items():
            getattr(logger, level)(content)
        return {}
    if operation == "format":
        return {
            "formatted": message.format_contract_event(
                **{k: v for k, v in fixture.items() if k != "operation"}
            )
        }
    if operation != "extended":
        raise ValueError("unsupported Python logging operation")
    logger.trace(fixture["trace"])
    logger.log("info", fixture["dynamic"])
    native = message.Message(fixture["message"], message.MessageType.Warning)
    native.set_title(fixture["title"])
    native.set_details(fixture["details"])
    logger.log_message(native)
    rejected = []
    for invoke in (
            lambda: logger.log(fixture["invalid"], "ignored"),
            lambda: logger.is_enabled_for(fixture["invalid"]),
    ):
        try:
            invoke()
        except ValueError:
            rejected.append(True)
        else:
            rejected.append(False)
    return {
        "enabled": [
            logger.is_info_enabled(),
            logger.is_debug_enabled(),
            logger.is_trace_enabled(),
            logger.is_enabled_for("warning"),
        ],
        "name": logger.name(),
        "invalidLog": rejected[0],
        "invalidEnabled": rejected[1],
    }


def observe_message_logging(fixture):
    """Capture severity and message bytes, omitting environmental timestamp and log target prefixes."""
    child = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), json.dumps(fixture)],
        env={**os.environ, "RUST_LOG": "trace", "RUST_LOG_STYLE": "never"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if child.returncode != 0:
        raise ValueError(f"native logging worker failed: {child.stderr}")
    records = []
    for line in child.stderr.splitlines():
        match = re.fullmatch(
            r"\[[^\]]+\s(TRACE|DEBUG|INFO|WARN|ERROR)\s+[^\]]+\] (.*)", line
        )
        if match is None:
            raise ValueError(f"unrecognized native log record: {line}")
        records.append({"level": match[1], "message": match[2]})
    return {"records": records, **json.loads(child.stdout)}


if __name__ == "__main__":
    print(json.dumps(_worker(json.loads(sys.argv[1]))))
