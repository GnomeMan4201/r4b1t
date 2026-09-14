'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const test = require('node:test');
const trail = require('../trail-manifest.js');
const blind = require('../blind-manifest.js');

const CORPUS = `sha256:${'a'.repeat(64)}`;
const SALT = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
const NONCE_1 = 'AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE';
const NONCE_2 = 'AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI';

async function origin() {
  return blind.create({
    created_at: '2026-09-14T23:00:00.000Z',
    corpus_revision: CORPUS,
    terrain: 'RESEARCH',
    trail_salt: SALT,
  });
}

test('concealed public form leaks neither route identity nor nonce', async () => {
  const committed = await blind.commit(await origin(), 'https://example.org/hidden', NONCE_1);
  assert.deepEqual(Object.keys(committed.manifest.steps[0]).sort(), ['commitment', 'index', 'state']);
  assert.equal(JSON.stringify(committed.manifest).includes('example.org'), false);
  assert.equal(JSON.stringify(committed.manifest).includes(NONCE_1), false);
  assert.equal(JSON.stringify(committed.manifest).includes('seed'), false);

  const verified = await blind.verify(await blind.envelope(committed.manifest));
  assert.equal(verified.statuses[0].status, 'COMMITMENT PRESENT');
});

test('reveal verifies against the exact concealed commitment', async () => {
  const committed = await blind.commit(await origin(), 'https://example.org/hidden', NONCE_1);
  const revealed = await blind.reveal(committed.manifest, committed.secret);
  const verified = await blind.verify(await blind.envelope(revealed));
  assert.equal(verified.statuses[0].status, 'COMMITMENT VERIFIED');
  assert.equal(verified.manifest.steps[0].route.url, 'https://example.org/hidden');
});

test('substituted reveal fails even when the attacker recomputes trail_id', async () => {
  const committed = await blind.commit(await origin(), 'https://example.org/hidden', NONCE_1);
  const revealed = await blind.reveal(committed.manifest, committed.secret);
  revealed.steps[0].route.url = 'https://example.net/substituted';
  revealed.steps[0].route.route_id = await trail.routeId(revealed.steps[0].route.url);
  const forged = {
    trail_id: `sha256:${await trail.sha256Hex(trail.canonicalJson(revealed))}`,
    manifest: revealed,
  };
  await assert.rejects(() => blind.verify(forged), /Commitment mismatch at index 0/);
});

test('commitments are chained to their genesis and prior position', async () => {
  const first = await blind.commit(await origin(), 'https://example.org/one', NONCE_1);
  const second = await blind.commit(first.manifest, 'https://example.net/two', NONCE_2);
  const firstRevealed = await blind.reveal(second.manifest, first.secret);
  const fullyRevealed = await blind.reveal(firstRevealed, second.secret);
  const verified = await blind.verify(await blind.envelope(fullyRevealed));
  assert.deepEqual(verified.statuses.map((entry) => entry.status), [
    'COMMITMENT VERIFIED',
    'COMMITMENT VERIFIED',
  ]);

  fullyRevealed.steps.reverse();
  fullyRevealed.steps.forEach((step, index) => { step.index = index; });
  const forged = {
    trail_id: `sha256:${await trail.sha256Hex(trail.canonicalJson(fullyRevealed))}`,
    manifest: fullyRevealed,
  };
  await assert.rejects(() => blind.verify(forged), /Commitment mismatch/);
});

test('genesis identity binds exact fork lineage', async () => {
  const parent = {
    trail_id: `sha256:${'b'.repeat(64)}`,
    genesis_id: `sha256:${'c'.repeat(64)}`,
    fork_at: 3,
    commitment: `sha256:${'d'.repeat(64)}`,
  };
  const manifest = await blind.create({
    created_at: '2026-09-14T23:00:00.000Z',
    corpus_revision: CORPUS,
    terrain: 'RESEARCH',
    trail_salt: SALT,
    parent,
  });
  const originalId = manifest.genesis_id;
  manifest.genesis.parent.fork_at = 4;
  assert.notEqual(await blind.genesisId(manifest.genesis), originalId);
});

test('v0.2 lineage resolves an exact parent snapshot and commitment', async () => {
  const first = await blind.commit(await origin(), 'https://example.org/one', NONCE_1);
  const parent = await blind.envelope(first.manifest);
  const childManifest = await blind.create({
    created_at: '2026-09-14T23:30:00.000Z',
    corpus_revision: CORPUS,
    terrain: 'RESEARCH',
    trail_salt: NONCE_2,
    parent: {
      trail_id: parent.trail_id,
      genesis_id: parent.manifest.genesis_id,
      fork_at: 0,
      commitment: parent.manifest.steps[0].commitment,
    },
  });
  const child = await blind.envelope(childManifest);
  const lineage = await blind.verifyLineage(child, parent);
  assert.equal(lineage.fork_at, 0);

  child.manifest.genesis.parent.commitment = `sha256:${'f'.repeat(64)}`;
  child.manifest.genesis_id = await blind.genesisId(child.manifest.genesis);
  child.trail_id = `sha256:${await trail.sha256Hex(trail.canonicalJson(child.manifest))}`;
  await assert.rejects(() => blind.verifyLineage(child, parent), /Parent fork commitment mismatch/);
});

test('v0.1 migration is valid but never reported as precommitted', async () => {
  const sourceManifest = await trail.createManifest({
    created_at: '2026-09-14T21:00:00.000Z',
    corpus_revision: CORPUS,
    seed: 'legacy-seed',
    terrain: 'RESEARCH',
    routes: [{ url: 'https://example.org/legacy', action: 'ROLL' }],
    parent: null,
  });
  const migrated = await blind.migrateV01(await trail.envelope(sourceManifest), {
    created_at: '2026-09-14T23:00:00.000Z',
    trail_salt: SALT,
  });
  const verified = await blind.verify(await blind.envelope(migrated));
  assert.equal(verified.manifest.migration.commitment_status, 'retroactive');
  assert.equal(verified.statuses[0].status, 'RETROACTIVE / NOT PRECOMMITTED');
});

test('derived wear counts commitments without entering the manifest', async () => {
  const first = await blind.commit(await origin(), 'https://example.org/one', NONCE_1);
  const second = await blind.commit(first.manifest, 'https://example.net/two', NONCE_2);
  assert.deepEqual(blind.deriveWear(second.manifest), {
    committed_count: 2,
    creases: 2,
    fold_size: 8,
  });
  assert.equal(Object.hasOwn(second.manifest, 'wear'), false);
});

test('published concealed and revealed vectors retain stable identities', async () => {
  const vector = async (name) => JSON.parse(await fs.readFile(
    path.join(__dirname, 'fixtures', 'blind', name),
    'utf8',
  ));
  const concealed = await blind.verify(await vector('concealed.json'));
  const revealed = await blind.verify(await vector('revealed.json'));
  assert.equal(concealed.trail_id,
    'sha256:d3acbe0ee784626e6ebceff5ed5012b2e08899b43b6a220e4f5e281b609dfad0');
  assert.equal(revealed.trail_id,
    'sha256:f6ba66bd58f40217aa27d996d4f504011ab3695b4af8808d7aa0b53d83fc4f5c');
  assert.equal(concealed.manifest.genesis_id, revealed.manifest.genesis_id);
  assert.equal(concealed.manifest.steps[0].commitment, revealed.manifest.steps[0].commitment);
});
