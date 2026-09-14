# ADR 0002: Content-addressed rabbit trails

Status: Accepted

## Decision

A Rabbit Trail is a canonical manifest, not an account-bound server record. Its identifier is the lowercase SHA-256 digest of the manifest's deterministic UTF-8 JSON representation.

```text
trail_id = sha256(canonical_json(manifest))
```

The version 0.1 manifest records:

- the format version;
- creation time;
- exact corpus revision hash;
- sampler, PRNG, and seed;
- selected terrain;
- the ordered route sequence and action that produced each step; and
- an optional parent trail ID and fork position.

Each route ID is independently content-addressed from the exact URL stored in the manifest. Version 0.1 deliberately does not perform lossy URL normalization.

## Trust properties

- A matching trail ID proves manifest integrity.
- A parent reference proves declared lineage only when the referenced parent manifest is also available and verifies.
- Lineage verification requires both artifacts, an exact parent ID match, and byte-equivalent canonical route records through `fork_at`.
- A trail ID does not prove authorship, destination safety, current liveness, or editorial approval.
- Signatures are outside version 0.1. A later format may add optional Ed25519 signatures without requiring accounts.

## Replay rule

The recorded ordered URLs are authoritative for replay. The seed, sampler version, and corpus revision describe how random selections were generated, but a replay never silently substitutes a newer URL when the corpus changes.

Import fails closed on an unknown format, malformed route, invalid URL, mismatched route ID, or mismatched trail ID.

## Fork rule

A fork is self-contained for replay: it copies the parent's ordered route prefix through `fork_at`, records the parent's trail ID, then appends its divergent routes. `verifyLineage(child, parent)` verifies both artifacts and rejects a substituted parent, an out-of-range fork position, or any altered inherited route record.

The browser's **FORK HERE** action forks at the most recently replayed step. Forking at step zero is valid and declares lineage without inheriting a route.
