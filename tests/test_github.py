from __future__ import annotations

import io
import json
import unittest
import urllib.error
import urllib.request
from email.message import Message
from unittest.mock import MagicMock

from ci_evidence_gate.errors import ApiError, InvalidEvaluation
from ci_evidence_gate.github import (
    MAX_RESPONSE_BYTES,
    GitHubClient,
    _SameOriginRedirectHandler,
    check_run_id,
    workflow_job_reference,
    workflow_run_id,
)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class GitHubClientTests(unittest.TestCase):
    def test_collects_exact_sha_with_read_only_get(self) -> None:
        payload = json.dumps({"check_runs": [{"id": 1}]}).encode()
        client = GitHubClient("owner/repo", "token")
        mocked = MagicMock(return_value=Response(payload))
        client._opener.open = mocked
        self.assertEqual(client.check_runs("a" * 40), [{"id": 1}])
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertIn("/commits/" + "a" * 40 + "/check-runs", request.full_url)
        self.assertEqual(request.headers["Authorization"], "Bearer token")

    def test_rejects_non_https_api_origin(self) -> None:
        with self.assertRaisesRegex(InvalidEvaluation, "HTTPS"):
            GitHubClient("owner/repo", "token", api_url="http://attacker.invalid")

    def test_rejects_missing_token_before_request(self) -> None:
        with self.assertRaisesRegex(InvalidEvaluation, "token"):
            GitHubClient("owner/repo", "")

    def test_rejects_api_url_query_and_fragment(self) -> None:
        with self.assertRaisesRegex(InvalidEvaluation, "query"):
            GitHubClient(
                "owner/repo", "token", api_url="https://api.github.com?redirect=1"
            )

    def test_rejects_cross_origin_redirect_before_forwarding_token(self) -> None:
        handler = _SameOriginRedirectHandler(("https", "api.github.com", 443))
        request = urllib.request.Request(
            "https://api.github.com/repos/o/r",
            headers={"Authorization": "Bearer token"},
        )
        response = io.BytesIO()
        try:
            with self.assertRaisesRegex(
                urllib.error.HTTPError, "cross-origin"
            ) as raised:
                handler.redirect_request(
                    request,
                    response,
                    302,
                    "Found",
                    Message(),
                    "https://attacker.invalid/collect",
                )
            raised.exception.close()
        finally:
            response.close()

    def test_rate_limit_fails_closed_without_retry(self) -> None:
        headers = Message()
        headers["X-RateLimit-Remaining"] = "0"
        headers["X-RateLimit-Reset"] = "1788036000"
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/o/r",
            403,
            "Forbidden",
            headers,
            io.BytesIO(b'{"message":"rate limit exceeded"}'),
        )
        client = GitHubClient("owner/repo", "token")
        client._opener.open = MagicMock(side_effect=error)
        with self.assertRaisesRegex(ApiError, "rate limit exceeded.*reset=1788036000"):
            client.check_runs("a" * 40)
        self.assertEqual(client._opener.open.call_count, 1)

    def test_permission_error_fails_closed_without_retry(self) -> None:
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/o/r",
            403,
            "Forbidden",
            Message(),
            io.BytesIO(b'{"message":"Resource not accessible by integration"}'),
        )
        client = GitHubClient("owner/repo", "token")
        client._opener.open = MagicMock(side_effect=error)
        with self.assertRaisesRegex(ApiError, "HTTP 403.*Resource not accessible"):
            client.check_runs("a" * 40)
        self.assertEqual(client._opener.open.call_count, 1)

    def test_invalid_json_response_is_rejected(self) -> None:
        client = GitHubClient("owner/repo", "token")
        client._opener.open = MagicMock(return_value=Response(b"not-json"))
        with self.assertRaisesRegex(ApiError, "invalid JSON"):
            client.check_runs("a" * 40)

    def test_workflow_job_lookup_is_cached(self) -> None:
        payload = json.dumps({"id": 123, "run_attempt": 2}).encode()
        client = GitHubClient("owner/repo", "token")
        client._opener.open = MagicMock(return_value=Response(payload))
        self.assertEqual(client.workflow_job(123)["run_attempt"], 2)
        self.assertEqual(client.workflow_job(123)["run_attempt"], 2)
        self.assertEqual(client._opener.open.call_count, 1)

    def test_rejects_oversized_response(self) -> None:
        client = GitHubClient("owner/repo", "token")
        client._opener.open = MagicMock(
            return_value=Response(b"x" * (MAX_RESPONSE_BYTES + 1))
        )
        with self.assertRaisesRegex(ApiError, "response exceeded"):
            client.check_runs("a" * 40)

    def test_extracts_workflow_run_id(self) -> None:
        self.assertEqual(
            workflow_run_id("https://github.com/o/r/actions/runs/123/job/456"), 123
        )
        self.assertIsNone(workflow_run_id("https://checks.example.invalid/123"))
        self.assertEqual(
            workflow_job_reference(
                "https://github.com/o/r/actions/runs/123/job/456?pr=1"
            ),
            (123, 456),
        )
        self.assertEqual(
            check_run_id("https://api.github.com/repos/o/r/check-runs/789"), 789
        )


if __name__ == "__main__":
    unittest.main()
