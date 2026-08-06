#!/usr/bin/env python3
"""Deterministic structural health analysis for the r4b1t URL corpus.

This tool does not perform network requests and never mutates the corpus. It
produces stable JSON/Markdown evidence suitable for review and CI artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit


_CREDENTIAL_RE = re.compile(r"(?i)\b(https?://)([^/@\s]+)@")


@dataclass(frozen=True)
class Finding:
    line: int
    kind: str
    value: str
    detail: str


@dataclass(frozen=True)
class Metrics:
    source: str
    source_sha256: str
    total_lines: int
    nonempty_lines: int
    valid_urls: int
    unique_exact_urls: int
    exact_duplicate_count: int
    unique_canonical_urls: int
    canonical_duplicate_count: int
    invalid_url_count: int
    credential_url_count: int
    fragment_url_count: int
    http_count: int
    https_count: int
    other_scheme_count: int
    unique_hosts: int
    singleton_hosts: int
    top_10_host_share: float
    host_hhi: float


def normalize_hostname(hostname: str) -> str:
    """Normalize case, a terminal root dot, and IDN spelling for comparison."""
    normalized = hostname.rstrip(".").lower()
    try:
        return normalized.encode("idna").decode("ascii")
    except UnicodeError:
        return normalized


def authority(parts: SplitResult, *, redact_credentials: bool) -> str:
    """Build a normalized authority while preserving non-default ports."""
    hostname = normalize_hostname(parts.hostname or "")
    rendered_host = f"[{hostname}]" if ":" in hostname else hostname
    port = parts.port
    scheme = parts.scheme.lower()
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        rendered_host = f"{rendered_host}:{port}"
    if redact_credentials and (parts.username is not None or parts.password is not None):
        rendered_host = f"[redacted]@{rendered_host}"
    return rendered_host


def redact_url(value: str, parts: SplitResult | None = None) -> str:
    """Return a display-safe URL that never emits embedded user information."""
    if parts is None:
        try:
            parts = urlsplit(value)
            _ = parts.port
        except ValueError:
            return _CREDENTIAL_RE.sub(r"\1[redacted]@", value)
    if parts.scheme and parts.hostname:
        return urlunsplit(
            (
                parts.scheme.lower(),
                authority(parts, redact_credentials=True),
                parts.path,
                parts.query,
                parts.fragment,
            )
        )
    return _CREDENTIAL_RE.sub(r"\1[redacted]@", value)


def canonicalize(parts: SplitResult) -> str:
    """Return a conservative comparison form without path/query rewriting.

    User information and fragments are excluded. Credential-bearing entries are
    reported separately and must not leak secrets into generated evidence.
    """
    return urlunsplit(
        (
            parts.scheme.lower(),
            authority(parts, redact_credentials=False),
            parts.path or "/",
            parts.query,
            "",
        )
    )


def analyze(path: Path) -> tuple[Metrics, list[Finding], Counter[str]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()

    findings: list[Finding] = []
    exact_counts: Counter[str] = Counter()
    canonical_counts: Counter[str] = Counter()
    canonical_variants: dict[str, set[str]] = defaultdict(set)
    host_counts: Counter[str] = Counter()
    valid_urls = 0
    credential_count = 0
    fragment_count = 0
    schemes: Counter[str] = Counter()

    for line_number, raw_line in enumerate(lines, start=1):
        value = raw_line.strip()
        if not value:
            continue

        try:
            parts = urlsplit(value)
            _ = parts.port  # Force validation of malformed ports.
        except ValueError as exc:
            findings.append(
                Finding(line_number, "invalid-url", redact_url(value), str(exc))
            )
            continue

        scheme = parts.scheme.lower()
        if scheme not in {"http", "https"} or not parts.hostname:
            findings.append(
                Finding(
                    line_number,
                    "invalid-url",
                    redact_url(value, parts),
                    "URL must use http/https and contain a hostname",
                )
            )
            schemes[scheme or "missing"] += 1
            continue

        canonical = canonicalize(parts)
        hostname = normalize_hostname(parts.hostname)
        valid_urls += 1
        schemes[scheme] += 1
        exact_counts[value] += 1
        canonical_counts[canonical] += 1
        canonical_variants[canonical].add(value)
        host_counts[hostname] += 1

        if parts.username is not None or parts.password is not None:
            credential_count += 1
            findings.append(
                Finding(
                    line_number,
                    "embedded-credentials",
                    redact_url(value, parts),
                    "User information is embedded in the URL authority",
                )
            )
        if parts.fragment:
            fragment_count += 1

    for value, count in sorted(exact_counts.items()):
        if count > 1:
            findings.append(
                Finding(
                    0,
                    "exact-duplicate",
                    redact_url(value),
                    f"appears {count} times",
                )
            )

    for canonical, variants in sorted(canonical_variants.items()):
        if len(variants) > 1:
            findings.append(
                Finding(
                    0,
                    "canonical-duplicate",
                    canonical,
                    f"{len(variants)} distinct exact entries normalize to this value",
                )
            )

    exact_duplicate_count = valid_urls - len(exact_counts)
    canonical_duplicate_count = len(exact_counts) - len(canonical_counts)
    total_valid = sum(host_counts.values())
    top_10_share = (
        sum(count for _, count in host_counts.most_common(10)) / total_valid
        if total_valid
        else 0.0
    )
    hhi = (
        sum((count / total_valid) ** 2 for count in host_counts.values())
        if total_valid
        else 0.0
    )

    metrics = Metrics(
        source=str(path),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        total_lines=len(lines),
        nonempty_lines=sum(1 for line in lines if line.strip()),
        valid_urls=valid_urls,
        unique_exact_urls=len(exact_counts),
        exact_duplicate_count=exact_duplicate_count,
        unique_canonical_urls=len(canonical_counts),
        canonical_duplicate_count=canonical_duplicate_count,
        invalid_url_count=sum(1 for finding in findings if finding.kind == "invalid-url"),
        credential_url_count=credential_count,
        fragment_url_count=fragment_count,
        http_count=schemes["http"],
        https_count=schemes["https"],
        other_scheme_count=sum(
            count for scheme, count in schemes.items() if scheme not in {"http", "https"}
        ),
        unique_hosts=len(host_counts),
        singleton_hosts=sum(1 for count in host_counts.values() if count == 1),
        top_10_host_share=round(top_10_share, 8),
        host_hhi=round(hhi, 10),
    )
    return metrics, sorted(findings, key=lambda f: (f.kind, f.line, f.value)), host_counts


_POLICY_CHECKS = {
    "min_valid_urls": ("count", "minimum", "valid_urls"),
    "max_invalid_urls": ("count", "maximum", "invalid_url_count"),
    "max_exact_duplicates": ("count", "maximum", "exact_duplicate_count"),
    "max_canonical_duplicates": ("count", "maximum", "canonical_duplicate_count"),
    "max_credential_urls": ("count", "maximum", "credential_url_count"),
    "max_top_10_host_share": ("ratio", "maximum", "top_10_host_share"),
}


def _validate_policy_limit(name: str, value: object) -> str | None:
    kind, _, _ = _POLICY_CHECKS[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"{name}: threshold must be a finite number"
    numeric = float(value)
    if not math.isfinite(numeric):
        return f"{name}: threshold must be a finite number"
    if kind == "count" and (not isinstance(value, int) or value < 0):
        return f"{name}: threshold must be a non-negative integer"
    if kind == "ratio" and not 0.0 <= numeric <= 1.0:
        return f"{name}: threshold must be between 0 and 1"
    return None


def policy_failures(metrics: Metrics, policy: dict[str, object]) -> list[str]:
    failures: list[str] = []

    for name in sorted(policy):
        if name not in _POLICY_CHECKS:
            failures.append(f"unknown policy key: {name}")

    for name, (_, direction, metric_name) in _POLICY_CHECKS.items():
        if name not in policy:
            continue
        limit = policy[name]
        validation_error = _validate_policy_limit(name, limit)
        if validation_error is not None:
            failures.append(validation_error)
            continue

        actual = getattr(metrics, metric_name)
        if direction == "minimum" and actual < limit:
            failures.append(f"{name}: {actual} must be >= {limit}")
        elif direction == "maximum" and actual > limit:
            failures.append(f"{name}: {actual} must be <= {limit}")

    return failures


def _escape_markdown_code(value: str) -> str:
    return value.replace("|", "\\|")


def markdown_report(
    metrics: Metrics,
    findings: list[Finding],
    host_counts: Counter[str],
    failures: list[str],
) -> str:
    rows = "\n".join(
        f"| `{_escape_markdown_code(host)}` | {count} |"
        for host, count in host_counts.most_common(20)
    ) or "| _none_ | 0 |"
    failure_text = (
        "\n".join(f"- {failure}" for failure in failures)
        if failures
        else "- No configured policy failures."
    )
    finding_counts = Counter(finding.kind for finding in findings)
    finding_text = (
        "\n".join(
            f"- **{kind}:** {count}" for kind, count in sorted(finding_counts.items())
        )
        if finding_counts
        else "- No structural findings."
    )
    return f"""# r4b1t Corpus Health Report

Source SHA-256: `{metrics.source_sha256}`

## Structural metrics

- Valid URLs: **{metrics.valid_urls}**
- Unique exact URLs: **{metrics.unique_exact_urls}**
- Exact duplicate entries: **{metrics.exact_duplicate_count}**
- Unique canonical URLs: **{metrics.unique_canonical_urls}**
- Canonical-only duplicate entries: **{metrics.canonical_duplicate_count}**
- Invalid URLs: **{metrics.invalid_url_count}**
- URLs with embedded credentials: **{metrics.credential_url_count}**
- HTTP / HTTPS: **{metrics.http_count} / **{metrics.https_count}**
- Non-HTTP(S) scheme entries: **{metrics.other_scheme_count}**
- Unique hosts: **{metrics.unique_hosts}**
- Singleton hosts: **{metrics.singleton_hosts}**
- Top-10 host share: **{metrics.top_10_host_share:.4%}**
- Host HHI: **{metrics.host_hhi:.8f}**

## Policy result

{failure_text}

## Finding counts

{finding_text}

## Top hosts

| Host | URL count |
|---|---:|
{rows}
"""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("urls.txt"))
    parser.add_argument("--json", type=Path, default=Path("corpus-health.json"))
    parser.add_argument("--markdown", type=Path, default=Path("corpus-health.md"))
    parser.add_argument("--policy", type=Path)
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Exit non-zero when the supplied policy is violated",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.input.is_file():
        print(f"error: corpus not found: {args.input}", file=sys.stderr)
        return 2
    if args.enforce and args.policy is None:
        print("error: --enforce requires --policy", file=sys.stderr)
        return 2

    metrics, findings, host_counts = analyze(args.input)
    policy: dict[str, object] = {}
    if args.policy is not None:
        try:
            loaded = json.loads(args.policy.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read policy: {exc}", file=sys.stderr)
            return 2
        if not isinstance(loaded, dict):
            print("error: policy must be a JSON object", file=sys.stderr)
            return 2
        policy = loaded

    failures = policy_failures(metrics, policy)
    payload = {
        "schema_version": 1,
        "metrics": asdict(metrics),
        "policy": policy,
        "policy_failures": failures,
        "findings": [asdict(finding) for finding in findings],
        "top_hosts": host_counts.most_common(100),
    }

    for output_path in (args.json, args.markdown):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.markdown.write_text(
        markdown_report(metrics, findings, host_counts, failures), encoding="utf-8"
    )

    print(json.dumps(asdict(metrics), sort_keys=True))
    if failures:
        print("policy failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
    return 1 if args.enforce and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
