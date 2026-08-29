from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path

MANIFEST = b"""schema = "ci-evidence-manifest/v1"

[policy]
max_evidence_age_hours = 24
protected = [".github/workflows/evidence.yml", "tests/**"]

[[checks]]
id = "test"
name = "test"
workflow = ".github/workflows/ci.yml"
app_slug = "github-actions"
allowed_conclusions = ["success"]
events = ["pull_request"]

[[surfaces]]
name = "python"
patterns = ["src/**/*.py", "pyproject.toml"]
checks = ["test"]
"""


def run(repo: Path, *args: str) -> str:
    return subprocess.run(
        args,
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def make_repo(root: Path, changed_path: str = "src/app.py") -> tuple[Path, str, str]:
    repo = root / "repo"
    repo.mkdir()
    run(repo, "git", "init", "-q")
    run(repo, "git", "config", "user.email", "tests@example.invalid")
    run(repo, "git", "config", "user.name", "CI Evidence Gate Tests")
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / ".github/ci-evidence.toml").write_bytes(MANIFEST)
    (repo / ".github/workflows/ci.yml").write_text("name: CI\n", encoding="utf-8")
    (repo / ".github/workflows/evidence.yml").write_text(
        "name: Evidence\n", encoding="utf-8"
    )
    (repo / "src/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    run(repo, "git", "add", ".")
    run(repo, "git", "commit", "-qm", "base")
    base = run(repo, "git", "rev-parse", "HEAD")
    target = repo / changed_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        target.read_text(encoding="utf-8") + "# change\n"
        if target.exists()
        else "changed\n",
        encoding="utf-8",
    )
    run(repo, "git", "add", ".")
    run(repo, "git", "commit", "-qm", "head")
    head = run(repo, "git", "rev-parse", "HEAD")
    return repo, base, head


def fixture(
    head: str, *, conclusion: str = "success", attempt: int = 1, hours_old: int = 0
) -> dict[str, object]:
    completed = dt.datetime.now(dt.UTC) - dt.timedelta(hours=hours_old)
    return {
        "schema": "ci-evidence-fixture/v1",
        "check_runs": [
            {
                "id": 101 + attempt,
                "name": "test",
                "head_sha": head,
                "status": "completed",
                "conclusion": conclusion,
                "completed_at": completed.isoformat().replace("+00:00", "Z"),
                "details_url": "https://github.com/example/repo/actions/runs/77/job/88",
                "app": {"id": 15368, "slug": "github-actions"},
            }
        ],
        "workflow_runs": {
            "77": {
                "id": 77,
                "head_sha": head,
                "path": ".github/workflows/ci.yml",
                "event": "pull_request",
                "run_attempt": attempt,
            }
        },
    }


def write_fixture(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
