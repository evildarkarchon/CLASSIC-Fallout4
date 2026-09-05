"""Prepare one source-scoped input-only frontend consumer invocation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_REPO_ROOT = SCRIPT_PATH.parents[4]
TOOLS_ROOT = SCRIPT_PATH.parents[2]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from conformance.consumers import (
    load_consumer_obligations,
    prepare_consumer_run,
)
from conformance.packs import (
    MaterializationError,
    PackValidationError,
    load_and_validate_pack,
)

DEFAULT_PACK_PATH = Path("tests/conformance/packs/crash_log_scan_run/v1.json")
DEFAULT_ARTIFACT_ROOT = Path("tools/binding_compliance/artifacts")


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the private frontend-launcher preparation interface."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK_PATH)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--participant", required=True, choices=("cli", "gui", "tui"))
    parser.add_argument("--execution-instance", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Prepare a fresh run and print stable paths for a native launcher."""

    arguments = build_argument_parser().parse_args(argv)
    repo_root = arguments.repo_root.resolve()
    try:
        pack = load_and_validate_pack(repo_root, arguments.pack)
        catalog = load_consumer_obligations(repo_root)
        run = prepare_consumer_run(
            pack,
            participant_id=arguments.participant,
            execution_instance_id=arguments.execution_instance,
            artifact_root=arguments.artifact_root,
            catalog=catalog,
        )
    except (PackValidationError, MaterializationError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    plan = run.document()
    print(
        json.dumps(
            {
                "artifactDir": str(run.artifact_dir),
                "runPlanPath": str(run.run_plan_path),
                "receiptPath": str(run.receipt_path),
                "familyId": plan["familyId"],
                "participantId": plan["participant"]["id"],
                "executionInstanceId": plan["participant"]["executionInstanceId"],
                "invocationId": plan["invocation"]["id"],
                "sourceIdentity": plan["invocation"]["sourceIdentity"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
