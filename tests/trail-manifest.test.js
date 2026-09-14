'use strict';

const assert = require('node:assert/strict');
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
