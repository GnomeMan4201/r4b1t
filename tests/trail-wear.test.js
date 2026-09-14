'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const wear = require('../trail-wear.js');

test('wear fields map directly into a static visual model', () => {
  const model = wear.normalize({
    depth: 7,
    crease_count: 11,
    fold_size: 24,
    stops: [
      { index: 0, state: 'revealed', label: 'example.org', url: 'https://example.org/', action: 'REVEAL' },
      { index: 1, state: 'concealed', commitment: 'sha256:hidden', action: 'COMMIT' },
    ],
  });
  assert.equal(model.depth, 7);
  assert.equal(model.crease_count, 11);
  assert.equal(model.fold_size, 24);
  assert.equal(model.concealed_count, 1);
  assert.equal(model.stops[1].label, 'REDACTED');
  assert.equal(model.stops[1].url, null);
});

test('v0.1 forked routes retain inherited wear before divergence', () => {
  const model = wear.normalize({
    format: 'r4b1t-trail/v0.1',
    parent: { trail_id: 'sha256:parent', fork_at: 2 },
    stops: [
      { index: 0, state: 'revealed', label: 'one', url: 'https://one.example/', inherited: true },
      { index: 1, state: 'revealed', label: 'two', url: 'https://two.example/', inherited: true },
      { index: 2, state: 'revealed', label: 'three', url: 'https://three.example/' },
    ],
  });
  assert.equal(model.inherited_count, 2);
});

test('v0.2 fork composition carries parent paper to fork then diverges', () => {
  const parent = {
    stops: [
      { index: 0, state: 'revealed', label: 'visible', url: 'https://example.org/' },
      { index: 1, state: 'concealed', label: 'REDACTED', url: null },
      { index: 2, state: 'revealed', label: 'after', url: 'https://after.example/' },
    ],
  };
  const child = {
    format: 'r4b1t-trail/v0.2',
    parent: { trail_id: 'sha256:parent', fork_at: 1 },
    stops: [{ index: 0, state: 'revealed', label: 'branch', url: 'https://branch.example/' }],
  };
  const stops = wear.composeFork(child, parent);
  assert.equal(stops.length, 3);
  assert.equal(stops[0].inherited, true);
  assert.equal(stops[1].inherited, true);
  assert.equal(stops[1].state, 'concealed');
  assert.equal(stops[2].inherited, false);
  assert.equal(stops[2].divergent, true);
});
