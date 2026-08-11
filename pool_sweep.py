#!/usr/bin/env python3
"""r4b1t URL corpus health sweep.

This tool is evidence/report oriented. It reads ``urls.txt``, performs bounded
HTTP observations, records the results in SQLite, and writes review artifacts.
It does not mutate the production corpus.

Classification is deliberately conservative:
- confirmed reachable: final observed HTTP status < 400;
- confirmed missing: final observed HTTP status is 404 or 410;
- indeterminate: timeouts, connection failures, authentication/rate-limit
  responses, server errors, and other non-success statuses.

A common HEAD-rejection response receives one bounded streaming GET fallback.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import sqlite3
import sys
import threading
import time
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Dependency check ──────────────────────────────────────────────────────────
_missing = []
try:
    import requests
except ImportError:
    _missing.append("requests")
try:
    from tqdm import tqdm
except ImportError:
    _missing.append("tqdm")

if _missing:
    print(f"Missing dependencies: {', '.join(_missing)}")
    print(f"Install with: pip install {' '.join(_missing)}")
    sys.exit(1)

# ── Paths / constants ─────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
URLS_FILE = BASE_DIR / "urls.txt"
DB_PATH = BASE_DIR / "pool_sweep.db"
ALIVE_OUT = BASE_DIR / "pool_alive.txt"
DEAD_OUT = BASE_DIR / "pool_dead.txt"
INDETERMINATE_OUT = BASE_DIR / "pool_indeterminate.txt"
REPORT_OUT = BASE_DIR / "pool_report.md"

DEFAULT_WORKERS = 50
DEFAULT_TIMEOUT = 10
DOMAIN_RATE_S = 0.5
UA = "Mozilla/5.0 (compatible; r4b1t-sweep/2.0)"

CONFIRMED_MISSING = {404, 410}
HEAD_GET_FALLBACK = {400, 403, 405, 406, 501}


# ── Input ─────────────────────────────────────────────────────────────────────
def extract_urls(path: Path) -> list[str]:
    """Return non-empty HTTP(S) URLs from the corpus file in source order."""
    urls: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith(("http://", "https://")):
                urls.append(stripped)
    return urls


# ── SQLite helpers ─────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS pool (
    url          TEXT PRIMARY KEY,
    last_checked INTEGER,
    status_code  INTEGER,
    reachable    INTEGER,
    redirect_url TEXT,
    check_count  INTEGER DEFAULT 0
);
"""


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def db_init_urls(conn: sqlite3.Connection, urls: list[str]) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO pool (url) VALUES (?)",
        [(u,) for u in urls],
    )
    conn.commit()


def db_reset_statuses(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE pool SET
            last_checked = NULL,
            status_code  = NULL,
            reachable    = NULL,
            redirect_url = NULL,
            check_count  = 0
        """
    )
    conn.commit()


def db_get_pending(conn: sqlite3.Connection, urls_ordered: list[str]) -> list[str]:
    """Return corpus URLs with no observation in this database revision."""
    cur = conn.execute("SELECT url FROM pool WHERE last_checked IS NULL")
    pending_set = {row[0] for row in cur.fetchall()}
    return [u for u in urls_ordered if u in pending_set]


def db_update(
    conn: sqlite3.Connection,
    url: str,
    status_code: Optional[int],
    reachable: Optional[int],
    redirect_url: Optional[str],
    ts: int,
) -> None:
    conn.execute(
        """UPDATE pool SET
               last_checked = ?,
               status_code  = ?,
               reachable    = ?,
               redirect_url = ?,
               check_count  = check_count + 1
           WHERE url = ?""",
        (ts, status_code, reachable, redirect_url, url),
    )


# ── HTTP observation ───────────────────────────────────────────────────────────
def registered_domain(url: str) -> str:
    """Return a stable host key with only a literal leading ``www.`` removed."""
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower().rstrip(".")
        if host.startswith("www."):
            host = host[4:]
        return host or url
    except Exception:
        return url


def classify_status(status_code: Optional[int]) -> Optional[int]:
    """Map a final HTTP observation to confirmed reachable/missing/unknown."""
    if status_code is None:
        return None
    if status_code < 400:
        return 1
    if status_code in CONFIRMED_MISSING:
        return 0
    return None


class RateLimiter:
    def __init__(self, min_gap: float = DOMAIN_RATE_S):
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()
        self._min_gap = min_gap

    def wait(self, domain: str) -> None:
        with self._lock:
            now = time.monotonic()
            last = self._last.get(domain, 0.0)
            gap = now - last
            if gap < self._min_gap:
                sleep_for = self._min_gap - gap
                self._last[domain] = now + sleep_for
            else:
                sleep_for = 0.0
                self._last[domain] = now
        if sleep_for > 0:
            time.sleep(sleep_for)


_thread_state = threading.local()


def get_worker_session() -> requests.Session:
    """Return one requests.Session per worker thread, never shared across threads."""
    session = getattr(_thread_state, "session", None)
    if session is None:
        session = requests.Session()
        session.max_redirects = 10
        _thread_state.session = session
    return session


def _final_redirect(original: str, final: Optional[str]) -> Optional[str]:
    if final and final.rstrip("/") != original.rstrip("/"):
        return final
    return None


def check_url(
    url: str,
    session: requests.Session,
    rate_limiter: RateLimiter,
    timeout: int,
) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Observe one URL without turning ambiguous failures into deletion evidence."""
    domain = registered_domain(url)
    rate_limiter.wait(domain)
    headers = {"User-Agent": UA}

    try:
        head = session.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers=headers,
        )
        status = head.status_code
        final_url = head.url
        head.close()

        # Some otherwise usable endpoints reject HEAD. One streaming GET is a
        # bounded fallback; the response body is never consumed.
        if status in HEAD_GET_FALLBACK:
            rate_limiter.wait(domain)
            get_headers = {"User-Agent": UA, "Range": "bytes=0-0"}
            response = session.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers=get_headers,
                stream=True,
            )
            status = response.status_code
            final_url = response.url
            response.close()

        return status, classify_status(status), _final_redirect(url, final_url)

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.TooManyRedirects,
        requests.exceptions.RequestException,
    ):
        return None, None, None


def sweep(
    urls: list[str],
    conn: sqlite3.Connection,
    workers: int,
    timeout: int,
) -> None:
    rate_limiter = RateLimiter()
    db_lock = threading.Lock()
    counts = {"reachable": 0, "missing": 0, "indeterminate": 0}

    def worker(url: str) -> None:
        ts = int(time.time())
        session = get_worker_session()
        status, reachable, redirect_url = check_url(url, session, rate_limiter, timeout)

        with db_lock:
            db_update(conn, url, status, reachable, redirect_url, ts)
            conn.commit()
            if reachable == 1:
                counts["reachable"] += 1
            elif reachable == 0:
                counts["missing"] += 1
            else:
                counts["indeterminate"] += 1

    with tqdm(
        total=len(urls),
        unit="url",
        dynamic_ncols=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}",
    ) as bar:

        def wrapped_worker(url: str) -> None:
            worker(url)
            short = url[:60] + "…" if len(url) > 60 else url
            bar.set_postfix(
                reachable=counts["reachable"],
                missing=counts["missing"],
                indeterminate=counts["indeterminate"],
                url=short,
            )
            bar.update(1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(wrapped_worker, u): u for u in urls}
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    print(f"\n[WORKER ERR] {futures[future]}: {exc}", file=sys.stderr)


# ── Output ─────────────────────────────────────────────────────────────────────
def write_outputs(conn: sqlite3.Connection, urls_ordered: list[str], duration: float) -> None:
    cur = conn.execute(
        "SELECT url, status_code, reachable, redirect_url, last_checked FROM pool"
    )
    rows = {row[0]: row for row in cur.fetchall()}

    alive = [u for u in urls_ordered if rows.get(u, (None, None, None))[2] == 1]
    ALIVE_OUT.write_text("\n".join(alive) + ("\n" if alive else ""), encoding="utf-8")

    dead_lines: list[str] = []
    indeterminate_lines: list[str] = []
    for url in urls_ordered:
        row = rows.get(url)
        if not row:
            continue
        _, code, reachable, _, last_checked = row
        prefix = str(code) if code is not None else "ERR"
        if reachable == 0:
            dead_lines.append(f"{prefix} {url}")
        elif last_checked is not None and reachable is None:
            indeterminate_lines.append(f"{prefix} {url}")

    DEAD_OUT.write_text(
        "\n".join(dead_lines) + ("\n" if dead_lines else ""), encoding="utf-8"
    )
    INDETERMINATE_OUT.write_text(
        "\n".join(indeterminate_lines) + ("\n" if indeterminate_lines else ""),
        encoding="utf-8",
    )

    total = len(urls_ordered)
    reachable_count = sum(
        1 for u in urls_ordered if rows.get(u, (None, None, None))[2] == 1
    )
    missing_count = sum(
        1 for u in urls_ordered if rows.get(u, (None, None, None))[2] == 0
    )
    indeterminate_count = sum(
        1
        for u in urls_ordered
        if rows.get(u) and rows[u][4] is not None and rows[u][2] is None
    )
    redirect_count = sum(
        1 for u in urls_ordered if rows.get(u) and rows[u][3] is not None
    )
    unchecked_count = sum(
        1 for u in urls_ordered if not rows.get(u) or rows[u][4] is None
    )

    summary = (
        "\nSWEEP COMPLETE\n"
        f"total:         {total}\n"
        f"reachable:     {reachable_count}  (final status < 400)\n"
        f"missing:       {missing_count}  (404 / 410 only)\n"
        f"indeterminate: {indeterminate_count}  (auth/rate/server/error/other)\n"
        f"redirect:      {redirect_count}\n"
        f"unchecked:     {unchecked_count}\n"
    )
    print(summary)

    sweep_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    duration_text = f"{int(duration // 60)}m {int(duration % 60)}s"

    code_counter: Counter = Counter()
    domain_missing: defaultdict[str, int] = defaultdict(int)
    domain_alive: defaultdict[str, int] = defaultdict(int)
    domain_indeterminate: defaultdict[str, int] = defaultdict(int)
    redirects: list[tuple[str, str]] = []

    for url in urls_ordered:
        row = rows.get(url)
        if not row or row[4] is None:
            continue
        _, code, reachable, redirect, _ = row
        code_counter[str(code) if code is not None else "ERR"] += 1
        domain = registered_domain(url)
        if reachable == 1:
            domain_alive[domain] += 1
        elif reachable == 0:
            domain_missing[domain] += 1
        else:
            domain_indeterminate[domain] += 1
        if redirect:
            redirects.append((url, redirect))

    checked = total - unchecked_count
    code_table = "| Status | Count | % of Checked |\n|--------|-------|--------------|\n"
    for code_key, count in sorted(code_counter.items(), key=lambda item: -item[1]):
        percentage = 100 * count / checked if checked else 0
        code_table += f"| {code_key} | {count} | {percentage:.1f}% |\n"

    def domain_table(values: dict[str, int], heading: str) -> str:
        table = f"| Domain | {heading} |\n|--------|{'-' * (len(heading) + 2)}|\n"
        for domain, count in sorted(values.items(), key=lambda item: -item[1])[:20]:
            table += f"| {domain} | {count} |\n"
        return table

    redirect_md = "".join(
        f"- `{original}` → `{final}`\n" for original, final in redirects[:50]
    ) or "_No redirects recorded._\n"

    report = f"""# r4b1t Pool Sweep Report

**Sweep date:** {sweep_date}
**Duration:** {duration_text}
**Total checked:** {checked} / {total}

## Interpretation boundary

This is a time-bounded observation report, not deletion authority.

- **reachable** means the final observed response status was below 400;
- **missing** is limited to 404/410 after the bounded request strategy;
- **indeterminate** includes authentication/rate-limit responses, server errors,
  request failures, and other outcomes that are not safe evidence for removal.

A single sweep must not directly replace the production corpus.

---

## Outcome Summary

| Outcome | Count |
|---------|------:|
| Reachable | {reachable_count} |
| Confirmed missing | {missing_count} |
| Indeterminate | {indeterminate_count} |
| Unchecked | {unchecked_count} |
| Redirected | {redirect_count} |

---

## Status Code Distribution

{code_table}

---

## Top 20 Domains by Confirmed-Missing Count

{domain_table(domain_missing, 'Missing Count')}

---

## Top 20 Domains by Reachable Count

{domain_table(domain_alive, 'Reachable Count')}

---

## Top 20 Domains by Indeterminate Count

{domain_table(domain_indeterminate, 'Indeterminate Count')}

---

## Redirect Chains (up to 50)

{redirect_md}
"""
    REPORT_OUT.write_text(report, encoding="utf-8")
    print(
        "Output written:\n"
        f"  {ALIVE_OUT}\n"
        f"  {DEAD_OUT}\n"
        f"  {INDETERMINATE_OUT}\n"
        f"  {REPORT_OUT}"
    )


# ── CLI ────────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pool_sweep.py",
        description=(
            "r4b1t URL corpus health sweep — report-only HTTP observations from urls.txt"
        ),
    )
    parser.add_argument(
        "--recheck",
        action="store_true",
        help="Reset stored observations and re-sweep the full corpus",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        metavar="N",
        help=f"Thread pool size (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        metavar="N",
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")
    if args.timeout < 1:
        raise SystemExit("--timeout must be at least 1 second")
    if not URLS_FILE.exists():
        raise SystemExit(f"Error: {URLS_FILE} not found.")

    print(f"Reading corpus from {URLS_FILE.name} …")
    urls = extract_urls(URLS_FILE)
    if not urls:
        raise SystemExit("No HTTP(S) URLs found in corpus file.")
    print(f"  Loaded {len(urls):,} URLs")

    conn = db_connect()
    db_init_urls(conn, urls)

    if args.recheck:
        print("--recheck: resetting stored observations …")
        db_reset_statuses(conn)

    already_checked = conn.execute(
        "SELECT COUNT(*) FROM pool WHERE last_checked IS NOT NULL"
    ).fetchone()[0]
    pending = db_get_pending(conn, urls)

    if already_checked and not args.recheck:
        print(
            f"Resuming: {already_checked:,} already observed, "
            f"{len(pending):,} remaining"
        )
    else:
        print(f"Starting sweep: {len(pending):,} URLs to observe")

    if not pending:
        print("Nothing to sweep. Use --recheck to re-run.")
        conn.close()
        return

    started = time.monotonic()
    sweep(pending, conn, workers=args.workers, timeout=args.timeout)
    duration = time.monotonic() - started

    write_outputs(conn, urls, duration)
    conn.close()


if __name__ == "__main__":
    main()
