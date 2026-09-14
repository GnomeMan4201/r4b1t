(function (root, factory) {
  'use strict';
  var commonJs = typeof module === 'object' && module.exports;
  var api = factory(commonJs ? require('./trail-manifest.js') : root && root.R4b1tTrail);
  if (commonJs) module.exports = api;
  if (root) root.R4b1tBlind = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (trail) {
  'use strict';

  if (!trail) throw new Error('R4b1tTrail v0.1 compatibility API is required');

  var FORMAT = 'r4b1t-trail/v0.2';
  var GENESIS_DOMAIN = 'r4b1t-genesis/v0.2';
  var STEP_DOMAIN = 'r4b1t-blind-step/v0.2';
  var SAMPLER = 'uniform-csprng-rejection-v1';
  var SHA256 = /^sha256:[0-9a-f]{64}$/;
  var BASE64URL_32 = /^[A-Za-z0-9_-]{43}$/;

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function assertKeys(value, expected, label) {
    if (Object.keys(value).sort().join(',') !== expected.slice().sort().join(',')) {
      throw new TypeError(label + ' contains unsupported fields');
    }
  }

  function randomBytes(size) {
    var bytes = new Uint8Array(size);
    globalThis.crypto.getRandomValues(bytes);
    return bytes;
  }

  function bytesToBase64Url(bytes) {
    if (typeof Buffer !== 'undefined') return Buffer.from(bytes).toString('base64url');
    var binary = '';
    for (var index = 0; index < bytes.length; index += 1) binary += String.fromCharCode(bytes[index]);
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  function base64UrlToBytes(value) {
    if (!BASE64URL_32.test(value || '')) throw new TypeError('Nonce must be canonical base64url for 32 bytes');
    var bytes;
    if (typeof Buffer !== 'undefined') {
      bytes = new Uint8Array(Buffer.from(value, 'base64url'));
    } else {
      var binary = atob(value.replace(/-/g, '+').replace(/_/g, '/') + '=');
      bytes = Uint8Array.from(binary, function (character) { return character.charCodeAt(0); });
    }
    if (bytes.length !== 32 || bytesToBase64Url(bytes) !== value) {
      throw new TypeError('Nonce must be canonical base64url for 32 bytes');
    }
    return bytes;
  }

  function randomNonce() {
    return bytesToBase64Url(randomBytes(32));
  }

  function assertTimestamp(value) {
    if (typeof value !== 'string' || new Date(value).toISOString() !== value) {
      throw new TypeError('Genesis creation time is invalid');
    }
    return value;
  }

  function normalizeParent(parent) {
    if (parent === null || typeof parent === 'undefined') return null;
    assertKeys(parent, ['trail_id', 'genesis_id', 'fork_at', 'commitment'], 'Genesis parent');
    if (!parent || !SHA256.test(parent.trail_id || '') || !SHA256.test(parent.genesis_id || '') ||
        !Number.isSafeInteger(parent.fork_at) || parent.fork_at < 0 ||
        !SHA256.test(parent.commitment || '')) {
      throw new TypeError('Genesis parent declaration is invalid');
    }
    return {
      trail_id: parent.trail_id,
      genesis_id: parent.genesis_id,
      fork_at: parent.fork_at,
      commitment: parent.commitment
    };
  }

  function genesisPayload(genesis) {
    return {
      domain: GENESIS_DOMAIN,
      format: FORMAT,
      created_at: genesis.created_at,
      corpus_revision: genesis.corpus_revision,
      terrain: genesis.terrain,
      sampler_algorithm: genesis.sampler_algorithm,
      trail_salt: genesis.trail_salt,
      parent: genesis.parent
    };
  }

  function validateGenesis(genesis) {
    if (!genesis || genesis.domain !== GENESIS_DOMAIN || genesis.format !== FORMAT) {
      throw new TypeError('Genesis format is invalid');
    }
    assertKeys(genesis, [
      'domain', 'format', 'created_at', 'corpus_revision', 'terrain',
      'sampler_algorithm', 'trail_salt', 'parent'
    ], 'Genesis');
    assertTimestamp(genesis.created_at);
    if (!SHA256.test(genesis.corpus_revision || '')) throw new TypeError('Genesis corpus revision is invalid');
    if (typeof genesis.terrain !== 'string' || !genesis.terrain) throw new TypeError('Genesis terrain is invalid');
    if (genesis.sampler_algorithm !== SAMPLER) throw new TypeError('Genesis sampler is invalid');
    base64UrlToBytes(genesis.trail_salt);
    normalizeParent(genesis.parent);
  }

  async function genesisId(genesis) {
    validateGenesis(genesis);
    return 'sha256:' + await trail.sha256Hex(trail.canonicalJson(genesisPayload(genesis)));
  }

  async function create(options) {
    options = options || {};
    var genesis = {
      domain: GENESIS_DOMAIN,
      format: FORMAT,
      created_at: new Date(options.created_at || Date.now()).toISOString(),
      corpus_revision: options.corpus_revision,
      terrain: String(options.terrain || 'ALL').toUpperCase(),
      sampler_algorithm: SAMPLER,
      trail_salt: options.trail_salt || randomNonce(),
      parent: normalizeParent(options.parent)
    };
    validateGenesis(genesis);
    return {
      format: FORMAT,
      genesis: genesis,
      genesis_id: await genesisId(genesis),
      steps: [],
      migration: options.migration || null
    };
  }

  async function stepCommitment(input) {
    if (!input || !SHA256.test(input.genesis_id || '') || !SHA256.test(input.previous_commitment || '') ||
        !Number.isSafeInteger(input.step_index) || input.step_index < 0 || !SHA256.test(input.route_id || '')) {
      throw new TypeError('Blind commitment input is invalid');
    }
    base64UrlToBytes(input.nonce);
    return 'sha256:' + await trail.sha256Hex(trail.canonicalJson({
      domain: STEP_DOMAIN,
      genesis_id: input.genesis_id,
      previous_commitment: input.previous_commitment,
      step_index: input.step_index,
      route_id: input.route_id,
      nonce: input.nonce
    }));
  }

  function validateMigration(migration) {
    if (migration === null || typeof migration === 'undefined') return null;
    assertKeys(migration, ['from', 'source_trail_id', 'commitment_status'], 'Migration');
    if (!migration || migration.from !== 'r4b1t-trail/v0.1' ||
        !SHA256.test(migration.source_trail_id || '') || migration.commitment_status !== 'retroactive') {
      throw new TypeError('Migration declaration is invalid');
    }
    return migration;
  }

  async function validateManifest(manifest) {
    if (!manifest || manifest.format !== FORMAT || !Array.isArray(manifest.steps)) {
      throw new TypeError('Blind trail manifest is malformed');
    }
    assertKeys(manifest, ['format', 'genesis', 'genesis_id', 'steps', 'migration'], 'Blind trail manifest');
    validateGenesis(manifest.genesis);
    var expectedGenesisId = await genesisId(manifest.genesis);
    if (manifest.genesis_id !== expectedGenesisId) throw new Error('Genesis ID mismatch');
    validateMigration(manifest.migration);
    var statuses = [];
    for (var index = 0; index < manifest.steps.length; index += 1) {
      var step = manifest.steps[index];
      if (!step || step.index !== index) throw new Error('Step indexes must be contiguous');
      if (!SHA256.test(step.commitment || '')) throw new TypeError('Step commitment is invalid at index ' + index);
      if (step.state === 'concealed') {
        if (Object.keys(step).sort().join(',') !== 'commitment,index,state') {
          throw new TypeError('Concealed step leaks unsupported fields at index ' + index);
        }
        statuses.push({ index: index, status: 'COMMITMENT PRESENT' });
        continue;
      }
      if (step.state !== 'revealed' || !step.route || typeof step.route.url !== 'string') {
        throw new TypeError('Step state is invalid at index ' + index);
      }
      assertKeys(step, ['index', 'state', 'commitment', 'route', 'nonce'], 'Revealed step');
      assertKeys(step.route, ['route_id', 'url'], 'Revealed route');
      var routeId = await trail.routeId(step.route.url);
      if (step.route.route_id !== routeId) throw new Error('Route ID mismatch at index ' + index);
      var previous = index === 0 ? manifest.genesis_id : manifest.steps[index - 1].commitment;
      var expectedCommitment = await stepCommitment({
        genesis_id: manifest.genesis_id,
        previous_commitment: previous,
        step_index: index,
        route_id: routeId,
        nonce: step.nonce
      });
      if (step.commitment !== expectedCommitment) throw new Error('Commitment mismatch at index ' + index);
      statuses.push({
        index: index,
        status: manifest.migration ? 'RETROACTIVE / NOT PRECOMMITTED' : 'COMMITMENT VERIFIED'
      });
    }
    return statuses;
  }

  async function commit(manifestInput, url, nonce) {
    var manifest = clone(manifestInput);
    await validateManifest(manifest);
    var index = manifest.steps.length;
    var routeId = await trail.routeId(url);
    var secretNonce = nonce || randomNonce();
    var previous = index === 0 ? manifest.genesis_id : manifest.steps[index - 1].commitment;
    var commitment = await stepCommitment({
      genesis_id: manifest.genesis_id,
      previous_commitment: previous,
      step_index: index,
      route_id: routeId,
      nonce: secretNonce
    });
    manifest.steps.push({ index: index, state: 'concealed', commitment: commitment });
    return {
      manifest: manifest,
      secret: { index: index, route_id: routeId, url: url, nonce: secretNonce }
    };
  }

  async function reveal(manifestInput, secret) {
    var manifest = clone(manifestInput);
    await validateManifest(manifest);
    if (!secret || !Number.isSafeInteger(secret.index) || !manifest.steps[secret.index]) {
      throw new TypeError('Reveal secret is invalid');
    }
    var step = manifest.steps[secret.index];
    if (step.state !== 'concealed') throw new Error('Step is not concealed');
    var routeId = await trail.routeId(secret.url);
    if (secret.route_id !== routeId) throw new Error('Reveal route ID mismatch');
    var previous = secret.index === 0 ? manifest.genesis_id : manifest.steps[secret.index - 1].commitment;
    var commitment = await stepCommitment({
      genesis_id: manifest.genesis_id,
      previous_commitment: previous,
      step_index: secret.index,
      route_id: routeId,
      nonce: secret.nonce
    });
    if (step.commitment !== commitment) throw new Error('Reveal does not match commitment');
    manifest.steps[secret.index] = {
      index: secret.index,
      state: 'revealed',
      commitment: step.commitment,
      route: { route_id: routeId, url: secret.url },
      nonce: secret.nonce
    };
    return manifest;
  }

  async function envelope(manifestInput) {
    var manifest = clone(manifestInput);
    await validateManifest(manifest);
    return {
      trail_id: 'sha256:' + await trail.sha256Hex(trail.canonicalJson(manifest)),
      manifest: manifest
    };
  }

  async function verify(input) {
    var parsed = typeof input === 'string' ? JSON.parse(input) : clone(input);
    if (!parsed || !SHA256.test(parsed.trail_id || '') || !parsed.manifest) {
      throw new TypeError('Blind trail envelope is malformed');
    }
    var statuses = await validateManifest(parsed.manifest);
    var expected = await envelope(parsed.manifest);
    if (parsed.trail_id !== expected.trail_id) throw new Error('Trail ID mismatch');
    return { trail_id: parsed.trail_id, manifest: parsed.manifest, statuses: statuses };
  }

  async function verifyLineage(childInput, parentInput) {
    var child = await verify(childInput);
    var parent = await verify(parentInput);
    var declaration = child.manifest.genesis.parent;
    if (!declaration) throw new TypeError('Child genesis does not declare a parent');
    if (declaration.trail_id !== parent.trail_id) throw new Error('Parent snapshot ID mismatch');
    if (declaration.genesis_id !== parent.manifest.genesis_id) throw new Error('Parent genesis ID mismatch');
    var parentStep = parent.manifest.steps[declaration.fork_at];
    if (!parentStep || parentStep.commitment !== declaration.commitment) {
      throw new Error('Parent fork commitment mismatch');
    }
    return { child: child, parent: parent, fork_at: declaration.fork_at };
  }

  function deriveWear(manifest) {
    var committed = manifest && Array.isArray(manifest.steps) ? manifest.steps.length : 0;
    return {
      committed_count: committed,
      creases: Math.min(committed, 12),
      fold_size: Math.min(24, 4 + committed * 2)
    };
  }

  async function migrateV01(input, options) {
    var source = await trail.verify(input);
    options = options || {};
    var manifest = await create({
      created_at: options.created_at,
      corpus_revision: source.manifest.corpus_revision,
      terrain: source.manifest.terrain,
      trail_salt: options.trail_salt,
      parent: options.parent,
      migration: {
        from: 'r4b1t-trail/v0.1',
        source_trail_id: source.trail_id,
        commitment_status: 'retroactive'
      }
    });
    for (var index = 0; index < source.manifest.routes.length; index += 1) {
      var route = source.manifest.routes[index];
      var committed = await commit(manifest, route.url);
      manifest = await reveal(committed.manifest, committed.secret);
    }
    return manifest;
  }

  return {
    FORMAT: FORMAT,
    GENESIS_DOMAIN: GENESIS_DOMAIN,
    STEP_DOMAIN: STEP_DOMAIN,
    SAMPLER: SAMPLER,
    randomNonce: randomNonce,
    create: create,
    genesisId: genesisId,
    stepCommitment: stepCommitment,
    commit: commit,
    reveal: reveal,
    envelope: envelope,
    verify: verify,
    verifyLineage: verifyLineage,
    deriveWear: deriveWear,
    migrateV01: migrateV01
  };
});
