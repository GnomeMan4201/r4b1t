<div align="center">

# r4b1t_h0l3

**A StumbleUpon-style random discovery engine for OSINT, security tools, and the open web.**

103,394 URLs. No algorithm. No recommendations. No tracking. Pure chaos.

[![Live](https://img.shields.io/badge/live-gnomeman4201.github.io%2Fr4b1t-red?style=flat-square)](https://gnomeman4201.github.io/r4b1t)
[![URLs](https://img.shields.io/badge/pool-103%2C394_URLs-111?style=flat-square&labelColor=222)](https://gnomeman4201.github.io/r4b1t)
[![No backend](https://img.shields.io/badge/backend-none-111?style=flat-square&labelColor=222)](https://gnomeman4201.github.io/r4b1t)
[![No tracking](https://img.shields.io/badge/tracking-none-111?style=flat-square&labelColor=222)](https://gnomeman4201.github.io/r4b1t)
[![badBANANA](https://img.shields.io/badge/badBANANA-Research_Collective-111?style=flat-square&labelColor=222)](https://github.com/GnomeMan4201)

**→ [gnomeman4201.github.io/r4b1t](https://gnomeman4201.github.io/r4b1t)**

</div>

---

## What it is

Remember StumbleUpon? You'd click a button and land somewhere unexpected, a weird personal site, an obscure tool, a community you didn't know existed. The discovery was the point. Then it died, and we got recommendation engines that already know what you think you want.

r4b1t_h0l3 is that, rebuilt, except instead of recipe blogs and motivational quotes, it's 103,394 curated URLs across OSINT tools, threat intelligence platforms, security research blogs, dark web resources, CTF environments, and corners of the open web that don't rank well and don't have anyone promoting them.

Hit **GO**. See what surfaces. Go down the hole.

---

## How it works

![r4b1t_h0l3 fresh load — the interface on startup](Screenshot%20from%202026-06-15%2004-33-42.png)

A URL surfaces at random from the pool. You see the domain and a live preview card before you go anywhere.

![A URL surfaces: Airbus Space & Defence — geospatial products and secure connectivity. Domain and preview visible before visiting.](Screenshot%20from%202026-06-15%2004-35-15.png)

**VISIT ↗** opens the site in a new tab. **SKIP →** rolls another. Your trail of visited domains builds at the bottom of the session. The counter keeps score.

![The Airbus Space & Defence site — opened in a new tab directly from the r4b1t_h0l3 interface](Screenshot%20from%202026-06-15%2004-35-33.png)

---

## BRANCH — go deeper

Random surfacing is one mode. BRANCH is the other.

Hit **BRANCH** on any surfaced URL and r4b1t_h0l3 generates a radial tree of related domains from the pool — then gives you four intent-driven navigation paths:

![BRANCH mode active — radial tree of related domains sprouting from Airbus Space & Defence](Screenshot%20from%202026-06-15%2004-35-43.png)

| Intent | What it does |
|---|---|
| **DEEPER** — drill into this niche | More from the same category |
| **CONNECT** — adjacent territory | Related but different angle |
| **OPPOSITE** — contrasting view | Counterpart or alternative |
| **WILD** — unexpected tangent | Somewhere you didn't expect |

![BRANCH expanded — four intent labels with domain suggestions. Drill into this niche / adjacent territory / contrasting view / unexpected tangent.](Screenshot%20from%202026-06-15%2004-35-51.png)

Each intent rolls a URL that fits. You can follow a thread or break from it entirely. The radial tree stays visible so you can see what's in the vicinity before choosing.

---

## Another roll

Every session is different. Here's Cesium surfacing on a second roll, a 3D geospatial platform most people in the OSINT space haven't encountered directly.

![Cesium.com surfaces — The Platform for 3D Geospatial, with a globe render in the preview card](Screenshot%20from%202026-06-15%2004-36-00.png)

![Cesium.com opened directly — "The Platform for 3D Geospatial", part of Bentley Systems](Screenshot%20from%202026-06-15%2004-36-16.png)

BRANCH on Cesium pulls in a different tree — cesiumjs.org, GitHub repos, video platforms, government data portals.

![BRANCH on Cesium — radial tree includes cesiumjs.org, ehupp/Predict, github.com, targun.video, uber-web/rst, nslog.gov](Screenshot%20from%202026-06-15%2004-36-24.png)

---

## What's in the pool

103,394 URLs assembled from a multi-source pipeline: Start.me public pages, GitHub awesome-lists, and manual curation. The pool covers:

- OSINT tools and frameworks
- Threat intelligence platforms
- Security research blogs and personal sites
- Digital forensics and incident response tools
- Network analysis and traffic inspection tools
- CTF platforms and training environments
- Dark web resources (148 `.onion` addresses)
- Geospatial and imagery intelligence tools
- Development resources, archives, and a lot of things that resist easy categorization

Every URL has an equal probability of surfacing. A tool maintained by one researcher has the same chance as a major commercial platform. That's intentional.

---

## Onion sites

148 `.onion` addresses are in the pool. The first time one surfaces, r4b1t_h0l3 asks if you have Tor Browser installed before opening anything.

- **Yes** → opens in a new tab via Tor
- **No** → skips it or excludes all `.onion` addresses from the session, your call

[Download Tor Browser](https://www.torproject.org/download/)

---

## Keyboard shortcuts

| Key | Action |
|---|---|
| `Space` or `→` | Roll a new random URL |
| `Enter` | Visit current URL |
| `S` | Skip → roll next |
| `P` | Sprout branches from current URL |
| `Esc` | Close iframe / close panel |
| `?` | Toggle help panel |

---

## Bookmark it

After your first roll, a **⬛ r4b1t_h0l3** bookmarklet appears. Drag it to your bookmarks bar — one click from any page brings you back to the hole.

---

## Technical non-architecture

No server. No database. No calls home. Everything runs in your browser.

- The URL pool ships embedded in the HTML
- The Worker that handles randomization is sandboxed
- Your session trail persists in `localStorage`
- Trail sharing works via URL-encoded state
- Hosted as a static file on GitHub Pages

Nothing to hack. No user data to leak. No infrastructure costs.

---

## Part of badBANANA Research Collective

r4b1t_h0l3 is open tooling from the [badBANANA Research Collective](https://github.com/GnomeMan4201) — independent security research, OSINT investigation, and detection engineering. Published findings at [dev.to/gnomeman4201](https://dev.to/gnomeman4201).

If r4b1t_h0l3 is useful, a ⭐ helps other people find it.

---

<div align="center">

*No tracking. No server. No database. Everything runs in your browser.*

**→ [gnomeman4201.github.io/r4b1t](https://gnomeman4201.github.io/r4b1t)**

</div>
