#!/usr/bin/env python3
"""
r4b1t_h0l3 — URL Pool Cleaner
Runs between extract_pool.py and r4b1t_tagger.py.
Strips noise from the regex extraction pass:
  - CDN / asset URLs (fonts, JS, CSS, images)
  - GitHub internal paths
  - Shields.io badges
  - Partial JS template literals
  - Trailing punctuation artifacts
  - Localhost / private IP ranges
  - Duplicate normalisation (trailing slash, www)

Usage:
    python3 clean_pool.py --input urls.txt --output urls_clean.txt
    python3 clean_pool.py --input urls.txt --output urls_clean.txt --report
"""

import re
import argparse
import ipaddress
from urllib.parse import urlparse, urlunparse
from collections import defaultdict

# ─────────────────────────────────────────────
# BLOCKLIST — domains/patterns to drop entirely
# ─────────────────────────────────────────────

BLOCKED_DOMAINS = {
    # CDN / asset delivery
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "ajax.googleapis.com",
    "code.jquery.com",
    "stackpath.bootstrapcdn.com",
    "maxcdn.bootstrapcdn.com",

    # Badge / shield services
    "shields.io",
    "img.shields.io",
    "badgen.net",
    "badge.fury.io",

    # GitHub infra (not target URLs)
    "github.com/fluidicon.png",
    "avatars.githubusercontent.com",
    "camo.githubusercontent.com",
    "collector.github.com",
    "alive.github.com",
    "api.github.com",

    # Analytics / tracking
    "google-analytics.com",
    "googletagmanager.com",
    "analytics.twitter.com",
    "platform.twitter.com",
    "syndication.twitter.com",

    # Self-referential
    "gnomeman4201.github.io",
}

# ─────────────────────────────────────────────
# PATH EXTENSION BLOCKLIST — asset files
# ─────────────────────────────────────────────

BLOCKED_EXTENSIONS = {
    ".js", ".css", ".map", ".json", ".xml",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf",  # keep if you want PDFs in pool — remove this line if so
}

# ─────────────────────────────────────────────
# TRAILING NOISE PATTERNS
# ─────────────────────────────────────────────

TRAILING_NOISE = re.compile(r'[);\],."\'\\}]+$')

# ─────────────────────────────────────────────
# PRIVATE / LOCALHOST IP RANGES
# ─────────────────────────────────────────────

PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

def is_private_ip(hostname: str) -> bool:
    try:
        addr = ipaddress.ip_address(hostname)
        return any(addr in net for net in PRIVATE_NETWORKS)
    except ValueError:
        return False

# ─────────────────────────────────────────────
# NORMALISATION
# ─────────────────────────────────────────────

def normalise(url: str) -> str:
    """
    Strip trailing slash, lowercase scheme+host, drop default ports.
    Keeps path/query/fragment intact.
    """
    try:
        p = urlparse(url)
        scheme = p.scheme.lower()
        host = p.hostname or ""
        port = p.port

        # Drop default ports
        if (scheme == "http" and port == 80) or \
           (scheme == "https" and port == 443):
            port = None

        netloc = host
        if port:
            netloc = f"{host}:{port}"

        path = p.path.rstrip("/") or ""
        normalised = urlunparse((scheme, netloc, path, p.params, p.query, p.fragment))
        return normalised
    except Exception:
        return url

# ─────────────────────────────────────────────
# FILTER LOGIC
# ─────────────────────────────────────────────

def should_keep(url: str) -> tuple[bool, str]:
    """Returns (keep: bool, reason: str)."""

    # Strip trailing noise characters from regex extraction
    url = TRAILING_NOISE.sub("", url)

    if not url.startswith(("http://", "https://")):
        return False, "not_http"

    try:
        p = urlparse(url)
    except Exception:
        return False, "parse_error"

    hostname = (p.hostname or "").lower().lstrip("www.")
    full_host = (p.hostname or "").lower()
    path = p.path.lower()

    # Blocked domains
    if full_host in BLOCKED_DOMAINS or hostname in BLOCKED_DOMAINS:
        return False, "blocked_domain"

    # Partial domain blocks (endswith check)
    for blocked in BLOCKED_DOMAINS:
        if full_host.endswith("." + blocked):
            return False, "blocked_domain"

    # Private IPs / localhost
    if full_host in ("localhost", "127.0.0.1", "0.0.0.0"):
        return False, "localhost"
    if is_private_ip(full_host):
        return False, "private_ip"

    # Asset file extensions
    path_no_query = path.split("?")[0]
    for ext in BLOCKED_EXTENSIONS:
        if path_no_query.endswith(ext):
            return False, f"asset_file:{ext}"

    # JS template literal artifacts (contain ${ or ` )
    if "${" in url or "`" in url:
        return False, "template_literal"

    # Suspiciously short or malformed
    if len(hostname) < 4:
        return False, "short_hostname"

    return True, "ok"

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def clean_pool(input_path: str, output_path: str, report: bool = False):
    with open(input_path, encoding="utf-8") as f:
        raw = [line.strip() for line in f if line.strip()]

    print(f"[clean_pool] loaded {len(raw)} URLs from {input_path}")

    kept = []
    dropped = defaultdict(list)

    seen_normalised = set()

    for url in raw:
        keep, reason = should_keep(url)
        if not keep:
            dropped[reason].append(url)
            continue

        norm = normalise(url)
        if norm in seen_normalised:
            dropped["duplicate"].append(url)
            continue

        seen_normalised.add(norm)
        kept.append(url)

    with open(output_path, "w", encoding="utf-8") as f:
        for url in sorted(kept):
            f.write(url + "\n")

    total_dropped = len(raw) - len(kept)
    print(f"[clean_pool] kept:    {len(kept)}")
    print(f"[clean_pool] dropped: {total_dropped}")
    print(f"[clean_pool] output → {output_path}")

    if report:
        print(f"\n  drop breakdown:")
        for reason, urls in sorted(dropped.items(), key=lambda x: -len(x[1])):
            print(f"    {reason:<30} {len(urls[1])}")
        report_path = output_path.replace(".txt", "_drop_report.txt")
        with open(report_path, "w") as f:
            for reason, urls in dropped.items():
                for url in urls:
                    f.write(f"{reason}\t{url}\n")
        print(f"\n  full drop report → {report_path}")

def parse_args():
    p = argparse.ArgumentParser(description="r4b1t_h0l3 URL pool cleaner")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report", action="store_true",
                   help="Write a drop report showing why each URL was excluded")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    clean_pool(args.input, args.output, report=args.report)
