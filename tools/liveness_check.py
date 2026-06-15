#!/usr/bin/env python3
"""
r4b1t_h0l3 — Liveness Checker & Pool Rebuilder
Checks which URLs in the pool are still alive and rebuilds index.html
with only live URLs.

Two modes:
  check   — check liveness, output live/dead URL lists
  rebuild — rebuild index.html with live URLs only

Usage:
    # Check liveness (fast HEAD requests)
    python3 liveness_check.py check \
        --input urls.txt \
        --live urls_live.txt \
        --dead urls_dead.txt \
        --workers 100

    # Rebuild index.html with live URLs
    python3 liveness_check.py rebuild \
        --live urls_live.txt \
        --html ~/r4b1t/index.html \
        --output ~/r4b1t/index.html

    # Full pipeline: check then rebuild
    python3 liveness_check.py check \
        --input urls.txt --live urls_live.txt --dead urls_dead.txt --workers 100
    python3 liveness_check.py rebuild \
        --live urls_live.txt --html ~/r4b1t/index.html
"""

import asyncio
import aiohttp
import argparse
import sys
import json
from datetime import datetime, timezone
from collections import defaultdict

# ─────────────────────────────────────────────
# LIVENESS CHECK
# ─────────────────────────────────────────────

# Status codes we consider "alive"
ALIVE_CODES = {
    200, 201, 202, 203, 204,
    301, 302, 303, 307, 308,  # redirects — URL exists, just moved
    401, 403,                  # auth required — site exists
    405,                       # method not allowed — HEAD rejected, site exists
    429,                       # rate limited — site exists
}

# Status codes that mean dead
DEAD_CODES = {
    404, 410, 451,             # not found, gone, legal block
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; r4b1t-liveness/1.0)",
}

TIMEOUT = aiohttp.ClientTimeout(total=10, connect=4)


async def check_url(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
) -> tuple[str, bool, int, str]:
    """
    Returns (url, is_alive, status_code, error).
    Uses HEAD first, falls back to GET if HEAD returns 405.
    """
    async with semaphore:
        # Skip onion sites — can't check without Tor
        if ".onion" in url:
            return url, True, 0, "onion_skip"

        try:
            async with session.head(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
                allow_redirects=True,
                ssl=False,
            ) as resp:
                code = resp.status
                if code == 405:
                    # HEAD not allowed, try GET with early close
                    async with session.get(
                        url,
                        headers=HEADERS,
                        timeout=TIMEOUT,
                        allow_redirects=True,
                        ssl=False,
                    ) as get_resp:
                        code = get_resp.status
                        return url, code in ALIVE_CODES, code, ""
                return url, code in ALIVE_CODES, code, ""

        except asyncio.TimeoutError:
            return url, False, 0, "timeout"
        except aiohttp.ClientConnectorError:
            return url, False, 0, "connection_error"
        except aiohttp.TooManyRedirects:
            return url, False, 0, "too_many_redirects"
        except Exception as e:
            return url, False, 0, f"{type(e).__name__}"


async def run_liveness_check(
    urls: list[str],
    live_path: str,
    dead_path: str,
    workers: int = 100,
    checkpoint_every: int = 5000,
):
    semaphore = asyncio.Semaphore(workers)
    live = []
    dead = []
    errors = defaultdict(int)
    processed = 0

    connector = aiohttp.TCPConnector(
        limit=workers,
        ttl_dns_cache=300,
        ssl=False,
    )

    total = len(urls)
    print(f"[liveness] checking {total} URLs with {workers} workers")
    print(f"[liveness] onion sites skipped (kept as live)")

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            check_url(session, url.strip(), semaphore)
            for url in urls if url.strip()
        ]

        for coro in asyncio.as_completed(tasks):
            url, is_alive, code, error = await coro
            processed += 1

            if is_alive:
                live.append(url)
            else:
                dead.append((url, code, error))
                if error:
                    errors[error] += 1

            if processed % 1000 == 0:
                pct = processed / total * 100
                live_pct = len(live) / processed * 100
                print(
                    f"  [{processed}/{total}] {pct:.1f}% done | "
                    f"live={len(live)} ({live_pct:.1f}%) | "
                    f"dead={len(dead)}"
                )

            if processed % checkpoint_every == 0:
                with open(live_path + f".checkpoint_{processed}", "w") as f:
                    f.write("\n".join(live))
                print(f"  [checkpoint] {len(live)} live URLs saved")

    # Write final outputs
    with open(live_path, "w") as f:
        f.write("\n".join(live))

    with open(dead_path, "w") as f:
        for url, code, error in dead:
            f.write(f"{url}\t{code}\t{error}\n")

    # Summary
    print(f"\n[liveness] complete")
    print(f"  total:    {total}")
    print(f"  live:     {len(live)} ({len(live)/total*100:.1f}%)")
    print(f"  dead:     {len(dead)} ({len(dead)/total*100:.1f}%)")
    print(f"  live  → {live_path}")
    print(f"  dead  → {dead_path}")

    if errors:
        print(f"\n  error breakdown:")
        for err, count in sorted(errors.items(), key=lambda x: -x[1]):
            print(f"    {err:<30} {count}")

    return live, dead


# ─────────────────────────────────────────────
# DOMAIN DEDUPLICATION
# ─────────────────────────────────────────────

def deduplicate_by_domain(urls: list[str], tagged_map: dict = None) -> list[str]:
    """
    Keep at most MAX_PER_DOMAIN URLs per domain.
    Prefer URLs that are tagged (in tagged_map) over untagged.
    """
    from urllib.parse import urlparse
    from collections import defaultdict

    MAX_PER_DOMAIN = 3  # max URLs per domain in final pool

    by_domain = defaultdict(list)
    for url in urls:
        try:
            host = urlparse(url).hostname or ""
            host = host.lstrip("www.")
            by_domain[host].append(url)
        except Exception:
            by_domain["__invalid__"].append(url)

    result = []
    dominated = 0

    for domain, domain_urls in by_domain.items():
        if len(domain_urls) <= MAX_PER_DOMAIN:
            result.extend(domain_urls)
            continue

        dominated += len(domain_urls) - MAX_PER_DOMAIN

        # Sort: tagged URLs first, then by URL length (shorter = more canonical)
        if tagged_map:
            domain_urls.sort(
                key=lambda u: (
                    tagged_map.get(u, "Unknown") == "Unknown",  # tagged first
                    len(u)
                )
            )
        else:
            domain_urls.sort(key=len)

        result.extend(domain_urls[:MAX_PER_DOMAIN])

    print(f"[dedup] {len(urls)} → {len(result)} URLs")
    print(f"[dedup] removed {dominated} over-represented domain URLs")
    print(f"[dedup] unique domains: {len(by_domain)}")

    return result


# ─────────────────────────────────────────────
# POOL REBUILDER
# ─────────────────────────────────────────────

def rebuild_index(
    live_urls: list[str],
    html_path: str,
    output_path: str,
    tagged_path: str = None,
):
    """
    Replace the URL pool in index.html with live_urls.
    Finds the template literal between line 893 and the .split() call.
    """
    print(f"[rebuild] loading {html_path}...")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Find pool boundaries
    pool_start = "const URLS = `"
    pool_end = "`.split('\\n').map(u => u.trim()).filter(Boolean);"

    start_idx = html.find(pool_start)
    end_idx = html.find(pool_end)

    if start_idx == -1 or end_idx == -1:
        print("[rebuild] ERROR: could not find URL pool boundaries")
        print(f"  pool_start found: {start_idx != -1}")
        print(f"  pool_end found: {end_idx != -1}")
        sys.exit(1)

    # Optional: load tagged map for dedup prioritization
    tagged_map = {}
    if tagged_path:
        try:
            data = json.load(open(tagged_path))
            tagged_map = {r["url"]: r["category"] for r in data}
            print(f"[rebuild] loaded {len(tagged_map)} tagged URLs for dedup priority")
        except Exception as e:
            print(f"[rebuild] warning: could not load tagged data: {e}")

    # Deduplicate
    deduped = deduplicate_by_domain(live_urls, tagged_map)

    # Build new pool string
    new_pool = pool_start + "\n".join(deduped) + "\n" + pool_end

    # Replace in HTML
    old_pool = html[start_idx:end_idx + len(pool_end)]
    html = html[:start_idx] + new_pool + html[end_idx + len(pool_end):]

    old_count = old_pool.count("\n") - 1  # rough URL count
    new_count = len(deduped)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[rebuild] pool rebuilt")
    print(f"  before: ~{old_count} URLs")
    print(f"  after:  {new_count} URLs")
    print(f"  output: {output_path}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="r4b1t_h0l3 liveness checker and pool rebuilder"
    )
    sub = p.add_subparsers(dest="command", required=True)

    # check subcommand
    check = sub.add_parser("check", help="Check URL liveness")
    check.add_argument("--input", required=True, help="Input URL file")
    check.add_argument("--live", required=True, help="Output live URLs file")
    check.add_argument("--dead", required=True, help="Output dead URLs file")
    check.add_argument("--workers", type=int, default=100,
                       help="Concurrent workers (default: 100)")
    check.add_argument("--checkpoint", type=int, default=5000,
                       help="Checkpoint every N URLs")

    # rebuild subcommand
    rebuild = sub.add_parser("rebuild", help="Rebuild index.html with live URLs")
    rebuild.add_argument("--live", required=True, help="Live URLs file")
    rebuild.add_argument("--html", required=True, help="Path to index.html")
    rebuild.add_argument("--output", help="Output path (default: same as --html)")
    rebuild.add_argument("--tagged", help="tagged_final.json for dedup priority")

    return p.parse_args()


def main():
    args = parse_args()

    if args.command == "check":
        with open(args.input) as f:
            urls = [line.strip() for line in f if line.strip()]

        print(f"[liveness] loaded {len(urls)} URLs from {args.input}")
        asyncio.run(run_liveness_check(
            urls,
            args.live,
            args.dead,
            workers=args.workers,
            checkpoint_every=args.checkpoint,
        ))

    elif args.command == "rebuild":
        with open(args.live) as f:
            live_urls = [line.strip() for line in f if line.strip()]

        print(f"[rebuild] loaded {len(live_urls)} live URLs")
        output = args.output or args.html
        rebuild_index(
            live_urls,
            args.html,
            output,
            tagged_path=args.tagged,
        )
        print(f"\nNext steps:")
        print(f"  cd ~/r4b1t")
        print(f"  git add index.html")
        print(f"  git commit -m 'chore: purge dead URLs, deduplicate pool'")
        print(f"  git push origin main")


if __name__ == "__main__":
    main()
