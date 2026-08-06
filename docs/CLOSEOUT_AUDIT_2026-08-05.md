# r4b1t Closeout Audit — 2026-08-05

## Scope

Initial evidence-backed review of the release, browser-test, and corpus-maintenance surfaces. This document records observed repository state and bounds the first closeout change set.

## Verified strengths

- The application is publicly deployed as a static PWA.
- The corpus is maintained in `urls.txt` and a scheduled sweep exists.
- A Playwright workflow and Node package manifest are present.
- The project has a narrow, immediately usable public purpose.

## Findings requiring correction

### 1. Scheduled liveness results are treated as deletion authority

The weekly sweep currently copies `pool_alive.txt` over `urls.txt` and pushes the result directly to the default branch. The current checker classifies every timeout, connection failure, `HEAD` rejection, `401`, `403`, `429`, and server error as unreachable. That makes transient or method-specific failure capable of permanently removing a valid resource after one run.

**Required disposition:** move scheduled operation to report-only behavior until repeated observations, bounded GET fallback, removal thresholds, and review artifacts are implemented.

### 2. Domain normalization is incorrect

The sweep uses `netloc.lstrip("www.")`. Python `str.lstrip` removes any leading characters in the supplied character set rather than the literal prefix. Hosts beginning with `w`, `m`, or `.` can therefore be grouped under an incorrect rate-limit/reporting key.

**Required disposition:** replace with literal prefix handling and cover it with unit tests.

### 3. Shared HTTP session crosses worker threads

A single `requests.Session` is passed to every thread. The implementation does not establish that concurrent mutation and connection reuse are safe for this workload.

**Required disposition:** use one session per worker/thread or plain bounded requests with explicit adapters and retry policy.

### 4. Release workflow bypasses review

`.github/workflows/apply-release.yml` reconstructs an archive, stages the entire repository, commits, and pushes from a manually triggered workflow. This is an obsolete high-authority path that can replace broad repository state without a reviewable pull request.

**Required disposition:** remove the workflow after preserving its historical purpose in the changelog or issue record.

### 5. Advertised browser-test surface is internally inconsistent

The package manifest and CI workflow invoke Playwright, while the referenced `tests/test-server.js`, `tests/e2e.spec.js`, and `playwright.config.js` are not present at the current default-branch paths checked during this audit.

**Required disposition:** restore a minimal deterministic browser harness before claiming active end-to-end regression coverage.

### 6. Corpus count claims are not release-bound

The README states 53,869 verified live URLs, while the current document metadata describes 103k URLs. Neither claim is bound in the repository documentation to a source hash and dated verification report.

**Required disposition:** generate structural and liveness evidence from an exact corpus hash, then update every public count from that release evidence.

## First change-set boundary

This branch adds:

- deterministic, network-free corpus structural analysis;
- unit tests for structural invariants;
- CI-generated JSON and Markdown evidence;
- declared pool-sweep dependencies;
- corpus governance and removal policy;
- a policy template that is not enforced until the first baseline is reviewed.

It intentionally does not mutate `urls.txt`, claim a new verified count, or mark liveness remediation complete.

## Merge gate

The first change set is mergeable only when:

1. unit tests pass in CI;
2. corpus evidence is generated successfully against the current `urls.txt`;
3. the artifact is reviewed for duplicates, invalid entries, credentials, and host concentration;
4. no existing application behavior is modified;
5. follow-up issues are opened for the destructive sweep, browser harness, release workflow, and count reconciliation.
