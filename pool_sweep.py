#!/usr/bin/env python3
"""
pool_sweep.py — R4B1T URL Pool Health Sweep
Extracts URLs from index.html, sweeps them with HEAD requests,
records results in SQLite, and produces culled output files.
"""

import sys

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

# ── Stdlib imports ─────────────────────────────────────────────────────────────
import argparse
import sqlite3
import time
import threading
import concurrent.futures
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent.resolve()
INDEX_HTML     = BASE_DIR / "urls.txt"
DB_PATH        = BASE_DIR / "pool_sweep.db"
ALIVE_OUT      = BASE_DIR / "pool_alive.txt"
DEAD_OUT       = BASE_DIR / "pool_dead.txt"
REPORT_OUT     = BASE_DIR / "pool_report.md"
CULLED_HTML    = BASE_DIR / "index_culled.html"

URL_START_LINE = 1            # 1-indexed, inclusive
URL_END_LINE   = 999999999    # 1-indexed, inclusive
CLOSING_LINE   = 101323       # the backtick line

DEFAULT_WORKERS = 50
DEFAULT_TIMEOUT = 10
DOMAIN_RATE_S   = 0.5         # min seconds between requests to same domain
UA              = "Mozilla/5.0 (compatible; r4b1t-sweep/1.0)"


# ── Step 1: Extract URLs ───────────────────────────────────────────────────────
def extract_urls(html_path: Path) -> list[str]:
    """Read lines URL_START_LINE–URL_END_LINE from index.html, return URL list."""
    urls: list[str] = []
    with html_path.open("r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, start=1):
            if lineno < URL_START_LINE:
                continue
            if lineno > URL_END_LINE:
                break
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.startswith("http"):
                continue
            urls.append(stripped)
    return urls


# ── Step 2: SQLite helpers ─────────────────────────────────────────────────────
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
    """INSERT OR IGNORE all URLs with NULL status fields."""
    conn.executemany(
        "INSERT OR IGNORE INTO pool (url) VALUES (?)",
        [(u,) for u in urls],
    )
    conn.commit()


def db_reset_statuses(conn: sqlite3.Connection) -> None:
    conn.execute("""
        UPDATE pool SET
            last_checked = NULL,
            status_code  = NULL,
            reachable    = NULL,
            redirect_url = NULL,
            check_count  = 0
    """)
    conn.commit()


def db_get_pending(conn: sqlite3.Connection, urls_ordered: list[str]) -> list[str]:
    """Return URLs not yet checked, preserving original order."""
    cur = conn.execute(
        "SELECT url FROM pool WHERE status_code IS NULL AND reachable IS NULL"
    )
    pending_set = {row[0] for row in cur.fetchall()}
    return [u for u in urls_ordered if u in pending_set]


def db_update(
    conn: sqlite3.Connection,
    url: str,
    status_code: int | None,
    reachable: int,
    redirect_url: str | None,
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


# ── Step 3: HEAD sweep ─────────────────────────────────────────────────────────
def registered_domain(url: str) -> str:
    """Return netloc stripped of leading www. as a rough registered-domain key."""
    try:
        netloc = urllib.parse.urlparse(url).netloc
        return netloc.lstrip("www.").lower()
    except Exception:
        return url


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


def check_url(
    url: str,
    session: requests.Session,
    rate_limiter: RateLimiter,
    timeout: int,
) -> tuple[int | None, int, str | None]:
    """
    Returns (status_code, reachable, redirect_url).
    reachable: 1 if status < 400, else 0
    redirect_url: final URL if different from original, else None
    """
    domain = registered_domain(url)
    rate_limiter.wait(domain)
    try:
        resp = session.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": UA},
        )
        code = resp.status_code
        reachable = 1 if code < 400 else 0
        final = resp.url
        redirect_url = final if final and final.rstrip("/") != url.rstrip("/") else None
        return code, reachable, redirect_url
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.TooManyRedirects,
    ):
        return None, 0, None
    except Exception as exc:
        print(f"\n[ERR] {url}: {exc}", file=sys.stderr)
        return None, 0, None


def sweep(
    urls: list[str],
    conn: sqlite3.Connection,
    workers: int,
    timeout: int,
) -> None:
    rate_limiter = RateLimiter()
    session = requests.Session()
    session.max_redirects = 10

    db_lock = threading.Lock()
    counts = {"reachable": 0, "dead": 0, "error": 0}

    def worker(url: str) -> None:
        ts = int(time.time())
        code, reachable, redirect_url = check_url(url, session, rate_limiter, timeout)

        with db_lock:
            db_update(conn, url, code, reachable, redirect_url, ts)
            conn.commit()
            if code is None:
                counts["error"] += 1
            elif reachable:
                counts["reachable"] += 1
            else:
                counts["dead"] += 1

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
                dead=counts["dead"],
                error=counts["error"],
                url=short,
            )
            bar.update(1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(wrapped_worker, u): u for u in urls}
            for f in concurrent.futures.as_completed(futures):
                try:
                    f.result()
                except Exception as exc:
                    print(f"\n[WORKER ERR] {futures[f]}: {exc}", file=sys.stderr)

    session.close()


# ── Step 5: Output ─────────────────────────────────────────────────────────────
def write_outputs(conn: sqlite3.Connection, urls_ordered: list[str], duration: float) -> None:
    cur = conn.execute("SELECT url, status_code, reachable, redirect_url FROM pool")
    rows = {row[0]: row for row in cur.fetchall()}

    # Alive — preserve original order
    alive = [u for u in urls_ordered if rows.get(u, (None, None, 0))[2] == 1]
    ALIVE_OUT.write_text("\n".join(alive) + "\n", encoding="utf-8")

    # Dead
    dead_lines: list[str] = []
    for u in urls_ordered:
        row = rows.get(u)
        if row and row[2] == 0:
            code = row[1]
            prefix = str(code) if code is not None else "ERR"
            dead_lines.append(f"{prefix} {u}")
    DEAD_OUT.write_text("\n".join(dead_lines) + "\n", encoding="utf-8")

    # Summary counts
    total      = len(urls_ordered)
    reachable  = sum(1 for u in urls_ordered if rows.get(u, (None, None, 0))[2] == 1)
    dead_cnt   = sum(1 for row in rows.values() if row[2] == 0 and row[1] in (404, 410))
    error_cnt  = sum(1 for row in rows.values() if row[2] == 0 and row[1] is None)
    redirect_cnt = sum(1 for row in rows.values() if row[3] is not None)
    unchecked  = sum(1 for row in rows.values() if row[2] is None)

    summary = (
        f"\nSWEEP COMPLETE\n"
        f"total:     {total}\n"
        f"reachable: {reachable}  (status < 400)\n"
        f"dead:      {dead_cnt}  (404 / 410)\n"
        f"error:     {error_cnt}  (timeout / connection failure)\n"
        f"redirect:  {redirect_cnt}  (redirect_url IS NOT NULL)\n"
        f"unchecked: {unchecked}  (should be 0 on full run)\n"
    )
    print(summary)

    # Markdown report
    sweep_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    dur_str = f"{int(duration // 60)}m {int(duration % 60)}s"

    # Status code distribution
    from collections import Counter, defaultdict
    code_counter: Counter = Counter()
    domain_dead: defaultdict[str, int] = defaultdict(int)
    domain_alive: defaultdict[str, int] = defaultdict(int)
    redirects: list[tuple[str, str]] = []

    for u, row in rows.items():
        _, code, reach, redir = row
        code_key = str(code) if code is not None else "ERR"
        code_counter[code_key] += 1
        dom = registered_domain(u)
        if reach == 0:
            domain_dead[dom] += 1
        elif reach == 1:
            domain_alive[dom] += 1
        if redir:
            redirects.append((u, redir))

    checked = total - unchecked
    code_table_rows = sorted(code_counter.items(), key=lambda x: -x[1])
    code_table = "| Status | Count | % of Total |\n|--------|-------|------------|\n"
    for code_key, cnt in code_table_rows:
        pct = 100 * cnt / checked if checked else 0
        code_table += f"| {code_key} | {cnt} | {pct:.1f}% |\n"

    top_dead = sorted(domain_dead.items(), key=lambda x: -x[1])[:20]
    top_dead_md = "| Domain | Dead Count |\n|--------|------------|\n"
    for dom, cnt in top_dead:
        top_dead_md += f"| {dom} | {cnt} |\n"

    top_alive = sorted(domain_alive.items(), key=lambda x: -x[1])[:20]
    top_alive_md = "| Domain | Reachable Count |\n|--------|------------------|\n"
    for dom, cnt in top_alive:
        top_alive_md += f"| {dom} | {cnt} |\n"

    redirect_sample = redirects[:50]
    redirect_md = ""
    for orig, final in redirect_sample:
        redirect_md += f"- `{orig}` → `{final}`\n"
    if not redirect_md:
        redirect_md = "_No redirects recorded._\n"

    report = f"""# R4B1T Pool Sweep Report

**Sweep date:** {sweep_date}
**Duration:** {dur_str}
**Total checked:** {checked} / {total}

---

## Status Code Distribution

{code_table}

---

## Top 20 Domains by Dead URL Count

{top_dead_md}

---

## Top 20 Domains by Reachable URL Count

{top_alive_md}

---

## Redirect Chains (up to 50)

{redirect_md}
"""
    REPORT_OUT.write_text(report, encoding="utf-8")
    print(f"Output written:\n  {ALIVE_OUT}\n  {DEAD_OUT}\n  {REPORT_OUT}")


# ── Step 6: Inject ─────────────────────────────────────────────────────────────
def inject_pool(alive_file: Path, html_file: Path) -> None:
    """Replace URL block in index.html with pool_alive.txt, write index_culled.html."""
    alive_urls = [
        line.strip()
        for line in alive_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    lines = html_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    original_url_count = URL_END_LINE - URL_START_LINE + 1

    # Lines before URL block (0-indexed: 0 … URL_START_LINE-2)
    before = lines[: URL_START_LINE - 1]
    # The closing backtick line (0-indexed: CLOSING_LINE - 1)
    closing = lines[CLOSING_LINE - 1] if CLOSING_LINE - 1 < len(lines) else "`\n"
    # Lines after closing backtick
    after = lines[CLOSING_LINE:] if CLOSING_LINE < len(lines) else []

    new_url_block = [u + "\n" for u in alive_urls]
    out_lines = before + new_url_block + [closing] + after

    CULLED_HTML.write_text("".join(out_lines), encoding="utf-8")

    # Verify count
    import subprocess
    result = subprocess.run(
        ["grep", "-c", "^https://", str(CULLED_HTML)],
        capture_output=True, text=True,
    )
    verified = result.stdout.strip()
    print(
        f"Wrote {CULLED_HTML} — {len(alive_urls)} URLs "
        f"(was ~{original_url_count})\n"
        f"grep -c verified: {verified}"
    )


# ── CLI ────────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pool_sweep.py",
        description="R4B1T URL Pool Health Sweep — HEAD-check ~101k URLs from index.html",
    )
    p.add_argument(
        "--recheck",
        action="store_true",
        help="Reset all statuses and re-sweep everything from scratch",
    )
    p.add_argument(
        "--inject",
        action="store_true",
        help="Inject pool_alive.txt back into index.html as index_culled.html, then exit",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        metavar="N",
        help=f"Thread pool size (default: {DEFAULT_WORKERS})",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        metavar="N",
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # ── Inject mode ──
    if args.inject:
        if not ALIVE_OUT.exists():
            print(f"Error: {ALIVE_OUT} not found. Run sweep first.", file=sys.stderr)
            sys.exit(1)
        if not INDEX_HTML.exists():
            print(f"Error: {INDEX_HTML} not found.", file=sys.stderr)
            sys.exit(1)
        inject_pool(ALIVE_OUT, INDEX_HTML)
        return

    # ── Sweep mode ──
    if not INDEX_HTML.exists():
        print(f"Error: {INDEX_HTML} not found.", file=sys.stderr)
        sys.exit(1)

    print("Extracting URLs from index.html …")
    urls = extract_urls(INDEX_HTML)
    print(f"  Extracted {len(urls):,} URLs")

    conn = db_connect()
    db_init_urls(conn, urls)

    if args.recheck:
        print("--recheck: resetting all statuses …")
        db_reset_statuses(conn)

    # Resumability
    cur = conn.execute("SELECT COUNT(*) FROM pool WHERE status_code IS NOT NULL")
    already_checked = cur.fetchone()[0]
    pending = db_get_pending(conn, urls)

    if already_checked and not args.recheck:
        print(f"Resuming: {already_checked:,} already checked, {len(pending):,} remaining")
    else:
        print(f"Starting sweep: {len(pending):,} URLs to check")

    if not pending:
        print("Nothing to sweep. Use --recheck to re-run.")
        conn.close()
        return

    start = time.monotonic()
    sweep(pending, conn, workers=args.workers, timeout=args.timeout)
    duration = time.monotonic() - start

    write_outputs(conn, urls, duration)
    conn.close()


if __name__ == "__main__":
    main()
