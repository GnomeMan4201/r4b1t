from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from tools.corpus_health import (
    analyze,
    canonicalize,
    markdown_report,
    policy_failures,
    redact_url,
)


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
        self.assertEqual(metrics.other_scheme_count, 1)
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
        self.assertEqual(metrics.canonical_duplicate_count, 1)
        self.assertEqual(metrics.fragment_url_count, 1)
        kinds = {finding.kind for finding in findings}
        self.assertIn("exact-duplicate", kinds)
        self.assertIn("canonical-duplicate", kinds)

    def test_exact_duplicates_alone_are_not_canonical_only_duplicates(self) -> None:
        metrics, findings, _ = analyze(
            self.write_corpus("https://example.com\nhttps://example.com\n")
        )
        self.assertEqual(metrics.exact_duplicate_count, 1)
        self.assertEqual(metrics.canonical_duplicate_count, 0)
        self.assertNotIn("canonical-duplicate", {finding.kind for finding in findings})

    def test_embedded_credentials_are_counted_but_never_emitted(self) -> None:
        secret = "https://user:super-secret@example.com/path"
        metrics, findings, _ = analyze(self.write_corpus(f"{secret}\n{secret}\n"))
        self.assertEqual(metrics.credential_url_count, 2)
        rendered = "\n".join(
            finding.value + finding.detail for finding in findings
        )
        self.assertNotIn("super-secret", rendered)
        self.assertIn("[redacted]@example.com", rendered)

    def test_malformed_port_still_redacts_credentials(self) -> None:
        value = "https://user:secret@example.com:invalid/path"
        self.assertNotIn("secret", redact_url(value))
        _, findings, _ = analyze(self.write_corpus(value + "\n"))
        self.assertNotIn("secret", findings[0].value)

    def test_hostname_normalization_is_literal_and_idn_aware(self) -> None:
        self.assertEqual(
            canonicalize(urlsplit("https://world.example/path")),
            "https://world.example/path",
        )
        self.assertEqual(
            canonicalize(urlsplit("https://BÜCHER.example./")),
            "https://xn--bcher-kva.example/",
        )

    def test_policy_failures_have_stable_order(self) -> None:
        metrics, _, _ = analyze(
            self.write_corpus("https://example.com\nhttps://example.com\n")
        )
        failures = policy_failures(
            metrics,
            {
                "max_invalid_urls": 0,
                "max_exact_duplicates": 0,
                "min_valid_urls": 3,
            },
        )
        self.assertEqual(
            failures,
            [
                "min_valid_urls: 2 must be >= 3",
                "max_exact_duplicates: 1 must be <= 0",
            ],
        )

    def test_invalid_and_unknown_policy_values_fail_closed(self) -> None:
        metrics, _, _ = analyze(self.write_corpus("https://example.com\n"))
        self.assertEqual(
            policy_failures(
                metrics,
                {
                    "imaginary_threshold": 1,
                    "max_invalid_urls": True,
                    "max_top_10_host_share": 1.5,
                },
            ),
            [
                "unknown policy key: imaginary_threshold",
                "max_invalid_urls: threshold must be a finite number",
                "max_top_10_host_share: threshold must be between 0 and 1",
            ],
        )

    def test_markdown_report_is_reproducible(self) -> None:
        metrics, findings, hosts = analyze(
            self.write_corpus("https://example.com\n")
        )
        first = markdown_report(metrics, findings, hosts, [])
        second = markdown_report(metrics, findings, hosts, [])
        self.assertEqual(first, second)
        self.assertNotIn("Generated:", first)


if __name__ == "__main__":
    unittest.main()
