# ADR 0001: Anti-ranking boundary

Status: Accepted

## Decision

r4b1t separates corpus admission, explicit eligibility controls, mechanical repeat suppression, and route presentation.

The selection algorithm may depend only on:

1. the committed corpus revision;
2. an explicit terrain selected by the user;
3. protocol and policy exclusions chosen by the user; and
4. documented mechanical constraints that prevent an immediate repeat.

Within that boundary, selection is driven by the declared pseudorandom sampler. Route metadata must never silently increase or decrease a route's probability.

## Display-only metadata

The following fields may be shown in a route dossier but must not condition selection:

- HTTP status or redirect count;
- last-checked or first-seen time;
- archive availability;
- popularity, reputation, or editorial assessment; and
- any inferred quality, safety, or relevance score.

Corpus admission remains a reviewed governance action. Removing an invalid, credential-bearing, malicious, or policy-prohibited entry is not ranking. Liveness alone is not sufficient grounds for automatic removal.

## Verification

Selection code and tests must keep route metadata outside the sampler input. Any future weighted sampler requires a new ADR and must not replace the default unranked sampler silently.
