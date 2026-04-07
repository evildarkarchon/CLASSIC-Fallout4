#!/usr/bin/env python3
"""Generate Rust->CXX bridge parity baseline artifacts.

STUB: Task 2 implements parse_cxx_bridge_surface, parse_build_rs_file_list,
extract_ffi_block, write_json, and the __main__ entrypoint.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    raise NotImplementedError("Task 2")


def parse_build_rs_file_list(build_rs_source: str) -> list[str]:
    raise NotImplementedError("Task 2")


def extract_ffi_block(source: str) -> tuple[str | None, str]:
    raise NotImplementedError("Task 2")


def parse_cxx_bridge_surface(
    repo_root: Path,
    bridge_crate_rel: str = "ClassicLib-rs/cpp-bindings/classic-cpp-bridge",
) -> dict[str, Any]:
    raise NotImplementedError("Task 2")
