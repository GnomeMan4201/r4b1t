# Contributing to r4b1t

Low-ceremony. One maintainer. Contributions are welcome when they fit the project's philosophy and preserve the evidence/maintenance boundaries documented in the repository.

---

## Submitting a URL

The most valuable contribution is a URL worth adding to the pool.

**Via the tool:** click **SUBMIT URL** inside r4b1t.  
**Via GitHub:** [open an issue](https://github.com/GnomeMan4201/r4b1t/issues/new?labels=url-submission) with the label `url-submission`.

### What gets considered

- OSINT tools, frameworks, and methodology resources
- security research blogs and writeups
- threat-intelligence platforms and feeds
- digital-forensics and network-analysis tools
- CTF platforms and training resources
- verified `.onion` addresses with a useful description
- weird, niche, or genuinely hard-to-find corners of the internet

Candidate additions are expected to pass the pool-maintenance liveness checks at review time and a human relevance pass before being accepted. Reachability is time-bounded evidence: a URL that was live during review can still disappear later.

### What usually does not get added

- content that cannot be meaningfully evaluated without an account or subscription
- link farms, SEO aggregators, or low-value directory spam
- generic homepages that add little discovery value
- material that is unlawful to access in the jurisdictions relevant to the project

---

## Reporting a bug

Open an issue and include:

- what you expected
- what actually happened
- browser and OS
- console output when relevant
- the page/repository revision if the behavior may have changed recently

Do not include credentials, private browsing data, or third-party sensitive information in a public issue.

---

## Code contributions

The application lives primarily in `index.html`: vanilla JavaScript, HTML, and CSS with no production build step. Keep that property unless there is a concrete technical reason to change it.

Supporting tooling lives in `tools/` and `pool_sweep.py`; the service worker is `sw.js`.

**Before opening a PR:**

- run the repository's Playwright browser tests
- test the mobile layout
- preserve the no-tracking/no-account model
- do not introduce new production JavaScript dependencies without a demonstrated need
- preserve the deployed `/r4b1t/` path behavior
- make targeted changes and verify the affected output before committing

Prefer small, reviewable PRs over framework migrations or unrelated rewrites.

---

## Pool tooling

The `tools/` directory contains supporting corpus-maintenance utilities:

| Script | Purpose |
|--------|---------|
| `extract_pool.py` | Extract URLs from `index.html` |
| `liveness_check.py` | Reachability sweep with timeouts |
| `clean_pool.py` | Deduplicate and normalize |
| `r4b1t_classifier.py` | Assign categories |
| `r4b1t_tagger.py` | Tag metadata |
| `r4b1t_pipeline.sh` | Pipeline runner |

Example pool sweep:

```bash
python pool_sweep.py --workers 30 --timeout 8
sqlite3 pool_sweep.db "SELECT url FROM pool WHERE reachable=1" > urls.txt
```

Preserve the corpus revision and sweep output when using reachability results as research evidence.

---

GnomeMan4201 / badBANANA Research
