#!/usr/bin/env python3
"""Check inexpensive release and supply-chain invariants."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
RELEASE_VERSION = "0.1.3"
RELEASE_COMMIT_SHA = "0a7afe3091057f4913dffa0d970ecb3937ba8c9b"


def fail(message: str) -> None:
    print(f"release validation: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    required = [
        "LICENSE",
        "NOTICE",
        "README.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "action.yml",
        "docs/DEMO.md",
        "docs/RFC.md",
        "docs/THREAT_MODEL.md",
        "docs/assets/ci-evidence-gate-demo.gif",
        "docs/assets/ci-evidence-gate-launch-card.png",
        "docs/assets/ci-evidence-gate-launch-card.svg",
        "docs/assets/ci-evidence-gate-square.png",
        "docs/assets/ci-evidence-gate-square.svg",
        "examples/sample-receipt.json",
        "schemas/manifest-v1.schema.json",
        "schemas/receipt-v1.schema.json",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        fail("missing release files: " + ", ".join(missing))

    versions = {
        re.search(r'version = "([^"]+)"', (ROOT / "pyproject.toml").read_text()).group(
            1
        ),  # type: ignore[union-attr]
        re.search(
            r'__version__ = "([^"]+)"',
            (ROOT / "src/ci_evidence_gate/__init__.py").read_text(),
        ).group(1),  # type: ignore[union-attr]
        re.search(
            r'TOOL_VERSION = "([^"]+)"',
            (ROOT / "src/ci_evidence_gate/evaluator.py").read_text(),
        ).group(1),  # type: ignore[union-attr]
        re.search(
            r'"User-Agent": "ci-evidence-gate/([^"]+)"',
            (ROOT / "src/ci_evidence_gate/github.py").read_text(),
        ).group(1),  # type: ignore[union-attr]
    }
    if versions != {RELEASE_VERSION}:
        fail(f"inconsistent versions: {sorted(versions)}")

    metadata = (ROOT / "action.yml").read_text(encoding="utf-8")
    for field in ("name:", "description:", "author:", "branding:", "runs:"):
        if field not in metadata:
            fail(f"action.yml lacks {field}")

    expected_pin = (
        f"korovin-aa97/ci-evidence-gate@{RELEASE_COMMIT_SHA} # v{RELEASE_VERSION}"
    )
    for path in [
        ROOT / "README.md",
        ROOT / "docs/PINNING.md",
        ROOT / "examples/sample-repository/.github/workflows/ci.yml",
    ]:
        if expected_pin not in path.read_text(encoding="utf-8"):
            fail(f"{path.relative_to(ROOT)} does not pin the current release commit")

    for path in [
        ROOT / "action.yml",
        *sorted((ROOT / ".github/workflows").glob("*.yml")),
        *sorted((ROOT / "examples").rglob("*.yml")),
    ]:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            match = re.search(r"\buses:\s*([^\s#]+)", line)
            if not match:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            if reference.startswith("docker://"):
                if "@sha256:" not in reference:
                    fail(
                        f"{path.relative_to(ROOT)}:{line_number} docker action is not digest-pinned"
                    )
                continue
            if "@" not in reference or not FULL_SHA.fullmatch(
                reference.rsplit("@", 1)[1]
            ):
                if reference.endswith("@RELEASE_COMMIT_SHA"):
                    continue
                fail(
                    f"{path.relative_to(ROOT)}:{line_number} action is not full-SHA pinned: {reference}"
                )

    json.loads((ROOT / "schemas/manifest-v1.schema.json").read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schemas/receipt-v1.schema.json").read_text(encoding="utf-8")
    )
    if schema.get("properties", {}).get("verdict", {}).get("enum") != [
        "sufficient",
        "insufficient",
        "invalid",
    ]:
        fail("receipt schema verdict enum drifted")

    sample = json.loads(
        (ROOT / "examples/sample-receipt.json").read_text(encoding="utf-8")
    )
    if sample.get("schema") != "ci-evidence-receipt/v1":
        fail("sample receipt schema drifted")
    if sample.get("tool", {}).get("version") != RELEASE_VERSION:
        fail("sample receipt version drifted")
    if sample.get("verdict") != "sufficient" or sample.get("findings") != []:
        fail("sample receipt is not the clean sufficient scenario")

    square = (ROOT / "docs/assets/ci-evidence-gate-square.png").read_bytes()
    if square[:8] != b"\x89PNG\r\n\x1a\n":
        fail("square launch card is not a PNG")
    width = int.from_bytes(square[16:20], "big")
    height = int.from_bytes(square[20:24], "big")
    if (width, height) != (1080, 1080):
        fail(f"square launch card is {width}x{height}, expected 1080x1080")

    launch_card = (ROOT / "docs/assets/ci-evidence-gate-launch-card.png").read_bytes()
    if launch_card[:8] != b"\x89PNG\r\n\x1a\n":
        fail("1200x630 launch card is not a PNG")
    width = int.from_bytes(launch_card[16:20], "big")
    height = int.from_bytes(launch_card[20:24], "big")
    if (width, height) != (1200, 630):
        fail(f"launch card is {width}x{height}, expected 1200x630")

    demo = (ROOT / "docs/assets/ci-evidence-gate-demo.gif").read_bytes()
    if demo[:6] not in {b"GIF87a", b"GIF89a"}:
        fail("terminal demo is not a GIF")
    width = int.from_bytes(demo[6:8], "little")
    height = int.from_bytes(demo[8:10], "little")
    if (width, height) != (1280, 720):
        fail(f"terminal demo is {width}x{height}, expected 1280x720")

    forbidden = [
        "Compensa" + "Me",
        "/Users/" + "alexander",
        "remote-" + "fleet",
        "remote-" + "qa",
        "remote-" + "feature",
    ]
    scan_suffixes = {".md", ".py", ".toml", ".yml", ".yaml", ".json"}
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or ".git" in path.parts
            or path.suffix not in scan_suffixes
        ):
            continue
        content = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in content:
                fail(f"private marker {marker!r} found in {path.relative_to(ROOT)}")

    print("release validation: ok")


if __name__ == "__main__":
    main()
