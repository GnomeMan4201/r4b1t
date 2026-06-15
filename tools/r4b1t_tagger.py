#!/usr/bin/env python3
"""
r4b1t_h0l3 — Phase 1 URL Tagger
Extends the liveness checker with header fingerprinting,
URL tokenization, and meta-tag extraction.

Usage:
    python3 r4b1t_tagger.py --input urls.txt --output tagged.json
    python3 r4b1t_tagger.py --input urls.txt --output tagged.json --workers 20
"""

import asyncio
import aiohttp
import json
import re
import argparse
import sys
from urllib.parse import urlparse
from html.parser import HTMLParser
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# TAG TAXONOMY
# ─────────────────────────────────────────────

CATEGORIES = {
    "SDR_Interface",        # Software Defined Radio web UIs
    "Sovereign_Gateway",    # Alt-DNS, decentralized routing
    "Mesh_Node",            # Meshtastic, LoRa, mesh dashboards
    "Onion_Service",        # .onion, Tor hidden services
    "I2P_Node",             # I2P eepsites
    "Yggdrasil_Node",       # Yggdrasil network nodes
    "ThreatIntel_Feed",     # IOC feeds, threat intel platforms
    "OSINT_Tool",           # OSINT frameworks and tools
    "Darkweb_Forum",        # Dark web forums/markets
    "Security_Blog",        # Research blogs, write-ups
    "CTF_Platform",         # CTF and training environments
    "Gov_Data",             # Government open data portals
    "Radio_Comms",          # Amateur radio, shortwave, SIGINT
    "Privacy_Tool",         # VPN, Tor, privacy-focused tools
    "Crypto_Infra",         # Cryptocurrency nodes, explorers
    "Alt_Media",            # Alternative/independent media
    "Research_Archive",     # Academic papers, archives
    "Decentralized_Net",    # IPFS, ZeroNet, Freenet
    "Unknown",              # Fallback
}

# ─────────────────────────────────────────────
# HEURISTIC DICTIONARIES
# ─────────────────────────────────────────────

# TLD / domain suffix signals
TLD_SIGNALS = {
    ".onion":       ("Onion_Service", 0.99),
    ".i2p":         ("I2P_Node", 0.99),
    ".ygg":         ("Yggdrasil_Node", 0.95),
    ".bit":         ("Sovereign_Gateway", 0.85),
    ".libre":       ("Sovereign_Gateway", 0.80),
    ".coin":        ("Sovereign_Gateway", 0.75),
    ".gnu":         ("Sovereign_Gateway", 0.75),
}

# URL token signals — subdomains, paths, keywords
URL_TOKEN_SIGNALS = {
    # SDR
    "sdr":              ("SDR_Interface", 0.80),
    "gqrx":             ("SDR_Interface", 0.90),
    "rtlsdr":           ("SDR_Interface", 0.90),
    "openwebrx":        ("SDR_Interface", 0.95),
    "websdr":           ("SDR_Interface", 0.95),
    "kiwisdr":          ("SDR_Interface", 0.95),
    "gnuradio":         ("SDR_Interface", 0.90),
    "hackrf":           ("SDR_Interface", 0.85),
    "airspy":           ("SDR_Interface", 0.85),
    "spectrum":         ("SDR_Interface", 0.60),
    "waterfall":        ("SDR_Interface", 0.65),
    "uhd":              ("SDR_Interface", 0.70),
    "usrp":             ("SDR_Interface", 0.80),

    # Radio / comms
    "aprs":             ("Radio_Comms", 0.90),
    "hamradio":         ("Radio_Comms", 0.90),
    "qrz":              ("Radio_Comms", 0.90),
    "eqsl":             ("Radio_Comms", 0.85),
    "dxcluster":        ("Radio_Comms", 0.85),
    "shortwave":        ("Radio_Comms", 0.85),
    "adsb":             ("Radio_Comms", 0.85),
    "meshtastic":       ("Mesh_Node", 0.95),
    "lora":             ("Mesh_Node", 0.75),
    "helium":           ("Mesh_Node", 0.70),

    # Threat intel / OSINT
    "ioc":              ("ThreatIntel_Feed", 0.75),
    "threatintel":      ("ThreatIntel_Feed", 0.90),
    "malware":          ("ThreatIntel_Feed", 0.70),
    "shodan":           ("OSINT_Tool", 0.95),
    "censys":           ("OSINT_Tool", 0.95),
    "osint":            ("OSINT_Tool", 0.80),
    "recon":            ("OSINT_Tool", 0.70),
    "maltego":          ("OSINT_Tool", 0.90),
    "spiderfoot":       ("OSINT_Tool", 0.90),
    "theharvester":     ("OSINT_Tool", 0.90),

    # Decentralized / alt-infra
    "ipfs":             ("Decentralized_Net", 0.85),
    "zeronet":          ("Decentralized_Net", 0.90),
    "freenet":          ("Decentralized_Net", 0.85),
    "yggdrasil":        ("Yggdrasil_Node", 0.90),
    "cjdns":            ("Sovereign_Gateway", 0.85),
    "i2p":              ("I2P_Node", 0.85),
    "torproject":       ("Privacy_Tool", 0.85),
    "torbrowser":       ("Privacy_Tool", 0.85),

    # Privacy tools
    "vpn":              ("Privacy_Tool", 0.65),
    "wireguard":        ("Privacy_Tool", 0.75),
    "openvpn":          ("Privacy_Tool", 0.80),
    "privacyguides":    ("Privacy_Tool", 0.90),

    # CTF
    "ctf":              ("CTF_Platform", 0.85),
    "hackthebox":       ("CTF_Platform", 0.95),
    "tryhackme":        ("CTF_Platform", 0.95),
    "pwnable":          ("CTF_Platform", 0.85),
    "picoctf":          ("CTF_Platform", 0.90),
    "overthewire":      ("CTF_Platform", 0.90),

    # Gov data
    ".gov":             ("Gov_Data", 0.80),
    "data.":            ("Gov_Data", 0.60),
    "open-data":        ("Gov_Data", 0.65),

    # Crypto
    "blockchain":       ("Crypto_Infra", 0.65),
    "explorer":         ("Crypto_Infra", 0.60),
    "mempool":          ("Crypto_Infra", 0.80),
    "etherscan":        ("Crypto_Infra", 0.95),

    # Research
    "arxiv":            ("Research_Archive", 0.95),
    "paper":            ("Research_Archive", 0.55),
    "preprint":         ("Research_Archive", 0.75),
    "archive":          ("Research_Archive", 0.60),
}

# HTTP response header signals
HEADER_SIGNALS = {
    "server": {
        "yggdrasil":        ("Yggdrasil_Node", 0.90),
        "cjdns":            ("Sovereign_Gateway", 0.90),
        "openwebrx":        ("SDR_Interface", 0.95),
        "lighttpd":         ("Alt_Media", 0.40),          # weak signal alone
        "nginx":            None,                          # too generic
        "apache":           None,
        "caddy":            None,
        "gunicorn":         ("OSINT_Tool", 0.35),         # weak
        "werkzeug":         ("OSINT_Tool", 0.40),
        "tornado":          ("OSINT_Tool", 0.35),
    },
    "x-powered-by": {
        "yggdrasil":        ("Yggdrasil_Node", 0.90),
        "i2p":              ("I2P_Node", 0.90),
        "freenet":          ("Decentralized_Net", 0.90),
    },
}

# Meta description / title keyword signals
CONTENT_SIGNALS = [
    (r'\bsdr\b|\bsoftware.defined.radio\b',         ("SDR_Interface", 0.80)),
    (r'\bosint\b|\bopen.source.intel',               ("OSINT_Tool", 0.75)),
    (r'\bthreat.intel|\bioc\b|\bindicator',          ("ThreatIntel_Feed", 0.75)),
    (r'\bctf\b|\bcapture.the.flag',                  ("CTF_Platform", 0.80)),
    (r'\byggdrasil\b',                               ("Yggdrasil_Node", 0.90)),
    (r'\bi2p\b',                                     ("I2P_Node", 0.85)),
    (r'\bmeshtastic\b|\blora\b',                     ("Mesh_Node", 0.85)),
    (r'\bmalware\b|\bransomware\b|\bvirus\b',        ("ThreatIntel_Feed", 0.70)),
    (r'\bprivacy\b|\banonymit',                      ("Privacy_Tool", 0.55)),
    (r'\bdecentrali|\bblockchain\b|\bipfs\b',        ("Decentralized_Net", 0.65)),
    (r'\bshortwave\b|\bham.radio\b|\bamateur.radio', ("Radio_Comms", 0.80)),
    (r'\baprs\b|\badsb\b|\bfreq',                    ("Radio_Comms", 0.75)),
    (r'\bsecurity.research|\bvulnerabilit|\bcve\b',  ("Security_Blog", 0.70)),
    (r'\bpentest|\bpenetration.test',                ("OSINT_Tool", 0.65)),
    (r'\bgovernment|\bfederal|\bmunicip',            ("Gov_Data", 0.60)),
    (r'\barchive|\bpreprint|\bjournal\b',            ("Research_Archive", 0.60)),
]

# ─────────────────────────────────────────────
# HTML META PARSER
# ─────────────────────────────────────────────

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            name = attrs.get("name", "").lower()
            prop = attrs.get("property", "").lower()
            content = attrs.get("content", "")
            if name == "description" or prop == "og:description":
                self.description = content[:500]

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()[:200]

# ─────────────────────────────────────────────
# RESULT DATACLASS
# ─────────────────────────────────────────────

@dataclass
class TagResult:
    url: str
    alive: bool
    status_code: Optional[int] = None
    category: str = "Unknown"
    confidence: float = 0.0
    tag_source: str = "none"       # tld | url_token | header | content | combined
    title: str = ""
    description: str = ""
    server: str = ""
    x_powered_by: str = ""
    error: Optional[str] = None
    tagged_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

# ─────────────────────────────────────────────
# TAGGING LOGIC
# ─────────────────────────────────────────────

def tag_from_url(url: str) -> Optional[tuple[str, float, str]]:
    """Check TLD signals then URL token signals."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    full = url.lower()

    # TLD check first (highest confidence)
    for tld, (cat, conf) in TLD_SIGNALS.items():
        if hostname.endswith(tld):
            return cat, conf, "tld"

    # URL token scan — hostname + path
    tokens_str = (hostname + parsed.path).lower()
    best_cat, best_conf, best_source = None, 0.0, "url_token"
    for token, (cat, conf) in URL_TOKEN_SIGNALS.items():
        if token in tokens_str and conf > best_conf:
            best_cat, best_conf = cat, conf

    if best_cat:
        return best_cat, best_conf, best_source

    return None


def tag_from_headers(headers: dict) -> Optional[tuple[str, float, str]]:
    """Check HTTP response headers for fingerprints."""
    for header_name, signals in HEADER_SIGNALS.items():
        value = headers.get(header_name, "").lower()
        if not value:
            continue
        for keyword, result in signals.items():
            if result and keyword in value:
                return result[0], result[1], "header"
    return None


def tag_from_content(title: str, description: str) -> Optional[tuple[str, float, str]]:
    """Scan title + description with regex content signals."""
    text = (title + " " + description).lower()
    best_cat, best_conf = None, 0.0
    for pattern, (cat, conf) in CONTENT_SIGNALS:
        if re.search(pattern, text) and conf > best_conf:
            best_cat, best_conf = cat, conf
    if best_cat:
        return best_cat, best_conf, "content"
    return None


def resolve_tag(
    url_tag, header_tag, content_tag
) -> tuple[str, float, str]:
    """
    Combine signals with priority: tld > header > url_token > content.
    If multiple signals agree, boost confidence.
    """
    candidates = [t for t in [url_tag, header_tag, content_tag] if t]
    if not candidates:
        return "Unknown", 0.0, "none"

    # If TLD signal present, trust it
    for cat, conf, source in candidates:
        if source == "tld":
            return cat, conf, source

    # Check for agreement between sources
    cats = [c[0] for c in candidates]
    if len(set(cats)) == 1:
        # All agree — boost confidence slightly
        best = max(candidates, key=lambda x: x[1])
        return best[0], min(best[1] + 0.05, 0.99), "combined"

    # Take highest confidence single signal
    best = max(candidates, key=lambda x: x[1])
    return best

# ─────────────────────────────────────────────
# ASYNC FETCHER
# ─────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; r4b1t-tagger/1.0)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = aiohttp.ClientTimeout(total=12, connect=5)


async def fetch_and_tag(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore,
) -> TagResult:
    async with semaphore:
        result = TagResult(url=url, alive=False)

        # Phase 1a: URL token + TLD (no network needed)
        url_tag = tag_from_url(url)

        try:
            async with session.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
                allow_redirects=True,
                ssl=False,
            ) as resp:
                result.alive = True
                result.status_code = resp.status
                result.server = resp.headers.get("Server", "")
                result.x_powered_by = resp.headers.get("X-Powered-By", "")

                # Phase 1b: Header fingerprinting
                header_tag = tag_from_headers(dict(resp.headers))

                content_tag = None
                # Phase 1c: Meta-tag extraction (200 OK only, first 50KB)
                if resp.status == 200:
                    content_type = resp.headers.get("Content-Type", "")
                    if "text/html" in content_type:
                        try:
                            chunk = await resp.content.read(51200)  # 50KB max
                            html = chunk.decode("utf-8", errors="ignore")
                            parser = MetaParser()
                            parser.feed(html)
                            result.title = parser.title
                            result.description = parser.description
                            content_tag = tag_from_content(
                                parser.title, parser.description
                            )
                        except Exception:
                            pass

                # Resolve final tag
                cat, conf, source = resolve_tag(url_tag, header_tag, content_tag)
                result.category = cat
                result.confidence = round(conf, 3)
                result.tag_source = source

        except asyncio.TimeoutError:
            result.error = "timeout"
            # Still apply URL-based tag even if unreachable
            if url_tag:
                result.category, result.confidence, result.tag_source = url_tag

        except aiohttp.ClientConnectorError as e:
            result.error = f"connection_error: {type(e).__name__}"
            if url_tag:
                result.category, result.confidence, result.tag_source = url_tag

        except Exception as e:
            result.error = f"{type(e).__name__}: {str(e)[:100]}"
            if url_tag:
                result.category, result.confidence, result.tag_source = url_tag

        return result

# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────

async def run_pipeline(
    urls: list[str],
    output_path: str,
    workers: int = 15,
    checkpoint_every: int = 500,
):
    semaphore = asyncio.Semaphore(workers)
    results = []
    processed = 0

    connector = aiohttp.TCPConnector(
        limit=workers,
        ttl_dns_cache=300,
        ssl=False,
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_and_tag(session, url.strip(), semaphore)
            for url in urls
            if url.strip()
        ]

        total = len(tasks)
        print(f"[r4b1t-tagger] starting — {total} URLs, {workers} workers")

        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(asdict(result))
            processed += 1

            # Progress
            if processed % 100 == 0:
                alive = sum(1 for r in results if r["alive"])
                tagged = sum(1 for r in results if r["category"] != "Unknown")
                print(
                    f"  [{processed}/{total}] alive={alive} tagged={tagged} "
                    f"({tagged/processed*100:.1f}%)"
                )

            # Checkpoint
            if processed % checkpoint_every == 0:
                checkpoint_path = output_path.replace(".json", f"_checkpoint_{processed}.json")
                with open(checkpoint_path, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"  [checkpoint] saved → {checkpoint_path}")

    # Final write
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    alive = sum(1 for r in results if r["alive"])
    tagged = sum(1 for r in results if r["category"] != "Unknown")
    by_category = {}
    for r in results:
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1

    print(f"\n[r4b1t-tagger] complete")
    print(f"  total:   {total}")
    print(f"  alive:   {alive} ({alive/total*100:.1f}%)")
    print(f"  tagged:  {tagged} ({tagged/total*100:.1f}%)")
    print(f"\n  category breakdown:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"    {cat:<25} {count}")
    print(f"\n  output → {output_path}")

# ─────────────────────────────────────────────
# URL-ONLY MODE (no network, instant)
# ─────────────────────────────────────────────

def tag_url_only(urls: list[str], output_path: str):
    """
    Fast pass — URL tokenization and TLD signals only.
    No network requests. Use this to pre-tag the full pool instantly
    before running the full async pipeline on unknowns.
    """
    results = []
    unknown = 0

    for url in urls:
        url = url.strip()
        if not url:
            continue
        tag = tag_from_url(url)
        if tag:
            cat, conf, source = tag
        else:
            cat, conf, source = "Unknown", 0.0, "none"
            unknown += 1

        results.append({
            "url": url,
            "category": cat,
            "confidence": round(conf, 3),
            "tag_source": source,
        })

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    tagged = len(results) - unknown
    print(f"[url-only] {len(results)} URLs processed")
    print(f"  tagged:  {tagged} ({tagged/len(results)*100:.1f}%)")
    print(f"  unknown: {unknown}")
    print(f"  output → {output_path}")

# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="r4b1t_h0l3 Phase 1 URL Tagger"
    )
    p.add_argument("--input", required=True, help="Input file — one URL per line")
    p.add_argument("--output", required=True, help="Output JSON file")
    p.add_argument(
        "--workers", type=int, default=15,
        help="Concurrent async workers (default: 15)"
    )
    p.add_argument(
        "--url-only", action="store_true",
        help="URL tokenization only — no network requests"
    )
    p.add_argument(
        "--checkpoint", type=int, default=500,
        help="Save checkpoint every N URLs (default: 500)"
    )
    return p.parse_args()


def main():
    args = parse_args()

    with open(args.input) as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print("No URLs found in input file.")
        sys.exit(1)

    print(f"[r4b1t-tagger] loaded {len(urls)} URLs from {args.input}")

    if args.url_only:
        tag_url_only(urls, args.output)
    else:
        asyncio.run(
            run_pipeline(
                urls,
                args.output,
                workers=args.workers,
                checkpoint_every=args.checkpoint,
            )
        )


if __name__ == "__main__":
    main()
