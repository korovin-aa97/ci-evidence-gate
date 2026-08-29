from __future__ import annotations

import unittest

from ci_evidence_gate.errors import InvalidEvaluation
from ci_evidence_gate.manifest import parse_manifest
from ci_evidence_gate.patterns import matches
from tests.helpers import MANIFEST


class ManifestTests(unittest.TestCase):
    def test_valid_manifest(self) -> None:
        manifest = parse_manifest(MANIFEST)
        self.assertEqual(manifest.schema, "ci-evidence-manifest/v1")
        self.assertEqual(manifest.checks[0].id, "test")

    def test_unknown_check_is_invalid(self) -> None:
        raw = MANIFEST.replace(b'checks = ["test"]', b'checks = ["missing"]')
        with self.assertRaisesRegex(InvalidEvaluation, "unknown ids"):
            parse_manifest(raw)

    def test_unknown_key_is_invalid(self) -> None:
        raw = MANIFEST.replace(b"[policy]\n", b"[policy]\ntrust_me = true\n")
        with self.assertRaisesRegex(InvalidEvaluation, "unknown policy keys"):
            parse_manifest(raw)

    def test_globstar_matches_root_and_nested_files(self) -> None:
        self.assertTrue(matches("src/app.py", ("src/**/*.py",)))
        self.assertTrue(matches("src/pkg/app.py", ("src/**/*.py",)))
        self.assertFalse(matches("src/app.js", ("src/**/*.py",)))


if __name__ == "__main__":
    unittest.main()
