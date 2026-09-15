# Motion sync

The production Site and static GitHub runtime now share the same motion constants through
`motion-tokens.js`. It exposes `window.R4b1tMotion.tokens` and applies CSS custom
properties at startup, so the static shell can consume the same timings as the Site.

The existing static runtime remains authoritative for its DOM and trail state. The already
merged wear layer remains unchanged: persistent crease rendering, concealed redaction,
fork inheritance, radial ink reveal (680ms), descend (360ms), and return (340ms).

This sync deliberately does not replace `index.html` with the Site's React/Vinext build.
The Site deployment is a separate production target; the GitHub repo remains a no-build
static application with its existing trail, blind-manifest, topology, and Playwright
coverage.

Token highlights: reveal 680ms, descend 360ms, return 340ms, roll 440ms, reject 260ms,
forward 380ms, press 80ms, release 180ms, ledger row 260ms, sprout root 420/460ms,
burn hold 2200ms and burn fade 900ms. Easing curves match the production reference.
