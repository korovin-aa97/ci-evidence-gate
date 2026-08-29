#!/usr/bin/env python3
"""Check inexpensive release and supply-chain invariants."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


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
        "docs/RFC.md",
        "docs/THREAT_MODEL.md",
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
    if versions != {"0.1.3"}:
        fail(f"inconsistent versions: {sorted(versions)}")

    metadata = (ROOT / "action.yml").read_text(encoding="utf-8")
    for field in ("name:", "description:", "author:", "branding:", "runs:"):
        if field not in metadata:
            fail(f"action.yml lacks {field}")

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
