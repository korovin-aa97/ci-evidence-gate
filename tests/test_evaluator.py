from __future__ import annotations

import copy
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from ci_evidence_gate.errors import InvalidEvaluation
from ci_evidence_gate.evaluator import evaluate
from ci_evidence_gate.github import FixtureProvider
from tests.helpers import fixture, make_repo, run


class NoNetworkProvider:
    def check_runs(self, head_sha: str):
        raise AssertionError("protected changes must not query check runs")

    def workflow_run(self, run_id: int):
        raise AssertionError("protected changes must not query workflow runs")

    def workflow_job(self, job_id: int):
        raise AssertionError("protected changes must not query workflow jobs")


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
            provider=FixtureProvider(fixture(head, base=base, **fixture_args)),
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
            root = Path(value)
            repo, base, head = make_repo(
                root, changed_path=".github/workflows/evidence.yml"
            )
            receipt = evaluate(
                workspace=repo,
                repository="example/repo",
                base_sha=base,
                head_sha=head,
                manifest_path=".github/ci-evidence.toml",
                provider=NoNetworkProvider(),
                now=dt.datetime.now(dt.UTC),
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
                provider=FixtureProvider(fixture(head, base=base)),
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
                provider=FixtureProvider(fixture(head, base=base)),
                now=dt.datetime.now(dt.UTC),
            )
        self.assertEqual(receipt["verdict"], "invalid")

    def test_wrong_workflow_identity_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head, base=base)
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
            payload = fixture(head, base=base)
            old_check = payload["check_runs"][0]  # type: ignore[index]
            failed = dict(old_check)
            failed.update(
                {
                    "id": 103,
                    "conclusion": "failure",
                    "details_url": "https://github.com/example/repo/actions/runs/77/job/103",
                }
            )
            payload["check_runs"].append(failed)  # type: ignore[union-attr]
            payload["workflow_runs"]["77"]["run_attempt"] = 2  # type: ignore[index]
            payload["workflow_jobs"]["103"] = {  # type: ignore[index]
                "id": 103,
                "run_id": 77,
                "run_attempt": 2,
                "head_sha": head,
                "name": "test",
                "check_run_url": "https://api.github.com/repos/example/repo/check-runs/103",
            }
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

    def test_successful_rerun_selects_concrete_latest_job(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head, base=base)
            rerun = copy.deepcopy(payload["check_runs"][0])  # type: ignore[index]
            rerun.update(
                {
                    "id": 103,
                    "details_url": "https://github.com/example/repo/actions/runs/77/job/103",
                }
            )
            payload["check_runs"].append(rerun)  # type: ignore[union-attr]
            payload["workflow_runs"]["77"]["run_attempt"] = 2  # type: ignore[index]
            payload["workflow_jobs"]["103"] = {  # type: ignore[index]
                "id": 103,
                "run_id": 77,
                "run_attempt": 2,
                "head_sha": head,
                "name": "test",
                "check_run_url": "https://api.github.com/repos/example/repo/check-runs/103",
            }
            receipt = evaluate(
                workspace=repo,
                repository="example/repo",
                base_sha=base,
                head_sha=head,
                manifest_path=".github/ci-evidence.toml",
                provider=FixtureProvider(payload),
                now=dt.datetime.now(dt.UTC),
            )
        self.assertEqual(receipt["verdict"], "sufficient")
        self.assertEqual(receipt["check_evidence"][0]["check_run_id"], 103)
        self.assertEqual(receipt["check_evidence"][0]["run_attempt"], 2)

    def test_newer_workflow_run_beats_higher_attempt_from_older_run(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head, base=base, attempt=3, hours_old=1)
            newer = copy.deepcopy(payload["check_runs"][0])  # type: ignore[index]
            newer.update(
                {
                    "id": 104,
                    "conclusion": "failure",
                    "details_url": "https://github.com/example/repo/actions/runs/78/job/104",
                }
            )
            payload["check_runs"].append(newer)  # type: ignore[union-attr]
            created = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
            payload["workflow_runs"]["78"] = {  # type: ignore[index]
                "id": 78,
                "head_sha": head,
                "path": ".github/workflows/ci.yml",
                "event": "pull_request",
                "run_attempt": 1,
                "created_at": created,
                "pull_requests": copy.deepcopy(newer["pull_requests"]),
            }
            payload["workflow_jobs"]["104"] = {  # type: ignore[index]
                "id": 104,
                "run_id": 78,
                "run_attempt": 1,
                "head_sha": head,
                "name": "test",
                "check_run_url": "https://api.github.com/repos/example/repo/check-runs/104",
            }
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
        self.assertEqual(receipt["check_evidence"][0]["workflow_run_id"], 78)
        self.assertEqual(receipt["check_evidence"][0]["run_attempt"], 1)

    def test_pull_request_evidence_must_match_exact_base_and_head(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head, base=base)
            payload["workflow_runs"]["77"]["pull_requests"][0]["base"]["sha"] = (  # type: ignore[index]
                "f" * 40
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
        self.assertIn(
            "required-check-missing", [item["code"] for item in receipt["findings"]]
        )

    def test_fork_pull_request_association_uses_sha_not_repository_owner(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head, base=base)
            association = payload["workflow_runs"]["77"]["pull_requests"][0]  # type: ignore[index]
            association["head"]["repo"] = {"full_name": "contributor/fork"}
            receipt = evaluate(
                workspace=repo,
                repository="example/repo",
                base_sha=base,
                head_sha=head,
                manifest_path=".github/ci-evidence.toml",
                provider=FixtureProvider(payload),
                now=dt.datetime.now(dt.UTC),
            )
        self.assertEqual(receipt["verdict"], "sufficient")

    def test_malformed_expected_actions_details_url_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head, base=base)
            payload["check_runs"][0]["details_url"] = "https://example.invalid/no-job"  # type: ignore[index]
            with self.assertRaisesRegex(InvalidEvaluation, "malformed.*details_url"):
                evaluate(
                    workspace=repo,
                    repository="example/repo",
                    base_sha=base,
                    head_sha=head,
                    manifest_path=".github/ci-evidence.toml",
                    provider=FixtureProvider(payload),
                    now=dt.datetime.now(dt.UTC),
                )

    def test_missing_check_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head, base=base)
            payload["check_runs"] = []
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

    def test_skipped_check_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            _, _, _, receipt = self.evaluate_repo(Path(value), conclusion="skipped")
        self.assertEqual(receipt["verdict"], "insufficient")

    def test_in_progress_check_is_insufficient_not_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head, base=base)
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
        self.assertEqual(codes, ["required-check-incomplete"])

    def test_pull_request_target_evidence_is_rejected_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            repo, base, head = make_repo(root)
            payload = fixture(head, base=base)
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
