'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const trail = require('../trail-manifest.js');
const blind = require('../blind-manifest.js');
const topology = require('../trail-topology.js');

const CORPUS = 'sha256:' + 'a'.repeat(64);
const SALT = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
const NONCE = 'AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE';

async function v01(options) {
  return trail.envelope(await trail.createManifest({
    created_at: options.created_at,
    corpus_revision: CORPUS,
    seed: options.seed,
    terrain: 'RESEARCH',
    routes: options.routes,
    parent: options.parent || null,
  }));
}

test('topology verifies, deduplicates, and links known v0.1 snapshots', async () => {
  const parent = await v01({
    created_at: '2026-09-14T20:00:00.000Z',
    seed: 'parent',
    routes: [{ url: 'https://example.org/one', action: 'ROLL' }],
  });
  const child = await v01({
    created_at: '2026-09-14T21:00:00.000Z',
    seed: 'child',
    routes: [
      { url: 'https://example.org/one', action: 'ROLL' },
      { url: 'https://example.net/two', action: 'BRANCH' },
    ],
    parent: { trail_id: parent.trail_id, fork_at: 1 },
  });
  const graph = await topology.build([child, parent, child]);
  assert.equal(graph.snapshots.length, 2);
  assert.equal(graph.snapshots[1].parent_known, true);
  assert.equal(graph.snapshots[1].stops[0].inherited, true);
  assert.equal(graph.snapshots[1].stops[1].inherited, false);
});

test('topology preserves an honest unresolved-parent stub', async () => {
  const child = await v01({
    created_at: '2026-09-14T21:00:00.000Z',
    seed: 'child',
    routes: [{ url: 'https://example.org/one', action: 'ROLL' }],
    parent: { trail_id: 'sha256:' + 'b'.repeat(64), fork_at: 1 },
  });
  const graph = await topology.build([child]);
  assert.equal(graph.snapshots[0].parent_known, false);
});

test('concealed v0.2 stops expose no route identity through topology', async () => {
  const manifest = await blind.create({
    created_at: '2026-09-14T22:00:00.000Z',
    corpus_revision: CORPUS,
    terrain: 'RESEARCH',
    trail_salt: SALT,
  });
  const committed = await blind.commit(manifest, 'https://secret.example/path', NONCE);
  const snapshot = await blind.envelope(committed.manifest);
  const graph = await topology.build([snapshot]);
  const serialized = JSON.stringify(graph);
  assert.equal(graph.snapshots[0].stops[0].state, 'concealed');
  assert.equal(graph.snapshots[0].stops[0].url, null);
  assert.equal(serialized.includes('secret.example'), false);
});

test('topology rejects a tampered snapshot instead of mapping it', async () => {
  const snapshot = await v01({
    created_at: '2026-09-14T20:00:00.000Z',
    seed: 'parent',
    routes: [{ url: 'https://example.org/one', action: 'ROLL' }],
  });
  snapshot.manifest.routes[0].url = 'https://attacker.invalid/';
  await assert.rejects(() => topology.build([snapshot]), /Route ID mismatch/);
});

test('topology rejects individually valid snapshots with false lineage', async () => {
  const parent = await v01({
    created_at: '2026-09-14T20:00:00.000Z',
    seed: 'parent',
    routes: [{ url: 'https://example.org/one', action: 'ROLL' }],
  });
  const child = await v01({
    created_at: '2026-09-14T21:00:00.000Z',
    seed: 'child',
    routes: [{ url: 'https://example.net/not-inherited', action: 'ROLL' }],
    parent: { trail_id: parent.trail_id, fork_at: 1 },
  });
  await assert.rejects(() => topology.build([parent, child]), /Fork prefix mismatch/);
});

test('v0.2 child stops begin after the parent fork and are not inherited', async () => {
  const parentManifest = await blind.create({
    created_at: '2026-09-14T22:00:00.000Z',
    corpus_revision: CORPUS,
    terrain: 'RESEARCH',
    trail_salt: SALT,
  });
  const parentCommitted = await blind.commit(parentManifest, 'https://example.org/parent', NONCE);
  const parent = await blind.envelope(parentCommitted.manifest);
  const childManifest = await blind.create({
    created_at: '2026-09-14T23:00:00.000Z',
    corpus_revision: CORPUS,
    terrain: 'RESEARCH',
    trail_salt: 'AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI',
    parent: {
      trail_id: parent.trail_id,
      genesis_id: parent.manifest.genesis_id,
      fork_at: 0,
      commitment: parent.manifest.steps[0].commitment,
    },
  });
  const childCommitted = await blind.commit(
    childManifest,
    'https://example.net/after-fork',
    'AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwM',
  );
  const child = await blind.envelope(childCommitted.manifest);
  const graph = await topology.build([parent, child]);
  const childNode = graph.snapshots.find((snapshot) => snapshot.trail_id === child.trail_id);
  assert.equal(childNode.parent_known, true);
  assert.equal(childNode.stops[0].inherited, false);
});
