(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.R4b1tTrail = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var FORMAT = 'r4b1t-trail/v0.1';
  var ROUTE_PREFIX = 'r4b1t-route/v0.1\n';
  var TRAIL_PREFIX = 'sha256:';

  function canonicalJson(value) {
    if (value === null || typeof value === 'boolean' || typeof value === 'string') {
      return JSON.stringify(value);
    }
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) throw new TypeError('Canonical JSON rejects non-finite numbers');
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
    if (value && Object.getPrototypeOf(value) === Object.prototype) {
      var keys = Object.keys(value).sort();
      return '{' + keys.map(function (key) {
        if (typeof value[key] === 'undefined') throw new TypeError('Canonical JSON rejects undefined values');
        return JSON.stringify(key) + ':' + canonicalJson(value[key]);
      }).join(',') + '}';
    }
    throw new TypeError('Canonical JSON accepts plain JSON values only');
  }

  function utf8(value) {
    return new TextEncoder().encode(value);
  }

  async function sha256Hex(value) {
    var bytes = typeof value === 'string' ? utf8(value) : value;
    if (!(bytes instanceof Uint8Array)) bytes = new Uint8Array(bytes);
    if (!globalThis.crypto || !globalThis.crypto.subtle) throw new Error('Web Crypto SHA-256 is unavailable');
    var digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), function (byte) {
      return byte.toString(16).padStart(2, '0');
    }).join('');
  }

  function seedToUint32(seed) {
    var bytes = utf8(String(seed));
    var hash = 2166136261;
    for (var index = 0; index < bytes.length; index += 1) {
      hash ^= bytes[index];
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function createSampler(seed) {
    var state = seedToUint32(seed);
    return function nextFloat() {
      state = (state + 0x6d2b79f5) >>> 0;
      var mixed = state;
      mixed = Math.imul(mixed ^ (mixed >>> 15), mixed | 1);
      mixed ^= mixed + Math.imul(mixed ^ (mixed >>> 7), mixed | 61);
      return ((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296;
    };
  }

  function assertUrl(url) {
    if (typeof url !== 'string' || !url.trim()) throw new TypeError('Route URL must be a non-empty string');
    var parsed = new URL(url);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      throw new TypeError('Route URL must use HTTP or HTTPS');
    }
    if (parsed.username || parsed.password) throw new TypeError('Route URL must not contain credentials');
    return url.trim();
  }

  async function routeId(url) {
    return TRAIL_PREFIX + await sha256Hex(ROUTE_PREFIX + assertUrl(url));
  }

  function normalizeParent(parent) {
    if (parent === null || typeof parent === 'undefined') return null;
    if (!parent || typeof parent.trail_id !== 'string' || !/^sha256:[0-9a-f]{64}$/.test(parent.trail_id)) {
      throw new TypeError('Parent trail ID is invalid');
    }
    if (!Number.isSafeInteger(parent.fork_at) || parent.fork_at < 0) throw new TypeError('Fork position is invalid');
    return { trail_id: parent.trail_id, fork_at: parent.fork_at };
  }

  async function createManifest(options) {
    options = options || {};
    if (!/^sha256:[0-9a-f]{64}$/.test(options.corpus_revision || '')) {
      throw new TypeError('Corpus revision must be a sha256 identifier');
    }
    if (!Array.isArray(options.routes)) throw new TypeError('Routes must be an array');
    var routes = [];
    for (var index = 0; index < options.routes.length; index += 1) {
      var source = options.routes[index];
      var url = assertUrl(typeof source === 'string' ? source : source.url);
      routes.push({
        index: index + 1,
        route_id: await routeId(url),
        url: url,
        action: String((source && source.action) || 'ROLL').toUpperCase()
      });
    }
    var parent = normalizeParent(options.parent);
    if (parent && parent.fork_at > routes.length) {
      throw new TypeError('Fork position exceeds child route prefix');
    }
    return {
      format: FORMAT,
      created_at: new Date(options.created_at || Date.now()).toISOString(),
      corpus_revision: options.corpus_revision,
      sampler: {
        algorithm: 'uniform-with-repeat-guard-v1',
        prng: 'mulberry32-v1',
        seed: String(options.seed)
      },
      terrain: String(options.terrain || 'ALL').toUpperCase(),
      routes: routes,
      parent: parent
    };
  }

  async function envelope(manifest) {
    validateManifestShape(manifest);
    return {
      trail_id: TRAIL_PREFIX + await sha256Hex(canonicalJson(manifest)),
      manifest: manifest
    };
  }

  function validateManifestShape(manifest) {
    if (!manifest || manifest.format !== FORMAT) throw new TypeError('Unsupported trail format');
    if (typeof manifest.created_at !== 'string' || new Date(manifest.created_at).toISOString() !== manifest.created_at) {
      throw new TypeError('Trail creation time is invalid');
    }
    if (!/^sha256:[0-9a-f]{64}$/.test(manifest.corpus_revision || '')) {
      throw new TypeError('Corpus revision is invalid');
    }
    if (!manifest.sampler || manifest.sampler.algorithm !== 'uniform-with-repeat-guard-v1' ||
        manifest.sampler.prng !== 'mulberry32-v1' || typeof manifest.sampler.seed !== 'string' || !manifest.sampler.seed) {
      throw new TypeError('Sampler declaration is invalid');
    }
    if (typeof manifest.terrain !== 'string' || !manifest.terrain) throw new TypeError('Terrain is invalid');
    if (!Array.isArray(manifest.routes)) throw new TypeError('Routes must be an array');
    var parent = normalizeParent(manifest.parent);
    if (parent && parent.fork_at > manifest.routes.length) {
      throw new TypeError('Fork position exceeds child route prefix');
    }
  }

  async function verify(input) {
    var parsed = typeof input === 'string' ? JSON.parse(input) : input;
    if (!parsed || typeof parsed.trail_id !== 'string' || !parsed.manifest) {
      throw new TypeError('Trail envelope is malformed');
    }
    var manifest = parsed.manifest;
    validateManifestShape(manifest);
    for (var index = 0; index < manifest.routes.length; index += 1) {
      var route = manifest.routes[index];
      if (route.index !== index + 1) throw new TypeError('Route indexes must be contiguous');
      var expectedRouteId = await routeId(route.url);
      if (route.route_id !== expectedRouteId) throw new Error('Route ID mismatch at step ' + (index + 1));
    }
    var expected = await envelope(manifest);
    if (expected.trail_id !== parsed.trail_id) throw new Error('Trail ID mismatch');
    return parsed;
  }

  async function replay(input) {
    var verified = await verify(input);
    return verified.manifest.routes.map(function (route) { return route.url; });
  }

  async function verifyLineage(childInput, parentInput) {
    var child = await verify(childInput);
    var parent = await verify(parentInput);
    var declaration = child.manifest.parent;
    if (!declaration) throw new TypeError('Child trail does not declare a parent');
    if (declaration.trail_id !== parent.trail_id) throw new Error('Parent trail ID mismatch');
    if (declaration.fork_at > parent.manifest.routes.length ||
        declaration.fork_at > child.manifest.routes.length) {
      throw new Error('Fork position exceeds the available route prefix');
    }
    for (var index = 0; index < declaration.fork_at; index += 1) {
      if (canonicalJson(child.manifest.routes[index]) !== canonicalJson(parent.manifest.routes[index])) {
        throw new Error('Fork prefix mismatch at step ' + (index + 1));
      }
    }
    return { child: child, parent: parent, fork_at: declaration.fork_at };
  }

  return {
    FORMAT: FORMAT,
    canonicalJson: canonicalJson,
    sha256Hex: sha256Hex,
    createSampler: createSampler,
    routeId: routeId,
    createManifest: createManifest,
    envelope: envelope,
    verify: verify,
    verifyLineage: verifyLineage,
    replay: replay
  };
});
