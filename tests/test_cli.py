from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ci_evidence_gate.cli import (
    _validate_action_context,
    _write_output,
    _write_receipt,
)
from ci_evidence_gate.errors import InvalidEvaluation


class CliSafetyTests(unittest.TestCase):
    def _context(self, root: Path) -> tuple[SimpleNamespace, dict[str, str]]:
        base = "a" * 40
        head = "b" * 40
        event = root / "event.json"
        event.write_text(
            json.dumps(
                {
                    "pull_request": {
                        "base": {"sha": base},
                        "head": {"sha": head},
                    }
                }
            ),
            encoding="utf-8",
        )
        args = SimpleNamespace(
            repository="owner/repo",
            api_url="https://api.github.com",
            base_sha=base,
            head_sha=head,
        )
        environment = {
            "GITHUB_ACTIONS": "true",
            "EVIDENCE_TRUSTED_REPOSITORY": "owner/repo",
            "EVIDENCE_TRUSTED_API_URL": "https://api.github.com",
            "EVIDENCE_TRUSTED_EVENT_NAME": "pull_request",
            "EVIDENCE_TRUSTED_EVENT_PATH": str(event),
        }
        return args, environment

    def test_action_inputs_match_trusted_event_context(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            args, environment = self._context(Path(value))
            with patch.dict(os.environ, environment, clear=True):
                _validate_action_context(args)

    def test_untrusted_api_override_is_rejected_before_network_use(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            args, environment = self._context(Path(value))
            args.api_url = "https://attacker.invalid"
            with (
                patch.dict(os.environ, environment, clear=True),
                self.assertRaisesRegex(InvalidEvaluation, "api-url"),
            ):
                _validate_action_context(args)

    def test_untrusted_sha_override_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            args, environment = self._context(Path(value))
            args.head_sha = "c" * 40
            with (
                patch.dict(os.environ, environment, clear=True),
                self.assertRaisesRegex(InvalidEvaluation, "base-sha/head-sha"),
            ):
                _validate_action_context(args)

    def test_multiline_output_uses_random_delimiter_form(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            output = Path(value) / "github-output"
            with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}):
                _write_output("receipt", "first\nverdict=sufficient")
            lines = output.read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines[0].startswith("receipt<<ci_evidence_gate_"))
        self.assertEqual(lines[1:3], ["first", "verdict=sufficient"])
        self.assertEqual(lines[3], lines[0].split("<<", 1)[1])

    def test_receipt_atomically_replaces_symlink_without_following_it(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            target = root / "target.txt"
            target.write_text("do not overwrite\n", encoding="utf-8")
            receipt = root / "receipt.json"
            receipt.symlink_to(target)
            _write_receipt(receipt, '{"verdict":"invalid"}\n')
            self.assertFalse(receipt.is_symlink())
            self.assertEqual(target.read_text(encoding="utf-8"), "do not overwrite\n")
            self.assertEqual(
                receipt.read_text(encoding="utf-8"), '{"verdict":"invalid"}\n'
            )


if __name__ == "__main__":
    unittest.main()
