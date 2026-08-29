from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from ci_evidence_gate.errors import InvalidEvaluation
from ci_evidence_gate.github import GitHubClient, workflow_run_id


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class GitHubClientTests(unittest.TestCase):
    def test_collects_exact_sha_with_read_only_get(self) -> None:
        payload = json.dumps({"check_runs": [{"id": 1}]}).encode()
        with patch("urllib.request.urlopen", return_value=Response(payload)) as mocked:
            client = GitHubClient("owner/repo", "token")
            self.assertEqual(client.check_runs("a" * 40), [{"id": 1}])
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertIn("/commits/" + "a" * 40 + "/check-runs", request.full_url)
        self.assertEqual(request.headers["Authorization"], "Bearer token")

    def test_rejects_non_https_api_origin(self) -> None:
        with self.assertRaisesRegex(InvalidEvaluation, "HTTPS"):
            GitHubClient("owner/repo", "token", api_url="http://attacker.invalid")

    def test_extracts_workflow_run_id(self) -> None:
        self.assertEqual(
            workflow_run_id("https://github.com/o/r/actions/runs/123/job/456"), 123
        )
        self.assertIsNone(workflow_run_id("https://checks.example.invalid/123"))


if __name__ == "__main__":
    unittest.main()
