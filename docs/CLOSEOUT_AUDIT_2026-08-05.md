# r4b1t Closeout Audit — 2026-08-05

## Scope

Evidence-backed review of the release, browser-test, dependency, and corpus-maintenance surfaces. This record distinguishes defects observed on the original default branch from controls established by the first closeout change set.

## Verified strengths

- The application is publicly deployed as a static PWA.
- The corpus is maintained in `urls.txt` and a scheduled sweep exists.
- The project has a narrow, immediately usable public purpose.
- The application itself requires no build step.

## Findings requiring follow-up

### 1. Scheduled liveness results are treated as deletion authority

The weekly sweep currently copies `pool_alive.txt` over `urls.txt` and pushes the result directly to the default branch. The checker classifies timeout, connection failure, `HEAD` rejection, authentication, rate limiting, and server errors as unreachable. A transient or method-specific failure can therefore become a permanent corpus deletion after one run.

**Required disposition:** move scheduled operation to report-only behavior until repeated observations, bounded `GET` fallback, removal thresholds, and review artifacts are implemented.

### 2. Domain normalization is incorrect

The sweep uses `netloc.lstrip("www.")`. Python `str.lstrip` removes any leading character contained in the supplied character set rather than the literal prefix. Hosts beginning with `w`, `m`, or `.` can therefore receive an incorrect rate-limit or reporting key.

**Required disposition:** replace it with literal prefix handling and cover the behavior with unit tests.

### 3. Shared HTTP session crosses worker threads

A single `requests.Session` is passed to every worker. The implementation does not establish a safe concurrency contract for session mutation and connection reuse.

**Required disposition:** use thread-local sessions or another explicitly bounded request design.

### 4. Release workflow bypasses review

`.github/workflows/apply-release.yml` reconstructs an archive, stages the entire repository, commits, and pushes from a manually triggered workflow. This high-authority path can replace broad repository state without a reviewable pull request.

**Required disposition:** remove or redesign the workflow after preserving its historical purpose in the changelog or issue record.

### 5. Corpus count claims are not release-bound

The README states 53,869 verified live URLs, while document metadata describes 103k URLs. Neither claim is bound to a dated source hash and verification artifact.

**Required disposition:** update every public count from a reviewed release evidence bundle rather than an informal or stale total.

## Controls established by the first change set

- Deterministic, network-free structural analysis of `urls.txt`.
- Source SHA-256 binding for generated JSON and Markdown evidence.
- Distinct exact-duplicate and canonical-only duplicate semantics.
- Credential-authority detection with evidence redaction.
- Fail-closed validation for malformed policy thresholds.
- Ten unit tests covering parsing, normalization, duplicate semantics, redaction, policy handling, and reproducibility.
- Desktop and mobile Chromium regression coverage through a bounded local static server.
- External network and service-worker blocking during browser tests.
- Exact Playwright dependency locking at 1.62.0.
- CI rejection of high-severity npm dependency findings.
- Read-only workflow permissions, concurrency cancellation, timeouts, and maintained action runtimes.
- Corpus governance, removal policy, and a release-quality gate.

## First measured structural baseline

The first successful corpus-quality run measured the current `urls.txt` as:

- source SHA-256: `5d7339b8cbfe7bd35bb8502ca753e5b4663bc2fc4ba3721b23b791dbace01c41`;
- 50,109 valid URLs;
- 0 invalid URLs;
- 0 exact duplicate entries;
- 1,037 canonical-only duplicate entries;
- 0 credential-bearing URLs;
- 642 fragment-bearing URLs;
- 12,397 unique hosts;
- 9,878 singleton hosts;
- 61.5139% of URLs concentrated in the ten largest hosts;
- host HHI of 0.331178556.

These are structural measurements only. They do not prove current liveness, relevance, safety, or content integrity.

## First change-set boundary

This branch does not mutate `urls.txt`, claim a corrected verified-live count, or repair the scheduled liveness sweep. It establishes the evidence and browser-test baseline required to make those later changes reviewable.

## Merge gate

The first change set is mergeable only when:

1. corpus unit tests pass in CI;
2. desktop and mobile browser tests pass in CI;
3. `npm audit --audit-level=high` passes;
4. the current corpus evidence artifact is generated and reviewed;
5. no application behavior or corpus entries are silently modified;
6. destructive sweep, release-workflow, and count-reconciliation work remains explicitly tracked.
