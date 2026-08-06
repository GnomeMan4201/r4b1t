from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.corpus_health import analyze, canonicalize, policy_failures
from urllib.parse import urlsplit


class CorpusHealthTests(unittest.TestCase):
    def write_corpus(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "urls.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def test_empty_lines_are_not_urls(self) -> None:
        metrics, findings, hosts = analyze(
            self.write_corpus("\nhttps://example.com\n   \n")
        )
        self.assertEqual(metrics.total_lines, 3)
        self.assertEqual(metrics.nonempty_lines, 1)
        self.assertEqual(metrics.valid_urls, 1)
        self.assertEqual(metrics.unique_hosts, 1)
        self.assertEqual(findings, [])
        self.assertEqual(hosts["example.com"], 1)

    def test_invalid_schemes_hosts_and_ports_are_reported(self) -> None:
        corpus = "\n".join(
            [
                "ftp://example.com/file",
                "https:///missing-host",
                "https://example.com:invalid/",
            ]
        )
        metrics, findings, _ = analyze(self.write_corpus(corpus))
        self.assertEqual(metrics.valid_urls, 0)
        self.assertEqual(metrics.invalid_url_count, 3)
        self.assertEqual({finding.kind for finding in findings}, {"invalid-url"})

    def test_exact_and_canonical_duplicates_are_distinguished(self) -> None:
        corpus = "\n".join(
            [
                "https://example.com",
                "https://example.com",
                "https://EXAMPLE.com:443/#fragment",
            ]
        )
        metrics, findings, _ = analyze(self.write_corpus(corpus))
        self.assertEqual(metrics.valid_urls, 3)
        self.assertEqual(metrics.exact_duplicate_count, 1)
        self.assertEqual(metrics.canonical_duplicate_count, 2)
        self.assertEqual(metrics.fragment_url_count, 1)
        kinds = {finding.kind for finding in findings}
        self.assertIn("exact-duplicate", kinds)
        self.assertIn("canonical-duplicate", kinds)

    def test_embedded_credentials_are_visible(self) -> None:
        metrics, findings, _ = analyze(
            self.write_corpus("https://user:secret@example.com/path\n")
        )
        self.assertEqual(metrics.credential_url_count, 1)
        self.assertEqual(findings[0].kind, "embedded-credentials")

    def test_hostname_normalization_does_not_use_character_lstrip(self) -> None:
        canonical = canonicalize(urlsplit("https://world.example/path"))
        self.assertEqual(canonical, "https://world.example/path")

    def test_policy_failures_are_deterministic(self) -> None:
        metrics, _, _ = analyze(
            self.write_corpus("https://example.com\nhttps://example.com\n")
        )
        failures = policy_failures(
            metrics,
            {
                "min_valid_urls": 3,
                "max_exact_duplicates": 0,
                "max_invalid_urls": 0,
            },
        )
        self.assertEqual(
            failures,
            [
                "min_valid_urls: 2 must be >= 3",
                "max_exact_duplicates: 1 must be <= 0",
            ],
        )

    def test_unknown_policy_key_fails_closed(self) -> None:
        metrics, _, _ = analyze(self.write_corpus("https://example.com\n"))
        self.assertEqual(
            policy_failures(metrics, {"imaginary_threshold": 1}),
            ["unknown policy key: imaginary_threshold"],
        )


if __name__ == "__main__":
    unittest.main()
