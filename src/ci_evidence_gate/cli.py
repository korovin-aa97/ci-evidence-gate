"""Evaluate exact-SHA and changed-surface CI evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import subprocess
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Surface:
    name: str
    patterns: tuple[str, ...]
    checks: tuple[str, ...]


@dataclass(frozen=True)
class Receipt:
    schema: str
    created_at: str
    base_sha: str
    head_sha: str
    manifest_sha256: str
    changed_files: tuple[str, ...]
    matched_surfaces: tuple[str, ...]
    required_checks: tuple[str, ...]
    passed_checks: tuple[str, ...]
    uncovered_files: tuple[str, ...]
    protected_changes: tuple[str, ...]
    verdict: str


def git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def changed_files(base_sha: str, head_sha: str) -> tuple[str, ...]:
    output = git("diff", "--name-only", "--diff-filter=ACMR", f"{base_sha}...{head_sha}")
    return tuple(line for line in output.splitlines() if line)


def load_manifest(path: Path) -> tuple[bytes, tuple[str, ...], tuple[Surface, ...]]:
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    protected = tuple(str(value) for value in data.get("policy", {}).get("protected", []))
    surfaces = tuple(
        Surface(
            name=str(item["name"]),
            patterns=tuple(str(value) for value in item.get("patterns", [])),
            checks=tuple(str(value) for value in item.get("checks", [])),
        )
        for item in data.get("surfaces", [])
    )
    return raw, protected, surfaces


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def evaluate(
    base_sha: str,
    head_sha: str,
    manifest: Path,
    passed_checks: set[str],
) -> Receipt:
    actual_head = git("rev-parse", head_sha)
    if actual_head != head_sha:
        head_sha = actual_head
    raw_manifest, protected, surfaces = load_manifest(manifest)
    files = changed_files(base_sha, head_sha)
    protected_changes = tuple(path for path in files if matches(path, protected))
    covered: set[str] = set()
    required: set[str] = set()
    matched_surface_names: set[str] = set()
    for surface in surfaces:
        surface_files = {path for path in files if matches(path, surface.patterns)}
        if surface_files:
            covered.update(surface_files)
            required.update(surface.checks)
            matched_surface_names.add(surface.name)
    uncovered = tuple(sorted(set(files) - covered))
    if protected_changes:
        verdict = "invalid"
    elif uncovered or not required.issubset(passed_checks):
        verdict = "insufficient"
    else:
        verdict = "sufficient"
    return Receipt(
        schema="ci-evidence-receipt/v1-draft",
        created_at=dt.datetime.now(dt.UTC).isoformat(),
        base_sha=git("rev-parse", base_sha),
        head_sha=head_sha,
        manifest_sha256=hashlib.sha256(raw_manifest).hexdigest(),
        changed_files=files,
        matched_surfaces=tuple(sorted(matched_surface_names)),
        required_checks=tuple(sorted(required)),
        passed_checks=tuple(sorted(passed_checks)),
        uncovered_files=uncovered,
        protected_changes=protected_changes,
        verdict=verdict,
    )


def command_evaluate(args: argparse.Namespace) -> int:
    passed = {
        value.strip()
        for value in args.passed_checks.split(",")
        if value.strip()
    }
    receipt = evaluate(args.base_sha, args.head_sha, args.manifest, passed)
    payload: dict[str, Any] = asdict(receipt)
    args.receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as stream:
            stream.write(f"verdict={receipt.verdict}\n")
    return 0 if receipt.verdict == "sufficient" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci-evidence-gate")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("evaluate")
    command.add_argument(
        "--base-sha", default=os.environ.get("EVIDENCE_BASE_SHA"), required=False
    )
    command.add_argument(
        "--head-sha", default=os.environ.get("EVIDENCE_HEAD_SHA"), required=False
    )
    command.add_argument(
        "--manifest",
        type=Path,
        default=Path(os.environ.get("EVIDENCE_MANIFEST", ".github/ci-evidence.toml")),
    )
    command.add_argument(
        "--passed-checks", default=os.environ.get("CI_EVIDENCE_PASSED_CHECKS", "")
    )
    command.add_argument("--receipt", type=Path, default=Path("evidence-receipt.json"))
    command.set_defaults(handler=command_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.base_sha or not args.head_sha:
        raise SystemExit("ci-evidence-gate: base and head SHA are required")
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
