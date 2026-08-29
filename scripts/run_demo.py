#!/usr/bin/env python3
"""Build disposable repositories and print all three v1 verdicts."""

from __future__ import annotations

import datetime as dt
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path

from ci_evidence_gate.evaluator import evaluate
from ci_evidence_gate.github import FixtureProvider

MANIFEST = """schema = "ci-evidence-manifest/v1"
[policy]
max_evidence_age_hours = 24
protected = [".github/workflows/evidence.yml"]
[[checks]]
id = "test"
name = "test"
workflow = ".github/workflows/ci.yml"
app_slug = "github-actions"
allowed_conclusions = ["success"]
events = ["pull_request"]
[[surfaces]]
name = "python"
patterns = ["**"]
checks = ["test"]
"""


def git(repo: Path, *arguments: str) -> str:
    # Fixed Git executable and arguments are limited to this disposable fixture.
    executable = shutil.which("git")
    if not executable:
        raise RuntimeError("git executable was not found on PATH")
    return subprocess.run(  # nosec B603
        [executable, *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def make_repo(root: Path, label: str, changed_path: str) -> tuple[Path, str, str]:
    repo = root / label.replace(" ", "-")
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "CI Evidence Gate Demo")
    git(repo, "config", "user.email", "demo@example.invalid")
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / ".github/ci-evidence.toml").write_text(MANIFEST)
    (repo / ".github/workflows/ci.yml").write_text("name: CI\n")
    (repo / ".github/workflows/evidence.yml").write_text("name: Evidence\n")
    (repo / "src/app.py").write_text("VALUE = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    target = repo / changed_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        target.read_text() + "# changed\n" if target.exists() else "changed\n"
    )
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "candidate")
    return repo, base, git(repo, "rev-parse", "HEAD")


def evidence(base: str, head: str, conclusion: str) -> FixtureProvider:
    completed = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
    pull_requests = [{"number": 1, "base": {"sha": base}, "head": {"sha": head}}]
    return FixtureProvider(
        {
            "schema": "ci-evidence-fixture/v1",
            "check_runs": [
                {
                    "id": 56,
                    "name": "test",
                    "head_sha": head,
                    "status": "completed",
                    "conclusion": conclusion,
                    "completed_at": completed,
                    "details_url": "https://github.com/example/demo/actions/runs/34/job/56",
                    "app": {"id": 15368, "slug": "github-actions"},
                    "pull_requests": pull_requests,
                }
            ],
            "workflow_runs": {
                "34": {
                    "id": 34,
                    "head_sha": head,
                    "path": ".github/workflows/ci.yml",
                    "event": "pull_request",
                    "run_attempt": 1,
                    "created_at": completed,
                    "pull_requests": pull_requests,
                }
            },
            "workflow_jobs": {
                "56": {
                    "id": 56,
                    "run_id": 34,
                    "run_attempt": 1,
                    "head_sha": head,
                    "name": "test",
                    "check_run_url": "https://api.github.com/repos/example/demo/check-runs/56",
                }
            },
        }
    )


def scenario(root: Path, label: str, changed_path: str, conclusion: str) -> None:
    repo, base, head = make_repo(root, label, changed_path)
    receipt = evaluate(
        workspace=repo,
        repository="example/demo",
        base_sha=base,
        head_sha=head,
        manifest_path=".github/ci-evidence.toml",
        provider=evidence(base, head, conclusion),
        now=dt.datetime.now(dt.UTC),
    )
    codes = ", ".join(item["code"] for item in receipt["findings"]) or "none"
    print(f"{label:12} {receipt['verdict']:12} findings={codes}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ci-evidence-demo-") as value:
        root = Path(value)
        scenario(root, "valid", "src/app.py", "success")
        scenario(root, "failed test", "src/app.py", "failure")
        scenario(root, "policy edit", ".github/workflows/evidence.yml", "success")


if __name__ == "__main__":
    main()
