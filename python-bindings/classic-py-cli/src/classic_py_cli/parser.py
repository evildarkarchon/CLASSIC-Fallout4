"""Argparse parser construction for the CLASSIC Python CLI."""

from __future__ import annotations

import argparse

from . import commands


def build_parser() -> argparse.ArgumentParser:
    """Build the stdlib argparse command tree and global options."""

    parser = argparse.ArgumentParser(prog="classic-py", description="CLASSIC Python binding diagnostics and compliance runner")
    parser.add_argument("--json", action="store_true", help="write one JSON envelope to stdout")
    parser.add_argument("--output", help="write report artifacts under this directory")
    parser.add_argument("--repo-root", help="repository root override")
    parser.add_argument("--fixture-root", help="fixture root override")
    parser.add_argument("--no-color", action="store_true", help="disable colored output")
    parser.add_argument("--verbose", action="store_true", help="write diagnostics to stderr")
    parser.add_argument("--tracebacks", action="store_true", help="show Python tracebacks for unexpected CLI errors")
    subcommands = parser.add_subparsers(dest="command_group", required=True)

    bindings = subcommands.add_parser("bindings", help="binding diagnostics")
    bindings_sub = bindings.add_subparsers(dest="bindings_command", required=True)
    bindings_list = bindings_sub.add_parser("list", help="list maintained binding modules")
    bindings_list.set_defaults(handler=commands.bindings_list)
    bindings_smoke = bindings_sub.add_parser("smoke", help="run binding import smoke checks")
    bindings_smoke.set_defaults(handler=commands.bindings_smoke)

    doctor = subcommands.add_parser("doctor", help="check local Python binding readiness")
    doctor.set_defaults(handler=commands.doctor)

    compliance = subcommands.add_parser("compliance", help="compliance scenario commands")
    compliance_sub = compliance.add_subparsers(dest="compliance_command", required=True)
    compliance_list = compliance_sub.add_parser("list", help="list compliance scenarios")
    compliance_list.set_defaults(handler=commands.compliance_list)
    compliance_explain = compliance_sub.add_parser("explain", help="explain one compliance scenario")
    compliance_explain.add_argument("scenario_id")
    compliance_explain.set_defaults(handler=commands.compliance_explain)
    compliance_run = compliance_sub.add_parser("run", help="run a compliance profile")
    compliance_run.add_argument("--profile", default="smoke", help="profile name, for example smoke, python-ci, or surface:classic_version")
    compliance_run.set_defaults(handler=commands.compliance_run)

    version = subcommands.add_parser("version", help="version utility commands")
    version_sub = version.add_subparsers(dest="version_command", required=True)
    version_parse = version_sub.add_parser("parse", help="parse a semantic version")
    version_parse.add_argument("version")
    version_parse.set_defaults(handler=commands.version_parse)

    config = subcommands.add_parser("config", help="configuration utility commands")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_main = config_sub.add_parser("main-version", help="read bundled main YAML version")
    config_main.set_defaults(handler=commands.config_main_version)
    config_inspect = config_sub.add_parser("inspect", help="inspect a CLASSIC config YAML file")
    config_inspect.add_argument("path")
    config_inspect.set_defaults(handler=commands.config_inspect)

    path = subcommands.add_parser("path", help="path validation utilities")
    path_sub = path.add_subparsers(dest="path_command", required=True)
    path_validate = path_sub.add_parser("validate", help="validate a path")
    path_validate.add_argument("path")
    path_validate.set_defaults(handler=commands.path_validate)

    file_cmd = subcommands.add_parser("file", help="file utility commands")
    file_sub = file_cmd.add_subparsers(dest="file_command", required=True)
    file_hash = file_sub.add_parser("hash", help="hash a file")
    file_hash.add_argument("path")
    file_hash.set_defaults(handler=commands.file_hash)

    database = subcommands.add_parser("database", help="database binding commands")
    database_sub = database.add_subparsers(dest="database_command", required=True)
    database_info = database_sub.add_parser("info", help="show deterministic database binding constants")
    database_info.set_defaults(handler=commands.database_info)

    xse = subcommands.add_parser("xse", help="script extender binding commands")
    xse_sub = xse.add_subparsers(dest="xse_command", required=True)
    xse_parse = xse_sub.add_parser("parse-type", help="parse an XSE type name")
    xse_parse.add_argument("type_name")
    xse_parse.set_defaults(handler=commands.xse_parse_type)

    update = subcommands.add_parser("update", help="update metadata commands")
    update_sub = update.add_subparsers(dest="update_command", required=True)
    update_url = update_sub.add_parser("validate-url", help="validate a URL without network access")
    update_url.add_argument("url")
    update_url.set_defaults(handler=commands.update_validate_url)

    resource = subcommands.add_parser("resource", help="resource binding commands")
    resource_sub = resource.add_subparsers(dest="resource_command", required=True)
    resource_detect = resource_sub.add_parser("detect", help="detect a resource type")
    resource_detect.add_argument("path")
    resource_detect.set_defaults(handler=commands.resource_detect)

    scan = subcommands.add_parser("scan", help="binding-backed scan commands")
    scan_sub = scan.add_subparsers(dest="scan_command", required=True)
    scan_logs = scan_sub.add_parser("logs", help="scan crash logs")
    scan_logs.add_argument("--path", help="scan path or fixture directory")
    scan_logs.set_defaults(handler=commands.scan_logs)
    scan_game = scan_sub.add_parser("game", help="scan game setup fixtures")
    scan_game.add_argument("--path", help="game root or fixture directory")
    scan_game.set_defaults(handler=commands.scan_game)

    return parser
