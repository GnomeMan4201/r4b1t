# r4b1t

Curated random discovery across security, OSINT, research, development, and the weird internet.

<p align="center">
  <a href="https://r4b1t.badbananaresearch.com"><strong>Project site</strong></a>
  ·
  <a href="https://gnomeman4201.github.io/r4b1t/"><strong>Auto launch</strong></a>
</p>

## Quick launch

<table>
<tr>
<td align="center" width="50%">
<strong>DESKTOP / WORKSTATION</strong><br>
<sub>Full exploratory interface · keyboard-first controls · branch tree</sub><br><br>
<a href="https://gnomeman4201.github.io/r4b1t/"><strong>LAUNCH DESKTOP ↗</strong></a>
</td>
<td align="center" width="50%">
<strong>MOBILE / FIELD SHELL</strong><br>
<sub>Thumb-first hole surface · compact route cards · sticky navigation</sub><br><br>
<a href="https://gnomeman4201.github.io/r4b1t/"><strong>LAUNCH MOBILE ↗</strong></a>
</td>
</tr>
</table>

Both launch controls open the same GitHub Pages deployment. r4b1t selects the interface from the viewport: **desktop above 900 px**, **mobile at 900 px and below**. Resizing across the breakpoint switches shells without reloading. Both interfaces use the same corpus, session state, and discovery engine.

r4b1t is a random-discovery instrument. Roll the corpus, inspect what appears, follow it, reject it, or branch away from it. There is no ranking model, recommendation profile, or engagement feed deciding what appears next.

---

## Interface model

```text
same application / same corpus / same session state
                    │
          viewport-based shell
                    │
          ┌─────────┴─────────┐
          │                   │
      > 900 px             ≤ 900 px
      desktop              mobile
      workstation          field shell
          │                   │
          └─────────┬─────────┘
                    │
      roll / visit / sprout / filter
      history / trail / share / inspect
```

The split is presentation-only. Mobile does not run a second discovery engine or maintain a parallel corpus. Both interfaces delegate to the same browser state and core application logic.

### Mobile shell

The mobile interface is recomposed for phone use rather than shrinking the desktop layout. Its top surface is now an operational **hole/readout** instead of a slogan panel. It shows corpus readiness, current mode, scope, and privacy/ranking state around a depth graphic, then hands control directly to ROLL.

The mobile shell provides:

- hole/readout state surface with `CORPUS READY` and route-ready state
- compact ROLL control
- route cards with hostname, metadata, category, and full URL
- one-thumb **FILTER**, **BRANCH**, **HISTORY**, and **INSPECT** navigation
- mobile terrain-filter sheets with active-state mirroring
- branch direction sheets backed by the existing SPROUT engine
- horizontally scrollable trail history
- viewport switching without a page reload
- safe-area-aware sticky navigation and horizontal-overflow protection

Desktop keeps the original r4b1t workstation experience.

---

## Screenshots

<table>
<tr>
<td><img src="docs/demo1.png" alt="First load" width="100%"/></td>
<td><img src="docs/demo2.png" alt="OG card preview with trail" width="100%"/></td>
</tr>
<tr>
<td><img src="docs/demo3.png" alt="Screenshot proxy overlay" width="100%"/></td>
<td><img src="docs/demo4.png" alt="Category filter and SVG tree" width="100%"/></td>
</tr>
</table>

<img src="docs/demo5.png" alt="BRANCH mode with SPROUT directions" width="100%"/>

The retained screenshots document the desktop lineage. The live application automatically exposes the dedicated mobile shell at widths of 900 px and below.

---

## What it does

Roll a URL from the curated pool, visit it, skip it, or **SPROUT** four directional suggestions:

- **deeper** — drill further into the current niche
- **sideways** — move into adjacent territory
- **opposite** — surface a contrasting direction
- **weird** — take an intentionally unexpected tangent

Branch generation uses available page metadata and lightweight semantic signals to find related candidates inside the existing corpus.

## Corpus

The live application currently identifies the working pool as roughly **103k curated URLs**. That number reflects the evolving corpus and should not be confused with the last frozen evidence baseline.

The current evidence-bound baseline remains **50,109 structurally valid URLs across 12,396 unique hosts** with SHA-256:

```text
5d7339b8cbfe7bd35bb8502ca753e5b4663bc2fc4ba3721b23b791dbace01c41
```

That baseline is a reproducible structural count for the audited corpus revision. It is not a claim that every third-party endpoint remains reachable indefinitely. The pool-sweep workflow exists to produce newer time-bounded liveness evidence without rewriting old evidence.

The corpus was assembled from sources including:

- Start.me OSINT and security pages collected via Playwright/CDP
- GitHub awesome-lists across 21 categories
- manual curation passes
- two-stage liveness work combining automated HTTP sweeps with human relevance review

---

## Features

| Surface | Behavior |
|---|---|
| **RANDOM** | Roll a URL from the current eligible corpus |
| **BRANCH / SPROUT** | Generate four directional candidates from the current route |
| **FILTER** | Restrict rolls by category |
| **HISTORY** | Revisit routes seen during the session |
| **TRAIL** | Preserve the visited path through the rabbit hole |
| **INSPECT** | Review current route details on mobile without leaving the shell |
| **SHARE CARD** | Generate a PNG card for the current route |
| **COPY TRAIL** | Export the session as Markdown with links and timestamps |
| **SUBMIT URL** | Open a pre-filled GitHub issue for corpus suggestions |
| **PWA** | Installable shell with cached static assets |
| **Dark / light mode** | Persist the selected display preference |

Current filter categories include CODE, BLOG, NEWS, RESEARCH, PAPER, OSINT, BOUNTY, VIDEO, SOCIAL, REF, ARCHIVE, PKG, COURSE, EVENT, HARDWARE, and TOR.

## Keyboard shortcuts

Desktop retains keyboard-first operation:

| Key | Action |
|---|---|
| `Space` | Roll new URL |
| `Enter` | Visit current URL |
| `S` | Skip |
| `P` | Sprout branches |
| `C` | Download share card |
| `?` or `H` | Toggle help |
| `Esc` | Close overlay |

---

## Quick local preview

The production client is static HTML/CSS/JavaScript and has no application build step.

```bash
git clone https://github.com/GnomeMan4201/r4b1t.git
cd r4b1t
python3 -m http.server 8080
```

Open:

```text
http://127.0.0.1:8080/
```

Some metadata and preview behavior relies on deployed backend services, so a bare local static server is not identical to production. It is still suitable for interface, corpus, PWA-shell, navigation, and client-side regression work.

## Browser tests

Node.js is required for the test harness only.

```bash
npm ci
npx playwright install chromium
npm test
```

Playwright exercises dedicated desktop and mobile Chromium projects. CI stages the site under the same `/r4b1t/` path shape used by GitHub Pages and verifies the interaction paths for both shells.

Current regression coverage includes:

- correct desktop/mobile shell selection
- live viewport switching without reload
- ROLL propagation through the shared engine
- mobile route hostname fidelity
- terrain-filter selection and reset
- mobile branch controls
- hole/readout replacement and absence of the old campaign slogan
- sheet interaction behavior
- horizontal-overflow protection
- desktop shell preservation

The workflow also rejects high-severity npm dependency findings before browser execution.

---

## Architecture

The application is intentionally framework-free. The browser client is vanilla JavaScript, HTML, and CSS. A Cloudflare Worker provides metadata/proxy-related services, while Playwright is development-only infrastructure.

```text
                     r4b1t
                       │
                shared browser engine
                       │
        ┌──────────────┴──────────────┐
        │                             │
 desktop shell                  mobile shell
        │                             │
        └──────────────┬──────────────┘
                       │
              corpus + session state
                       │
        optional Worker-backed services
```

The mobile layer mirrors authoritative state from the existing engine rather than duplicating discovery logic. This keeps route selection, filters, branching, history, and trail behavior consistent across interfaces.

The mobile hole/readout is also presentation-only. It reads existing route, mode, scope, and counter state and does not create a second source of truth.

## PWA and deployment

The service worker precaches the static application shell, including the dual-shell and hole-surface assets. Corpus and Worker-backed requests remain network-oriented rather than being treated as permanently valid cached evidence.

GitHub Pages serves the live application from the repository deployment path. The same deployed code chooses the appropriate interface from viewport width; there is no separate mobile site or user-agent fork.

---

## Pool management

```bash
python pool_sweep.py --workers 30 --timeout 8
sqlite3 pool_sweep.db "SELECT url FROM pool WHERE reachable=1" > pool_alive.txt
```

Treat each sweep as time-bounded evidence. A route reachable during one run may disappear, redirect, or change later. Preserve the corpus revision and sweep output when using the pool in research.

## Verification surfaces

| Surface | Evidence |
|---|---|
| Desktop behavior | Playwright desktop Chromium project |
| Mobile behavior | Playwright mobile Chromium project |
| Responsive shell switch | viewport-switch regression coverage |
| Filter fidelity | mobile select/reset regression coverage |
| Route fidelity | selected URL hostname mirrored into mobile shell |
| Mobile identity | hole/readout surface with old slogan excluded by regression test |
| Dependency gate | `npm audit --audit-level=high` in CI |
| Corpus maintenance | pool-sweep workflow and preserved evidence revisions |
| Deployment | GitHub Pages |
| Visual lineage | retained project screenshots |

A green browser workflow establishes the tested interaction paths for that revision. It does not prove that every third-party URL in the corpus is reachable at viewing time.

## Submit a URL

Found something worth adding? Use **SUBMIT URL** inside r4b1t or open a repository issue with the `url-submission` label.

## Built by

[badBANANA Research Collective](https://github.com/GnomeMan4201) / GnomeMan4201

*badBANANA Research Collective · [dev.to/gnomeman4201](https://dev.to/gnomeman4201)*
