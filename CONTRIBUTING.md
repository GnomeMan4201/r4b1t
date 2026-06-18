# Contributing to r4B1T_h0L3

Low-ceremony. One maintainer. Contributions welcome if they fit the project's philosophy.

---

## Submitting a URL

The most valuable contribution is a URL worth adding to the pool.

**Via the tool:** Click **SUBMIT URL** inside r4B1T_h0L3.  
**Via GitHub:** [Open an issue](https://github.com/GnomeMan4201/r4b1t/issues/new?labels=url-submission) with the label `url-submission`.

### What gets added

- OSINT tools, frameworks, and methodology resources
- Security research blogs and writeups
- Threat intelligence platforms and feeds
- Digital forensics and network analysis tools
- CTF platforms and training resources
- Verified `.onion` addresses (include a brief description of content)
- Weird, niche, or genuinely hard-to-find corners of the internet

All submissions go through `pool_sweep.py` liveness gate before merging. Dead URLs don't make it in.

### What doesn't get added

- Paywalled content or anything requiring login to access
- Link farms, SEO aggregators, AI slop directories
- Mainstream news, social media homepages, or anything already universally known
- Anything illegal to access in most jurisdictions

---

## Reporting a bug

Open an issue. Include:

- What you expected
- What actually happened
- Browser and OS
- Console output if relevant (F12 → Console)

---

## Code contributions

The tool lives in `index.html` — single-file vanilla JS/HTML/CSS, no framework, no build step. Keep it that way.

Supporting tooling lives in `tools/` (Python). Pool management is `pool_sweep.py`. Service worker is `sw.js`.

**Before opening a PR:**

- Test in Chrome and Firefox
- Test mobile layout (DevTools responsive mode minimum)
- Don't introduce external JS dependencies
- Don't add tracking, analytics, or outbound calls beyond the existing Cloudflare Worker endpoints
- Patch protocol: grep first, targeted replace, verify output before committing

Small, focused PRs only. One thing per PR. No framework migrations, no full rewrites.

---

## Pool tooling

The `tools/` directory contains the full pipeline:

| Script | Purpose |
|--------|---------|
| `extract_pool.py` | Extract URLs from index.html |
| `liveness_check.py` | HEAD sweep with timeout |
| `clean_pool.py` | Dedup and normalize |
| `r4b1t_classifier.py` | Assign categories |
| `r4b1t_tagger.py` | Tag metadata |
| `r4b1t_pipeline.sh` | Full pipeline runner |

Pool sweep:
```bash
python pool_sweep.py --workers 30 --timeout 8
sqlite3 pool_sweep.db "SELECT url FROM pool WHERE reachable=1" > urls.txt
```

---

Built by [badBANANA Research Collective](https://github.com/GnomeMan4201) / GnomeMan4201.  
Part of the BANANA_TREE ecosystem of independent security research tooling.
