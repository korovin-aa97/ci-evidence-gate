"""Command-line entry point for CI Evidence Gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from .errors import GateError
from .evaluator import RECEIPT_SCHEMA, TOOL_VERSION, evaluate
from .github import FixtureProvider, GitHubClient


def _annotation(level: str, message: str) -> None:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::{level} title=CI Evidence Gate::{escaped}")


def _write_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as stream:
            stream.write(f"{name}={value}\n")


def _write_summary(receipt: dict[str, Any]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        "## CI Evidence Gate",
        "",
        f"**Verdict:** `{receipt['verdict']}`",
        "",
        f"Subject: `{receipt['subject']['head_sha']}`",
        "",
    ]
    findings = receipt.get("findings", [])
    if findings:
        lines.extend(["### Findings", ""])
        lines.extend(f"- `{item['code']}` — {item['message']}" for item in findings)
        lines.append("")
    with Path(summary_path).open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines))


def _invalid_receipt(args: argparse.Namespace, message: str) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "tool": {"name": "ci-evidence-gate", "version": TOOL_VERSION},
        "repository": args.repository or "unknown",
        "subject": {"base_sha": args.base_sha or "", "head_sha": args.head_sha or ""},
        "findings": [
            {
                "code": "evaluation-invalid",
                "message": message,
                "check_id": None,
                "path": None,
            }
        ],
        "verdict": "invalid",
    }


def command_evaluate(args: argparse.Namespace) -> int:
    receipt_path: Path = args.receipt
    try:
        if args.evidence_fixture:
            payload = json.loads(args.evidence_fixture.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("fixture root must be an object")
            provider = FixtureProvider(payload)
        else:
            provider = GitHubClient(
                repository=args.repository,
                token=args.token,
                api_url=args.api_url,
                api_version=args.api_version,
            )
        receipt = evaluate(
            workspace=args.workspace,
            repository=args.repository,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
            manifest_path=args.manifest,
            provider=provider,
        )
    except (GateError, json.JSONDecodeError, OSError, ValueError) as exc:
        message = str(exc) or exc.__class__.__name__
        receipt = _invalid_receipt(args, message)
        _annotation("error", message)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    receipt_path.write_text(serialized, encoding="utf-8")
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    print(serialized, end="")
    verdict = str(receipt["verdict"])
    _write_output("verdict", verdict)
    _write_output("receipt", str(receipt_path))
    _write_output("receipt-sha256", digest)
    _write_summary(receipt)
    if verdict == "sufficient":
        _annotation("notice", f"Evidence is sufficient for {args.head_sha}")
        return 0
    for finding in receipt.get("findings", []):
        _annotation(
            "warning" if verdict == "insufficient" else "error", finding["message"]
        )
    return 1 if verdict == "insufficient" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci-evidence-gate")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {TOOL_VERSION}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("evaluate", help="evaluate exact-SHA CI evidence")
    command.add_argument("--base-sha", default=os.environ.get("EVIDENCE_BASE_SHA"))
    command.add_argument("--head-sha", default=os.environ.get("EVIDENCE_HEAD_SHA"))
    command.add_argument("--repository", default=os.environ.get("EVIDENCE_REPOSITORY"))
    command.add_argument("--token", default=os.environ.get("EVIDENCE_TOKEN", ""))
    command.add_argument(
        "--api-url",
        default=os.environ.get("EVIDENCE_API_URL", "https://api.github.com"),
    )
    command.add_argument(
        "--api-version", default=os.environ.get("EVIDENCE_API_VERSION", "2022-11-28")
    )
    command.add_argument(
        "--manifest",
        default=os.environ.get("EVIDENCE_MANIFEST", ".github/ci-evidence.toml"),
    )
    command.add_argument(
        "--workspace", type=Path, default=Path(os.environ.get("GITHUB_WORKSPACE", "."))
    )
    command.add_argument(
        "--receipt",
        type=Path,
        default=Path(os.environ.get("EVIDENCE_RECEIPT", "ci-evidence-receipt.json")),
    )
    command.add_argument("--evidence-fixture", type=Path, help=argparse.SUPPRESS)
    command.set_defaults(handler=command_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    missing = [
        name
        for name in ("base_sha", "head_sha", "repository")
        if not getattr(args, name)
    ]
    if missing:
        print(
            f"ci-evidence-gate: missing required values: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 2
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
