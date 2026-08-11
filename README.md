# R4B1T_H0L3

[![r4b1t — Not search. Not a feed. A door.](docs/banner.png)](https://r4b1t-repo.abroooosh.chatgpt.site)

<p align="center">
  <a href="https://r4b1t-repo.abroooosh.chatgpt.site"><strong>Explore the flagship project site</strong></a>
  ·
  <a href="https://gnomeman4201.github.io/r4b1t/"><strong>Launch the original application</strong></a>
</p>

> Curated web discovery instrument — 50,109 structurally valid URLs across 12,396 unique hosts spanning security, OSINT, research, development, and the weird internet.

**Not search. Not a feed. A door.**

---

## Screenshots

<table>
<tr>
<td><img src="docs/demo1.png" alt="First load" width="100%"/></td>
<td><img src="docs/demo2.png" alt="OG card preview with trail" width="100%"/></td>
</tr>
<tr>
<td><img src="docs/demo3.png" alt="Screenshot proxy overlay" width="100%"/></td>
<td><img src="docs/demo4.png" alt="Category filter + SVG tree" width="100%"/></td>
</tr>
</table>

<img src="docs/demo5.png" alt="BRANCH mode with SPROUT directions" width="100%"/>

---

## What it is

A deliberate random-discovery instrument for the security and OSINT community. Roll a URL from a hand-curated pool, visit it, skip it, or SPROUT — generate four directional suggestions (deeper, sideways, opposite, weird) based on the page's semantic content.

No accounts. No tracking. No recommendation profile. Just the pool and the roll.

## Quick local preview

The application itself is static HTML/CSS/JavaScript and has no build step.

```bash
git clone https://github.com/GnomeMan4201/r4b1t.git
cd r4b1t
python3 -m http.server 8080
```

Open:

```text
http://127.0.0.1:8080/
```

Some features rely on the deployed backend/proxy and therefore will not behave identically under a bare local static server. The local preview is still useful for UI, navigation, corpus, PWA-shell, and client-side regression work.

## Run the browser tests

The test harness uses pinned Playwright dependencies. Node.js is needed for testing only; it is not required to build the application.

```bash
npm ci
npx playwright install chromium
npm test
```

CI stages the site under the same `/r4b1t/` path shape used by GitHub Pages and exercises both desktop and mobile browser projects. The workflow also rejects high-severity npm audit findings before E2E execution.

---

## How the pool was built

The URL corpus was assembled from:

- Start.me OSINT and security pages collected via Playwright/CDP
- GitHub awesome-lists across 21 categories
- manual curation passes with a two-stage liveness gate (automated HTTP sweep + human relevance sign-off)

The current evidence-bound corpus baseline contains **50,109 structurally valid URLs across 12,396 unique hosts** (SHA-256: `5d7339b8cbfe7bd35bb8502ca753e5b4663bc2fc4ba3721b23b791dbace01c41`). This is a reproducible structural count for the audited corpus revision, not proof that every third-party endpoint is live at viewing time. The pool-sweep workflow performs continuing liveness maintenance.

## Features

- **RANDOM** — roll a verified live URL from the pool
- **BRANCH** — SPROUT generates four directional suggestions using OG metadata + Wikipedia API keyword extraction
- **FILTER** — lock rolls to a category (CODE, OSINT, BLOG, NEWS, RESEARCH, BOUNTY, VIDEO, SOCIAL, REF, ARCHIVE, PKG, COURSE, EVENT, HARDWARE, TOR)
- **HISTORY** — scrollable session history with revisit links
- **SHARE CARD** — download a PNG card of the current rabbit hole
- **COPY TRAIL** — export the session as Markdown with links and timestamps
- **SUBMIT URL** — suggest additions through a pre-filled GitHub issue
- **PWA** — installable home-screen app with an offline shell cache
- **Dark/light mode** — persisted display preference

## Keyboard shortcuts

| Key | Action |
|---|---|
| Space | Roll new URL |
| Enter | Visit current URL |
| S | Skip |
| P | Sprout branches |
| C | Download share card |
| ? or H | Toggle help |
| ESC | Close overlay |

## Architecture

The browser application is intentionally framework-free: vanilla JavaScript, HTML, and CSS with no production build pipeline. A Cloudflare Worker backend handles metadata fetching and proxy-related functionality, including cache/rate/origin controls. Playwright exists as a development-only browser test harness.

```text
browser / GitHub Pages
        ↓
static r4b1t client
        ↓
curated URL corpus + session state
        ↓
optional Worker-backed metadata/proxy services
```

## Pool management

```bash
python pool_sweep.py --workers 30 --timeout 8
sqlite3 pool_sweep.db "SELECT url FROM pool WHERE reachable=1" > pool_alive.txt
```

Treat a sweep as time-bounded evidence: an endpoint reachable during one run can disappear or change later. Preserve the corpus revision and sweep output when using the pool in research.

## Verification surfaces

| Surface | Evidence |
|---|---|
| Browser behavior | Playwright E2E workflow across desktop/mobile projects |
| Dependency gate | `npm audit --audit-level=high` in CI |
| Corpus maintenance | scheduled/operational pool-sweep workflow |
| Deployment | GitHub Pages deployment workflow |
| Visual proof | five retained project screenshots above |

A green browser workflow establishes the tested interaction paths for that revision. It does not prove that every third-party URL in the corpus is still reachable at viewing time.

## Submit a URL

Found something worth adding? Click **SUBMIT URL** in the tool or [open an issue](https://github.com/GnomeMan4201/r4b1t/issues/new?labels=url-submission).

## Built by

[badBANANA Research Collective](https://github.com/GnomeMan4201) / GnomeMan4201

Part of the BANANA_TREE ecosystem of independent security research tooling.

---

## Part of the BANANA_TREE Research Ecosystem

| | |
|---|---|
| **Research Hub** | [GnomeMan4201](https://github.com/GnomeMan4201/GnomeMan4201) |
| **Corpus & Discovery** | [r4b1t](https://gnomeman4201.github.io/r4b1t) — curated OSINT/security discovery |
| **Detection Engineering** | [SHENRON](https://github.com/GnomeMan4201/shenron) |
| **AI Safety Research** | [drift_orchestrator](https://github.com/GnomeMan4201/drift_orchestrator) |
| **Analytical Method** | [reasoning-diff-lab](https://github.com/GnomeMan4201/reasoning-diff-lab) |

*badBANANA Research Collective · [dev.to/gnomeman4201](https://dev.to/gnomeman4201)*
