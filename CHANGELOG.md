# Changelog

All notable changes to r4B1T_h0L3 are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-06-17

### Added

**Core discovery engine**
- RANDOM mode — roll a verified live URL from a pool of 53,869 URLs across 14,488 unique domains
- SKIP — roll again without visiting
- VISIT — open current URL in new tab
- Domain preview shown before any navigation

**BRANCH mode**
- SPROUT generates four directional suggestions: deeper, sideways, opposite, weird
- Powered by OG metadata + Wikipedia API keyword extraction — zero API cost
- Pure JS category adjacency graph, no LLM dependency

**FILTER**
- Lock rolls to a category: CODE, OSINT, BLOG, NEWS, RESEARCH, BOUNTY, VIDEO, SOCIAL, REF, ARCHIVE, PKG, COURSE, EVENT, HARDWARE, TOR

**Session tools**
- HISTORY — full scrollable session history, clickable to revisit
- SHARE CARD — download PNG card of current rabbit hole
- COPY TRAIL — export session as markdown with clickable links and timestamps
- SUBMIT URL — suggest additions via pre-filled GitHub issue

**Onion support**
- 148 verified `.onion` addresses in the pool
- Tor Browser detection gate on first onion surface — skip or exclude for session

**UX / shell**
- Keyboard shortcuts: Space (roll), Enter (visit), S (skip), P (sprout), C (share card), ? / H (help), ESC (close overlay)
- Dark/light mode with warm light palette, persisted across sessions
- PWA — installable as home screen app, offline shell cache via service worker (`sw.js`, cache key `r4b1t-v1`)
- SVG branch history visualization
- Microlink screenshot proxy replacing iframe previews
- Bookmarklet — drag **⬛ r4B1T_h0L3** to bookmarks bar after first roll

**Infrastructure**
- Cloudflare Worker backend (`r4b1t-proxy`) — OG metadata fetch (/api), site proxy with RFC1918 blocking (/proxy), OG image route (/og)
- Edge cache: 1hr TTL
- Rate limited: 60 req/min per IP, origin-locked
- `urls.txt` — flat pool file served via GitHub Pages, network-first in service worker
- `pool_sweep.py` — multithreaded HEAD sweep with SQLite result store, `--workers` and `--timeout` flags
- `tools/` — classifier, tagger, pipeline, category filter patcher, branch injection, liveness check, pool extractor/cleaner
- 173 commits from first upload (2026-06-07) through public release

---

## [0.1.0] — 2026-06-07

- Initial upload: single-file `index.html`, `demo.svg`, base README
