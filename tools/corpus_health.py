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
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit


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


def canonicalize(parts: SplitResult) -> str:
    """Return a conservative comparison form without changing path/query data."""
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        host = f"{host}:{port}"
    if parts.username is not None:
        userinfo = parts.username
        if parts.password is not None:
            userinfo += f":{parts.password}"
        host = f"{userinfo}@{host}"
    return urlunsplit((scheme, host, parts.path or "/", parts.query, ""))


def analyze(path: Path) -> tuple[Metrics, list[Finding], Counter[str]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()

    findings: list[Finding] = []
    exact_counts: Counter[str] = Counter()
    canonical_counts: Counter[str] = Counter()
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
            findings.append(Finding(line_number, "invalid-url", value, str(exc)))
            continue

        if parts.scheme not in {"http", "https"} or not parts.hostname:
            findings.append(
                Finding(
                    line_number,
                    "invalid-url",
                    value,
                    "URL must use http/https and contain a hostname",
                )
            )
            schemes[parts.scheme or "missing"] += 1
            continue

        valid_urls += 1
        schemes[parts.scheme] += 1
        exact_counts[value] += 1
        canonical_counts[canonicalize(parts)] += 1
        host_counts[parts.hostname.lower()] += 1

        if parts.username is not None or parts.password is not None:
            credential_count += 1
            findings.append(
                Finding(
                    line_number,
                    "embedded-credentials",
                    value,
                    "User information is embedded in the URL authority",
                )
            )
        if parts.fragment:
            fragment_count += 1

    for value, count in sorted(exact_counts.items()):
        if count > 1:
            findings.append(
                Finding(0, "exact-duplicate", value, f"appears {count} times")
            )

    for value, count in sorted(canonical_counts.items()):
        if count > 1 and exact_counts.get(value, 0) <= 1:
            findings.append(
                Finding(
                    0,
                    "canonical-duplicate",
                    value,
                    f"has {count} equivalent corpus entries",
                )
            )

    exact_duplicate_count = sum(count - 1 for count in exact_counts.values() if count > 1)
    canonical_duplicate_count = sum(
        count - 1 for count in canonical_counts.values() if count > 1
    )
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
        invalid_url_count=sum(1 for f in findings if f.kind == "invalid-url"),
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


def policy_failures(metrics: Metrics, policy: dict[str, float | int]) -> list[str]:
    checks = {
        "min_valid_urls": (metrics.valid_urls, lambda actual, limit: actual >= limit, ">="),
        "max_invalid_urls": (
            metrics.invalid_url_count,
            lambda actual, limit: actual <= limit,
            "<=",
        ),
        "max_exact_duplicates": (
            metrics.exact_duplicate_count,
            lambda actual, limit: actual <= limit,
            "<=",
        ),
        "max_canonical_duplicates": (
            metrics.canonical_duplicate_count,
            lambda actual, limit: actual <= limit,
            "<=",
        ),
        "max_credential_urls": (
            metrics.credential_url_count,
            lambda actual, limit: actual <= limit,
            "<=",
        ),
        "max_top_10_host_share": (
            metrics.top_10_host_share,
            lambda actual, limit: actual <= limit,
            "<=",
        ),
    }
    failures: list[str] = []
    for name, limit in policy.items():
        if name not in checks:
            failures.append(f"unknown policy key: {name}")
            continue
        actual, predicate, operator = checks[name]
        if not predicate(actual, limit):
            failures.append(f"{name}: {actual} must be {operator} {limit}")
    return failures


def markdown_report(
    metrics: Metrics,
    findings: list[Finding],
    host_counts: Counter[str],
    failures: list[str],
) -> str:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = "\n".join(
        f"| `{host}` | {count} |" for host, count in host_counts.most_common(20)
    ) or "| _none_ | 0 |"
    failure_text = (
        "\n".join(f"- {failure}" for failure in failures)
        if failures
        else "- No configured policy failures."
    )
    finding_counts = Counter(f.kind for f in findings)
    finding_text = (
        "\n".join(f"- **{kind}:** {count}" for kind, count in sorted(finding_counts.items()))
        if finding_counts
        else "- No structural findings."
    )
    return f"""# r4b1t Corpus Health Report

Generated: `{timestamp}`
Source SHA-256: `{metrics.source_sha256}`

## Structural metrics

- Valid URLs: **{metrics.valid_urls}**
- Unique exact URLs: **{metrics.unique_exact_urls}**
- Exact duplicate entries: **{metrics.exact_duplicate_count}**
- Unique canonical URLs: **{metrics.unique_canonical_urls}**
- Canonical duplicate entries: **{metrics.canonical_duplicate_count}**
- Invalid URLs: **{metrics.invalid_url_count}**
- URLs with embedded credentials: **{metrics.credential_url_count}**
- HTTP / HTTPS: **{metrics.http_count} / {metrics.https_count}**
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
    policy: dict[str, float | int] = {}
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
