'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const test = require('node:test');
const trail = require('../trail-manifest.js');

const CORPUS_REVISION = `sha256:${'a'.repeat(64)}`;

async function fixture() {
  const manifest = await trail.createManifest({
    created_at: '2026-09-14T21:00:00.000Z',
    corpus_revision: CORPUS_REVISION,
    seed: 'rabbit-seed',
    terrain: 'RESEARCH',
    routes: [
      { url: 'https://example.org/one', action: 'ROLL' },
      { url: 'https://example.net/two', action: 'BRANCH' },
    ],
    parent: null,
  });
  return trail.envelope(manifest);
}

async function forkFixture(parent, routes) {
  const manifest = await trail.createManifest({
    created_at: '2026-09-14T22:00:00.000Z',
    corpus_revision: CORPUS_REVISION,
    seed: 'fork-seed',
    terrain: 'RESEARCH',
    routes,
    parent: { trail_id: parent.trail_id, fork_at: 1 },
  });
  return trail.envelope(manifest);
}

test('canonical JSON is independent of object insertion order', () => {
  assert.equal(
    trail.canonicalJson({ z: 2, a: { y: 4, b: 3 } }),
    trail.canonicalJson({ a: { b: 3, y: 4 }, z: 2 }),
  );
});

test('seeded sampler produces an identical sequence for the same seed', () => {
  const left = trail.createSampler('same-seed');
  const right = trail.createSampler('same-seed');
  assert.deepEqual(
    Array.from({ length: 12 }, left),
    Array.from({ length: 12 }, right),
  );
});

test('trail envelope verifies and replays exact recorded order', async () => {
  const envelope = await fixture();
  assert.match(envelope.trail_id, /^sha256:[0-9a-f]{64}$/);
  assert.deepEqual(await trail.replay(JSON.stringify(envelope)), [
    'https://example.org/one',
    'https://example.net/two',
  ]);
});

test('import fails closed after manifest tampering', async () => {
  const envelope = await fixture();
  envelope.manifest.routes[0].url = 'https://attacker.invalid/replaced';
  await assert.rejects(() => trail.verify(envelope), /Route ID mismatch/);
});

test('import rejects a recomputed envelope with an unknown sampler', async () => {
  const original = await fixture();
  original.manifest.sampler.prng = 'mystery-prng';
  original.trail_id = `sha256:${await trail.sha256Hex(trail.canonicalJson(original.manifest))}`;
  await assert.rejects(() => trail.verify(original), /Sampler declaration is invalid/);
});

test('route identifiers reject credentials and unsupported protocols', async () => {
  await assert.rejects(() => trail.routeId('https://user:secret@example.org'), /credentials/);
  await assert.rejects(() => trail.routeId('javascript:alert(1)'), /HTTP or HTTPS/);
});

test('lineage verification accepts an identical inherited prefix', async () => {
  const parent = await fixture();
  const child = await forkFixture(parent, [
    { url: 'https://example.org/one', action: 'ROLL' },
    { url: 'https://example.com/divergent', action: 'ROLL' },
  ]);
  const result = await trail.verifyLineage(child, parent);
  assert.equal(result.fork_at, 1);
  assert.equal(result.parent.trail_id, parent.trail_id);
  assert.equal(result.child.trail_id, child.trail_id);
});

test('lineage verification rejects a valid child with a false inherited prefix', async () => {
  const parent = await fixture();
  const child = await forkFixture(parent, [
    { url: 'https://example.org/not-inherited', action: 'ROLL' },
  ]);
  await assert.rejects(() => trail.verifyLineage(child, parent), /Fork prefix mismatch at step 1/);
});

test('lineage verification rejects the wrong parent artifact', async () => {
  const parent = await fixture();
  const child = await forkFixture(parent, [{ url: 'https://example.org/one', action: 'ROLL' }]);
  const other = await trail.envelope(await trail.createManifest({
    created_at: '2026-09-14T21:30:00.000Z',
    corpus_revision: CORPUS_REVISION,
    seed: 'other-parent',
    terrain: 'RESEARCH',
    routes: [{ url: 'https://example.org/one', action: 'ROLL' }],
    parent: null,
  }));
  await assert.rejects(() => trail.verifyLineage(child, other), /Parent trail ID mismatch/);
});

test('manifest creation rejects a fork beyond its inherited child prefix', async () => {
  const parent = await fixture();
  await assert.rejects(() => trail.createManifest({
    created_at: '2026-09-14T22:00:00.000Z',
    corpus_revision: CORPUS_REVISION,
    seed: 'fork-seed',
    terrain: 'RESEARCH',
    routes: [{ url: 'https://example.org/one', action: 'ROLL' }],
    parent: { trail_id: parent.trail_id, fork_at: 2 },
  }), /Fork position exceeds child route prefix/);
});

test('published parent and child vectors retain stable IDs and lineage', async () => {
  const vector = async (name) => JSON.parse(await fs.readFile(
    path.join(__dirname, 'fixtures', 'trails', name),
    'utf8',
  ));
  const parent = await vector('parent.json');
  const child = await vector('child.json');
  assert.equal((await trail.verify(parent)).trail_id,
    'sha256:f3157a79164b07f2f3fa40902981e06e0f5417a4565a8efa279984706fe2596c');
  assert.equal((await trail.verify(child)).trail_id,
    'sha256:26d7e7b5585123024fe1ab5de428e030c7da3d45d9ad62fa597b5a03591dee74');
  assert.equal((await trail.verifyLineage(child, parent)).fork_at, 1);
});
