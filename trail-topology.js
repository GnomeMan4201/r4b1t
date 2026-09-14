(function (root, factory) {
  'use strict';
  var commonJs = typeof module === 'object' && module.exports;
  var api = factory(
    commonJs ? require('./trail-manifest.js') : root && root.R4b1tTrail,
    commonJs ? require('./blind-manifest.js') : root && root.R4b1tBlind
  );
  if (commonJs) module.exports = api;
  if (root) root.R4b1tTopology = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (trail, blind) {
  'use strict';

  if (!trail || !blind) throw new Error('Trail v0.1 and v0.2 APIs are required');

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function shortId(value) {
    return typeof value === 'string' ? value.replace(/^sha256:/, '').slice(0, 12) : 'unknown';
  }

  function host(url) {
    try { return new URL(url).hostname.replace(/^www\./, ''); }
    catch (_) { return 'invalid route'; }
  }

  async function verifyAny(input) {
    var value = typeof input === 'string' ? JSON.parse(input) : clone(input);
    if (!value || !value.manifest) throw new TypeError('Trail snapshot is malformed');
    if (value.manifest.format === trail.FORMAT) return trail.verify(value);
    if (value.manifest.format === blind.FORMAT) return blind.verify(value);
    throw new TypeError('Unsupported trail format');
  }

  function parentOf(snapshot) {
    var manifest = snapshot.manifest;
    if (manifest.format === trail.FORMAT) {
      return manifest.parent ? {
        trail_id: manifest.parent.trail_id,
        fork_at: manifest.parent.fork_at,
        commitment: null
      } : null;
    }
    var parent = manifest.genesis && manifest.genesis.parent;
    return parent ? {
      trail_id: parent.trail_id,
      fork_at: parent.fork_at,
      commitment: parent.commitment
    } : null;
  }

  function stopsOf(snapshot) {
    var manifest = snapshot.manifest;
    var parent = parentOf(snapshot);
    if (manifest.format === trail.FORMAT) {
      return manifest.routes.map(function (route, position) {
        return {
          index: position,
          state: 'revealed',
          label: host(route.url),
          url: route.url,
          action: route.action,
          inherited: Boolean(parent && position < parent.fork_at)
        };
      });
    }
    return manifest.steps.map(function (step, position) {
      return {
        index: position,
        state: step.state,
        label: step.state === 'revealed' ? host(step.route.url) : 'concealed',
        url: step.state === 'revealed' ? step.route.url : null,
        action: step.state === 'revealed' ? 'REVEAL' : 'COMMIT',
        inherited: false,
        commitment: step.commitment
      };
    });
  }

  async function build(inputs) {
    if (!Array.isArray(inputs)) throw new TypeError('Topology input must be an array');
    var snapshots = [];
    var seen = Object.create(null);
    for (var index = 0; index < inputs.length; index += 1) {
      var snapshot = await verifyAny(inputs[index]);
      if (!seen[snapshot.trail_id]) {
        seen[snapshot.trail_id] = true;
        snapshots.push(snapshot);
      }
    }
    snapshots.sort(function (left, right) {
      var leftTime = left.manifest.created_at || left.manifest.genesis.created_at;
      var rightTime = right.manifest.created_at || right.manifest.genesis.created_at;
      return leftTime.localeCompare(rightTime) || left.trail_id.localeCompare(right.trail_id);
    });
    var known = Object.create(null);
    snapshots.forEach(function (snapshot) { known[snapshot.trail_id] = snapshot; });
    for (var childIndex = 0; childIndex < snapshots.length; childIndex += 1) {
      var child = snapshots[childIndex];
      var declaration = parentOf(child);
      var parent = declaration && known[declaration.trail_id];
      if (!parent) continue;
      if (child.manifest.format === trail.FORMAT) await trail.verifyLineage(child, parent);
      else await blind.verifyLineage(child, parent);
    }
    return {
      snapshots: snapshots.map(function (snapshot) {
        var parent = parentOf(snapshot);
        var format = snapshot.manifest.format;
        return {
          trail_id: snapshot.trail_id,
          short_id: shortId(snapshot.trail_id),
          format: format,
          created_at: format === trail.FORMAT ? snapshot.manifest.created_at : snapshot.manifest.genesis.created_at,
          terrain: format === trail.FORMAT ? snapshot.manifest.terrain : snapshot.manifest.genesis.terrain,
          parent: parent,
          parent_known: !parent || Boolean(known[parent.trail_id]),
          stops: stopsOf(snapshot)
        };
      })
    };
  }

  return {
    verifyAny: verifyAny,
    parentOf: parentOf,
    stopsOf: stopsOf,
    build: build,
    shortId: shortId
  };
});
