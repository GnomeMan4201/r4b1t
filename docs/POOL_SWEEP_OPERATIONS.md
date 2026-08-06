# Pool Sweep Operations

## Safety posture

The scheduled pool sweep is an observation job. It does not have authority to replace `urls.txt`, commit corpus changes, or push to the default branch.

A network observation is not a removal decision. Timeout, DNS failure, TLS failure, connection failure, `HEAD` incompatibility, authentication, bot protection, rate limiting, and server error are all capable of making a usable resource appear non-reachable during one run.

## Workflow behavior

The `Pool Sweep Evidence` workflow:

1. checks out the reviewed repository state with read-only contents permission;
2. installs the exact declared direct dependency versions;
3. copies the sweep program and corpus into an isolated workspace;
4. runs the existing classifier without modifying the canonical corpus;
5. verifies the database and report outputs;
6. records the event, commit, input count, input hash, output counts, and artifact hashes;
7. uploads the complete evidence bundle for review.

Pull requests run a 200-URL smoke sample. Scheduled and manually dispatched runs use the complete corpus.

## Evidence products

Each run produces:

- `input.sha256` — hash of the exact observed input corpus;
- `sweep-manifest.txt` — run identity, counts, and artifact hashes;
- `pool_sweep.db` — row-level observations;
- `pool_alive.txt` — URLs classified reachable by the current implementation;
- `pool_dead.txt` — all observations classified non-reachable by the current implementation;
- `pool_report.md` — human-readable distribution and domain summary.

The words `alive` and `dead` are legacy filenames, not adjudicated corpus states. Until the classifier is replaced, reviewers must treat both files as provisional observations.

## Removal requirements

No URL may be removed solely because it appears in one `pool_dead.txt` artifact. Removal requires the criteria in [Corpus Governance and Removal Policy](CORPUS_GOVERNANCE.md), including repeated independent observations or separately verified content, ownership, security, privacy, legal, or duplicate evidence.

A future mutation workflow must use a pull request, preserve the removed-entry list and source hash, enforce bounded change thresholds, and pass the corpus non-regression policy.

## Known classifier limitations

The current sweep engine remains intentionally unchanged in this safety PR. Known limitations include:

- `HEAD`-only checks;
- broad status-to-reachability reduction;
- incorrect `www.` prefix handling;
- a shared `requests.Session` across workers;
- automatic redirect following;
- no explicit private-address or redirect-target guard;
- no persistent repeated-observation decision model.

These limitations are the scope of the next tested sweep-engine change set. Report-only operation prevents them from silently deleting corpus entries in the meantime.
