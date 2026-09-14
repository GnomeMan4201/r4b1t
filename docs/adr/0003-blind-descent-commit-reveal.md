# ADR 0003: Blind Descent commit-reveal trails

Status: Accepted for implementation

## Decision

Blind Descent uses `r4b1t-trail/v0.2`. A route is selected locally with an unbiased CSPRNG sampler and committed before any route identity is rendered. Reveal discloses the route and nonce and must reproduce the existing commitment; it cannot reroll, replace, filter, or reject the committed route.

Version 0.2 uses the same deterministic UTF-8 canonical JSON implementation as v0.1. The accepted value profile is plain JSON containing strings, booleans, null, arrays, objects with lexicographically sorted keys, and safe integers. Floats are forbidden in v0.2 identity inputs. SHA-256 identifiers are lowercase hex with a `sha256:` prefix. Nonces and salts are exactly 32 bytes in canonical unpadded base64url form.

## Identities

- `genesis_id` is the stable logical identity derived from founding parameters. It excludes steps and avoids a hash cycle.
- `trail_id` identifies the complete exported manifest snapshot and changes as the trail changes.
- `commitment` binds one route to its genesis, prior commitment, and monotonically increasing step index.
- a fork is included in genesis and binds every descendant commitment to the exact parent snapshot, genesis, fork position, and parent commitment.

```text
genesis_id = SHA256(canonical_json(genesis))

commitment = SHA256(canonical_json({
  domain: "r4b1t-blind-step/v0.2",
  genesis_id,
  previous_commitment,
  step_index,
  route_id,
  nonce
}))
```

For step zero, `previous_commitment` is `genesis_id`.

## Concealment boundary

A public concealed step contains only `index`, `state`, and `commitment`. It contains no URL, route ID, nonce, sampler seed, or partial route hash. Private reveal material remains in device-local storage and is never included in a public snapshot.

This protects recipients of an exported artifact from offline corpus lookup. It does not conceal client memory from the person controlling the browser.

## Verification claims

For a concealed step, verification proves only that the snapshot is content-addressed, the commitment is well-formed, and the step is structurally positioned. Its cryptographic chain cannot be resolved until reveal provides the route and nonce.

For a revealed step, verification recomputes the route ID and commitment and checks the exact genesis, previous commitment, and index. It detects internal gaps, duplicate indexes, reordered revealed steps, and substituted reveals. It cannot prove wall-clock ordering or detect a privately truncated tail without another known snapshot.

The user-facing states are:

- `CONCEALED / COMMITMENT PRESENT`
- `REVEALED / COMMITMENT VERIFIED`
- `REJECTED / COMMITMENT MISMATCH`
- `VALID MIGRATION / NOT PRECOMMITTED`

## Wear and navigation

Wear begins when a step is committed, whether it is later revealed or not. It is derived at render time and is absent from the manifest. Wear and route metadata never enter selection or verification.

Committed count is monotonic. Current depth is separate navigation state and may decrease when the user returns toward the surface. Version 0.2 does not claim that current depth can be reconstructed from the commitment sequence.

## Compatibility

Version 0.1 remains readable and verifiable. A v0.1 artifact may be migrated into fully revealed v0.2 steps, but the migration is permanently marked `retroactive`; those steps are never described as precommitted. New blind steps can be appended only after migration creates a v0.2 genesis.

## Anti-ranking boundary

Blind Descent samples uniformly from its declared corpus pool using CSPRNG rejection sampling. Reveal state, wear, HTTP status, archive availability, popularity, and all other route metadata have no influence on selection.
