(function () {
  'use strict';

  var api = window.R4b1tTopology;
  var wear = window.R4b1tWear;
  var blind = window.R4b1tBlind;
  if (!api || !wear || !blind) return;
  var STORAGE_KEY = 'r4b1t_topology_atlas_v1';
  var LIMIT = 64;

  function readAtlas() {
    try {
      var value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      return Array.isArray(value) ? value : [];
    } catch (_) { return []; }
  }

  function writeAtlas(values) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(values.slice(-LIMIT)));
  }

  async function remember(input) {
    var verified = await api.verifyAny(input);
    var values = readAtlas().filter(function (item) { return item.trail_id !== verified.trail_id; });
    values.push(verified); writeAtlas(values); return verified;
  }

  function ensureOverlay() {
    if (document.getElementById('trailTopologyOverlay')) return;
    var style = document.createElement('style');
    style.textContent =
      '#trailTopologyOverlay{display:none;position:fixed;inset:0;z-index:10060;background:#090807f5;color:#e8e0d0;font-family:"DM Mono",monospace;overflow:auto}' +
      '#trailTopologyOverlay.open{display:block}.topology-shell{width:min(1040px,100%);min-height:100%;margin:auto;padding:24px}' +
      '.topology-head{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;border-bottom:1px solid #49312c;padding-bottom:16px;position:sticky;top:0;background:#090807fa;z-index:12}' +
      '.topology-kicker{font-size:9px;letter-spacing:.22em;color:#ff3333}.topology-title{font:58px/.9 "Bebas Neue",sans-serif;letter-spacing:.05em;margin:6px 0}' +
      '.topology-note{font-size:9px;line-height:1.6;color:#9a8f7a;max-width:620px}.topology-controls{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}' +
      '.topology-controls button{border:1px solid #49312c;background:#141210;color:#e8e0d0;padding:12px;font:9px "DM Mono",monospace;letter-spacing:.1em}.topology-controls .topology-sample{border-color:#cc1111;color:#ff3333}' +
      '.topology-map{padding:28px 0 70px}.topology-empty{border:1px dashed #49312c;padding:30px;color:#9a8f7a;font-size:10px}' +
      '.topology-line{position:relative;padding:0 0 34px 46px}.topology-line:before{content:"";position:absolute;left:14px;top:0;bottom:0;width:4px;background:#cc1111}' +
      '.topology-line:after{content:"";position:absolute;left:7px;top:23px;width:16px;height:16px;border-radius:50%;background:#090807;border:4px solid #ff3333}' +
      '.topology-line.forked{margin-left:28px}.topology-line.forked:before{transform:rotate(-2deg);transform-origin:top}.topology-line.forked:after{border-radius:0;transform:rotate(45deg)}' +
      '.topology-card{border:1px solid #49312c;background:#141210;padding:17px;box-shadow:7px 7px 0 #250b09}' +
      '.topology-card-head{display:flex;justify-content:space-between;gap:12px}.topology-id{font:28px "Bebas Neue",sans-serif;letter-spacing:.08em}.topology-format{font-size:8px;color:#ff3333;letter-spacing:.15em}' +
      '.topology-meta{font-size:8px;color:#9a8f7a;margin-top:5px;overflow-wrap:anywhere}.topology-parent{margin:12px 0;padding:8px;border-left:3px solid #cc1111;background:#0d0b0a;font-size:8px;color:#9a8f7a}' +
      '.topology-parent.missing{border-left-style:dashed;color:#cc9b7f}.topology-wear{margin-top:14px}.topology-legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;font-size:8px;color:#9a8f7a}.topology-legend b{color:#e8e0d0}' +
      '@media(max-width:600px){.topology-shell{padding:16px 13px}.topology-title{font-size:44px}.topology-head{position:static;display:block}.topology-controls{justify-content:flex-start;margin-top:12px}.topology-card-head{display:block}.topology-line{padding-left:30px}.topology-line:before{left:8px}.topology-line:after{left:1px}.topology-line.forked{margin-left:12px}}';
    document.head.appendChild(style);
    var overlay = document.createElement('section');
    overlay.id = 'trailTopologyOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'trailTopologyTitle');
    overlay.innerHTML = '<div class="topology-shell"><header class="topology-head"><div><div class="topology-kicker">LOCAL ATLAS / VERIFIED SNAPSHOTS</div><h2 class="topology-title" id="trailTopologyTitle">TRAIL TOPOLOGY</h2><div class="topology-note">Wear is evidence at rest: folds encode depth, crease weight encodes accumulated handling, black-red blocks remain concealed, and inherited paper continues to the fork before the child diverges.</div></div><div class="topology-controls"><button class="topology-sample" type="button">VIEW SAMPLE</button><button class="topology-close" type="button">CLOSE</button></div></header><main class="topology-map" id="trailTopologyMap"></main><div class="topology-legend"><span><b>PAPER</b> REVEALED</span><span><b>BLACK-RED</b> CONCEALED</span><span><b>WHITE EDGE</b> INHERITED</span><span><b>RED EDGE</b> DIVERGENT</span></div></div>';
    overlay.querySelector('.topology-close').addEventListener('click', close);
    overlay.querySelector('.topology-sample').addEventListener('click', function () { sample().catch(showError); });
    overlay.addEventListener('click', function (event) { if (event.target === overlay) close(); });
    document.body.appendChild(overlay);
  }

  function findParent(snapshot, graph) {
    if (!snapshot.parent || !snapshot.parent_known) return null;
    return graph.snapshots.find(function (candidate) { return candidate.trail_id === snapshot.parent.trail_id; }) || null;
  }

  function render(graph, status) {
    ensureOverlay();
    var map = document.getElementById('trailTopologyMap');
    map.innerHTML = '';
    if (status) {
      var banner = document.createElement('div');
      banner.className = 'topology-parent';
      banner.textContent = status;
      map.appendChild(banner);
    }
    if (!graph.snapshots.length) {
      map.innerHTML += '<div class="topology-empty">NO VERIFIED SNAPSHOTS IN THIS LOCAL ATLAS. CHOOSE VIEW SAMPLE TO INSPECT EVERY WEAR STATE.</div>';
      return;
    }
    graph.snapshots.forEach(function (snapshot) {
      var parentSnapshot = findParent(snapshot, graph);
      var displayStops = wear.composeFork(snapshot, parentSnapshot);
      var line = document.createElement('section');
      line.className = 'topology-line' + (snapshot.parent ? ' forked' : '');
      var card = document.createElement('article');
      card.className = 'topology-card';
      var head = document.createElement('div');
      head.className = 'topology-card-head';
      var id = document.createElement('div');
      id.className = 'topology-id'; id.textContent = 'TRAIL / ' + snapshot.short_id;
      var format = document.createElement('div');
      format.className = 'topology-format'; format.textContent = snapshot.format.toUpperCase();
      head.appendChild(id); head.appendChild(format); card.appendChild(head);
      var meta = document.createElement('div');
      meta.className = 'topology-meta';
      meta.textContent = snapshot.terrain + ' / ' + displayStops.length + ' VISIBLE SEGMENTS / ' + snapshot.created_at;
      card.appendChild(meta);
      if (snapshot.parent) {
        var parent = document.createElement('div');
        parent.className = 'topology-parent' + (snapshot.parent_known ? '' : ' missing');
        parent.textContent = (snapshot.parent_known ? 'VERIFIED PARENT PRESENT / ' : 'DECLARED PARENT ABSENT / ') +
          api.shortId(snapshot.parent.trail_id) + ' / FORK ' + String(snapshot.parent.fork_at).padStart(3, '0');
        card.appendChild(parent);
      }
      var mount = document.createElement('div');
      mount.className = 'topology-wear';
      wear.render(mount, {
        stops: displayStops,
        parent: snapshot.parent,
        depth: displayStops.length,
        crease_count: displayStops.length + (snapshot.parent ? snapshot.parent.fork_at + 1 : 0),
        fold_size: Math.min(28, 4 + displayStops.length * 2)
      }, {
        onOpen: function (url) {
          if (typeof window.selectUrl === 'function') window.selectUrl(url);
          close();
        }
      });
      card.appendChild(mount); line.appendChild(card); map.appendChild(line);
    });
  }

  async function validLocalGraph(current) {
    if (current) await remember(current);
    var valid = [], values = readAtlas();
    for (var index = 0; index < values.length; index += 1) {
      try { valid.push(await api.verifyAny(values[index])); } catch (_) {}
    }
    writeAtlas(valid);
    return api.build(valid);
  }

  async function open(current) {
    ensureOverlay(); render(await validLocalGraph(current));
    document.getElementById('trailTopologyOverlay').classList.add('open');
  }

  async function sample() {
    ensureOverlay();
    var parentManifest = await blind.create({
      created_at: '2026-09-14T20:00:00.000Z',
      corpus_revision: 'sha256:' + 'a'.repeat(64),
      terrain: 'SAMPLE / MIXED',
      trail_salt: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    });
    var first = await blind.commit(parentManifest, 'https://example.org/revealed', 'AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE');
    parentManifest = await blind.reveal(first.manifest, first.secret);
    var second = await blind.commit(parentManifest, 'https://concealed.invalid/withheld', 'AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI');
    parentManifest = second.manifest;
    var parent = await blind.envelope(parentManifest);
    var childManifest = await blind.create({
      created_at: '2026-09-14T21:00:00.000Z',
      corpus_revision: 'sha256:' + 'a'.repeat(64),
      terrain: 'SAMPLE / FORK',
      trail_salt: 'AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwM',
      parent: {
        trail_id: parent.trail_id,
        genesis_id: parent.manifest.genesis_id,
        fork_at: 1,
        commitment: parent.manifest.steps[1].commitment
      }
    });
    var childStep = await blind.commit(childManifest, 'https://example.net/divergent', 'BAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQ');
    childManifest = await blind.reveal(childStep.manifest, childStep.secret);
    var child = await blind.envelope(childManifest);
    render(await api.build([parent, child]), 'SAMPLE / VALID ARTIFACTS / NOT SAVED TO LOCAL ATLAS');
    document.getElementById('trailTopologyOverlay').classList.add('open');
  }

  function showError(error) {
    var map = document.getElementById('trailTopologyMap');
    if (map) map.textContent = 'REJECTED / ' + String(error && error.message || error).toUpperCase();
  }
  function close() { var overlay = document.getElementById('trailTopologyOverlay'); if (overlay) overlay.classList.remove('open'); }
  function clear() { localStorage.removeItem(STORAGE_KEY); return open(); }

  window.openTrailTopology = open;
  window.openTrailWearSample = sample;
  window.closeTrailTopology = close;
  window.rememberTopologySnapshot = remember;
  window.clearTrailTopology = clear;
  document.addEventListener('DOMContentLoaded', ensureOverlay);
  document.addEventListener('keydown', function (event) {
    var overlay = document.getElementById('trailTopologyOverlay');
    if (event.code === 'Escape' && overlay && overlay.classList.contains('open')) {
      event.preventDefault(); event.stopImmediatePropagation(); close();
    }
  }, true);
})();
