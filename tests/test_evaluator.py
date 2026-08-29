from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from ci_evidence_gate.evaluator import evaluate
from ci_evidence_gate.github import FixtureProvider
from tests.helpers import fixture, make_repo, run


class EvaluatorTests(unittest.TestCase):
    def evaluate_repo(
        self, root: Path, changed_path: str = "src/app.py", **fixture_args: object
    ):
        repo, base, head = make_repo(root, changed_path)
        receipt = evaluate(
            workspace=repo,
            repository="example/repo",
            base_sha=base,
            head_sha=head,
            manifest_path=".github/ci-evidence.toml",
            provider=FixtureProvider(fixture(head, **fixture_args)),
            now=dt.datetime.now(dt.UTC),
        )
        return repo, base, head, receipt

    def test_sufficient_exact_sha_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            _, base, head, receipt = self.evaluate_repo(Path(value))
        self.assertEqual(receipt["verdict"], "sufficient")
        self.assertEqual(receipt["subject"], {"base_sha": base, "head_sha": head})
        self.assertEqual(receipt["required_checks"], ["test"])

    def test_failed_check_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            _, _, _, receipt = self.evaluate_repo(Path(value), conclusion="failure")
        self.assertEqual(receipt["verdict"], "insufficient")
        self.assertIn(
            "required-check-conclusion", [item["code"] for item in receipt["findings"]]
        )

    def test_stale_check_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            _, _, _, receipt = self.evaluate_repo(Path(value), hours_old=25)
        self.assertEqual(receipt["verdict"], "insufficient")
        self.assertIn(
            "required-check-stale", [item["code"] for item in receipt["findings"]]
        )

    def test_uncovered_path_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            _, _, _, receipt = self.evaluate_repo(
                Path(value), changed_path="assets/logo.svg"
            )
        self.assertEqual(receipt["verdict"], "insufficient")
        self.assertEqual(receipt["uncovered_files"], ["assets/logo.svg"])

    def test_base_policy_protects_modified_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            _, _, _, receipt = self.evaluate_repo(
                Path(value), changed_path=".github/workflows/evidence.yml"
            )
        self.assertEqual(receipt["verdict"], "invalid")
        self.assertEqual(
            receipt["protected_changes"], [".github/workflows/evidence.yml"]
        )

    def test_manifest_cannot_remove_its_own_protection(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            manifest = repo / ".github/ci-evidence.toml"
            manifest.write_text(
                manifest.read_text().replace(
                    'protected = [".github/workflows/evidence.yml", "tests/**"]',
                    "protected = []",
                )
            )
            run(repo, "git", "add", ".")
            run(repo, "git", "commit", "-qm", "weaken policy")
            head = run(repo, "git", "rev-parse", "HEAD")
            receipt = evaluate(
                workspace=repo,
                repository="example/repo",
                base_sha=base,
                head_sha=head,
                manifest_path=".github/ci-evidence.toml",
                provider=FixtureProvider(fixture(head)),
                now=dt.datetime.now(dt.UTC),
            )
        self.assertEqual(receipt["verdict"], "invalid")
        self.assertIn(".github/ci-evidence.toml", receipt["protected_changes"])

    def test_deleted_protected_file_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, _ = make_repo(root)
            (repo / "tests").mkdir(exist_ok=True)
            (repo / "tests/proof.txt").write_text("proof")
            run(repo, "git", "add", ".")
            run(repo, "git", "commit", "-qm", "add protected")
            base = run(repo, "git", "rev-parse", "HEAD")
            (repo / "tests/proof.txt").unlink()
            run(repo, "git", "add", "-u")
            run(repo, "git", "commit", "-qm", "delete protected")
            head = run(repo, "git", "rev-parse", "HEAD")
            receipt = evaluate(
                workspace=repo,
                repository="example/repo",
                base_sha=base,
                head_sha=head,
                manifest_path=".github/ci-evidence.toml",
                provider=FixtureProvider(fixture(head)),
                now=dt.datetime.now(dt.UTC),
            )
        self.assertEqual(receipt["verdict"], "invalid")

    def test_wrong_workflow_identity_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head)
            payload["workflow_runs"]["77"]["path"] = ".github/workflows/spoof.yml"  # type: ignore[index]
            receipt = evaluate(
                workspace=repo,
                repository="example/repo",
                base_sha=base,
                head_sha=head,
                manifest_path=".github/ci-evidence.toml",
                provider=FixtureProvider(payload),
                now=dt.datetime.now(dt.UTC),
            )
        self.assertEqual(receipt["verdict"], "insufficient")

    def test_latest_rerun_failure_beats_old_success(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head)
            old_check = payload["check_runs"][0]  # type: ignore[index]
            old_check["details_url"] = (
                "https://github.com/example/repo/actions/runs/76/job/88"
            )
            payload["workflow_runs"]["76"] = {  # type: ignore[index]
                "id": 76,
                "head_sha": head,
                "path": ".github/workflows/ci.yml",
                "event": "pull_request",
                "run_attempt": 1,
            }
            failed = dict(old_check)
            failed.update(
                {
                    "id": 103,
                    "conclusion": "failure",
                    "details_url": "https://github.com/example/repo/actions/runs/77/job/89",
                }
            )
            payload["check_runs"].append(failed)  # type: ignore[union-attr]
            payload["workflow_runs"]["77"]["run_attempt"] = 2  # type: ignore[index]
            receipt = evaluate(
                workspace=repo,
                repository="example/repo",
                base_sha=base,
                head_sha=head,
                manifest_path=".github/ci-evidence.toml",
                provider=FixtureProvider(payload),
                now=dt.datetime.now(dt.UTC),
            )
        self.assertEqual(receipt["verdict"], "insufficient")
        self.assertEqual(receipt["check_evidence"][0]["run_attempt"], 2)

    def test_skipped_check_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            _, _, _, receipt = self.evaluate_repo(Path(value), conclusion="skipped")
        self.assertEqual(receipt["verdict"], "insufficient")

    def test_in_progress_check_is_insufficient_not_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head)
            check = payload["check_runs"][0]  # type: ignore[index]
            check.update(
                {"status": "in_progress", "conclusion": None, "completed_at": None}
            )
            receipt = evaluate(
                workspace=repo,
                repository="example/repo",
                base_sha=base,
                head_sha=head,
                manifest_path=".github/ci-evidence.toml",
                provider=FixtureProvider(payload),
                now=dt.datetime.now(dt.UTC),
            )
        self.assertEqual(receipt["verdict"], "insufficient")
        codes = [item["code"] for item in receipt["findings"]]
        self.assertIn("required-check-incomplete", codes)

    def test_pull_request_target_evidence_is_rejected_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head)
            payload["workflow_runs"]["77"]["event"] = "pull_request_target"  # type: ignore[index]
            receipt = evaluate(
                workspace=repo,
                repository="example/repo",
                base_sha=base,
                head_sha=head,
                manifest_path=".github/ci-evidence.toml",
                provider=FixtureProvider(payload),
                now=dt.datetime.now(dt.UTC),
            )
        self.assertEqual(receipt["verdict"], "insufficient")


if __name__ == "__main__":
    unittest.main()
