# r4b1t Documentation

- [Corpus governance and removal policy](CORPUS_GOVERNANCE.md)
- [Pool sweep operations](POOL_SWEEP_OPERATIONS.md)
- [Closeout quality gate](QUALITY_GATE.md)
- [Closeout audit — 2026-08-05](CLOSEOUT_AUDIT_2026-08-05.md)

The `Corpus Quality` workflow generates source-hash-bound JSON and Markdown artifacts and enforces `.github/corpus-policy.json` as the reviewed non-regression baseline. `.github/corpus-policy.example.json` is the stricter target state; it is not currently enforced because the measured corpus does not yet satisfy it.

The `Pool Sweep Evidence` workflow is report-only. Its network observations are uploaded for review and cannot directly replace or push the canonical corpus.
