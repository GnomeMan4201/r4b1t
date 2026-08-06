# r4b1t Closeout Quality Gate

A change is not considered complete until all applicable checks below are evidenced.

- Scope is bounded and the canonical project identity is unchanged or explicitly migrated.
- Static application behavior is covered by a reproducible browser harness.
- Corpus changes include source hashes, before/after metrics, reasons, and a recoverable removal list.
- A transient network failure cannot silently delete a corpus entry.
- CI uses least-privilege permissions and does not push broad unreviewed changes to `main`.
- README counts and claims match a dated release artifact.
- Generated evidence distinguishes structural validity, liveness, relevance, and safety.
- Security-sensitive proxy and metadata behavior is tested against private-address and redirect edge cases.
- No critical or high-severity defect remains open for the supported release surface.
- The release includes a changelog entry, tagged version, and completion report.
