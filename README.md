<p align="center">
  <a href="https://r4b1t.badbananaresearch.com">
    <img src="./docs/readme/r4b1t_h0le-banner.jpg" alt="r4b1t_h0le — not search, not a feed, down the rabbit hole" width="100%">
  </a>
</p>

<p align="center">
  <img src="./docs/readme/field-reel-mobile-shell.svg" alt="r4b1t_h0le field reel — first contact, route and sprout, terrain lock, and local ledger" width="100%">
</p>

<p align="center">
  <img src="./docs/readme/r4b1t_h0le-mechanism.jpg" alt="r4b1t_h0le mechanism — corpus, route, branch, terrain, and device-local trail" width="100%">
</p>

<h1 align="center">r4b1t_h0le</h1>

<p align="center">
  <strong>Chance-driven discovery across security, OSINT, research, development, and the weird web.</strong><br>
  <sub>No recommendation profile. No engagement feed. No ranking model deciding what deserves to be next.</sub>
</p>

<p align="center">
  <a href="https://r4b1t.badbananaresearch.com"><strong>PROJECT SITE</strong></a>
  &nbsp;·&nbsp;
  <a href="https://gnomeman4201.github.io/r4b1t/"><strong>LAUNCH APP</strong></a>
  &nbsp;·&nbsp;
  <a href="https://dev.to/gnomeman4201/r4b1th0l3-5aa3"><strong>DEV WRITE-UP</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/GnomeMan4201/r4b1t/releases"><strong>RELEASES</strong></a>
</p>

<p align="center">
  <a href="https://github.com/GnomeMan4201/r4b1t/actions/workflows/test.yml"><img alt="Playwright E2E" src="https://github.com/GnomeMan4201/r4b1t/actions/workflows/test.yml/badge.svg"></a>
  <a href="https://github.com/GnomeMan4201/r4b1t/actions/workflows/corpus-quality.yml"><img alt="Corpus quality" src="https://github.com/GnomeMan4201/r4b1t/actions/workflows/corpus-quality.yml/badge.svg"></a>
  <a href="https://github.com/GnomeMan4201/r4b1t/actions/workflows/deploy.yml"><img alt="Deploy" src="https://github.com/GnomeMan4201/r4b1t/actions/workflows/deploy.yml/badge.svg"></a>
  <a href="./LICENSE"><img alt="MIT License" src="https://img.shields.io/github/license/GnomeMan4201/r4b1t?style=flat-square"></a>
  <img alt="Local-first" src="https://img.shields.io/badge/state-device--local-111111?style=flat-square">
  <img alt="Vanilla JavaScript" src="https://img.shields.io/badge/client-vanilla%20JS-d71920?style=flat-square">
</p>

<p align="center">
  <a href="#what-r4b1t_h0le-is">WHAT IT IS</a> ·
  <a href="#how-it-works">HOW IT WORKS</a> ·
  <a href="#evidence-boundary">EVIDENCE</a> ·
  <a href="#two-shells-one-engine">ARCHITECTURE</a> ·
  <a href="#verifiable-trails">TRAILS</a> ·
  <a href="#trust-privacy--external-content">TRUST</a>
</p>

---

## What `r4b1t_h0le` is

> [!NOTE]
> **Not search. Not a feed.** `r4b1t_h0le` is a chance-driven discovery instrument built around a curated corpus rather than a ranked result set.

You do not begin with a query. You begin with an aperture.

A route is rolled from the current eligible ground. From there you can follow it, refuse it, inspect it, narrow the terrain, or sprout outward in a new direction. The route you actually make can be preserved locally as a trail.

<p align="center"><code>CORPUS → CHANCE → ROUTE → BRANCH → DEVICE-LOCAL TRAIL</code></p>

<table>
<tr>
<td width="25%" align="center"><strong>50,109</strong><br><sub>structurally valid URLs</sub></td>
<td width="25%" align="center"><strong>12,396</strong><br><sub>unique hosts</sub></td>
<td width="25%" align="center"><strong>0</strong><br><sub>invalid / duplicate / credential-bearing entries admitted</sub></td>
<td width="25%" align="center"><strong>LOCAL</strong><br><sub>trail and session state</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%" valign="top">

### What it does

- surfaces an eligible route by chance
- lets you narrow the eligible terrain without ranking it
- branches in four explicit directions instead of silently profiling you
- preserves the route you made locally
- separates corpus claims from stronger claims the evidence cannot support

</td>
<td width="50%" valign="top">

### What it refuses to become

- a ranked search-results page
- a personalized recommendation profile
- an engagement-maximizing feed
- a cloud account requirement for exploration
- a claim that structural validity proves safety, truth, or current liveness

</td>
</tr>
</table>

---

## Why this exists

Modern discovery systems are extremely good at narrowing.

Search engines optimize for relevance. Feeds optimize for engagement. Recommendation systems learn the neighborhood most likely to keep you clicking. Those systems are useful when you know what you want — but they are poor substitutes for wandering.

`r4b1t_h0le` is built for the opposite condition: **you do not know the useful thing yet.**

> [!TIP]
> The design goal is deliberate serendipity: enough structure to make exploration useful, but not enough invisible scoring to collapse it back into a recommendation engine.

The project grew out of the hole left by StumbleUpon, then became more specific: security research, OSINT, development, technical research, obscure tools, old corners of the web, and the kinds of useful links that rarely win a ranking contest.

The original public build notes are here:

**[r4b1t_h0l3 — 53,000+ curated links for security and OSINT](https://dev.to/gnomeman4201/r4b1th0l3-5aa3)**

<sub>That post documents an earlier corpus revision. The repository and evidence surfaces below are authoritative for the current implementation.</sub>

---

## How it works

<table>
<tr>
<td width="20%" align="center"><kbd>ROLL</kbd><br><sub>chance chooses</sub></td>
<td width="20%" align="center"><kbd>FOLLOW</kbd><br><sub>open the route</sub></td>
<td width="20%" align="center"><kbd>REJECT</kbd><br><sub>refuse it</sub></td>
<td width="20%" align="center"><kbd>SPROUT ×4</kbd><br><sub>branch outward</sub></td>
<td width="20%" align="center"><kbd>TRAIL</kbd><br><sub>keep the path</sub></td>
</tr>
</table>

### `01 / ROLL` — chance chooses

A roll selects one route from the currently eligible terrain. There is no ranked results page and no relevance score exposed as an ordering mechanism. Immediate repetition and excessive domain repetition are constrained so randomness does not collapse into the same host repeatedly.

### `02 / FOLLOW or REJECT` — you choose

A surfaced route is an invitation, not an instruction. Follow it outward, inspect it, share/cut the card, or reject it and roll again. Refusal is part of the route — not a negative engagement signal used to tune a hidden profile.

### `03 / SPROUT` — branch without becoming a feed

| Direction | Intent | Mental model |
| --- | --- | --- |
| **DEEPER** | stay near the current niche | same neighborhood, more depth |
| **SIDEWAYS** | move into adjacent territory | related context, different angle |
| **OPPOSITE** | deliberately contrast the current route | counter-direction / tension |
| **WEIRD** | take the low-signal tangent | distant, unusual, serendipitous |

Branch generation uses available page metadata and lightweight semantic signals against the existing corpus. The branch labels are navigational directions, not a personalized recommendation score.

### `04 / TERRAIN` — narrow the ground, not the ranking

Filtering changes **what is eligible to appear**, not **what the system thinks should appear**.

<p align="center">
  <code>CODE</code> · <code>BLOG</code> · <code>NEWS</code> · <code>RESEARCH</code> · <code>PAPER</code> · <code>OSINT</code> · <code>BOUNTY</code> · <code>VIDEO</code> · <code>SOCIAL</code> · <code>REF</code> · <code>ARCHIVE</code> · <code>PKG</code> · <code>COURSE</code> · <code>EVENT</code> · <code>HARDWARE</code> · <code>TOR</code>
</p>

### `05 / TRAIL` — preserve the route you made

History is useful when it reflects your movement rather than a platform's model of you. Route/session state stays on the device so you can revisit what appeared, where you branched, and where you went next without requiring an account.

---

## Two shells. One engine.

<table>
<tr>
<td width="50%" valign="top">

### DESKTOP / WORKSTATION

**For deliberate exploration.**

Keyboard-first controls, expanded route context, branch topology, history, trail tooling, and the larger investigative surface.

<p align="center"><a href="https://gnomeman4201.github.io/r4b1t/"><strong>LAUNCH WORKSTATION ↗</strong></a></p>

</td>
<td width="50%" valign="top">

### MOBILE / FIELD SHELL

**For the same engine in your hand.**

First-contact clarity, compact route cards, thumb-first controls, terrain sheets, branching, and the device-local ledger.

<p align="center"><a href="https://gnomeman4201.github.io/r4b1t/"><strong>LAUNCH FIELD SHELL ↗</strong></a></p>

</td>
</tr>
</table>

```text
                         same corpus
                             │
                       shared engine
                             │
                   shared session state
                             │
                 ┌───────────┴───────────┐
                 │                       │
             > 900 px                 ≤ 900 px
          workstation               field shell
                 │                       │
                 └───────────┬───────────┘
                             │
           roll / follow / sprout / filter
           history / trail / share / inspect
```

The breakpoint changes presentation, not the discovery engine or corpus.

---

## Evidence boundary

> [!IMPORTANT]
> **The corpus changes over time. Evidence should not.** A frozen baseline is a statement about one audited revision, not a promise about the future state of the open web.

| Measurement | Frozen baseline |
| --- | ---: |
| Structurally valid URLs | **50,109** |
| Unique hosts | **12,396** |
| Invalid entries admitted | **0** |
| Exact duplicates admitted | **0** |
| Credential-bearing entries admitted | **0** |

**Baseline SHA-256**

```text
5d7339b8cbfe7bd35bb8502ca753e5b4663bc2fc4ba3721b23b791dbace01c41
```

### What this establishes

The baseline provides a reproducible structural count for the audited revision and a cryptographic identifier for the source material being described.

### What it deliberately does not establish

Structural validity does **not** prove that a third-party URL is currently reachable, relevant, trustworthy, safe, unchanged, or factually correct. Those are separate measurements. Liveness sweeps are time-bounded evidence and do not rewrite older frozen evidence because the web later changed.

<details>
<summary><strong>Corpus inputs and promotion boundary</strong></summary>

<br>

Corpus work has included Start.me OSINT/security collections gathered through browser automation, GitHub awesome-lists across 21 categories, manual curation, automated liveness sweeps, human relevance review, and duplicate/credential/policy checks before evidence-bound revisions are promoted.

The guiding rule is simple: **do not upgrade a structural observation into a stronger claim without the evidence required for that claim.**

</details>

---

## Verifiable trails

`r4b1t_h0le` can export content-addressed trail material without requiring a server-side identity record.

The trail system separates what can be cryptographically verified from stronger claims an artifact cannot support. A verified reveal can establish that disclosed route material matches its commitment; it does not, by itself, establish authorship or prove real-world wall-clock ordering.

<table>
<tr>
<td width="33%" valign="top"><strong>ADR 0001</strong><br><a href="./docs/adr/0001-anti-ranking-boundary.md">Anti-ranking boundary</a></td>
<td width="33%" valign="top"><strong>ADR 0002</strong><br><a href="./docs/adr/0002-content-addressed-trails.md">Content-addressed trails</a></td>
<td width="33%" valign="top"><strong>ADR 0003</strong><br><a href="./docs/adr/0003-blind-descent-commit-reveal.md">Blind Descent commit/reveal</a></td>
</tr>
</table>

```bash
# Verify one exported trail
npm run trail:verify -- trail.json

# Verify a child and its declared parent together
npm run trail:verify -- child.json parent.json
```

---

## Architecture

```text
                           r4b1t_h0le
                                │
                      vanilla browser client
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
        desktop workstation             mobile field shell
                 │                             │
                 └──────────────┬──────────────┘
                                │
                     corpus + session state
                                │
                  optional metadata services
```

<table>
<tr><th>Surface</th><th>Role</th></tr>
<tr><td><code>index.html</code> / <code>r4b1t.html</code></td><td>application entry surfaces</td></tr>
<tr><td><code>dual-shell.js</code> / <code>dual-shell.css</code></td><td>shared responsive shell behavior</td></tr>
<tr><td><code>trail-runtime.js</code> / <code>trail-manifest.js</code></td><td>trail state, export, and verification support</td></tr>
<tr><td><code>trail-topology.js</code> / <code>topology-runtime.js</code></td><td>trail topology and lineage surfaces</td></tr>
<tr><td><code>blind-runtime.js</code> / <code>blind-manifest.js</code></td><td>Blind Descent commit/reveal behavior</td></tr>
<tr><td><code>trail-wear.js</code> / <code>trail-wear.css</code></td><td>persistent visual trail-wear layer</td></tr>
<tr><td><code>pool_sweep.py</code></td><td>time-bounded liveness and pool maintenance</td></tr>
<tr><td><code>urls.txt</code></td><td>corpus route material</td></tr>
<tr><td><code>tests/</code></td><td>browser and regression coverage</td></tr>
<tr><td><code>docs/adr/</code></td><td>architectural decisions and trust boundaries</td></tr>
</table>

<details>
<summary><strong>Why the client stays framework-free</strong></summary>

<br>

The production surface is static HTML, CSS, and JavaScript. Node.js exists primarily for development, test, and verification tooling rather than as an application build requirement. This keeps the browser runtime small, inspectable, and directly hostable while preserving a separate test harness for regression coverage.

</details>

---

## Run it

<table>
<tr>
<td width="50%" valign="top">

### Production

**Project front door**  
https://r4b1t.badbananaresearch.com

**Direct application**  
https://gnomeman4201.github.io/r4b1t/

</td>
<td width="50%" valign="top">

### Local preview

```bash
git clone https://github.com/GnomeMan4201/r4b1t.git
cd r4b1t
python3 -m http.server 8080
```

Open `http://127.0.0.1:8080/`.

</td>
</tr>
</table>

> [!NOTE]
> Some metadata/preview behavior can depend on deployed services, so a bare static server is not identical to production. It is still suitable for primary client, PWA-shell, navigation, corpus, and interface regression work.

---

## Tests and verification

```bash
npm ci
npx playwright install chromium
npm test

# Python corpus and pool-sweep tests
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-pool-sweep.txt
python -m unittest discover -s tests -p 'test_*.py' -v
```

<table>
<tr>
<td width="33%" align="center"><strong>Browser regression</strong><br><sub>desktop + mobile Chromium</sub></td>
<td width="33%" align="center"><strong>Corpus quality</strong><br><sub>bounded data checks</sub></td>
<td width="33%" align="center"><strong>Dependency gate</strong><br><sub>high-severity npm audit rejection</sub></td>
</tr>
</table>

The browser suite covers shell selection, viewport switching, roll propagation, filtering, branching, route fidelity, overflow containment, trail behavior, Blind Descent leak prevention, topology/tamper cases, and desktop preservation.

> [!WARNING]
> A green workflow verifies the tested behavior for that revision. It does **not** certify the safety or continued availability of every external destination in the corpus.

---

## Trust, privacy & external content

> [!CAUTION]
> **`r4b1t_h0le` curates pointers. It does not control the destinations those pointers lead to.**

The application itself is deliberately local-first: no r4b1t account is required for exploration, route/session state is designed to remain device-local, and the core selection loop does not depend on a personalized server-side feed.

That boundary ends when you leave the application origin.

Third-party destinations may log requests, set cookies, require authentication, run analytics, redirect, disappear, change ownership, or become compromised. Inclusion in the corpus is not an endorsement, certification, guarantee of safety, or statement that a resource remains unchanged after review.

Category and branch labels are navigation aids, not legal, security, or factual classifications. A successful liveness check establishes reachability at a point in time — not trustworthiness or content integrity.

The software is distributed under the MIT License and provided **“AS IS”**, without warranty of any kind. See [`LICENSE`](./LICENSE). Vulnerabilities in `r4b1t_h0le` itself should be reported through [`SECURITY.md`](./SECURITY.md); vulnerabilities in third-party destinations belong with the relevant operator.

---

## Project links

<table>
<tr><td><strong>Project site</strong></td><td><a href="https://r4b1t.badbananaresearch.com">r4b1t.badbananaresearch.com</a></td></tr>
<tr><td><strong>Live application</strong></td><td><a href="https://gnomeman4201.github.io/r4b1t/">gnomeman4201.github.io/r4b1t/</a></td></tr>
<tr><td><strong>Original DEV write-up</strong></td><td><a href="https://dev.to/gnomeman4201/r4b1th0l3-5aa3">r4b1t_h0l3 — 53,000+ curated links for security and OSINT</a></td></tr>
<tr><td><strong>DEV profile</strong></td><td><a href="https://dev.to/gnomeman4201">dev.to/gnomeman4201</a></td></tr>
<tr><td><strong>Releases</strong></td><td><a href="https://github.com/GnomeMan4201/r4b1t/releases">GitHub Releases</a></td></tr>
<tr><td><strong>Changelog</strong></td><td><a href="./CHANGELOG.md">CHANGELOG.md</a></td></tr>
<tr><td><strong>Issues / URL submissions</strong></td><td><a href="https://github.com/GnomeMan4201/r4b1t/issues">GitHub Issues</a></td></tr>
<tr><td><strong>Contributing</strong></td><td><a href="./CONTRIBUTING.md">CONTRIBUTING.md</a></td></tr>
<tr><td><strong>Security</strong></td><td><a href="./SECURITY.md">SECURITY.md</a></td></tr>
</table>

---

## Contributing

Useful contributions are the ones that sharpen the instrument without breaking its trust boundary: corpus-quality fixes, broken-link reports, reproducible UI bugs, accessibility problems, evidence/verification corrections, and well-scoped changes that preserve the anti-ranking model.

Start with [`CONTRIBUTING.md`](./CONTRIBUTING.md). New corpus candidates should go through the issue/submission flow rather than silently mutating evidence-bound material.

---

<p align="center">
  <strong>badBANANA Research Collective</strong><br>
  <sub>open internet exploration · bounded claims · local-first trails</sub>
</p>

<p align="center">
  <a href="https://github.com/GnomeMan4201">GitHub</a> ·
  <a href="https://dev.to/gnomeman4201">DEV</a> ·
  <a href="https://r4b1t.badbananaresearch.com">r4b1t_h0le</a>
</p>

<p align="center"><strong>NOT SEARCH. NOT A FEED. DOWN THE RABBIT HOLE.</strong></p>
